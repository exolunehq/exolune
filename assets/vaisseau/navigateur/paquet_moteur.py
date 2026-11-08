"""Cook the smooth Navigator and connected cabin with the shared VSX3 writer; no animation pivots."""
from pathlib import Path
import importlib.util
import numpy as np

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ship_pack', root.parent/'chasseur'/'paquet_moteur.py')
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)
pack.ROOT, pack.PIVOTS = root, ()
gltf,_=pack.lire_glb(root/'navigateur-cockpit.glb')
pack.ROLES={m['name']:10 if m['name']=='Navigator | polished chrome' else
            12 if m['name']=='Navigator | live instrument face' else 11 for m in gltf['materials']}
if __name__ == '__main__':
    vertices, indices = pack.cuire(root/'navigateur-cockpit.glb',root/'vaisseau.vsx')
    assert np.isfinite(vertices).all()
    assert len(vertices) > 98306 and len(indices) > 196608*3
    assert np.allclose(np.linalg.norm(vertices[:, 3:6], axis=1), 1, atol=1e-4)
    assert np.allclose(np.linalg.norm(vertices[:, 6:9], axis=1), 1, atol=1e-4)
    assert np.allclose((vertices[:, 3:6]*vertices[:, 6:9]).sum(axis=1), 0, atol=1e-4)
    assert (vertices[:, 14] == 0).all()
    assert np.linalg.norm(vertices[:, :3], axis=1).max() < 6.7
    print('Navigator pack verified: smooth static hull and cockpit, finite orthonormal shading frames.')
