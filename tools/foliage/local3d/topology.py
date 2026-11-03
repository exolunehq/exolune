"""Blender CPU diagnostic for substantial rejoining woody branches.

Persistent handles after coarse solid remeshing flag a potential branch loop.
This rejects suspect assets; it never silently prunes the generated tree.
"""
from pathlib import Path
import argparse
import json
import sys
import hashlib
import bpy
import bmesh
from mathutils import Vector

p=argparse.ArgumentParser(description=__doc__);p.add_argument('asset',type=Path);p.add_argument('--out',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(a.asset))
wood=next(o for o in bpy.context.scene.objects if o.type=='MESH' and '_LEAF_WEIGHT' not in o.data.attributes)
bpy.context.view_layer.objects.active=wood;wood.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=min(v.co.z for v in wood.data.vertices);h=max(v.co.z for v in wood.data.vertices)-lo
for v in wood.data.vertices:v.co=(v.co-Vector((0,0,lo)))/h
bm=bmesh.new();bm.from_mesh(wood.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
seen=set();source_groups=[]
for vertex in bm.verts:
    if vertex in seen:continue
    group={vertex};seen.add(vertex);pending=[vertex]
    while pending:
        current=pending.pop()
        for edge in current.link_edges:
            other=edge.other_vert(current)
            if other not in seen:seen.add(other);group.add(other);pending.append(other)
    faces={f for v in group for f in v.link_faces};source_groups.append((sum(f.calc_area() for f in faces),group))
largest=max(source_groups,key=lambda item:item[0]);retained=largest[0]/max(sum(item[0] for item in source_groups),1e-12)
if retained<.9:raise ValueError('Generated wood is too fragmented for structural acceptance')
discard=[v for v in bm.verts if v not in largest[1]]
if discard:bmesh.ops.delete(bm,geom=discard,context='VERTS')
cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,.2),plane_no=(0,0,1),clear_inner=True)
boundary=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
clip_bounds=[min(v.co.z for v in bm.verts),max(v.co.z for v in bm.verts)]
bm.to_mesh(wood.data);bm.free();original=wood.data.copy();records=[]
for resolution in [96,128,160]:
    wood.data=original.copy();mod=wood.modifiers.new('Structural solid probe','REMESH');mod.mode='VOXEL';mod.voxel_size=1/resolution
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(wood.data)
    seen=set();components=0;groups=[]
    for v in bm.verts:
        if v in seen:continue
        components+=1;pending=[v];seen.add(v);group={v}
        while pending:
            current=pending.pop()
            for edge in current.link_edges:
                other=edge.other_vert(current)
                if other not in seen:seen.add(other);group.add(other);pending.append(other)
        faces={f for vertex in group for f in vertex.link_faces};edges={e for vertex in group for e in vertex.link_edges}
        area=sum(f.calc_area() for f in faces);closed=all(len(e.link_faces)==2 for e in edges)
        genus=max(0,round(1-(len(group)-len(edges)+len(faces))/2)) if closed else None
        groups.append({'vertices':len(group),'area':area,'handles':genus})
    nonmanifold=sum(len(e.link_faces)!=2 for e in bm.edges)
    euler=len(bm.verts)-len(bm.edges)+len(bm.faces)
    largest=max((g['area'] for g in groups),default=0)
    relevant=[g for g in groups if g['area']>=largest*.01]
    handles=sum(g['handles'] or 0 for g in relevant) if all(g['handles'] is not None for g in relevant) else None
    records.append({'resolution':resolution,'components':components,'nonmanifold_edges':nonmanifold,'handles':handles,
                    'substantial_components':relevant,'all_component_handles':max(0,round(components-euler/2)) if not nonmanifold else None})
    bm.free()
suspect=sum(row['handles'] is not None and row['handles']>0 for row in records)>=2
result={'status':'potential branch cycle' if suspect else 'no persistent coarse handle detected','suspect':suspect,'probes':records,
        'clipped_height_range':clip_bounds,
        'retained_source_area_fraction':retained,
        'auditor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(a.asset.read_bytes()).hexdigest(),
        'scope':'Substantial woody components above the root collar; tiny discarded fragments excluded. Does not prove botanical correctness or detect every visual intersection'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
