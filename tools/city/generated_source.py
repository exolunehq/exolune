"""Turn a generated first draft into a metric city source. Runs in background Blender.

The generated mesh keeps its form. This stage orients it, sets its metric
scale and ground datum, bounds its triangle count, separates the entrance leaf
and fits a threshold and a pull on it. It writes master.glb and source.json for
the common cooker. It never marks art or performance accepted.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def triangles(objects):
    for obj in objects:
        obj.data.calc_loop_triangles()
    return sum(len(obj.data.loop_triangles) for obj in objects)


def load(path):
    """Import the draft as one mesh object with applied transforms."""
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
    for other in list(bpy.context.scene.objects):
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    return obj


def normalize(obj, yaw_degrees, height_m, stretch=(1.0, 1.0, 1.0), length_m=None, anchor='ground', align=False):
    """Entrance towards -Y, metric size, footprint centred, lowest point on the ground datum.

    `length_m` scales by the X extent instead of the height (a beam segment); `anchor`
    'top' hangs the model from z = 0 (a suspended cabin under its guide beam), 'centre' centres it."""
    mesh = obj.data
    mesh.transform(Matrix.Rotation(math.radians(yaw_degrees), 4, 'Z'))
    if align:
        # An object drafted in three-quarter view can come out turned: square it to its
        # smallest bounding rectangle, long side along X.
        xy = np.array([v.co[:2] for v in mesh.vertices])[::max(1, len(mesh.vertices) // 20000)]
        def extent(a):
            c, s = math.cos(a), math.sin(a)
            r = xy @ np.array([[c, -s], [s, c]])
            return np.ptp(r[:, 0]), np.ptp(r[:, 1])
        best = min(np.radians(np.arange(0, 90, .5)), key=lambda a: np.prod(extent(a)))
        w, d = extent(best)
        mesh.transform(Matrix.Rotation(-(best + (math.pi / 2 if d > w else 0)), 4, 'Z'))
    points = np.array([v.co for v in mesh.vertices])
    lo, hi = points.min(0), points.max(0)
    scale = length_m / (hi[0] - lo[0]) if length_m else height_m / (hi[2] - lo[2])
    centre = (lo + hi) / 2
    mesh.transform(Matrix.Translation((-centre[0], -centre[1], -{'top': hi[2], 'centre': centre[2]}.get(anchor, lo[2]))))
    mesh.transform(Matrix.Diagonal((scale * stretch[0], scale * stretch[1], scale * stretch[2], 1.0)))
    mesh.update()
    return float(scale)


def reduce(obj, limit):
    """Weld import seams, collapse to `limit` triangles and keep area-weighted normals with crisp creases."""
    before = triangles([obj])
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new('Recover geometric adjacency', 'WELD')
    modifier.merge_threshold = 1e-5
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if before > limit:
        modifier = obj.modifiers.new('Bounded source reduction', 'DECIMATE')
        modifier.ratio = limit / before
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return before, triangles([obj])


def probe(obj, entry, heights=(0.3, 1.1, 2.0)):
    """The built surface met from the front, the standing line in front of its nearest point, and the ground there.

    `heights` above the floor sample the facade; an open entrance samples above furniture seen through its glazing.
    """
    tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    x, floor = entry['x'], entry['z_floor']

    def surface(px, pz):
        """Depth of the first surface met from the front at (px, pz)."""
        hit = tree.ray_cast(Vector((px, -200.0, pz)), Vector((0, 1, 0)), 400.0)
        if hit[0] is None:
            raise ValueError('No surface in front of the declared entrance')
        return hit[0].y

    # A generated wall is rarely square to the facade: stand in front of its nearest point.
    # A reduced glazed front can keep small holes: a ray through one is ignored, not fatal.
    hits = [tree.ray_cast(Vector((x + dx, -200.0, floor + dz)), Vector((0, 1, 0)), 400.0)[0]
            for dx in (-0.6, -0.3, 0.0, 0.3, 0.6) for dz in heights]
    hits = [h.y for h in hits if h is not None]
    if len(hits) < 3:
        raise ValueError('No surface in front of the declared entrance')
    front = min(hits)
    down = tree.ray_cast(Vector((x, front - 0.35, floor + 1.0)), Vector((0, 0, -1)), 5.0)
    ground = down[0].z if down[0] is not None else floor
    return surface, front, ground


def separate_door(obj, entry):
    """Split the generated door leaf from the shell; return it with a probe of the built surface."""
    surface, front, ground = probe(obj, entry)
    x, floor, width, height = entry['x'], entry['z_floor'], entry['width'], entry['height']
    plane = surface(x, floor + height * 0.5)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    count = 0
    for poly in obj.data.polygons:
        c = poly.center
        poly.select = (abs(c.x - x) <= width / 2 and floor <= c.z <= floor + height and abs(c.y - plane) <= 0.3
                       and poly.normal.y < -0.35)
        count += poly.select
    if count < 2:
        raise ValueError('Declared entrance does not match a door surface')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    leaf = next(o for o in bpy.context.selected_objects if o != obj)
    leaf.name = 'entry_door_leaf'
    return leaf, surface, front, ground


def box(name, centre, size, material, tags):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=centre, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        p = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = (p.x * 0.5 + p.y * 0.5, p.z * 0.5)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for key, value in tags.items():
        obj[key] = value
    return obj


def prepare(spec, asset_id, model, out):
    import author
    import details
    folder = Path(out) / asset_id
    if (folder / 'source.json').exists():
        raise ValueError('Keep immutable source evidence; select a fresh output directory')
    folder.mkdir(parents=True, exist_ok=True)
    shell = load(model)
    source_triangles = triangles([shell])
    scale = normalize(shell, spec['yaw_degrees'], spec.get('height_m'), spec.get('stretch', (1.0, 1.0, 1.0)),
                      spec.get('length_m'), spec.get('anchor', 'ground'), spec.get('align', False))
    before, after = reduce(shell, spec.get('triangles', 56000))
    shell.name = 'generated_shell'
    for material in shell.data.materials:
        material['city_material'] = 'generated_shell'
    shell['city_part'] = 'shell'
    if 'entry' not in spec:
        # Furniture, canopies and transport structures have no entrance to fit.
        smooth(shell, spec)
        return write(spec, asset_id, model, folder, [shell], scale, source_triangles, before, after, {'parts': {}, 'assemblies': {}})
    entry = spec['entry']
    author.materials()
    metal = next(m for m in author.MATS if m['city_material'] == 'satin_metal')
    group = 'entry'
    tags = lambda role, detail: {'city_part': role, 'city_assembly': group, 'detail': detail}
    if entry.get('open'):
        # A patio or a glazed lobby has no generated leaf to separate: fit a timber leaf, as on the
        # boards, at the nearest facade point, so the entrance keeps a readable door, pull and threshold.
        # The facade is sampled above furniture: a table seen through the glazing is not the front.
        surface, front, ground = probe(shell, entry, (1.3, 1.7, 2.1))
        timber = next(m for m in author.MATS if m['city_material'] == 'timber')
        leaf = box('entry_door_leaf', (entry['x'], front - 0.04, ground + entry['height'] / 2),
                   (entry['width'], 0.06, entry['height']), timber, {})
        surface = lambda px, pz: front - 0.07
    else:
        leaf, surface, front, ground = separate_door(shell, entry)
    details.mark(leaf, 'door', group)
    leaf['city_primary_entry'] = [entry['x'], front - 0.10, ground]
    pull_x = entry['x'] + entry['width'] * 0.32
    pull_y = surface(pull_x, ground + 1.08)
    parts = [
        box('entry_threshold', (entry['x'], front - 0.02, ground + 0.012), (entry['width'] + 0.10, 0.30, 0.024), metal,
            tags('threshold', 1)),
        box('entry_pull', (pull_x, pull_y - 0.055, ground + 1.08), (0.028, 0.028, 0.62), metal, tags('handle', 2)),
        box('entry_pull_upper_standoff', (pull_x, pull_y - 0.028, ground + 1.32), (0.02, 0.055, 0.02), metal, tags('handle', 2)),
        box('entry_pull_lower_standoff', (pull_x, pull_y - 0.028, ground + 0.84), (0.02, 0.055, 0.02), metal, tags('handle', 2)),
    ]
    for obj in (shell,) if entry.get('open') else (shell, leaf):
        smooth(obj, spec)
    objects = [shell, leaf, *parts]
    fittings = details.audit(objects)
    if not fittings['approach_clear']:
        raise ValueError('Entrance approach obstructed: ' + json.dumps(fittings['approach_obstructions'][:6]))
    write(spec, asset_id, model, folder, objects, scale, source_triangles, before, after, fittings)


def smooth(obj, spec):
    """Area-weighted normals on generated geometry; creases sharper than the limit stay crisp."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    limit = math.radians(spec.get('sharp_degrees', 42.0))
    for edge in bm.edges:
        edge.smooth = len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) < limit
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(obj.data)
    bm.free()
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new('Area-weighted normals', 'WEIGHTED_NORMAL')
    modifier.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def write(spec, asset_id, model, folder, objects, scale, source_triangles, before, after, fittings=None):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj['asset_id'] = asset_id
        obj.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'master.blend'))
    bpy.ops.export_scene.gltf(filepath=str(folder / 'master.glb'), export_format='GLB', use_selection=True,
                              export_extras=True, export_tangents=False, export_yup=True, export_cameras=False,
                              export_lights=False)
    points = np.array([o.matrix_world @ v.co for o in objects for v in o.data.vertices])
    lo, hi = points.min(0), points.max(0)
    source = {'id': asset_id, 'kind': spec['kind'], 'floors': spec.get('floors', 1),
              'backend': 'Generated first draft; local metric fitting, bounded reduction and fitted entrance hardware',
              'neural_mesh': True, 'draft': spec['draft'], 'draft_sha256': digest(model),
              'draft_triangles': source_triangles, 'metric_scale': scale, 'reduction': {'before': before, 'after': after},
              'bounds_z_up': [lo.tolist(), hi.tolist()], 'triangles': triangles(objects), 'fittings': fittings,
              'master_sha256': digest(folder / 'master.glb'),
              'tools': {name: digest(HERE / name) for name in ['generated_source.py', 'author.py', 'details.py']},
              'art_accepted': False, 'performance_accepted': False}
    (folder / 'source.json').write_text(json.dumps(source, indent=2) + '\n', encoding='utf8')
    print('SOURCE', asset_id, source['triangles'], 'triangles', [round(v, 2) for v in (hi - lo)], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, default=HERE.parents[1] / 'assets/city/generated-buildings.json')
    parser.add_argument('--asset', required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--entry-x', type=float, help='Try another entrance position along the front; record it in the spec once it passes')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    spec = json.loads(args.spec.read_text(encoding='utf8'))['assets'][args.asset]
    if args.entry_x is not None:
        spec['entry']['x'] = args.entry_x
    prepare(spec, args.asset, args.model, args.out)


if __name__ == '__main__':
    main()
