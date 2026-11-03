"""Hidden functional coverage controls with frozen weather and a fixed camera.

Retain native frames and effective settings. This is not a performance or
canonical quality benchmark. The white sequence is a same-executable control.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pose',default='35 -11.040133 49.783643 -5.04 115.64')
    p.add_argument('--sun',default='-10 60');p.add_argument('--frames',type=int,default=16)
    args=p.parse_args();pose=[str(float(x)) for x in args.pose.split()]
    if len(pose)!=5 or args.frames<8:raise ValueError('A five-number pose and at least eight frozen frames are required')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);exe=ROOT/'x64/Release/MyPlanetEngine.exe'
    sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
    inputs={'exe':sha(exe),'shaders':{f.name:sha(f) for f in exe.parent.glob('*.cso')},
            'catalogue':str(args.catalogue.resolve()),'pose':pose,'sun':args.sun,'frames':args.frames,
            'weather_time':0,'mesh_shift_speed':0,'performance_validated':False}
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    frames={};settings={}
    cases=[('sobol',{}),('white_control',{'MYPLANETENGINE_FOLIAGE_WHITE_NOISE':'1'}),('disabled',{'MYPLANETENGINE_TAA':'0'})]
    for name,extra in cases:
        folder=out/name;folder.mkdir();prefix=folder/'frame'
        env={k:v for k,v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
        env.update(MYPLANETENGINE_FOLIAGE_ASSETS=str(args.catalogue.resolve()),MYPLANETENGINE_TREMBLE=str(prefix),
            MYPLANETENGINE_TREMBLE_SPEED='0',MYPLANETENGINE_TREMBLE_FRAMES=str(args.frames),
            MYPLANETENGINE_RESOLUTION='960 540',MYPLANETENGINE_FULLSCREEN='0',MYPLANETENGINE_VSYNC='0',
            MYPLANETENGINE_TIME='0 0',MYPLANETENGINE_NO_CLOUDS='1',MYPLANETENGINE_SUN=args.sun,
            MYPLANETENGINE_SCANS=str(ROOT.parent/'scans'))
        env.update(extra)
        with (folder/'engine.log').open('w') as log:
            subprocess.run([str(exe),*pose],cwd=exe.parent,env=env,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=True,timeout=900)
        files=sorted(folder.glob('frame_*.bmp'));assert len(files)==args.frames,'Missing native control frames'
        frames[name]=np.stack([np.asarray(Image.open(f).convert('RGB')) for f in files]).astype(np.float32)
        settings[name]=[json.loads(Path(str(f)+'.foliage-filter.json').read_text()) for f in files]
        assert all(s['temporal_aa']==(name!='disabled') for s in settings[name]),'The effective AA setting differs from the requested control'
        assert all(s['coverage_sequence']==('white-control' if name=='white_control' else 'sobol3') for s in settings[name])
        for file in [files[0],files[-1]]:Image.open(file).save(file.with_suffix('.png'))
        print(name,'functional frozen frames complete',flush=True)
    assert np.array_equal(frames['disabled'],np.broadcast_to(frames['disabled'][0],frames['disabled'].shape)),\
        'The fixed scene still changes when temporal coverage is disabled; inspect native frames'
    # The upper skyline includes the reported crowns, excluding the near meadow.
    region=np.zeros((540,960),bool);region[140:335,:]=True
    variation={name:values.std(axis=0).mean(axis=2) for name,values in frames.items()}
    active=region&(variation['white_control']>0.5)
    assert active.any(),'The witness does not exercise fractional crown coverage'
    report={'status':'functional controls complete; inspect retained native images',
        'effective_settings':{k:v[0] for k,v in settings.items()},'disabled_frames_bit_identical':True,
        'skyline_mean_temporal_std_bytes':{k:float(v[active].mean()) for k,v in variation.items()},
        'skyline_control_pixel_share':float(active.mean()),'performance_validated':False}
    (out/'filter-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
