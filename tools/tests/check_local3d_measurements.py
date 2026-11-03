"""Audit all four captured rounds without submitting any rendering work."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from banc_local3d import VIEWS, sha


def check(folder):
    folder=Path(folder);inputs=json.loads((folder/'inputs.json').read_text())
    perf=json.loads((folder/'performance.json').read_text());protocol=perf['protocol'];fingerprints={}
    assert sha(folder/'frozen/bin/MyPlanetEngine.exe')==inputs['executable']
    for name,digest in inputs['shaders'].items():assert sha(folder/'frozen/bin'/name)==digest
    for kind,files in inputs['catalogues'].items():
        for relative,digest in files.items():assert sha(folder/'frozen'/kind/relative)==digest
    for relative,digest in inputs['shared_assets'].items():assert sha(folder/'frozen'/relative)==digest
    for view,*_ in VIEWS:
        population=None
        for sequence,kind in enumerate(protocol['order']):
            base=folder/f'{sequence}_{kind}'
            marker=base/f'complete_{view}.json'
            if not marker.exists():marker=base/'complete_all.json'
            checkpoint=json.loads(marker.read_text())
            assert checkpoint['inputs']==inputs and view in checkpoint['views']
            assert checkpoint['samples']==protocol['samples_per_view_per_round']
            assert checkpoint['warmup']==protocol['warmup']
            file=base/(view+'.bmp.planet-foliage.json');meta=json.loads(file.read_text())
            assert not sum(meta['overflow'])
            series=np.asarray(meta['gpu_samples_ms'])
            assert series.shape==(protocol['samples_per_view_per_round'],3)
            assert np.isfinite(series).all() and (series>=0).all()
            if population is None:population=meta['model_counts']
            assert population==meta['model_counts'],'Classified population changed between paired rounds'
            counts=np.asarray(meta['model_counts']);draws=np.asarray(meta['mesh_lod_counts'])
            assert counts.shape==(31,2) and draws.shape==(31,5)
            assert (draws>=0).all() and (draws.sum(1)>=counts[:,0]).all() and (draws.sum(1)<=2*counts[:,0]).all()
            for captured in [file,base/(view+'.bmp.perf')]:fingerprints[str(captured.relative_to(folder))]=sha(captured)
    return {'status':'pass','views':len(VIEWS),'rounds':len(protocol['order']),
            'samples_per_view_per_representation':2*protocol['samples_per_view_per_round'],
            'all_round_populations_equal':True,'overflow':False,'frozen_inputs_verified':True,
            'timing_note':'Isolation is enforced by the capturing monitor; this audit verifies the retained protocol and data',
            'auditor_sha256':sha(Path(__file__)),'capture_hashes':fingerprints}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('measurements',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=check(args.measurements)
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='capture_hashes'},indent=2))
