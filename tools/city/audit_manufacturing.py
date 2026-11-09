"""CPU topology gate for connected manufactured source parts; not an art gate."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--overrides',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);results=[];failures=[]
    overrides=json.loads(a.overrides.read_text()) if a.overrides else {}
    for item in json.loads(a.recipe.read_text())['assets']:
        source=Path(overrides.get(item['id'],a.sources/item['id']/'master.glb'))
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(source));parts=[]
        for obj in bpy.context.scene.objects:
            construction=obj.get('city_construction')
            if obj.type!='MESH' or not construction:continue
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
            remaining=set(bm.verts);components=0
            while remaining:
                todo=[remaining.pop()];components+=1
                while todo:
                    v=todo.pop()
                    for edge in v.link_edges:
                        other=edge.other_vert(v)
                        if other in remaining:remaining.remove(other);todo.append(other)
            opened=sum(not e.is_manifold for e in bm.edges)
            flipped=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
            collapsed=sum(f.calc_area()<1e-10 for f in bm.faces)
            record={'part':obj.name,'construction':construction,'components':components,
                    'non_manifold_edges':opened,'inconsistent_edges':flipped,'collapsed_faces':collapsed}
            parts.append(record)
            if components!=1 or opened or flipped or collapsed:failures.append(item['id']+': '+obj.name)
            bm.free()
        results.append({'id':item['id'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':parts})
    a.out.write_text(json.dumps({'scope':'Connected authored mouldings only; unrelated parts and neural shells need their own art review',
        'accepted':not failures,'failures':failures,'models':results},indent=2)+'\n')
    print('Connected parts:',sum(len(r['parts']) for r in results),'Failures:',len(failures),flush=True)
    if failures:raise ValueError('; '.join(failures[:12]))


if __name__=='__main__':main()
