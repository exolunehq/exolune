"""Offline geometry review in background Blender; never starts the game or changes the source scene."""
from pathlib import Path
import argparse,sys,math
import bpy
from mathutils import Vector

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=root.parents[2]/'artifacts/navigateur-cockpit-son-2026-11-03/modelisation-v5')
parser.add_argument('--view',choices=['ensemble','console','instruments','pilote','arriere','capteur','structure'])
parser.add_argument('--samples',type=int,default=48)
parser.add_argument('--glb',action='store_true',help='Review the reimported delivery rather than the editable source.')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.out=args.out.resolve()
args.out.mkdir(parents=True,exist_ok=True)
if args.glb:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(root/'navigateur-cockpit.glb'))
else:bpy.ops.wm.open_mainfile(filepath=str(root/'vaisseau_travail.blend'))
for obj in bpy.context.scene.objects:
    if 'smooth exterior' in obj.name:obj.hide_render=True
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.5
world=bpy.data.worlds.new('Neutral review studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.035,.045,.07,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25;scene.world=world

def area(name,location,target,energy,size,color=(1,1,1),size_y=None):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.color=color
    data.shape='RECTANGLE';data.size=size;data.size_y=size_y or size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=location;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

area('Large soft key',(1,-3,6),(0,0,0),850,2.5)
area('Blue side strip',(-3,-1,2),(0,0,.5),400,1.8,(.4,.56,1),.22)
area('Warm return',(3,1,1),(0,0,.5),220,1.5,(1,.72,.43),.25)
area('Forward card',(0,-5,1),(0,1,.6),350,3, size_y=1.5)
area('Instrument reading light',(0,-1,2.5),(-.8,-.8,0),65,.8,(.7,.82,1),.18)

for i,position in enumerate([(-1.3281282,.6395928,1.1799152),(1.3281267,.6395921,1.1799138),(0,1.2511272,1.6602174)]):
    data=bpy.data.lights.new(f'Fixture {i}','POINT');data.energy=12;data.color=(.2,.4,1);data.shadow_soft_size=.10
    obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=position

data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
data.clip_start=.02;data.clip_end=100
views=[('ensemble',(6,-7,4),(0,.1,.15),48),
       ('console',(-1.7,-2.35,.85),(-.6,-.8,-.05),48),
       ('instruments',(-1.20,-.93,.70),(-.82,-.65,.075),52),
       ('pilote',(0,-.65,.70),(-.76,-1.22,.16),28),
       ('arriere',(0,-.9,1.5),(0,2.5,.55),28),
       ('capteur',(-.1,-1.2,1.25),(-1.05,-2.2,.95),62),
       ('structure',(6,-7,4),(0,.1,.15),48)]
for name,position,target,lens in views:
    if args.view and args.view!=name:continue
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=lens
    data.dof.use_dof=name in ['instruments','capteur'];data.dof.aperture_fstop=11
    data.dof.focus_distance=(Vector(target)-camera.location).length
    if name=='structure':
        clay=bpy.data.materials.new('Neutral geometry check');clay.use_nodes=True
        p=clay.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.42,.46,.52,1);p.inputs['Roughness'].default_value=.65
        scene.view_layers[0].material_override=clay
    scene.render.filepath=str(args.out/(name+'.png'));bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=None
print('Offline cabin review complete:',args.out)
