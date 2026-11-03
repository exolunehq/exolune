"""Blender background asset conversion; never opens or controls the user's Blender session.

Run through prepare_biomes.py. Preserve UVs and normals while reducing the two selected CC0 source meshes.
"""
import sys
from pathlib import Path
import bpy
import numpy as np

source, output = map(Path, sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
for node, name, budget in [('fir_sapling_a', 'fir_open', 48000), ('fir_sapling_c', 'fir_dense', 48000)]:
    obj = bpy.data.objects.get(node)
    if obj is None or obj.type != 'MESH':
        raise ValueError('Missing source mesh: '+node)
    obj.data.calc_loop_triangles()
    modifier = obj.modifiers.new('Runtime triangle budget', 'DECIMATE')
    modifier.ratio = min(1.0, budget / len(obj.data.loop_triangles))
    modifier.use_collapse_triangulate = True
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    vertices = np.empty((len(mesh.loop_triangles)*3, 9), dtype='<f4')
    uv = mesh.uv_layers.active.data
    transform = obj.matrix_world
    normals = transform.to_3x3().inverted().transposed()
    for t, tri in enumerate(mesh.loop_triangles):
        for corner, loop in enumerate(tri.loops):
            p = transform @ mesh.vertices[mesh.loops[loop].vertex_index].co
            n = (normals @ mesh.corner_normals[loop].vector).normalized()
            # Blender Z-up -> the glTF/engine Y-up reference frame.
            vertices[3*t+corner] = (p.x,p.z,-p.y,n.x,n.z,-n.y,uv[loop].uv.x,1-uv[loop].uv.y,tri.material_index)
    output.mkdir(parents=True, exist_ok=True)
    np.savez(output/(name+'.npz'), vertices=vertices)
    print(name, len(vertices)//3, 'triangles', flush=True)
    evaluated.to_mesh_clear()
