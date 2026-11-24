"""Landing gear of the Navette AAA: three retractable legs and the liners of their wells.

    build(mats, grid) -> the gear's objects, keyed on the clip "Train" (grid: hullgrid.HullGrid)
    self_check(objs)  -> dict of measured facts; raises AssertionError on a broken invariant

Frame: metres, nose -Y, up +Z, port +X. At rest (u = 0) the gear is down: the three pad soles rest
on GROUND, the door leaves the legs pass through are open and the others are shut. At u = 1 the
whole gear lies inside the hull, each pad level just above its closed doors, and the twelve gear
doors are shut flush.

Every part is generated, never booleaned:
  lathe()    turned parts from an (r, z) profile whose corners are already chamfered
  tube()     hoses along a spline
  lattice()  forged and machined blocks: boundary quads of a hexahedral node lattice
  bevel()    real chamfers on every edge sharper than BEVEL_ANGLE (bmesh, on a clean quad cage)
  loft()     stacked rings closed by grid caps (pads, plates, liners)
Shading is face-weighted: custom normals follow the large faces, so chamfers carry the gradient and
flats stay flat. An edge left sharper than SHARP_ANGLE is split, never smeared.

Each leg is a twin oleo strut hung on a trunnion along its fold axis. It swings about that axis and
stows, its oleo shortening by Leg.c on the way. Each rigid part is its own object:
  <leg>_Jambe        trunnion, barrels, gland nuts, bridge, retraction horn, harness
  <leg>_Coulisse     pistons, crosshead, fork and pitch pin
  <leg>_Compas_Haut, <leg>_Compas_Bas   torque links, folding beside one strut, in the struts' plane
  <leg>_Verin, <leg>_Tige   the retraction actuator's cylinder (with its hoses) and rod
  <leg>_Patin        the pad and its gimbal; it stays level
  <leg>_Fixe         static: trunnion bearings, the actuator's clevis and manifold
Leg.poses(u) solves every pin exactly. A leg is drawn in its leg frame: origin on the trunnion
axis, +Z down the strut to the ankle at rest, X along the fold axis towards the torque links, +Y
on the strut's underside, which faces down once stowed. Baies_Trains (the well liners) is static.

The nose leg rakes forward from a trunnion at the back of its well and folds forwards, level over
its low pad. The main legs hang at the front of the belly wells on a fold axis canted MAIN_CANT
above the horizontal, which splays them outboard, and fold aft over their pads. The hull is never
cut here: the wells are the hull's own openings (hullgrid), closed by the doors of panels.py, which
build() keys on the same clip.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import anim
import hullgrid as hg
import materials as nav_materials
import meshkit
import panels
from surface import T2

GROUND = -0.3665 * 7.2                     # -2.6388 m
COLLECTION = "04_Trains_Atterrissage"
CLIP = "Train"
BEVEL_ANGLE = math.radians(40.0)           # a cage edge sharper than this gets a chamfer
SHARP_ANGLE = math.radians(50.0)           # an edge still sharper than this splits the normals
TRI_BUDGET = 80000


# =============================================================================================
# Kernel
# =============================================================================================
def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def frame(origin, z, x=(1.0, 0.0, 0.0)):
    """4x4 matrix: local Z along z, local X as close to x as a right angle allows."""
    z = unit(z)
    x = np.asarray(x, dtype=float)
    x = unit(x - z * (x @ z))
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, origin
    return m


def shift(x=0.0, y=0.0, z=0.0):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


AXIS_X = frame((0, 0, 0), (1, 0, 0), (0, 1, 0))       # lays a part's Z along X
AXIS_Y = frame((0, 0, 0), (0, 1, 0), (0, 0, 1))       # lays a part's Z along Y


def newell(p):
    """Area vector of a polygon (k, 3): its normal times its area."""
    return 0.5 * np.cross(p, np.roll(p, -1, axis=0)).sum(axis=0)


class Part:
    """A piece of mesh in its own frame: vertices, faces, optional per-corner UVs and materials."""

    def __init__(self, v, f, uv=None, m=None):
        self.v = np.asarray(v, dtype=float).reshape(-1, 3)
        self.f = [tuple(int(i) for i in face) for face in f]
        self.uv = uv                       # list of (k, 2) arrays, one per face; None = box projection
        self.m = m                         # one key, or a list with one key per face; None = caller's


def box_uv(v, faces):
    """Box projection in metres: each face takes the two axes its normal is not along."""
    out = []
    for face in faces:
        p = v[list(face)]
        a = int(np.argmax(np.abs(newell(p))))
        out.append(p[:, [(a + 1) % 3, (a + 2) % 3]])
    return out


class Geo:
    """Accumulates parts into one mesh."""

    def __init__(self):
        self.v, self.f, self.uv, self.m, self.n = [], [], [], [], 0
        self.vn = {}                       # vertex index -> a normal that overrides the computed one

    def add(self, part, mat=None, xf=None, normals=None):
        """normals: {vertex index of the part: normal}, kept as given instead of the face-weighted one."""
        v, f = part.v, part.f
        uv = part.uv if part.uv is not None else box_uv(v, f)
        if xf is not None:
            v = v @ xf[:3, :3].T + xf[:3, 3]
            if np.linalg.det(xf[:3, :3]) < 0.0:
                f = [face[::-1] for face in f]
                uv = [u[::-1] for u in uv]
        m = part.m if part.m is not None else mat
        self.m += list(m) if isinstance(m, (list, tuple)) else [m] * len(f)
        self.f += [tuple(i + self.n for i in face) for face in f]
        self.uv += [np.asarray(u, dtype=float) for u in uv]
        for k, nrm in (normals or {}).items():
            self.vn[self.n + int(k)] = np.asarray(nrm, dtype=float) if xf is None else xf[:3, :3] @ nrm
        self.v.append(v)
        self.n += len(v)
        return self

    def merge(self, other):
        self.vn.update({k + self.n: nrm for k, nrm in other.vn.items()})
        self.f += [tuple(i + self.n for i in face) for face in other.f]
        self.v += other.v
        self.uv += other.uv
        self.m += other.m
        self.n += other.n
        return self

    def mirrored(self):
        """The same mesh across x = 0, wound outward again."""
        g = Geo()
        g.v = [v * np.array([-1.0, 1.0, 1.0]) for v in self.v]
        g.f = [face[::-1] for face in self.f]
        g.uv = [u[::-1] * np.array([-1.0, 1.0]) for u in self.uv]
        g.m, g.n = list(self.m), self.n
        g.vn = {k: nrm * np.array([-1.0, 1.0, 1.0]) for k, nrm in self.vn.items()}
        return g


# ---- 2D outlines ----------------------------------------------------------------------------
def rounded(pts, r, segs=1, cells=1):
    """Open 2D polyline through corner points, its interior corners rounded.

    r, segs: one value per interior corner or a scalar; segs = 1 is a chamfer, r = 0 keeps the
    corner. cells: number of cells along each straight (one value per straight or a scalar).
    """
    pts = np.asarray(pts, dtype=float)
    k = len(pts)
    r = np.broadcast_to(np.asarray(r, dtype=float), (k - 2,))
    segs = np.broadcast_to(np.asarray(segs, dtype=int), (k - 2,))
    cells = np.broadcast_to(np.asarray(cells, dtype=int), (k - 1,))
    arcs = [pts[:1]]
    for c in range(1, k - 1):
        p0, p1, p2 = pts[c - 1], pts[c], pts[c + 1]
        u_in, u_out = p1 - p0, p2 - p1
        l_in, l_out = np.linalg.norm(u_in), np.linalg.norm(u_out)
        u_in, u_out = u_in / l_in, u_out / l_out
        cross = u_in[0] * u_out[1] - u_in[1] * u_out[0]
        phi = math.atan2(abs(cross), float(u_in @ u_out))
        if r[c - 1] <= 0.0 or phi < 1e-6:
            arcs.append(p1[None, :])
            continue
        d = min(r[c - 1] * math.tan(0.5 * phi), 0.48 * l_in, 0.48 * l_out)
        rad = d / math.tan(0.5 * phi)
        side = 1.0 if cross > 0.0 else -1.0
        a = p1 - u_in * d
        centre = a + rad * side * np.array([-u_in[1], u_in[0]])
        start = math.atan2(a[1] - centre[1], a[0] - centre[0])
        ang = start + side * np.linspace(0.0, phi, segs[c - 1] + 1)
        arcs.append(centre + rad * np.stack([np.cos(ang), np.sin(ang)], axis=1))
    arcs.append(pts[-1:])
    out = [arcs[0]]
    for c in range(k - 1):
        a, b = arcs[c][-1], arcs[c + 1][0]
        n = cells[c]
        if n > 1:
            out.append(a + (b - a) * np.linspace(0.0, 1.0, n + 1)[1:-1, None])
        if n > 0 or np.linalg.norm(b - a) > 1e-9:
            out.append(arcs[c + 1])
        else:
            out.append(arcs[c + 1][1:])
    return np.vstack(out)


def rrect(hx, hy, r, fx=(), fy=(), na=4):
    """Closed rounded rectangle, counter-clockwise from the middle of the (-x, -y) corner.

    fx, fy: fractions in (0, 1) dividing the straight parts of the x and y sides; na: segments per
    quarter arc (even). A side whose straight part vanishes (r equal to the half size) has no
    straight cell. Returns (points (n, 2), a, b): a and b are the cell counts of the grid cap.
    """
    r = min(r, hx, hy)
    sx, sy = hx - r, hy - r
    quarter = lambda cx, cy, a0: [(cx + r * math.cos(a0 + q * 0.5 * math.pi / na),
                                   cy + r * math.sin(a0 + q * 0.5 * math.pi / na)) for q in range(na + 1)]
    corners = [quarter(sx, -sy, -0.5 * math.pi), quarter(sx, sy, 0.0),
               quarter(-sx, sy, 0.5 * math.pi), quarter(-sx, -sy, math.pi)]
    straights = [(sx > 1e-9, fx, (-sx, -hy), (sx, -hy)), (sy > 1e-9, fy, (hx, -sy), (hx, sy)),
                 (sx > 1e-9, fx, (sx, hy), (-sx, hy)), (sy > 1e-9, fy, (-hx, sy), (-hx, -sy))]
    pts = []
    half = na // 2
    pts += quarter(-sx, -sy, math.pi)[half:-1]                 # second half of the starting corner
    for k in range(4):
        has, fr, p, q = straights[k]
        p, q = np.array(p), np.array(q)
        if has:
            pts.append(tuple(p))
            pts += [tuple(p + (q - p) * f) for f in fr]
        pts += corners[k][:-1] if k < 3 else corners[k][:half]
    a = na + (len(fx) + 1 if sx > 1e-9 else 0)
    b = na + (len(fy) + 1 if sy > 1e-9 else 0)
    pts = np.array(pts)
    assert len(pts) == 2 * (a + b), (len(pts), a, b)
    return pts, a, b


# ---- caps -----------------------------------------------------------------------------------
def cap_grid(v, ring, a, b, flip=False):
    """Quads closing a ring of 2 (a + b) vertices that starts on a grid corner.

    Returns (new vertices, faces). Faces run with the ring (normal by the right-hand rule) unless
    flip. Inner nodes come from a Coons patch of the four sides.
    """
    ring = list(ring)
    assert len(ring) == 2 * (a + b), (len(ring), a, b)
    p = np.asarray(v, dtype=float)[ring]
    bottom, right = p[:a + 1], p[a:a + b + 1]
    top, left = p[a + b:2 * a + b + 1][::-1], np.vstack([p[2 * a + b:], p[:1]])[::-1]
    idx = -np.ones((a + 1, b + 1), dtype=np.int64)
    idx[:, 0] = ring[:a + 1]
    idx[a, :] = ring[a:a + b + 1]
    idx[:, b] = ring[a + b:2 * a + b + 1][::-1]
    idx[0, :] = (ring[2 * a + b:] + ring[:1])[::-1]
    new = []
    base = len(v)
    for i in range(1, a):
        for j in range(1, b):
            u, w = i / a, j / b
            q = ((1 - w) * bottom[i] + w * top[i] + (1 - u) * left[j] + u * right[j]
                 - ((1 - u) * (1 - w) * bottom[0] + u * (1 - w) * bottom[a] + (1 - u) * w * top[0] + u * w * top[a]))
            idx[i, j] = base + len(new)
            new.append(q)
    faces = []
    for i in range(a):
        for j in range(b):
            quad = (idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1])
            faces.append(quad[::-1] if flip else quad)
    return np.array(new).reshape(-1, 3), faces


def cap_strip(ring, flip=False):
    """Quads across an even ring: the cheap closure of a face nobody sees."""
    n = len(ring)
    faces = [(ring[i], ring[i + 1], ring[n - 2 - i], ring[n - 1 - i]) for i in range(n // 2 - 1)]
    return [face[::-1] for face in faces] if flip else faces


def _close(v, faces, uv, ring, kind, flip, a=None, b=None):
    """Append a cap to (v, faces, uv); the cap's UVs are a planar projection."""
    if kind is None:
        return v
    if kind == "strip":
        new_faces = cap_strip(list(ring), flip)
    else:
        n = len(ring)
        extra, new_faces = cap_grid(v, ring, a or n // 4, b or n // 4, flip)
        if len(extra):
            v = np.vstack([v, extra])
    faces += new_faces
    uv += box_uv(v, new_faces)
    return v


# ---- generators -----------------------------------------------------------------------------
def lathe(profile, n, caps=(None, None), phase=0.0, mats=None):
    """Turned part about +Z from an (r, z) profile; run the profile with z rising on outer walls.

    caps: None (an end buried in another part stays open), 'grid' (n divisible by 4) or 'strip'.
    mats: one key per profile segment; a cap takes its neighbour's.
    """
    prof = np.asarray(profile, dtype=float)
    k = len(prof)
    ang = phase + 2.0 * math.pi * np.arange(n) / n
    v = np.stack([prof[:, None, 0] * np.cos(ang)[None, :], prof[:, None, 0] * np.sin(ang)[None, :],
                  np.repeat(prof[:, None, 1], n, axis=1)], axis=-1).reshape(-1, 3)
    r_ref = float(prof[:, 0].max())
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))])
    faces, uv = [], []
    for ka in range(k - 1):
        kb = ka + 1
        for i in range(n):
            j = (i + 1) % n
            faces.append((ka * n + i, ka * n + j, kb * n + j, kb * n + i))
            u0, u1 = i / n * 2.0 * math.pi * r_ref, (i + 1) / n * 2.0 * math.pi * r_ref
            uv.append(np.array([(u0, along[ka]), (u1, along[ka]), (u1, along[ka + 1]), (u0, along[ka + 1])]))
    m = [key for key in mats for _ in range(n)] if mats is not None else None
    for ring, kind, flip, key in ((range(n), caps[0], True, 0), (range((k - 1) * n, k * n), caps[1], False, -1)):
        before = len(faces)
        v = _close(v, faces, uv, ring, kind, flip)
        if m is not None:
            m += [mats[key]] * (len(faces) - before)
    return Part(v, faces, uv, m)


def spline(points, per=6):
    """Catmull-Rom curve through the points, `per` samples per span."""
    p = np.asarray(points, dtype=float)
    p = np.vstack([2.0 * p[0] - p[1], p, 2.0 * p[-1] - p[-2]])
    out = []
    for k in range(1, len(p) - 2):
        u = np.linspace(0.0, 1.0, per, endpoint=False)[:, None]
        out.append(0.5 * ((2.0 * p[k]) + (-p[k - 1] + p[k + 1]) * u
                          + (2.0 * p[k - 1] - 5.0 * p[k] + 4.0 * p[k + 1] - p[k + 2]) * u * u
                          + (-p[k - 1] + 3.0 * p[k] - 3.0 * p[k + 1] + p[k + 2]) * u ** 3))
    out.append(p[-2][None, :])
    return np.vstack(out)


def tube(path, r, n=8):
    """Round hose along a polyline (use spline() first); frames by parallel transport.

    Both ends stay open: a hose always ends inside a ferrule or a block."""
    p = np.asarray(path, dtype=float)
    m = len(p)
    tan = np.gradient(p, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(tan[0], (0.0, 0.0, 1.0))
    if np.linalg.norm(side) < 0.2:
        side = np.cross(tan[0], (1.0, 0.0, 0.0))
    side = unit(side)
    ang = 2.0 * math.pi * np.arange(n) / n
    v, along = [], 0.0
    faces, uv = [], []
    for k in range(m):
        if k:
            side = unit(side - tan[k] * (side @ tan[k]))
            step = float(np.linalg.norm(p[k] - p[k - 1]))
            for i in range(n):
                j = (i + 1) % n
                faces.append(((k - 1) * n + i, (k - 1) * n + j, k * n + j, k * n + i))
                u0, u1 = i / n * 2.0 * math.pi * r, (i + 1) / n * 2.0 * math.pi * r
                uv.append(np.array([(u0, along), (u1, along), (u1, along + step), (u0, along + step)]))
            along += step
        up = np.cross(tan[k], side)
        v.append(p[k] + r * (np.cos(ang)[:, None] * side + np.sin(ang)[:, None] * up))
    return Part(np.vstack(v), faces, uv)


def loft(rings, caps=(None, None), grid=None, mats=None):
    """Quads between stacked closed rings (k, n, 3), each running counter-clockwise seen from
    the side the stack grows to. grid = (a, b) of the caps; mats = one key per band (+ per cap)."""
    rings = np.asarray(rings, dtype=float)
    k, n = rings.shape[:2]
    v = rings.reshape(-1, 3)
    faces, uv, m = [], [], []
    for ka in range(k - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((ka * n + i, ka * n + j, (ka + 1) * n + j, (ka + 1) * n + i))
        if mats is not None:
            m += [mats[ka]] * n
    uv += box_uv(v, faces)
    a, b = grid if grid else (n // 4, n // 4)
    for which, ring, flip in ((0, range(n), True), (1, range((k - 1) * n, k * n), False)):
        before = len(faces)
        v = _close(v, faces, uv, ring, caps[which], flip, a, b)
        if mats is not None:
            m += [mats[0] if which == 0 else mats[k - 2]] * (len(faces) - before)
    return Part(v, faces, uv, m if mats is not None else None)


def lattice(nodes, solid=None):
    """Boundary quads of a hexahedral lattice: nodes (I, J, K, 3), solid (I-1, J-1, K-1) cells."""
    nodes = np.asarray(nodes, dtype=float)
    ni, nj, nk = nodes.shape[:3]
    if solid is None:
        solid = np.ones((ni - 1, nj - 1, nk - 1), dtype=bool)
    solid = np.asarray(solid, dtype=bool)
    pad = np.pad(solid, 1)
    idx = np.arange(ni * nj * nk).reshape(ni, nj, nk)
    faces = []
    for i, j, k in zip(*np.nonzero(solid)):
        c = idx[i:i + 2, j:j + 2, k:k + 2]
        sides = (((0, 1, 1), (c[0, 0, 0], c[0, 0, 1], c[0, 1, 1], c[0, 1, 0])),
                 ((2, 1, 1), (c[1, 0, 0], c[1, 1, 0], c[1, 1, 1], c[1, 0, 1])),
                 ((1, 0, 1), (c[0, 0, 0], c[1, 0, 0], c[1, 0, 1], c[0, 0, 1])),
                 ((1, 2, 1), (c[0, 1, 0], c[0, 1, 1], c[1, 1, 1], c[1, 1, 0])),
                 ((1, 1, 0), (c[0, 0, 0], c[0, 1, 0], c[1, 1, 0], c[1, 0, 0])),
                 ((1, 1, 2), (c[0, 0, 1], c[1, 0, 1], c[1, 1, 1], c[0, 1, 1])))
        for (di, dj, dk), quad in sides:
            if not pad[i + di, j + dj, k + dk]:
                faces.append(quad)
    used = np.unique(np.array(faces))
    remap = -np.ones(ni * nj * nk, dtype=np.int64)
    remap[used] = np.arange(len(used))
    v = nodes.reshape(-1, 3)[used]
    faces = [tuple(remap[list(q)]) for q in faces]
    if sum(float(np.dot(v[q[0]], newell(v[list(q)]))) for q in faces) < 0.0:   # left-handed lattice
        faces = [q[::-1] for q in faces]
    return Part(v, faces)


def bevel(part, width, segs=1, angle=BEVEL_ANGLE):
    """Chamfer every edge of the part sharper than `angle`. Materials are kept per face."""
    bm = bmesh.new()
    verts = [bm.verts.new(tuple(p)) for p in part.v]
    per_face = isinstance(part.m, (list, tuple))
    keys = list(dict.fromkeys(part.m)) if per_face else []
    for n, face in enumerate(part.f):
        f = bm.faces.new([verts[i] for i in face])
        if per_face:
            f.material_index = keys.index(part.m[n])
    bm.normal_update()
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle() > angle]
    bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type="OFFSET", segments=segs, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    big = [f for f in bm.faces if len(f.verts) > 4]
    if big:
        bmesh.ops.triangulate(bm, faces=big)
    bm.verts.index_update()
    out = Part([tuple(vt.co) for vt in bm.verts], [[vt.index for vt in f.verts] for f in bm.faces],
               m=[keys[f.material_index] for f in bm.faces] if per_face else part.m)
    bm.free()
    return out


def box(sx, sy, sz, chamfer=0.003, segs=1):
    """Chamfered box centred on the origin."""
    g = np.stack(np.meshgrid([-0.5 * sx, 0.5 * sx], [-0.5 * sy, 0.5 * sy], [-0.5 * sz, 0.5 * sz], indexing="ij"), axis=-1)
    return bevel(lattice(g), chamfer, segs) if chamfer else lattice(g)


# =============================================================================================
# Shading, objects, materials
# =============================================================================================
def corner_normals(v, faces, power=3.0, sharp=SHARP_ANGLE):
    """Face-weighted normal of every face corner, split across edges sharper than `sharp`.

    A corner's normal is the mean of the faces around its vertex that it reaches without crossing
    a sharp edge, weighted by area ** power and by the corner angle: large flats win.
    """
    # ponytail: a Python loop per vertex, a few seconds for the gear's 80 k triangles; vectorise it
    # with numpy if the budget grows tenfold.
    fn = np.array([newell(v[list(f)]) for f in faces])
    area = np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(area, 1e-30)[:, None]
    edge_faces = {}
    for fi, f in enumerate(faces):
        for a, b in zip(f, f[1:] + f[:1]):
            edge_faces.setdefault((a, b) if a < b else (b, a), []).append(fi)
    cos_sharp = math.cos(sharp)
    smooth = {e for e, fs in edge_faces.items() if len(fs) == 2 and float(fn[fs[0]] @ fn[fs[1]]) > cos_sharp}
    start = np.concatenate([[0], np.cumsum([len(f) for f in faces])])
    corners = {}
    for fi, f in enumerate(faces):
        for ci, vi in enumerate(f):
            corners.setdefault(vi, []).append((fi, ci))
    out = np.zeros((start[-1], 3))
    for vi, items in corners.items():
        parent = list(range(len(items)))

        def root(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        seen = {}
        weights = []
        for n, (fi, ci) in enumerate(items):
            f = faces[fi]
            prev, nxt = f[ci - 1], f[(ci + 1) % len(f)]
            e0, e1 = v[prev] - v[vi], v[nxt] - v[vi]
            cosang = float(e0 @ e1) / max(float(np.linalg.norm(e0) * np.linalg.norm(e1)), 1e-30)
            weights.append(math.acos(max(-1.0, min(1.0, cosang))))
            for w in (prev, nxt):
                e = (vi, w) if vi < w else (w, vi)
                if e in smooth:
                    if e in seen:
                        parent[root(n)] = root(seen[e])
                    else:
                        seen[e] = n
        groups = {}
        for n in range(len(items)):
            groups.setdefault(root(n), []).append(n)
        for members in groups.values():
            top = max(area[items[n][0]] for n in members)
            acc = np.zeros(3)
            for n in members:
                fi = items[n][0]
                acc += fn[fi] * (area[fi] / top) ** power * weights[n]
            length = np.linalg.norm(acc)
            acc = acc / length if length > 1e-12 else fn[items[members[0]][0]]
            for n in members:
                fi, ci = items[n]
                out[start[fi] + ci] = acc
    return out


def to_object(name, geo, mats, origin=None):
    """Mesh object from a Geo: material slots, per-corner UVs in metres, custom normals.

    origin: world point the object's origin sits on (a moving part's pivot); the mesh stays put.
    """
    v = np.vstack(geo.v)
    origin = np.zeros(3) if origin is None else np.asarray(origin, dtype=float)
    keys = list(dict.fromkeys(geo.m))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in v - origin], [], geo.f)
    for key in keys:
        me.materials.append(mats[key])
    me.polygons.foreach_set("material_index", np.array([keys.index(k) for k in geo.m], dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    layer = me.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", np.vstack(geo.uv).astype(np.float32).ravel())
    me.update()
    normals = corner_normals(v, geo.f)
    if geo.vn:
        start = 0
        for f in geo.f:
            for ci, vi in enumerate(f):
                if vi in geo.vn:
                    normals[start + ci] = geo.vn[vi]
            start += len(f)
    me.normals_split_custom_set([tuple(n) for n in normals])
    obj = bpy.data.objects.new(name, me)
    meshkit.collection(COLLECTION).objects.link(obj)
    obj.matrix_world = Matrix.Translation(tuple(origin))   # read at once by anim.bake: no depsgraph update
    return obj


def gear_materials(mats):
    """The gear's own materials (NAV_Train_*), added to a copy of the caller's library."""
    out = dict(mats or {})

    def get(key, name, *args, brushed=False, **kwargs):
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = nav_materials.principled(name, *args, **kwargs)
            if brushed:                    # the hull metals' own micro-surface maps; UVs are in metres
                nav_materials.textured(mat, "metal_brushed_normal.png", "metal_brushed_roughness.png", tiles=4.0,
                                       strength=0.25)
        out[key] = mat

    get("gun", "NAV_Train_Gunmetal", (0.10, 0.11, 0.12), 0.32, 0.92, brushed=True)
    get("cast", "NAV_Train_Titane_Sombre", (0.23, 0.24, 0.26), 0.34, 1.0, brushed=True)
    get("ti", "NAV_Train_Titane_Brosse", (0.60, 0.59, 0.56), 0.30, 1.0, brushed=True)
    get("chrome", "NAV_Train_Chrome", (0.90, 0.91, 0.92), 0.05, 1.0)
    get("rubber", "NAV_Train_Caoutchouc", (0.022, 0.022, 0.024), 0.82, 0.0)
    get("panel", "NAV_Train_Panneau_Sombre", (0.05, 0.065, 0.08), 0.46, 0.75)
    get("braid", "NAV_Train_Tresse_Inox", (0.36, 0.37, 0.38), 0.42, 0.95)
    get("bay", "NAV_Train_Baie", (0.045, 0.05, 0.055), 0.62, 0.55, brushed=True)
    get("glow", "NAV_Train_Lumiere_Sarcelle", (0.05, 0.55, 0.62), 0.30, emit=(0.05, 0.55, 0.62), emit_strength=3.0)
    if "white" not in out:
        get("white", "NAV_Train_Email_Blanc", (0.90, 0.89, 0.86), 0.24, 0.0, coat=0.5)
    out.setdefault("belly", out["white"])
    return out


# =============================================================================================
# Mechanical primitives
# =============================================================================================
def tip_rows(r, steps=2):
    """(rise, half width) rows of a round end above its pin; the end is flat across the top."""
    return [(r * math.sin(math.pi * (k + 1) / (2 * steps + 1)), r * math.cos(math.pi * (k + 1) / (2 * steps + 1)))
            for k in range(steps)]


def bracket(ears, w0, pin_h, r, base=None, steps=2, chamfer=0.003, segs=1):
    """Ears standing along +Z around a pin along Y at height pin_h, on an optional base plate.

    ears: (y0, y1) spans; w0: half width of an ear at its root; base: (half_x, y0, y1, thickness),
    the plate's top is the ears' root. Without a base the root (z = 0) is meant to be buried.
    """
    t = base[3] if base else 0.0
    rows = ([(0.0, w0)] if base else []) + [(t, w0), (pin_h, r)] + [(pin_h + dz, w) for dz, w in tip_rows(r, steps)]
    ys = sorted({y for span in ears for y in span} | ({base[1], base[2]} if base else set()))
    nodes = np.zeros((4 if base else 2, len(ys), len(rows), 3))
    for k, (z, w) in enumerate(rows):
        for i, x in enumerate([-base[0], -w, w, base[0]] if base else [-w, w]):
            for j, y in enumerate(ys):
                nodes[i, j, k] = (x, y, z)
    solid = np.zeros((nodes.shape[0] - 1, len(ys) - 1, len(rows) - 1), dtype=bool)
    if base:
        solid[:, :, 0] = True
    for y0, y1 in ears:
        solid[1 if base else 0, ys.index(y0):ys.index(y1), (1 if base else 0):] = True
    return bevel(lattice(nodes, solid), chamfer, segs)


def link(length, r0, r1, t, steps=2, gap=None, fork0=0.0, fork1=0.0, chamfer=0.003, segs=1):
    """Plate link along +Z between two pins along Y: round ends of radius r0 (z = 0) and r1.

    With a gap the link is forked: the slot runs fork0 from the first pin and fork1 from the
    second one towards the middle; what is left between the slots is the web.
    """
    rows = [(-dz, w) for dz, w in tip_rows(r0, steps)][::-1] + [(0.0, r0)]
    if gap:
        rows += [(z, r0 + (r1 - r0) * z / length) for z in (fork0, length - fork1) if 0.0 < z < length]
    rows += [(length, r1)] + [(length + dz, w) for dz, w in tip_rows(r1, steps)]
    ys = [-0.5 * t, -0.5 * gap, 0.5 * gap, 0.5 * t] if gap else [-0.5 * t, 0.5 * t]
    nodes = np.zeros((2, len(ys), len(rows), 3))
    for k, (z, w) in enumerate(rows):
        for i, x in enumerate((-w, w)):
            for j, y in enumerate(ys):
                nodes[i, j, k] = (x, y, z)
    solid = np.ones((1, len(ys) - 1, len(rows) - 1), dtype=bool)
    if gap:
        for k in range(len(rows) - 1):
            solid[0, 1, k] = fork0 < 0.5 * (rows[k][0] + rows[k + 1][0]) < length - fork1
    return bevel(lattice(nodes, solid), chamfer, segs)


def pin(length, r, n=12):
    """Pin along +Z centred on the origin, `length` between the inner faces of its head and nut.

    Returns (shaft with its head, hex nut).
    """
    h, c = 0.5 * length, 0.18 * r
    rh, th, tn = 1.55 * r, max(0.45 * r, 0.004), 0.9 * r
    prof = [(rh - c, -h - th), (rh, -h - th + c), (rh, -h - c), (rh - c, -h), (r, -h), (r, h + tn + 0.35 * r),
            (r - c, h + tn + 0.35 * r + c)]
    shaft = lathe(prof, n, caps=("grid", "grid"))
    nut = bevel(lathe([(1.75 * r, h), (1.75 * r, h + tn)], 6, caps=("strip", "strip"), phase=math.pi / 6), 0.1 * r)
    return shaft, nut


def add_pin(g, at, length, r, n=12):
    # ponytail: ears and blocks have no bore, the pin's shaft simply passes through them. Model the
    # bores if a pin ever has to come out on screen.
    shaft, nut = pin(length, r, n)
    g.add(shaft, "chrome", at)
    g.add(nut, "ti", at)


def bolt(r=0.006, h=0.005, n=8):
    """Round head of a fastener sitting on z = 0, pointing +Z; its foot is buried."""
    return lathe([(r, -0.002), (r, h - 0.3 * r), (0.7 * r, h)], n, caps=(None, "grid"))


# =============================================================================================
# Footpads
# =============================================================================================
# w, l, h: the pad's plan size and height; riser, yoke: the gimbal's stack above its top plate
PADS = {"main": {"w": 0.66, "l": 1.24, "h": 0.30, "riser": 0.056, "yoke": 0.115},
        "low": {"w": 0.60, "l": 1.00, "h": 0.120, "riser": 0.022, "yoke": 0.068}}
PAD_FX = (0.14, 0.86)                      # end faces: rib, panel, rib
PAD_FY = (0.045, 0.335, 0.375, 0.625, 0.665, 0.955)      # long faces: three panels between ribs
PAD_PANELS = (3, 10, 12, 14, 21, 28, 30, 32)             # ring cells of the recessed panels
PAD_EMBLEMS = (12, 30)                                   # the middle panel of each long face
PAD_R = 0.090                              # corner radius of the bumper slab (main pad)
PAD_TOP = (0.165, 0.27)                    # main pad's top plate: half width, half length as a share of the pad's
EMBLEM = [(0.045, -0.004), (0.045, 0.003), (0.043, 0.005), (0.035, 0.005), (0.0325, 0.0025),
          (0.0155, 0.0025), (0.013, 0.005)]


def ankle_height(kind):
    """Height of the gimbal's axes above the pad's top plate, along the gimbal's own up."""
    return PADS[kind]["riser"] + PADS[kind]["yoke"]


def emblem(g, at):
    g.add(lathe(EMBLEM, 32, caps=(None, "strip"), mats=["ti", "ti", "ti", "ti", "panel", "ti"]), xf=at)


def tread(g, xf, hx, length, r):
    """Tread bars under the sole: they carry the pad, their feet are the ground plane."""
    bars = 9
    pitch = (length - 0.10) / bars
    for k in range(bars):
        y = (k - 0.5 * (bars - 1)) * pitch
        reach = abs(y) + 0.28 * pitch - (0.5 * length - r)               # how far into the corner radius
        cut = r - math.sqrt(max(r ** 2 - reach ** 2, 0.0)) if reach > 0.0 else 0.0
        g.add(box(2.0 * (hx - 0.024 - cut), 0.56 * pitch, 0.020, 0.003), "rubber", xf @ shift(0.0, y, 0.010))


def footpad(g, xf, kind):
    """Trapezoidal pad on the ground: origin under its centre, X across, Y along.

    "main": a rubber sole on tread bars, a bumper slab with a recessed light strip round its top,
    then a truncated pyramid with recessed panels and an emblem on each long face; two position
    lights on its top plate. "low": the same sole, slab and light strip under a low chamfered top
    that carries the emblem, ahead of the gimbal where the stowed strut leaves it free.
    """
    pad = PADS[kind]
    hx, hy = 0.5 * pad["w"], 0.5 * pad["l"]
    if kind == "low":
        r = 0.080
        slab = lambda z, d, mat: (z, hx - d, hy - d, r - d, mat)
        levels = [slab(0.010, 0.016, "rubber"), slab(0.013, 0.013, "rubber"), slab(0.026, 0.013, "gun"),
                  slab(0.034, 0.004, "gun"), slab(0.042, 0.000, "gun"), slab(0.064, 0.000, "gun"),
                  slab(0.071, 0.004, "gun"), slab(0.076, 0.013, "gun"), slab(0.076, 0.022, "glow"),
                  slab(0.086, 0.022, "gun"), slab(0.090, 0.026, "cast"), slab(0.096, 0.040, "cast"),
                  slab(0.110, 0.054, "cast"), slab(0.1155, 0.062, "cast"), slab(pad["h"], 0.070, "cast")]
        rings = []
        for z, ax, ay, rr, _ in levels:
            pts, a, b = rrect(ax, ay, rr, PAD_FX, PAD_FY, 4)
            rings.append(np.column_stack([pts, np.full(len(pts), z)]))
        g.add(loft(rings, caps=("grid", "grid"), grid=(a, b), mats=[lv[4] for lv in levels[:-1]]), xf=xf)
        tread(g, xf, hx, pad["l"], r)
        emblem(g, xf @ shift(0.0, -0.46 * (hy - 0.070), pad["h"]))
        return

    tx, ty = PAD_TOP[0], PAD_TOP[1] * pad["l"]
    z0, z1, foot = 0.152, 0.288, 0.064                   # pyramid: foot and top edge heights, foot inset

    def pyramid(z, inset=0.0):
        w = (z - z0) / (z1 - z0)
        return hx - foot + (tx - hx + foot) * w - inset, hy - foot + (ty - hy + foot) * w - inset

    # (z, half sizes, corner radius, material of the band above)
    slab = lambda z, d, mat: (z, hx - d, hy - d, PAD_R - d, mat)
    levels = [slab(0.014, 0.017, "rubber"), slab(0.017, 0.014, "rubber"), slab(0.036, 0.014, "gun"),
              slab(0.046, 0.004, "gun"), slab(0.060, 0.000, "gun"), slab(0.104, 0.000, "gun"),
              slab(0.118, 0.004, "gun"), slab(0.128, 0.014, "gun"), slab(0.128, 0.024, "glow"),
              slab(0.142, 0.024, "gun"), slab(0.146, 0.028, "cast"),
              (z0, *pyramid(z0), 0.030, "cast"), (0.172, *pyramid(0.172), 0.030, "cast"),
              (0.268, *pyramid(0.268), 0.030, "cast"), (z1, *pyramid(z1), 0.030, "cast"),
              (0.296, *pyramid(z1, 0.013), 0.022, "cast"), (pad["h"], *pyramid(z1, 0.028), 0.016, "cast")]
    rings = []
    for z, ax, ay, r, _ in levels:
        pts, a, b = rrect(ax, ay, r, PAD_FX, PAD_FY, 4)
        rings.append(np.column_stack([pts, np.full(len(pts), z)]))
    body = loft(rings, caps=("grid", "grid"), grid=(a, b), mats=[lv[4] for lv in levels[:-1]])
    n, band = len(rings[0]), 12                          # band 12 is the pyramid's main slope

    # recess the panels with a bmesh inset: the cage stays all quads
    bm = bmesh.new()
    verts = [bm.verts.new(tuple(p)) for p in body.v]
    bfaces = [bm.faces.new([verts[i] for i in f]) for f in body.f]
    bm.normal_update()
    tags = {f: body.m[i] for i, f in enumerate(bfaces)}
    recessed = [bfaces[band * n + c] for c in PAD_PANELS]
    emblems = [(np.array(bfaces[band * n + c].calc_center_median()), np.array(bfaces[band * n + c].normal))
               for c in PAD_EMBLEMS]
    for f in recessed:
        tags[f] = "panel"
    bmesh.ops.inset_region(bm, faces=recessed, thickness=0.010, depth=-0.008, use_even_offset=True, use_boundary=True)
    bm.verts.index_update()
    g.add(Part([tuple(vt.co) for vt in bm.verts], [[vt.index for vt in f.verts] for f in bm.faces],
               m=[tags.get(f, "cast") for f in bm.faces]), xf=xf)
    bm.free()
    tread(g, xf, hx, pad["l"], PAD_R)
    for centre, normal in emblems:                       # medallions on the middle panels
        emblem(g, xf @ frame(centre - 0.008 * normal, normal, (0.0, 1.0, 0.0)))
    top = xf @ shift(0.0, 0.0, pad["h"])
    for sy in (-1, 1):                                   # position lights, nearly flush with the top plate
        g.add(box(0.150, 0.014, 0.006, 0.002), "glow", top @ shift(0.0, sy * (ty - 0.085), 0.001))
    g.add(box(0.040, 0.060, 0.022, 0.003), "cast", top @ shift(-0.122, 0.0, 0.010))   # lights' junction box


def gimbal(g, G, kind):
    """Gimbal on the pad's top plate, in the frame G: origin on the plate, X along the pitch pin
    (the fold axis), Z up through the gimbal's centre. A riser carries the yoke whose two ears
    along Y hold the roll pin; the block between them takes the pitch pin. The riser's foot sinks
    into the plate, so a canted gimbal still stands on it."""
    pad = PADS[kind]
    riser, yoke = pad["riser"], pad["yoke"]
    tilted = abs(float(G[2, 2]) - 1.0) > 1e-6
    if kind == "low":
        rows = [(0.066, 0.094, 0.020, -0.002), (0.066, 0.094, 0.020, 0.005), (0.062, 0.090, 0.017, 0.010),
                (0.062, 0.090, 0.017, riser - 0.004), (0.058, 0.086, 0.013, riser)]
        w0, base = 0.046, (0.058, -0.090, 0.090, 0.010)
    else:
        rows = [(0.088, 0.118, 0.036, -0.045 if tilted else -0.002), (0.088, 0.118, 0.036, 0.006),
                (0.078, 0.108, 0.028, 0.016), (0.074, 0.104, 0.026, riser - 0.006), (0.068, 0.098, 0.020, riser)]
        w0, base = 0.055, (0.064, -0.094, 0.094, 0.012)
    rings = []
    for ax, ay, r, z in rows:
        pts, a, b = rrect(ax, ay, r, (0.5,), (0.5,), 2)
        rings.append(np.column_stack([pts, np.full(len(pts), z)]))
    g.add(loft(rings, caps=(None, "grid"), grid=(a, b)), "cast", G)
    at = G @ shift(0.0, 0.0, riser - 0.001)
    g.add(bracket([(-0.070, -0.050), (0.050, 0.070)], w0, yoke + 0.001, 0.034, base=base, steps=3), "ti", at)
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.add(bolt(0.006, 0.005), "gun", at @ shift(sx * (base[0] - 0.014), sy * (base[2] - 0.012), base[3]))
    centre = G @ shift(0.0, 0.0, riser + yoke)
    g.add(box(0.094, 0.094, 0.078, 0.007, 2), "cast", centre)
    add_pin(g, centre @ AXIS_Y, 0.144, 0.016, 16)


# =============================================================================================
# Leg kinematics
# =============================================================================================
SX = 0.100                                 # offset of each strut from the leg's plane
R_BARREL, R_COLLAR, R_CLAMP, R_GLAND, R_PISTON = 0.058, 0.064, 0.068, 0.068, 0.038
R_TRUNNION, R_HUB = 0.040, 0.054
R_FOOT = 0.054                             # round ends of the crosshead beam, round each piston
FOOT_BEAM = (-0.172, -0.104)               # crosshead beam along the strut, from the ankle axis: clear of the gimbal pins
SCISSOR_Y = -0.105                         # top torque links: their mid-plane, off the strut's upper face
SCISSOR_X = SX + R_GLAND + 0.020           # side torque links: their pins, beside the strut, in its plane
STROKE_STOWED = 0.018                      # chrome left showing on a stowed strut
PISTON_IN = 0.045                          # piston length inside the barrel, deployed
U_SWING, U_SHORTEN = (0.14, 0.86), (0.18, 0.60)      # the oleo is short before the pad reaches its well


class Leg:
    """Geometry and motion of one leg, port side or centreline, in world coordinates.

    T: trunnion centre; A0, A1: ankle (gimbal centre) deployed and stowed, both in the plane through
    T normal to `axis`, the fold axis. x_dir: the leg frame's X, along the axis either way, the side
    of the torque links. zb: station of the bridge along the strut; walls: the stations of the two
    trunnion bearings along the leg's X. horn: (station along the leg's X, length, angle at rest)
    of the retraction horn; anchor: the actuator's fixed pin from the horn's root. Angles and
    offsets in the fold plane run from aft (u_y) towards up (u_n = axis x u_y). swivel: +1 or -1,
    the side along the leg's X of the wall (x = wall_x) that carries the actuator's manifold; roof:
    height of the well's roof, which carries its clevis; front: y of the front wall that carries
    the trunnion bearings, or None when they sit on the side walls. pad: a key of PADS.
    """

    def __init__(self, T, A0, A1, axis, x_dir, zb, walls, horn, anchor, swivel, wall_x, roof, pad,
                 front=None, scissor="side"):
        self.T, self.A0, self.A1 = (np.asarray(p, dtype=float) for p in (T, A0, A1))
        self.axis, self.x_dir = unit(axis), unit(x_dir)
        self.zb, self.walls, self.scissor, self.pad = zb, tuple(walls), scissor, pad
        self.swivel, self.wall_x, self.roof, self.front = swivel, wall_x, roof, front
        assert abs(abs(float(self.axis @ self.x_dir)) - 1.0) < 1e-9, "the leg's X must lie along the fold axis"
        for p in (self.A0, self.A1):
            assert abs(float((p - self.T) @ self.axis)) < 1e-9, "the ankle leaves the fold plane"
        self.L0 = float(np.linalg.norm(self.A0 - self.T))
        self.L1 = float(np.linalg.norm(self.A1 - self.T))
        self.c = self.L0 - self.L1
        self.e0 = (self.A0 - self.T) / self.L0
        e1 = (self.A1 - self.T) / self.L1
        self.theta = math.atan2(float(np.cross(self.e0, e1) @ self.axis), float(self.e0 @ e1))
        self.u_y = unit(np.array([0.0, 1.0, 0.0]) - self.axis * self.axis[1])
        self.u_n = np.cross(self.axis, self.u_y)
        # the strut's underside (+Y) faces down once stowed
        y = np.cross(self.e0, self.axis)
        if (anim.about((0, 0, 0), self.axis, self.theta)[:3, :3] @ y)[2] > 0.0:
            y = -y
        self.F = np.eye(4)
        self.F[:3, 0], self.F[:3, 1], self.F[:3, 2], self.F[:3, 3] = self.x_dir, y, self.e0, self.T
        self.ex, self.ey = self.F[:3, 0], self.F[:3, 1]
        self.zg = self.L1 + FOOT_BEAM[0] - 0.030 - STROKE_STOWED - 0.063     # gland nut station
        self.z_piston = self.zg + 0.063 - PISTON_IN                          # piston head, deployed
        xh, q, phi = horn
        self.xh, self.H = xh, self.T + xh * self.x_dir                         # the horn's root on the trunnion
        self.Q0 = self.H + q * (math.cos(phi) * self.u_y + math.sin(phi) * self.u_n)
        self.P = self.H + anchor[0] * self.u_y + anchor[1] * self.u_n
        if scissor == "top":                               # on the bridge and the crosshead's middle
            x, yy, zu, zl, bow = 0.0, SCISSOR_Y, zb, self.L0 + 0.5 * (FOOT_BEAM[0] + FOOT_BEAM[1]), 0.050
        else:                                              # under the barrel's lug collar, on the crosshead's top
            x, yy, zu, zl, bow = SCISSOR_X, 0.0, self.zg - 0.030, self.L0 + FOOT_BEAM[0] + 0.022, 0.040
        self.B, self.C0, self.span0 = self.at(x, yy, zu), self.at(x, yy, zl), zl - zu
        self.arm = math.hypot(0.5 * self.span0, bow)
        self.K0 = self.apex_at(0.0)
        spans = [float(np.linalg.norm(self.pin_q(u) - self.P)) for u in np.linspace(0.0, 1.0, 101)]
        self.act_span = (min(spans), max(spans))
        assert self.c >= 0.0 and self.z_piston - self.c > 0.134, "the stroke runs the piston into the trunnion"
        assert 0.168 <= zb <= self.zg - (0.100 if scissor == "side" else 0.060), "no room for the bridge"
        assert self.act_span[1] < 2.0 * self.act_span[0] - 0.27, "the actuator's rod would leave its cylinder"

    def at(self, x, y, z):
        """World point of leg frame coordinates, at rest."""
        return self.F[:3, :3] @ np.array([x, y, z], dtype=float) + self.T

    def swing(self, u):
        return self.theta * anim.ease(u, *U_SWING)

    def shorten(self, u):
        return self.c * anim.ease(u, *U_SHORTEN)

    def pin_q(self, u):
        return anim.about(self.T, self.axis, self.swing(u))[:3] @ np.append(self.Q0, 1.0)

    def apex_at(self, u):
        """The torque links' apex at phase u, in the leg's rest frame: it stands out along the leg's X."""
        s = self.span0 - self.shorten(u)
        return self.B + self.F[:3, 2] * 0.5 * s + self.ex * math.sqrt(self.arm ** 2 - 0.25 * s * s)

    def about_axis(self, a, b):
        """Signed angle about the fold axis that turns a onto b."""
        return math.atan2(float(np.cross(a, b) @ self.axis), float(a @ b))

    def poses(self, u):
        """World transforms of the leg's rigid parts at phase u: identity at u = 0."""
        R = anim.about(self.T, self.axis, self.swing(u))
        down = anim.shift(-self.shorten(u) * self.e0)
        K, C = self.apex_at(u), self.C0 - self.shorten(u) * self.e0

        def turn(centre, a, b):                            # about a torque link pin, a onto b
            return anim.about(centre, self.ey, math.atan2(float(np.cross(a, b) @ self.ey), float(a @ b)))
        ankle = R[:3, :3] @ (self.A0 - self.shorten(u) * self.e0) + R[:3, 3]
        Q = self.pin_q(u)
        tilt = self.about_axis(self.Q0 - self.P, Q - self.P)
        return {"Jambe": R, "Coulisse": R @ down,
                "Compas_Haut": R @ turn(self.B, self.K0 - self.B, K - self.B),
                "Compas_Bas": R @ down @ turn(self.C0, self.K0 - self.C0, K - C),
                "Verin": anim.about(self.P, self.axis, tilt),
                "Tige": anim.shift(Q - self.Q0) @ anim.about(self.Q0, self.axis, tilt),
                "Patin": anim.shift(ankle - self.A0)}

    def pins(self):
        """Every joint at rest: (part, part or None for the airframe, point, axis, kind, radius, half length).

        Radius and half length bound the cylinder round a pin inside which its two parts may touch:
        a pin through an eye, a tube in its bearing. A slide's parts never touch.
        """
        ax, ey = self.axis, self.ey
        w0, w1 = self.walls
        return [("Jambe", None, self.T + self.x_dir * 0.5 * (w0 + w1), ax, "pin", 0.070, 0.5 * abs(w1 - w0) + 0.02),
                ("Jambe", "Compas_Haut", self.B, ey, "pin", 0.030, 0.040),
                ("Compas_Haut", "Compas_Bas", self.K0, ey, "pin", 0.030, 0.040),
                ("Compas_Bas", "Coulisse", self.C0, ey, "pin", 0.030, 0.040),
                ("Coulisse", "Patin", self.A0, ax, "pin", 0.030, 0.100),
                ("Jambe", "Tige", self.Q0, ax, "pin", 0.035, 0.060),
                ("Verin", None, self.P, ax, "pin", 0.035, 0.060),
                ("Jambe", "Coulisse", self.at(SX, 0.0, self.zg), self.e0, "slide", 0.0, 0.0),
                ("Verin", "Tige", self.P, self.Q0 - self.P, "slide", 0.0, 0.0)]


MIRROR = np.diag([-1.0, 1.0, 1.0, 1.0])


def mirrored_pose(pose):
    return lambda u: MIRROR @ pose(u) @ MIRROR


# =============================================================================================
# Leg parts, drawn at rest in world coordinates
# =============================================================================================
def strut(jambe, coulisse, leg, x):
    """One oleo strut at offset x: barrel, collars, gland nut and wiper on the leg; piston on the slide."""
    at = leg.F @ shift(x, 0.0, 0.0)
    zb, zg, L = leg.zb, leg.zg, leg.L0
    corners = [(0.030, 0.090), (R_COLLAR, 0.090), (R_COLLAR, 0.124), (R_BARREL, 0.124), (R_BARREL, zb - 0.034),
               (R_CLAMP, zb - 0.034), (R_CLAMP, zb + 0.034), (R_BARREL, zb + 0.034)]
    radii = [0.005, 0.004, 0.0, 0.0, 0.003, 0.003, 0.0]
    if leg.scissor == "side":                            # lug collar of the torque links
        zu = zg - 0.030
        corners += [(R_BARREL, zu - 0.024), (R_COLLAR, zu - 0.024), (R_COLLAR, zu + 0.024), (R_BARREL, zu + 0.024)]
        radii += [0.0, 0.002, 0.002, 0.0]
    corners.append((R_BARREL, zg + 0.035))
    jambe.add(lathe(rounded(corners, radii, 1), 24), "gun", at)                       # ends buried
    zs = 0.5 * (zb + 0.034 + (zg - 0.054 if leg.scissor == "side" else zg))        # charging valve
    if leg.scissor != "side" or x < 0.0:
        side = 1.0 if x > 0.0 else -1.0
        valve = [(0.010, -0.004), (0.010, 0.009), (0.008, 0.011), (0.0065, 0.011), (0.0065, 0.021), (0.005, 0.0225)]
        jambe.add(lathe(valve, 8, caps=(None, "grid")), "ti",
                  at @ frame((side * R_BARREL, 0.0, zs), (side, 0.0, 0.0), (0.0, 0.0, 1.0)))
    gland = rounded([(R_BARREL - 0.004, zg), (R_GLAND, zg), (R_GLAND, zg + 0.028), (R_GLAND - 0.007, zg + 0.028),
                     (R_GLAND - 0.007, zg + 0.050), (0.045, zg + 0.050)], [0.004, 0.003, 0.0, 0.004], 1)
    jambe.add(lathe(gland, 24), "ti", at)
    jambe.add(lathe([(0.047, zg + 0.045), (0.047, zg + 0.056), (0.0405, zg + 0.063), (R_PISTON + 0.0009, zg + 0.063)],
                    24), "rubber", at)
    # head lug: rises from the barrel's top collar and wraps the trunnion
    up = frame((0.0, 0.0, 0.098), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))
    jambe.add(bracket([(-0.032, 0.032)], 0.058, 0.098, R_COLLAR, steps=5, chamfer=0.004), "gun", at @ up)
    # piston and its socket on the crosshead
    coulisse.add(lathe([(R_PISTON, leg.z_piston), (R_PISTON, L + FOOT_BEAM[0] - 0.010)], 32), "chrome", at)
    socket = rounded([(R_PISTON - 0.002, L + FOOT_BEAM[0] - 0.030), (0.050, L + FOOT_BEAM[0] - 0.030),
                      (0.050, L + FOOT_BEAM[0] + 0.004)], [0.004], 1)
    coulisse.add(lathe(socket, 24), "ti", at)


def crosshead(g, foot, scissor):
    """Forged beam joining the two pistons, with the fork that holds the gimbal's pitch pin.

    `foot` is the leg frame moved to the ankle: z = 0 on the pitch axis, the struts above (z < 0).
    Seen along the struts the beam is a stadium round each piston; the fork hangs under its middle.
    The lower torque link rides on a boss on its upper face, or on a tongue at its +X end.
    """
    r, re = R_FOOT, 0.036
    tips = tip_rows(r, 5)
    cols = ([(-SX - dz, w) for dz, w in tips][::-1] + [(x, r) for x in (-SX, -0.070, -0.050, 0.050, 0.070, SX)]
            + [(SX + dz, w) for dz, w in tips])
    rows = [(FOOT_BEAM[0], None), (FOOT_BEAM[1], None), (0.0, re)] + tip_rows(re, 3)
    nodes = np.zeros((len(cols), 2, len(rows), 3))
    for k, (z, we) in enumerate(rows):
        for i, (x, w) in enumerate(cols):
            half = w if we is None else we
            nodes[i, 0, k], nodes[i, 1, k] = (x, -half, z), (x, half, z)
    solid = np.zeros((len(cols) - 1, 1, len(rows) - 1), dtype=bool)
    solid[:, 0, 0] = True
    for i, (x, _) in enumerate(cols[:-1]):
        if abs(abs(x + 0.010) - 0.060) < 1e-6:           # the two fork ears: 0.050 .. 0.070
            solid[i, 0, 1:] = True
    g.add(bevel(lattice(nodes, solid), 0.005, 2), "ti", foot)
    if scissor == "top":
        zc = 0.5 * (FOOT_BEAM[0] + FOOT_BEAM[1])
        reach = -SCISSOR_Y - 0.024 - R_FOOT               # to 1 mm short of the lower link
        g.add(lathe([(0.022, -0.004), (0.022, reach - 0.003), (0.019, reach)], 16, caps=(None, "grid")), "ti",
              foot @ frame((0.0, -R_FOOT, zc), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)))
    else:
        root = SX + R_FOOT - 0.006
        g.add(bracket([(-0.011, 0.011)], 0.022, SCISSOR_X - root, 0.022, steps=3), "ti",
              foot @ frame((root, 0.0, FOOT_BEAM[0] + 0.022), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))


def block(nodes, chamfer=0.004):
    """Chamfered hexahedron from its eight corners, nodes (2, 2, 2, 3); three segments, for skewed corners."""
    return bevel(lattice(np.asarray(nodes, dtype=float)), chamfer, 3)


def trunnion(jambe, fixed, leg):
    """Trunnion tube between its two bearings, a hub for the strut heads and one for the retraction
    horn; each bearing sits on a side wall, or on a block cantilevered from the well's front wall."""
    F = leg.F
    w0, w1 = leg.walls
    hubs = sorted([(-0.046, 0.046), (leg.xh - 0.046, leg.xh + 0.046)])
    corners = [(R_TRUNNION - 0.004, w0 + 0.022), (R_TRUNNION, w0 + 0.022)]
    radii = [0.003]
    for lo, hi in hubs:
        corners += [(R_TRUNNION, lo), (R_HUB, lo), (R_HUB, hi), (R_TRUNNION, hi)]
        radii += [0.0, 0.003, 0.003, 0.0]
    corners += [(R_TRUNNION, w1 - 0.022), (R_TRUNNION - 0.004, w1 - 0.022)]
    radii += [0.003]
    jambe.add(lathe(rounded(corners, radii, 1), 20, caps=("grid", "grid")), "ti", F @ AXIS_X)
    # horn: a clevis on its hub; its pin carries the actuator's rod eye
    h = unit(leg.Q0 - leg.H)
    horn = frame(leg.H, h, np.cross(leg.axis, h))
    q = float(np.linalg.norm(leg.Q0 - leg.H))
    jambe.add(bracket([(-0.036, -0.019), (0.019, 0.036)], 0.046, q, 0.030, steps=3, chamfer=0.003), "ti", horn)
    add_pin(jambe, frame(leg.Q0, leg.axis, leg.u_y), 0.074, 0.012)
    # bearings: a housing round each end of the tube, on a round flange
    for w in leg.walls:
        side = math.copysign(1.0, w)
        at = F @ frame((w, 0.0, 0.0), (-side, 0.0, 0.0), (0.0, 1.0, 0.0))
        housing = rounded([(0.050, -0.004), (0.062, -0.004), (0.062, 0.012), (0.050, 0.012), (0.050, 0.062),
                           (0.043, 0.066), (R_TRUNNION + 0.002, 0.066)], [0.003, 0.003, 0.0, 0.004, 0.0], 1)
        fixed.add(lathe(housing, 20), "cast", at)
        for k in range(4):
            a = math.pi * (0.25 + 0.5 * k)
            fixed.add(bolt(0.0055, 0.005), "gun", at @ shift(0.056 * math.cos(a), 0.056 * math.sin(a), 0.012))
        if leg.front is not None:                         # the flange's block, out to the front wall
            ss = sorted([w - side * 0.004, w + side * 0.036])
            ys = (leg.front - 0.010 - leg.T[1], 0.068)
            fixed.add(block([[[leg.T + s * leg.x_dir + a * leg.u_y + b * leg.u_n for b in (-0.066, 0.066)]
                              for a in ys] for s in ss]), "cast")


def bridge(jambe, leg):
    """Bridge between the barrels' clamp collars: a forged web, and the upper torque link's boss on top."""
    b = leg.F @ shift(0.0, 0.0, leg.zb)
    half = SX - R_BARREL + 0.006                          # the web's ends sink into the barrels' walls
    g = np.stack(np.meshgrid([-half, half], [-0.050, 0.050], [-0.028, 0.028], indexing="ij"), axis=-1)
    jambe.add(bevel(lattice(g), 0.005, 2), "ti", b)
    for sy in (-1.0, 1.0):
        for x in (-0.034, 0.034):
            jambe.add(bolt(0.007, 0.005), "gun", b @ frame((x, sy * 0.050, 0.0), (0.0, sy, 0.0), (0.0, 0.0, 1.0)))
    if leg.scissor == "top":
        reach = -SCISSOR_Y - 0.012 - 0.046                # from inside the web to 1 mm short of the upper link
        jambe.add(lathe([(0.020, 0.0), (0.020, reach - 0.003), (0.017, reach)], 16, caps=(None, "grid")), "ti",
                  b @ frame((0.0, -0.046, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)))


def torque_links(parts, leg):
    """Upper link on the leg, lower link on the crosshead, pinned at the apex; all pins along the leg's Y."""
    def along(p, q):
        d = q - p
        return frame(p, d, np.cross(leg.ey, d))
    r_eye = 0.024 if leg.scissor == "top" else 0.020   # beside the strut, the eye clears the lug collar
    parts["Compas_Haut"].add(link(leg.arm, r_eye, 0.022, 0.022), "ti", along(leg.B, leg.K0))
    out = lambda p: frame(p, -leg.ey, leg.ex)              # pins point out of the strut's upper face
    if leg.scissor == "top":                               # lower link: an eye on the crosshead's boss
        parts["Compas_Bas"].add(link(leg.arm, 0.024, 0.024, 0.046, gap=0.026, fork0=-1.0, fork1=0.052), "ti",
                                along(leg.C0, leg.K0))
        add_pin(parts["Jambe"], out(leg.B), 0.024, 0.009)
    else:                                                  # lower link forked round the crosshead's tongue
        parts["Compas_Bas"].add(link(leg.arm, 0.024, 0.024, 0.046, gap=0.026, fork0=0.046, fork1=0.052), "ti",
                                along(leg.C0, leg.K0))
        root = leg.at(SX + R_BARREL - 0.004, 0.0, leg.zg - 0.030)
        parts["Jambe"].add(bracket([(-0.027, -0.013), (0.013, 0.027)], 0.024, SCISSOR_X - SX - R_BARREL + 0.004, 0.024,
                                   steps=3), "ti", frame(root, leg.ex, leg.F[:3, 2]))
        add_pin(parts["Jambe"], frame(leg.B, -leg.ey, leg.ex), 0.056, 0.009)
    add_pin(parts["Compas_Haut"], out(leg.K0), 0.048, 0.009)
    add_pin(parts["Coulisse"], out(leg.C0), 0.048, 0.009)


def to_plane(p, d, x):
    """p moved along d onto the plane of constant world x."""
    return p + d * ((x - p[0]) / d[0])


def actuator(verin, tige, fixed, leg):
    """Retraction actuator from its clevis, hung under the well's roof, to the horn.

    The cylinder is as short as the rod's travel allows; the hoses run from a swivel on the fixed
    pin's axis, so nothing has to bend as the cylinder tilts. The swivel's manifold is a block from
    the nearest side wall.
    """
    P, Q = leg.P, leg.Q0
    lo, hi = leg.act_span
    z_head = lo - 0.160                                  # head gland of the cylinder, from the fixed pin
    sw = leg.swivel * leg.x_dir                          # along the pins, towards the manifold's wall
    act = frame(P, Q - P, sw)                            # Z along the actuator, X along the pins
    rod = frame(Q, P - Q, sw)
    # fixed clevis: its ears stand behind the pin, away from the cylinder, from a block under the roof
    back = unit(P - leg.pin_q(0.5))
    hang = frame(P + 0.060 * back, -back, np.cross(back, leg.axis))      # Z to the pin, Y along it
    fixed.add(bracket([(-0.036, -0.019), (0.019, 0.036)], 0.036, 0.060, 0.028), "ti", hang)
    corner = lambda x, y: hang[:3, :3] @ np.array([x, y, 0.004]) + hang[:3, 3]
    fixed.add(block([[[corner(x, y), np.append(corner(x, y)[:2], leg.roof + 0.001)] for y in (-0.050, 0.050)]
                     for x in (-0.060, 0.060)]), "cast")
    add_pin(fixed, frame(P, leg.axis, leg.u_y), 0.074, 0.012)
    # manifold: a block from the side wall carrying the swivel's fixed half on the pin's axis
    wall = leg.wall_x + math.copysign(0.003, sw[0])                     # just into the wall
    face = [[P + sw * 0.098 + a * leg.u_y + b * leg.u_n for b in (-0.030, 0.030)] for a in (-0.025, 0.025)]
    fixed.add(block([[[p, to_plane(p, sw, wall)] for p in row] for row in face]), "cast")
    fixed.add(lathe([(0.016, 0.0), (0.016, 0.0085), (0.013, 0.0115)], 12, caps=(None, "grid")), "ti",
              frame(P + sw * 0.1005, -sw, leg.u_y))
    # cylinder: tail eye, end cap, barrel, head gland; swivel on the pin's axis
    verin.add(bracket([(-0.016, 0.016)], 0.030, 0.066, 0.028), "gun",
              act @ frame((0.0, 0.0, 0.066), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
    corners = [(0.024, 0.056), (0.050, 0.056), (0.050, 0.088), (0.042, 0.088), (0.042, z_head), (0.050, z_head),
               (0.050, z_head + 0.034), (0.031, z_head + 0.034), (0.031, z_head + 0.052), (0.0215, z_head + 0.052)]
    verin.add(lathe(rounded(corners, [0.004, 0.003, 0.0, 0.0, 0.003, 0.004, 0.0, 0.003], 1), 20, caps=("strip", None)),
              "gun", act)
    verin.add(lathe([(0.014, 0.050), (0.017, 0.053), (0.017, 0.084), (0.014, 0.087)], 12, caps=("grid", "grid")), "ti",
              act @ AXIS_X)
    # rod: chrome, jam nut, eye
    tige.add(lathe([(0.021, 0.084), (0.021, lo - 0.110)], 16), "chrome", rod)
    tige.add(bevel(lathe([(0.032, 0.082), (0.032, 0.102)], 6, caps=("strip", "strip")), 0.002), "ti", rod)
    tige.add(bracket([(-0.016, 0.016)], 0.025, 0.086, 0.028), "ti", rod @ frame((0.0, 0.0, 0.086), (0.0, 0.0, -1.0),
                                                                                   (0.0, 1.0, 0.0)))
    # hoses: swivel to the tail port, swivel along the barrel to the head port
    at = lambda x, y, z: act[:3, :3] @ np.array([x, y, z]) + act[:3, 3]
    port = lathe([(0.012, -0.004), (0.012, 0.014), (0.010, 0.016)], 8, caps=(None, "grid"))
    verin.add(port, "ti", act @ frame((0.042, 0.0, 0.118), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    z_end = z_head - 0.030
    verin.add(box(0.026, 0.026, 0.030, 0.003), "ti", act @ shift(0.051, 0.0, z_end + 0.012))
    hose(verin, [at(0.068, -0.013, 0.014), at(0.072, -0.016, 0.060), at(0.074, -0.008, 0.108), at(0.060, 0.0, 0.118)],
         0.0065, "braid")
    rho = 0.050 + 0.020
    hose(verin, [at(0.068, 0.013, 0.014), at(0.074, 0.016, 0.060), at(rho, 0.012, 0.16), at(rho, 0.0, 0.24),
                 at(rho, 0.0, 0.5 * (0.24 + z_end)), at(rho, 0.0, z_end - 0.02), at(0.066, 0.0, z_end + 0.012)],
         0.0065, "braid")
    clip(verin, at(rho, 0.0, 0.5 * (0.24 + z_end)), act[:3, 2], act[:3, 0])


def harness(jambe, leg):
    """Light harness down the -X strut: from the trunnion along the barrel, past the bridge to the gland.

    It enters the leg through the trunnion's bore, so it never bends; the pad lights are fed
    through the oleo. It runs on the strut's outer underside, which faces down once stowed.
    """
    az = np.array([math.cos(math.radians(40.0)), math.sin(math.radians(40.0))])       # lower outer side
    ring = lambda rho, z: leg.at(-SX - rho * az[0], rho * az[1], z)
    out = leg.F[:3, :3] @ np.array([-az[0], az[1], 0.0])
    ez = leg.F[:3, 2]
    base = leg.at(-SX - 0.070, 0.0, 0.0)
    start = leg.at(-SX - 0.070, 0.036, 0.0)
    jambe.add(lathe([(0.012, -0.004), (0.012, 0.014), (0.010, 0.016)], 8, caps=(None, "grid")), "ti",
              frame(start, start - base))
    end = ring(R_GLAND + 0.010, leg.zg + 0.012)
    run = np.linspace(leg.zb + 0.060, leg.zg - 0.040, max(2, int(round((leg.zg - leg.zb) / 0.08))))
    hose(jambe, [start + (start - base) * 0.45, ring(R_COLLAR + 0.018, 0.105), ring(R_CLAMP + 0.0155, leg.zb)]
         + [ring(R_BARREL + 0.020, z) for z in run] + [end], 0.0060, "rubber")
    clip(jambe, ring(R_CLAMP + 0.0155, leg.zb), ez, out)
    jambe.add(box(0.030, 0.022, 0.036, 0.003), "cast", frame(ring(R_GLAND + 0.004, leg.zg + 0.012), ez, out))


def leg_parts(leg):
    """The rigid parts of one leg at rest, in world coordinates: ({part: Geo}, fixed Geo)."""
    parts = {k: Geo() for k in ("Jambe", "Coulisse", "Compas_Haut", "Compas_Bas", "Verin", "Tige", "Patin")}
    fixed = Geo()
    A = leg.A0
    lift = ankle_height(leg.pad)
    foot = leg.F @ shift(0.0, 0.0, leg.L0)
    footpad(parts["Patin"], shift(A[0], A[1], GROUND), leg.pad)
    G = np.eye(4)                                        # the gimbal stands on the top plate, canted with the fold axis
    G[:3, 0], G[:3, 1], G[:3, 2], G[:3, 3] = leg.axis, leg.u_y, leg.u_n, A - lift * leg.u_n
    gimbal(parts["Patin"], G, leg.pad)
    add_pin(parts["Coulisse"], foot @ AXIS_X, 0.144, 0.016, 16)       # pitch pin, in the crosshead's fork
    crosshead(parts["Coulisse"], foot, leg.scissor)
    for x in (-SX, SX):
        strut(parts["Jambe"], parts["Coulisse"], leg, x)
    trunnion(parts["Jambe"], fixed, leg)
    bridge(parts["Jambe"], leg)
    torque_links(parts, leg)
    actuator(parts["Verin"], parts["Tige"], fixed, leg)
    harness(parts["Jambe"], leg)
    return parts, fixed


# =============================================================================================
# Lines
# =============================================================================================
def hose(g, points, r, mat):
    """Line through the points (a spline), with a swaged ferrule at each end."""
    path = spline(points, 5)
    g.add(tube(path, r, 8), mat)
    ferrule = rounded([(r - 0.002, -0.010), (r + 0.0045, -0.010), (r + 0.0045, 0.012), (r + 0.002, 0.0145),
                       (r + 0.002, 0.024), (r - 0.0005, 0.0265)], [0.0015, 0.0, 0.0, 0.0], 1)
    for p, q in ((path[0], path[1]), (path[-1], path[-2])):
        g.add(lathe(ferrule, 8), "ti", frame(p, q - p))


def clip(g, point, along, outward):
    """Saddle clamp: holds a line passing `point` 15 mm off the surface that `outward` leaves."""
    at = frame(point, along, outward)
    g.add(box(0.036, 0.026, 0.014, 0.0025), "ti", at @ shift(-0.007, 0.0, 0.0))
    g.add(bolt(0.0045, 0.0035), "gun", at @ shift(0.011, 0.0, 0.0) @ AXIS_X)


# =============================================================================================
# Legs and wells
# =============================================================================================
# Nose leg: its trunnion at the back of the well, level with the stowed ankle; it rakes forward
# and folds forwards, level over the low pad, under the cabin floor.
NOSE_TRUNNION_Y, NOSE_STOW_Y = -2.50, -3.75       # trunnion; the stowed pad's centre
NOSE_RAKE, NOSE_BRIDGE = math.radians(40.0), 0.178
NOSE_HORN, NOSE_ANCHOR = (-0.25, 0.18, math.radians(-95.0)), (-0.65, 0.0)    # see Leg: horn, anchor
NOSE_ROOF = -1.312                         # the cabin floor's structure is above
NOSE_LIMIT = -4.40                         # nothing of the gear forward of this: the glazed prow
NOSE_WELL_BOX = (0.40, (-4.40, -2.32), -1.31)   # the nose well inside the hull: |x|, y range, top
NOSE_FRAMES = (-4.24,)                     # a roof frame ahead of the folded gear, past the well's rounded corners
# Main legs (port; starboard is the mirror image): the trunnion at the front of the well; the fold
# axis is canted up outboard, so the deployed leg splays out; the leg folds aft over its pad.
MAIN_STOW = (1.07, 1.85)                   # the stowed pad's centre
MAIN_CANT = math.radians(24.0)             # fold axis above the horizontal, outboard
MAIN_LEAN, MAIN_TILT = math.radians(20.0), math.radians(6.0)   # deployed lean aft; stowed strut above level
MAIN_L1, MAIN_BRIDGE = 1.10, 0.220         # trunnion to the stowed ankle; bridge station
MAIN_WALLS = (-0.30, 0.40)                 # trunnion bearings along the leg's X: outboard, inboard
MAIN_HORN, MAIN_ANCHOR = (0.24, 0.18, math.radians(-110.0)), (0.62, 0.18)    # see Leg: horn, anchor
MAIN_ROOF, DUCT_ROOF = -0.82, -1.07        # the well's roof, and its floor under the thruster ducts
DUCT = (1.39, 1.48)                        # the ducts fill z above -1.05 outboard of x and aft of y
AIRLOCK = (0.63, -1.28)                    # the airlock's liner: |x| up to, z from
FREE_TOP = -0.80                           # nothing of the gear above this
PAD_CLEAR = 0.012                          # a stowed sole above the highest inner face of its doors
SKIN = 0.014                               # the skin's thickness shown round an opening
DEEP = panels.THICK + 0.008                # the liner follows the skin's normal this deep, past the doors' inner face
HINGE_CLEAR = 0.003                        # a door's hinge line runs at least this far outside its leaf's rim
HINGE_TILT = 0.040                         # its slope against the leaf's ends: a 45 mm end slides 1.8 mm


def stow_sole(hull, centre, kind):
    """Height of a stowed sole: just above the inner face of the closed doors under its footprint."""
    pad = PADS[kind]
    xs, ys = np.meshgrid(centre[0] + np.linspace(-0.5, 0.5, 13) * pad["w"],
                         centre[1] + np.linspace(-0.5, 0.5, 25) * pad["l"])
    p, n = skin_at(hull, xs.ravel(), ys.ravel(), normals=True)
    return float((p - panels.THICK * n)[:, 2].max()) + PAD_CLEAR


def nose_leg(hull):
    """The nose leg: its low pad stowed level just above the doors, the leg folded level over it."""
    kind = "low"
    lift = PADS[kind]["h"] + ankle_height(kind)
    A1 = np.array([0.0, NOSE_STOW_Y, stow_sole(hull, (0.0, NOSE_STOW_Y), kind) + lift])
    T = np.array([0.0, NOSE_TRUNNION_Y, A1[2]])
    z0 = GROUND + lift
    A0 = np.array([0.0, T[1] - (T[2] - z0) * math.tan(NOSE_RAKE), z0])
    return Leg(T, A0, A1, (1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), NOSE_BRIDGE, (-hg.NOSE_WELL_HALF, hg.NOSE_WELL_HALF),
               NOSE_HORN, NOSE_ANCHOR, -1.0, hg.NOSE_WELL_HALF - 0.004, NOSE_ROOF, kind)


def main_leg(hull):
    """The port main leg: its pad stowed level just above the doors, the leg folded aft over it."""
    kind = "main"
    axis = np.array([math.cos(MAIN_CANT), 0.0, math.sin(MAIN_CANT)])
    y, up = np.array([0.0, 1.0, 0.0]), np.array([-math.sin(MAIN_CANT), 0.0, math.cos(MAIN_CANT)])
    lift = PADS[kind]["h"] + ankle_height(kind) * up[2]
    A1 = np.array([MAIN_STOW[0], MAIN_STOW[1], stow_sole(hull, MAIN_STOW, kind) + lift])
    T = A1 - MAIN_L1 * (math.cos(MAIN_TILT) * y + math.sin(MAIN_TILT) * up)
    phi = -math.atan2(1.0, math.tan(MAIN_LEAN) * up[2])          # e0 leans MAIN_LEAN aft of the vertical
    e0 = math.cos(phi) * y + math.sin(phi) * up
    A0 = T + e0 * (T[2] - GROUND - lift) / -e0[2]
    return Leg(T, A0, A1, axis, -axis, MAIN_BRIDGE, MAIN_WALLS, MAIN_HORN, MAIN_ANCHOR, 1.0,
               hg.MAIN_WELL_X[0] - 0.0165, MAIN_ROOF, kind, front=hg.MAIN_WELL_Y[0])


def skin_at(hull, x, y, normals=False):
    """Points of the hull's lower skin above (x, y): x falls from the shoulder to the keel."""
    x, y = np.broadcast_arrays(np.abs(np.asarray(x, dtype=float)), np.asarray(y, dtype=float))
    s = hull.s_of_y(y)
    lo, hi = np.full(x.shape, T2), np.ones(x.shape)
    for _ in range(46):
        mid = 0.5 * (lo + hi)
        wide = hull.eval(s, mid)[..., 0] > x
        lo, hi = np.where(wide, mid, lo), np.where(wide, hi, mid)
    return hull.eval(s, 0.5 * (lo + hi), normals=normals)


def skin_table(hull, h=0.02):
    """Height of the lower skin over the gear's plan, as a function of points (n, 3): bilinear."""
    xs, ys = np.arange(0.0, 1.76, h), np.arange(-4.6, 2.81, h)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = skin_at(hull, X.ravel(), Y.ravel())[:, 2].reshape(X.shape)

    def z_of(p):
        x, y = np.abs(p[:, 0]), p[:, 1]
        i = np.clip(((x - xs[0]) / h).astype(int), 0, len(xs) - 2)
        j = np.clip(((y - ys[0]) / h).astype(int), 0, len(ys) - 2)
        tx, ty = np.clip((x - xs[i]) / h, 0.0, 1.0), np.clip((y - ys[j]) / h, 0.0, 1.0)
        return ((1 - tx) * (1 - ty) * Z[i, j] + tx * (1 - ty) * Z[i + 1, j] + (1 - tx) * ty * Z[i, j + 1]
                + tx * ty * Z[i + 1, j + 1])
    return z_of


def turned_out(part):
    """The same Part with every face reversed: a box drawn from outside, seen from inside."""
    uv = part.uv if part.uv is not None else box_uv(part.v, part.f)
    return Part(part.v, [f[::-1] for f in part.f], [u[::-1] for u in uv], part.m)


def main_roof(q):
    """Height of the main well's roof over plan points (n, 2): it steps down under the thruster ducts."""
    s = lambda t: np.clip(t, 0.0, 1.0) ** 2 * (3.0 - 2.0 * np.clip(t, 0.0, 1.0))
    duct = s((q[:, 0] - DUCT[0] + 0.06) / 0.06) * s((q[:, 1] - DUCT[1] + 0.08) / 0.08)
    return MAIN_ROOF + (DUCT_ROOF - MAIN_ROOF) * duct


def main_liner(grid):
    """Liner of the port main well, on the opening's own nodes: the skin's thickness, walls, roof."""
    c = grid.col
    pts, nrm, _ = grid.side_rim_loop(c["g0"], c["g1"], hg.B_MAIN_OUT, hg.B_WELL)
    a, b = c["g1"] - c["g0"], hg.B_WELL - hg.B_MAIN_OUT
    deep = pts - DEEP * nrm
    top = main_roof(deep[:, :2])
    rings = [pts, pts - SKIN * nrm, deep, np.column_stack([deep[:, :2], 0.5 * (deep[:, 2] + top)]),
             np.column_stack([deep[:, :2], top])]
    walls = loft(rings, caps=(None, "grid"), grid=(a, b), mats=["belly", "bay", "bay", "bay"])
    n = len(rings) * len(pts)
    walls.v[n:, 2] = main_roof(walls.v[n:, :2])           # the roof's inner nodes, on the roof
    return Geo().add(turned_out(walls))


def nose_liner(grid):
    """Liner of the nose gear well, on the opening's own nodes: the skin's thickness, walls, roof."""
    pts, nrm, _ = grid.rim_loop(grid.col["w0"], grid.col["w1"])
    k = hg.B_MAX - hg.B_WELL                               # the port front corner of the opening
    pts, nrm = np.roll(pts, -k, axis=0), np.roll(nrm, -k, axis=0)
    a = grid.col["w1"] - grid.col["w0"]
    b = len(pts) // 2 - a
    deep = pts - DEEP * nrm
    rings = [pts, pts - SKIN * nrm, deep,
             np.column_stack([deep[:, :2], np.full(len(pts), 0.5 * (deep[:, 2].mean() + NOSE_ROOF))]),
             np.column_stack([deep[:, :2], np.full(len(pts), NOSE_ROOF)])]
    walls = loft(rings, caps=(None, "grid"), grid=(a, b), mats=["belly", "bay", "bay", "bay"])
    g = Geo().add(turned_out(walls))
    half = hg.NOSE_WELL_HALF - 0.002
    for y in NOSE_FRAMES:
        g.add(box(2.0 * half, 0.024, 0.030, 0.003), "bay", shift(0.0, y, NOSE_ROOF - 0.015))
    return g


# =============================================================================================
# Assembly
# =============================================================================================
_RIG = {}                                  # what build() made: self_check replays the motion from it
# leaf: (angle at rest, angle for the swing, opening span, closing span), degrees and phases. A leaf the
# leg passes through hangs beside it on the ground, like a fence; the others are shut at rest. The
# outer main leaves open wide only while the pad passes their hinge.
DOOR_PLAN = {"Avant_Av": (0.0, 95.0, (0.00, 0.10), (0.90, 1.00)),
             "Avant_Ar": (95.0, 95.0, (0.00, 0.10), (0.90, 1.00)),
             "Principal_Av_Ext": (100.0, 140.0, (0.00, 0.10), (0.90, 1.00)),
             "Principal_Av_Int": (0.0, 100.0, (0.00, 0.10), (0.86, 0.96)),
             "Principal_Ar_Ext": (0.0, 140.0, (0.00, 0.10), (0.90, 1.00)),
             "Principal_Ar_Int": (0.0, 100.0, (0.03, 0.13), (0.86, 0.96))}
NOSE_STAGGER = 0.04                        # the starboard nose leaves open after the port ones and close before


def hinge_line(grid, key, sign, h0, h1):
    """The line a gear door turns about: panels' hinge chord, turned towards the fore-and-aft axis
    until it slopes at most HINGE_TILT against the leaf's ends, so they do not slide across their
    gap, then moved out under the leaf's rim until the whole hinge edge lies inside it. On a rim
    that curves or slopes, a leaf turning about the bare chord would enter the skin."""
    a0, a1, b0, b1 = grid.door_leaves()[key]
    b = b0 if key.startswith("Avant") or key.endswith("Ext") else b1            # panels.gear_doors' rim
    flip = np.array([sign, 1.0, 1.0])
    rim, out = grid.points[a0:a1 + 1, b] * flip, unit((grid.normals[a0:a1 + 1, b] * flip).mean(axis=0))
    chord, along = unit(h1 - h0), np.array([0.0, 1.0, 0.0])
    tilt = math.hypot(chord[0], chord[2]) / chord[1]
    axis = unit(along + min(1.0, HINGE_TILT / max(tilt, 1e-9)) * (chord - along))
    mid, half = 0.5 * (h0 + h1), 0.5 * float(np.linalg.norm(h1 - h0))
    rel = rim - mid
    off = (rel - np.outer(rel @ axis, axis)) @ out                               # + : outside the line
    shift = (off.max() + HINGE_CLEAR) / (1.0 - float(out @ axis) ** 2)
    centre = mid + shift * out
    return centre - half * axis, centre + half * axis


def door_angle(u, key, tag):
    """Opening of a gear door leaf at phase u, radians from shut; tag G port, D starboard."""
    rest, swing, opening, closing = DOOR_PLAN[key]
    lag = NOSE_STAGGER if key.startswith("Avant") and tag == "D" else 0.0
    a = rest + (swing - rest) * anim.ease(u, opening[0] + lag, opening[1] + lag)
    return math.radians(a) * (1.0 - anim.ease(u, closing[0] - lag, closing[1] - lag))


def build(mats, grid):
    """Build the gear in the current scene, keyed on the clip "Train"; returns its objects."""
    mats = gear_materials(mats)
    hull = grid.hull
    nose, main = nose_leg(hull), main_leg(hull)
    print(f"GEAR_LEGS nose: pad at y {nose.A0[1]:.3f}, legs {nose.L0:.3f} to {nose.L1:.3f} m, swing "
          f"{math.degrees(nose.theta):.1f} deg; main: pad at ({main.A0[0]:.3f}, {main.A0[1]:.3f}), legs "
          f"{main.L0:.3f} to {main.L1:.3f} m, swing {math.degrees(main.theta):.1f} deg about an axis canted "
          f"{math.degrees(MAIN_CANT):.0f} deg")
    nose_parts, nose_fixed = leg_parts(nose)
    main_parts, main_fixed = leg_parts(main)
    port_bay = main_liner(grid)
    bays = Geo().merge(port_bay).merge(port_bay.mirrored()).merge(nose_liner(grid))

    pivots = lambda leg: {"Jambe": leg.T, "Coulisse": leg.A0, "Compas_Haut": leg.B, "Compas_Bas": leg.C0,
                          "Verin": leg.P, "Tige": leg.Q0, "Patin": leg.A0}
    objs, legs = [], []
    for tag, leg, parts, fixed, mirror in (("Train_Avant", nose, nose_parts, nose_fixed, False),
                                           ("Train_Principal_G", main, main_parts, main_fixed, False),
                                           ("Train_Principal_D", main, main_parts, main_fixed, True)):
        legs.append((tag, leg, mirror))
        for name, geo in parts.items():
            pose = lambda u, n=name, lg=leg: lg.poses(u)[n]
            origin = pivots(leg)[name]
            if mirror:
                geo, pose, origin = geo.mirrored(), mirrored_pose(pose), origin * (-1.0, 1.0, 1.0)
            obj = to_object(f"{tag}_{name}", geo, mats, origin)
            anim.bake(obj, CLIP, pose)
            objs.append(obj)
        objs.append(to_object(f"{tag}_Fixe", fixed.mirrored() if mirror else fixed, mats))   # bearings, clevis
    objs.append(to_object("Baies_Trains", bays, mats))

    doors = []
    hinges = panels.gear_doors(grid)
    for name, (h0, h1) in hinges.items():
        door = bpy.data.objects.get(name)
        if door is None:                                   # the panels module was not built
            continue
        key, tag = name[len("Trappe_Train_"):-2], name[-1]
        h0, h1 = hinge_line(grid, key, 1.0 if tag == "G" else -1.0, h0, h1)
        print(f"GEAR_DOOR {name}: hinge {1e3 * float(np.linalg.norm(h0 - hinges[name][0])):.1f} and "
              f"{1e3 * float(np.linalg.norm(h1 - hinges[name][1])):.1f} mm out of panels' chord")
        centre = np.mean([tuple(door.matrix_world @ v.co) for v in door.data.vertices], axis=0)
        trial = anim.about(h0, h1 - h0, 0.3)[:3] @ np.append(centre, 1.0)
        turn = 1.0 if trial[2] < centre[2] else -1.0                         # the free edge goes down
        pose = lambda u, h0=h0, axis=h1 - h0, turn=turn, key=key, tag=tag: anim.about(h0, axis, turn * door_angle(u, key, tag))
        rest = pose(0.0)                                   # a leaf the leg passes through stands open at rest
        door.matrix_world = Matrix(rest.tolist()) @ door.matrix_world
        relative = lambda u, pose=pose, back=np.linalg.inv(rest): pose(u) @ back
        anim.bake(door, CLIP, relative)
        doors.append((name, relative))
    _RIG.update(legs=legs, doors=doors, hull=hull)
    return objs


# =============================================================================================
# Self-check
# =============================================================================================
def mesh_facts(obj):
    """Measured facts of one mesh object, in world coordinates at rest: counts and defects, no judgement."""
    me = obj.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    mw = np.array(obj.matrix_world)
    v = v.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    faces = [tuple(p.vertices) for p in me.polygons]
    fn = np.array([newell(v[list(f)]) for f in faces])
    area = np.linalg.norm(fn, axis=1)
    fn = fn / np.maximum(area, 1e-30)[:, None]
    used = np.zeros(len(v), dtype=bool)
    edge_faces, directed = {}, {}
    short = 0
    for fi, f in enumerate(faces):
        used[list(f)] = True
        for a, b in zip(f, f[1:] + f[:1]):
            edge_faces.setdefault((a, b) if a < b else (b, a), []).append(fi)
            directed[(a, b)] = directed.get((a, b), 0) + 1
            short += float(np.linalg.norm(v[a] - v[b])) < 1e-6
    # shells: vertices joined by faces
    parent = np.arange(len(v))

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for f in faces:
        r0 = root(f[0])
        for i in f[1:]:
            parent[root(i)] = r0
    shell = np.array([root(i) for i in range(len(v))])
    boundary = [e for e, fs in edge_faces.items() if len(fs) == 1]
    open_shells = {shell[e[0]] for e in boundary}
    volume = {}
    for fi, f in enumerate(faces):
        s = shell[f[0]]
        volume[s] = volume.get(s, 0.0) + float(v[f[0]] @ fn[fi]) * area[fi] / 3.0
    razor = 0
    for (a, b), fs in edge_faces.items():
        if len(fs) != 2:
            continue
        if float(fn[fs[0]] @ fn[fs[1]]) < math.cos(SHARP_ANGLE):
            centre = v[list(faces[fs[1]])].mean(axis=0) - v[list(faces[fs[0]])].mean(axis=0)
            razor += float(centre @ fn[fs[0]]) < -1e-9            # convex and unbevelled
    key = np.round(v / 2e-5).astype(np.int64)
    doubles = len(key) - len(np.unique(key, axis=0))
    return {
        "verts": len(v), "faces": len(faces), "tris": int(sum(len(f) - 2 for f in faces)),
        "ngons": int(sum(len(f) > 4 for f in faces)),
        "loose_verts": int((~used).sum()),
        "degenerate_faces": int((area < 1e-9).sum()), "zero_edges": int(short),
        "doubled_verts": int(doubles),
        "non_manifold_edges": int(sum(len(fs) > 2 for fs in edge_faces.values())),
        "flipped_edges": int(sum(c > 1 for c in directed.values())),
        "boundary_edges": len(boundary),
        "shells": len(set(shell[used])), "open_shells": len(open_shells),
        "inverted_closed_shells": int(sum(vol < 0.0 for s, vol in volume.items() if s not in open_shells)),
        "razor_edges": int(razor),
        "uv": len(me.uv_layers) == 1, "custom_normals": bool(me.has_custom_normals),
        "z_min": float(v[:, 2].min()),
        "sole": v[np.abs(v[:, 2] - v[:, 2].min()) < 1e-3],
        "points": v,
    }


def _mirror_error(a, b):
    """Largest distance from a point of `a`, mirrored across x = 0, to the nearest point of `b`."""
    from mathutils import kdtree
    tree = kdtree.KDTree(len(b))
    for i, p in enumerate(b):
        tree.insert(p, i)
    tree.balance()
    return max(tree.find((-p[0], p[1], p[2]))[2] for p in a)


def _local(obj):
    """Vertices (object space, homogeneous) and faces of a mesh object."""
    me = obj.data
    v = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", v)
    return np.column_stack([v.reshape(-1, 3), np.ones(len(me.vertices))]), [tuple(p.vertices) for p in me.polygons]


def envelope(p, skin_z):
    """Points of the gear inside the hull that leave the volume left to it: {fault: count}."""
    q = p[p[:, 2] > skin_z(p) + 0.002]
    return {"above the free volume": int((q[:, 2] > FREE_TOP).sum()),
            "in the thruster ducts": int(((np.abs(q[:, 0]) >= DUCT[0]) & (q[:, 1] >= DUCT[1])
                                          & (q[:, 2] > DUCT_ROOF + 0.02)).sum()),
            "within 3 cm of the airlock": int(((np.abs(q[:, 0]) < AIRLOCK[0] + 0.03) & (q[:, 2] > AIRLOCK[1] - 0.03)).sum())}


def motion_check(phases=25, verbose=True):
    """Replay the clip from the rig: joints, ground, envelope, the stowed state, interference.
    Returns (facts, problems).

    Two parts joined by a pin may touch inside the pin's cylinder (a pin through an eye, a tube in
    its bearing); anywhere else a pair of crossing faces is a collision. The scene's other meshes
    that reach into the gear's sweep (the hull first) are tested against every moving part.
    """
    from mathutils.bvhtree import BVHTree
    problems, facts = [], {"pin_error": 0.0, "axis_error": 0.0}
    us = np.linspace(0.0, 1.0, phases)
    # 1. joints: each pin carried by both its parts, each slide kept on one line
    for tag, leg, mirror in _RIG["legs"]:
        for a, b, p, axis, kind, _, _ in leg.pins():
            for u in us:
                poses = leg.poses(u)
                Ma, Mb = poses[a], (poses[b] if b else np.eye(4))
                pa, pb = Ma[:3] @ np.append(p, 1.0), Mb[:3] @ np.append(p, 1.0)
                da, db = unit(Ma[:3, :3] @ axis), unit(Mb[:3, :3] @ axis)
                err = np.linalg.norm(pa - pb) if kind == "pin" else np.linalg.norm(np.cross(pb - pa, da))
                facts["pin_error"] = max(facts["pin_error"], float(err))
                facts["axis_error"] = max(facts["axis_error"], float(np.linalg.norm(np.cross(da, db))))
    if facts["pin_error"] > 1e-6 or facts["axis_error"] > 1e-6:
        problems.append(f"joints drift: {facts['pin_error'] * 1e3:.4f} mm, {facts['axis_error']:.2e} rad")
    # every moving object with its pose, the static ones at rest
    movers = {}
    for tag, leg, mirror in _RIG["legs"]:
        for part in leg.poses(0.0):
            pose = lambda u, lg=leg, pt=part: lg.poses(u)[pt]
            movers[f"{tag}_{part}"] = (mirrored_pose(pose) if mirror else pose, tag)
    for name, pose in _RIG["doors"]:
        movers[name] = (pose, "doors")
    gear_static = [n for n in ["Baies_Trains"] + [f"{t}_Fixe" for t, _, _ in _RIG["legs"]] if n in bpy.data.objects]
    geo = {n: _local(bpy.data.objects[n]) for n in list(movers) + gear_static}
    rest = {n: np.array(bpy.data.objects[n].matrix_world) for n in geo}
    world = lambda n, M: (geo[n][0] @ (M @ rest[n]).T)[:, :3]
    skin_z = skin_table(_RIG["hull"])
    gear = [n for n in movers if n.startswith("Train_")] + gear_static
    # 2. ground, the free volume, the glazed prow and the nose well, phase by phase
    lowest = {n: math.inf for n in movers}
    lo, hi = np.full(3, math.inf), np.full(3, -math.inf)
    faults, box = {}, np.full(3, -math.inf)
    facts["foremost"] = math.inf
    for u in us:
        for n in gear + [m for m in movers if m not in gear]:
            p = world(n, movers[n][0](u) if n in movers else np.eye(4))
            lo, hi = np.minimum(lo, p.min(axis=0)), np.maximum(hi, p.max(axis=0))
            if n in movers:
                lowest[n] = min(lowest[n], float(p[:, 2].min()))
            if n not in gear:
                continue
            for k, count in envelope(p, skin_z).items():
                if count:
                    faults.setdefault((n, k), u)
            facts["foremost"] = min(facts["foremost"], float(p[:, 1].min()))
            if n.startswith(("Train_Avant", "Baies_")):
                q = p[(p[:, 2] > skin_z(p) + 0.002) & (np.abs(p[:, 0]) < 1.0) & (p[:, 1] < -1.0)]
                if len(q):
                    box = np.maximum(box, [np.abs(q[:, 0]).max(), max(NOSE_WELL_BOX[1][0] - q[:, 1].min(),
                                                                       q[:, 1].max() - NOSE_WELL_BOX[1][1]), q[:, 2].max()])
    for n, z in lowest.items():
        if z < GROUND - 1e-6:
            problems.append(f"{n} goes {1e3 * (GROUND - z):.1f} mm under the ground")
    for (n, k), u in sorted(faults.items()):
        problems.append(f"{n}: {k} (first at u = {u:.2f})")
    if facts["foremost"] < NOSE_LIMIT:
        problems.append(f"the gear reaches y {facts['foremost']:.3f}, forward of {NOSE_LIMIT}")
    facts["lowest"], facts["nose_well"] = lowest, box     # |x| max, y beyond the limits, z max
    if box[0] > NOSE_WELL_BOX[0] or box[1] > 0.0 or box[2] > NOSE_WELL_BOX[2]:
        problems.append(f"the nose gear leaves its well: |x| {box[0]:.3f}, y {box[1]:+.3f} beyond, z {box[2]:.3f}")
    # 3. stowed: nothing below the skin; the gear's clearance to the skin and to its shut doors
    shut = {n: world(n, movers[n][0](1.0)) for n in movers if n not in gear}
    verts, faces = [], []
    for n, w in shut.items():
        faces += [tuple(i + len(verts) for i in f) for f in geo[n][1]]
        verts += [tuple(q) for q in w]
    door_tree = BVHTree.FromPolygons(verts, faces) if verts else None
    facts["below_skin"], facts["stowed"] = {}, {}
    for n in list(movers) + gear_static:
        p = shut[n] if n in shut else world(n, movers[n][0](1.0) if n in movers else np.eye(4))
        under = float((skin_z(p) - p[:, 2]).max())
        facts["below_skin"][n] = under
        if under > 5e-4:
            problems.append(f"{n}: {1e3 * under:.1f} mm below the skin at u = 1")
    for tag, _, _ in _RIG["legs"]:
        p = np.vstack([world(n, movers[n][0](1.0)) for n in movers if n.startswith(tag + "_")])
        gap = float((p[:, 2] - skin_z(p)).min())
        near = min(door_tree.find_nearest(tuple(q))[3] for q in p) if door_tree else math.nan
        facts["stowed"][tag] = (gap, near)
    sweep = (lo - 0.05, hi + 0.05)
    # 4. interference, phase by phase, with the scene's other meshes that reach into the sweep
    others = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.name in geo or o.name.startswith("Train_"):
            continue
        corners = np.array([tuple(o.matrix_world @ Vector(c)) for c in o.bound_box])
        if (corners.max(axis=0) >= sweep[0]).all() and (corners.min(axis=0) <= sweep[1]).all():
            others.append(o.name)
            geo[o.name] = _local(o)
            rest[o.name] = np.array(o.matrix_world)
    statics = gear_static + others

    def zones(u):
        out = {}
        for tag, leg, mirror in _RIG["legs"]:
            poses = leg.poses(u)
            for a, b, p, axis, kind, r, half in leg.pins():
                if kind == "pin":
                    c, d = poses[a][:3] @ np.append(p, 1.0), unit(poses[a][:3, :3] @ axis)
                    if mirror:
                        c, d = c * (-1.0, 1.0, 1.0), d * (-1.0, 1.0, 1.0)
                    key = frozenset((f"{tag}_{a}", f"{tag}_{b or 'Fixe'}"))
                    out.setdefault(key, []).append((c, d, r, half))
        return out
    static_trees = {n: BVHTree.FromPolygons([tuple(q) for q in world(n, np.eye(4))], geo[n][1]) for n in statics}
    order = list(movers)
    pairs = [(m, s) for m in order for s in statics]
    pairs += [(m1, m2) for i, m1 in enumerate(order) for m2 in order[i + 1:]]
    worst = {}
    for u in us:
        pts = {n: world(n, pose(u)) for n, (pose, _) in movers.items()}
        trees = {n: BVHTree.FromPolygons([tuple(q) for q in w], geo[n][1]) for n, w in pts.items()}
        allowed = zones(u)
        for m1, m2 in pairs:
            hits = trees[m1].overlap(static_trees[m2] if m2 in static_trees else trees[m2])
            zone = allowed.get(frozenset((m1, m2)), [])
            if hits and zone:
                faces1, w1 = geo[m1][1], pts[m1]

                def outside(f):
                    c = w1[list(faces1[f])].mean(axis=0)
                    for p, d, r, half in zone:
                        along = float((c - p) @ d)
                        if abs(along) < half and np.linalg.norm(c - p - along * d) < r:
                            return False
                    return True
                hits = [h for h in hits if outside(h[0])]
            if len(hits) > worst.get((m1, m2), (0, 0.0))[0]:
                worst[(m1, m2)] = (len(hits), float(u))
    for (m1, m2), (count, u) in sorted(worst.items()):
        problems.append(f"{m1} cuts {m2}: {count} face pairs at worst (u = {u:.2f})")
    facts["collisions"] = {f"{a} / {b}": c for (a, b), (c, _) in worst.items()}
    if verbose:
        print(f"GEAR_MOTION joints over {phases} phases: pin error {facts['pin_error'] * 1e6:.3f} um, "
              f"axis error {facts['axis_error']:.2e} rad")
        for n, z in sorted(lowest.items()):
            print(f"GEAR_MOTION {n}: lowest point {z:.4f}, {1e3 * (z - GROUND):+.1f} mm from the ground")
        for tag, (gap, near) in facts["stowed"].items():
            print(f"GEAR_MOTION {tag} stowed: {1e3 * gap:.1f} mm above the skin at least, "
                  f"{1e3 * near:.1f} mm from its shut doors")
        print(f"GEAR_MOTION below the skin at u = 1, worst: {1e3 * max(facts['below_skin'].values()):+.2f} mm "
              f"({max(facts['below_skin'], key=facts['below_skin'].get)})")
        print(f"GEAR_MOTION free volume: {len(faults)} faults; foremost point y {facts['foremost']:.3f} "
              f"(limit {NOSE_LIMIT})")
        print(f"GEAR_MOTION nose gear inside the hull: |x| <= {box[0]:.3f}, {box[1]:+.3f} m past its y limits, "
              f"top z {box[2]:.3f}")
        print(f"GEAR_MOTION interference: {len(worst)} pairs of parts cross, {len(pairs)} pairs tested, "
              f"statics {statics}")
    return facts, problems


def self_check(objs, verbose=True, phases=25):
    """Numeric invariants of the built gear, at rest and over the clip. Prints one line per fact,
    raises on a broken one. A pass here is necessary, not sufficient: the review images are the proof.

    At rest: mesh defects, UVs and normals, soles on GROUND, mirror symmetry, the triangle budget.
    Over `phases` samples of the clip (motion_check): every pin carried by both its parts, the
    lowest point of every moving part against GROUND, the gear inside the hull's free volume and
    forward limit, the nose gear inside its well, nothing below the skin at u = 1, and crossing
    faces between parts, the doors, the wells, the hull and its other meshes.
    """
    bpy.context.scene.frame_set(0)
    facts = {o.name: mesh_facts(o) for o in objs}
    problems = []
    for name, f in facts.items():
        for key in ("ngons", "loose_verts", "degenerate_faces", "zero_edges", "doubled_verts",
                    "non_manifold_edges", "flipped_edges", "inverted_closed_shells"):
            if f[key]:
                problems.append(f"{name}: {key} = {f[key]}")
        if not (f["uv"] and f["custom_normals"]):
            problems.append(f"{name}: missing UVs or custom normals")
        if verbose:
            print(f"GEAR_CHECK {name}: tris={f['tris']} verts={f['verts']} shells={f['shells']} "
                  f"open_shells={f['open_shells']} boundary_edges={f['boundary_edges']} razor_edges={f['razor_edges']}")
    for name in [n for n in facts if n.endswith("_Patin")]:
        sole = facts[name]["sole"]
        off = float(np.abs(sole[:, 2] - GROUND).max())
        if off > 1e-4:
            problems.append(f"{name}: sole {off * 1000:.3f} mm off the ground plane")
        if verbose:
            print(f"GEAR_CHECK {name}: sole on z={GROUND:.4f} within {off * 1e6:.1f} um, "
                  f"{np.ptp(sole[:, 0]):.3f} x {np.ptp(sole[:, 1]):.3f} m, centre x {sole[:, 0].mean():+.3f}")
    pairs = [(n, n.replace("_G_", "_D_")) for n in facts if n.startswith("Train_Principal_G_")]
    pairs += [("Baies_Trains", "Baies_Trains")]
    for a, b in pairs:
        if a in facts and b in facts:
            err = max(_mirror_error(facts[a]["points"], facts[b]["points"]),
                      _mirror_error(facts[b]["points"], facts[a]["points"]))
            if err > 1e-5:
                problems.append(f"{a} / {b}: mirror error {err * 1000:.4f} mm")
            if verbose:
                print(f"GEAR_CHECK {a} / {b}: mirror error {err * 1e6:.2f} um")
    total = sum(f["tris"] for f in facts.values())
    if total > TRI_BUDGET:
        problems.append(f"{total} triangles exceed the budget of {TRI_BUDGET}")
    if verbose:
        print(f"GEAR_CHECK total triangles {total} / {TRI_BUDGET} in {len(facts)} objects")
    motion, more = motion_check(phases, verbose)
    problems += more
    for line in problems:
        print("GEAR_PROBLEM", line)
    assert not problems, "; ".join(problems)
    return {"triangles": total, "motion": motion,
            "objects": {n: {k: v for k, v in f.items() if k not in ("sole", "points")} for n, f in facts.items()}}
