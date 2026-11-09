"""Reproduce the directed house reconstruction and its variant through the city chain.

The neural source remains a pinned design guide. This command does not pretend
that the reviewed profile controls were inferred automatically from that mesh.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--base-bank',type=Path,required=True,help='Reviewed full city bank with production.json')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--terrain',type=Path,required=True)
    p.add_argument('--recipe',type=Path,default=ROOT/'assets/city/shell-house-continuous.json')
    p.add_argument('--city-recipe',type=Path,default=ROOT/'assets/city/solarpunk.json')
    p.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    p.add_argument('--review',action='store_true')
    p.add_argument('--plants',type=Path)
    a=p.parse_args();a.out=a.out.resolve();a.base_bank=a.base_bank.resolve()
    if a.out.is_relative_to(ROOT) or a.out==a.base_bank.parent:raise ValueError('Use a separate external output directory')
    if (a.out/'art-review.json').exists():raise ValueError('Retain reviewed evidence; use a fresh output directory')
    a.out.mkdir(parents=True,exist_ok=True)
    def run(command,label):
        print(label,flush=True)
        with (a.out/(label+'.log')).open('w') as log:
            subprocess.run(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    run([a.blender,'--background','--factory-startup','--threads','5','--python-exit-code','1',
         '--python',HERE/'continuous_house.py','--','--recipe',a.recipe,'--out',a.out/'models',
         '--source',a.source,'--reference',a.reference],'finish-sources')
    production=json.loads((a.base_bank/'production.json').read_text())
    overrides={item['id']:item['path'] for item in production['sources']}
    recipe=json.loads(a.recipe.read_text())
    for asset in recipe['assets']:
        if asset['id'] not in overrides:raise ValueError('House slot absent from the pinned city: '+asset['id'])
        overrides[asset['id']]=str(a.out/'models'/asset['id']/'master.glb')
    (a.out/'overrides.json').write_text(json.dumps(overrides,indent=2)+'\n')
    (a.out/'authoring-recipe.json').write_bytes(a.recipe.read_bytes())
    # Every copied entry is revalidated by the common cooker signature.
    if (a.base_bank/'cook-cache').exists():
        shutil.copytree(a.base_bank/'cook-cache',a.out/'bank/cook-cache',dirs_exist_ok=True)
    run([sys.executable,HERE/'produce.py','--recipe',a.city_recipe,'--out',a.out,
         '--terrain',a.terrain,'--overrides',a.out/'overrides.json','--blender',a.blender],'produce-city')
    if a.review:
        run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'tools/lance.ps1','-Build','-NoLaunch'],'build')
        command=[sys.executable,HERE/'review_native.py','--houses','--bank',a.out/'bank','--out',a.out/'native-houses']
        if a.plants:command+=['--plants',a.plants]
        run(command,'review-houses')
    print('Prepared:',a.out/'bank',flush=True)


if __name__=='__main__':main()
