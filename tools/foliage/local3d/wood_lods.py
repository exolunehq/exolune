"""Reduce wood alone, retaining UVs and sampling source normals/light. Blender CLI."""
from pathlib import Path
import argparse
import json
import os
import sys
import bpy
import bmesh
import numpy as np
from mathutils.kdtree import KDTree
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# The offline dependency is kept on the asset/tool disk, outside the game.
sys.path.insert(0,os.environ.get('EXOLUNE_PYTHON_DEPS','E:/ExoluneTools/python-deps'))
import fast_simplification
if fast_simplification.__version__!='0.2.0':raise ValueError('Install the pinned offline fast-simplification==0.2.0 dependency')

p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path)
p.add_argument('--glb',type=Path,required=True)
p.add_argument('--shrub',action='store_true',help='Keep the sparse woody collar and stems through coarser levels')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out.mkdir(parents=True,exist_ok=True)
data=np.load(args.source);vertices=data['vertices'];indices=data['indices'].reshape(-1,3)
tree=KDTree(len(vertices))
for i,v in enumerate(vertices):tree.insert(v[:3],i)
tree.balance()
targets=[len(indices)]*4+[min(2400,max(24,int(len(indices)*.23))),min(600,max(24,int(len(indices)*.057)))]
if args.shrub:
    targets[4:]=[max(24,int(len(indices)*fraction)) for fraction in [.65,.40]]
section_heights=np.linspace(.10,.45,8)
def sections(points,triangles):
    edges=points[triangles[:,[0,1,1,2,2,0]]].reshape(-1,2,3);result=[]
    for y in section_heights:
        a,b=edges[:,0],edges[:,1]
        hit=((a[:,1]<=y)&(b[:,1]>y))|((b[:,1]<=y)&(a[:,1]>y))
        a,b=a[hit],b[hit]
        if not len(a):result.append([0,0,0,0]);continue
        p=a+(b-a)*((y-a[:,1])/(b[:,1]-a[:,1]))[:,None]
        result.append([*p[:,[0,2]].min(0),*p[:,[0,2]].max(0)])
    return np.asarray(result)
reference_sections=sections(vertices[:,:3],indices)
resolved=np.min(reference_sections[:,2:]-reference_sections[:,:2],axis=1)>.035
def support(mesh):
    mesh.calc_loop_triangles()
    candidate=sections(np.array([v.co[:] for v in mesh.vertices]),np.array([t.vertices[:] for t in mesh.loop_triangles]))
    overlap=np.maximum(0,np.minimum(candidate[:,2:],reference_sections[:,2:])-np.maximum(candidate[:,:2],reference_sections[:,:2]))
    shares=overlap/np.maximum(reference_sections[:,2:]-reference_sections[:,:2],1e-8)
    return float(shares[resolved].min()) if resolved.any() else 1.0
reconstruction=[]
source_bvh=BVHTree.FromPolygons(vertices[:,:3].tolist(),indices.tolist(),all_triangles=True)
root_probes=vertices[(vertices[:,1]>.002)&(vertices[:,1]<.18),:3]
def root_error(mesh):
    mesh.calc_loop_triangles()
    points=np.array([v.co[:] for v in mesh.vertices]);faces=np.array([t.vertices[:] for t in mesh.loop_triangles])
    bvh=BVHTree.FromPolygons(points.tolist(),faces.tolist(),all_triangles=True)
    inward=[bvh.find_nearest(Vector(p))[3] for p in root_probes]
    outward=[source_bvh.find_nearest(Vector(p))[3] for p in points[(points[:,1]>.002)&(points[:,1]<.18)]]
    distances=np.asarray(inward+outward)
    return {'p95':float(np.percentile(distances,95)),'max':float(distances.max())} if len(distances) else {'p95':0.,'max':0.}
for level,target in enumerate(targets,1):
    if level<=4:
        # Neural branch junctions can collapse into a face spanning an empty
        # loop even while root and trunk bounds pass. Keep all nearby wood.
        np.savez_compressed(args.out/f'wood{level}.npz',vertices=vertices,indices=data['indices'].reshape(-1),light=data['light'],extra=data['extra'])
        reconstruction.append({'level':level,'protected_roots':True,'protected_branches':True,'method':'Exact master wood',
            'requested_triangles':target,'actual_triangles':len(indices),'root_error':{'p95':0.,'max':0.},'root_error_limit':0.})
        print('WOOD_LOD',level,len(vertices),len(indices),flush=True);continue
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new('Wood');mesh.from_pydata(vertices[:,:3].tolist(),[],indices.tolist());mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('Wood',mesh);bpy.context.collection.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    # Direct QEM may retain extra faces at low aggressiveness; geometry gates
    # and the final whole-plant budget remain mandatory.
    points=np.array([v.co[:] for v in mesh.vertices]);mesh.calc_loop_triangles()
    faces=np.array([t.vertices[:] for t in mesh.loop_triangles])
    points,faces=fast_simplification.simplify(points,faces,target_count=target,agg=3)
    points=np.clip(points,vertices[:,:3].min(0),vertices[:,:3].max(0))
    mesh=bpy.data.meshes.new('Direct coarse wood');mesh.from_pydata(points.tolist(),[],faces.tolist());mesh.update();obj.data=mesh
    mesh.calc_loop_triangles()
    if level>1 and support(mesh)<.55:raise ValueError('Wood reduction removes the resolved trunk envelope')
    error=root_error(mesh);limit={5:.006,6:.012}[level]
    if error['p95']>limit or error['max']>limit*3:
        raise ValueError(f'LOD {level} exceeds root surface error budget: {error}')
    reconstruction.append({'level':level,'protected_roots':False,'method':'Direct QEM, aggressiveness 3',
                           'requested_triangles':target,'actual_triangles':len(mesh.loop_triangles),'root_error':error,'root_error_limit':limit})
    if level>4:
        # A new UV set removes the source's chart constraints at coarse levels.
        for vertex in mesh.vertices:
            point=vertex.co.copy();vertex.co=(point.x,-point.z,point.y)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
        normals=[]
        for vertex in mesh.vertices:
            native=np.array([vertex.co.x,vertex.co.z,-vertex.co.y]);nearest=tree.find(native)[1];n=vertices[nearest,3:6];normals.append((n[0],-n[2],n[1]))
        for face in mesh.polygons:face.use_smooth=True
        mesh.normals_split_custom_set_from_vertices(normals)
        target_obj=obj
        bpy.ops.object.select_all(action='DESELECT');bpy.ops.import_scene.gltf(filepath=str(args.glb))
        imported=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=target_obj]
        reference=next(o for o in imported if '_LEAF_WEIGHT' not in o.data.attributes)
        for other in imported:
            if other!=reference:bpy.data.objects.remove(other,do_unlink=True)
        bpy.context.view_layer.objects.active=reference;reference.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        origin=data['origin'];height=float(data['height'])
        offset=Vector((float(origin[0]),float(-origin[2]),float(origin[1])))
        for vertex in reference.data.vertices:vertex.co=(vertex.co-offset)/height
        resolution={5:256,6:128}[level]
        material=bpy.data.materials.new('LOD bake target');material.use_nodes=True;target_obj.data.materials.clear();target_obj.data.materials.append(material)
        node=material.node_tree.nodes.new('ShaderNodeTexImage');material.node_tree.nodes.active=node
        scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=4
        scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.025;scene.render.bake.max_ray_distance=.15;scene.render.bake.margin=8
        bpy.ops.object.select_all(action='DESELECT');reference.select_set(True);target_obj.select_set(True);bpy.context.view_layer.objects.active=target_obj
        for label,kind in [('basecolor','EMIT'),('normal','NORMAL'),('roughness','ROUGHNESS')]:
            image=bpy.data.images.new(f'Wood LOD {level} {label}',resolution,resolution,alpha=True)
            image.colorspace_settings.name='sRGB' if label=='basecolor' else 'Non-Color';node.image=image
            restored=[]
            if kind=='EMIT':
                # Transfer base colour itself. A diffuse-lobe bake attenuates
                # it by the generated material's metallic response.
                for source_material in reference.data.materials:
                    nodes=source_material.node_tree.nodes;links=source_material.node_tree.links
                    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
                    output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
                    prior=output.inputs['Surface'].links[0].from_socket
                    emission=nodes.new('ShaderNodeEmission');colour=bsdf.inputs['Base Color']
                    if colour.is_linked:links.new(colour.links[0].from_socket,emission.inputs['Color'])
                    else:emission.inputs['Color'].default_value=colour.default_value
                    links.new(emission.outputs[0],output.inputs['Surface']);restored.append((source_material,output,prior,emission))
            bpy.ops.object.bake(type=kind)
            for source_material,output,prior,emission in restored:
                source_material.node_tree.links.new(prior,output.inputs['Surface']);source_material.node_tree.nodes.remove(emission)
            image.filepath_raw=str(args.out/f'wood{level}_{label}.png');image.file_format='PNG';image.save()
    result=[];source=[]
    for triangle in mesh.loop_triangles:
        for loop_id in triangle.loops:
            loop=mesh.loops[loop_id];point=np.array(mesh.vertices[loop.vertex_index].co[:]);uv=np.array(mesh.uv_layers.active.data[loop_id].uv)
            if level>4:point=point[[0,2,1]]*np.array([1,1,-1]);uv[1]=1-uv[1]
            nearest=tree.find(point)[1]
            result.append([*point,*vertices[nearest,3:6],*uv,vertices[nearest,8]])
            source.append(nearest)
    result=np.asarray(result,dtype='<f4');source=np.asarray(source)
    rounded=np.round(result,7);_,unique,inverse=np.unique(rounded,axis=0,return_index=True,return_inverse=True)
    v=result[unique];light=data['light'][source[unique]];extra=data['extra'][source[unique]].copy()
    np.savez_compressed(args.out/f'wood{level}.npz',vertices=v,indices=inverse.astype('<u4'),light=light,extra=extra)
    print('WOOD_LOD',level,len(v),len(inverse)//3,flush=True)
(args.out/'wood-audit.json').write_text(json.dumps({'resolved_section_heights':section_heights.tolist(),'minimum_source_span':.035,
    'fast_simplification_version':fast_simplification.__version__,'reconstruction':reconstruction},indent=2)+'\n')
