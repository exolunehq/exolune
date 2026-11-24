"""Cook the reviewed shuttle GLB into the standalone flight packet. Run with Blender Python."""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

from mathutils import Matrix, Quaternion
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'chasseur'), str(HERE.parent / 'navette')]
import paquet_moteur as vsx
import finish_exterior as fittings
import hullgrid
from thrusters import DUCT_DIR

SOURCE_SHA = '0cf43af7664acc6534002f6c66a991fa10ab32a8f441e99ad4394143ca2c1b31'
CLIPS = ('Ailes', 'Train', 'Aerofrein', 'Trappe_Arriere')
CONTROLS = {'Manche': (0, 0, 1), 'Manette_Gaz': (1, 0, 0)}
ROLES = {'NAV_Ecran_Nav': 1, 'NAV_Ecran_Vol': 2, 'NAV_Ecran_Systemes': 3, 'NAV_Tuyere_Coeur': 7}
AXES = np.array(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)), dtype=float)
FPS = 24


def rigid_key(world):
    rotation = Matrix(world[:3,:3].tolist()).to_quaternion().normalized()
    return (*world[:3,3], rotation.x, rotation.y, rotation.z, rotation.w)


def sample(times, values, t, rotation):
    right = int(np.searchsorted(times, t))
    if right == 0 or right == len(times):
        return values[min(right, len(times)-1)]
    a, b = values[right-1], values[right]
    f = float((t-times[right-1])/(times[right]-times[right-1]))
    if rotation:
        qa = Quaternion((a[3], *a[:3]))
        qb = Quaternion((b[3], *b[:3]))
        q = qa.slerp(qb, f)
        return (q.x, q.y, q.z, q.w)
    return a + (b-a)*f


def animation(gltf, data):
    nodes = gltf['nodes']
    parent = {child:i for i,node in enumerate(nodes) for child in node.get('children', [])}
    def world(i):
        return (world(parent[i]) if i in parent else AXES) @ vsx.matrice(nodes[i])
    animations = {clip['name']:clip for clip in gltf['animations']}
    assert set(animations) == set(CLIPS)
    slots = {name:i+1 for i,name in enumerate(CONTROLS)}
    trailer = bytearray(struct.pack('<4sI', b'ANI1', len(CLIPS)))
    next_slot = 16  # poses 1..15 are shared with the legacy ship packets
    animated = {c['target']['node'] for clip in animations.values() for c in clip['channels']}
    for name in CLIPS:
        clip = animations[name]
        channels = {}
        last = 0.0
        for channel in clip['channels']:
            target = channel['target']
            curve = clip['samplers'][channel['sampler']]
            assert curve.get('interpolation','LINEAR') == 'LINEAR' and target['path'] in ('translation','rotation')
            times = vsx.accesseur(gltf,data,curve['input']).ravel()
            values = vsx.accesseur(gltf,data,curve['output'])
            assert np.all(np.diff(times)>0)
            channels.setdefault(target['node'], {})[target['path']] = (times,values)
            last = max(last, float(times[-1]))
        count = round(last*FPS)+1
        trailer.extend(struct.pack('<3I', len(channels), count, FPS))
        for i, curves in sorted(channels.items()):
            node = nodes[i]
            assert 'mesh' in node and node['name'] not in slots
            p = i
            while p in parent:
                p = parent[p]
                assert p not in animated, 'animated parent needs a hierarchical track'
            space = world(parent[i]) if i in parent else AXES
            rest = world(i)
            slots[node['name']] = next_slot
            trailer.extend(struct.pack('<I7f',next_slot,*rigid_key(rest)))
            next_slot += 1
            for frame in range(count):
                pose = node.copy()
                for path, (times,values) in curves.items():
                    pose[path] = sample(times,values,frame/FPS,path=='rotation')
                key = space @ vsx.matrice(pose)
                assert np.allclose(key[:3,:3].T @ key[:3,:3], np.eye(3), atol=.00001)
                trailer.extend(struct.pack('<7f',*rigid_key(key)))
        print(f'{name}: {len(channels)} moving parts, {count} frames')
    assert next_slot-1 <= 96
    return slots, trailer


def exhausts(images):
    grid = hullgrid.HullGrid()
    c0,c1 = grid.col['c0'],grid.col['c1']
    rows = grid.points[c0:c1+1]
    edges = [rows[:,hullgrid.B_CAV0], rows[:,hullgrid.B_CAV1]]
    edges += [.5*(rows[:,top]+rows[:,bottom]) for top,bottom in grid.blade_rows]
    stations = np.linspace(0,1,len(rows))
    result = bytearray()
    for side in (1,-1):
        mirror = np.array((side,1,1))
        axis = -DUCT_DIR*mirror/np.linalg.norm(DUCT_DIR)
        across = np.array((axis[1]*side,-axis[0]*side,0))
        frame = np.stack((across,(0,0,1),axis))
        mouth, radii, depth, image = fittings.chart_from_edges([edge*mirror for edge in edges],frame,stations)
        if image not in images:
            images.append(image)
        result.extend(struct.pack('<16f',*mouth,radii[0],*axis,radii[1],*across,0,images.index(image)+1,depth,0,0))
    return result


def support_boxes(vertex):
    """Conservative rest bounds per rigid part and longitudinal section of the fixed hull."""
    result = []
    for slot in np.unique(vertex[:,14]):
        pts = vertex[vertex[:,14]==slot,:3]
        groups = (pts,) if slot else [pts[np.floor(pts[:,1])==y] for y in np.unique(np.floor(pts[:,1]))]
        for group in groups:
            lo,hi = group.min(0),group.max(0)
            result.append(struct.pack('<I6f',int(slot),*((lo+hi)*.5),*((hi-lo)*.5)))
    return struct.pack('<4sI',b'SUP1',len(result))+b''.join(result)


def cook(source, destination):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Expected the reviewed v9 GLB')
    gltf, data = vsx.lire_glb(source)
    slots, clips = animation(gltf,data)
    # Write atomically. A failed cook must leave the installed transport playable.
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        scratch = Path(tmp)
        core = scratch/'base.vsx'
        vertex, indices = vsx.cuire(source,core,roles=ROLES,pivot_names=tuple(CONTROLS),
                                     control_axes=CONTROLS,rigid_poses=slots)
        assert np.isfinite(vertex).all() and set(slots.values()) <= set(np.unique(vertex[:,14]))
        raw = core.read_bytes()
        _,nv,ni,nd,nm,nimg = struct.unpack_from('<6I',raw,4)
        start = 28+nv*60+ni*4
        draws = np.frombuffer(raw,'<u4',3*nd,start).reshape(-1,3)
        merged = []
        for first,count,material in draws.tolist():
            if merged and material==merged[-1][2]:
                assert first == merged[-1][0]+merged[-1][1]
                merged[-1][1] += count
            else:
                merged.append([first,count,material])
        material = raw[start+nd*12:start+nd*12+nm*96]
        at = start+nd*12+len(material)
        images = []
        for _ in range(nimg):
            size = struct.unpack_from('<I',raw,at+4)[0]+8
            images.append(raw[at:at+size])
            at += size
        controls = raw[at:]
        assert len(controls)==52
        subprocess.run(['python',str(HERE/'flight_displays.py'),str(scratch)],check=True)
        for i,mat in enumerate(gltf['materials']):
            if ROLES.get(mat['name']) in (1,2,3):
                image_id = struct.unpack_from('<i',material,i*96+52)[0]
                png = (scratch/(mat['name']+'.png')).read_bytes()
                images[image_id] = struct.pack('<II',1,len(png))+png
        jets = exhausts(images)
        canopy = fittings.cook_glass(vertex,indices,merged,material,transport=True)
        assert len(images)<=16
        output = scratch/'transport.vsx'
        with output.open('wb') as file:
            file.write(struct.pack('<4s6I',b'VSX1',4,nv,ni,len(merged),nm,len(images)))
            file.write(raw[28:start])
            file.write(np.asarray(merged,'<u4').tobytes())
            file.write(material)
            file.writelines(images)
            file.write(controls)
            file.write(clips)
            file.write(jets)
            file.write(support_boxes(vertex))
            file.write(canopy)
        print('V9 packet',nv,'vertices',ni//3,'triangles',len(merged),'draws',
              hashlib.sha256(output.read_bytes()).hexdigest())
        output.replace(destination)


if __name__=='__main__':
    source, target = sys.argv[sys.argv.index('--')+1:]
    cook(Path(source),Path(target))
