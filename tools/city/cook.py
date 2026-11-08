"""Reimport generated masters, reduce separate parts and pack a shared native library.

Blender CLI stage. This architectural branch retains the production contract of
immutable GLBs, source fingerprints, bounded LODs and independent native review.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import convex_hull_2d

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from author import MATERIALS
from surface_contacts import preserve as preserve_contacts
MATERIAL_MAP = None


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(obj,repair_reduced_normals=False):
    mesh=obj.data;mesh.calc_loop_triangles()
    positions=np.empty((len(mesh.vertices),3),dtype='f4');mesh.vertices.foreach_get('co',positions.ravel())
    normals=np.empty((len(mesh.loops),3),dtype='f4');mesh.corner_normals.foreach_get('vector',normals.ravel())
    vertices=np.empty(len(mesh.loops),dtype='i4');mesh.loops.foreach_get('vertex_index',vertices)
    loops=np.empty((len(mesh.loop_triangles),3),dtype='i4');mesh.loop_triangles.foreach_get('loops',loops.ravel())
    materials=np.empty(len(mesh.loop_triangles),dtype='i4');mesh.loop_triangles.foreach_get('material_index',materials)
    mapping=[]
    for material in mesh.materials:
        name=material.name
        if MATERIAL_MAP is not None:
            if name not in MATERIAL_MAP and name.rsplit('.',1)[-1].isdigit():name=name.rsplit('.',1)[0]
            mapping.append(MATERIAL_MAP[name])
        else:mapping.append(next(i for i,m in enumerate(MATERIALS) if m[0]==name.split('.')[0]))
    if mesh.uv_layers.active:
        uv=np.empty((len(mesh.loops),2),dtype='f4');mesh.uv_layers.active.data.foreach_get('uv',uv.ravel())
    else:uv=positions[vertices][:,[0,2]]*.5
    matrix=np.array(obj.matrix_world);normal_matrix=np.linalg.inv(matrix[:3,:3]).T
    p=positions[vertices[loops.ravel()]]@matrix[:3,:3].T+matrix[:3,3]
    n=normals[loops.ravel()]@normal_matrix.T;n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    if repair_reduced_normals:
        invalid=(~np.isfinite(n).all(axis=1))|(np.linalg.norm(n,axis=1)<.5)
        if invalid.any():
            triangles=p.reshape(-1,3,3)
            face=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
            face/=np.maximum(np.linalg.norm(face,axis=1,keepdims=True),1e-12)
            n[invalid]=np.repeat(face,3,axis=0)[invalid]
    result=np.empty((len(p),9),dtype='<f4');result[:,:3]=p;result[:,3:6]=n;result[:,6:8]=uv[loops.ravel()]
    # Blender imports glTF's top-left texture coordinates into its bottom-left
    # UV convention. Native D3D samples the original PNG rows, like glTF.
    result[:,7]=1-result[:,7]
    result[:,8]=np.repeat(np.asarray(mapping)[materials],3)
    return result


def reduce_object(obj,ratio,level):
    # Footings, slab interfaces and reveal boundaries stay intact. Whole tiny
    # fittings retire only once subpixel, according to their authored detail tag.
    if level and (int(obj.get('detail',0))>=3 and level>=3 or int(obj.get('detail',0))==2 and level>=4):return None
    dup=obj.copy();dup.data=obj.data.copy();bpy.context.collection.objects.link(dup)
    bpy.context.view_layer.objects.active=dup
    keep=any(word in obj.name for word in ['foundation','plinth','podium','apron','entry_step'])
    if ratio<1 and not keep and len(dup.data.polygons)>24:
        # GLB splits vertices at normal and UV seams. Decimating those islands
        # independently deletes wall panels and ramp strips. Weld positions
        # within this part; UVs and split normals remain corner attributes.
        mod=dup.modifiers.new('Recover geometric adjacency','WELD');mod.merge_threshold=1e-6
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(dup.data)
        closed=not any(edge.is_boundary for edge in bm.edges);bm.free()
        mod=dup.modifiers.new('Bounded source reduction','DECIMATE');mod.ratio=ratio
        mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        if closed:
            bm=bmesh.new();bm.from_mesh(dup.data)
            opened=any(edge.is_boundary for edge in bm.edges) or not len(bm.faces);bm.free()
            if opened:
                bpy.data.objects.remove(dup,do_unlink=True)
                return extract(obj)
    result=extract(dup,repair_reduced_normals=level>0)
    bpy.data.objects.remove(dup,do_unlink=True)
    return result


def surface_tree(vertices):
    return BVHTree.FromPolygons([Vector(p) for p in vertices[:,:3]],np.arange(len(vertices)).reshape(-1,3).tolist(),all_triangles=True)


def surface_samples(vertices,count=512):
    triangles=vertices[:,:3].reshape(-1,3,3)
    areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
    cdf=np.cumsum(areas)
    indices=np.searchsorted(cdf,np.linspace(0,cdf[-1],count,endpoint=False)+cdf[-1]/(2*count))
    return triangles[indices].mean(1)


def ambient_visibility(vertices,tree,cache):
    """Short-range cosine-weighted visibility of the immutable master.

    Only indirect light uses this value. Reusing the source BVH at every LOD
    avoids baking a new dark silhouette each time geometry changes.
    """
    quantized=np.round(vertices[:,:6]*10)/10
    unique,first,inverse=np.unique(quantized,axis=0,return_index=True,return_inverse=True)
    values=np.ones(len(unique),dtype='f4')
    for i,row in enumerate(unique):
        key=tuple(row)
        if key not in cache:
            actual=vertices[first[i]]
            point=Vector(actual[:3]);normal=Vector(actual[3:6]).normalized()
            axis=Vector((0,0,1)) if abs(normal.z)<.9 else Vector((1,0,0))
            tangent=normal.cross(axis).normalized();bitangent=normal.cross(tangent)
            visibility=0.
            for j in range(8):
                radius=((j+.5)/8)**.5;angle=j*2.399963229728653
                direction=tangent*(radius*np.cos(angle))+bitangent*(radius*np.sin(angle))+normal*((1-radius*radius)**.5)
                hit=tree.ray_cast(point+normal*.018,direction,2.5)
                visibility+=1 if hit[0] is None else min(1,(hit[3]/2.5)**.55)
            cache[key]=visibility/8
        values[i]=cache[key]
    return values[inverse]


def audit(source,low,scale,source_tree,source_samples,level):
    if not len(low) or not np.isfinite(low).all():raise ValueError('Empty or non-finite architecture')
    faces=np.arange(len(low),dtype=np.int32).reshape(-1,3)
    cross=np.cross(low[faces[:,1],:3]-low[faces[:,0],:3],low[faces[:,2],:3]-low[faces[:,0],:3])
    degenerate=np.linalg.norm(cross,axis=1)<1e-8
    # Authored glass closes to the footing at its two ends. Remove zero-area
    # end triangles before the payload, never an elongated valid wall triangle.
    clean=low[faces[~degenerate].reshape(-1)]
    if not len(clean):raise ValueError('All faces degenerate')
    n=np.linalg.norm(clean[:,3:6],axis=1)
    if np.max(np.abs(n-1))>1e-3:raise ValueError('Invalid normals on nondegenerate surfaces')
    tree=surface_tree(clean)
    distances=[source_tree.find_nearest(Vector(p))[3] for p in surface_samples(clean)]
    distances.extend(tree.find_nearest(Vector(p))[3] for p in source_samples)
    p95=float(np.percentile(distances,95));maximum=max(distances)
    # This sampled bidirectional check protects visible shells, not just their
    # bounding box. Visual review still checks openings, rails and backsides.
    limit=max(.015,scale*[.001,.003,.008,.025,.065][level])
    if p95>limit:raise ValueError(f'LOD{level} surface deviation {p95:.4f} m exceeds {limit:.4f} m')
    return clean,{'triangles':len(clean)//3,'removed_zero_area':int(degenerate.sum()),
                  'sampled_surface_p95_m':p95,'sampled_surface_max_m':maximum,'surface_p95_limit_m':limit,
                  'bounds_error_m':float(np.max(np.abs(np.r_[clean[:,:3].min(0)-source[:,:3].min(0),clean[:,:3].max(0)-source[:,:3].max(0)])))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    recipe=json.loads(args.recipe.read_text(encoding='utf8'));args.out.mkdir(parents=True,exist_ok=True)
    materials=json.loads((args.out/'materials.json').read_text()) if (args.out/'materials.json').exists() else None
    overrides=json.loads((args.out/'overrides.json').read_text()) if (args.out/'overrides.json').exists() else {}
    all_vertices=[];all_indices=[];models=[];vertex_first=index_first=0
    cache_dir=args.out/'cook-cache';cache_dir.mkdir(exist_ok=True)
    global MATERIAL_MAP
    for entry in recipe['assets']:
        source=Path(overrides.get(entry['id'],args.sources/entry['id']/'master.glb'))
        if not source.exists():raise ValueError('Missing generated master '+str(source))
        metadata=json.loads((source.parent/'source.json').read_text(encoding='utf8'))
        contacts=metadata.get('surface_contacts',[])
        signature=hashlib.sha256(json.dumps({'source':sha(source),'recipe':entry,'ratios':recipe['lod_ratios'],
            'materials':materials['mapping'][entry['id']] if materials else None,'cooker':sha(__file__),
            'contact_tool':sha(HERE/'surface_contacts.py'),'surface_contacts':contacts},sort_keys=True).encode()).hexdigest()
        cache=cache_dir/(entry['id']+'.npz');meta=cache.with_suffix('.json')
        saved=json.loads(meta.read_text()) if meta.exists() else {}
        if cache.exists() and saved.get('signature')==signature and saved.get('sha256')==sha(cache):
            data=np.load(cache,allow_pickle=False);v=data['vertices'];ix=data['indices'];model=saved['model']
            for lod in model['levels']:lod['first_index']+=index_first
            all_vertices.append(v);all_indices.append(ix+vertex_first);vertex_first+=len(v);index_first+=len(ix);models.append(model)
            print('CACHED',entry['id'],flush=True);continue
        start_part=len(all_vertices);base_vertex=vertex_first;base_index=index_first
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        for data in [bpy.data.meshes,bpy.data.materials]:
            for item in list(data):
                if item.users==0:data.remove(item)
        bpy.ops.import_scene.gltf(filepath=str(source))
        MATERIAL_MAP=materials['mapping'][entry['id']] if materials else None
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
        raw=np.concatenate([extract(o) for o in objects]);lo=raw[:,:3].min(0);hi=raw[:,:3].max(0)
        tree=surface_tree(raw);samples=surface_samples(raw)
        points=[Vector((x,y)) for x,y in np.unique(raw[:,:2],axis=0)]
        outline=[list(points[i]) for i in convex_hull_2d(points)]
        model={'id':entry['id'],'kind':entry['kind'],'floors':entry.get('floors',1),
               'footprint_outline':outline,'bounds_z_up':[lo.tolist(),hi.tolist()],'source_sha256':sha(source),'levels':[]}
        model['fittings']=metadata.get('fittings',{})
        entries=model['fittings'].get('primary_entries',[])
        if entries:model['entrance_z_up']=entries[0]
        previous=None;previous_interfaces=[];ao_cache={}
        for level,ratio in enumerate(recipe['lod_ratios']):
            parts=[reduce_object(o,ratio,level) for o in objects]
            try:
                interfaces=preserve_contacts(objects,parts,contacts,level,float(max(hi-lo)))
                rawlow=np.concatenate([p for p in parts if p is not None and len(p)])
                low,metrics=audit(raw,rawlow,float(np.linalg.norm(hi-lo)),tree,samples,level)
                if interfaces:metrics['surface_contacts']=interfaces
            except ValueError as error:
                if previous is None:raise
                low,metrics=audit(raw,previous,float(np.linalg.norm(hi-lo)),tree,samples,level)
                metrics['fallback']=str(error)+'; retained preceding accepted geometry'
                interfaces=previous_interfaces
                if interfaces:metrics['surface_contacts']=interfaces
            previous=low
            previous_interfaces=interfaces
            # Shared vertices include split normals, material and UV seams.
            visibility=ambient_visibility(low,tree,ao_cache)
            unique,inverse=np.unique(np.column_stack([low,visibility]),axis=0,return_inverse=True)
            indices=inverse.astype('<u4')+vertex_first
            all_vertices.append(unique);all_indices.append(indices)
            model['levels'].append({'first_index':index_first,'indices':len(indices),'vertices':len(unique),
                                   'ambient_visibility_min':float(visibility.min()),**metrics})
            index_first+=len(indices);vertex_first+=len(unique)
        models.append(model)
        cached_vertices=np.concatenate(all_vertices[start_part:]);cached_indices=np.concatenate(all_indices[start_part:])-base_vertex
        np.savez(cache,vertices=cached_vertices,indices=cached_indices)
        cached_model=json.loads(json.dumps(model))
        for lod in cached_model['levels']:lod['first_index']-=base_index
        meta.write_text(json.dumps({'signature':signature,'sha256':sha(cache),'model':cached_model},indent=2)+'\n')
        print('COOKED',entry['id'],[x['triangles'] for x in model['levels']],flush=True)
    vertices=np.concatenate(all_vertices).astype('<f4');indices=np.concatenate(all_indices).astype('<u4')
    with (args.out/'library.bin').open('wb') as stream:
        stream.write(struct.pack('<8s5I',b'CITYLIB1',3,len(models),len(materials['materials']) if materials else len(MATERIALS),len(vertices),len(indices)))
        for model in models:
            stream.write(model['id'].encode().ljust(64,b'\0'))
            stream.write(struct.pack('<6fI',*model['bounds_z_up'][0],*model['bounds_z_up'][1],len(model['levels'])))
            for lod in model['levels']:stream.write(struct.pack('<2I',lod['first_index'],lod['indices']))
        if materials:
            for material in materials['materials']:stream.write(struct.pack('<12f',*material['color'],*material['properties'],*material['texture']))
        else:
            for slot,(_,rgb,rough,metal) in enumerate(MATERIALS):
                stream.write(struct.pack('<12f',*rgb,1,rough,metal,2.5 if slot==6 else 0,float(slot),0,1,0,0))
        stream.write(vertices.tobytes());stream.write(indices.tobytes())
    report={'schema':1,'recipe_sha256':sha(args.recipe),'cooker_sha256':sha(__file__),
            'library_sha256':sha(args.out/'library.bin'),'models':models,
            'vertices':len(vertices),'triangles_all_levels':len(indices)//3,
            'geometry_bytes':vertices.nbytes+indices.nbytes,'art_accepted':False,'performance_accepted':False,
            'vertex_stride_bytes':40,'ambient_visibility':'8 cosine rays; source BVH; 2.5 m; 0.1 m cache; indirect only',
            'geometric_seam_weld_m':1e-6,'closed_part_boundary_guard':True,
            'missing_reduced_corner_normal':'geometric face normal; source normals unchanged',
            'impostors':'pending','runtime_review':'pending'}
    report['material_slots']={m['name']:i for i,m in enumerate(materials['materials'])} if materials else {m[0]:i for i,m in enumerate(MATERIALS)}
    (args.out/'library.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
