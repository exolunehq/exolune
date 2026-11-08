"""Export the approved smooth v2 skin in the game's metre frame with Blender.

blender --background --factory-startup --python preparer.py -- <smooth-v2.blend>
The reference source stays untouched. Nose -Y, up +Z, width approximately 8 m.
"""
from pathlib import Path
import sys, math, json
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cabine_maillage as cockpit

root = Path(__file__).resolve().parent
source = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
hull = bpy.data.objects['Navigator_Normal_Smooth']
for obj in list(bpy.data.objects):
    if obj != hull:
        bpy.data.objects.remove(obj, do_unlink=True)
hull.hide_set(False)
hull.hide_render = False
bpy.context.view_layer.objects.active = hull
hull.select_set(True)
hull.scale = tuple(s * 4 for s in hull.scale)
hull.rotation_euler.z += math.pi
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
hull.name = 'Navigator | smooth exterior'
material = hull.data.materials[0]
material.name = 'Navigator | polished chrome'
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.84, .87, .91, 1)
bsdf.inputs['Metallic'].default_value = 1
bsdf.inputs['Roughness'].default_value = .075
cockpit.build(hull,root)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'vaisseau_travail.blend'))
# Save the editable parts, then evaluate and batch only the export copy into hull and cabin.
bpy.ops.object.select_all(action='DESELECT')
copies=[]
deps=bpy.context.evaluated_depsgraph_get()
for obj in list(bpy.context.scene.objects):
    if obj.type not in {'MESH','CURVE'}:continue
    mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),depsgraph=deps)
    copy=bpy.data.objects.new('Export | '+obj.name,mesh)
    bpy.context.collection.objects.link(copy)
    copy.matrix_world=obj.matrix_world.copy()
    if obj!=hull:copies.append(copy)
    else:exportHull=copy
for obj in copies:obj.select_set(True)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join()
cab=bpy.context.object;cab.name='Navigator | cabin'
bpy.ops.object.select_all(action='DESELECT')
cab.select_set(True);exportHull.select_set(True)
bpy.context.view_layer.objects.active=exportHull
bpy.ops.export_scene.gltf(filepath=str(root/'navigateur-cockpit.glb'), export_format='GLB',
    use_selection=True, export_apply=False, export_cameras=False, export_lights=False)
print('NAVIGATOR_GAME_EXPORT_COMPLETE', list(hull.dimensions))
