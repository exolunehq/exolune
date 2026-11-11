"""Bake the room behind one window of a generated draft into an RGBA layer. Runs in background Blender.

A draft whose input image shows a furnished interior keeps that room behind its
glazing. This stage looks into it orthogonally from the window plane, inside an
oriented box: RGB stores the draft's own colour, A the first-hit depth over the
box depth. The city draws it behind the pane by parallax, without interior
geometry (docs/spec-ville-procedurale.md#baked-interiors).

The box is given in the draft's imported space: `origin` is the window's lower
left corner seen from outside, `u` and `v` span its width and height, and the
outward normal is u x v. Rays start on the window plane, so geometry in front
of it (mullions, the shell around a recessed pane) never enters the bake.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SKY = (0.80, 0.84, 0.88)   # A ray that leaves the room through a far window meets open daylight.


def load(path):
    """Import the draft as one triangulated mesh object with applied transforms."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def colour_map(obj, side):
    """The base colour feeding the draft's surface, resampled once to `side`; rows run bottom-up like UVs."""
    material = obj.data.materials[0]
    bsdf = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    image = bsdf.inputs['Base Color'].links[0].from_node.image
    if tuple(image.size) != (side, side):
        image = image.copy()
        image.scale(side, side)
    pixels = np.empty(side * side * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(side, side, 4)[:, :, :3]


def bake(obj, box, size, texture_side=2048):
    """Return a (size, size, 4) array: colour and normalised depth, row 0 at the bottom of the window."""
    origin, u, v = (np.asarray(box[k], dtype=float) for k in ('origin', 'u', 'v'))
    depth = float(box['depth'])
    inward = -np.cross(u, v) / np.linalg.norm(np.cross(u, v))
    mesh = obj.data
    if any(p.loop_total != 3 for p in mesh.polygons):
        raise ValueError('The draft must be triangulated')
    tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', co)
    corners = np.empty(len(mesh.polygons) * 3, dtype=np.int64)
    mesh.polygons.foreach_get('vertices', corners)
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers.active.data.foreach_get('uv', uv)
    co, corners, uv = co.reshape(-1, 3), corners.reshape(-1, 3), uv.reshape(-1, 3, 2)
    step = (np.arange(size) + 0.5) / size
    direction = Vector(inward)
    hit_face = np.full((size, size), -1, dtype=np.int64)
    hit_point = np.zeros((size, size, 3))
    distance = np.ones((size, size))
    for row, t in enumerate(step):
        for col, s in enumerate(step):
            location, _, face, length = tree.ray_cast(Vector(origin + u * s + v * t), direction, depth)
            if location is not None:
                hit_face[row, col], hit_point[row, col], distance[row, col] = face, location, length / depth
    rgba = np.empty((size, size, 4), dtype=np.float32)
    rgba[:, :] = (*SKY, 1.0)
    found = hit_face >= 0
    faces = hit_face[found]
    a, b, c = (co[corners[faces, k]] for k in range(3))
    p = hit_point[found]
    # Barycentric weights of each hit inside its triangle, then its texture coordinate.
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    denominator = np.maximum(d00 * d11 - d01 * d01, 1e-20)
    wb = (d11 * d20 - d01 * d21) / denominator
    wc = (d00 * d21 - d01 * d20) / denominator
    wa = 1 - wb - wc
    texcoord = wa[:, None] * uv[faces, 0] + wb[:, None] * uv[faces, 1] + wc[:, None] * uv[faces, 2]
    texels = colour_map(obj, texture_side)
    x = np.clip(texcoord[:, 0] % 1.0 * texture_side - 0.5, 0, texture_side - 1.001)
    y = np.clip(texcoord[:, 1] % 1.0 * texture_side - 0.5, 0, texture_side - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    colour = ((texels[y0, x0] * (1 - fx) + texels[y0, x0 + 1] * fx) * (1 - fy)
              + (texels[y0 + 1, x0] * (1 - fx) + texels[y0 + 1, x0 + 1] * fx) * fy)
    rgba[found, :3] = colour
    rgba[:, :, 3] = distance
    return rgba, {'hits': float(found.mean()), 'depth_mean': float(distance[found].mean()) if found.any() else 1.0}


def save(rgba, path):
    side = rgba.shape[0]
    image = bpy.data.images.new('interior_bake', side, side, alpha=True)
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()


def check():
    """A back wall 2 m behind a 4 m deep box: half depth, colour rising along u."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new('wall')
    mesh.from_pydata([(-1, 2, -1), (1, 2, -1), (1, 2, 1), (-1, 2, 1)], [], [(0, 1, 2), (0, 2, 3)])
    layer = mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        p = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = ((p.x + 1) / 2, (p.z + 1) / 2)
    image = bpy.data.images.new('gradient', 64, 64)
    image.pixels.foreach_set(np.repeat(np.tile(np.linspace(0, 1, 64), 64), 4).astype(np.float32))
    material = bpy.data.materials.new('wall')
    material.use_nodes = True
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    bsdf = material.node_tree.nodes['Principled BSDF']
    material.node_tree.links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
    mesh.materials.append(material)
    obj = bpy.data.objects.new('wall', mesh)
    bpy.context.scene.collection.objects.link(obj)
    box = {'origin': [-1, 0, -1], 'u': [2, 0, 0], 'v': [0, 0, 2], 'depth': 4}
    rgba, stats = bake(obj, box, 16, texture_side=64)
    assert stats['hits'] == 1.0, stats
    assert np.allclose(rgba[:, :, 3], 0.5, atol=1e-4), rgba[:, :, 3]
    assert (np.diff(rgba[8, :, 0]) > 0).all(), rgba[8, :, 0]
    print('interior_bake check passed', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', type=Path)
    parser.add_argument('--box', help='JSON text or a .json file: origin, u, v, depth in the draft space')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--size', type=int, default=1024)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.check:
        return check()
    box = json.loads(Path(args.box).read_text(encoding='utf8') if args.box.endswith('.json') else args.box)
    obj = load(args.draft)
    rgba, stats = bake(obj, box, args.size)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save(rgba, args.out)
    # Eight bits of depth step visibly at grazing views: the cooker packs this float map into 16 bits.
    depth = args.out.with_suffix('.depth.npy')
    np.save(depth, rgba[:, :, 3].astype('<f4'))
    record = {'draft': str(args.draft), 'draft_sha256': hashlib.sha256(args.draft.read_bytes()).hexdigest(),
              'box': box, 'size': args.size, 'image_sha256': hashlib.sha256(args.out.read_bytes()).hexdigest(),
              'depth_sha256': hashlib.sha256(depth.read_bytes()).hexdigest(), 'depth_rows': 'bottom-up',
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **stats}
    args.out.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    print('BAKED', args.out, json.dumps(stats), flush=True)


if __name__ == '__main__':
    main()
