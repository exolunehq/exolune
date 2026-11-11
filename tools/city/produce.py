"""Reproducible generated city kit, terrain layout and optional native review.

This command performs no performance or quality benchmark and never marks art
accepted. Large assets and captures belong in an external output directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from materials import prepare

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe',type=Path,default=ROOT/'assets/city/solarpunk.json')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--terrain',type=Path,required=True)
    p.add_argument('--bank',type=Path);p.add_argument('--overrides',type=Path)
    p.add_argument('--seed',type=int,default=11072026);p.add_argument('--review',action='store_true')
    p.add_argument('--assets-only',action='store_true',help='Prepare the immutable kit before terrain placement')
    p.add_argument('--references',type=Path,help='Folder containing the user reference boards; retain hashes only')
    p.add_argument('--plants',type=Path)
    p.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    a=p.parse_args();a.out=a.out.resolve();bank=(a.bank or a.out/'bank').resolve()
    if a.out.is_relative_to(ROOT) or bank.is_relative_to(ROOT):raise ValueError('Keep production binaries outside Git')
    a.out.mkdir(parents=True,exist_ok=True);bank.mkdir(parents=True,exist_ok=True)
    recipe=json.loads(a.recipe.read_text(encoding='utf8'));sources=a.out/'models'
    if a.references:
        refs=[]
        for name in recipe.get('reference_files',[]):
            source=(a.references/name).resolve()
            if not source.is_file():raise FileNotFoundError(source)
            refs.append({'name':name,'path':str(source),'sha256':sha(source)})
        save(a.out/'references.json',{'provenance':'User-supplied art direction; images are not meshes','references':refs})
    overrides=json.loads(a.overrides.read_text(encoding='utf8')) if a.overrides else {}
    if set(overrides)-{item['id'] for item in recipe['assets']}:raise ValueError('Unknown architectural override')
    save(bank/'overrides.json',overrides)
    def run(command,label):
        print(label,flush=True)
        with (a.out/(label+'.log')).open('w') as log:
            subprocess.run(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    def blender(script,*args):return [a.blender,'--background','--factory-startup','--threads','5','--python-exit-code','1','--python',HERE/script,'--',*args]
    inputs=[]
    for entry in recipe['assets']:
        source=Path(overrides.get(entry['id'],sources/entry['id']/'master.glb')).resolve()
        metadata=source.parent/'source.json'
        old=json.loads(metadata.read_text()) if metadata.exists() else {}
        if entry['id'] not in overrides and (old.get('author_sha256')!=sha(HERE/'author.py') or old.get('structure_sha256')!=sha(HERE/'architecture.py') or old.get('details_sha256')!=sha(HERE/'details.py') or old.get('manufacturing_sha256')!=sha(HERE/'manufacturing.py') or old.get('recipe')!=entry or not source.exists() or old.get('master_sha256')!=sha(source)):
            run(blender('author.py','--recipe',a.recipe,'--out',sources,'--asset',entry['id']),'author-'+entry['id'])
            old=json.loads(metadata.read_text())
        if not source.is_file() or not old or old.get('master_sha256')!=sha(source):raise ValueError('Missing generated source provenance: '+str(source))
        inputs.append({'id':entry['id'],'path':str(source),'sha256':sha(source),'metadata_sha256':sha(metadata),'method':old.get('backend'),
                       'neural_geometry':old.get('neural_mesh',False)})
    # Structural source parts have their own topology gate before reduction.
    audit_command=blender('audit_manufacturing.py','--sources',sources,'--recipe',a.recipe,'--out',bank/'manufacturing-validation.json')
    if a.overrides:audit_command+=['--overrides',a.overrides]
    run(audit_command,'manufacturing-audit')
    signature=hashlib.sha256(json.dumps({'sources':inputs,'recipe':recipe,'materials':sha(HERE/'materials.py'),
        'surface_classes':sha(HERE/'surface_classes.py'),
        'cooker':sha(HERE/'cook.py'),'surface_contacts':sha(HERE/'surface_contacts.py')},sort_keys=True).encode()).hexdigest()
    stamp=bank/'cook-state.json';old=json.loads(stamp.read_text()) if stamp.exists() else {}
    expected=['library.bin','library.json','materials.json','texture0.bin','texture1.bin','texture2.bin','atlas0.bin','atlas1.bin','atlas2.bin']
    if old.get('signature')!=signature or any(not (bank/f).is_file() or old.get('files',{}).get(f)!=sha(bank/f) for f in expected):
        prepare(recipe,sources,bank,overrides=overrides)
        run(blender('cook.py','--recipe',a.recipe,'--sources',sources,'--out',bank),'cook')
        save(stamp,{'signature':signature,'files':{f:sha(bank/f) for f in expected}})
    if a.assets_only:return
    run([sys.executable,HERE/'layout.py','--terrain',a.terrain,'--library',bank/'library.json','--out',bank,'--seed',a.seed],'layout')
    run([sys.executable,HERE/'planboard.py','--layout',bank/'layout.json','--out',bank/'plan.png'],'plan')
    run([sys.executable,HERE/'validate.py','--terrain',a.terrain,'--library',bank/'library.json','--recipe',a.recipe,'--out',bank/'validation.json'],'validation')
    if a.review:
        run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'tools/lance.ps1','-Build','-NoLaunch'],'build')
        command=[sys.executable,HERE/'review_native.py','--bank',bank,'--out',a.out/'native-review']
        if a.plants:command+=['--plants',a.plants]
        run(command,'native-review')
    layout=json.loads((bank/'layout.json').read_text());library=json.loads((bank/'library.json').read_text())
    save(bank/'production.json',{'schema':1,'sources':inputs,'recipe':str(a.recipe.resolve()),'recipe_sha256':sha(a.recipe),
        'tools':{script.name:sha(script) for script in HERE.glob('*.py')},
        'terrain_sha256':sha(a.terrain),'library_sha256':sha(bank/'library.bin'),'scene_sha256':sha(bank/'scene.bin'),
        'reference_manifest':str(a.out/'references.json') if (a.out/'references.json').exists() else None,
        'model_count':len(inputs),'instances':len(layout['instances']),'building_instances':len(layout['parcels']),
        'masterplan':layout['masterplan']['pattern'],'district_count':len(layout['districts']),'transport':layout['transport'],
        'triangles_all_levels':library['triangles_all_levels'],'geometry_bytes':library['geometry_bytes'],
        'path_triangles':layout['street_triangles'],'native_vertex_stride_bytes':40,
        'five_geometry_levels':True,'distant_representation':'coarsest mesh; no city impostor or HLOD',
        'functional_cpu':json.loads((bank/'validation.json').read_text()),'native_review':str(a.out/'native-review') if a.review else None,
        'manufacturing_topology':json.loads((bank/'manufacturing-validation.json').read_text()),
        'art_accepted':False,'performance_accepted':False,'planetwide_streaming':False})
    print('Prepared review bank:',bank,flush=True)


if __name__=='__main__':main()
