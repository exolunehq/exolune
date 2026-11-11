"""Swap generated city sources into an existing complete bank, on CPU.

Every other source stays pinned to the base delivery. The generated sources
must already exist under `<out>/models/<id>` (see `generated_source.py`). This
command does not launch the engine or claim art or performance acceptance.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True, help='Delivery directory holding recipe.json and bank/')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--assets', required=True, help='Comma-separated asset ids to replace')
    p.add_argument('--terrain', type=Path, help='Terrain export; defaults to the base layout terrain')
    p.add_argument('--blender', type=Path, default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    a = p.parse_args()
    a.out = a.out.resolve()
    if a.out.is_relative_to(ROOT) or a.out == a.base.resolve():
        raise ValueError('Use a separate external delivery directory')
    recipe = json.loads((a.base / 'recipe.json').read_text(encoding='utf8'))
    production = json.loads((a.base / 'bank/production.json').read_text())
    layout = json.loads((a.base / 'bank/layout.json').read_text())
    overrides = {item['id']: item['path'] for item in production['sources']}
    spec = json.loads((ROOT / 'assets/city/generated-buildings.json').read_text(encoding='utf8'))
    for asset in a.assets.split(','):
        source = a.out / 'models' / asset / 'master.glb'
        metadata = json.loads((source.parent / 'source.json').read_text())
        if sha(source) != metadata['master_sha256']:
            raise ValueError('Generated source hash mismatch: ' + asset)
        entry = next((e for e in recipe['assets'] if e['id'] == asset), None)
        if entry is None:
            # A new generated asset joins the kit: its source is its only geometry.
            entry = {'id': asset, 'kind': spec['assets'][asset]['kind'], 'seed': 1 + max(e['seed'] for e in recipe['assets'])}
            recipe['assets'].append(entry)
        lo, hi = metadata['bounds_z_up']
        entry.update(width=hi[0] - lo[0], depth=hi[1] - lo[1], height=hi[2] - lo[2], floors=metadata['floors'],
                     generated_source_sha256=sha(source))
        for key in ('neutral_series_id', 'neutral_source_sha256'):
            entry.pop(key, None)
        # The shared surface rule, then the building's own values: how the cook reads the atlas.
        # `"surface": false` keeps the atlas displayed: the class reading assumes closed, opaque glazing.
        asset_spec = spec['assets'][asset]
        if asset_spec.get('surface', {}) is False:
            entry.pop('surface', None)
        else:
            entry['surface'] = {**spec['surface'], **asset_spec.get('surface', {}), 'floor_z': asset_spec['entry']['z_floor']}
        # Rooms baked behind the glazing, in the source's metric model space.
        entry['interiors'] = asset_spec.get('interiors', [])
        overrides[asset] = str(source)
    (a.out / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n', encoding='utf8')
    (a.out / 'overrides.json').write_text(json.dumps(overrides, indent=2) + '\n')
    if (a.base / 'bank/cook-cache').exists() and not (a.out / 'bank/cook-cache').exists():
        shutil.copytree(a.base / 'bank/cook-cache', a.out / 'bank/cook-cache')
    terrain = a.terrain or Path(layout['terrain_source'])
    with (a.out / 'produce-city.log').open('w') as log:
        subprocess.run([sys.executable, str(HERE / 'produce.py'), '--recipe', str(a.out / 'recipe.json'), '--out', str(a.out),
                        '--terrain', str(terrain), '--overrides', str(a.out / 'overrides.json'), '--blender', str(a.blender),
                        '--seed', str(layout['seed'])], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    cooked = json.loads((a.out / 'bank/layout.json').read_text())
    counts = {name: sum(i['id'] == name for i in cooked['instances']) for name in a.assets.split(',')}
    if not all(counts.values()):
        raise ValueError('Generated source missing from the review layout: ' + str(counts))
    (a.out / 'integration.json').write_text(json.dumps({
        'base': str(a.base), 'terrain': str(terrain), 'terrain_sha256': sha(terrain), 'placements': counts,
        'bank': str(a.out / 'bank'), 'art_accepted': False, 'performance_accepted': False,
        'native_review': 'pending'}, indent=2) + '\n')
    print('Integrated:', counts, flush=True)


if __name__ == '__main__':
    main()
