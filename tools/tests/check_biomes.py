"""Functional asset and hidden-render checks. No performance or quality benchmark.

The renderer stays hidden and silent. Captures exercise real placement, catalogue dispatch, wind and LOD.
Run from the worktree root: python tools/tests/check_biomes.py [--assets-only]
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
CATALOGUE=ROOT/'assets/foliage/game_biomes_v1'
OUT=ROOT/'x64/VegetationDiversity/game-checks'


def assets():
    records=(CATALOGUE/'biomes.txt').read_text().splitlines()
    assert records[0]=='FOLBIO02 31' and len(records)==32,'Incomplete catalogue'
    seen=set();triangles={}
    for line in records[1:]:
        name,kind,leaf=line.split();folder=CATALOGUE/name
        raw=(folder/'mesh.bin').read_bytes()
        magic,n,indices,w,h,materials,*bounds=struct.unpack('<8s5I6f',raw[:52])
        assert magic==b'FOLMESH1' and indices%3==0 and n>0 and w%materials==0
        assert len(raw)==52+n*36+indices*4+w*h*4
        vertices=np.frombuffer(raw,dtype='<f4',count=n*9,offset=52).reshape(-1,9)
        ids=np.frombuffer(raw,dtype='<u4',count=indices,offset=52+n*36)
        assert np.isfinite(vertices).all() and ids.max()<n
        assert np.all(np.linalg.norm(vertices[:,3:6],axis=1)>.99),'Missing normals'
        assert np.all(np.linalg.norm(vertices[:,3:6],axis=1)<1.01),'Invalid normals'
        assert vertices[:,8].min()>=0 and vertices[:,8].max()<materials
        assert 0<=int(kind)<=2 and 0<int(leaf)<1<<materials
        digest=hashlib.sha256(raw).hexdigest(); assert digest not in seen,'Duplicate model';seen.add(digest)
        assert (folder/'impostor.bin').read_bytes()[:8]==b'FOLIMP01'
        light=(folder/'lighting.bin').read_bytes()
        assert struct.unpack('<8s2I',light[:16])==(b'FOLLIT01',n,8)
        assert (folder/'impostor_light.bin').read_bytes()[:8]==b'FOLIL001'
        roots=np.mod(vertices[:,8],1)>.125
        if int(kind)<2:
            form=(folder/'form.bin').read_bytes()
            magic,base,crest,reach,crown=struct.unpack('<8s4f',form)
            assert magic==b'FOLFORM1' and min(base,crest,reach,crown)>0
            assert roots.sum()>400,'Missing volumetric roots'
            root_vertices=vertices[roots]
            assert root_vertices[:,1].min()<0 and root_vertices[:,1].max()>.03,'Roots must enter the ground and flare upward'
            assert np.linalg.norm(root_vertices[:,[0,2]],axis=1).max()>.7*reach,'Missing root reach'
            assert all(not (int(leaf)&(1<<int(m))) for m in root_vertices[:,8]),'Roots use leaf cutouts'
            assert crown<=max(bounds[3]-bounds[0],bounds[5]-bounds[2])*1.001,'Invalid independent crown width'
        else:
            assert not roots.any() and not (folder/'form.bin').exists(),'Root settings leaked into ground plants'
        triangles[name]=indices//3
    assert max(triangles[n] for n in ['game_fir','fir_open','fir_dense'])<8000
    assert max(triangles[n] for n in ['game_broadleaf','broadleaf_2','broadleaf_3','broadleaf_4','broadleaf_5'])<9000
    assert max(triangles[n] for n in ['grass_tall_a','grass_tall_c','flower_a','flower_d'])<1000
    assert max(triangles[n] for n in ['fern_b','fern_c'])<2500
    return triangles


def read_plants(path):
    raw=path.read_bytes();magic,a,b=struct.unpack('<8s2I',raw[:16]);assert magic==b'FOLPLN01'
    assert len(raw)==16+(a+b)*16
    plants=np.frombuffer(raw,offset=16,dtype=[('seed','<u4'),('pos','<f4',3)])
    return plants


def captures():
    OUT.mkdir(parents=True,exist_ok=True)
    # Heights are clearance above the settled terrain; climate labels are witnesses, not latitude classifications.
    views=[('forest',2,-7.75,-37.25,8,0,-5,-20,0),
           ('temperate',2,34.75,50.75,8,0,30,70,0),
           ('boreal',2,42.002542495,65.003025314,-10,41.4837,35,80,0),
           ('desert',2,-11.825,110.867,8,114,-5,100,0),
           ('steppe',2,41.75,-22.25,8,0,35,-5,0),
           ('snow',2,-47.207948,75.090399,8,-122,-40,70,0),
           ('forest_120m',120,-7.75,-37.25,20,0,-5,-20,0),
           ('temperate_120m',120,34.75,50.75,20,0,30,70,0),
           ('windward',2,-12.375,112.125,8,294,-5,125,0),
           ('temperate_roots',1.68,34.75,50.75,32,0,30,70,0),
           ('boreal_roots',1.68,42.002542495,65.003025314,32,41.4837,35,80,0),
           ('boreal_other_sun',1.68,42.002542495,65.003025314,20,41.4837,50,45,0),
           ('rooted_slope',1.68,-8.44835,118.48865,28,163,-20,130,0),
           ('boreal_120m',120,42.002542495,65.003025314,20,41.4837,35,80,0),
           ('forest_wind',2,-7.75,-37.25,8,0,-5,-20,1.5),
           ('forest_repeat',2,-7.75,-37.25,8,0,-5,-20,0)]
    jobs=OUT/'captures.txt'
    lines=[]
    for name,height,lat,lon,pitch,heading,sunlat,sunlon,time in views:
        lines.append(f'{OUT/name}.bmp natural {height} {lat} {lon} {pitch} {heading} 1 {time} {sunlat} {sunlon}')
    jobs.write_text('\n'.join(lines)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update({'MYPLANETENGINE_BATCH':str(jobs),
                'MYPLANETENGINE_RESOLUTION':'960 540','MYPLANETENGINE_FOLIAGE_WARMUP':'8',
                'MYPLANETENGINE_FOLIAGE_SAMPLES':'1','MYPLANETENGINE_TAA':'0',
                'MYPLANETENGINE_OBJECT_LIST':'1','MYPLANETENGINE_NO_CLOUDS':'1',
                'MYPLANETENGINE_SCANS':str(ROOT.parent/'scans')})
    with (OUT/'renderer.log').open('w') as log:
        proc=subprocess.run([str(ROOT/'x64/Release/MyPlanetEngine.exe')],cwd=ROOT/'x64/Release',env=env,
                            stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=900)
    assert proc.returncode==0,(OUT/'renderer.log').read_text()
    board=Image.new('RGB',(960*2,574*((len(views)+1)//2)),(20,25,28));draw=ImageDraw.Draw(board)
    totals=np.zeros(31,dtype=np.int64);stats={}
    for i,(name,*_) in enumerate(views):
        photo=OUT/(name+'.bmp');image=Image.open(photo).convert('RGB')
        assert image.size==(960,540) and np.std(np.asarray(image))>2,'Blank capture'
        report=json.loads(Path(str(photo)+'.planet-foliage.json').read_text())
        assert report['diverse_biomes'] and report['art_directed'] and len(report['model_names'])==31,'Default game catalogue not loaded'
        assert sum(report['overflow'])==0,'Renderer queue overflow'
        assert report['queue_bytes']==192*1024*1024,'Per-species queues grew'
        totals+=np.asarray(report['model_counts']).sum(axis=1)
        if name=='boreal':assert sum(v[0] for v in report['model_counts'][14:16])>0,'No new conifer mesh at the cold forest witness'
        if name in ['desert','snow']:assert sum(sum(v) for v in report['model_counts'][23:])==0,'Herbs leaked into unsuitable ground'
        stats[name]={'counts':report['counts'],'new_models':sum(sum(v) for v in report['model_counts'][14:])}
        read_plants(Path(str(photo)+'.plantes'))
        x=(i%2)*960;y=(i//2)*574;board.paste(image,(x,y));draw.text((x+8,y+546),name,fill='white')
    assert totals[14:20].sum()>0,'No additional tree form rendered'
    assert totals[25:29].sum()>0,'No grass/flower ground layer rendered'
    assert totals[29:31].sum()>0,'No fern undergrowth rendered'
    a=read_plants(OUT/'forest.bmp.plantes');b=read_plants(OUT/'forest_repeat.bmp.plantes')
    assert len(a)>0 and len(a)==len(b),'Repeated camera changed the population'
    ia=np.argsort(a['seed']);ib=np.argsort(b['seed'])
    assert np.array_equal(a['seed'][ia],b['seed'][ib]),'Repeated camera changed identities'
    assert np.max(np.abs(a['pos'][ia]-b['pos'][ib]))<.01,'Repeated camera moved plants'
    # Weather animates vertices, never the population's foot or identity.
    w=read_plants(OUT/'forest_wind.bmp.plantes');iw=np.argsort(w['seed'])
    assert np.array_equal(a['seed'][ia],w['seed'][iw]),'Wind changed plant identities'
    assert np.max(np.abs(a['pos'][ia]-w['pos'][iw]))<.01,'Wind moved the plant feet'
    original=np.asarray(Image.open(OUT/'forest.bmp').convert('RGB')).astype(float)[220:500,180:780]
    repeat=np.asarray(Image.open(OUT/'forest_repeat.bmp').convert('RGB')).astype(float)[220:500,180:780]
    moving=np.asarray(Image.open(OUT/'forest_wind.bmp').convert('RGB')).astype(float)[220:500,180:780]
    assert np.mean(abs(original-moving))>1.1*np.mean(abs(original-repeat)),'Wind must move the foreground beyond relay dithering'
    board.save(OUT/'review.jpg',quality=90)
    return {'views':stats,'models_used':np.flatnonzero(totals).tolist(),'stable_repeat_and_wind_feet':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--assets-only',action='store_true');args=parser.parse_args()
    result={'triangles':assets()}
    if not args.assets_only:result.update(captures())
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Biome functional checks pass:',len(result['triangles']),'models;',len(result.get('views',{})),'hidden views.')
