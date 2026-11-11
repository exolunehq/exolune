"""Read the material regions of a generated shell and pack them for the runtime.

A generated draft paints flat regions: shell, timber, glazing, light lines,
solar skin and cladding. This stage names the class of every atlas texel from
its colour, rejects the classes its surface orientation forbids, returns
painted highlights and shadows to the surface around them, and writes one
clamped signed-distance mask per class. The runtime thresholds the masks, so
class borders stay sharp at any distance, and renders each class with a
shared city material. The atlas colour only chooses the class and its mean
colour.
"""
import argparse
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# Mask channels follow this order after the shell: R timber, G glazing, B light, A solar,
# then cladding in the alpha of the colour map.
CLASSES = ('shell', 'timber', 'glazing', 'light', 'solar', 'cladding')
UNKNOWN, UNCOVERED = 254, 255
SPAN = 4  # The masks store the signed distance to a class border over +/- SPAN output texels.
COMPONENT = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path):
    data = Path(path).read_bytes()
    if struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('Expected a complete glTF 2 GLB')
    chunks, offset = {}, 12
    while offset < len(data):
        size, kind = struct.unpack_from('<II', data, offset)
        chunks[kind] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    return json.loads(chunks[0x4e4f534a]), chunks[0x004e4942]


def accessor(doc, blob, index):
    record = doc['accessors'][index]
    view = doc['bufferViews'][record['bufferView']]
    kind, width = np.dtype(COMPONENT[record['componentType']]), WIDTH[record['type']]
    start = view.get('byteOffset', 0) + record.get('byteOffset', 0)
    stride = view.get('byteStride', kind.itemsize * width)
    rows = np.lib.stride_tricks.as_strided(
        np.frombuffer(blob, 'u1', (record['count'] - 1) * stride + kind.itemsize * width, start),
        (record['count'], kind.itemsize * width), (stride, 1))
    return np.ascontiguousarray(rows).view(kind).reshape(record['count'], width)


def world_matrices(doc):
    """World matrix of every node that carries a mesh."""
    def local(node):
        if 'matrix' in node:
            return np.array(node['matrix'], 'f8').reshape(4, 4).T
        x, y, z, w = node.get('rotation', (0, 0, 0, 1))
        rotation = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        matrix = np.eye(4)
        matrix[:3, :3] = rotation * np.array(node.get('scale', (1, 1, 1)))
        matrix[:3, 3] = node.get('translation', (0, 0, 0))
        return matrix
    result = {}

    def visit(index, parent):
        node = doc['nodes'][index]
        matrix = parent @ local(node)
        if 'mesh' in node:
            result[index] = matrix
        for child in node.get('children', []):
            visit(child, matrix)
    for root in doc['scenes'][doc.get('scene', 0)]['nodes']:
        visit(root, np.eye(4))
    return result


def shell_triangles(doc, blob, material):
    """Atlas coordinates and upward normal component of every triangle that uses `material`. glTF is Y up."""
    uvs, ups = [], []
    for index, matrix in world_matrices(doc).items():
        for primitive in doc['meshes'][doc['nodes'][index]['mesh']]['primitives']:
            if primitive.get('material') != material:
                continue
            attributes = primitive['attributes']
            position = accessor(doc, blob, attributes['POSITION']).astype('f8') @ matrix[:3, :3].T
            normal = accessor(doc, blob, attributes['NORMAL']).astype('f8') @ np.linalg.inv(matrix[:3, :3])
            faces = accessor(doc, blob, primitive['indices']).reshape(-1, 3).astype('i8')
            corner = position[faces]
            face = np.cross(corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0])
            face /= np.maximum(np.linalg.norm(face, axis=1, keepdims=True), 1e-20)
            # The winding may be mirrored by a transform; the vertex normals name the outside.
            face *= np.sign(np.einsum('ij,ij->i', face, normal[faces].sum(1)))[:, None]
            uvs.append(accessor(doc, blob, attributes['TEXCOORD_0']).astype('f8')[faces])
            ups.append(face[:, 1])
    if not uvs:
        raise ValueError('The source has no generated shell surface')
    return np.concatenate(uvs), np.concatenate(ups)


def raster(uv, value, height, width):
    """Texels whose centre a triangle covers, with that triangle's value. Image rows follow glTF V."""
    covered = np.zeros((height, width), bool)
    field = np.zeros((height, width), 'f4')
    points = uv * (width, height) - 0.5
    for (a, b, c), v in zip(points, value):
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, width - 1), min(y1, height - 1)
        if x1 < x0 or y1 < y0:
            continue
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(area) < 1e-12:
            continue
        x, y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        s = ((b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)) / area
        t = ((c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)) / area
        inside = (s >= 0) & (t >= 0) & (s + t <= 1)
        covered[y0:y1 + 1, x0:x1 + 1] |= inside
        field[y0:y1 + 1, x0:x1 + 1][inside] = v
    return covered, field


def linear(rgb):
    c = np.asarray(rgb, 'f4') / 255
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


def oklab(rgb):
    c = linear(rgb)
    lms = np.cbrt(np.stack([.4122214708 * c[..., 0] + .5363325363 * c[..., 1] + .0514459929 * c[..., 2],
                            .2119034982 * c[..., 0] + .6806995451 * c[..., 1] + .1073969566 * c[..., 2],
                            .0883024619 * c[..., 0] + .2817188376 * c[..., 1] + .6299787005 * c[..., 2]], -1))
    return np.stack([.2104542553 * lms[..., 0] + .7936177850 * lms[..., 1] - .0040720468 * lms[..., 2],
                     1.9779984951 * lms[..., 0] - 2.4285922050 * lms[..., 1] + .4505937099 * lms[..., 2],
                     .0259040371 * lms[..., 0] + .7827717662 * lms[..., 1] - .8086757660 * lms[..., 2]], -1)


def spread(labels, target, allowed=None):
    """Each `target` texel takes the class of the nearest labelled texel, walking through `target` only.

    `allowed[k]` marks the texels class k may enter. Unreached texels keep their value.
    """
    height, width = labels.shape
    count = height * width
    flat = bytearray(labels.tobytes())
    todo = bytearray(target.astype('u1').tobytes())
    enter = None if allowed is None else [bytearray(a.astype('u1').tobytes()) for a in allowed]
    wanted = target.ravel()
    near = np.zeros(count, bool)
    near[1:] |= wanted[:-1]
    near[:-1] |= wanted[1:]
    near[width:] |= wanted[:-width]
    near[:-width] |= wanted[width:]
    queue = np.flatnonzero(near & ~wanted & (labels.ravel() < UNKNOWN)).tolist()
    head = 0
    while head < len(queue):
        i = queue[head]
        head += 1
        k = flat[i]
        x = i % width
        for j in (i - 1 if x else -1, i + 1 if x != width - 1 else -1, i - width, i + width):
            if 0 <= j < count and todo[j] and (enter is None or enter[k][j]):
                flat[j] = k
                todo[j] = 0
                queue.append(j)
    return np.frombuffer(bytes(flat), 'u1').reshape(height, width).copy()


def grow(mask, steps, within=None):
    for _ in range(steps):
        mask = mask | np.roll(mask, 1, 0) | np.roll(mask, -1, 0) | np.roll(mask, 1, 1) | np.roll(mask, -1, 1)
        if within is not None:
            mask &= within
    return mask


def components(mask):
    """Four-connected regions of `mask`: an index per texel, zero outside, and the region count."""
    height, width = mask.shape
    count = height * width
    todo = bytearray(mask.astype('u1').tobytes())
    index = np.zeros(count, 'i4')
    regions = 0
    for first in np.flatnonzero(mask.ravel()).tolist():
        if not todo[first]:
            continue
        regions += 1
        todo[first] = 0
        stack, members = [first], []
        while stack:
            i = stack.pop()
            members.append(i)
            x = i % width
            for j in (i - 1 if x else -1, i + 1 if x != width - 1 else -1, i - width, i + width):
                if 0 <= j < count and todo[j]:
                    todo[j] = 0
                    stack.append(j)
        index[members] = regions
    return index.reshape(height, width), regions


def majority(labels, covered, allowed, radius, fixed):
    """Most frequent class in a square window; the `fixed` class neither votes nor changes."""
    votes = np.stack([np.asarray(Image.fromarray((labels == k).astype('u1') * 255).filter(ImageFilter.BoxBlur(radius)), 'f4')
                      for k in range(len(CLASSES))])
    votes[~allowed] = -1
    votes[fixed] = -1
    return np.where(covered & (labels != fixed), votes.argmax(0), labels).astype('u1')


def classify(atlas, covered, up, surface):
    """Class index of every covered texel; UNCOVERED elsewhere. Also returns the median colour of each class."""
    classes = surface['classes']
    scale = covered.shape[1] / 2048  # Texel limits are stated for a 2048 atlas.
    lab = oklab(atlas)
    # A draft paints light and shadow into its colour: lightness says little about the material.
    weight = np.array([surface.get('lightness_weight', .25), 1, 1], 'f4')
    distance = np.full((len(CLASSES),) + covered.shape, np.inf, 'f4')
    allowed = np.empty((len(CLASSES),) + covered.shape, bool)
    for k, name in enumerate(CLASSES):
        low, high = classes[name].get('up', (-1, 1))
        allowed[k] = covered & (up >= low) & (up <= high)
        if 'reference' in classes[name]:
            distance[k] = np.linalg.norm((lab - oklab(classes[name]['reference'])) * weight, axis=-1)
    painted = distance.argmin(0)
    nearest = np.take_along_axis(distance, painted[None], 0)[0]
    # Dark strokes are joints and outlines; they belong to the surface around them.
    labels = np.where((nearest < surface.get('confidence', .06)) & (lab[..., 0] > surface.get('stroke_lightness', .30)),
                      painted, UNKNOWN).astype('u1')
    labels[~covered] = UNCOVERED
    # A painted region has a painted border: another colour or the island edge lies just across it.
    # A highlight or a shadow fades instead; it is not a material and returns to the surface around it.
    step = max(1, int(round(2 * scale)))
    coarse = labels[::step, ::step].copy()
    reach = int(surface.get('border_texels', 6) // 2)
    for k in range(len(CLASSES)):
        if not (coarse == k).any():
            continue
        # Strokes join the region: the cells of one glazed or solar surface are one region.
        mask = grow(coarse == k, reach, (coarse == k) | (coarse == UNKNOWN))
        index, regions = components(mask)
        edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
        firm = edge & grow(((coarse < UNKNOWN) & (coarse != k)) | (coarse == UNCOVERED), 1)
        share = np.bincount(index[firm], minlength=regions + 1) / np.maximum(np.bincount(index[edge], minlength=regions + 1), 1)
        faded = share < surface.get('painted_border', .4)
        faded[0] = False
        full = np.repeat(np.repeat(faded[index], step, 0), step, 1)[:labels.shape[0], :labels.shape[1]]
        labels[full & (labels == k)] = UNKNOWN
    # Orientation decides last. A class may name the one that wears its colour where it cannot be:
    # a pane cannot be a soffit, but cladding in the glazing colour can. A second choice is never asserted.
    for k, name in enumerate(CLASSES):
        barred = (labels == k) & ~allowed[k]
        other = CLASSES.index(classes[name]['else']) if 'else' in classes[name] else k
        labels[barred] = np.where(allowed[other][barred], other, UNKNOWN)
    distance[~allowed] = np.inf
    best = distance.argmin(0)
    colours = []
    for k, name in enumerate(CLASSES):
        chosen = atlas[labels == k]
        named = classes[name].get('reference') or classes[next(n for n in CLASSES if classes[n].get('else') == name)]['reference']
        colours.append(linear(np.median(chosen, 0) if len(chosen) else named).tolist())
    coarse = labels[::step, ::step]
    # A wide unread zone is a painted fade. It continues the readable surface it touches most,
    # so its border is the edge of something painted. Strokes are shared out from both sides.
    wide = int(round(surface.get('stroke_texels', 8) * scale / step / 2))
    zone = grow(~grow(coarse != UNKNOWN, wide), wide, coarse == UNKNOWN)
    index, regions = components(zone)
    touch = np.stack([np.bincount(index[zone & grow(coarse == k, reach)], minlength=regions + 1) for k in range(len(CLASSES))])
    choice = np.repeat(np.repeat(touch.argmax(0)[index], step, 0), step, 1)[:labels.shape[0], :labels.shape[1]]
    inside = np.repeat(np.repeat(zone, step, 0), step, 1)[:labels.shape[0], :labels.shape[1]] & (labels == UNKNOWN)
    inside &= np.take_along_axis(allowed, choice[None], 0)[0]
    labels[inside] = choice[inside]
    labels = spread(labels, labels == UNKNOWN, allowed)
    labels = np.where(labels == UNKNOWN, best, labels).astype('u1')
    # Opening: a region thinner than twice its class limit is a stroke or a bake smear, not a surface.
    removed = np.zeros(covered.shape, bool)
    for k, name in enumerate(CLASSES):
        mask = labels == k
        steps = int(round(classes[name].get('thin_texels', surface.get('thin_texels', 3)) * scale))
        if not mask.any() or steps < 1:
            continue
        core = mask & ~grow(covered & ~mask, steps)
        removed |= mask & ~grow(core, steps + 1, mask)
    before = labels.copy()
    labels[removed] = UNKNOWN
    labels = spread(labels, removed, allowed)
    labels = np.where(labels == UNKNOWN, before, labels).astype('u1')
    # Majority in a square window: a ragged painted border becomes a clean curve. Light lines keep their width.
    light = CLASSES.index('light')
    radius = int(round(surface.get('smooth_texels', 3) * scale))
    for _ in range(2 if radius else 0):
        labels = majority(labels, covered, allowed, radius, light)
    radius = int(round(2 * scale))
    if radius:
        lit = np.asarray(Image.fromarray((labels == light).astype('u1') * 255).filter(ImageFilter.BoxBlur(radius)), 'f4') > 127
        labels[covered & (labels == light) & ~lit] = UNKNOWN
        labels = spread(labels, labels == UNKNOWN, allowed)
        labels[lit & covered] = light
    return labels, colours


def border_distance(inside, reach):
    """Distance in texels from each texel centre to the nearest texel centre of the other side, clamped."""
    far = float(reach + 1)
    result = np.empty(inside.shape, 'f4')
    for side in (True, False):
        target = inside != side
        column = np.full(inside.shape, far, 'f4')
        for d in range(-reach, reach + 1):
            column = np.where(np.roll(target, d, 0), np.minimum(column, abs(d)), column)
        squared = np.full(inside.shape, far * far, 'f4')
        for d in range(-reach, reach + 1):
            squared = np.minimum(squared, np.roll(column, d, 1) ** 2 + d * d)
        result[inside == side] = np.sqrt(squared)[inside == side]
    return result


def masks(labels, size):
    """Clamped signed distances to the class borders: an RGBA image for timber, glazing, light and solar, and one for cladding."""
    height, width = labels.shape
    if height != width or width % size:
        raise ValueError('The atlas must be square and a multiple of the packed texture size')
    step = width // size
    padded = spread(labels, labels == UNCOVERED)  # Island margins continue their own class.
    padded[padded == UNCOVERED] = 0
    reach = SPAN * step
    channels = []
    for k in range(1, len(CLASSES)):
        inside = padded == k
        signed = np.where(inside, 1, -1) * (border_distance(inside, reach) - .5) if inside.any() else np.full(labels.shape, -float(reach), 'f4')
        signed = np.clip(signed, -reach, reach).reshape(size, step, size, step).mean((1, 3))
        channels.append(np.rint((.5 + signed / (2 * reach)) * 255).astype('u1'))
    return Image.fromarray(np.stack(channels[:4], -1), 'RGBA'), Image.fromarray(channels[4], 'L')


def read(source, surface):
    """Class map and class colours of the generated shell material in `source`."""
    doc, blob = load_glb(source)
    for index, material in enumerate(doc['materials']):
        if material.get('extras', {}).get('city_material') == 'generated_shell':
            break
    else:
        raise ValueError('No generated_shell material in ' + str(source))
    info = material['pbrMetallicRoughness']['baseColorTexture']
    view = doc['bufferViews'][doc['images'][doc['textures'][info['index']]['source']]['bufferView']]
    start = view.get('byteOffset', 0)
    atlas = np.asarray(Image.open(io.BytesIO(blob[start:start + view['byteLength']])).convert('RGB'))
    uv, up = shell_triangles(doc, blob, index)
    covered, field = raster(uv, up, *atlas.shape[:2])
    labels, colours = classify(atlas, covered, field, surface)
    return atlas, labels, colours


def preview(atlas, labels, colours, path):
    """Atlas beside its classes, each drawn in its measured colour."""
    paint = np.zeros(atlas.shape, 'u1')
    for k, colour in enumerate(colours):
        c = np.asarray(colour)
        paint[labels == k] = np.rint(np.where(c <= .0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - .055) * 255)
    Image.fromarray(np.concatenate([atlas, paint], 1)).save(path)


def demo():
    """A light stroke survives, a hairline does not, a glazed ceiling is cladding and borders sit at mid-grey."""
    # Stroke limits are stated for a 2048 atlas; this one is 256.
    surface = {'thin_texels': 24,
               'classes': {'shell': {'reference': [240, 230, 215]}, 'timber': {'reference': [180, 130, 80]},
                           'glazing': {'reference': [45, 80, 90], 'up': [-.35, .7], 'else': 'cladding'},
                           'light': {'reference': [250, 238, 170], 'thin_texels': 8},
                           'solar': {'reference': [20, 50, 105], 'up': [.25, 1]}, 'cladding': {}}}
    atlas = np.zeros((256, 256, 3), 'u1')
    atlas[:] = surface['classes']['shell']['reference']
    atlas[32:128, 32:128] = surface['classes']['timber']['reference']
    atlas[64:68, 40:120] = surface['classes']['light']['reference']
    atlas[100, 40:120] = surface['classes']['glazing']['reference']
    atlas[160:224, 32:128] = surface['classes']['glazing']['reference']
    atlas[160:224, 144:240] = surface['classes']['glazing']['reference']
    covered = np.ones((256, 256), bool)
    covered[:8] = False
    up = np.zeros((256, 256), 'f4')
    up[:, 136:] = -1  # A ceiling cannot be glazed: the glazing colour is cladding there.
    labels, colours = classify(atlas, covered, up, surface)
    assert labels[80, 80] == 1 and labels[66, 80] == 3 and labels[100, 80] == 1, 'strokes'
    assert labels[190, 80] == 2 and labels[190, 190] == 5 and labels[4, 4] == UNCOVERED, 'orientation'
    packed = np.asarray(masks(labels, 128)[0])
    assert packed[40, 40, 0] > 200 and packed[2, 60, 0] < 60 and abs(int(packed[16, 40, 0]) - 127) < 40, 'distance'
    print('surface_classes: self-check passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='master.glb of a generated building')
    parser.add_argument('--spec', type=Path, default=Path(__file__).resolve().parents[2] / 'assets/city/generated-buildings.json')
    parser.add_argument('--preview', type=Path, help='Write the atlas beside its classes')
    args = parser.parse_args()
    if not args.source:
        return demo()
    surface = json.loads(args.spec.read_text(encoding='utf8'))['surface']
    atlas, labels, colours = read(args.source, surface)
    share = {name: round(float((labels == k).sum() / max((labels < UNKNOWN).sum(), 1)), 4) for k, name in enumerate(CLASSES)}
    print(json.dumps({'classes': share, 'colours_linear': [[round(v, 3) for v in c] for c in colours]}))
    if args.preview:
        preview(atlas, labels, colours, args.preview)


if __name__ == '__main__':
    sys.exit(main())
