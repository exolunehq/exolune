"""Paired offscreen native cost test of a generated-plant catalogue.

Run only on explicit user request. Freeze the executable and runtime assets, keep
the population unchanged, and stop our process if another engine or Comfy job starts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import numpy as np
from PIL import Image
from banc_arbustes_climat import engine_processes

ROOT=Path(__file__).resolve().parents[1]
VIEWS=[('temperate',1.68,34.75,50.75,12,0,30,70),
       ('temperate_side',1.68,34.75,50.75,12,80,30,70),
       ('temperate_canopy',30,34.75,50.75,25,0,30,70),
       ('temperate_120m',120,34.75,50.75,20,0,30,70),
       ('forest',1.68,-7.75,-37.25,12,0,-5,-20),
       ('forest_120m',120,-7.75,-37.25,20,0,-5,-20),
       ('distant',1300,34.75,50.75,32,0,30,70)]
RUNTIME=['mesh.bin','material.bin','lighting.bin','impostor.bin','impostor_light.bin','form.bin','lods.bin']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')


def comfy_busy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8188/queue',timeout=3) as stream:q=json.load(stream)
        return bool(q['queue_running'] or q['queue_pending'])
    except urllib.error.URLError:return False


class GpuBusy(RuntimeError):
    pass


def guarded(command,env,cwd,log,exe,wait=True):
    start=time.monotonic();reported=False
    while engine_processes() or comfy_busy():
        if not wait:raise GpuBusy('Concurrent GPU task: another engine or inference is active')
        if not reported:print('Waiting for an idle GPU; no other process will be closed',flush=True);reported=True
        if time.monotonic()-start>1800:raise TimeoutError('GPU remains busy; no measurement started')
        time.sleep(3)
    with Path(log).open('w') as stream:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            while process.poll() is None:
                engines=engine_processes()
                foreign=[p for p in engines if str(p.get('ExecutablePath','')).lower()!=str(exe).lower()]
                if foreign or len(engines)>1 or comfy_busy():
                    raise GpuBusy('Concurrent GPU task detected; this measurement is invalid and our job is stopping')
                if time.monotonic()-start>7200:raise TimeoutError('Offscreen run timed out')
                time.sleep(2)
            if process.returncode:raise RuntimeError('Renderer failed; see '+str(log))
        except BaseException:
            # Stop only this run and its own children, never another session.
            if process.poll() is None:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
            raise


def freeze_catalogue(source,target,store):
    target.mkdir(parents=True,exist_ok=True);records=(source/'biomes.txt').read_text()
    files={}
    for name in sorted({line.split()[0] for line in records.splitlines()[1:]}):
        folder=target/name;folder.mkdir(exist_ok=True)
        for filename in RUNTIME:
            original=source/name/filename
            if not original.exists():continue
            digest=sha(original);dest=folder/filename
            if not dest.exists():
                if digest in store:
                    try:os.link(store[digest],dest)
                    except OSError:shutil.copyfile(store[digest],dest)
                else:shutil.copyfile(original,dest)
            if sha(dest)!=digest:raise ValueError('Frozen input changed: '+str(dest))
            store[digest]=dest;files[str(dest.relative_to(target))]=digest
    (target/'biomes.txt').write_text(records);files['biomes.txt']=sha(target/'biomes.txt')
    return files


def distribution(values):
    x=np.asarray(values,dtype=float)
    if not x.size or not np.isfinite(x).all() or (x<0).any():raise ValueError('Invalid GPU series')
    return {'median_ms':float(np.median(x)),'p95_ms':float(np.percentile(x,95)),'samples':len(x)}


def quality_delta(reference,current):
    old={(r['material'],r['height']):r for r in reference['tiles']};checks=[]
    for row in current['tiles']:
        prior=old.get((row['material'],row['height']))
        if not prior:continue
        for field in ['gap_p95','repeat_p95']:
            if field not in prior:continue
            a,b=prior[field],row[field]
            checks.append({'metric':field,'material':row['material'],'height':row['height'],'before':a,'after':b,'pass':b<=a*1.1+1e-9})
    for height,row in current.get('mutation',{}).items():
        if height in reference.get('mutation',{}):
            a,b=reference['mutation'][height]['p95'],row['p95']
            checks.append({'metric':'mutation_p95','height':height,'before':a,'after':b,'pass':b<=a*1.1+1e-9})
    missing=sorted(set(old)-{(r['material'],r['height']) for r in current['tiles']})
    missing_mutation=sorted(set(reference.get('mutation',{}))-set(current.get('mutation',{})))
    return {'pass':bool(checks) and not missing and not missing_mutation and all(c['pass'] for c in checks),
            'checks':checks,'missing_material_heights':missing,'missing_mutation_heights':missing_mutation}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=128);parser.add_argument('--warmup',type=int,default=32)
    parser.add_argument('--freeze-only',action='store_true',help='Freeze inputs without submitting a GPU job')
    parser.add_argument('--quality-sites',type=int,default=30)
    parser.add_argument('--quality',action='store_true');parser.add_argument('--opportunistic',action='store_true',help='Checkpoint each view and yield when the GPU is shared');args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=out/'frozen';binary=frozen/'bin';binary.mkdir(parents=True,exist_ok=True)
    executable=ROOT/'x64/Release/MyPlanetEngine.exe';exe=binary/executable.name
    for path in executable.parent.iterdir():
        if path.name==executable.name or path.suffix in ['.cso','.dll'] or (path.suffix=='.bin' and path.name.split('-')[0] in ['climat','tectonique','erosion','meteo','volcans']):
            dest=binary/path.name
            if not dest.exists():shutil.copyfile(path,dest)
            # Terrain maps are mutable engine caches, not executable inputs.
            # Keep this bundle's copy; never replace it from another run.
            elif path.suffix!='.bin' and sha(dest)!=sha(path):raise ValueError('Executable inputs changed; use a new output directory: '+str(path))
    shared_assets={}
    for name in ['clouds','vaisseau','audio']:
        source=ROOT/'assets'/name;target=frozen/'assets'/name
        if not source.is_dir():continue
        for original in source.rglob('*'):
            if not original.is_file():continue
            dest=target/original.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copyfile(original,dest)
            shared_assets[str(dest.relative_to(frozen))]=sha(dest)
    store={};catalogues={'baseline':frozen/'baseline','candidate':frozen/'candidate'}
    fingerprints={}
    for name,source in [('baseline',ROOT/'assets/foliage/game_biomes_v1'),('candidate',args.catalogue)]:
        fingerprints[name]=freeze_catalogue(source,catalogues[name],store)
    freeze_info={'executable':sha(exe),'shaders':{p.name:sha(p) for p in binary.glob('*.cso')},'shared_assets':shared_assets,'catalogues':fingerprints}
    inputs=out/'inputs.json'
    if inputs.exists() and json.loads(inputs.read_text())!=freeze_info:raise ValueError('Frozen inputs changed; use a new output directory')
    save(inputs,freeze_info)
    if args.freeze_only:return
    environment={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    environment.update(MYPLANETENGINE_RESOLUTION='1920 1080',MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',
                       MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'),MYPLANETENGINE_TIME='0 0',
                       MYPLANETENGINE_FOLIAGE_WARMUP=str(args.warmup),MYPLANETENGINE_FOLIAGE_SAMPLES=str(args.samples),
                       MYPLANETENGINE_TAA='1')
    captures={name:[] for name in catalogues}
    def pending(stage,reason):
        save(out/'progress.json',{'status':'pending GPU availability','stage':stage,'reason':reason})
        print('Pending:',stage,reason,flush=True)
    for sequence,name in enumerate(['baseline','candidate','candidate','baseline']):
        folder=out/f'{sequence}_{name}';folder.mkdir(exist_ok=True)
        groups=[[view] for view in VIEWS] if args.opportunistic else [VIEWS]
        for group in groups:
            label=group[0][0] if args.opportunistic else 'all';marker=folder/('complete_'+label+'.json');jobs=folder/('views_'+label+'.txt')
            protocol={'inputs':freeze_info,'samples':args.samples,'warmup':args.warmup,'views':[row[0] for row in group]}
            if marker.exists():
                if json.loads(marker.read_text())!=protocol:raise ValueError('Refusing to reuse a different measurement protocol')
                continue
            if args.opportunistic and (engine_processes() or comfy_busy()):pending(f'{sequence}_{name}/{label}','Another engine or inference is active');return
            jobs.write_text('\n'.join(f'{folder/view}.bmp natural {height} {lat} {lon} {pitch} {heading} 2 0 {slat} {slon}' for view,height,lat,lon,pitch,heading,slat,slon in group)+'\n')
            env=environment|{'MYPLANETENGINE_BATCH':str(jobs),'MYPLANETENGINE_FOLIAGE_ASSETS':str(catalogues[name])}
            print('Measuring '+str(sequence)+' '+name+' '+label,flush=True)
            try:guarded([str(exe)],env,binary,folder/('engine_'+label+'.log'),exe,wait=not args.opportunistic)
            except GpuBusy as error:
                if args.opportunistic:pending(f'{sequence}_{name}/{label}',str(error));return
                raise
            save(marker,protocol)
        captures[name].append(folder)
    result={'protocol':{'resolution':[1920,1080],'order':['baseline','candidate','candidate','baseline'],'warmup':args.warmup,'samples_per_view_per_round':args.samples,'clouds':'enabled','sea':'enabled','time':'0 0','population':'unchanged','scope':'five broadleaf slots use one approved witness; existing native wind'},'views':{}}
    triangles={}
    for name,catalogue in catalogues.items():
        triangles[name]=[]
        for line in (catalogue/'biomes.txt').read_text().splitlines()[1:]:
            header=struct.unpack('<8s5I6f',(catalogue/line.split()[0]/'mesh.bin').read_bytes()[:52]);triangles[name].append(header[2]//3)
    for view,*_ in VIEWS:
        row={};counts={}
        for name,folders in captures.items():
            series=[];reps=[];cadence=[]
            for folder in folders:
                meta=json.loads((folder/(view+'.bmp.planet-foliage.json')).read_text())
                if sum(meta['overflow']):raise ValueError('Native foliage queue overflow')
                if len(meta['gpu_samples_ms'])!=args.samples:raise ValueError('Wrong sample count')
                series+=meta['gpu_samples_ms'];reps=meta['representation_bytes'];counts[name]=meta['model_counts']
                from banc_perf import PASSES
                values=(folder/(view+'.bmp.perf')).read_text().split()
                passes=dict(zip(PASSES,map(float,values[:-1])))
                if int(values[-1])<1:raise ValueError('Missing cadence samples')
                cadence.append(passes['cadence'])
                if not (folder/(view+'.png')).exists():Image.open(folder/(view+'.bmp')).save(folder/(view+'.png'))
            row[name]={'draw':distribution([s[1] for s in series]),'frame':distribution([s[2] for s in series]),
                       'mesh_instances':sum(n[0] for n in counts[name]),'proxy_instances':sum(n[1] for n in counts[name]),
                       'mesh_triangles_submitted':sum(sum(n*t for n,t in zip(levels,sizes)) for levels,sizes in zip(meta['mesh_lod_counts'],meta['mesh_lod_triangles'])) if 'mesh_lod_counts' in meta else sum(n[0]*t for n,t in zip(counts[name],triangles[name])),
                       'mesh_lod_counts':meta.get('mesh_lod_counts'),
                       'cadence_mean_ms_per_round':cadence,'cadence_mean_ms':float(np.mean(cadence)),
                       'representation_bytes':sum(reps),'counts':counts[name]}
        if counts['baseline']!=counts['candidate']:raise ValueError('Asset change altered the classified population')
        row['frame_median_delta_percent']=(row['candidate']['frame']['median_ms']/row['baseline']['frame']['median_ms']-1)*100
        row['draw_median_delta_percent']=(row['candidate']['draw']['median_ms']/row['baseline']['draw']['median_ms']-1)*100
        result['views'][view]=row
        print(view+': '+json.dumps({n:row[n]['frame'] for n in catalogues}),flush=True)
    save(out/'performance.json',result)
    if args.quality and args.opportunistic:
        from quality_local3d import run_quality
        if not run_quality(out,exe,catalogues,environment,args.quality_sites):return
    if args.quality and not args.opportunistic:
        for name,catalogue in catalogues.items():
            folder=out/('quality_'+name);env=environment|{'MYPLANETENGINE_FOLIAGE_ASSETS':str(catalogue),
                  'MYPLANETENGINE_RESOLUTION':'1280 720','MYPLANETENGINE_FOLIAGE_WARMUP':'32','MYPLANETENGINE_FOLIAGE_SAMPLES':'1'}
            command=[sys.executable,'-u',str(ROOT/'tools/banc_qualite.py'),str(exe),str(folder),'--sites',str(args.quality_sites),'--before',str(ROOT/'tools/banc_qualite_reference.json')]
            if name=='candidate':command+=['--from-sites',str(out/'quality_baseline/qualite.json'),'--batch-suns']
            print('Quality guard: '+name,flush=True)
            if not (folder/'qualite.json').exists():guarded(command,env,binary,out/('quality_'+name+'.log'),exe)
        canonical=json.loads((ROOT/'tools/banc_qualite_reference.json').read_text())['summary']
        old=json.loads((out/'quality_baseline/qualite.json').read_text())['summary'];new=json.loads((out/'quality_candidate/qualite.json').read_text())['summary']
        save(out/'quality-guard.json',{'protocol':f'{args.quality_sites} selected sites, 1280x720, canonical metrics; 32 warmup/1 capture sample',
             'baseline_vs_canonical':quality_delta(canonical,old),'candidate_vs_canonical':quality_delta(canonical,new),'candidate_vs_current':quality_delta(old,new)})
    save(out/'progress.json',{'status':'complete','performance':str(out/'performance.json'),'quality':str(out/'quality-guard.json') if args.quality else None})
    print('Completed offscreen comparison: '+str(out),flush=True)


if __name__=='__main__':main()
