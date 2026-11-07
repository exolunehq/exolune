"""Blender assembly regression checks; run on vaisseau_travail.blend.

Checks the actual meshes, pilot visibility and all six animated assemblies.
This is a geometry check, not a performance or image-quality benchmark.
"""
import json
import math
import bpy
from mathutils import Vector

bpy.context.view_layer.update()
errors = []
contacts = 0
recessed = 0
covers = 0
fitted = 0
min_control_gap = math.inf
max_gap = 0.0
for obj in bpy.data.objects:
    if 'support_mesh' not in obj:
        continue
    support = bpy.data.objects[obj['support_mesh']]
    normal = Vector(obj['support_normal'])
    xyz = obj['support_contacts']
    for i in range(0, len(xyz), 3):
        p = Vector(xyz[i:i+3])
        hit, q, _, _ = support.ray_cast(p+normal*.03, -normal, distance=.06)
        gap = (q-p).length if hit else math.inf
        max_gap = max(max_gap, gap); contacts += 1
        if gap > .002:
            errors.append((obj.name, 'support gap', gap))
    mode = obj.get('mounting_mode', '')
    if mode.startswith('recessed'):
        recessed += mode == 'recessed'; covers += mode == 'recessed-cover'
        center = Vector(obj['mounting_center'])
        probe = Vector(obj.get('pocket_probe',center))
        hit, q, _, _ = support.ray_cast(probe+normal*.04, -normal, distance=.10)
        depth = (q-probe).dot(normal) if hit else 0
        if abs(depth+obj['pocket_depth']) > .001:
            errors.append((obj.name, 'missing closed recess', depth))
        # Measure the actual printed fascia / display bezel, not the switches.
        mat = 'Jeu | Structure cabine' if mode == 'recessed-cover' else 'Jeu | plaques' if obj.name.startswith('Module |') else 'Jeu | Caoutchouc'
        vertices = {i for p in obj.data.polygons if obj.data.materials[p.material_index].name == mat for i in p.vertices}
        top = max((obj.matrix_world @ obj.data.vertices[i].co-center).dot(normal) for i in vertices)
        if abs(top-obj['fascia_depth']) > .0001:
            errors.append((obj.name, 'protruding fascia', top))
        if obj.get('fitted_panel'):
            fitted += 1
            min_control_gap=min(min_control_gap,obj['control_clearance'])
            if obj['control_clearance'] < -.0001:
                errors.append((obj.name,'control crosses the panel outline'))

# Check the face centre and eight near-corner points of every live display.
eye = Vector((0, -.9192, 1.03))
scene, dg = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
screen_samples = 0
for obj in bpy.data.objects:
    if obj.type != 'MESH' or not obj.name.startswith('Ecran | '):
        continue
    faces = [p for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith('Jeu | ecran_')]
    for face in faces:
        pts = [obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices]
        assert len(pts) == 4, obj.name
        for a in (.08, .5, .92):
            for b in (.08, .5, .92):
                p = pts[0].lerp(pts[1], a).lerp(pts[3].lerp(pts[2], a), b)
                delta = p-eye
                hit, q, _, _, blocker, _ = scene.ray_cast(dg, eye, delta.normalized(), distance=delta.length+.001)
                screen_samples += 1
                if not hit or blocker != obj or (q-p).length > .002:
                    errors.append((obj.name, 'screen occluded', blocker.name if hit else None))

# No fixed trim enters the initial pilot-eye clearance sphere.
for obj in bpy.data.collections['Spaceship_Cockpit'].all_objects:
    if obj.type != 'MESH':
        continue
    for v in obj.data.vertices:
        if (obj.matrix_world @ v.co-eye).length < .08:
            errors.append((obj.name, 'pilot eye clearance')); break

pivots = [o for o in bpy.data.objects if o.name.startswith('Pivot |')]
assert len(pivots) == 6, [o.name for o in pivots]
assert contacts >= 500 and recessed == 10 and fitted == 7 and covers == 4 and screen_samples == 27, (contacts, recessed, fitted, covers, screen_samples)
retainer = bpy.data.objects['Verriere | cadre']
assert retainer['retainer_width_m'] == .034 and retainer['retainer_thickness_m'] == .012
print(json.dumps({'support_samples': contacts, 'max_support_gap_mm': round(max_gap*1000, 4),
                  'recessed_instruments': recessed, 'recessed_service_covers': covers, 'visible_screen_samples': screen_samples,
                  'fitted_panels': fitted, 'minimum_control_edge_clearance_mm': round(min_control_gap*1000,3),
                  'animation_pivots': len(pivots), 'retainer_width_mm': 34, 'retainer_thickness_mm': 12, 'errors': errors}, indent=2))
assert not errors, errors
