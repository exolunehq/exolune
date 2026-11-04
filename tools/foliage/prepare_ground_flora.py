"""Generate low-poly ground flora with the standard foliage cook."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import bake
from prepare_biomes import write_model
import volume_assets


FLOWERS = {
    'flower_wood_anemone': {'seed': 1763, 'blooms': 5, 'petals': 7, 'height': (.13, .24),
                            'petal': (.018, .010), 'colour': ((214, 198, 155), (251, 245, 224))},
    'flower_wood_violet': {'seed': 8127, 'blooms': 6, 'petals': 5, 'height': (.10, .18),
                           'petal': (.016, .0078), 'colour': ((214, 171, 210), (103, 72, 177))},
}
HERBS = {
    'sorrel_wood_round': dict(kind='sorrel', seed=6117, shoots=6, height=.14, spread=.11),
    'sorrel_wood_spread': dict(kind='sorrel', seed=1159, shoots=8, height=.11, spread=.15),
    'grass_wood_arching': dict(kind='grass', seed=7913, shoots=27, height=.47, spread=.30),
    'grass_meadow_upright': dict(kind='grass', seed=1271, shoots=31, height=.57, spread=.23),
    'fern_wood_arching': dict(kind='fern', seed=4283, shoots=7, height=.49, spread=.43),
    'fern_wood_upright': dict(kind='fern', seed=8779, shoots=8, height=.57, spread=.35),
}
UP = np.array([0., 1., 0.])


class PlantMesh:
    def __init__(self):
        self.vertices, self.indices, self.uvs = [], [], []

    def surface(self, points, faces, band, uv):
        first = len(self.vertices)
        self.vertices.extend(points)
        self.indices.extend(np.array(faces) + first)
        self.uvs.extend(((band + .08 + .84*u) / 4, .08 + .84*v) for u, v in uv)

    def stem(self, base, tip):
        points = []
        for row, center in enumerate((base, (base+tip)*.5, tip)):
            radius = .0026 - row*.0005
            for i in range(5):
                angle = math.tau*i/5
                points.append(center + radius*np.array([math.cos(angle), 0, math.sin(angle)]))
        faces = []
        for row in range(2):
            for i in range(5):
                a, b = row*5+i, row*5+(i+1)%5
                faces.extend([(a,b+5,b), (a,a+5,b+5)])
        self.surface(points, faces, 0, [(.5,row/2) for row in range(3) for _ in range(5)])

    def blade(self, base, direction, side, normal, length, width, arch, band, lobes):
        points, uv = [], []
        for row, t in enumerate((0., .42, .77, 1.)):
            for col, across in enumerate((-1., 0., 1.)):
                edge = lobes[row]
                points.append(base + direction*length*t + side*across*width*edge
                              + normal*(arch*math.sin(t*math.pi*.75) - abs(across)*width*.23*edge))
                uv.append((col*.5,t))
        faces = []
        for row in range(3):
            for col in range(2):
                a = row*3+col
                faces.extend([(a,a+1,a+4), (a,a+4,a+3)])
        self.surface(points, faces, band, uv)

    def part(self):
        points = np.asarray(self.vertices)
        faces = np.asarray(self.indices)
        a,b,c = points[faces[:,0]],points[faces[:,1]],points[faces[:,2]]
        cross = np.cross(b-a,c-a)
        normals = np.zeros_like(points)
        for corner in range(3):
            np.add.at(normals,faces[:,corner],cross)
        if np.any(np.linalg.norm(normals,axis=1)<1e-10):
            raise ValueError('Degenerate plant surface')
        return (points,normals,np.asarray(self.uvs),faces,0)


def direction(angle):
    return np.array([math.cos(angle),0,math.sin(angle)])


def colony(profile):
    rng = np.random.default_rng(profile['seed'])
    mesh = PlantMesh()
    for i in range(profile['blooms']):
        angle = i*2.399963 + rng.uniform(-.2,.2)
        radial = direction(angle)
        base = radial * rng.uniform(.028,.092)
        tip = base + UP*rng.uniform(*profile['height']) + radial*rng.uniform(.018,.055)
        mesh.stem(base, tip)
        for j in range(3):
            heading = angle+j*math.tau/3
            way = np.array([math.cos(heading), .37, math.sin(heading)])
            side = np.cross(way,UP)
            mesh.blade(base+UP*(.024+.012*j),way,side,UP,rng.uniform(.035,.065),.017,.012,1,
                       [.08,1,.70,.06])
        normal = UP + radial*rng.uniform(.25,.62)
        normal /= np.linalg.norm(normal)
        x = np.cross(normal,radial)
        x /= np.linalg.norm(x)
        z = np.cross(x,normal)
        phase = rng.uniform(0,math.tau)
        for j in range(profile['petals']):
            a = phase+j*math.tau/profile['petals']
            petal_dir = x*math.cos(a)+z*math.sin(a)
            length,width = profile['petal']
            if profile['petals']==5:
                length*=1.22 if j==0 else .90 if j in (2,3) else 1.0
                width*=1.14 if j==0 else 1.0
            mesh.blade(tip+petal_dir*.0018,petal_dir,np.cross(petal_dir,normal),normal,
                       length*rng.uniform(.83,1.19),width,.0036,2,[.15,.80,1,.22])
        rim = [tip+.004*(x*math.cos(j*math.tau/7)+z*math.sin(j*math.tau/7)) for j in range(7)]
        mesh.surface([tip+normal*.004,*rim],[(0,(j+1)%7+1,j+1) for j in range(7)],
                     3, [(.5,.75)]+[(.5,.25)]*7)
    return mesh.part()


def ground_cluster(profile):
    mesh = PlantMesh()
    rng = np.random.default_rng(profile['seed'])
    for shoot in range(profile['shoots']):
        angle = shoot*2.399963+rng.uniform(-.18,.18)
        radial = direction(angle)
        side = np.cross(radial,UP)
        height = profile['height']*rng.uniform(.63,1.07)
        reach = profile['spread']*rng.uniform(.67,1.13)
        foot = radial*rng.uniform(.006,.042)
        kind = profile['kind']
        band = 1+shoot%3
        if kind=='sorrel':
            tip = foot + UP*height + radial*reach*.55
            mesh.stem(foot,tip)
            for leaf in range(3):
                way = direction(angle+leaf*math.tau/3)
                mesh.blade(tip,way,np.cross(way,UP),UP,reach*.64,reach*.26,.009,band,[.06,1,.84,.07])
        elif kind=='grass':
            path = radial*reach + UP*height*.65
            mesh.blade(foot,path,side,UP,1.0,rng.uniform(.006,.013),height*.38,band,[.37,1,.65,.04])
        else:
            def frond(t):
                return foot + radial*(reach*t) + UP*height*(1.8*t-.85*t*t)
            spine = [frond(j/8)+side*sign*(.0034-.0024*j/8)
                     for j in range(9) for sign in (-1,1)]
            faces = [face for j in range(8) for face in ((2*j,2*j+1,2*j+3),(2*j,2*j+3,2*j+2))]
            mesh.surface(spine,faces,0,[(col,j/8) for j in range(9) for col in (0,1)])
            for j in range(9):
                t = (j+1)/10
                length = reach*(.30+.39*math.sin(math.pi*t))*(1-.65*t)
                for sign in (-1,1):
                    way = side*sign*.78 + radial*.55 + UP*.18
                    mesh.blade(frond(t),way,np.cross(way,UP),UP,length,length*.14,.014*(1-t),
                               band,[.08,.85,.63,.05])
    return mesh.part()


def maps(profile):
    colors = [((48,65,23),(91,112,39)),((37,64,21),(87,116,43)),
              profile.get('colour',((39,62,25),(105,139,61))),
              ((157,83,24),(249,199,66)) if 'petals' in profile else ((44,65,20),(121,141,65))]
    u = np.linspace(0,1,64)[None,:,None]
    v = np.linspace(0,1,256)[:,None,None]
    texture = np.zeros((256,256,4),np.uint8)
    texture[:,:,3] = 255
    for i,(low,high) in enumerate(colors):
        grain = .93 + .07*np.cos((u-.5)*np.pi)**4 + .025*np.sin(u*38+v*12)
        shade = (np.asarray(low)*(1-v)+np.asarray(high)*v)*grain
        texture[:,i*64:(i+1)*64,:3] = shade.clip(0,255).astype('u1')
    return Image.fromarray(texture), Image.new('RGBA',(2,2),(128,128,255,255)), Image.new('RGBA',(2,2),(255,215,128,255))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--group', choices=['flowers','herbs','all'], default='all')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.drive.lower() != 'e:':
        raise ValueError('Ground flora belongs on E:')
    out.mkdir(parents=True,exist_ok=False)
    bake.OUT = volume_assets.DEST = out
    report = {}
    profiles = FLOWERS if args.group=='flowers' else HERBS if args.group=='herbs' else FLOWERS|HERBS
    for name, profile in profiles.items():
        part = colony(profile) if 'petals' in profile else ground_cluster(profile)
        color, normal, mask = maps(profile)
        write_model(out,name,[part],[color],[normal],[mask],tile=256,origin=(0,0,0))
        volume_assets.SPEC[name] = {'leaf':0}
        loaded = bake.load(name)
        bake.volume(name,*loaded,64)
        bake.impostor(name,*loaded)
        volume_assets.bake_light(name)
        report[name] = {'profile':profile,'triangles':len(part[3]),'leaf_mask':1,
                        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (out/name).glob('*.bin')}}
    (out/'ground-flora-report.json').write_text(json.dumps(
        {'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'models':report},indent=2)+'\n')


if __name__ == '__main__':
    main()
