"""Native hidden orbit comparison, stationary or moving, one engine at a time.

python tools/banc_orbite.py --exe <exe> --out <new-directory>
    --motion "0.08 0.003 0.016666667 1 0 0" [--erosion-mode 0|1|2]

GPU percentiles use native timestamps, not averages of FPS. Cadence includes CPU
and presentation overhead. The optional erosion mode is a diagnostic comparison,
not a performance fix. It requires an executable supporting that setting.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

PASSES = ['mer_fft', 'terrain_calc', 'objets_place', 'plantes_place', 'copies', 'feuillage_tri',
          'terrain_dessin', 'objets_dessin', 'feuillage_dessin', 'nuages_aux', 'nuages_trace',
          'atmosphere', 'post', 'total', 'cpu_prep', 'cpu_liste', 'cpu_present', 'cpu_attente',
          'cadence', 'gpu_inactif']
ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    'massif1231': (1230920.1, -9.148316, 124.767492, 71.08, 20.70, 20, 120),
    'hemisphere3000': (3000000, 42.693130, -175.950838, 90, 0, 40, -170),
    'globe10000': (10000000, -0.5, -18.225, 90, 0, 10, -5),
    'far40000': (40000000, 25, 60, 90, 0, 20, 120),
}


def run(a):
    active = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq MyPlanetEngine.exe', '/FO', 'CSV'], text=True)
    if 'MyPlanetEngine.exe' in active:
        raise RuntimeError('Another engine is already running; do not share the GPU.')
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    selected = {name: VIEWS[name] for name in a.views.split(',')}
    jobs = out / 'jobs.txt'
    jobs.write_text(''.join(f"{out / (name + '.bmp')} rendu {h} {lat} {lon} {pitch} {heading} 2 0 {slat} {slon}\n"
                           for name, (h, lat, lon, pitch, heading, slat, slon) in selected.items()))
    env = {k: v for k, v in os.environ.items() if not k.startswith('MYPLANETENGINE_')}
    env.update(MYPLANETENGINE_BATCH=str(jobs), MYPLANETENGINE_RESOLUTION=a.res,
               MYPLANETENGINE_VSYNC='0', MYPLANETENGINE_FULLSCREEN='0',
               MYPLANETENGINE_SCANS=str(Path(a.scans).resolve()),
               MYPLANETENGINE_FOLIAGE_WARMUP=str(a.warmup),
               MYPLANETENGINE_FOLIAGE_SAMPLES=str(a.samples))
    if a.motion:
        env['MYPLANETENGINE_BATCH_MOTION'] = a.motion
    if a.no_clouds:
        env['MYPLANETENGINE_NO_CLOUDS'] = '1'
    if a.erosion_mode is not None:
        env['MYPLANETENGINE_EROSION_MODE'] = str(a.erosion_mode)
    if a.gpu_breadcrumbs:
        env['MYPLANETENGINE_GPU_BREADCRUMBS'] = '1'
    exe = Path(a.exe).resolve()
    meta = {'exe': str(exe), 'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
            'shader_sha256': {shader.name: hashlib.sha256(shader.read_bytes()).hexdigest()
                              for shader in sorted(exe.parent.glob('*.cso'))},
            'resolution': a.res, 'motion_per_frame': a.motion, 'clouds': not a.no_clouds,
            'warmup': a.warmup, 'samples': a.samples, 'views': selected, 'erosion_mode': a.erosion_mode,
            'gpu_breadcrumbs': a.gpu_breadcrumbs, 'started': time.strftime('%Y-%m-%d %H:%M:%S')}
    (out / 'config.json').write_text(json.dumps(meta, indent=2))
    print('START', out, flush=True)
    start = time.monotonic()
    with (out / 'engine.log').open('w') as log:
        process = subprocess.run([str(exe)], cwd=exe.parent, env=env, stdout=log, stderr=log,
                                 timeout=1500, creationflags=subprocess.CREATE_NO_WINDOW)
    if process.returncode:
        error_path = Path(str(jobs) + '.error.txt')
        error = error_path.read_text(errors='replace') if error_path.exists() else 'No native error sidecar.'
        (out / 'failure.json').write_text(json.dumps({'exit_code': process.returncode, 'error': error}, indent=2))
        raise RuntimeError(f'Engine failed ({process.returncode}): {error.strip()}')
    result = {}
    for name in selected:
        values = (out / (name + '.bmp.perf')).read_text().split()
        count = int(values[-1])
        if count != a.samples:
            raise RuntimeError(f'{name}: {count} samples instead of {a.samples}')
        averages = dict(zip(PASSES, map(float, values[:-1])))
        foliage = json.loads((out / (name + '.bmp.planet-foliage.json')).read_text())
        gpu = np.array(foliage['gpu_samples_ms'])[:, 2]
        if len(gpu) != a.samples:
            raise RuntimeError(f'{name}: incomplete GPU series')
        stats = {key: float(value) for key, value in zip(['p50_ms', 'p95_ms', 'p99_ms', 'max_ms'],
                                                        np.percentile(gpu, [50, 95, 99, 100]))}
        stats.update(mean_ms=float(gpu.mean()), fps=1000 / averages['cadence'],
                     over_33_ms=int((gpu > 33.333).sum()), over_50_ms=int((gpu > 50).sum()))
        result[name] = {'frames': count, 'gpu': stats, 'passes_ms': averages}
        frames_path = out / (name + '.bmp.frames.csv')
        if frames_path.exists():
            with frames_path.open() as f:
                rows = list(csv.DictReader(f))
            if len(rows) != a.samples:
                raise RuntimeError(f'{name}: incomplete per-frame trace')
            result[name]['trace'] = {
                key: dict(zip(['mean_ms', 'p50_ms', 'p95_ms', 'p99_ms', 'max_ms'],
                              map(float, [np.mean(v), *np.percentile(v, [50, 95, 99, 100])])))
                for key in rows[0] for v in [[float(row[key]) for row in rows]]}
        print(name, json.dumps(stats), 'terrain_ms', averages['terrain_calc'], flush=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2))
    print('DONE', round(time.monotonic() - start, 1), 's', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--gpu-breadcrumbs', action='store_true')
    p.add_argument('--exe', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--res', default='1920 1080')
    p.add_argument('--views', default=','.join(VIEWS))
    p.add_argument('--motion', default='')
    p.add_argument('--warmup', type=int, default=30)
    p.add_argument('--samples', type=int, default=180)
    p.add_argument('--no-clouds', action='store_true')
    p.add_argument('--erosion-mode', type=int, choices=(0, 1, 2))
    p.add_argument('--scans', default=str(ROOT.parent / 'scans'))
    run(p.parse_args())
