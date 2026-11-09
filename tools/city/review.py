"""Reimport a delivered GLB and render architectural review views on the CPU."""
from pathlib import Path
import argparse
import math
import sys
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('asset',type=Path);parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--views',default='quarter,back,street');parser.add_argument('--size',type=int,default=960)
parser.add_argument('--clay',action='store_true',help='Neutral material for geometry-only comparisons')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.asset))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if args.clay:
    material=bpy.data.materials.new('Geometry diagnostic, not a material preview');material.use_nodes=True
    shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.42,.43,.40,1)
    shader.inputs['Roughness'].default_value=.65
    for obj in objects:
        obj.data.materials.clear();obj.data.materials.append(material)
        for face in obj.data.polygons:face.material_index=0
points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
target=(lo+hi)*.5;scale=max(hi.x-lo.x,hi.y-lo.y,(hi.z-lo.z)*1.2)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=args.size;scene.render.resolution_y=int(args.size*.75);scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.0
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.68,.84,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.40
bpy.ops.mesh.primitive_plane_add(size=scale*80,location=(0,0,lo.z-.03))
floor=bpy.context.object;m=bpy.data.materials.new('Review ground');m.use_nodes=True
m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.12,.15,.10,1)
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.92;floor.data.materials.append(m)
data=bpy.data.lights.new('Sun','SUN');data.energy=2.5;data.angle=math.radians(3)
sun=bpy.data.objects.new('Sun',data);scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(28),math.radians(-25),math.radians(-38))
data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(camera);scene.camera=camera
views={'quarter':(Vector((1.1,-1.6,.72))*scale+target,target,True),
       'back':(Vector((-1.25,1.7,.60))*scale+target,target,True),
       'street':(Vector((scale*.62,-scale*.95,2.0)),Vector((0,0,hi.z*.32)),False),
       'top':(Vector((.3,-.5,2.1))*scale+target,target,True)}
for name in args.views.split(','):
    position,look,ortho=views[name]
    data.type='ORTHO' if ortho else 'PERSP';data.ortho_scale=scale*1.53;data.lens=28
    camera.location=position;camera.rotation_euler=(look-position).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(args.out/(name+'.png'));bpy.ops.render.render(write_still=True)
