"""CPU geometry checks for the forward sightline and dashboard wing junctions.

Run in Blender on vaisseau_travail.blend. This checks ray intersections with
the actual opaque meshes; it does not render or measure game performance.
"""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panneaux_cockpit import clearance

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
vertices, faces, owners = [], [], []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or obj.name == 'Canopy_Glass':
        continue
    evaluated = obj.evaluated_get(dg)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    base = len(vertices)
    vertices.extend(obj.matrix_world @ v.co for v in mesh.vertices)
    for tri in mesh.loop_triangles:
        faces.append(tuple(base+i for i in tri.vertices))
        owners.append(obj.name)
    evaluated.to_mesh_clear()
tree = BVHTree.FromPolygons(vertices, faces, all_triangles=True)

eye = Vector((0, -.9192, 1.03))
offsets = ((0, 0, 0), (.03, 0, 0), (-.03, 0, 0), (0, -.06, 0), (0, .06, 0))
report = {'nose': [], 'wings': {}}
for offset in offsets:
    origin = eye+Vector(offset)
    hits = 0
    for i in range(181):
        for j in range(101):
            ray = Vector((-1+2*i/180, -1, -.5625+1.125*j/100)).normalized()
            p, _, index, _ = tree.ray_cast(origin, ray, 20)
            if index is not None and owners[index] == 'Coque | peau' and p.y < -1.52:
                hits += 1
    report['nose'].append({'eye_offset': offset, 'visible_rays': hits})

for name in ('Module | feux', 'Module | carbu'):
    obj = bpy.data.objects[name]
    center, u, v, normal = (Vector(obj[key]) for key in
                           ('mounting_center', 'mounting_u', 'mounting_v', 'support_normal'))
    flat = list(obj['mounting_outline'])
    outline, size = list(zip(flat[::2], flat[1::2])), obj['mounting_size']
    total, blocked = 0, []
    for offset in offsets:
        origin = eye+Vector(offset)
        for i in range(15):
            for j in range(12):
                x, y = (-.5+(i+.5)/15)*size[0], (-.5+(j+.5)/12)*size[1]
                if clearance(outline, (x, y)) < .006:
                    continue
                total += 1
                p = center+u*x+v*y-normal*.0015
                ray = p-origin
                _, _, index, _ = tree.ray_cast(origin, ray.normalized(), ray.length+.004)
                if index is None or owners[index] != name:
                    blocked.append(owners[index] if index is not None else 'none')
    report['wings'][name] = {'samples': total, 'blocked': len(blocked), 'blockers': sorted(set(blocked))}

print(json.dumps(report, indent=2))
assert all(item['visible_rays'] == 0 for item in report['nose']), 'Foredeck enters the pilot sightline'
assert all(item['blocked'] == 0 for item in report['wings'].values()), 'Console return occludes a dashboard panel'
