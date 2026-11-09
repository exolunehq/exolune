"""Native functional cabin stills. Runs the normal game off screen, without UI automation or benchmarks."""
from pathlib import Path
import math, json, os, subprocess, argparse
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[2]
out=root/'artifacts'/'navigateur-cockpit-son-2026-11-03'/'integration-v6'
views=[
    ('pilote-ocean','cockpit',-20.47,-75.45,30,160,(0,-.65,.7),0,-4.6,'-50.47 -75.45'),
    ('pilote-foret','cockpit',-11.039991,49.783625,80,40,(0,-.65,.7),0,-4.6,'-10 60'),
    ('capteur-max','cabine',-20.47,-75.45,30,160,(0,-.65,.7),35,-1,'-50.47 -75.45'),
    ('paroi-arriere','cabine',-20.47,-75.45,30,160,(0,-.65,.95),180,-10,'-50.47 -75.45'),
    ('pilote-orbite','cockpit',38.1445,103.5352,150000,90,(0,-.65,.7),0,-4.6,'38.1445 128.5352'),
    ('exterieur','exterieur',-20.47,-75.45,30,160,(11,13,6),0,0,'-50.47 -75.45'),
    ('coupe-cabine','cabine',-20.47,-75.45,30,160,(6,-6,4),0,0,'-50.47 -75.45'),
    ('console-detail','cabine',-20.47,-75.45,30,160,(-1.7,-1.9,.3),-134,-19,'-50.47 -75.45'),
    ('puissance-repos','cabine',-20.47,-75.45,30,0,(0,-.65,.7),90,-38,'-50.47 -75.45'),
    ('puissance-vol','cabine',-20.47,-75.45,30,90,(0,-.65,.7),90,-38,'-50.47 -75.45'),
    ('cap-repos','cabine',-20.47,-75.45,30,0,(0,-.65,.7),-90,-38,'-50.47 -75.45'),
    ('cap-vol','cabine',-20.47,-75.45,30,90,(0,-.65,.7),-90,-38,'-50.47 -75.45'),
    ('pilote-nuit','cockpit',38.1445,103.5352,5000,90,(0,-.65,.7),0,-4.6,'-38.1445 -76.4648'),
    ('puissance-nuit','cabine',38.1445,103.5352,5000,90,(0,-.65,.7),90,-38,'-38.1445 -76.4648'),
    ('exterieur-foret','exterieur',-11.039991,49.783625,80,40,(11,13,6),0,0,'-10 60'),
]
def prepare(v):
    name,kind,lat,lon,alt,cap,offset,yaw,pitch,sun=v
    folder=out/name;folder.mkdir(parents=True,exist_ok=True)
    a,b,h=np.radians([lat,lon,cap])
    up=np.array([math.cos(a)*math.cos(b),math.sin(a),math.cos(a)*math.sin(b)])
    north=np.array([-math.sin(a)*math.cos(b),math.cos(a),-math.sin(a)*math.sin(b)])
    east=np.array([-math.sin(b),0,math.cos(b)])
    forward=north*math.cos(h)+east*math.sin(h);left=np.cross(forward,up)
    ship=up*(6378000+alt)
    camera=ship+left*offset[0]-forward*offset[1]+up*offset[2]
    radius=np.linalg.norm(camera);ca=math.asin(camera[1]/radius);cb=math.atan2(camera[2],camera[0])
    cameraCap=cap+yaw
    if kind=='exterieur' or name=='coupe-cabine':
        cn=np.array([-math.sin(ca)*math.cos(cb),math.cos(ca),-math.sin(ca)*math.sin(cb)])
        ce=np.array([-math.sin(cb),0,math.cos(cb)])
        direction=(ship-camera)/np.linalg.norm(ship-camera)
        cameraCap=math.degrees(math.atan2(direction@ce,direction@cn))
        pitch=math.degrees(math.asin(direction@(camera/radius)))
    fov=42 if name=='coupe-cabine' or name.startswith(('puissance-','cap-')) else 50 if name=='console-detail' else 65
    pose=[lat,lon,alt,cap,0,0,math.degrees(ca),math.degrees(cb),radius-6378000,cameraCap,pitch,0,fov,0]
    moving=name.endswith('-vol');first=24 if moving else 0;lines=['fps 60']
    for frame in range(first+1):
        sample=pose.copy()
        # A real 12 m/s translation exercises the normal CINE velocity/throttle path; no shader override.
        advance=math.degrees(frame*.2/6378030) if moving else 0
        sample[0]+=advance;sample[6]+=advance
        lines.append(str(frame)+' '+kind+' '+' '.join(f'{p:.10f}' for p in sample))
    (folder/'pose.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (folder/'expected.json').write_text(json.dumps({'heading_deg':cap,'propulsion_percent':60 if moving else 0,
                                                   'native_cine_frame':first},indent=2),encoding='utf-8')
    return folder,sun,first

parser=argparse.ArgumentParser();parser.add_argument('--view',choices=[v[0] for v in views],nargs='+');parser.add_argument('--prepare-only',action='store_true')
args=parser.parse_args()
for view in views:
    if args.view and view[0] not in args.view:continue
    folder,sun,first=prepare(view)
    if args.prepare_only:continue
    env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update(MYPLANETENGINE_CINE=str(folder/'pose.txt'),MYPLANETENGINE_CINE_OUT=str(folder),
               MYPLANETENGINE_CINE_RANGE=f'{first} 1 24',MYPLANETENGINE_RESOLUTION='1280 720',
               MYPLANETENGINE_MODELE_VAISSEAU='navigateur',MYPLANETENGINE_SUN=sun,
               MYPLANETENGINE_SCANS=str(root.parent/'scans'),MYPLANETENGINE_TAA='1',MYPLANETENGINE_FULLSCREEN='0')
    exe=root/'x64'/'Release'/'MyPlanetEngine.exe'
    with (folder/'engine.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(exe)],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,
                       creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=600)
    image=Image.open(folder/f'frame_{first:05d}.bmp');assert image.size==(1280,720)
    image.save(folder/'apercu.png')
    print(view[0], 'native capture complete',flush=True)
