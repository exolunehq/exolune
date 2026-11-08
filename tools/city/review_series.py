"""Reimport exact series GLBs, audit, and render neutral CPU evidence."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import sys
import bpy
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reference_house_master as common


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--views',default='hero,back,entry')
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
    source=json.loads((args.asset_dir/'source.json').read_text());glb=args.asset_dir/'master.glb'
    if common.sha(glb)!=source['master_sha256']:raise ValueError('Source GLB hash mismatch')
    shutil.copy2(args.asset_dir/'source.json',args.out/'source-snapshot.json')
    shutil.copy2(__file__,args.out/'review-script.py')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(glb));objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    transforms={o:o.matrix_world.copy() for o in objects}
    for obj in objects:obj.data.transform(transforms[obj]);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    topology=common.topology(objects)
    failures=[i for i in topology if i['components']!=1 or i['nonmanifold_edges'] or i['zero_faces']]
    triangles=0
    for obj in objects:obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    textures=sum(1 for image in bpy.data.images if image.type=='IMAGE' and image.name!='Render Result')
    validation={'master_sha256':common.sha(glb),'objects':len(objects),'triangles':triangles,'topology':topology,
                'textures':textures,'passed':not failures and triangles==source['triangles'] and len(objects)==source['objects'] and textures==0}
    (args.out/'reimport-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    if not validation['passed']:raise ValueError('Reimport validation failed: '+json.dumps(failures))
    if args.audit_only:return
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=8 if args.preview else 24;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=6
    scene.render.resolution_x=864 if args.preview else 1200;scene.render.resolution_y=576 if args.preview else 800
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.world.use_nodes=True;world=scene.world.node_tree.nodes['Background'];world.inputs[0].default_value=(.6,.6,.6,1);world.inputs[1].default_value=.45
    lo,hi=map(Vector,source['bounds']);center=(lo+hi)*.5;span=max(hi.x-lo.x,hi.y-lo.y);target=Vector((center.x,center.y,hi.z*.42))
    bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-.005));floor=bpy.context.object;floor.name='Review floor only';floor.data.materials.append(common.material('Review neutral ground',.32,.9))
    for name,offset,power,size in [('Key',(-.6,-.8,1),11,.5),('Fill',(.8,-.2,.6),5,.5),('Rim',(.2,.8,1),8,.4)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power*span*span;data.shape='DISK';data.size=size*span
        light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=Vector(offset)*span+target
        light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Exact GLB neutral review');camera=bpy.data.objects.new('Exact GLB neutral review',data);scene.collection.objects.link(camera);scene.camera=camera
    entry=Vector(source['construction']['entries'][0]);entry.z+=1.5
    views={'hero':{'position':list(target+Vector((.85,-1.45,.64))*span),'target':list(target),'lens':48},
           'back':{'position':list(target+Vector((-.95,1.45,.58))*span),'target':list(target),'lens':48},
           'entry':{'position':list(entry+Vector((5,-11,4))),'target':list(entry),'lens':48}}
    for name in args.views.split(','):
        view=views[name];camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();data.type='PERSP';data.lens=view['lens']
        if name!='entry':
            corners=[Vector((x,y,z)) for x in [lo.x,hi.x] for y in [lo.y,hi.y] for z in [lo.z,hi.z]]
            for _ in range(24):
                bpy.context.view_layer.update();projected=[world_to_camera_view(scene,camera,p) for p in corners]
                if all(.035<=p.x<=.965 and .035<=p.y<=.965 and p.z>0 for p in projected):break
                camera.location=Vector(view['target'])+(camera.location-Vector(view['target']))*1.045
            else:raise ValueError('Could not frame the full source bounds')
            view['position']=list(camera.location)
        scene.render.filepath=str(args.out/(name+'.png'));bpy.ops.render.render(write_still=True)
    settings={'source_sha256':common.sha(glb),'renderer':'Cycles CPU','samples':scene.cycles.samples,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'views':views,'render_script_sha256':common.sha(__file__),'neutral':True}
    (args.out/'render-settings.json').write_text(json.dumps(settings,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'neutral-review.blend'))
    print('SERIES_REVIEW',source['id'],'passed',flush=True)


if __name__=='__main__':main()
