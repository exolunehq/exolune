"""Nuages : une transmission solaire de 1 doit laisser les surfaces intactes.

Deux variantes du meme natif, sans fenetre : la composition de l'ombre des nuages
retiree, puis l'ombre tracee avec sa transmission forcee a 1, dans deux copies de
MyPlanetEngine/Clouds.hlsli. Chaque variante recompile les quatre points d'entree
des nuages, la passe unique et les trois de la passe temporelle, celle que le jeu
emploie. La meteo, les modeles, les cameras et la lumiere ne changent pas. Aucun
fichier du runtime fourni n'est modifie. Ce controle d'integration ne mesure pas
la qualite des nuages.

python tools/banc_composition_surfaces.py --exe x64/Release/MyPlanetEngine.exe --out <dossier> --dxc <dxc.exe> --scans <dossier>
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
VIEWS = [
    ('boreal_sol', (2, -49.632, 90.531, 5, -60), (-30, 100)),
    ('boreal_haut', (31, -49.23454, 92.64887, 14.8, 109.2), (-30, 100)),
    ('tempere', (2, 30.38761, 120.52330, -14.4, -115), (20, 120)),
    ('desert', (2, -19.63208, .52597, 5, 0), (-15, 5)),
]
# Les points d'entree des nuages (MyPlanetEngine.vcxproj), compiles depuis AtmospherePass.hlsl.
ENTRIES = [('PSMain', 'AtmospherePass.cso'), ('PSCloudTrace', 'CloudTrace.cso'),
           ('PSCloudTraceHalf', 'CloudTraceHalf.cso'), ('PSCloudResolve', 'CloudResolve.cso')]
# Sans ombre : la composition qui retire la lumiere du soleil ; avec : le trace de l'ombre, a transmission 1.
VARIANTS = {
    'sans_ombres': ('scene.a > 0.0 && clouds.surfaceShadowT < 1.0', 'false /* controle de neutralite */'),
    'ombres': ('CloudTraceShadow(receiverQKm, sunQ)', '1.0 /* controle de neutralite */'),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--exe', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--dxc', type=Path, required=True)
    ap.add_argument('--scans', type=Path, required=True)
    ap.add_argument('--assets', type=Path, default=ROOT/'assets/foliage/climate_shrubs_v2')
    a = ap.parse_args()
    exe, out = a.exe.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = (ROOT/'MyPlanetEngine/Clouds.hlsli').read_text(encoding='utf8')
    for old, _ in VARIANTS.values():
        if source.count(old) != 1:
            raise ValueError('La composition solaire a change ; adapter le controle.')
    for variant, (old, new) in VARIANTS.items():
        runtime = out/variant
        runtime.mkdir()
        for p in [exe, *exe.parent.glob('*.cso')]:
            shutil.copy2(p, runtime/p.name)
        # Ces copies ne sortent jamais du repertoire de ce banc ; les autres en-tetes viennent du depot (-I).
        (runtime/'Clouds.hlsli').write_text(source.replace(old, new), encoding='utf8')
        for name in ('AtmospherePass.hlsl', 'CloudsTemporal.hlsli'):
            shutil.copy2(ROOT/'MyPlanetEngine'/name, runtime/name)
        log = b''
        for entry, cso in ENTRIES:
            compiled = subprocess.run([str(a.dxc.resolve()), '-T', 'ps_6_0', '-E', entry, '-O3', '-I', str(ROOT/'MyPlanetEngine'),
                                       '-Fo', str(runtime/cso), str(runtime/'AtmospherePass.hlsl')], capture_output=True, check=True)
            log += compiled.stdout+compiled.stderr
        (runtime/'compilation.log').write_bytes(log)
        jobs = runtime/'jobs.txt'
        jobs.write_text(''.join(' '.join(map(str, [runtime/(name+'.bmp'), '-', *pose, 2, *sun]))+'\n'
                                for name, pose, sun in VIEWS), encoding='utf8')
        # Le jeu est le defaut de l'exe : nuages, meteo figee a l'instant 0, sans antialiasing temporel ni halo.
        env = {k:v for k,v in os.environ.items() if not k.upper().startswith('MYPLANETENGINE_')}
        env.update(MYPLANETENGINE_BATCH=str(jobs), MYPLANETENGINE_SCANS=str(a.scans.resolve()), MYPLANETENGINE_TIME='0 0',
                   MYPLANETENGINE_FOLIAGE_ASSETS=str(a.assets.resolve()),
                   MYPLANETENGINE_FOLIAGE_WARMUP='1', MYPLANETENGINE_FOLIAGE_SAMPLES='1')
        rendered = subprocess.run([str(runtime/exe.name)], cwd=runtime, env=env,
                                  capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
        (runtime/'rendu.log').write_bytes(rendered.stdout+rendered.stderr)
        rendered.check_returncode()
        print(runtime.name+' termine', flush=True)
    report = {}
    for name, _, _ in VIEWS:
        arrays = []
        for variant in VARIANTS:
            path = out/variant/(name+'.bmp')
            with Image.open(path) as im:
                im.convert('RGB').save(path.with_suffix('.png'))
                arrays.append(np.asarray(im.convert('RGB'), dtype=np.int16))
        delta = abs(arrays[0]-arrays[1])
        report[name] = dict(ecart_moyen_255=float(delta.mean()), maximum_255=int(delta.max()),
                            pixels_plus_de_1=int((delta.max(axis=2)>1).sum()))
    (out/'rapport.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(report), flush=True)
    if any(row['pixels_plus_de_1'] for row in report.values()):
        raise SystemExit('Echec : la composition solaire modifie des surfaces avec transmission=1.')


if __name__ == '__main__':
    main()
