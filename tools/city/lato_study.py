"""Run local LATO.2 with traceable inputs and retain raw/rebuilt topology separately.

Run with the ComfyUI-LATO2 isolated Python. Neither an inference exit code nor a
closed surface promotes an architectural asset. The two exports have no UV/PBR.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import trimesh

from partcrafter_study import digest
from inspect_geometry import inspect


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def export_raw(source_path, dump_path, target):
    scene = trimesh.load(source_path, force='scene', process=False)
    source = trimesh.util.concatenate([m for m in scene.dump() if isinstance(m, trimesh.Trimesh)])
    center = (source.bounds[0] + source.bounds[1]) * .5
    extent = float((source.bounds[1] - source.bounds[0]).max())
    with np.load(dump_path) as data:
        mesh = trimesh.Trimesh(vertices=data['vertices'] * extent + center,
                               faces=data['lato_faces'], process=False)
    mesh.export(target)


def orient_candidate(source_path, target):
    """Separate shading/winding repair from changes to the generated surface."""
    mesh = trimesh.load(source_path, force='mesh', process=False)
    vertices, faces = mesh.vertices.copy(), mesh.faces.copy()
    trimesh.repair.fix_normals(mesh, multibody=True)
    if not np.array_equal(vertices, mesh.vertices) or not np.array_equal(
            np.sort(faces, axis=1), np.sort(mesh.faces, axis=1)):
        raise RuntimeError('Orientation-only finishing unexpectedly changed the surface')
    target.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(mesh), include_normals=True))
    save(target.with_suffix('.json'), {'source': str(source_path), 'source_sha256': digest(source_path),
         'output_sha256': digest(target), 'method': 'Orient faces; export smooth vertex normals.',
         'vertex_positions_unchanged': True, 'undirected_faces_unchanged': True,
         'triangles': len(mesh.faces), 'winding_consistent': bool(mesh.is_winding_consistent),
         'art_accepted': False, 'runtime_accepted': False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--vertices', type=int, default=5000)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--topology-samples', type=int, choices=[1, 2, 4], default=1)
    p.add_argument('--azimuth', type=float, default=45)
    p.add_argument('--elevation', type=float, default=30)
    p.add_argument('--wrapper', type=Path, default=Path('E:/ComfyUI/custom_nodes/ComfyUI-LATO2'))
    p.add_argument('--models', type=Path, default=Path('E:/ComfyUI_Models/models/lato2'))
    a = p.parse_args()
    if not 200 <= a.vertices <= 5000:
        p.error('Keep the published 200–5,000 vertex request range')
    if (a.out / 'mesh.glb').exists():
        p.error('Use a separate output directory for each candidate')
    a.out.mkdir(parents=True, exist_ok=True)
    runner = a.wrapper / 'runners/lato2_runner.py'
    repo = a.wrapper / 'vendor/LATO.2'
    command = [sys.executable, '-u', str(runner), '--repo', str(repo), '--ckpt', str(a.models),
               '--dino_hub_dir', str(a.models / 'dinov2'), '--input', str(a.source.resolve()),
               '--output', str(a.out / 'mesh.glb'), '--vert_num', str(a.vertices),
               '--seed', str(a.seed), '--tflow_samples', str(a.topology_samples),
               '--vflow_steps', '24', '--tflow_steps', '50', '--cfg', '3.0',
               '--azimuth', str(a.azimuth), '--elevation', str(a.elevation), '--renderer', 'auto',
               '--no-solidify', '--surface', '--dump', str(a.out / 'topology.npz'),
               '--condition_image', str(a.out / 'conditioning.png')]
    recipe = {'backend': 'LATO.2 with the ComfyUI-LATO2 Windows runtime', 'command': command,
              'source': {'path': str(a.source.resolve()), 'sha256': digest(a.source)},
              'requested_vertices': a.vertices, 'seed': a.seed, 'topology_samples': a.topology_samples,
              'conditioning_camera': {'azimuth': a.azimuth, 'elevation': a.elevation},
              'solidify': False, 'surface_rebuild': True,
              'runner_sha256': digest(runner), 'study_runner_sha256': digest(__file__),
              'revisions': {str(d): subprocess.check_output(['git', '-C', str(d), 'rev-parse', 'HEAD'],
                            text=True).strip() for d in [repo, a.wrapper]},
              'models': [{'path': str(f), 'sha256': digest(f)}
                         for f in sorted(a.models.rglob('*')) if f.suffix in {'.pt', '.pth'}]}
    save(a.out / 'recipe.json', recipe)
    env = os.environ.copy()
    temp = Path('E:/ExoluneTools/tmp-architecture')
    temp.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temp), TMP=str(temp), OMP_NUM_THREADS='4', PYTHONIOENCODING='utf8')
    with (a.out / 'inference.log').open('w', encoding='utf8') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    export_raw(a.source, a.out / 'topology.npz', a.out / 'raw.glb')
    orient_candidate(a.out / 'mesh.glb', a.out / 'oriented.glb')
    outputs = {}
    for name in ['mesh', 'raw', 'oriented']:
        result = inspect(a.out / (name + '.glb'))
        save(a.out / (name + '-geometry.json'), result)
        outputs[name] = {k: result[k] for k in ['path', 'sha256', 'triangles', 'exported_vertices']}
    save(a.out / 'manifest.json', {'recipe': recipe, 'outputs': outputs,
         'scope': 'Geometry only; raw and rebuilt topology retained; no UV/PBR transfer.',
         'art_accepted': False, 'runtime_accepted': False, 'performance_accepted': False})
    print(json.dumps(outputs), flush=True)


if __name__ == '__main__':
    main()
