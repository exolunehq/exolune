"""Hidden functional city captures. This tool does not accept or benchmark performance."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geographical(lat,lon,x,y):
    a,b=map(math.radians,[lat,lon]);up=np.array([math.cos(a)*math.cos(b),math.sin(a),math.cos(a)*math.sin(b)])
    east=np.array([-math.sin(b),0,math.cos(b)]);north=np.array([-math.sin(a)*math.cos(b),math.cos(a),-math.sin(a)*math.sin(b)])
    p=up*6378000+east*x+north*y;p/=np.linalg.norm(p)
    return math.degrees(math.asin(p[1])),math.degrees(math.atan2(p[2],p[0]))


def views(layout):
    poses=[('city_aerial',660,-800,550,31,-38),('city_far',0,-2200,680,18,0)]
    for name,label in [('ribbon_crown','dense_crown'),('ribbon_garden_steps','terraced_habitat'),('shell_house','house_front'),
                        ('civic_petals','civic'),('nested_greenhouse','greenhouse'),('asymmetric_hangar','hangar')]:
        match=next((p for p in layout['instances'] if p['id']==name),None)
        if not match:raise ValueError('Required review asset is absent from this layout: '+name)
        x,y,_=match['position'];yaw=match['yaw'];distance=21 if name=='shell_house' else 35 if name.startswith('ribbon_') else 29 if name=='asymmetric_hangar' else 48
        lateral=5 if name=='shell_house' else 0
        camera=(x+math.sin(yaw)*distance+math.cos(yaw)*lateral,y-math.cos(yaw)*distance+math.sin(yaw)*lateral)
        heading=math.degrees(math.atan2(x-camera[0],y-camera[1]))
        pitch=-22 if name=='ribbon_crown' else -12 if name.startswith('ribbon_') else -7
        poses.append((label,*camera,2.0,pitch,heading))
    station=next(p for p in layout['instances'] if p['id']=='interlaced_station')
    x,y,z=station['position'];poses.append(('station',x+43,y-47,5,-12,math.degrees(math.atan2(-43,47))))
    train=next(p for p in layout['instances'] if p['id']=='panoramic_train')
    x,y,z=train['position'];poses.append(('suspended_train',x+17,y-23,z-33-3,-3,math.degrees(math.atan2(-17,23))))
    cx,cy=layout['habitat_centres'][4]
    poses.append(('shared_garden',cx+12,cy-16,1.8,-3,-25))
    line=layout['road_lines'][2];cx,cy=line[5]
    target=layout['road_lines'][2][11]
    poses.append(('path_junction',cx+2,cy-3,1.8,16,math.degrees(math.atan2(target[0]-cx-2,target[1]-cy+3))))
    return poses


def detail_views(layout,library):
    models={m['id']:m for m in library['models']};poses=[]
    from layout import Terrain
    terrain=Terrain(layout['terrain_source'])
    if terrain.digest!=layout['terrain_sha256']:raise ValueError('Capture terrain differs from placement terrain')
    def front(name,label,distance,lateral=0,h=1.7,pitch=0,entry=False):
        item=next((p for p in layout['instances'] if p['id']==name),None)
        if item is None:return
        x,y,z=item['position'];yaw=item['yaw'];model=models[name]
        target=model.get('entrance_z_up',[0,model['bounds_z_up'][0][1],0]) if entry else [0,0,0]
        tx=x+target[0]*math.cos(yaw)-target[1]*math.sin(yaw)
        ty=y+target[0]*math.sin(yaw)+target[1]*math.cos(yaw)
        cx=tx+math.sin(yaw)*distance+math.cos(yaw)*lateral
        cy=ty-math.cos(yaw)*distance+math.sin(yaw)*lateral
        if entry:h+=max(0,z+target[2]-terrain.sample(cx,cy))
        poses.append((label,cx,cy,h,pitch,math.degrees(math.atan2(tx-cx,ty-cy))))
    front('ribbon_crown','collective_entry',5.0,1.6,entry=True)
    front('shell_house','neural_house_entry',8.5,0,1.9,2,entry=True)
    front('civic_petals','civic_entry',6,2,entry=True)
    front('nested_greenhouse','greenhouse_entry',5.5,1.5,entry=True)
    front('interlaced_station','station_entry',6,1.5,entry=True)
    front('ribbon_helix','helix_architecture',32,0,2,-22)
    front('ribbon_lantern','lantern_architecture',34,-5,2,-16)
    front('ribbon_garden_steps','stepped_architecture',38,10,2,-10)
    front('planted_bench','bench_fittings',4.4,2.2,1.6,10)
    front('drinking_fountain','fountain_fittings',2.1,1,1.6,14)
    front('service_cabinet','service_fittings',3,1,1.65,3)
    item=next(p for p in layout['instances'] if p['id']=='panoramic_train')
    x,y,z=item['position'];yaw=item['yaw'];cx=x+math.sin(yaw)*8+math.cos(yaw)*3;cy=y-math.cos(yaw)*8+math.sin(yaw)*3
    poses.append(('train_fittings',cx,cy,z-33-3.0,-7,math.degrees(math.atan2(x-cx,y-cy))))
    return poses


def house_views(layout,library,lods=False):
    """The same functional camera rig on the two independently placed houses."""
    from layout import Terrain
    terrain=Terrain(layout['terrain_source'])
    if terrain.digest!=layout['terrain_sha256']:raise ValueError('Capture terrain differs from placement terrain')
    models={m['id']:m for m in library['models']};poses=[]
    for name,label in [('shell_house','house'),('patio_house','variant')]:
        item=next(p for p in layout['instances'] if p['id']==name)
        x,y,z=item['position'];yaw=item['yaw'];entry=models[name]['entrance_z_up']
        rigs=[('quarter',(10,-17,5),(0,0,3.4)),('street',(2,-20,1.75),(0,0,3.8)),
              ('back',(-12,20,6),(0,0,3.6)),('distant',(0,-400,120),(0,0,3.7)),
              ('entry',(entry[0]+1.5,entry[1]-5.4,entry[2]+1.65),(entry[0],entry[1],entry[2]+1.4)),
              ('underside',(6.0,-7.0,1.75),(4.8,-.5,4.3))]
        if lods:
            lo,hi=models[name]['bounds_z_up'];extent=max(hi[i]-lo[i] for i in range(3))
            radius=math.sqrt(sum((hi[i]-lo[i])**2 for i in range(3)))*.5
            rigs=[]
            for level,pixels in [(1,380),(2,180),(3,75)]:
                distance=extent*720/pixels+radius*.3
                rigs.append(('lod'+str(level),(0,-distance,9.7+distance*.30),(0,0,3.7)))
        for suffix,camera,target in rigs:
            cx=x+camera[0]*math.cos(yaw)-camera[1]*math.sin(yaw)
            cy=y+camera[0]*math.sin(yaw)+camera[1]*math.cos(yaw)
            tx=x+target[0]*math.cos(yaw)-target[1]*math.sin(yaw)
            ty=y+target[0]*math.sin(yaw)+target[1]*math.cos(yaw)
            if suffix=='distant' or lods:
                # Look back from the inner common, keeping even the distant
                # camera within the pinned terrain probe for edge houses.
                length=max(math.hypot(x,y),1);distance=abs(camera[1])
                cx=x-x/length*distance;cy=y-y/length*distance
            height=z+camera[2]-terrain.sample(cx,cy)
            pitch=math.degrees(math.atan2(camera[2]-target[2],math.hypot(cx-tx,cy-ty)))
            heading=math.degrees(math.atan2(tx-cx,ty-cy))
            poses.append((label+'_'+suffix,cx,cy,height,pitch,heading))
    return poses


def series_views(layout,library):
    """Source-sized rigs for every model in the mapped neutral series."""
    from layout import Terrain
    terrain=Terrain(layout['terrain_source'])
    if terrain.digest!=layout['terrain_sha256']:raise ValueError('Capture terrain differs from placement terrain')
    mapping=json.loads((ROOT/'assets/city/series-runtime.json').read_text())['models']
    models={m['id']:m for m in library['models']};poses=[]
    def pose(name,label,entry=False):
        item=next(p for p in layout['instances'] if p['id']==name)
        x,y,z=item['position'];yaw=item['yaw'];model=models[name];lo,hi=model['bounds_z_up']
        w=hi[0]-lo[0];d=hi[1]-lo[1];h=hi[2]-lo[2]
        if entry:
            target=np.array(model['entrance_z_up'])+np.array([0,0,1.4])
            camera=target+np.array([1.2,-5.8,.25])
        else:
            target=np.array([(lo[0]+hi[0])*.5,(lo[1]+hi[1])*.5,lo[2]+h*.44])
            # Lateral ground cameras can land inside the natural canopy beside
            # the cleared approach. Frame the whole source from its front axis
            # at roof height; separate entry views retain standing eye height.
            camera=target+np.array([0,-max(w*1.15,d*1.10),h*.55])
        def world(p):return (x+p[0]*math.cos(yaw)-p[1]*math.sin(yaw),y+p[0]*math.sin(yaw)+p[1]*math.cos(yaw))
        cx,cy=world(camera);tx,ty=world(target)
        height=z+camera[2]-terrain.sample(cx,cy)
        pitch=math.degrees(math.atan2(camera[2]-target[2],math.hypot(cx-tx,cy-ty)))
        poses.append((label,cx,cy,height,pitch,math.degrees(math.atan2(tx-cx,ty-cy))))
    for runtime_id,source_id in mapping.items():pose(runtime_id,source_id)
    pose('shell_house','house_entry',True)
    pose('civic_petals','civic_entry',True)
    poses.extend(views(layout)[:2])
    return poses


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--plants',type=Path)
    p.add_argument('--exe',type=Path,default=ROOT/'x64/Release/MyPlanetEngine.exe');p.add_argument('--size',default='1280 720')
    p.add_argument('--only',help='Comma-separated functional views for a focused iteration')
    p.add_argument('--details',action='store_true',help='Twelve near-field function and architecture views')
    p.add_argument('--houses',action='store_true',help='Paired house/variant source-to-native functional views')
    p.add_argument('--house-lods',action='store_true',help='Six static intermediate-LOD views at 720 pixels high')
    p.add_argument('--series',action='store_true',help='Eight mapped sources, two entries and two city-scale views')
    p.add_argument('--poses',type=Path,help='Pinned library/scene hashes and explicit functional view tuples')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);layout=json.loads((a.bank/'layout.json').read_text())
    lat,lon=layout['anchor'];lines=[];route=[]
    if a.poses:
        poses=json.loads(a.poses.read_text())
        if poses['library']!=sha(a.bank/'library.bin') or poses['scene']!=sha(a.bank/'scene.bin'):
            raise ValueError('Explicit cameras belong to another city bank')
        selected=poses['views']
        (a.out/'poses.json').write_bytes(a.poses.read_bytes())
    elif a.series:selected=series_views(layout,json.loads((a.bank/'library.json').read_text()))
    elif a.house_lods:
        if a.size.split()[-1]!='720':raise ValueError('The intermediate LOD rig is calibrated for 720 pixels high')
        selected=house_views(layout,json.loads((a.bank/'library.json').read_text()),True)
    elif a.houses:selected=house_views(layout,json.loads((a.bank/'library.json').read_text()))
    elif a.details:selected=detail_views(layout,json.loads((a.bank/'library.json').read_text()))
    else:selected=views(layout)
    if a.only:selected=[v for v in selected if v[0] in a.only.split(',')]
    if not selected:raise ValueError('No selected review view')
    for name,x,y,h,pitch,heading in selected:
        la,lo=geographical(lat,lon,x,y)
        lines.append(f'{a.out/name}.bmp natural {h} {la:.10f} {lo:.10f} {pitch} {heading} 2 0 {lat+5} {lon-30}')
        route.append(f'{name} | {34+h:.3f} {la:.10f} {lo:.10f} {pitch} {heading} | {lat+5} {lon-30}')
    jobs=a.out/'views.txt';jobs.write_text('\n'.join(lines)+'\n');(a.out/'route.txt').write_text('\n'.join(route)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update(MYPLANETENGINE_BATCH=str(jobs),MYPLANETENGINE_CITY_ASSETS=str(a.bank),MYPLANETENGINE_RESOLUTION=a.size,
               MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'),
               MYPLANETENGINE_TIME='0 0',MYPLANETENGINE_TAA='1',MYPLANETENGINE_FOLIAGE_WARMUP='64',MYPLANETENGINE_FOLIAGE_SAMPLES='1')
    if a.plants:env['MYPLANETENGINE_FOLIAGE_ASSETS']=str(a.plants)
    protocol={'executable':sha(a.exe),'library':sha(a.bank/'library.bin'),'scene':sha(a.bank/'scene.bin'),
              'shaders':{x.name:sha(x) for x in a.exe.parent.glob('*.cso')},
              'textures':{x.name:sha(x) for x in a.bank.glob('texture*.bin')},'runner':sha(__file__)}
    if a.poses:protocol['poses']=sha(a.poses)
    (a.out/'runner.py').write_bytes(Path(__file__).read_bytes())
    with (a.out/'engine.log').open('w') as log:
        result=subprocess.run([str(a.exe)],cwd=a.exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=600)
    if result.returncode:raise RuntimeError(f'City native capture failed ({result.returncode}); inspect {jobs}.error.txt')
    captures=[];actual_route=[]
    for name,*_ in selected:
        file=a.out/(name+'.bmp');im=Image.open(file).convert('RGB');values=np.asarray(im)
        if values.std()<1:raise ValueError('Blank native capture '+name)
        metadata=json.loads(file.with_suffix('.bmp.city.json').read_text())
        if metadata['visible_representations']==0:raise ValueError('City absent in '+name)
        im.save(file.with_suffix('.png'));captures.append({'name':name,'sha256':sha(file),'stats':metadata})
        title=file.with_suffix('.bmp.txt').read_text(encoding='utf8',errors='replace')
        position=re.search(r'\| position ([\d.\-]+)',title)
        line=next(line for line in route if line.startswith(name+' | '))
        if position:line=re.sub(r'(\| )[-\d.]+',lambda m:m.group(1)+position.group(1),line,count=1)
        actual_route.append(line)
    (a.out/'route.txt').write_text('\n'.join(actual_route)+'\n')
    (a.out/'functional.json').write_text(json.dumps({'functional_only':True,'performance_accepted':False,
        'art_accepted':False,'protocol':protocol,'captures':captures},indent=2)+'\n')


if __name__=='__main__':main()
