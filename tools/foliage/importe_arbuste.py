"""Télécharge puis convertit l'arbuste Searsia Lucida CC0 en FOLMESH1/FOLMAT01.

Dépendances : numpy, Pillow, et fichiers auxiliaires importe.py et importe_jeu.py.
Le cache et les résultats lourds sont régénérables. Voir sources_arbuste.json.
"""
from pathlib import Path
import hashlib, json, urllib.request
import numpy as np
from PIL import Image
from importe import CACHE, accessor
from importe_jeu import write

SOURCE = Path(__file__).with_name('sources_arbuste.json')
FOLDER = CACHE / 'searsia_lucida'


def download():
    manifest = json.loads(SOURCE.read_text(encoding='utf8'))
    for item in manifest['files']:
        path = FOLDER / item['path']; path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            with urllib.request.urlopen(item['url'], timeout=120) as src:
                data = src.read()
            if hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('SHA-256 incorrect : ' + item['url'])
            path.write_bytes(data)
    return manifest


def main():
    manifest = download()
    doc = json.loads((FOLDER / 'searsia_lucida_1k.gltf').read_text(encoding='utf8'))
    blob = (FOLDER / 'searsia_lucida.bin').read_bytes()
    nodes = [n for n in doc['nodes'] if n.get('name') == manifest['node']]
    if len(nodes) != 1: raise ValueError('Variante source introuvable')
    node = nodes[0]
    if any(k in node for k in ('matrix','rotation','scale','children')): raise ValueError('Transformation inconnue')
    translation=np.asarray(node.get('translation',[0,0,0]))
    parts=[]
    for p in doc['meshes'][node['mesh']]['primitives']:
        if p.get('mode',4) != 4: raise ValueError('Triangles attendus')
        a=p['attributes']; mat=doc['materials'][p['material']]['name']
        if mat == 'searsia_lucida': tile=0
        elif mat in ('searsia_lucida_leaves','searsia_lucida_twigs'): tile=1
        else: raise ValueError('Matériau inconnu : '+mat)
        parts.append((accessor(doc,blob,a['POSITION']).astype(float)+translation,
                      accessor(doc,blob,a['NORMAL']), accessor(doc,blob,a['TEXCOORD_0']),
                      accessor(doc,blob,p['indices']),tile))
    folder=FOLDER/'textures'
    color=Image.open(folder/'searsia_lucida_diff_1k.jpg').convert('RGBA')
    alpha=Image.open(folder/'searsia_lucida_alpha_1k.png').convert('L')
    if alpha.size != color.size: raise ValueError('Dimensions alpha incompatibles')
    leaves=color.copy();leaves.putalpha(alpha)
    normals=Image.open(folder/'searsia_lucida_nor_gl_1k.jpg').convert('RGBA')
    arm=np.asarray(Image.open(folder/'searsia_lucida_arm_1k.jpg').convert('RGB'))
    masks=[]
    for transmission in (0,255):
        m=np.empty((*arm.shape[:2],4),dtype=np.uint8)
        m[:,:,0]=arm[:,:,0];m[:,:,1]=arm[:,:,1];m[:,:,2]=transmission;m[:,:,3]=255
        masks.append(Image.fromarray(m))
    write('game_shrub',parts,[color,leaves],[normals,normals],masks)

if __name__=='__main__': main()
