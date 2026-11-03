"""Functional native asset review, without a window or performance claims.

Shared-GPU captures remain useful for image/format checks. Timings from this tool
are never used to accept performance; the separate paired benchmark needs isolation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tools/tests'))
from banc_arbustes_climat import engine_processes
from check_biomes import read_plants
from check_local3d_native import assets

POSES=[('near',1.68,12,0,0),('canopy',30,25,0,0),('relay',120,20,0,0),('far',1300,32,0,0),
       ('near_repeat',1.68,12,0,0),('wind',1.68,12,0,2)]


def fingerprint(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(exe,catalogue,out,forced=None,full=False):
    out.mkdir(parents=True,exist_ok=True)
    poses=POSES if full else POSES[:3]
    report=json.loads((catalogue/'native-report.json').read_text())
    protocol={'executable':fingerprint(exe),'shaders':{p.name:fingerprint(p) for p in exe.parent.glob('*.cso')},
              'catalogue':fingerprint(catalogue/'biomes.txt'),
              'asset':{p.name:fingerprint(p) for p in (catalogue/report['name']).glob('*.bin')},
              'reviewer':fingerprint(Path(__file__)),'forced':forced,'full':full}
    if (out/'complete.json').exists():
        if json.loads((out/'complete.json').read_text()).get('protocol')!=protocol:raise ValueError('Functional inputs changed; use a fresh output directory')
        return
    jobs=out/'views.txt';styles=['natural','plantalbedo','plantlod'] if full else ['plantalbedo','plantlod']
    jobs.write_text('\n'.join(f'{out/(name+"_"+style)}.bmp {style} {height} 34.75 50.75 {pitch} {heading} 2 {weather} 30 70'
                            for name,height,pitch,heading,weather in poses for style in styles)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update(MYPLANETENGINE_BATCH=str(jobs),MYPLANETENGINE_FOLIAGE_ASSETS=str(catalogue),
               MYPLANETENGINE_RESOLUTION='960 540',MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',
               MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'),MYPLANETENGINE_TIME='0 0',MYPLANETENGINE_TAA='1',
               MYPLANETENGINE_NO_CLOUDS='1',MYPLANETENGINE_OBJECT_LIST='1',MYPLANETENGINE_FOLIAGE_WARMUP='8',MYPLANETENGINE_FOLIAGE_SAMPLES='1')
    if forced is not None:env['MYPLANETENGINE_FOLIAGE_TEST_LOD']=str(forced)
    peers=engine_processes()
    print('Functional native captures:',out.name,'forced LOD',forced,'peer engines',len(peers),flush=True)
    with (out/'engine.log').open('w') as log:
        result=subprocess.run([str(exe)],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=900)
    if result.returncode:raise RuntimeError('Native capture failed; see '+str(out/'engine.log'))
    for name,*_ in poses:
        for style in styles:
            file=out/(name+'_'+style+'.bmp');image=Image.open(file).convert('RGB')
            if image.size!=(960,540) or np.std(np.asarray(image))<1:raise ValueError('Blank native capture')
            image.save(file.with_suffix('.png'))
    (out/'complete.json').write_text(json.dumps({'functional_only':True,'timing_usable':False,'forced_lod':forced,'peer_engines_at_start':peers,'protocol':protocol},indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--catalogue',type=Path,required=True)
    parser.add_argument('--exe',type=Path,default=ROOT/'x64/Release/MyPlanetEngine.exe');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);catalogue=args.catalogue.resolve();exe=args.exe.resolve()
    structural=assets(catalogue);source=json.loads((catalogue/'native-report.json').read_text());slots=source['replaced_slots']
    capture(exe,catalogue,out/'automatic',full=True)
    level_count=len(source['lods']['levels'])
    for level in range(level_count):capture(exe,catalogue,out/f'forced{level}',forced=level)
    active=set();counts={}
    for name,*_ in POSES:
        meta=json.loads((out/'automatic'/(name+'_plantlod.bmp.planet-foliage.json')).read_text())
        assert not sum(meta['overflow']) and meta['queue_bytes']==192*1024*1024 and meta['mesh_order_bytes']==12*1024*1024
        assert all(meta['model_names'][slot]==source['name'] for slot in slots)
        levels=np.array(meta['mesh_lod_counts'])[slots].sum(0);active.update(np.flatnonzero(levels).tolist());counts[name]=levels.tolist()
    assert active==set(range(level_count)),'The review route must exercise every geometry level'
    for level in range(level_count):
        for name,*_ in POSES[:3]:
            meta=json.loads((out/f'forced{level}'/(name+'_plantlod.bmp.planet-foliage.json')).read_text())
            draws=np.array(meta['mesh_lod_counts'])[slots].sum(0);expected=sum(meta['model_counts'][slot][0] for slot in slots)
            assert draws[level]==expected and draws.sum()==expected,'Forced native level does not match its logical population'
    # Stationary classification is independent of dispatch order and capture history.
    assert counts['near']==counts['near_repeat'],'Stationary LOD selection changed'
    base=read_plants(out/'automatic/near_plantalbedo.bmp.plantes');wind=read_plants(out/'automatic/wind_plantalbedo.bmp.plantes')
    a=np.argsort(base['seed']);b=np.argsort(wind['seed'])
    assert len(a)==len(b) and np.array_equal(base['seed'][a],wind['seed'][b])
    assert np.max(np.abs(base['pos'][a]-wind['pos'][b]))<.01,'Wind moved plant identities or feet'
    near=np.asarray(Image.open(out/'automatic/near_plantalbedo.png')).astype(int);moving=np.asarray(Image.open(out/'automatic/wind_plantalbedo.png')).astype(int)
    motion=float((np.max(np.abs(near-moving),axis=2)>2).mean())
    assert motion>0,'Wind pose did not change the rendered foliage'
    metrics={}
    for level in range(1,5):
        metrics[str(level)]={}
        for name,*_ in POSES[:3]:
            reference=np.asarray(Image.open(out/f'forced0/{name}_plantalbedo.png')).astype(float)/255
            image=np.asarray(Image.open(out/f'forced{level}/{name}_plantalbedo.png')).astype(float)/255
            metrics[str(level)][name]={'mean_rgb_difference':float(np.abs(reference-image).mean()),'p95_rgb_difference':float(np.percentile(np.abs(reference-image).max(2),95))}
    report={'status':'functional checks pass; visual acceptance requires image review','assets':structural,'automatic_lod_counts':counts,
            'stable_stationary_selection':True,'wind_feet_stable':True,'wind_changed_pixel_share':motion,'forced_lod_image_differences':metrics,
            'performance_validated':False,'timing_note':'Functional captures may share the GPU; no performance conclusion is drawn from them',
            'views':str(out)}
    (out/'native-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
