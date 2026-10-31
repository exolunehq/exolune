"""Cuit vaisseau.glb en vaisseau.vsx, le paquet lu par le moteur.

Usage : python paquet_moteur.py   (Python 3 et numpy, sans Blender)

Le moteur n'a ni lecteur JSON ni lecteur glTF : ce script fait le travail une
fois. Les nœuds sont aplatis (le manche et la manette restent repérés par sommet), tous les maillages fusionnés dans un seul tampon,
les sommets entrelacés, les images gardées en PNG (décodées par WIC).

Repère du paquet : celui de Blender, en mètres. Le nez est vers −Y, le haut
vers +Z ; la gauche du pilote est en +X.

Format, petit-boutiste :
  'VSX1', u32 version (3)
  u32 sommets, u32 indices, u32 tracés, u32 matériaux, u32 images
  sommets  : position 3f, normale 3f, tangente 4f, uv0 2f, uv1 2f, pose f (60 octets)
             (pose : l'attribut _POSE, 0 fixe, ]0, 1] le manche, ]1, 2] la manette, 3 à 6 les volets)
  indices  : u32
  tracés   : u32 premier indice, u32 nombre d'indices, u32 matériau
  matériaux: couleur 4f, émission 3f, métal f, rugosité f, échelle de normale f,
             force d'occlusion f, u32 mode (0 opaque, 1 mélange, 2 verrière),
             u32 recto-verso, i32 image[5], u32 uv[5], u32 rôle (96 octets)
             (images : couleur, métal-rugosité, normale, occlusion, émission ;
             -1 sans image ; uv : 0 ou 1 ; rôle : ROLES, ce que le moteur anime, 0 rien)
  images   : u32 sRGB, u32 octets, PNG
  pivots   : u32 nombre (6), puis point 3f et axe 3f : le manche, la manette, les volets dessus gauche et droit,
             dessous gauche et droit (vides « Pivot | … » ; pose 1 à 6 dans cet ordre)
Les tracés opaques viennent d'abord, puis ceux à mélange.
"""
import json, struct, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
# Ce que le moteur anime, par nom de matériau (Ship.hlsli, SHIP_ROLE_…) : les écrans et cadrans, le cœur des tuyères
# qui suit les gaz, les feux à éclats et anticollision.
ROLES = {'Jeu | ecran_nav': 1, 'Jeu | ecran_vol': 2, 'Jeu | ecran_systemes': 3, 'Jeu | jauge_prop': 4, 'Jeu | jauge_att': 5,
         'Jeu | jauge_alt': 6, 'Jeu | Tuyere chaude': 7, 'Jeu | Feu a eclats': 8, 'Jeu | Feu anticollision': 9}
# Les pièces mobiles, dans l'ordre de leur pose (Ship.hlsli, ShipPose) : pieces_mobiles.py, puis details_v3.py.
PIVOTS = ('Pivot | manche', 'Pivot | gaz', 'Pivot | volet dessus gauche', 'Pivot | volet dessus droit',
          'Pivot | volet dessous gauche', 'Pivot | volet dessous droit')
COMPONENTS = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

def lire_glb(path):
    data = path.read_bytes()
    magic, version, _ = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67 and version == 2, 'GLB 2.0 attendu'
    n, _ = struct.unpack_from('<II', data, 12); gltf = json.loads(data[20:20 + n])
    m, _ = struct.unpack_from('<II', data, 20 + n); binary = data[28 + n:28 + n + m]
    return gltf, binary

def accesseur(gltf, binary, index):
    a = gltf['accessors'][index]; view = gltf['bufferViews'][a['bufferView']]
    dtype = COMPONENTS[a['componentType']]; width = WIDTH[a['type']]
    start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = view.get('byteStride', 0) or width * np.dtype(dtype).itemsize
    raw = np.frombuffer(binary, np.uint8, count=stride * (a['count'] - 1) + width * np.dtype(dtype).itemsize, offset=start)
    rows = np.lib.stride_tricks.as_strided(raw, (a['count'], width * np.dtype(dtype).itemsize), (stride, 1))
    return np.ascontiguousarray(rows).view(dtype).reshape(a['count'], width)

def matrice(node):
    if 'matrix' in node: return np.array(node['matrix'], np.float64).reshape(4, 4).T
    x, y, z, w = node.get('rotation', (0, 0, 0, 1))
    r = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                  [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                  [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    m = np.eye(4); m[:3, :3] = r * np.array(node.get('scale', (1, 1, 1))); m[:3, 3] = node.get('translation', (0, 0, 0))
    return m

def cuire():
    gltf, binary = lire_glb(ROOT / 'vaisseau.glb')
    # glTF (x, y, z) vers Blender (x, -z, y).
    axes = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], np.float64)
    blocs = []   # (matériau, sommets, indices)
    pivots = {}  # nom -> (point, axe Z local), repère du paquet
    def visiter(i, parent):
        node = gltf['nodes'][i]; m = parent @ matrice(node)
        if node.get('name', '').startswith('Pivot | '):
            # L'axe Z local de Blender est l'axe Y local du glTF.
            full = axes @ m; axe = full[:3, :3] @ np.array([0, 1, 0])
            pivots[node['name']] = (full[:3, 3], axe / np.linalg.norm(axe))
        if 'mesh' in node:
            for prim in gltf['meshes'][node['mesh']]['primitives']:
                at = prim['attributes']; get = lambda k: accesseur(gltf, binary, at[k]) if k in at else None
                pos = get('POSITION').astype(np.float64); count = len(pos)
                nrm = get('NORMAL'); tan = get('TANGENT')
                uv0 = get('TEXCOORD_0'); uv1 = get('TEXCOORD_1')
                full = axes @ m; lin = full[:3, :3]; nlin = np.linalg.inv(lin).T
                p = pos @ lin.T + full[:3, 3]
                n = nrm @ nlin.T; n /= np.linalg.norm(n, axis=1, keepdims=True)
                t = np.zeros((count, 4)); t[:, 3] = 1
                if tan is not None:
                    t[:, :3] = tan[:, :3] @ lin.T; t[:, :3] /= np.maximum(np.linalg.norm(t[:, :3], axis=1, keepdims=True), 1e-12)
                    t[:, 3] = tan[:, 3] * np.sign(np.linalg.det(lin))
                u0 = uv0 if uv0 is not None else np.zeros((count, 2)); u1 = uv1 if uv1 is not None else u0
                pose = get('_POSE'); pose = pose if pose is not None else np.zeros((count, 1))
                v = np.hstack((p, n, t, u0, u1, pose)).astype(np.float32)
                idx = accesseur(gltf, binary, prim['indices']).astype(np.uint32).ravel()
                if np.linalg.det(lin) < 0: idx = idx.reshape(-1, 3)[:, ::-1].ravel()
                blocs.append((prim.get('material', 0), v, idx))
        for c in node.get('children', []): visiter(c, m)
    for i in gltf['scenes'][gltf.get('scene', 0)]['nodes']: visiter(i, np.eye(4))

    images = []; image_de = {}
    def image(info, srgb):
        if not info: return -1, 0
        source = gltf['textures'][info['index']]['source']
        if source not in image_de:
            view = gltf['bufferViews'][gltf['images'][source]['bufferView']]
            image_de[source] = len(images); images.append((srgb, binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]))
        return image_de[source], info.get('texCoord', 0)
    materiaux = []
    for mat in gltf['materials']:
        pbr = mat.get('pbrMetallicRoughness', {})
        force = mat.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength', 1)
        mode = 0 if mat.get('alphaMode', 'OPAQUE') != 'BLEND' else 2 if 'Verriere' in mat['name'] else 1
        tex = [image(pbr.get('baseColorTexture'), 1), image(pbr.get('metallicRoughnessTexture'), 0),
               image(mat.get('normalTexture'), 0), image(mat.get('occlusionTexture'), 0), image(mat.get('emissiveTexture'), 1)]
        materiaux.append(struct.pack('<4f3f4f2I5i5II', *pbr.get('baseColorFactor', (1, 1, 1, 1)),
            *[c * force for c in mat.get('emissiveFactor', (0, 0, 0))], pbr.get('metallicFactor', 1), pbr.get('roughnessFactor', 1),
            mat.get('normalTexture', {}).get('scale', 1), mat.get('occlusionTexture', {}).get('strength', 1),
            mode, int(mat.get('doubleSided', False)), *[t for t, _ in tex], *[u for _, u in tex], ROLES.get(mat['name'], 0)))
        print(f"{mat['name']:34s} mode {mode} images {[t for t, _ in tex]} rôle {ROLES.get(mat['name'], 0)}")
    modes = [struct.unpack_from('<11fI', m)[11] for m in materiaux]
    blocs.sort(key=lambda b: (modes[b[0]] != 0, b[0]))
    sommets = []; indices = []; traces = []; base = 0
    for mat, v, idx in blocs:
        traces.append((sum(len(i) for i in indices), len(idx), mat)); sommets.append(v); indices.append(idx + base); base += len(v)
    sommets = np.vstack(sommets); indices = np.concatenate(indices)
    with open(ROOT / 'vaisseau.vsx', 'wb') as f:
        f.write(b'VSX1' + struct.pack('<6I', 3, len(sommets), len(indices), len(traces), len(materiaux), len(images)))
        f.write(sommets.tobytes()); f.write(indices.tobytes())
        for t in traces: f.write(struct.pack('<3I', *t))
        for m in materiaux: f.write(m)
        for srgb, png in images: f.write(struct.pack('<2I', srgb, len(png))); f.write(png)
        f.write(struct.pack('<I', len(PIVOTS)))
        for nom in PIVOTS:
            point, axe = pivots[nom]; f.write(struct.pack('<6f', *point, *axe))
            print(nom, np.round(point, 4), 'axe', np.round(axe, 3))
    lo, hi = sommets[:, :3].min(0), sommets[:, :3].max(0)
    mobiles = sommets[:, 14]
    print('pose : manche', int(((mobiles > 0) & (mobiles <= 1)).sum()), 'sommets, manette', int(((mobiles > 1) & (mobiles <= 2)).sum()),
          'volets', [int((mobiles == k).sum()) for k in (3, 4, 5, 6)])
    print('VSX', len(sommets), 'sommets', len(indices) // 3, 'triangles', len(traces), 'tracés', len(images), 'images',
          'boîte', np.round(lo, 2), np.round(hi, 2))
    return sommets, indices

if __name__ == '__main__':
    s, i = cuire()
    # Contrôle : le paquet relu redonne le même nombre de sommets et des normales unitaires.
    data = (ROOT / 'vaisseau.vsx').read_bytes(); assert data[:4] == b'VSX1'
    nv, ni = struct.unpack_from('<2I', data, 8); assert nv == len(s) and ni == len(i)
    assert np.allclose(np.linalg.norm(s[:, 3:6], axis=1), 1, atol=1e-3)
    assert ((s[:, 14] > 0) & (s[:, 14] <= 1)).any() and ((s[:, 14] > 1) & (s[:, 14] <= 2)).any(), 'manche ou manette absents'
    assert all((s[:, 14] == k).any() for k in (3, 4, 5, 6)) and s[:, 14].max() <= 6, 'volets absents'
    assert struct.unpack_from('<I', data, len(data) - 4 - 24 * len(PIVOTS))[0] == len(PIVOTS), 'pivots absents'
    nt, nm = struct.unpack_from('<2I', data, 16); roles = set()
    # Chaque rôle présent : sinon un écran ou un feu manque, ou un nom a changé dans Blender.
    at = 28 + nv * 60 + ni * 4 + nt * 12
    for k in range(nm): roles.add(struct.unpack_from('<I', data, at + 96 * k + 92)[0])
    assert roles - {0} == set(ROLES.values()), ('rôles manquants', set(ROLES.values()) - roles)
    print('paquet OK')
