"""Record candidate geometry defects without confusing topology with art acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def inspect(path):
    scene = trimesh.load(path, force='scene', process=False)
    records = []
    for index, source in enumerate(scene.dump()):
        if not isinstance(source, trimesh.Trimesh):
            continue
        v = np.asarray(source.vertices)
        f = np.asarray(source.faces)
        item = {'part': index, 'exported_vertices': len(v), 'triangles': len(f),
                'finite_vertices': bool(np.isfinite(v).all()), 'bounds': source.bounds.tolist()}
        if len(f) <= 1_000_000:
            mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
            mesh.merge_vertices(digits_vertex=7)
            counts = np.bincount(mesh.edges_unique_inverse)
            item.update({'geometric_vertices_at_1e7_precision': len(mesh.vertices),
                         'boundary_edges': int(np.count_nonzero(counts == 1)),
                         'nonmanifold_edges': int(np.count_nonzero(counts > 2)),
                         'degenerate_faces': int(np.count_nonzero(mesh.area_faces < 1e-14)),
                         'duplicate_faces': int(len(mesh.faces) - np.count_nonzero(mesh.unique_faces())),
                         'winding_consistent': bool(mesh.is_winding_consistent),
                         'watertight': bool(mesh.is_watertight)})
            components = trimesh.graph.connected_components(mesh.face_adjacency,
                            nodes=np.arange(len(mesh.faces)), min_len=1)
            sizes = sorted((len(c) for c in components), reverse=True)
            item['connected_components'] = len(sizes)
            item['largest_components_triangles'] = sizes[:10]
        else:
            item['topology_scope'] = 'Dense source: counts only. Detailed topology is checked on bounded candidates.'
        records.append(item)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return {'path': str(path.resolve()), 'sha256': h.hexdigest(), 'parts': records,
            'triangles': sum(r['triangles'] for r in records),
            'exported_vertices': sum(r['exported_vertices'] for r in records),
            'art_accepted': False, 'runtime_accepted': False,
            'scope': 'Geometry diagnostics; a closed mesh can still erase apertures or distort the design.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mesh', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = inspect(a.mesh)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['path', 'triangles', 'exported_vertices']}))


if __name__ == '__main__':
    main()
