"""Prepare exact neutral-series sources for the shared city cooker (CPU Blender).

The neutral source remains immutable. Only dense structural surfaces are reduced;
fitted panes, access, sills and steps keep their source geometry at runtime LOD0.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import author
import cook
import details
import reference_house_master as common


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf8')


def triangles(objects):
    for obj in objects:
        obj.data.calc_loop_triangles()
    return sum(len(obj.data.loop_triangles) for obj in objects)


def palette(objects):
    author.materials()
    materials = {m.name: m for m in author.MATS}
    aliases = {'shell': 'ceramic', 'soffit': 'timber', 'reveal': 'teal',
               'glass': 'glazing', 'metal': 'satin_metal', 'door': 'slatted_timber', 'floor': 'stone'}
    for obj in objects:
        for slot in obj.material_slots:
            old = slot.material
            name = old.get('city_material', old.name.split(' - ')[-1])
            name = aliases.get(name, name)
            if name not in materials:
                raise ValueError('Unknown neutral material: ' + old.name)
            slot.material = materials[name]
        # Give each faceted material chart metric coordinates. The shared city
        # shader supplies normal/roughness detail without additional vertices.
        mesh = obj.data
        uv = mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            n = poly.normal
            axes = (0, 1) if abs(n.z) > .6 else (0, 2) if abs(n.y) > abs(n.x) else (1, 2)
            for loop in poly.loop_indices:
                p = obj.matrix_world @ mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv = (p[axes[0]] * .5, p[axes[1]] * .5)


def access(objects, metadata):
    """Describe the existing fitted access, then independently ray-test it."""
    family = metadata['family']
    groups = ['entry'] if family == 'house' else ['left_front', 'right_front'] if family == 'civic' else ['Conservatory_front', 'Conservatory_rear']
    for obj in objects:
        name = obj.name
        group = next((g for g in groups if g.lower() in name.lower()), None)
        if family == 'house' and ('entry' in name.lower()):
            group = 'entry'
        if group and ('sliding_leaf' in name or name == 'Recessed_entry_leaf'):
            details.mark(obj, 'door', group)
        elif group and ('opening_control' in name or name == 'Entry_opening_strip'):
            details.mark(obj, 'opening_control', group)
        if 'steps' in name.lower():
            details.mark(obj, 'threshold')
        if 'opening' in name.lower():
            obj['detail'] = 2
    for index, point in enumerate(metadata['construction']['entries']):
        group = groups[index]
        leaf = next(o for o in objects if o.get('city_assembly') == group and o.get('city_part') == 'door')
        # The neutral datum lies on the closed leaf plane. Put the walking
        # target in front of its actual thickness and projecting frame, as in
        # the common authoring door contract; do not ray-test through the door.
        points = [o.matrix_world @ v.co for o in objects
                  if o.get('city_assembly') == group and o.get('city_part') == 'door'
                  for v in o.data.vertices]
        approach = list(point)
        approach[1] = min(point[1], min(v.y for v in points)) - .10
        leaf['city_primary_entry'] = approach
    result = details.audit(objects)
    if not result['approach_clear']:
        raise ValueError('Source approach obstructed: ' + json.dumps(result['approach_obstructions'][:8]))
    return result


def prepare(source, destination, runtime_id, target):
    metadata = json.loads((source.parent / 'source.json').read_text())
    if sha(source) != metadata['master_sha256'] or not metadata['topology_passed']:
        raise ValueError('Unverified neutral source: ' + str(source))
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'source.json').exists():
        raise ValueError('Keep immutable runtime evidence; select a fresh output directory')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    palette(objects)
    raw = np.concatenate([cook.extract(o) for o in objects])
    total = triangles(objects)
    dense = [o for o in objects if len(o.data.loop_triangles) > 15000]
    fixed = total - triangles(dense)
    ratio = min(1., (target - fixed) / max(1, total - fixed))
    if ratio <= 0:
        raise ValueError('Fitted-part budget exceeds the building target')
    reductions = []
    for obj in dense:
        original = obj.copy()
        original.data = obj.data.copy()
        bpy.context.collection.objects.link(original)
        before = triangles([obj])
        bpy.context.view_layer.objects.active = obj
        if ratio < 1:
            mod = obj.modifiers.new('Recover source adjacency', 'WELD')
            mod.merge_threshold = 1e-6
            bpy.ops.object.modifier_apply(modifier=mod.name)
            mod = obj.modifiers.new('Bounded runtime structural surface', 'DECIMATE')
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=mod.name)
            # Reproject the original smooth shading after geometric reduction.
            mod = obj.modifiers.new('Retain source surface normals', 'DATA_TRANSFER')
            mod.object = original
            mod.use_loop_data = True
            mod.data_types_loops = {'CUSTOM_NORMAL'}
            mod.loop_mapping = 'POLYINTERP_NEAREST'
            bpy.ops.object.modifier_apply(modifier=mod.name)
        reductions.append({'part': obj.name, 'before': before, 'after': triangles([obj]), 'ratio': ratio})
        bpy.data.objects.remove(original, do_unlink=True)
    common.prepare_meshes(objects, dense)
    topology = common.topology(objects)
    if any(p['components'] != 1 or p['boundary_edges'] or p['nonmanifold_edges'] or p['zero_faces'] for p in topology):
        save(destination / 'rejected-topology.json', topology)
        raise ValueError('Runtime structural topology failed')
    reduced = np.concatenate([cook.extract(o) for o in objects])
    _, metrics = cook.audit(raw, reduced, float(np.linalg.norm(np.ptp(raw[:, :3], axis=0))),
                            cook.surface_tree(raw), cook.surface_samples(raw, 4096), 0)
    if triangles(objects) > 60000:
        raise ValueError('Runtime LOD0 exceeds the shared building limit')
    fittings = access(objects, metadata)
    for obj in objects:
        obj['asset_id'] = runtime_id
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    output = destination / 'master.glb'
    bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
                             export_extras=True, export_yup=True, export_normals=True, export_texcoords=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(destination / 'master.blend'))
    shutil.copy2(source.parent / 'source.json', destination / 'neutral-source.json')
    shutil.copy2(__file__, destination / Path(__file__).name)
    save(destination / 'source.json', {
        'id': runtime_id, 'backend': 'Directed neutral master; bounded structural reduction; shared city materials',
        'neural_mesh': False, 'neutral_source': str(source), 'neutral_source_sha256': sha(source),
        'neutral_metadata_sha256': sha(source.parent / 'source.json'), 'master_sha256': sha(output),
        'tools': {p: sha(HERE / p) for p in ['prepare_series_runtime.py', 'reference_house_master.py', 'cook.py', 'details.py', 'author.py']},
        'source_triangles': total, 'triangles': triangles(objects), 'structural_reductions': reductions,
        'source_surface': metrics, 'topology': topology, 'fittings': fittings,
        'reference': metadata['reference'], 'source_recipe': metadata['recipe'],
        'art_accepted': False, 'performance_accepted': False,
        'glazing': 'Shared opaque reflective exterior shader; interior traversal is not implemented'})
    print('PREPARED', runtime_id, total, '->', triangles(objects), 'p95', metrics['sampled_surface_p95_m'], flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--series', type=Path, required=True)
    p.add_argument('--mapping', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--asset')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    mapping = json.loads(a.mapping.read_text())
    for runtime_id, source_id in mapping['models'].items():
        if a.asset and runtime_id != a.asset:
            continue
        prepare(a.series / 'models' / source_id / 'master.glb', a.out / runtime_id,
                runtime_id, mapping.get('lod0_target', 54000))


if __name__ == '__main__':
    main()
