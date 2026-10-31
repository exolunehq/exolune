"""Outils communs de la chaîne des modèles : dossiers des assets et lecture des accesseurs glTF.
L'import des modèles photo Poly Haven, retiré avec eux le 2026-10-30, reste au tag jalon/24-vegetation-detaillee-main."""
from __future__ import annotations
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'assets/foliage/cache'
OUT = ROOT / 'assets/foliage'


def accessor(doc, blob, i):
    a = doc['accessors'][i]
    v = doc['bufferViews'][a['bufferView']]
    types = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = np.dtype(types[a['componentType']])
    off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', dt.itemsize * width)
    arr = np.ndarray((a['count'], width), dtype=dt, buffer=blob, offset=off, strides=(stride, dt.itemsize))
    return arr
