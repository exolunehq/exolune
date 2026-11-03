"""Hidden root-volume regression captures. Functional checks, never timings."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/tests'))
from check_biomes import read_plants

POSES=[
    ('reported',1.5,-11.040080,49.783495,12.92,54.34,-10,60,0),
    ('reported_left',1.5,-11.040080,49.783495,12.92,24.34,-10,60,0),
    ('reported_right',1.5,-11.040080,49.783495,12.92,74.34,-10,60,0),
    ('temperate',1.68,34.75,50.75,10,0,30,70,0),
    ('temperate_second',1.68,34.75,50.75,10,80,30,70,0),
    ('tropical',1.68,-7.75,-37.25,10,0,-5,-20,0),
    ('slope',1.68,-8.44835,118.48865,30,163,-20,130,0),
    ('boreal',1.68,42.002542495,65.003025314,-10,41.4837,35,80,0),
    ('desert',1.68,-11.825,110.867,25,114,-5,100,0),
    ('low_sun',1.68,34.75,50.75,10,0,10,80,0),
    ('approach',30,-11.040080,49.783495,20,54.34,-10,60,0),
    ('relay',120,-11.040080,49.783495,20,54.34,-10,60,0),
    ('branch_report',4,-11.039991,49.783625,-7.67,-123.35,-10,60,0),
    ('backlight',4,-11.039991,49.783625,-7.67,-123.35,-20,-15,0),
    ('reported_repeat',1.5,-11.040080,49.783495,12.92,54.34,-10,60,0),
    ('reported_wind',1.5,-11.040080,49.783495,12.92,54.34,-10,60,2)]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(exe,catalogue,out,poses,level,contacts=True):
    out.mkdir();jobs=out/'views.txt'
    jobs.write_text('\n'.join(f'{out/name}.bmp natural {h} {lat} {lon} {pitch} {heading} 2 {time} {slat} {slon}'
        for name,h,lat,lon,pitch,heading,slat,slon,time in poses)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update(MYPLANETENGINE_BATCH=str(jobs),MYPLANETENGINE_FOLIAGE_ASSETS=str(catalogue),
        MYPLANETENGINE_RESOLUTION='960 540',MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',
        MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'),MYPLANETENGINE_TIME='0 0',MYPLANETENGINE_TAA='0',
        MYPLANETENGINE_NO_CLOUDS='1',MYPLANETENGINE_OBJECT_LIST='1',MYPLANETENGINE_PLANT_INSTANCES='1',
        MYPLANETENGINE_FOLIAGE_WARMUP='4',MYPLANETENGINE_FOLIAGE_SAMPLES='1')
    if level is not None:env['MYPLANETENGINE_FOLIAGE_TEST_LOD']=str(level)
    if not contacts:env['MYPLANETENGINE_LOCAL_CONTACTS']='0'
    with (out/'engine.log').open('w') as log:
        subprocess.run([str(exe)],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=900,check=True)
    for name,*_ in poses:
        file=out/f'{name}.bmp';image=Image.open(file).convert('RGB')
        assert image.size==(960,540) and np.std(np.asarray(image))>1,'Blank capture'
        image.save(file.with_suffix('.png'))
        meta=json.loads(Path(str(file)+'.planet-foliage.json').read_text())
        assert sum(meta['overflow'])==0,'Instance queue overflow'
        assert meta['queue_bytes']==192*1024*1024 and meta['mesh_order_bytes']==12*1024*1024
        lighting=json.loads(Path(str(file)+'.local-contacts.json').read_text())
        assert lighting['enabled']==contacts,'The contact-lighting control did not reach the renderer'
    print(out.name,'functional captures complete',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalogue',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--exe',type=Path,default=ROOT/'x64/Release/MyPlanetEngine.exe')
    args=p.parse_args();out=args.out.resolve();catalogue=args.catalogue.resolve();exe=args.exe.resolve()
    out.mkdir(exist_ok=False)
    protocol={'exe':sha(exe),'reviewer':sha(Path(__file__)),'catalogue':sha(catalogue/'biomes.txt'),
        'shaders':{f.name:sha(f) for f in exe.parent.glob('*.cso')},
        'assets':{f.relative_to(catalogue).as_posix():sha(f) for f in catalogue.rglob('*.bin')},
        'functional_only':True,'performance_validated':False}
    (out/'inputs.json').write_text(json.dumps(protocol,indent=2)+'\n')
    capture(exe,catalogue,out/'automatic',POSES,None)
    first_meta=json.loads((out/'automatic/reported.bmp.planet-foliage.json').read_text())
    level_count=int(np.count_nonzero(np.array(first_meta['mesh_lod_triangles'])[first_meta['model_names'].index('oak_spreading')]))
    for level in range(level_count):capture(exe,catalogue,out/f'forced{level}',POSES[:3],level)
    capture(exe,catalogue,out/'contacts_off',[POSES[0]],None,contacts=False)
    lit=np.asarray(Image.open(out/'automatic/reported.png')).astype(int)
    unoccluded=np.asarray(Image.open(out/'contacts_off/reported.png')).astype(int)
    delta=lit-unoccluded
    # A shared max-channel tone curve can raise a weaker display channel when
    # spectral balance changes. The displayed peak stays monotone in radiance.
    peak_increase=int((lit.max(2)-unoccluded.max(2)).max())
    assert peak_increase<=2,'Contact occlusion increased the tone-mapped radiance peak'
    contact_share=float((delta.min(2)<-2).mean());assert contact_share>0,'Contact lighting has no visible effect'
    first=read_plants(out/'automatic/reported.bmp.plantes')
    for name in ['reported_repeat','reported_wind']:
        other=read_plants(out/f'automatic/{name}.bmp.plantes');a=np.argsort(first['seed']);b=np.argsort(other['seed'])
        assert len(a)==len(b) and np.array_equal(first['seed'][a],other['seed'][b])
        assert np.max(np.abs(first['pos'][a]-other['pos'][b]))<.01,'Wind or capture history moved feet'
    before=np.asarray(Image.open(out/'automatic/reported.png')).astype(int)
    moving=np.asarray(Image.open(out/'automatic/reported_wind.png')).astype(int)
    motion=float((np.max(np.abs(before-moving),axis=2)>2).mean());assert motion>0,'Wind produced no visible motion'
    counts={}
    for level in range(level_count):
        path=out/f'forced{level}/reported.bmp';meta=json.loads(Path(str(path)+'.planet-foliage.json').read_text())
        draws=np.array(meta['mesh_lod_counts']);multi=np.array(meta['mesh_lod_triangles'])[:,1:].sum(1)>0;active=draws[multi].sum(0)
        assert active[level]==active.sum() and active[level]>0,'Forced LOD was not drawn'
        counts[str(level)]=active.tolist()
    raw=(out/'automatic/reported.bmp.plant-instances').read_bytes()
    assert raw[:8]==b'FOLPLC01';near,coarse=struct.unpack_from('<2I',raw,8)
    assert len(raw)==96+(near+coarse)*64
    values=np.frombuffer(raw,dtype='<f4',offset=96).reshape(-1,16)
    seeds=np.frombuffer(raw,dtype='<u4',offset=96).reshape(-1,16)[:,15]
    record=int(np.flatnonzero(seeds==3923462319)[0]);model=int(values[record,12]-1)
    meta=json.loads((out/'automatic/reported.bmp.planet-foliage.json').read_text())
    assert meta['model_names'][model]=='oak_spreading','The reported witness changed identity'
    result={'status':'functional checks pass; inspect native images for root appearance','captures':len(POSES)+3*level_count+1,
        'wind_feet_stable':True,'wind_changed_pixel_share':motion,'forced_lod_counts':counts,
        'reported_witness':{'seed':int(seeds[record]),'model':model,'name':meta['model_names'][model]},
        'contact_changed_pixel_share':contact_share,'maximum_contact_peak_increase_bytes':peak_increase,
        'performance_validated':False,'timing_note':'GPU may be shared; no performance acceptance'}
    (out/'root-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
