"""Functional native-engine asset POC. No performance or quality benchmark.

Render paired controls without opening a window or taking focus.
"""
from pathlib import Path
import argparse
import json
import os
import struct
import subprocess
import numpy as np
from PIL import Image
from check_biomes import read_plants

ROOT=Path(__file__).resolve().parents[2]
VIEWS=[('temperate',1.68,34.75,50.75,12,0,0,30,70),
       ('temperate_side',1.68,34.75,50.75,12,80,0,30,70),
       ('temperate_120m',120,34.75,50.75,20,0,0,30,70),
       ('forest',1.68,-7.75,-37.25,12,0,0,-5,-20),
       ('forest_120m',120,-7.75,-37.25,20,0,0,-5,-20),
       ('temperate_wind',1.68,34.75,50.75,12,0,1.5,30,70)]


def check_assets(catalogue):
    report=json.loads((catalogue/'poc-report.json').read_text())
    folder=catalogue/'folimesh_old_oak';raw=(folder/'mesh.bin').read_bytes()
    magic,nv,ni,w,h,materials,*bounds=struct.unpack_from('<8s5I6f',raw)
    assert magic==b'FOLMESH1' and ni==report['triangles']*3 and nv==report['vertices']
    assert len(raw)==52+nv*36+ni*4+w*h*4 and materials==2
    v=np.frombuffer(raw,dtype='<f4',count=nv*9,offset=52).reshape(-1,9)
    indices=np.frombuffer(raw,dtype='<u4',count=ni,offset=52+nv*36)
    assert np.isfinite(v).all() and indices.max()<nv and ni%3==0
    assert np.allclose(np.linalg.norm(v[:,3:6],axis=1),1,atol=1e-5)
    assert set(np.unique(v[:,8]))=={0,1} and report['leaf_mask']==2
    assert v[:,1].min()<0<v[:,1].max(),'Original buried roots and ground pivot required'
    assert (folder/'material.bin').stat().st_size==16+w*h*8
    assert (folder/'lighting.bin').stat().st_size==16+nv*32
    assert (folder/'impostor.bin').read_bytes()[:8]==b'FOLIMP01'
    assert (folder/'impostor_light.bin').read_bytes()[:8]==b'FOLIL001'
    assert np.load(folder/'source_attributes.npz').files,'Preserve source vertex attributes'
    return report


def render(catalogue,out):
    out.mkdir(parents=True,exist_ok=True);jobs=out/'views.txt'
    jobs.write_text('\n'.join(f'{out/name}.bmp natural {height} {lat} {lon} {pitch} {heading} 1 {time} {sunlat} {sunlon}'
                             for name,height,lat,lon,pitch,heading,time,sunlat,sunlon in VIEWS)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update({'MYPLANETENGINE_BATCH':str(jobs),'MYPLANETENGINE_RESOLUTION':'960 540',
                'MYPLANETENGINE_FOLIAGE_ASSETS':str(catalogue),'MYPLANETENGINE_FOLIAGE_WARMUP':'8',
                'MYPLANETENGINE_FOLIAGE_SAMPLES':'1','MYPLANETENGINE_TAA':'0',
                'MYPLANETENGINE_OBJECT_LIST':'1','MYPLANETENGINE_NO_CLOUDS':'1',
                'MYPLANETENGINE_SCANS':str(ROOT.parent/'scans')})
    with (out/'renderer.log').open('w') as log:
        result=subprocess.run([str(ROOT/'x64/Release/MyPlanetEngine.exe')],cwd=ROOT/'x64/Release',env=env,
                              stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=900)
    assert result.returncode==0,(out/'renderer.log').read_text()
    reports={}
    for name,*_ in VIEWS:
        path=out/(name+'.bmp');im=Image.open(path).convert('RGB')
        assert im.size==(960,540) and np.std(np.asarray(im))>2,'Blank native capture'
        im.save(out/(name+'.png'))
        r=json.loads(Path(str(path)+'.planet-foliage.json').read_text())
        assert sum(r['overflow'])==0 and r['queue_bytes']==192*1024*1024,'Foliage queue contract changed'
        reports[name]={'model_names':r['model_names'],'model_counts':r['model_counts'],'overflow':r['overflow']}
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--assets-only',action='store_true');args=parser.parse_args()
    source=check_assets(args.catalogue);result={'asset_checks':'pass','source':source}
    args.out.mkdir(parents=True,exist_ok=True)
    if not args.assets_only:
        control=render(ROOT/'assets/foliage/game_biomes_v1',args.out/'control')
        poc=render(args.catalogue,args.out/'folimesh')
        used=0
        for view in poc.values():
            for slot in source['replaced_model_ids']:
                assert view['model_names'][slot]=='folimesh_old_oak','POC catalogue not loaded'
                used+=view['model_counts'][slot][0]
        assert used>0,'The source model must actually be drawn as a nearby mesh'
        still=read_plants(args.out/'folimesh/temperate.bmp.plantes')
        wind=read_plants(args.out/'folimesh/temperate_wind.bmp.plantes')
        a=np.argsort(still['seed']);b=np.argsort(wind['seed'])
        assert len(a)>0 and len(a)==len(b) and np.array_equal(still['seed'][a],wind['seed'][b]),'Wind changed population identities'
        assert np.max(abs(still['pos'][a]-wind['pos'][b]))<.01,'Wind moved plant feet'
        result.update({'control':control,'folimesh':poc,'near_source_mesh_draws':used,'wind_feet_stable':True})
    (args.out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'assets':'pass','native_views':0 if args.assets_only else len(VIEWS)*2,
                      'near_source_mesh_draws':result.get('near_source_mesh_draws'),'benchmark':False}))


if __name__=='__main__':main()
