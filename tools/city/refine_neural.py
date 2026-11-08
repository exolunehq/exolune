"""Add metric fittings to an immutable neural house without remeshing its shell."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import author
from details import entrance,audit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(a.source))
    source_objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    # The user-approved house has its side entrance at local x=2.7 m.
    # A front ray locates the existing facade rather than guessing its depth.
    deps=bpy.context.evaluated_depsgraph_get()
    hit,location,normal,index,obj,matrix=bpy.context.scene.ray_cast(deps,Vector((2.7,-25,1.25)),Vector((0,1,0)))
    if not hit:raise ValueError('Neural entrance facade was not found')
    author.materials();recipe=next(r for r in json.loads(a.recipe.read_text(encoding='utf8'))['assets'] if r['id']=='shell_house')
    entrance(SimpleNamespace(**vars(author)),recipe,2.7,float(location.y)-.09,.18,double=False)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in objects:
        o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'source.blend'))
    for o in objects:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(a.out/'master.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True)
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    triangles=0
    for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    report={'id':'shell_house','backend':'ComfyUI master with metric procedural entrance fittings','neural_mesh':True,
        'original':str(a.source),'original_sha256':sha(a.source),'master_sha256':sha(a.out/'master.glb'),
        'refiner_sha256':sha(__file__),'details_sha256':sha(HERE/'details.py'),'author_sha256':sha(HERE/'author.py'),
        'manufacturing_sha256':sha(HERE/'manufacturing.py'),
        'facade_hit':list(location),'triangles':triangles,'fittings':audit(objects),'art_accepted':False,'performance_accepted':False}
    (a.out/'source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('REFINED',triangles,list(location),flush=True)


if __name__=='__main__':main()
