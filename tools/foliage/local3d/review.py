"""CPU review of the exported GLB, including a wind-data witness. Run with Blender."""
from pathlib import Path
import argparse
import json
import math
import sys
import bpy
import numpy as np
from mathutils import Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('asset',type=Path)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.asset))
plants=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.transparent_max_bounces=64;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-0.4
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.02));floor=bpy.context.object
material=bpy.data.materials.new('Review floor');material.diffuse_color=(.14,.14,.14,1);floor.data.materials.append(material)
for name,loc,power,size in [('Key',(-5,-7,11),1800,6),('Fill',(5,-2,7),650,5),('Rim',(2,6,10),1600,5)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=loc;light.rotation_euler=(Vector((0,0,4))-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(camera);scene.camera=camera

def render(name,position,target,ortho=None):
    data.type='ORTHO' if ortho else 'PERSP';data.ortho_scale=ortho or 11;data.lens=30
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(args.out/(name+'.png'));bpy.ops.render.render(write_still=True)

render('quarter',(16,-16,7.3),(0,0,4.3),11)
render('back',(-16,16,7.3),(0,0,4.3),11)
render('walking',(0,-6.2,1.7),(0,0,4.0))
render('roots',(3.6,-4,1.7),(0,0,.7))

def values(mesh,name,width=1):
    array=np.empty(len(mesh.vertices)*width,dtype=np.float32)
    mesh.attributes[name].data.foreach_get('vector' if width==3 else 'value',array)
    return array.reshape(-1,width)

def rotate(points,pivot,axis,angle):
    v=points-pivot;cos=np.cos(angle);sin=np.sin(angle)
    return pivot+v*cos+np.cross(axis,v)*sin+axis*np.sum(v*axis,axis=1,keepdims=True)*(1-cos)

metrics=[]
for obj in plants:
    mesh=obj.data
    if '_WIND_WEIGHT' not in mesh.attributes:continue
    points=np.array([v.co[:] for v in mesh.vertices],dtype=np.float32)
    # Custom glTF vectors stay Y-up on Blender import; positions become Z-up.
    def pivot(name):
        data=values(mesh,name,3);return data[:,[0,2,1]]*np.array([1,-1,1],dtype=np.float32)
    wp=pivot('_WIND_PIVOT');lp=pivot('_LEAF_PIVOT');w=values(mesh,'_WIND_WEIGHT');lw=values(mesh,'_LEAF_WEIGHT');phase=values(mesh,'_WIND_PHASE')
    axis=np.array([[0,1,0]],dtype=np.float32);time=0.75
    flutter=rotate(points,lp,axis,0.15*np.sin(time*3+phase)*lw)
    moved=rotate(flutter,wp,axis,0.13*np.sin(time*1.2+phase)*w)
    fixed=(w[:,0]==0)&(lw[:,0]==0)
    displacement=np.linalg.norm(moved-points,axis=1)
    error=float(displacement[fixed].max())
    if error>1e-6:raise ValueError('Wind moved a fixed shoot attachment')
    for vertex,position in zip(mesh.vertices,moved):vertex.co=position
    mesh.update()
    metrics.append({'mesh':obj.name,'fixed_vertices':int(fixed.sum()),'fixed_attachment_max_error_m':error,'moving_vertex_max_displacement_m':float(displacement.max()),'wood_motion_m':0.0})
if not metrics:raise ValueError('Exported GLB contains no wind attributes')
render('wind',(16,-16,7.3),(0,0,4.3),11)
(args.out/'wind-check.json').write_text(json.dumps({'source':str(args.asset),'method':'CPU witness using exported pivots and weights; not an engine animation test','results':metrics},indent=2)+'\n')
