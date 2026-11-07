"""Hidden functional checks of the extended biome bank. No timing acceptance."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,default=Path('E:/ExoluneAssets/biome-library/native-bank-review'))
parser.add_argument('--bank',type=Path,default=Path('E:/ExoluneAssets/biome-library/review-bank.json'))
args=parser.parse_args();OUT=args.out
if OUT.exists() and any(OUT.iterdir()):raise ValueError('Use a fresh native review directory')
bank=json.loads(args.bank.read_text());catalogue=Path(bank['catalogue'])
records=[line.split() for line in (catalogue/'biomes.txt').read_text().splitlines()[1:]]
poses=[('temperate',34.75,50.75,30,70),('tropical',-7.75,-37.25,-5,-20),('boreal',42.002542495,65.003025314,35,80),
       ('dry',41.75,-22.25,35,-5),('desert',-11.825,110.867,-5,100),('montane',-47.207948,75.090399,-40,70)]
OUT.mkdir(parents=True,exist_ok=True);jobs=OUT/'views.txt'
jobs.write_text('\n'.join(f'{OUT/name}.bmp natural 1.68 {lat} {lon} 12 0 2 0 {sun_lat} {sun_lon}' for name,lat,lon,sun_lat,sun_lon in poses)+'\n')
env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
env.update(MYPLANETENGINE_BATCH=str(jobs),MYPLANETENGINE_FOLIAGE_ASSETS=str(catalogue),MYPLANETENGINE_RESOLUTION='640 360',
           MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',MYPLANETENGINE_NO_CLOUDS='1',MYPLANETENGINE_TAA='0',
           MYPLANETENGINE_TIME='0 0',MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'),MYPLANETENGINE_FOLIAGE_WARMUP='8',MYPLANETENGINE_FOLIAGE_SAMPLES='1')
with (OUT/'engine.log').open('w') as log:
    subprocess.run([str(ROOT/'x64/Release/MyPlanetEngine.exe')],cwd=ROOT/'x64/Release',env=env,stdout=log,stderr=subprocess.STDOUT,
                   check=True,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
report={}
legacy_trees=[0,1,14,15,16,17,18,19]
for name,*_ in poses:
    m=json.loads((OUT/(name+'.bmp.planet-foliage.json')).read_text());counts=np.array(m['model_counts'])
    assert len(m['model_names'])==91 and counts.shape==(91,2) and not sum(m['overflow'])
    assert counts[legacy_trees].sum()==0,'A tree bypassed the biome bank'
    assert m['queue_bytes']==192*1024**2 and m['mesh_order_bytes']==12*1024**2
    for species in range(3):
        group=[i for i,row in enumerate(records) if int(row[1])==species]
        assert counts[group].sum(0).tolist()==m['counts'][species*2:species*2+2]
    image=Image.open(OUT/(name+'.bmp'));assert image.size==(640,360) and np.asarray(image).std()>1
    image.save(OUT/(name+'.png'))
    report[name]={'tree_banks':[int(counts[31+10*f:36+10*f].sum()) for f in range(6)],
                  'shrub_banks':[int(counts[36+10*f:41+10*f].sum()) for f in range(6)],'overflow':m['overflow']}
assert report['temperate']['tree_banks'][4]>0,'Temperate tree pool was not exercised'
assert report['tropical']['tree_banks'][5]>0,'Tropical tree pool was not exercised'
result={'status':'pass','scope':'Extended bank dispatch with explicit temporary baseline fallbacks; no generated-model or performance acceptance is implied',
        'generated_candidates':bank['generated_candidates'],'views':report}
(OUT/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
