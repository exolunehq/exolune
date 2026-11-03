"""Check the exported game asset contract without rendering or benchmarking."""
from pathlib import Path
import argparse
import io
import json
import struct
import numpy as np
from PIL import Image


def read_glb(path):
    with Path(path).open('rb') as stream:
        magic, version, total = struct.unpack('<4sII', stream.read(12))
        if magic != b'glTF' or version != 2 or total != Path(path).stat().st_size:
            raise ValueError('Invalid GLB container')
        length, kind = struct.unpack('<II', stream.read(8))
        if kind != 0x4E4F534A:
            raise ValueError('Missing glTF JSON chunk')
        document = json.loads(stream.read(length))
        length, kind = struct.unpack('<II', stream.read(8))
        if kind != 0x004E4942:
            raise ValueError('Missing glTF binary chunk')
        return document, stream.read(length)


def array(document, binary, index):
    entry = document['accessors'][index]
    view = document['bufferViews'][entry['bufferView']]
    dtype = np.dtype({5120:'i1', 5121:'u1', 5122:'<i2', 5123:'<u2', 5125:'<u4', 5126:'<f4'}[entry['componentType']])
    width = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4}[entry['type']]
    return np.ndarray((entry['count'], width), dtype=dtype, buffer=binary,
                      offset=view.get('byteOffset', 0) + entry.get('byteOffset', 0),
                      strides=(view.get('byteStride', width*dtype.itemsize), dtype.itemsize))


def check(path, budget=40000, height=8.0):
    doc, binary = read_glb(path)
    triangles = vertices = 0
    leaf_found = wood_found = False
    bounds = [];woody_triangles=[]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            if primitive.get('mode', 4) != 4:
                raise ValueError('Only triangle primitives are accepted')
            attrs = primitive['attributes']
            positions = array(doc, binary, attrs['POSITION'])
            indices = array(doc, binary, primitive['indices']).ravel()
            if not len(indices) or len(indices) % 3 or indices.max() >= len(positions):
                raise ValueError('Empty or invalid triangle indices')
            if not np.isfinite(positions).all():
                raise ValueError('Non-finite positions')
            for key in ['NORMAL', 'TEXCOORD_0', 'TANGENT']:
                if key not in attrs or not np.isfinite(array(doc, binary, attrs[key])).all():
                    raise ValueError('Missing or invalid ' + key)
            triangles += len(indices)//3
            vertices += len(positions)
            bounds.append((positions.min(axis=0), positions.max(axis=0)))
            mat = doc['materials'][primitive['material']]
            if '_LEAF_WEIGHT' in attrs:
                leaf_found = True
                for key in ['_WIND_WEIGHT', '_WIND_PHASE', '_WIND_PIVOT', '_LEAF_PIVOT', '_LEAF_WEIGHT', 'COLOR_0']:
                    if key not in attrs or len(array(doc, binary, attrs[key])) != len(positions) or not np.isfinite(array(doc, binary, attrs[key])).all():
                        raise ValueError('Missing per-vertex leaf data: ' + key)
                for key in ['_WIND_WEIGHT', '_LEAF_WEIGHT']:
                    values = array(doc, binary, attrs[key])
                    if not np.isfinite(values).all() or values.min() < 0 or values.max() > 1:
                        raise ValueError('Invalid wind weight range')
                for name in ['_WIND_PIVOT','_LEAF_PIVOT']:
                    pivot = array(doc, binary, attrs[name])
                    if pivot[:,1].min() < -0.01 or pivot[:,1].max() > height:
                        raise ValueError('Wind pivots must use the glTF Y-up coordinate frame')
                if mat.get('alphaMode') != 'MASK' or not mat.get('doubleSided'):
                    raise ValueError('Leaf cutouts must be masked and double sided')
                texture = doc['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]
                image = doc['images'][texture['source']]
                view = doc['bufferViews'][image['bufferView']]
                encoded = binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
                pixels = np.array(Image.open(io.BytesIO(encoded)).convert('RGBA'))
                if not (pixels[:,:,3].min() < 32 and pixels[:,:,3].max() > 224):
                    raise ValueError('Leaf atlas has no usable transparent cutout')
            else:
                wood_found = True
                woody_triangles.append(positions[indices.reshape(-1,3)])
                if 'normalTexture' not in mat or any(key not in mat['pbrMetallicRoughness'] for key in ['baseColorTexture','metallicRoughnessTexture']):
                    raise ValueError('Wood must retain baked colour, normal and roughness/metallic maps')
    if not leaf_found or not wood_found or len(doc['materials']) != 2:
        raise ValueError('Expected separate wood and foliage with two materials')
    if triangles > budget:
        raise ValueError(f'Triangle budget exceeded: {triangles} > {budget}')
    low = np.min([v[0] for v in bounds], axis=0)
    high = np.max([v[1] for v in bounds], axis=0)
    if abs(float(high[1])-height) > 0.02 or abs(float(low[1])) > 0.02:
        raise ValueError('Asset must have its foot at Y=0 and the requested total height')
    from branch_volume import measure
    volume=measure(np.concatenate(woody_triangles))
    if volume['status']!='pass':raise ValueError('Planar woody master: source volume must be reviewed and regenerated')
    return {'file':str(Path(path).resolve()), 'triangles':triangles, 'vertices':vertices,'woody_volume':volume,
            'materials':len(doc['materials']), 'bytes':Path(path).stat().st_size,
            'bounds_min':low.tolist(), 'bounds_max':high.tolist(),
            'leaf_alpha':'MASK', 'pivot_coordinates':'glTF Y-up', 'status':'pass'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset', type=Path)
    parser.add_argument('--budget', type=int, default=40000)
    parser.add_argument('--height', type=float, default=8.0)
    args = parser.parse_args()
    print(json.dumps(check(args.asset, args.budget, args.height), indent=2))
