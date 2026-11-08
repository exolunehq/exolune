"""Integrate pinned neutral variants into an existing complete city bank, on CPU.

This command does not launch the engine or claim art/performance acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--series', type=Path, required=True)
    p.add_argument('--base-bank', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mapping', type=Path, default=ROOT / 'assets/city/series-runtime.json')
    p.add_argument('--recipe', type=Path, default=ROOT / 'assets/city/solarpunk.json')
    p.add_argument('--blender', type=Path, default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    a = p.parse_args()
    a.out = a.out.resolve()
    if a.out.is_relative_to(ROOT) or a.out == a.base_bank.resolve().parent:
        raise ValueError('Use a separate external delivery directory')
    if (a.out / 'native-review').exists():
        raise ValueError('Retain captured evidence; choose another delivery directory')
    a.out.mkdir(parents=True, exist_ok=True)
    mapping = json.loads(a.mapping.read_text())
    recipe = json.loads(a.recipe.read_text())
    production = json.loads((a.base_bank / 'production.json').read_text())
    layout = json.loads((a.base_bank / 'layout.json').read_text())
    overrides = {item['id']: item['path'] for item in production['sources']}

    def run(command, label):
        print(label, flush=True)
        with (a.out / (label + '.log')).open('w') as log:
            subprocess.run(list(map(str, command)), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                           check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    for runtime_id, source_id in mapping['models'].items():
        neutral = a.series / 'models' / source_id / 'master.glb'
        metadata = json.loads((neutral.parent / 'source.json').read_text())
        if sha(neutral) != metadata['master_sha256']:
            raise ValueError('Neutral source hash mismatch: ' + source_id)
        entry = next((e for e in recipe['assets'] if e['id'] == runtime_id), None)
        if entry is None:
            entry = {'id': runtime_id, 'kind': metadata['family'], 'seed': 11082026, 'reference': 0}
            recipe['assets'].append(entry)
        lo, hi = metadata['bounds']
        entry.update(width=hi[0]-lo[0], depth=hi[1]-lo[1], height=hi[2]-lo[2],
                     neutral_series_id=source_id, neutral_source_sha256=sha(neutral))
        if entry['kind'] == 'house':
            entry['floors'] = 2
        target = a.out / 'models' / runtime_id / 'master.glb'
        saved = target.parent / 'source.json'
        old = json.loads(saved.read_text()) if saved.exists() else {}
        verified = (target.exists() and old.get('master_sha256') == sha(target)
                    and old.get('neutral_source_sha256') == sha(neutral)
                    and old.get('tools', {}).get('prepare_series_runtime.py') == sha(HERE / 'prepare_series_runtime.py'))
        if not verified:
            run([a.blender, '--background', '--factory-startup', '--threads', '5', '--python-exit-code', '1',
                 '--python', HERE / 'prepare_series_runtime.py', '--', '--series', a.series,
                 '--mapping', a.mapping, '--out', a.out / 'models', '--asset', runtime_id], 'prepare-' + runtime_id)
        overrides[runtime_id] = str(target)
    for filename, value in [('overrides.json', overrides), ('recipe.json', recipe)]:
        (a.out / filename).write_text(json.dumps(value, indent=2) + '\n')
    shutil.copy2(a.mapping, a.out / 'series-runtime.json')
    if (a.base_bank / 'cook-cache').exists() and not (a.out / 'bank/cook-cache').exists():
        shutil.copytree(a.base_bank / 'cook-cache', a.out / 'bank/cook-cache')
    run([sys.executable, HERE / 'produce.py', '--recipe', a.out / 'recipe.json', '--out', a.out,
         '--terrain', layout['terrain_source'], '--overrides', a.out / 'overrides.json',
         '--blender', a.blender, '--seed', str(layout['seed'])], 'produce-city')
    cooked = json.loads((a.out / 'bank/layout.json').read_text())
    counts = {name: sum(i['id'] == name for i in cooked['instances']) for name in mapping['models']}
    if not all(counts.values()):
        raise ValueError('New series missing from native review layout: ' + str(counts))
    (a.out / 'integration.json').write_text(json.dumps({
        'series': str(a.series), 'base_bank': str(a.base_bank), 'mapping_sha256': sha(a.mapping),
        'placements': counts, 'bank': str(a.out / 'bank'), 'art_accepted': False,
        'performance_accepted': False, 'native_review': 'pending'}, indent=2) + '\n')
    print('Integrated:', counts, flush=True)


if __name__ == '__main__':
    main()
