"""Recover a bounded CPU geometry candidate from an immutable dense neural GLB.

This diagnostic fallback does not invent PBR maps or mark the asset accepted.
It preserves the dense source and records any missing material stage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector,Matrix


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--triangles',type=int,default=28000)
    p.add_argument('--height',type=float,default=7.7);p.add_argument('--backend',default='pixal3d')
    p.add_argument('--minimum-part-triangles',type=int,default=0,
                   help='Reserve detail for small semantic parts within the same total budget')
    p.add_argument('--voxel-resolution',type=int,choices=[0,256,384,512],default=0,
                   help='Explicit opaque-shell diagnostic; can close or erase thin architectural openings')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
    if a.triangles<1000 or a.height<=0 or a.minimum_part_triangles<0:
        raise ValueError('Positive scale and useful diagnostic budget required')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(a.source));objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    counts=[]
    for obj in objects:obj.data.calc_loop_triangles();counts.append(len(obj.data.loop_triangles))
    total=sum(counts);print('Dense source triangles:',total,flush=True)
    minimums=[min(n,a.minimum_part_triangles) for n in counts]
    if sum(minimums)>a.triangles:raise ValueError('Part reservations exceed the total triangle budget')
    remaining=sum(n-m for n,m in zip(counts,minimums))
    budgets=[m+max(0,a.triangles-sum(minimums))*(n-m)/max(1,remaining)
             for n,m in zip(counts,minimums)]
    repairs=[]
    for obj,count,budget in zip(objects,counts,budgets):
        bpy.context.view_layer.objects.active=obj
        before=len(obj.data.vertices)
        repaired=obj.data.validate(clean_customdata=True)
        # GLB can split coincident vertices at material/normal seams. A face
        # ratio alone cannot reduce disconnected geometric islands correctly.
        weld=obj.modifiers.new('Recover geometric adjacency','WELD');weld.merge_threshold=1e-6
        bpy.ops.object.modifier_apply(modifier=weld.name)
        repairs.append({'object':obj.name,'source_vertices':before,'welded_vertices':len(obj.data.vertices),
                        'source_validation_repaired':repaired,'allocated_triangles':budget})
        print('Recovered adjacency:',repairs[-1],flush=True)
        if a.voxel_resolution:
            extent=max(max(v.co[k] for v in obj.data.vertices)-min(v.co[k] for v in obj.data.vertices) for k in range(3))
            remesh=obj.modifiers.new('Explicit opaque volume reconstruction','REMESH');remesh.mode='VOXEL'
            remesh.voxel_size=extent/a.voxel_resolution;remesh.use_smooth_shade=True
            bpy.ops.object.modifier_apply(modifier=remesh.name)
            obj.data.calc_loop_triangles()
            repairs[-1]['voxel_faces']=len(obj.data.loop_triangles)
            repairs[-1]['voxel_size_source_units']=extent/a.voxel_resolution
            print('Opaque volume reconstruction:',repairs[-1]['voxel_faces'],flush=True)
        obj.data.calc_loop_triangles();current=len(obj.data.loop_triangles)
        mod=obj.modifiers.new('CPU bounded QEM candidate','DECIMATE');mod.ratio=min(1,budget/max(1,current))
        mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        repairs[-1]['reduced_validation_repaired']=obj.data.validate(clean_customdata=True)
        for face in obj.data.polygons:face.use_smooth=True
    points=[obj.matrix_world@v.co for obj in objects for v in obj.data.vertices]
    lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
    origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=a.height/(hi.z-lo.z)
    for obj in objects:
        matrix=obj.matrix_world.copy()
        for v in obj.data.vertices:v.co=(matrix@v.co-origin)*scale
        obj.matrix_world=Matrix.Identity(4)
    actual=0
    for obj in objects:obj.data.calc_loop_triangles();actual+=len(obj.data.loop_triangles)
    target=a.out/'geometry-candidate.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',export_extras=True,export_yup=True)
    sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
    report={'backend':a.backend,'source':str(a.source),'source_sha256':sha(a.source),'source_triangles':total,
        'target_triangles':a.triangles,'actual_triangles':actual,'height_m':a.height,'scale':scale,
        'minimum_part_triangles':a.minimum_part_triangles,
        'output':str(target),'output_sha256':sha(target),'reducer_sha256':sha(__file__),
        'adjacency_weld_source_units':1e-6,'repairs':repairs,'within_triangle_budget':actual<=a.triangles*1.01,
        'method':'Blender CPU QEM, geometry diagnostic','voxel_resolution':a.voxel_resolution,
        'thin_openings_preserved':None if a.voxel_resolution else 'No solid reconstruction; requires visual review',
        'pbr_complete':False,'art_accepted':False,'runtime_accepted':False}
    (a.out/'reduction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CPU candidate triangles:',actual,flush=True)


if __name__=='__main__':main()
