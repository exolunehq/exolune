"""Select inspected native views without changing their pixels or bank identity."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageChops


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection', type=Path, required=True,
                   help='Ordered mapping: output label -> {directory, view}')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Keep review evidence immutable; choose a fresh directory')
    selected = json.loads(a.selection.read_text())
    captures = []
    routes = []
    common = None
    staged = []
    for label, source in selected.items():
        root = Path(source['directory'])
        review = json.loads((root / 'functional.json').read_text())
        protocol = {k: review['protocol'][k] for k in ['executable', 'library', 'scene', 'shaders', 'textures']}
        if common is None:
            common = protocol
        if protocol != common:
            raise ValueError('Cannot combine captures of different banks, engines or materials')
        name = source['view']
        capture = next(c for c in review['captures'] if c['name'] == name)
        bmp = root / (name + '.bmp')
        png = root / (name + '.png')
        if sha(bmp) != capture['sha256']:
            raise ValueError('Changed native capture: ' + str(bmp))
        if ImageChops.difference(Image.open(bmp).convert('RGB'), Image.open(png).convert('RGB')).getbbox():
            raise ValueError('PNG differs from the native pixels: ' + str(png))
        route = next(l for l in (root / 'route.txt').read_text().splitlines() if l.startswith(name + ' | '))
        routes.append(label + ' | ' + route.split(' | ', 1)[1])
        captures.append({**capture, 'name': label, 'origin': str(bmp),
                         'origin_protocol': review['protocol'],
                         'origin_manifest_sha256': sha(root / 'functional.json')})
        staged.append((label, root, name))
    a.out.mkdir(parents=True)
    for label, root, name in staged:
        for suffix in ['.bmp', '.png', '.bmp.txt', '.bmp.city.json']:
            shutil.copy2(root / (name + suffix), a.out / (label + suffix))
    shutil.copy2(a.selection, a.out / 'selection.json')
    shutil.copy2(__file__, a.out / 'assembler.py')
    (a.out / 'route.txt').write_text('\n'.join(routes) + '\n')
    (a.out / 'functional.json').write_text(json.dumps({
        'functional_only': True, 'art_accepted': False, 'performance_accepted': False,
        'protocol': common, 'captures': captures, 'assembler_sha256': sha(__file__),
        'selection_sha256': sha(a.selection)}, indent=2) + '\n')
    print('Selected', len(captures), 'unchanged native captures of the same bank')


if __name__ == '__main__':
    main()
