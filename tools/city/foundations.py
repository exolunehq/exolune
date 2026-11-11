"""Built supports that earthworks do not replace, in the city ground mesh: steps, cables and the guideway's piers.

Buildings, plazas, field terraces and transport footings stand on graded earth (`grading.py`).
Steps are solid treads on the graded ground: their tops are walkable, their risers are masonry.
Cables are thin steel members between their sampled points. Beyond the city the guideway stands on steel piers:
a column beside the line, set into the ground, an arm over the beam, a hanger and a brace. Risers, cables and piers are
structure:
the walking surface never reads them (`CITYSCN1` version 4 keeps them after the walkable indices).
"""
import math

import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon

CABLE_M = .06           # cable diameter


class Mesh:
    """Vertices shared by two index lists; only `walk` reaches the walking surface."""

    def __init__(self, vertices, walk):
        self.vertices, self.walk, self.structure = vertices, walk, []

    def emit(self, points, normals, uvs, material, walk=False):
        start = len(self.vertices)
        self.vertices.extend([(*p, *n, u, v, material, 1.0) for p, n, (u, v) in zip(points, normals, uvs)])
        target = self.walk if walk else self.structure
        for k in range(1, len(points) - 1):
            target.extend([start, start + k, start + k + 1])

    def face(self, points, facing, material, walk=False):
        """A flat triangle or quad; `facing` orients the normal; UVs project on the dominant axis."""
        p = np.asarray(points, float)
        n = np.cross(p[2] - p[0], p[3] - p[1]) if len(p) == 4 else np.cross(p[1] - p[0], p[2] - p[0])
        n /= max(float(np.linalg.norm(n)), 1e-12)
        if np.dot(n, facing) < 0:
            n = -n
        u, v = [(1, 2), (0, 2), (0, 1)][int(np.argmax(np.abs(n)))]
        self.emit(p, [n] * len(p), [(q[u] * .5, q[v] * .5) for q in p], material, walk)

    def flat(self, shape, z, material, walk=False):
        for tri in constrained_delaunay_triangles(shape).geoms:
            self.face([(x, y, z) for x, y in list(tri.exterior.coords)[:3]], (0, 0, 1), material, walk)

    def walls(self, shape, top, bottom, material):
        """Vertical walls down a convex outline from `top` to `bottom(p)`."""
        coords = list(shape.exterior.coords)[:-1]
        c = np.array([shape.centroid.x, shape.centroid.y])
        for i in range(len(coords)):
            a, b = np.array(coords[i]), np.array(coords[(i + 1) % len(coords)])
            e = b - a
            o = np.array([e[1], -e[0]]) / max(float(np.linalg.norm(e)), 1e-9)
            if np.dot(o, (a + b) / 2 - c) < 0:
                o = -o
            self.face([(*a, bottom(a)), (*b, bottom(b)), (*b, top), (*a, top)], (*o, 0), material)

    def member(self, p0, p1, width, material, sides=6):
        """A round prism along p0-p1; its UVs run along the member."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        axis = p1 - p0
        length = float(np.linalg.norm(axis))
        if length < .02:
            return
        axis /= length
        side = np.cross(axis, (0., 0., 1.)) if abs(axis[2]) < .95 else np.array([1., 0., 0.])
        side /= np.linalg.norm(side)
        up = np.cross(axis, side)
        ring = [(side * math.cos(t) + up * math.sin(t)) for t in np.arange(sides) * math.tau / sides]
        for k in range(sides):
            a, b = ring[k], ring[(k + 1) % sides]
            self.emit([p0 + a * width / 2, p0 + b * width / 2, p1 + b * width / 2, p1 + a * width / 2], [a, b, b, a],
                      [(k / sides, 0), ((k + 1) / sides, 0), ((k + 1) / sides, length * .5), (k / sides, length * .5)], material)


def build(mesh, terrain, foundations, materials, cables=(), piers=()):
    for item in foundations:
        shape, top = Polygon(item['outline']), item['top']
        mesh.flat(shape, top, materials['top'], walk=True)
        mesh.walls(shape, top, lambda p: terrain.sample(*p) - .15, materials['wall'])
    for line in cables:
        for p, q in zip(line, line[1:]):
            mesh.member(p, q, CABLE_M, materials['cable'])
    for p, q, width in piers:
        mesh.member(p, q, width, materials.get('pier', materials['cable']), 12)


if __name__ == '__main__':
    # Self-check on a 6 m slope: a step's top is walkable, its riser reaches below the ground,
    # and a cable is structure only.
    class Slope:
        def sample(self, x, y):
            return 100 - .6 * y
    vertices, walk = [], []
    mesh = Mesh(vertices, walk)
    m = {'top': 31, 'wall': 32, 'cable': 19}
    build(mesh, Slope(), [{'outline': [(-1, 0), (1, 0), (1, .3), (-1, .3)], 'top': 100.12}], m,
          [[(0, 0, 120), (50, 0, 118), (100, 0, 121)]])
    v = np.asarray(vertices)
    tops = v[np.asarray(walk).reshape(-1, 3)][:, :, 2]
    assert np.allclose(tops, 100.12), 'only the tread is walkable'
    risers = v[v[:, 8] == 32]
    assert risers[:, 2].min() < 100 - .6 * .3, 'the riser reaches the ground'
    assert (v[v[:, 8] == 19][:, 2] > 117).all() and len(mesh.structure) > len(walk), 'cables are structure'
    print('foundations self-check passed:', len(vertices), 'vertices,', len(walk) // 3, 'walkable,', len(mesh.structure) // 3, 'structure triangles')
