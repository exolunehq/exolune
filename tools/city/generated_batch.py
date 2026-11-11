"""Build metric sources for several generated assets, each from its H3.1 draft (`draft.model_path` in the spec).

An accessible asset whose entrance approach is obstructed is retried along its front, 2 m apart up to
10 m each way; the position that passes is written back into assets/city/generated-buildings.json.

usage: python tools/city/generated_batch.py --out <delivery>/models <asset> [<asset> ...]
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parents[1] / 'assets/city/generated-buildings.json'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--blender', default='C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
    p.add_argument('assets', nargs='+')
    a = p.parse_args()
    for slot in a.assets:
        spec = json.loads(SPEC.read_text(encoding='utf8'))['assets'][slot]
        if (a.out / slot / 'source.json').exists():
            print(slot, 'exists', flush=True)
            continue
        start = spec['entry']['x'] if 'entry' in spec else None
        tries = [start] if start is None else [start] + [v for d in (2, 4, 6, 8, 10) for v in (d, -d) if v != start]
        for x in tries:
            shutil.rmtree(a.out / slot, ignore_errors=True)
            args = [a.blender, '--background', '--factory-startup', '--threads', '6', '--python-exit-code', '1', '--python',
                    str(HERE / 'generated_source.py'), '--', '--asset', slot, '--model', spec['draft']['model_path'], '--out', str(a.out)]
            if x is not None:
                args += ['--entry-x', str(x)]
            run = subprocess.run(args, capture_output=True, text=True, errors='replace')
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / f'source-{slot}.log').write_text(run.stdout[-6000:] + run.stderr[-3000:], encoding='utf8')
            line = next((l for l in run.stdout.splitlines() if l.startswith('SOURCE')), None)
            if run.returncode == 0 and line:
                if x != start:
                    doc = json.loads(SPEC.read_text(encoding='utf8'))
                    doc['assets'][slot]['entry']['x'] = x
                    SPEC.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
                print(slot, 'x', x, line, flush=True)
                break
            reason = next((l for l in (run.stdout + run.stderr).splitlines() if 'Error' in l), 'failed')
            print(slot, 'x', x, 'FAILED', reason.strip()[:160], flush=True)


if __name__ == '__main__':
    main()
