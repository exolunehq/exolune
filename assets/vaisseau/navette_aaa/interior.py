"""Cockpit and passenger cabin of the Navette AAA: seats, flight station, floor, liners, bulkhead.

build(mats, hull) returns the objects of the collection 05_Cabine_Et_Cockpit; it needs no other
object in the scene. self_check(objs, hull) measures them against the hull it is given.

Every part is a loft: rings joined by quads, closed by quad grid caps. Bevels and rounded edges are
rings, so no edge is left sharp; there is no boolean, no n-gon and no triangle. Upholstery is the
same loft with its face lattice given: seams lie on lattice lines, panels swell between them, and
the edge rolls over into a skirt that ends inside the shell framing the pad; piping cords lie in the
seams and belts are straps laid on the pads. Liners are sheets laid 5 to 7 cm under the hull skin,
with a rolled edge standing just inside the glazing. Forward of the prow line the nose is a glass
bubble: a ring frame closes the hull along that line, the liners start on it, and the floor runs on
into the bubble as a free deck carried by one keel spine.
Frame: metres, nose -Y, up +Z, port +X; the pilot looks to -Y. UVs are in metres, except the three
screens (0-1, upright for the pilot). Only numpy and bpy are needed.
"""
import math
import os

import bpy
import numpy as np

import hullgrid as hg
import materials as matlib
import meshkit
from surface import T1, T2

COL = "05_Cabine_Et_Cockpit"
FLOOR = -1.24                      # top of the floor plate


# ---- small numeric helpers ------------------------------------------------------------------
def puff(d):
    """Pillow profile: 0 on a seam, 1 one unit away, leaving the seam upright."""
    d = np.clip(d, 0.0, 1.0)
    return np.sqrt(1.0 - (1.0 - d) ** 2)


def ramp(x, xp, fp):
    """Plateaus fp at the keys xp, joined by smoothstep ramps."""
    x, xp, fp = np.asarray(x, dtype=float), np.asarray(xp, dtype=float), np.asarray(fp, dtype=float)
    k = np.clip(np.searchsorted(xp, x) - 1, 0, len(xp) - 2)
    t = np.clip((x - xp[k]) / (xp[k + 1] - xp[k]), 0.0, 1.0)
    return fp[k] + (fp[k + 1] - fp[k]) * t * t * (3.0 - 2.0 * t)


def hermite(x, xp, fp):
    """Smooth curve through the keys (xp, fp): cubic Hermite with centred slopes."""
    x, xp, fp = np.asarray(x, dtype=float), np.asarray(xp, dtype=float), np.asarray(fp, dtype=float)
    slope = np.gradient(fp, xp)
    k = np.clip(np.searchsorted(xp, x) - 1, 0, len(xp) - 2)
    h = xp[k + 1] - xp[k]
    t = np.clip((x - xp[k]) / h, 0.0, 1.0)
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * fp[k] + (t ** 3 - 2 * t ** 2 + t) * h * slope[k]
            + (-2 * t ** 3 + 3 * t ** 2) * fp[k + 1] + (t ** 3 - t ** 2) * h * slope[k + 1])


def lines(base, fine=(), gap=0.012):
    """Sorted lattice lines: the fine lines, and the base lines farther than gap from them."""
    fine = np.asarray(sorted(fine), dtype=float)
    keep = [x for x in base if not len(fine) or np.abs(fine - x).min() > gap]
    return np.array(sorted(set(keep) | set(fine.tolist())))


def seam(s):
    """The five lattice lines that carve one seam."""
    return [s - 0.024, s - 0.006, s, s + 0.006, s + 0.024]


class Path2:
    """Polyline with rounded corners in a plane, by arc length. at(s) extends straight past both ends."""

    def __init__(self, pts, radii=None):
        p = np.asarray(pts, dtype=float)
        radii = np.zeros(len(p)) if radii is None else radii
        self.seg, prev = [], p[0]
        for k in range(1, len(p) - 1):
            u_in, u_out = p[k] - p[k - 1], p[k + 1] - p[k]
            u_in, u_out = u_in / np.linalg.norm(u_in), u_out / np.linalg.norm(u_out)
            turn = math.acos(float(np.clip(u_in @ u_out, -1.0, 1.0)))
            if radii[k] <= 0.0 or turn < 1e-6:
                self.seg.append(("L", prev, p[k], float(np.linalg.norm(p[k] - prev))))
                prev = p[k]
                continue
            r = radii[k]
            d = r * math.tan(0.5 * turn)
            side = 1.0 if u_in[0] * u_out[1] - u_in[1] * u_out[0] > 0 else -1.0
            a = p[k] - u_in * d
            centre = a + r * side * np.array([-u_in[1], u_in[0]])
            self.seg.append(("L", prev, a, float(np.linalg.norm(a - prev))))
            self.seg.append(("A", centre, (r, math.atan2(a[1] - centre[1], a[0] - centre[0]), side), r * turn))
            prev = p[k] + u_out * d
        self.seg.append(("L", prev, p[-1], float(np.linalg.norm(p[-1] - prev))))
        self.marks = np.concatenate([[0.0], np.cumsum([s[3] for s in self.seg])])
        self.length = float(self.marks[-1])

    def at(self, s):
        """Positions and unit tangents, (n, 2) each."""
        s = np.atleast_1d(np.asarray(s, dtype=float))
        pos, tan = np.zeros((len(s), 2)), np.zeros((len(s), 2))
        sc = np.clip(s, 0.0, self.length)
        for (kind, a, b, length), s0 in zip(self.seg, self.marks[:-1]):
            m = sc >= s0 - 1e-12
            if not m.any() or length <= 0.0:
                continue
            u = np.minimum(sc[m] - s0, length)
            if kind == "L":
                t = (b - a) / length
                pos[m], tan[m] = a + u[:, None] * t, t
            else:
                r, a0, side = b
                ang = a0 + side * u / r
                pos[m] = a + r * np.stack([np.cos(ang), np.sin(ang)], axis=1)
                tan[m] = side * np.stack([-np.sin(ang), np.cos(ang)], axis=1)
        return pos + (s - sc)[:, None] * tan, tan

    def s_where(self, axis, value):
        """Arc length at which the coordinate of the given axis first reaches value."""
        s = np.linspace(0.0, self.length, 4000)
        c = self.at(s)[0][:, axis] - value
        k = int(np.argmax(c[:-1] * c[1:] <= 0.0))
        return float(s[k] + (s[k + 1] - s[k]) * c[k] / (c[k] - c[k + 1]))


# ---- mesh pieces ----------------------------------------------------------------------------
class M:
    """Quad mesh piece: vertices, quads, UVs per face corner, a material key per face."""

    def __init__(self, v, f, uv=None, mat="graphite", hard=True):
        self.v = np.array(v, dtype=float).reshape(-1, 3)
        self.f = np.array(f, dtype=np.int64).reshape(-1, 4)
        self.uv = np.zeros((len(self.f), 4, 2)) if uv is None else np.array(uv, dtype=float).reshape(-1, 4, 2)
        self.m = np.empty(len(self.f), dtype=object)
        self.m[:] = mat
        self.hard = np.full(len(self.v), bool(hard))   # hard: the large faces rule the normals
        self.tag = {}

    def copy(self):
        c = M(self.v, self.f, self.uv, hard=True)
        c.m, c.hard, c.tag = self.m.copy(), self.hard.copy(), dict(self.tag)
        return c

    def move(self, x=0.0, y=0.0, z=0.0):
        self.v += (x, y, z)
        return self

    def place(self, origin, ex, ey, ez=None):
        """Send the local axes to ex, ey, ez (unit vectors) at origin."""
        ex, ey = np.asarray(ex, dtype=float), np.asarray(ey, dtype=float)
        ez = np.cross(ex, ey) if ez is None else np.asarray(ez, dtype=float)
        self.v = np.asarray(origin, dtype=float) + self.v[:, :1] * ex + self.v[:, 1:2] * ey + self.v[:, 2:] * ez
        if np.dot(np.cross(ex, ey), ez) < 0.0:
            self.flip()
        return self

    def flip(self):
        self.f, self.uv = self.f[:, ::-1].copy(), self.uv[:, ::-1].copy()
        return self

    def mirror(self):
        c = self.copy()
        c.v[:, 0] *= -1.0
        return c.flip()

    def volume(self):
        p = self.v[self.f]
        return float((np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2]))
                      + np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 2], p[:, 3]))).sum() / 6.0)

    def outward(self):
        """Closed shell: wind the faces outward."""
        return self.flip() if self.volume() < 0.0 else self

    def facing(self, direction, face=0):
        """Open sheet: wind the faces so that the given face looks along direction."""
        p = self.v[self.f[face]]
        n = np.cross(p[2] - p[0], p[3] - p[1])
        return self.flip() if np.dot(n, direction) < 0.0 else self


def join(parts):
    parts = [p for p in parts if p is not None]
    off = np.concatenate([[0], np.cumsum([len(p.v) for p in parts])])
    out = M(np.vstack([p.v for p in parts]), np.vstack([p.f + o for p, o in zip(parts, off)]),
            np.vstack([p.uv for p in parts]))
    out.m = np.concatenate([p.m for p in parts])
    out.hard = np.concatenate([p.hard for p in parts])
    return out


def both(piece):
    """The piece and its mirror image across the centre plane."""
    return join([piece, piece.mirror()])


def grid_uv(p):
    """Mean arc lengths along both directions of a node grid (m, k, 3)."""
    du = np.linalg.norm(np.diff(p, axis=1), axis=2).mean(axis=0)
    dv = np.linalg.norm(np.diff(p, axis=0), axis=2).mean(axis=1)
    return np.concatenate([[0.0], np.cumsum(du)]), np.concatenate([[0.0], np.cumsum(dv)])


def _cell_uv(u, v):
    u0, v0 = np.meshgrid(u[:-1], v[:-1])
    u1, v1 = np.meshgrid(u[1:], v[1:])
    return np.stack([np.stack([u0, v0], -1), np.stack([u1, v0], -1), np.stack([u1, v1], -1),
                     np.stack([u0, v1], -1)], axis=2).reshape(-1, 4, 2)


def _cap(ring, nrm, nu, nv, roll=0, bulge=0.0, interior=None):
    """Quad grid closing a ring of 2 (nu + nv) points. Returns the grid of codes (ring index, or
    K + k for the k-th new node), the new nodes and the cell UVs."""
    k_n = len(ring)
    assert k_n == 2 * (nu + nv), (k_n, nu, nv)
    r = (np.arange(k_n + 1) + roll) % k_n
    code = -np.ones((nv + 1, nu + 1), dtype=np.int64)
    code[0, :] = r[:nu + 1]
    code[:, nu] = r[nu:nu + nv + 1]
    code[nv, ::-1] = r[nu + nv:2 * nu + nv + 1]
    code[::-1, 0] = r[2 * nu + nv:]
    x = np.zeros((nv + 1, nu + 1, 3))
    edge = code >= 0
    x[edge] = ring[code[edge]]
    new = np.zeros((0, 3))
    if nu > 1 and nv > 1:
        if interior is None:
            arc = lambda line: np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))])
            frac = lambda line: arc(line) / max(arc(line)[-1], 1e-12)
            u = (0.5 * (frac(x[0]) + frac(x[nv])))[None, :, None]
            v = (0.5 * (frac(x[:, 0]) + frac(x[:, nu])))[:, None, None]
            fill = ((1 - v) * x[:1] + v * x[nv:] + (1 - u) * x[:, :1] + u * x[:, nu:]
                    - (1 - u) * (1 - v) * x[0, 0] - u * (1 - v) * x[0, nu] - (1 - u) * v * x[nv, 0] - u * v * x[nv, nu])
            fill = fill + bulge * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2) * nrm
            x[1:-1, 1:-1] = fill[1:-1, 1:-1]
        else:
            x[1:-1, 1:-1] = interior
        new = x[1:-1, 1:-1].reshape(-1, 3)
        code[1:-1, 1:-1] = k_n + np.arange(len(new)).reshape(nv - 1, nu - 1)
    return code, new, _cell_uv(*grid_uv(x))


def loft(rings, mat="graphite", caps=(None, None), closed=True, hard=True, colmat=None, capmat=None):
    """Quads between consecutive rings (m, K, 3). mat: one key, or one per ring step; colmat: one
    key per ring segment. A cap is None or (nu, nv, roll[, bulge[, interior]])."""
    rings = np.asarray(rings, dtype=float)
    m, k_n = rings.shape[:2]
    idx = np.arange(m * k_n).reshape(m, k_n)
    cols = np.arange(k_n if closed else k_n - 1)
    nxt = (cols + 1) % k_n
    faces = np.stack([idx[:-1][:, cols], idx[:-1][:, nxt], idx[1:][:, nxt], idx[1:][:, cols]], axis=-1).reshape(-1, 4)
    du = np.linalg.norm(rings[:, nxt] - rings[:, cols], axis=2).mean(axis=0)
    dv = np.linalg.norm(rings[1:] - rings[:-1], axis=2).mean(axis=1)
    uv = _cell_uv(np.concatenate([[0.0], np.cumsum(du)]), np.concatenate([[0.0], np.cumsum(dv)]))
    keys = np.empty((m - 1, len(cols)), dtype=object)
    if colmat is not None:
        keys[:] = np.asarray(colmat, dtype=object)[None, :]
    elif isinstance(mat, str):
        keys[:] = mat
    else:
        keys[:] = np.asarray(mat, dtype=object)[:, None]
    verts, fs, uvs, ms = [rings.reshape(-1, 3)], [faces], [uv], [keys.reshape(-1)]
    tag = {"side": slice(0, len(faces))}
    n_v, n_f = m * k_n, len(faces)
    centre = rings.mean(axis=1)
    for name, end, other, spec in (("cap0", 0, 1, caps[0]), ("cap1", m - 1, m - 2, caps[1])):
        if spec is None:
            continue
        ring = rings[end]
        nrm = np.cross(ring - ring.mean(axis=0), np.roll(ring, -1, axis=0) - ring.mean(axis=0)).sum(axis=0)
        nrm = nrm / max(np.linalg.norm(nrm), 1e-12)
        if np.dot(nrm, centre[end] - centre[other]) < 0.0:
            nrm = -nrm
        code, new, cuv = _cap(ring, nrm, *spec)
        gid = np.where(code < k_n, idx[end][np.minimum(code, k_n - 1)], n_v + code - k_n)
        cf = np.stack([gid[:-1, :-1], gid[:-1, 1:], gid[1:, 1:], gid[1:, :-1]], axis=-1).reshape(-1, 4)
        if end == 0:
            cf, cuv = cf[:, ::-1], cuv[:, ::-1]
        verts.append(new)
        fs.append(cf)
        uvs.append(cuv)
        key = np.empty(len(cf), dtype=object)
        key[:] = capmat or (mat if isinstance(mat, str) else keys.reshape(-1)[0 if end == 0 else -1])
        ms.append(key)
        tag[name] = slice(n_f, n_f + len(cf))
        n_v, n_f = n_v + len(new), n_f + len(cf)
    out = M(np.vstack(verts), np.vstack(fs), np.vstack(uvs), hard=hard)
    out.m, out.tag = np.concatenate(ms), tag
    return out


def rrect(w, h, r, n=2):
    """Rounded rectangle w x h, 4 (n + 1) points, counter-clockwise from the lower right corner arc.

    Returns the points and the cap (nu, nv, roll) that fills it."""
    r = min(r, 0.499 * min(w, h))
    pts = []
    for k, (cx, cy) in enumerate(((1, -1), (1, 1), (-1, 1), (-1, -1))):
        a = (k - 1) * 0.5 * math.pi + np.linspace(0.0, 0.5 * math.pi, n + 1)
        pts.append(np.stack([cx * (0.5 * w - r) + r * np.cos(a), cy * (0.5 * h - r) + r * np.sin(a)], axis=1))
    cap = {1: (1, 3, 1), 2: (3, 3, 1), 4: (5, 5, 2)}[n]
    return np.vstack(pts), cap


def sweep(path, sections, right=(1.0, 0.0, 0.0)):
    """Rings of 2D sections (m, K, 2) set across a 3D path (m, 3): x along right, y along right x tangent."""
    path = np.asarray(path, dtype=float)
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    right = np.broadcast_to(np.asarray(right, dtype=float), path.shape)
    right = right - tan * np.einsum("ij,ij->i", right, tan)[:, None]
    right /= np.linalg.norm(right, axis=1, keepdims=True)
    up = np.cross(right, tan)
    sections = np.broadcast_to(np.asarray(sections, dtype=float), (len(path),) + np.shape(sections)[-2:])
    return path[:, None, :] + sections[..., :1] * right[:, None, :] + sections[..., 1:] * up[:, None, :]


def lattice(ah, b, rc=(0.0, 0.0)):
    """Reference lattice of a symmetric face: half lines ah from 0, lines b. rc rounds the corners
    at the start and at the end of b (a radius, or the two half axes along a and b): the border
    nodes of each corner box go to the arc."""
    a = ah if ah[0] < 0.0 else np.concatenate([-ah[:0:-1], ah])        # all the lines, or the half from 0
    aa, bb = (g.copy() for g in np.meshgrid(a, np.asarray(b, dtype=float)))
    na, nb = len(a) - 1, len(b) - 1
    for row, r, sb in ((0, rc[0], 1.0), (nb, rc[1], -1.0)):
        ra, rb = (r, r) if np.isscalar(r) else r
        if ra <= 0.0:
            continue
        for col, sa in ((0, -1.0), (na, 1.0)):
            ca, cb = sa * (ah[-1] - ra), b[row] + sb * rb
            edge = np.zeros(aa.shape, dtype=bool)
            edge[row, :] = edge[:, col] = True
            m = edge & ((aa - ca) * sa > -1e-9) & ((bb - cb) * sb < 1e-9)
            d = np.stack([(aa[m] - ca) / ra, (bb[m] - cb) / rb], axis=1)
            d /= np.linalg.norm(d, axis=1, keepdims=True)
            aa[m], bb[m] = ca + ra * d[:, 0], cb + rb * d[:, 1]
    return aa, bb


def border(na, nb):
    """Lattice indices (j, i) of the border loop, in the order the caps expect."""
    jj = np.concatenate([np.zeros(na, int), np.arange(nb), np.full(na, nb), np.arange(nb, 0, -1)])
    ii = np.concatenate([np.arange(na), np.full(nb, na), np.arange(na, 0, -1), np.zeros(nb, int)])
    return jj, ii


def loop_normals(p):
    """Outward unit normals of a counter-clockwise closed loop (K, 2)."""
    t = np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)
    n = np.stack([t[:, 1], -t[:, 0]], axis=1)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def pad(ah, b, wi, xlaw, top, warp, rc=(0.0, 0.0), out=(0.040, 0.020, 0.007), rv=0.036, q_skirt=-0.062, n_roll=4):
    """Upholstered pad. Face lattice in reference coords (a across, b along), xlaw(a, b) the true
    abscissa, top(a, b) the height of the face. The edge rolls over to an outline lying out[0] beyond
    the face on the sides, out[1] and out[2] beyond its two ends, the corners staying concentric; the
    roll starts from the slope the face has at its border and drops as a skirt to q_skirt.
    warp sends (x, b, q) to space."""
    aa, bb = lattice(ah, b, rc)
    nb, na = aa.shape[0] - 1, aa.shape[1] - 1
    lat = np.stack([xlaw(aa, bb), bb, top(aa, bb)], axis=-1)
    jj, ii = border(na, nb)
    p = lat[jj, ii]
    # the outline of the skirt, node for node
    a_ref, b_ref = aa[jj, ii], bb[jj, ii]
    line_a = np.abs(np.concatenate([-ah[:0:-1], ah])[ii])              # the lattice lines the nodes sit on
    u, push = ((ii == 0) | (ii == na)).astype(float), np.zeros(len(ii))
    for row, r, sb, reach in ((0, rc[0], -1.0, out[1]), (nb, rc[1], 1.0, out[2])):
        v = (jj == row).astype(float)
        if r > 0.0:                                                    # nodes of the two corner arcs of this end
            cb = b[row] - sb * r
            arc = ((ii == 0) | (ii == na) | (jj == row)) & (line_a > ah[-1] - r - 1e-9) & ((b[jj] - cb) * sb > -1e-9)
            u = np.where(arc, (np.abs(a_ref) - (ah[-1] - r)) / r, u)
            v = np.where(arc, (b_ref - cb) * sb / r, v)
        push += sb * reach * v
    rim_a, rim_b = a_ref + np.sign(a_ref) * out[0] * u, b_ref + push
    rim = np.stack([xlaw(rim_a, rim_b), rim_b], axis=-1)
    inner = lat[jj + (jj == 0) - (jj == nb), ii + (ii == 0) - (ii == na)]
    slope = (inner[:, 2] - p[:, 2]) / np.maximum(np.linalg.norm(inner[:, :2] - p[:, :2], axis=1), 1e-9)
    alpha = np.minimum(np.arctan(np.maximum(slope, 0.0)), math.radians(84.0))
    rings = [p]
    for k in range(1, n_roll + 1):
        tau = alpha + (0.5 * math.pi - alpha) * k / n_roll
        share = (np.sin(tau) - np.sin(alpha)) / (1.0 - np.sin(alpha))
        rings.append(np.column_stack([p[:, :2] + (rim - p[:, :2]) * share[:, None], p[:, 2] - rv * (np.cos(alpha) - np.cos(tau))]))
    skirt = rings[-1].copy()
    skirt[:, :2] -= loop_normals(rim) * 0.003
    skirt[:, 2] = np.minimum(q_skirt, skirt[:, 2] - 0.012)
    rings.append(skirt)
    piece = loft(warp(np.array(rings)), "cuir", caps=((na, nb, 0, 0.0, warp(lat[1:-1, 1:-1])), None), hard=False)
    a_mid = 0.5 * (aa[:-1, :-1] + aa[1:, 1:])
    piece.m[piece.tag["cap0"]] = np.where(np.abs(a_mid) < wi, "cuir_clair", "cuir").reshape(-1)
    return piece


def slab(ah, b, xlaw, warp, q0, q1, rc=(0.0, 0.0), r=0.030, bev=0.004, camber=0.006, hide=0.016, mat="graphite"):
    """Shell framing a pad: its outline is the lattice border. The rim shows at q0, where the pad
    hides the open front; the shown face lies at q1 (a number or a function of b) behind a rounded edge."""
    aa, bb = lattice(ah, b, rc)
    nb, na = aa.shape[0] - 1, aa.shape[1] - 1
    jj, ii = border(na, nb)
    p = np.stack([xlaw(aa, bb), bb], axis=-1)[jj, ii]
    n2 = loop_normals(p)
    far = q1(p[:, 1]) if callable(q1) else np.full(len(p), float(q1))
    sg = np.sign(far - q0)
    r = np.minimum(r, 0.45 * np.abs(far - q0))
    ring = lambda inset, q: np.column_stack([p - n2 * np.reshape(inset, (-1, 1)), np.broadcast_to(q, (len(p),))])
    rings = [ring(hide, q0), ring(bev, q0), ring(0.0, q0 + sg * bev), ring(0.0, far - sg * r)]
    rings += [ring(r * (1.0 - math.cos(a)), far - sg * r * (1.0 - math.sin(a))) for a in np.radians([30.0, 60.0, 90.0])]
    rings = warp(np.array(rings))
    piece = loft(rings, mat, caps=(None, (na, nb, 0, camber)))
    return piece.facing(rings[-1].mean(axis=0) - rings[0].mean(axis=0), face=piece.tag["cap1"].start + (na * nb) // 2)


# ---- seats ----------------------------------------------------------------------------------
ROWS = (-3.15, -2.38, -1.61, -0.90)                     # passenger rows, two seats each at x = +-0.66
PASSENGER = dict(hc=0.42, W=0.245, wi=0.130, hb=0.036, hbb=0.044, Hb=0.80, base="pedestal")
PILOT = dict(hc=0.31, W=0.255, wi=0.134, hb=0.046, hbb=0.060, Hb=0.84, base="sled")


def round_end(rho, shares=(0.03, 0.14, 0.34, 0.62, 1.0)):
    """Stations of a half-round end of radius rho: distances from the tip and the half widths there."""
    d = rho * np.asarray(shares)
    return d, np.sqrt(np.maximum(rho ** 2 - (rho - d) ** 2, 0.0))


def bar(path, st, width, x0, x1, bev=0.004, crown=0.004, mat="graphite"):
    """Flat bar along a side-view path (y, z): its section spans width across the path and x0..x1
    (numbers or one per station), with bevelled edges and a crowned outer face."""
    pos, tan = path.at(st)
    nrm = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
    h = 0.5 * np.asarray(width, dtype=float)[:, None]
    b = np.minimum(bev, 0.3 * h)
    x0, x1 = (np.broadcast_to(np.asarray(v, dtype=float), (len(st),))[:, None] for v in (x0, x1))
    o = np.concatenate([-h + b, 0 * h, h - b, h, h, h - b, 0 * h, -h + b, -h, -h], axis=1)
    x = np.concatenate([x0, x0, x0, x0 + b, x1 - b, x1, x1 + crown * np.minimum(h / 0.02, 1.0), x1, x1 - b, x0 + b], axis=1)
    rings = np.stack([x, pos[:, :1] + o * nrm[:, :1], pos[:, 1:] + o * nrm[:, 1:]], axis=-1)
    return loft(rings, mat, caps=((2, 3, 0), (2, 3, 0)), hard=False).outward()


def tube(path, sections, cap, mat="graphite", right=(1.0, 0.0, 0.0), hard=True):
    """Closed solid of 2D sections along a 3D path."""
    return loft(sweep(path, sections, right), mat, caps=(cap, cap), hard=hard).outward()


def column(z, w, d, y, r=0.3, n=4, mat="dark"):
    """Upright solid of rounded rectangles w x d centred at (0, y) at the heights z."""
    rings = []
    for zk, wk, dk, yk in zip(z, w, d, y):
        sec, cap = rrect(wk, dk, r * min(wk, dk), n)
        rings.append(np.column_stack([sec[:, 0], yk + sec[:, 1], np.full(len(sec), zk)]))
    return loft(np.array(rings), mat, caps=(cap, cap), hard=False).outward()


def disc(profile, k_n=24, mat="graphite", base=True, hard=True):
    """Solid of revolution about +X: profile rows (x, radius[, material]). base=False leaves the
    first ring open, for an end buried in another part."""
    rows = np.array([(p[0], p[1]) for p in profile], dtype=float)
    keys = [p[2] if len(p) > 2 else mat for p in profile[1:]]
    ang = np.arange(k_n) * 2.0 * math.pi / k_n
    rings = np.stack([np.broadcast_to(rows[:, :1], (len(rows), k_n)), rows[:, 1:] * np.cos(ang),
                      rows[:, 1:] * np.sin(ang)], axis=-1)
    cap = (k_n // 4, k_n // 4, 0)
    piece = loft(rings, keys, caps=(cap if base else None, cap), hard=hard)
    return piece.outward() if base else piece.facing((1.0, 0.0, 0.0), face=piece.tag["cap1"].start)


def cord(path, radius, mat, right=(1.0, 0.0, 0.0), n=8):
    """Round cord along a 3D path: piping, handles, rods. right: a direction off the tangent."""
    ang = np.arange(n) * 2.0 * math.pi / n
    return tube(path, radius * np.stack([np.cos(ang), np.sin(ang)], axis=1), (n // 4, n // 4, 0), mat, right, hard=False)


def link(p0, p1, r, x0, x1, mat="graphite"):
    """Flat link between two pivots p0, p1 given in side view (y, z): half-round ends of radius r, across x0..x1."""
    path = Path2([p0, p1])
    d_end, w_end = round_end(r)
    st = np.concatenate([d_end - r, np.linspace(0.0, path.length, 4)[1:-1], path.length + r - d_end[::-1]])
    width = np.concatenate([2.0 * w_end, np.full(2, 2.0 * r), 2.0 * w_end[::-1]])
    return bar(path, st, width, x0, x1, bev=0.003, crown=0.002, mat=mat)


def face_frame(f, a, b, lift=0.0):
    """Points lift off a face f(a, b, q) -> space at its coords (a, b), and the unit normals there (towards +q)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    p = f(a, b, 0.0)
    n = np.cross(f(a + 1e-4, b, 0.0) - f(a - 1e-4, b, 0.0), f(a, b + 1e-4, 0.0) - f(a, b - 1e-4, 0.0))
    n *= np.sign((n * (f(a, b, 0.01) - p)).sum(axis=-1, keepdims=True))
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return p + n * np.reshape(lift, np.shape(lift) + (1,)), n


def strap(p, n, width, mat="sangle", thick=0.003):
    """Flat strap along points p lying on a surface of unit normals n; width: one, or one per point."""
    right = np.cross(np.gradient(p, axis=0), n)
    sec = np.array([rrect(w, thick, 0.4 * thick, 1)[0] for w in np.broadcast_to(width, (len(p),))])
    return tube(p, sec, (1, 3, 1), mat, right / np.linalg.norm(right, axis=1, keepdims=True))


def on_face(piece, f, a, b, proud=0.0, along=(1.0, 0.0)):
    """Set a plate (its face looking along its +Z) on a face f(a, b, q) at (a, b), its X along the
    direction along given in the face's coordinates (a, b)."""
    p, n = face_frame(f, [a], [b], proud)
    da, db = 1e-3 * np.asarray(along, dtype=float) / np.linalg.norm(along)
    ex = f(np.array([a + da]), np.array([b + db]), 0.0)[0] - f(np.array([a - da]), np.array([b - db]), 0.0)[0]
    ex -= n[0] * (ex @ n[0])
    ex /= np.linalg.norm(ex)
    return piece.place(p[0], ex, np.cross(n[0], ex), n[0])


def frame_ring(w, h, r, width, height, mat, n=2):
    """Raised frame round a w x h rectangle with corners of radius r, on z = 0 looking up: inner wall,
    rounded top, outer wall. Open below, where it stands."""
    loops = []
    for out, z in ((0.0, -0.001), (0.0, height - 0.0008), (0.25 * width, height), (0.75 * width, height),
                   (width, height - 0.0008), (width, -0.001)):
        sec = rrect(w + 2.0 * out, h + 2.0 * out, r + out, n)[0]
        loops.append(np.column_stack([sec, np.full(len(sec), z)]))
    piece = loft(np.array(loops), mat, hard=False)
    return piece.facing((0.0, 0.0, 1.0), face=2 * 4 * (n + 1))


def seat(p):
    """One seat in its own frame: origin on the floor under the middle of the cushion, front -Y.
    Returns the piece and the top of the control pod on the port armrest (pilot seat)."""
    hc, big_w, wi = p["hc"], p["W"], p["wi"]
    rr, rv, rc = 0.040, 0.036, 0.028                      # edge roll of the pads, corner radius of their faces
    a0 = big_w - rr                                        # half width of the face lattice
    ah = np.array([0.0, 0.5 * wi, 0.82 * wi, 0.95 * wi, wi, wi + 0.10 * (a0 - wi), wi + 0.34 * (a0 - wi)] + corner(a0, rc, 3))
    sd, pill, ledge, tilt = 0.007, 0.011, 0.013, 0.045
    out = rr - 0.003                                       # the skirts stand this far outside the face lattice
    ra, rb = rc + out + ledge, rc + ledge + 0.004          # corners of the shells: sides and ends differ
    parts = []

    def face(a, hb, ga, gf=1.0, swell=1.0):
        """Height across one row: insert panel swelling between its seams, seam, bolster."""
        u = np.abs(a) / wi
        xi = np.clip((np.abs(a) - wi) / (a0 - wi), 0.0, 1.0)
        insert = -sd + (pill * swell + sd) * puff((1.0 - u) / 0.5) * ga
        bolster = -sd + (hb * (0.35 + 0.65 * gf) + sd) * puff(xi / 0.88)
        return np.where(u <= 1.0 + 1e-9, insert, bolster) - 0.004 * (1.0 - gf)

    # ---- cushion: f runs from the rear end under the backrest to the waterfall front ------
    cq = -0.058                                            # the pan shows its rim this far under the face
    f_rear, f_c, r_w, f_seam = -0.262, 0.165, 0.080, 0.050
    f_front = f_c + r_w * math.sin(math.radians(75.0))
    fall = lambda f: r_w - np.sqrt(np.maximum(r_w ** 2 - np.maximum(f - f_c, 0.0) ** 2, 0.0))
    taper = lambda f: ramp(f, [f_rear, f_rear + 0.06, f_c - 0.12, f_front], [0.97, 1.0, 1.0, 0.90])
    seat_warp = lambda q: np.stack([q[..., 0], -q[..., 1], hc + tilt * q[..., 1] + q[..., 2]], axis=-1)

    def cushion_top(a, f):
        hb = ramp(f, [f_rear, -0.20, -0.10, 0.03, f_c, f_front], [0.010, 0.026, p["hb"], 0.85 * p["hb"], 0.42 * p["hb"], 0.004])
        return face(a, hb, puff(np.abs(f - f_seam) / 0.075)) - fall(f)

    fb = lines([f_rear, -0.20, -0.12, -0.04, 0.115, f_c, f_c + r_w * math.sin(math.radians(20.0))],
               seam(f_seam) + corner(f_front, rc, 3), gap=0.008)
    parts.append(pad(ah, fb, wi, lambda a, f: a * taper(f), cushion_top, seat_warp, rc=(0.0, rc), out=(rr, 0.02, 0.007),
                     rv=rv, q_skirt=cq - 0.018).facing((0.0, 0.0, 1.0), face=-1))

    wp = a0 + out + ledge
    fp0, fp1 = -0.318, f_front + ledge + 0.004
    ahp = np.array([0.0, 0.11] + corner(wp, ra, 3))
    fbp = np.array(sorted(corner(fp0, -0.026)) + [-0.20, -0.05, 0.08] + corner(fp1, rb, 3))
    thick = lambda f: ramp(f, [fp0, -0.12, 0.10, fp1], [0.046, 0.050, 0.042, 0.034])
    parts.append(slab(ahp, fbp, lambda a, f: a * taper(f), seat_warp, cq, lambda f: cq - thick(f),
                      rc=(0.026, (ra, rb)), r=0.030, camber=0.022))
    pan_z = lambda f: hc + tilt * f + cq - thick(f)       # underside of the pan

    # ---- backrest: h is the arc length along the back line, from under the cushion --------
    bq = -0.047                                            # the back shell shows its rim this far behind the face
    line = Path2([(0.2045, hc - 0.05), (0.180, hc + 0.21), (0.250, hc + 0.52), (0.270, hc + 0.605),
                  (0.252, hc + 0.70), (0.256, hc + p["Hb"])], [0, 0.45, 0.40, 0.10, 0.12, 0])
    h_top, h1, h2 = line.length, line.s_where(1, hc + 0.36), line.s_where(1, hc + 0.605)
    r_t = 0.045
    h_c = h_top - r_t
    h_end = h_c + r_t * math.sin(math.radians(75.0))
    ab = a0 - 0.005                                        # the back is a little narrower than the cushion
    half = lambda h: hermite(h, [0.0, 0.12, 0.34, 0.48, 0.56, h2 - 0.03, h2 + 0.06, h_top],
                             [ab - 0.016, ab - 0.004, ab + 0.002, ab + 0.003, ab - 0.010, ab - 0.046, ab - 0.052, ab - 0.066])
    seam_x = lambda h: ramp(h, [0.0, 0.48, h2, h_top], [wi, wi, 0.80 * wi, 0.74 * wi])

    def back_x(a, h):
        s, e = seam_x(h), half(h)
        return np.sign(a) * np.where(np.abs(a) <= wi, np.abs(a) / wi * s, s + (np.abs(a) - wi) / (a0 - wi) * (e - s))

    def back_warp(q):
        pos, tan = line.at(q[..., 1].reshape(-1))
        pos, tan = pos.reshape(q.shape[:-1] + (2,)), tan.reshape(q.shape[:-1] + (2,))
        return np.stack([q[..., 0], pos[..., 0] - tan[..., 1] * q[..., 2], pos[..., 1] + tan[..., 0] * q[..., 2]], axis=-1)

    def back_top(a, h):
        hb = ramp(h, [0.0, 0.07, 0.18, 0.46, h2, h2 + 0.07, h_top], [0.010, 0.022, p["hbb"], p["hbb"], 0.016, 0.022, 0.003])
        ga = puff(np.minimum(np.abs(h - h1), np.abs(h - h2)) / 0.075)
        roll = r_t - np.sqrt(np.maximum(r_t ** 2 - np.maximum(h - h_c, 0.0) ** 2, 0.0))
        return face(a, hb, ga, puff(np.abs(h - h2) / 0.05), swell=np.where(h > h2, 1.5, 1.0)) - roll

    shoulder = [0.47, 0.51, 0.55, 0.59, 0.625]             # lines that carry the turn from shoulder to neck
    hbl = lines([0.0, 0.07, 0.14, 0.22, 0.30] + shoulder + [h2 + 0.055, h_c], seam(h1) + seam(h2) + corner(h_end, rc, 3),
                gap=0.008)
    parts.append(pad(ah, hbl, wi, back_x, back_top, back_warp, rc=(0.0, rc), out=(rr, 0.02, 0.007), rv=rv,
                     q_skirt=bq - 0.015).facing((0.0, -1.0, 0.0), face=-1))

    ws = a0 + out + ledge
    ahs = np.array([0.0, 0.11] + corner(ws, ra, 3))
    hs1 = h_end + ledge + 0.004
    hbs = lines([-0.060, 0.10, 0.22, 0.36] + shoulder + [h2 + 0.02, h2 + 0.075], corner(hs1, rb, 3), gap=0.02)
    deep = lambda h: ramp(h, [0.0, 0.30, h_top], [0.050, 0.046, 0.036])
    shell_x = lambda a, h: a * (half(h) + out + ledge) / ws
    parts.append(slab(ahs, hbs, shell_x, back_warp, bq, lambda h: bq - deep(h), rc=(0.0, (ra, rb)), r=0.030, camber=0.010))

    def on_back(piece, h, proud):
        """Set a plate on the rear face of the back shell, at the height h of the back line."""
        o, up = back_warp(np.array([[0.0, h, bq - float(deep(h)) - proud], [0.0, h + 0.01, bq - float(deep(h)) - proud]]))
        up = (up - o) / np.linalg.norm(up - o)
        return piece.place(o, (-1.0, 0.0, 0.0), up, np.cross((-1.0, 0.0, 0.0), up))

    parts.append(on_back(tile(0.30, 0.17, 0.03, [(0.003, -0.003, "cuir_noir"), (0.008, -0.016, "cuir_noir")], "cuir_noir",
                              mid=(0.07,)), 0.20, 0.016))                                  # pocket
    parts.append(on_back(tile(0.31, 0.016, 0.005, [(0.002, -0.002, "graphite"), (0.002, -0.022, "graphite")], "graphite",
                              mid=(0.08,)), 0.292, 0.022))                                 # its lip
    parts.append(on_back(tile(0.07, 0.022, 0.006, [(0.0015, -0.0015, "champagne"), (0.0015, -0.012, "champagne")], "champagne"),
                         h2 + 0.11, 0.012))                                                # tag behind the headrest
    pilot = p["base"] == "sled"
    if not pilot:                                          # grab handle across the top of the shell
        g = Path2([(-0.10, -0.004), (-0.10, 0.034), (0.10, 0.034), (0.10, -0.004)], [0, 0.014, 0.014, 0])
        xo = g.at(np.unique(np.concatenate([np.linspace(a, b, 5) for a, b in zip(g.marks[:-1], g.marks[1:])])))[0]
        h_g = h_top - 0.06
        o, o2 = back_warp(np.array([[0.0, h_g, bq - float(deep(h_g))], [0.0, h_g + 0.01, bq - float(deep(h_g))]]))
        up = (o2 - o) / np.linalg.norm(o2 - o)
        out = np.cross((-1.0, 0.0, 0.0), up)
        parts.append(cord(o + xo[:, :1] * (-1.0, 0.0, 0.0) + xo[:, 1:] * out, 0.0075, "champagne", right=up))

    # ---- piping: a cord laid in each seam ---------------------------------------------------
    cush = lambda a, f, q: seat_warp(np.stack([a * taper(f), f, cushion_top(a, f) + q], axis=-1))
    back = lambda a, h, q: back_warp(np.stack([back_x(a, h), h, back_top(a, h) + q], axis=-1))
    rp = 0.0042
    sink = lambda n: 0.0022 - 0.005 * (np.arange(n) == n - 1)                   # the end dives into the pad
    f_run, h_run = np.linspace(f_rear + 0.05, f_front - 0.003, 22), np.linspace(0.07, h_end - 0.003, 30)
    parts.append(both(join([cord(cush(np.full(22, wi), f_run, sink(22)), rp, "passepoil"),
                            cord(back(np.full(30, wi), h_run, sink(30)), rp, "passepoil")])))
    parts.append(cord(cush(np.linspace(-wi, wi, 13), np.full(13, f_seam), 0.0022), rp, "passepoil", (0.0, 1.0, 0.0)))
    parts.append(cord(back(np.linspace(-wi, wi, 13), np.full(13, h1), 0.0022), rp, "passepoil", (0.0, 0.0, 1.0)))
    a_h2 = np.linspace(-a0 + 0.012, a0 - 0.012, 21)
    parts.append(cord(back(a_h2, np.full(21, h2), 0.0022 - 0.005 * (np.abs(a_h2) > a0 - 0.02)), rp, "passepoil",
                      (0.0, 0.0, 1.0)))

    # ---- belts laid on the pads, buckled on the lap: four points, five on the pilot seat -----
    def lay(face, top, a0_, b0_, a1_, b1_, n, tuck=0.0, rise=lambda a, b: 0.0):
        """n points of a strap laid on a face from (a0_, b0_) to (a1_, b1_), and its normals. It bridges
        the seams and their piping, along its run and across its width: it lies on the face's upper
        envelope. tuck sinks its first point; rise(a, b) lifts it more, over another strap."""
        a, b = np.linspace(a0_, a1_, 160), np.linspace(b0_, b1_, 160)
        side = (0.5 * wide_s + 0.003) * np.array([b1_ - b0_, a0_ - a1_]) / math.hypot(a1_ - a0_, b1_ - b0_)
        q = top(a, b)
        sag = 0.5 * (top(a + side[0], b + side[1]) + top(a - side[0], b - side[1])) - q   # hollow across the strap
        env = q + np.maximum(sag, 0.0)
        env = np.max([np.pad(env, 8, mode="edge")[k:k + len(q)] for k in range(17)], axis=0)
        env = np.convolve(np.pad(env, 4, mode="edge"), np.ones(9) / 9.0, mode="valid")
        k = np.linspace(0, len(a) - 1, n).round().astype(int)
        lift = np.maximum(env, q) - q + 0.0035 + rise(a, b)
        pts, nrm = face_frame(face, a[k], b[k], lift[k] - tuck * (np.arange(n) == 0))
        nrm = np.pad(nrm, ((1, 1), (0, 0)), mode="edge")
        nrm = 0.25 * nrm[:-2] + 0.5 * nrm[1:-1] + 0.25 * nrm[2:]
        return pts, nrm / np.linalg.norm(nrm, axis=1, keepdims=True)

    f_b, wide_s = 0.035, (0.050 if pilot else 0.046)
    sh0, sh1 = np.array([0.062, -0.12]), np.array([0.020, f_b - 0.012])  # shoulder strap on the cushion: (a, f) ends
    h_slot = h2 - 0.065
    pb, nb_ = lay(back, back_top, 0.080, h_slot, 0.066, 0.085, 14, 0.004)            # shoulder strap, from its slot
    pc, nc = lay(cush, cushion_top, *sh0, *sh1, 10)                                   # ... to under the buckle

    def over(a, f):
        """Rise of the lap strap where it crosses the shoulder strap: it lies over it."""
        w = np.clip(((a - sh0[0]) * (sh1 - sh0)[0] + (f - sh0[1]) * (sh1 - sh0)[1]) / ((sh1 - sh0) ** 2).sum(), 0.0, 1.0)
        d = np.hypot(a - sh0[0] - w * (sh1 - sh0)[0], f - sh0[1] - w * (sh1 - sh0)[1])
        return 0.0048 * hg.smoothstep(wide_s + 0.012, wide_s - 0.004, d)

    lap0, lap1 = np.array([a0 - 0.034, -0.178]), np.array([0.026, f_b])               # lap strap, from its guide
    pl, nl = lay(cush, cushion_top, *lap0, *lap1, 18, 0.0, over)
    bend = 0.5 * (pb[-1] + pc[0]) + 0.004 * (nb_[-1] + nc[0])                       # over the crease
    bn = (nb_[-1] + nc[0]) / np.linalg.norm(nb_[-1] + nc[0])
    tongue = np.concatenate([np.full(len(pb) + 1 + len(pc) - 3, wide_s), wide_s - (wide_s - 0.032) * np.array([0.4, 0.8, 1.0])])
    belt = [strap(pl, nl, wide_s), strap(np.vstack([pb, bend, pc]), np.vstack([nb_, bn, nc]), tongue),
            on_face(tile(0.064, 0.018, 0.007, [(0.002, -0.002, "dark"), (0.002, -0.010, "dark")], "dark"),
                    back, 0.080, h_slot, 0.003),                                   # slot bezel
            on_face(tile(wide_s + 0.016, 0.020, 0.007, rounded(0.003, "dark") + [(0.003, -0.012, "dark")], "dark"),
                    cush, *lap0, 0.004, along=((lap1 - lap0)[1], -(lap1 - lap0)[0]))]   # guide of the lap strap
    parts.append(both(join(belt)))
    if pilot:                                              # crotch strap and its slot; rotary buckle
        f_c0 = f_front - 0.055
        pz, nz = lay(cush, cushion_top, 0.0, f_c0, 0.0, f_b + 0.026, 9, 0.004)
        parts.append(strap(pz, nz, np.concatenate([np.full(6, wide_s), [0.044, 0.038, 0.034]])))
        parts.append(on_face(tile(0.064, 0.018, 0.007, [(0.002, -0.002, "dark"), (0.002, -0.010, "dark")], "dark"),
                             cush, 0.0, f_c0, 0.003))
        buckle = disc([(-0.008, 0.042, "dark"), (0.005, 0.043, "dark"), (0.007, 0.041, "champagne"),
                       (0.012, 0.038, "champagne"), (0.014, 0.031, "champagne"), (0.014, 0.015, "dark"),
                       (0.017, 0.013, "champagne"), (0.018, 0.005, "champagne")], 24)
        parts.append(on_face(buckle.place((0, 0, 0), (0, 0, 1), (1, 0, 0), (0, 1, 0)), cush, 0.0, f_b, 0.0))
    else:                                                  # lift-lever buckle, the lever proud on its plate
        parts.append(on_face(tile(0.100, 0.062, 0.014, rounded(0.004, "dark") + [(0.004, -0.018, "dark")], "dark"),
                             cush, 0.0, f_b, 0.010))
        parts.append(on_face(tile(0.078, 0.040, 0.010, rounded(0.003, "champagne") + [(0.003, -0.006, "champagne")],
                                  "champagne"), cush, 0.0, f_b, 0.0135))

    # ---- recliner: hub, armrest bracket and cover disc on each side, concentric -----------
    hy, hz, r_hub = 0.276, hc - 0.040, 0.046               # recliner axis, where the back shell meets the pan
    x_in = ws + 0.012                                      # inner face of the armrest bracket
    arm_z = hc + 0.178
    spine = Path2([(hy - 0.006, hz - r_hub), (hy + 0.012, arm_z), (-0.218, arm_z - 0.010)], [0, 0.060, 0])
    e0, e1, length = spine.marks[1], spine.marks[2], spine.length
    d_hub, w_hub = round_end(r_hub)
    d_tip, w_tip = round_end(0.017)
    st = np.concatenate([d_hub, [0.5 * (r_hub + e0)], np.linspace(e0, e1, 9), e1 + (length - 0.017 - e1) * np.array([0.3, 0.65]),
                         length - d_tip[::-1]])
    grow = hermite(st, [r_hub, e0, e1, 0.5 * (e1 + length), length - 0.017], [2 * r_hub - 0.012, 0.060, 0.050, 0.042, 0.034])
    width = grow.copy()                                    # half-round at the hub and at the front tip
    width[:5], width[-5:] = w_hub * grow[4] / r_hub, 2.0 * w_tip[::-1]
    thin = hermite(st, [0.0, e1, length], [0.032, 0.030, 0.025])
    side = [bar(spine, st, width, x_in, x_in + thin),
            disc([(ws - 0.008, 0.034), (x_in + 0.002, 0.034)], 12),
            disc([(x_in + 0.026, 0.050), (x_in + 0.040, 0.050), (x_in + 0.044, 0.046), (x_in + 0.044, 0.030),
                  (x_in + 0.041, 0.027), (x_in + 0.041, 0.016, "champagne"), (x_in + 0.046, 0.013, "champagne")], base=False)]
    for d in side[1:]:
        d.move(0.0, hy, hz)
    # armrest pad: a low cushion on the beam, rounded at both ends
    sec = np.array([(-0.74, 0.0), (0.0, 0.0), (0.74, 0.0), (1.0, 0.25), (1.0, 0.5), (0.87, 0.78), (0.52, 0.95), (0.0, 1.0),
                    (-0.52, 0.95), (-0.87, 0.78), (-1.0, 0.5), (-1.0, 0.25)]) * (0.027, 0.026)
    y0, y1 = 0.200, (-0.230 if p["base"] == "pedestal" else -0.105)
    d_end, w_end = round_end(1.0)
    yy = np.concatenate([y0 - 0.027 * d_end, [y0 - 0.15, y1 + 0.15], y1 + 0.027 * d_end[::-1]])
    wide = np.concatenate([w_end, [1.0, 1.0], w_end[::-1]])
    sb = np.linspace(e1, length, 40)
    beam = spine.at(sb)[0][::-1]
    top = np.interp(yy, beam[:, 0], beam[:, 1]) + 0.5 * np.interp(yy, beam[:, 0], hermite(sb, st, width)[::-1]) - 0.004
    rings = np.stack([x_in + 0.015 + sec[None, :, 0] * wide[:, None], np.broadcast_to(yy[:, None], (len(yy), 12)),
                      top[:, None] + sec[None, :, 1] * (0.30 + 0.70 * wide[:, None])], axis=-1)
    side.append(loft(rings, "cuir_noir", caps=((2, 4, 0), (2, 4, 0)), hard=False).outward())
    pod = np.array([x_in + 0.015, -0.19, arm_z + 0.050])   # top of the control pod, pilot seat only
    if p["base"] == "sled":
        box = tile(0.050, 0.165, 0.020, rounded(0.012, "graphite") + [(0.019, -0.040, "graphite"), (0.015, -0.062, "graphite")],
                   "graphite", back=0.0, n=3)
        side.append(box.place(pod, (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    parts.append(both(join(side)))
    if p["base"] == "sled":                                # slot of the throttle on the port pod
        slot = tile(0.018, 0.105, 0.008, [(0.0015, -0.0015, "caoutchouc"), (0.0015, -0.005, "caoutchouc")], "caoutchouc")
        parts.append(slot.place(pod + (0.0, 0.0, 0.0025), (1, 0, 0), (0, 1, 0), (0, 0, 1)))

    # ---- base ---------------------------------------------------------------------------
    if p["base"] == "pedestal":
        top = float(pan_z(0.0)) + 0.014
        zk = np.array([0.012, 0.045, 0.13, 0.23, top - 0.035, top])
        z = np.concatenate([np.linspace(0.012, 0.045, 3), np.linspace(0.075, top - 0.07, 4), np.linspace(top - 0.035, top, 2)])
        parts.append(column(z, hermite(z, zk, [0.20, 0.15, 0.105, 0.115, 0.17, 0.215]),
                            hermite(z, zk, [0.27, 0.20, 0.13, 0.14, 0.21, 0.26]),
                            hermite(z, zk, [0.02, 0.022, 0.03, 0.028, 0.012, 0.0])))
        parts.append(tile(0.27, 0.36, 0.035, [(0.004, -0.004, "dark"), (0.004, -0.015, "dark")], "dark").move(0.0, 0.02, 0.014))
        # track fittings: a clamp on each rail at both ends of the plate, its locking plunger on top
        clamp = tile(0.036, 0.066, 0.012, rounded(0.006, "dark") + [(0.006, -0.018, "dark")], "dark")
        plunger = upright(disc([(-0.004, 0.0075, "champagne"), (0.006, 0.0075, "champagne"), (0.008, 0.0055, "champagne")], 12))
        parts.append(both(join([q.copy().move(0.12, 0.02 + dy, 0.024) for dy in (-0.205, 0.205) for q in (clamp, plunger)])))
    else:
        # floor rails with bolted stops; on each a carriage, and the seat pan carried by two parallel links
        rail = np.array([-0.345, -0.341, 0.301, 0.305])
        sec = np.array([rrect(w, h, r, 1)[0] for w, h, r in ((0.042, 0.012, 0.002), (0.05, 0.02, 0.004), (0.05, 0.02, 0.004),
                                                             (0.042, 0.012, 0.002))])
        sled = [tube(np.column_stack([np.full(4, 0.17), rail, np.full(4, 0.009)]), sec, (1, 3, 1), "dark", (1, 0, 0))]
        car = np.array([-0.262, -0.256, 0.216, 0.222])
        sec = np.array([rrect(w, h, r, 1)[0] for w, h, r in ((0.062, 0.026, 0.004), (0.072, 0.036, 0.007), (0.072, 0.036, 0.007),
                                                             (0.062, 0.026, 0.004))])
        sled.append(tube(np.column_stack([np.full(4, 0.17), car, np.full(4, 0.030)]), sec, (1, 3, 1), "graphite", (1, 0, 0)))
        bolt = upright(disc([(-0.003, 0.007, "champagne"), (0.004, 0.007, "champagne"), (0.0055, 0.0055, "champagne")], 12))
        sled += [bolt.copy().move(0.17, y, 0.019) for y in (-0.318, 0.282)]
        z_l, z_u = 0.040, float(min(pan_z(-0.19), pan_z(0.13))) - 0.026          # pivots on the carriage, under the pan
        sled.append(link((-0.135, z_u), (0.195, z_u), 0.024, 0.136, 0.204))       # bracket under the pan
        pin = disc([(0.128, 0.0085, "dark"), (0.226, 0.0085, "dark"), (0.226, 0.012, "champagne"), (0.231, 0.012, "champagne"),
                    (0.233, 0.009, "champagne")], 12)
        for y0 in (-0.175, 0.045):
            sled.append(link((y0, z_l), (y0 + 0.085, z_u), 0.022, 0.208, 0.224))
            sled += [pin.copy().move(0.0, y, z) for y, z in ((y0, z_l), (y0 + 0.085, z_u))]
        # gas spring between the carriage and the bracket, inboard
        y_a, y_b = np.array([0.0, -0.215, 0.034]), np.array([0.0, 0.150, z_u - 0.004])
        axis = (y_b - y_a) / np.linalg.norm(y_b - y_a)
        span = float(np.linalg.norm(y_b - y_a))
        spring = disc([(0.0, 0.009, "dark"), (0.010, 0.013, "dark"), (0.15, 0.013, "dark"), (0.154, 0.0055, "champagne"),
                       (span - 0.012, 0.0055, "champagne"), (span - 0.010, 0.009, "dark"), (span, 0.009, "dark")], 12)
        sled.append(spring.place((0.118, y_a[1], y_a[2]), axis, np.cross((1.0, 0.0, 0.0), axis), (1.0, 0.0, 0.0)))
        parts.append(both(join(sled)))
        # fore-aft release bar across the front of the carriages
        g = Path2([(0.17, -0.235), (0.17, -0.325), (-0.17, -0.325), (-0.17, -0.235)], [0, 0.035, 0.035, 0])
        xy = g.at(np.unique(np.concatenate([np.linspace(a, b, 5) for a, b in zip(g.marks[:-1], g.marks[1:])])))[0]
        parts.append(cord(np.column_stack([xy, np.full(len(xy), 0.034)]), 0.0065, "champagne", right=(0.0, 0.0, 1.0)))
    return join(parts), pod


# ---- cabin ----------------------------------------------------------------------------------
LINER, CEIL = 0.065, 0.062         # depth of the side liners and of the ceiling under the outer skin
Y_BULKHEAD = -0.30                 # front face of the rear bulkhead
PAN = FLOOR - 0.062                # the liners turn in under the floor plate at this height
Z_UNDER = FLOOR - 0.048            # underside of the floor plate, a closed slab
CLEAR = 0.27                       # least distance from the deck's edge to the glass forward of the seat
Y_PILOT = -4.25                    # pilot seat: under the middle of its cushion
Y_SEAT_FRONT, Y_FLARE = -4.55, -3.75   # forward of the first the deck keeps CLEAR; aft of the second, cabin width
Y_BOW, L_BOW, W_BOW = -5.24, 0.23, 0.42   # the deck's sides level out at Y_BOW, W_BOW from the centreline,
                                   # then round off over L_BOW: the tip lies 0.335 m ahead of the console's foot
F0, T_FRAME, D_FRAME = -0.040, 0.036, 0.092   # prow frame: front face from the glass edge (aft +), thickness, web depth
Z_WEB = FLOOR - 0.024              # under the floor the frame's rounded edge runs inside the slab at this height


def weld(piece, tol=1e-6):
    """Merge the vertices of a piece that share a position."""
    key = np.round(piece.v / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    piece.v, piece.hard, piece.f = piece.v[first], piece.hard[first], inv.reshape(-1)[piece.f]
    return piece


def plate(aa, bb, steps, face="graphite", zf=None, back=None, hard=True):
    """Plate from a face lattice (see lattice) on z = 0, looking along +Z. steps: the rings under the
    face edge, each (distance outside the edge, z, material of the band above it); z may vary round
    the edge. back: camber of a closing face, None leaves the last ring open. zf(aa, bb) lifts face nodes."""
    nb, na = aa.shape[0] - 1, aa.shape[1] - 1
    jj, ii = border(na, nb)
    lat = np.stack([aa, bb, np.zeros_like(aa) if zf is None else zf(aa, bb)], axis=-1)
    edge = lat[jj, ii]
    n2 = loop_normals(edge[:, :2])
    rings = [edge] + [np.column_stack([edge[:, :2] + n2 * out, np.broadcast_to(z, (len(edge),))]) for out, z, _ in steps]
    piece = loft(np.array(rings), [k for _, _, k in steps], capmat=face, hard=hard,
                 caps=((na, nb, 0, 0.0, lat[1:-1, 1:-1]), None if back is None else (na, nb, 0, back)))
    if back is None:
        return piece.facing((0.0, 0.0, 1.0), face=piece.tag["cap0"].start)
    piece.m[piece.tag["cap1"]] = steps[-1][2]
    return piece.outward()


def rounded(r, mat, n=3):
    """Plate steps that turn the face edge over a quarter round of radius r."""
    return [(r * math.sin(a), -r * (1.0 - math.cos(a)), mat) for a in np.radians(90.0 * np.arange(1, n + 1) / n)]


def panel(a, b, depth, bev=0.003, rc=(0.0, 0.0), mat="graphite", zf=None):
    """Plain plate: bevelled edge, sides down to -depth, open at the back. a: all the lines, or the half from 0."""
    return plate(*lattice(np.asarray(a, dtype=float), b, rc), [(bev, -bev, mat), (bev, -depth, mat)], face=mat, zf=zf)


def corner(edge, r, n=2):
    """Lattice lines that carry a corner of radius r ending at edge: 2 n segments on the arc."""
    return [edge - r * (1.0 - math.tan(math.radians(45.0 * k / n))) for k in range(n)] + [edge]


def tile(w, h, r, steps, face, mid=(), back=None, zf=None, n=2):
    """Plate w x h with corners of radius r (2 n segments each), centred on its frame.
    mid: more half lines across."""
    def half_lines(half, extra):
        out = [0.0]
        for v in sorted({*extra, *corner(half, r, n)[:-1]} if r > 0.0 else set(extra)):
            if v - out[-1] > 0.004 and half - v > 0.004:
                out.append(v)
        return out + [half]

    a = np.array(half_lines(0.5 * w, mid))
    hb = half_lines(0.5 * h, ())[1:]
    b = np.array(sorted({*hb, *[-v for v in hb]}))
    return plate(*lattice(a, b, (r, r)), steps, face, zf, back)


def planar(piece, key, ex, ey):
    """UVs of the faces tagged key: the vertex positions measured along ex and ey."""
    p = piece.v[piece.f[piece.tag[key]]]
    piece.uv[piece.tag[key]] = np.stack([p @ np.asarray(ex, dtype=float), p @ np.asarray(ey, dtype=float)], axis=-1)
    return piece


def wall_x(skin, y, z, d=LINER):
    """Half width of the liner surface (d under the skin) at the heights z of the sections y."""
    y, z = np.broadcast_arrays(np.asarray(y, dtype=float), np.asarray(z, dtype=float))
    t = np.linspace(0.05, 0.97, 600)
    q = skin.inner(skin.maps.s_of_y(y.reshape(-1))[:, None], t[None, :], d)
    return np.array([np.interp(zk, row[::-1, 2], row[::-1, 0]) for zk, row in zip(z.reshape(-1), q)]).reshape(y.shape)


BEAD = ((0.004, 0.054), (-0.016, 0.054), (-0.025, 0.0570), (-0.023, 0.0615), (-0.013, 0.0650))
# rolled edge of a liner on the glazing: (distance outside the glass edge, depth under the skin), hull side first


def side_liner(skin, front, n_wall=12):
    """Side liners from the prow frame to the bulkhead: rolled edge standing just inside the glazing,
    wall along the hull, cove and pan under the floor plate. The first rows start on the frame's aft
    face, front = (t, y) along it, and lean with it; they straighten into sections across the ship."""
    m = skin.maps
    planes = np.concatenate([np.linspace(-3.60, -0.95, 25), np.linspace(-0.95, -0.72, 6)[1:],
                             np.linspace(-0.72, -0.55, 12)[1:], np.linspace(-0.55, Y_BULKHEAD + 0.03, 4)[1:]])
    lean = np.linspace(0.0, 1.0, 5)[:-1]                   # leaning rows: share of the way to the first section
    s_plane = m.s_of_y(planes)
    s_front = lambda t: m.s_of_y(np.interp(t, *front))
    rows, tops = [], []
    for k in range(len(lean) + len(planes)):
        if k < len(lean):
            s_row = lambda t, w=lean[k]: (1.0 - w) * s_front(t) + w * s_plane[0]
        else:
            s_row = lambda t, s=s_plane[k - len(lean)]: np.full(np.shape(t), s)
        s_top = s_row(np.array([front[0][0]]))
        t0 = float(skin.edge(s_top)[0])
        bead = np.vstack([skin.inner(s_top, skin.edge(s_top, mg), np.array([d])) for mg, d in BEAD])
        tt = np.linspace(t0, 0.985, 700)
        q = skin.inner(s_row(tt), tt, LINER)
        z_pan = min(PAN, q[0, 2] - 0.07)
        j = int(np.argmax(q[:, 2] < z_pan))
        w = (q[j - 1, 2] - z_pan) / (q[j - 1, 2] - q[j, 2])
        knee = q[j - 1] + w * (q[j] - q[j - 1])
        wall = np.vstack([q[:j], knee])
        arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(wall, axis=0), axis=1))])
        u_in = wall[-1, [0, 2]] - wall[-4, [0, 2]]
        u_in /= np.linalg.norm(u_in)
        reach = 0.03 * math.tan(0.5 * math.acos(float(np.clip(-u_in[0], -1.0, 1.0))))   # tangent length of the cove
        length = arc[-1] - reach
        d1, d2, kick = min(0.018, 0.2 * length), min(0.027, 0.32 * length), max(length - 0.10, 0.6 * length)
        pos = np.concatenate([[0.0, d1], np.linspace(d2, kick, n_wall - 2), [length]])
        nodes = np.stack([np.interp(pos, arc, wall[:, i]) for i in range(3)], axis=1)
        a, b = nodes[-1], knee + (-reach, 0.0, 0.0)
        cove = [(1 - u) ** 2 * a + 2 * u * (1 - u) * knee + u ** 2 * b for u in (1 / 3, 2 / 3, 1.0)]
        pan = [b + (-0.13, 0.0, 0.0), b + (-0.26, 0.0, 0.0)]
        rows.append(np.vstack([bead, nodes, cove, pan]))
        tops.append(bead[0, 1])
    rows, tops = np.array(rows), np.array(tops)
    n_row, n_b = rows.shape[1], len(BEAD)
    keys = np.empty((len(rows) - 1, n_row - 1), dtype=object)
    keys[:] = "habillage"
    keys[:, :n_b] = "habillage_sombre"                     # rolled edge
    keys[0.5 * (tops[:-1] + tops[1:]) > -3.72, n_b + 1] = "amber"   # light line under the sill, aft of the arch
    keys[:, n_b + n_wall - 1:] = "habillage_sombre"        # kick band, cove and pan
    half = loft(rows, closed=False, hard=False)
    half.m = keys.reshape(-1)
    half.facing((-1.0, 0.0, 0.3), face=(len(rows) // 2) * (n_row - 1) + n_b + 4)
    return join([half, half.mirror()])


def deck_width(skin):
    """Half width of the floor plate along the ship, y -> x: 40 mm inside the liners aft of Y_FLARE;
    at Y_SEAT_FRONT the most that keeps the plate's outer edge CLEAR from the glass, with a smooth
    flare between; forward of it a cubic that levels out at W_BOW by Y_BOW, where the bow rounds off."""
    yk = np.linspace(-6.4, 0.0, 321)
    cabin = wall_x(skin, yk, FLOOR) - 0.040                # face edge: 18 mm of shadow gap, 22 mm of lit edge
    lo, hi = np.zeros_like(yk), cabin + 0.022
    for _ in range(20):                                    # the plate's outer edge: 22 mm beyond the face, 20 mm down
        mid = 0.5 * (lo + hi)
        ok = skin.depth(np.column_stack([mid, yk, np.full_like(yk, FLOOR - 0.020)])) >= CLEAR
        lo, hi = np.where(ok, mid, lo), np.where(ok, hi, mid)
    deck = np.convolve(np.pad(lo, 6, mode="edge"), np.ones(13) / 13.0, mode="valid") - 0.024
    # forward of the seat the sides leave that law along a cubic, level out at W_BOW and round off
    p0, m0 = float(np.interp(Y_SEAT_FRONT, yk, deck)), float(np.interp(Y_SEAT_FRONT, yk, np.gradient(deck, yk)))
    t = np.clip((yk - Y_SEAT_FRONT) / (Y_BOW - Y_SEAT_FRONT), 0.0, 1.0)
    bow = ((2 * t ** 3 - 3 * t ** 2 + 1) * p0 + (t ** 3 - 2 * t ** 2 + t) * (Y_BOW - Y_SEAT_FRONT) * m0
           + (3 * t ** 2 - 2 * t ** 3) * W_BOW)
    deck = np.where(yk < Y_SEAT_FRONT, bow, deck)
    w = hg.smootherstep(Y_SEAT_FRONT, Y_FLARE, yk)
    return lambda y: np.interp(y, yk, (1.0 - w) * deck + w * cabin)


def floor_plate(hw):
    """Floor plate of the cabin and pilot deck, one thin dark slab: lit strip and rounded edge all
    round, closed underside. Its half width is hw(y); the bow rounds off forward of Y_BOW."""
    b = np.concatenate([np.linspace(-Y_BULKHEAD - 0.03, 2.9, 8), np.linspace(2.9, -Y_FLARE, 9)[1:],
                        np.linspace(-Y_FLARE, -Y_SEAT_FRONT, 33)[1:],
                        np.linspace(-Y_SEAT_FRONT, -Y_BOW, 9)[1:], -Y_BOW + L_BOW * (1.0 - np.array([0.8, 0.59, 0.33, 0.0]))])
    aa, bb = lattice(np.array([0.0, 0.25, 0.5, 0.75, 1.0]), b, (0.0, (1.0, L_BOW)))
    aa = aa * hw(-bb)
    steps = [(0.010, 0.0, "amber"), (0.016, -0.004, "amber"), (0.020, -0.010, "dark"), (0.022, -0.018, "dark"),
             (0.022, -0.028, "dark"), (0.019, -0.036, "dark"), (0.012, -0.042, "dark"), (0.002, -0.046, "dark"),
             (-0.020, Z_UNDER - FLOOR, "dark")]
    deck = plate(aa, bb, steps, face="plancher", back=0.0).place((0.0, 0.0, FLOOR), (1, 0, 0), (0, -1, 0), (0, 0, 1))
    planar(deck, "cap0", (1, 0, 0), (0, 1, 0))
    parts = [deck]
    # seat rails, two per row of seats; rubber covers in them between the seats
    rail = np.array([rrect(w, h, r, 1)[0] for w, h, r in ((0.024, 0.006, 0.001), (0.032, 0.012, 0.003),
                                                          (0.032, 0.012, 0.003), (0.024, 0.006, 0.001))])
    cover = np.array([rrect(w, h, r, 1)[0] for w, h, r in ((0.020, 0.004, 0.0015), (0.027, 0.008, 0.003),
                                                           (0.027, 0.008, 0.003), (0.020, 0.004, 0.0015))])
    ends = [-3.555] + [y + v for y in ROWS for v in (-0.225, 0.265)] + [-0.505]
    for x in (0.54, 0.78):
        path = np.column_stack([np.full(4, x), [-3.56, -3.555, -0.505, -0.50], np.full(4, FLOOR)])
        parts.append(both(tube(path, rail, (1, 3, 1), "dark", (1, 0, 0))))
        for y0, y1 in zip(ends[::2], ends[1::2]):
            path = np.column_stack([np.full(4, x), [y0, y0 + 0.004, y1 - 0.004, y1], np.full(4, FLOOR + 0.007)])
            parts.append(both(tube(path, cover, (1, 3, 1), "caoutchouc", (1, 0, 0))))
    lamp = panel(np.array([-0.005, 0.005]), np.array([-1.65, 1.65]), 0.003, bev=0.0015, mat="amber")   # aisle lights
    parts.append(both(lamp.move(0.32, -2.08, FLOOR + 0.0015)))
    return join(parts)


def fittings(skin):
    """What reads through the glazing: a grab handle over each row by the window tops, a trim along
    the sills, a number plate under the sill at each row."""
    g = Path2([(-0.10, -0.004), (-0.10, 0.036), (0.10, 0.036), (0.10, -0.004)], [0, 0.014, 0.014, 0])
    xz = g.at(np.unique(np.concatenate([np.linspace(a, b, 5) for a, b in zip(g.marks[:-1], g.marks[1:])])))[0]
    grip = cord(np.column_stack([xz[:, 0], np.zeros(len(xz)), xz[:, 1]]), 0.0075, "champagne", right=(0.0, 1.0, 0.0))
    foot = tile(0.032, 0.026, 0.010, rounded(0.004, "dark") + [(0.004, -0.010, "dark")], "dark")
    handle = join([grip] + [foot.copy().move(x, 0.0, 0.004) for x in (-0.10, 0.10)])
    plate_ = join([tile(0.074, 0.032, 0.008, rounded(0.003, "dark") + [(0.003, -0.008, "dark")], "dark"),
                   tile(0.046, 0.014, 0.004, [(0.001, -0.001, "champagne"), (0.001, -0.006, "champagne")], "champagne")
                   .move(0.0, 0.0, 0.002)])
    parts = []
    for y in ROWS:
        parts.append(on_liner(skin, handle.copy(), y + 0.10, share=0.84))
        parts.append(on_liner(skin, plate_.copy(), y - 0.34, z=float(hg.z_sill(y - 0.34)) - 0.075, proud=0.002))
    ys = np.linspace(-3.66, -1.02, 44)
    s = skin.maps.s_of_y(ys)
    parts.append(cord(skin.inner(s, skin.edge(s, 0.006), np.full(len(s), LINER + 0.0035)), 0.0038, "champagne"))
    return both(join(parts))


def prow_frame(skin, hw):
    """Ring frame along the prow line, where the glass ends, from sill to sill under the keel. Down
    the sides it is a web standing proud of the liners, which start on its aft face; under the floor
    it deepens into a curtain whose rounded edge runs inside the floor slab, so that nothing behind
    the skin or under the floor shows through the glass. Returns the piece and (t, y) of its aft face."""
    g = skin.grid
    col, rows = g.col["arch"], np.arange(hg.B_SILL, hg.B_MAX + 1)
    p, nrm = g.points[col, rows], g.normals[col, rows]
    fwd = g.points[col - 1, rows] - p
    aft = -(fwd - nrm * (fwd * nrm).sum(axis=1, keepdims=True))
    aft /= np.linalg.norm(aft, axis=1, keepdims=True)
    # inner edge: the web's depth down the sides; under the floor a line in the slab that leans forward,
    # clear of the nose gear well, and stays 35 mm inside the plate's edge
    y_c = p[:, 1] - 0.03 - 0.07 * hg.smoothstep(0.64, 0.44, p[:, 0])
    curtain = np.column_stack([np.minimum(p[:, 0], hw(y_c) - 0.035), y_c, np.full(len(p), Z_WEB)])
    w = hg.smoothstep(FLOOR + 0.015, FLOOR - 0.085, p[:, 2])[:, None]
    inner = (1.0 - w) * (p - nrm * D_FRAME) + w * curtain
    base = p + aft * F0 - nrm * 0.006
    u = inner - base
    length = np.linalg.norm(u, axis=1)
    u /= length[:, None]
    a2 = aft - u * (aft * u).sum(axis=1, keepdims=True)
    a2 /= np.linalg.norm(a2, axis=1, keepdims=True)
    # the foot of each face sinks under the curved skin: 6 mm under it at least
    dive = np.maximum((-u * nrm).sum(axis=1), 0.3)
    sink = [np.maximum(0.007 - skin.depth(base + a2 * da), 0.0) / dive for da in (0.0, T_FRAME)]
    r = 0.5 * T_FRAME
    ang = np.radians([0.0, 40.0, 75.0, 105.0, 140.0, 180.0])           # rounded inner edge, aft side first
    sec = []                                                          # (along a2, along u) per node: 10 points
    for ln, s0, s1 in zip(length, *sink):
        arc = [(r + r * math.cos(t), ln - r + r * math.sin(t)) for t in ang]
        sec.append([(0.0, s0), (T_FRAME, s1), (T_FRAME, 0.5 * (ln - r))] + arc + [(0.0, 0.5 * (ln - r))])
    sec = np.array(sec)
    half = base[:, None, :] + sec[..., :1] * a2[:, None, :] + sec[..., 1:] * u[:, None, :]
    rings = np.concatenate([half, (half[-2::-1] * (-1.0, 1.0, 1.0))])
    # Under the floor the curtain is the hull's own white chin, seen through the bubble as in the concept.
    wk = np.concatenate([w[:, 0], w[-2::-1, 0]])
    keys = np.where(0.5 * (wk[:-1] + wk[1:]) > 0.5, "blanc", "habillage_sombre").tolist()
    piece = loft(rings, keys, caps=((1, 4, 0), (1, 4, 0))).outward()
    return piece, (g.t[col, rows], p[:, 1] + aft[:, 1] * (F0 + T_FRAME + 0.002))


def keel_spine():
    """Keel spine: one slim blade on the centreline under the deck, from the prow curtain forward,
    deepest at its root; its rounded lower edge rises to the deck's underside near the bow, and a
    cove joins it to that underside."""
    y0, y1 = -4.72, Y_BOW - 0.06
    ys = y0 + (y1 - y0) * np.linspace(0.0, 1.0, 24) ** 0.9
    u = (ys - y0) / (y1 - y0)
    z_top = FLOOR - 0.030
    z_bot = hermite(u, [0.0, 0.4, 0.8, 1.0], [-1.520, -1.470, -1.360, Z_UNDER - 0.010])
    wide = hermite(u, [0.0, 0.5, 1.0], [0.046, 0.036, 0.026])
    rings, cove = [], []
    th = np.radians(np.linspace(90.0, 180.0, 5))
    for y, zb, wk in zip(ys, z_bot, wide):
        sec, cap = rrect(wk, z_top - zb, 0.5 * wk, 2)
        rings.append(np.column_stack([sec[:, 0], np.full(len(sec), y), 0.5 * (z_top + zb) + sec[:, 1]]))
        f = min(0.020, 0.45 * (Z_UNDER - zb))
        x, z = 0.5 * wk + f + f * np.cos(th), Z_UNDER - f + f * np.sin(th)
        x[-1], z[0] = x[-1] - 0.001, z[0] + 0.001                  # both edges run into the solids they join
        cove.append(np.column_stack([x, np.full(5, y), z]))
    cove = loft(np.array(cove), "graphite", closed=False, hard=False).facing((1.0, 0.0, -1.0), face=4 * (len(ys) // 2) + 2)
    return join([loft(np.array(rings), "graphite", caps=(cap, cap), hard=False).outward(), both(cove)])


def ceiling(skin):
    """Ceiling liner over the passenger rows, from the arch to the bulkhead: rolled edge hanging just
    inside the window tops, and two rows of short light dashes on each side."""
    m = skin.maps
    ys = np.concatenate([np.linspace(hg.ARCH_Y + 0.012, -0.95, 30), np.linspace(-0.95, -0.72, 5)[1:],
                         np.linspace(-0.72, -0.55, 10)[1:],
                         np.linspace(-0.55, Y_BULKHEAD + 0.03, 4)[1:]])
    s = m.s_of_y(ys)
    t1 = skin.edge(s, 0.0, upper=True)
    frac = np.linspace(0.0, 1.0, 11)
    bead = np.stack([skin.inner(s, skin.edge(s, mg, upper=True), np.full(len(s), d - LINER + CEIL))
                     for mg, d in BEAD[::-1]], axis=1)
    rows = np.concatenate([skin.inner(np.broadcast_to(s[:, None], (len(s), 11)), t1[:, None] * frac[None, :],
                                      np.full((len(s), 11), CEIL)), bead], axis=1)
    rows[:, 0, 0] = 0.0
    half = loft(rows, closed=False, colmat=["plafond"] * 10 + ["habillage_sombre"] * len(BEAD), hard=False)
    half.facing((0.0, 0.0, -1.0), face=5)
    parts = [weld(join([half, half.mirror()]))]
    dash = panel(np.array([-0.065, 0.065]), np.array([-0.011, 0.011]), 0.006, bev=0.0015, mat="amber")
    for share in (0.34, 0.72):
        for y in np.arange(-3.36, -0.42, 0.235):
            sk = m.s_of_y(np.array([y - 0.01, y, y + 0.01]))
            tk = share * skin.edge(sk, 0.0, upper=True)
            p, n = skin.hull.eval(sk, tk, normals=True)
            p = p - n * (CEIL + 0.003)
            along = (p[2] - p[0]) / np.linalg.norm(p[2] - p[0])
            across = np.cross(along, -n[1])
            parts.append(both(dash.copy().place(p[1], along, across / np.linalg.norm(across), -n[1])))
    return join(parts)


def on_liner(skin, piece, y, z=None, share=None, proud=0.0):
    """Set a plate (frame: along the ship, across, into the cabin) on the port side liner at the
    height z, or on the ceiling at a share of its half girth."""
    s = skin.maps.s_of_y(np.array([y - 0.02, y, y + 0.02]))
    if share is None:
        t = np.linspace(0.2, 0.97, 600)
        t = float(np.interp(-z, -skin.inner(np.full(600, s[1]), t, LINER)[:, 2], t))
    else:
        t = share * float(skin.edge(s[1:2], 0.0, upper=True)[0])
    pt, n = skin.hull.eval(s, np.full(3, t), normals=True)
    along = (pt[2] - pt[0]) / np.linalg.norm(pt[2] - pt[0])
    across = np.cross(-n[1], along)
    return piece.place(pt[1] - n[1] * ((LINER if share is None else CEIL) + proud), along, across / np.linalg.norm(across), -n[1])


def services(skin, rows):
    """Louvred vents low on the side liners between the rows, and a service unit over each seat:
    reading light and air outlet in a low pod."""
    rim = [(0.002, -0.002, "dark"), (0.002, -0.008, "dark")]
    parts = []
    for y in 0.5 * (np.array(rows[:-1]) + np.array(rows[1:])) + 0.12:
        parts.append(on_liner(skin, tile(0.26, 0.075, 0.016, rim, "dark", n=1), y, z=FLOOR + 0.21, proud=0.004))
        for k in range(3):
            louvre = tile(0.22, 0.011, 0.004, [(0.0015, -0.0015, "habillage_sombre"), (0.0015, -0.007, "habillage_sombre")],
                          "habillage_sombre")
            parts.append(on_liner(skin, louvre.move(0.0, -0.021 + 0.021 * k, 0.0), y, z=FLOOR + 0.21, proud=0.009))
    for y in rows:
        pod = tile(0.17, 0.08, 0.026, [(0.003, -0.003, "habillage_sombre"), (0.011, -0.018, "habillage_sombre")],
                   "habillage_sombre")
        parts.append(on_liner(skin, pod, y - 0.06, share=0.53, proud=0.013))
        lamp = upright(disc([(-0.004, 0.019, "champagne"), (0.002, 0.019, "champagne"), (0.0035, 0.017, "champagne"),
                             (0.0035, 0.014, "amber"), (0.002, 0.012, "amber")], 12, base=False))
        parts.append(on_liner(skin, lamp.move(0.042, 0.0, 0.0), y - 0.06, share=0.53, proud=0.013))
        vent = upright(disc([(-0.004, 0.018, "dark"), (0.004, 0.018, "dark"), (0.006, 0.016, "dark"), (0.006, 0.011, "champagne"),
                             (0.002, 0.009, "dark")], 12, base=False))
        parts.append(on_liner(skin, vent.move(-0.042, 0.0, 0.0), y - 0.06, share=0.53, proud=0.013))
    return both(join(parts))


def rib(skin, y_of_z, t0, t1, width, mat="habillage_sombre", n=26, to_crown=False):
    """Inner frame under a canopy post: a flat bar along the raked line y_of_z, between the liners."""
    m, hull = skin.maps, skin.hull
    tt = np.linspace(t0, t1, n)
    ss = np.full(n, float(m.s_of_y(y_of_z(-0.3))))
    for _ in range(12):
        ss = m.s_of_y(y_of_z(hull.eval(ss, tt)[:, 2]))
    p, nrm = hull.eval(ss, tt, normals=True)
    if to_crown:                                           # over the crown and down the other side
        p = np.vstack([p, (p[:-1] * (-1.0, 1.0, 1.0))[::-1]])
        nrm = np.vstack([nrm, (nrm[:-1] * (-1.0, 1.0, 1.0))[::-1]])
    tan = np.gradient(p, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(nrm, tan)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    cap = (1, 3, 1)
    run = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    fade = np.clip(1.0 - np.minimum(run, run[-1] - run) / 0.09, 0.0, 1.0) ** 2
    inner = 0.079 - 0.019 * fade                           # the bar spans 53 mm .. inner under the skin; flush at its ends
    sec = np.array([rrect(width, h, min(0.006, 0.3 * h), 1)[0] for h in inner - 0.053])
    mid = p - nrm * (0.5 * (0.053 + inner))[:, None]
    rings = mid[:, None, :] + sec[..., :1] * side[:, None, :] - sec[..., 1:] * nrm[:, None, :]
    return loft(rings, mat, caps=(cap, cap)).outward()


def bulkhead(skin):
    """Rear pressure bulkhead: the section of the cabin at Y_BULKHEAD, a framed door, its handle."""
    m = skin.maps
    s = float(m.s_of_y(Y_BULKHEAD))
    q = skin.inner(np.full(900, s), np.linspace(0.0, 0.97, 900), 0.063)
    q = q[:int(np.argmax(q[:, 2] < FLOOR - 0.004)) + 1]
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(q[:, [0, 2]], axis=0), axis=1))])
    k_c = int(np.argmax(q[:, 2] < 0.60))                   # the grid corner, on the haunch of the roof
    nu, nv = 12, 12
    roof = np.stack([np.interp(np.linspace(0.0, arc[k_c], nu // 2 + 1), arc, q[:, i]) for i in (0, 2)], axis=1)
    wall = np.stack([np.interp(np.linspace(arc[k_c], arc[-1], nv + 1), arc, q[:, i]) for i in (0, 2)], axis=1)
    sill = np.stack([np.linspace(wall[-1, 0], -wall[-1, 0], nu + 1), np.full(nu + 1, wall[-1, 1])], axis=1)
    flip = np.array([-1.0, 1.0])
    loop = np.vstack([sill[::-1][:-1], wall[::-1][:-1], roof[::-1][:-1], (roof * flip)[:-1], (wall * flip)[:-1]])
    ring = lambda y: np.column_stack([loop[:, 0], np.full(len(loop), y), loop[:, 1]])
    wall_m = loft(np.array([ring(Y_BULKHEAD), ring(Y_BULKHEAD + 0.04)]), "habillage", caps=((nu, nv, 0), None))
    wall_m.facing((0.0, -1.0, 0.0), face=-1)
    planar(wall_m, "cap0", (1, 0, 0), (0, 0, 1))
    parts = [wall_m]

    def on_wall(piece, x, z, proud):
        """Set a plate on the bulkhead, its face proud of the wall."""
        return piece.place((x, Y_BULKHEAD - proud, z), (1, 0, 0), (0, 0, 1), (0, -1, 0))

    # door: frame from the floor over a rounded head, leaf standing a little proud inside it
    top = 0.62
    frame = Path2([(-0.43, FLOOR - 0.01), (-0.43, top), (0.43, top), (0.43, FLOOR - 0.01)], [0, 0.17, 0.17, 0])
    st = np.concatenate([np.linspace(a, b, n)[:-1] for a, b, n in zip(frame.marks[:-1], frame.marks[1:], (4, 6, 3, 6, 4))]
                        + [[frame.length]])
    xz = frame.at(st)[0]
    parts.append(tube(np.column_stack([xz[:, 0], np.full(len(st), Y_BULKHEAD - 0.008), xz[:, 1]]),
                      rrect(0.026, 0.052, 0.007, 1)[0], (1, 3, 1), "habillage_sombre", right=(0.0, -1.0, 0.0)))
    hgt = top - 0.03 - FLOOR
    leaf = plate(*lattice(np.array([0.0, 0.20, 0.396 - 0.14, 0.396 - 0.586 * 0.14, 0.396]),
                          np.array([0.0, 0.3, 0.75, 1.2, hgt - 0.14, hgt - 0.586 * 0.14, hgt]), (0.0, 0.14)),
                 [(0.003, -0.003, "porte"), (0.003, -0.014, "porte")], face="porte")
    parts.append(on_wall(leaf, 0.0, FLOOR - 0.004, 0.012))
    rim = [(0.003, -0.003, "dark"), (0.003, -0.008, "dark")]
    parts.append(on_wall(tile(0.18, 0.46, 0.089, rim, "dark", n=4), 0.0, -0.02, 0.017))               # window surround
    parts.append(on_wall(tile(0.13, 0.41, 0.064, [(0.002, -0.002, "hublot"), (0.002, -0.006, "hublot")], "hublot", n=4),
                         0.0, -0.02, 0.0185))
    parts.append(on_wall(tile(0.66, 0.15, 0.02, [(0.002, -0.002, "champagne"), (0.002, -0.006, "champagne")], "champagne",
                              mid=(0.15,)), 0.0, FLOOR + 0.11, 0.0155))                                 # kick plate
    parts.append(on_wall(tile(0.05, 0.17, 0.024, rim, "dark", n=3), 0.31, -0.33, 0.0175))             # handle plate
    grip = Path2([(0.0, 0.0), (0.045, 0.0), (0.045, -0.115)], [0, 0.018, 0])                           # out, then down
    st = np.concatenate([[0.0], np.linspace(grip.marks[1], grip.marks[2], 5), [grip.length - 0.01, grip.length]])
    g = grip.at(st)[0]
    ang = np.arange(12) * math.pi / 6
    lever = 0.0095 * np.stack([np.cos(ang), np.sin(ang)], axis=1) * np.concatenate([np.ones(len(st) - 1), [0.7]])[:, None, None]
    parts.append(tube(np.column_stack([np.full(len(st), 0.31), Y_BULKHEAD - 0.012 - g[:, 0], -0.28 + g[:, 1]]), lever,
                      (3, 3, 0), "champagne", right=(1.0, 0.0, 0.0), hard=False))
    parts.append(on_wall(tile(0.30, 0.056, 0.014, [(0.003, -0.003, "dark"), (0.003, -0.016, "dark")], "dark"),
                         0.0, top + 0.105, 0.014))                                                       # sign over the door
    parts.append(on_wall(tile(0.25, 0.026, 0.008, [(0.0015, -0.0015, "amber"), (0.0015, -0.004, "amber")], "amber"),
                         0.0, top + 0.105, 0.0165))
    for sx in (-1.0, 1.0):                                 # service hatch and louvred vent on each side
        parts.append(on_wall(tile(0.40, 0.62, 0.05, [(0.003, -0.003, "habillage"), (0.003, -0.010, "habillage_sombre")],
                                  "habillage", mid=(0.08,)), sx * 0.86, -0.62, 0.008))
        parts.append(on_wall(tile(0.30, 0.11, 0.02, rim, "dark", mid=(0.07,)), sx * 0.86, -0.06, 0.0135))
        for k in range(4):
            louvre = tile(0.25, 0.012, 0.004, [(0.0015, -0.0015, "habillage_sombre"), (0.0015, -0.006, "habillage_sombre")],
                          "habillage_sombre")
            parts.append(on_wall(louvre, sx * 0.86, -0.096 + 0.024 * k, 0.018))
        parts.append(on_wall(tile(0.028, 0.05, 0.01, [(0.002, -0.002, "champagne"), (0.002, -0.006, "champagne")], "champagne"),
                             sx * (0.86 - 0.155), -0.62, 0.0125))                                      # hatch latch
    return parts


# ---- flight station --------------------------------------------------------------------------
TILT = math.radians(35.0)                               # the console face leans this much off the horizontal
CONSOLE = np.array([0.0, Y_PILOT - 0.53, -0.50])        # middle of the console face, within the pilot's reach
EX, EY = np.array([-1.0, 0.0, 0.0]), np.array([0.0, -math.cos(TILT), math.sin(TILT)])
EZ = np.cross(EX, EY)                                   # face frame: pilot's right, up the slope, out to the pilot
SCREENS = (("ecran_vol", -0.34, -0.13), ("ecran_nav", -0.118, 0.118), ("ecran_sys", 0.13, 0.34))
SCREEN_B = (-0.055, 0.11)
RIM = 0.004                                             # sunk bezel round each screen


def console():
    """Console: a slim slab with three sunk screens, two rows of keys, two knobs and a lit edge."""
    half = [0.0, 0.118 - RIM, 0.118, 0.13, 0.13 + RIM, 0.34 - RIM] + corner(0.38, 0.04, 4)
    ends = corner(0.15, 0.04, 4)
    b = np.array([-v for v in ends[::-1]] + [SCREEN_B[0], SCREEN_B[0] + RIM, SCREEN_B[1] - RIM] + ends)
    aa, bb = lattice(np.array(half), b, (0.04, 0.04))
    def glass(a, bq, a0, a1, eps):                         # nodes (eps 0.5) or cell middles (0.75) on the glass of a screen
        eps *= RIM
        return (a > a0 + eps) & (a < a1 - eps) & (bq > SCREEN_B[0] + eps) & (bq < SCREEN_B[1] - eps)

    sunk = lambda a, bq: np.where(sum(glass(a, bq, a0, a1, 0.5) for _, a0, a1 in SCREENS) > 0, -0.0025, 0.0)
    slab_m = plate(aa, bb, [(0.002, -0.002, "console"), (0.002, -0.007, "console"), (0.003, -0.009, "amber"),
                            (0.003, -0.017, "amber"), (0.0, -0.020, "graphite"), (-0.030, -0.037, "graphite")],
                   face="console", zf=sunk, back=0.0)
    cells = np.arange(slab_m.tag["cap0"].start, slab_m.tag["cap0"].stop)
    corners = slab_m.v[slab_m.f[cells]]
    mid = corners.mean(axis=1)
    for key, a0, a1 in SCREENS:
        on = glass(mid[:, 0], mid[:, 1], a0, a1, 0.75)
        slab_m.m[cells[on]] = key
        slab_m.uv[cells[on]] = np.stack([(corners[on][..., 0] - a0 - RIM) / (a1 - a0 - 2 * RIM),
                                         (corners[on][..., 1] - SCREEN_B[0] - RIM)
                                         / (SCREEN_B[1] - SCREEN_B[0] - 2 * RIM)], axis=-1)
    parts = [slab_m]
    key_m = panel(np.array([-0.011, 0.011]), np.array([-0.0095, 0.0095]), 0.006, bev=0.0018, mat="touche")
    for row, bk in enumerate((-0.122, -0.092)):
        for k in range(14):
            cap = key_m.copy().move(-0.21 + k * 0.0323, bk, 0.0038)
            if (row, k) in ((0, 0), (0, 13), (1, 6), (1, 7)):
                cap.m[:] = "amber"
            parts.append(cap)
    trim = [(0.001, -0.001, "champagne"), (0.001, -0.004, "champagne")]
    parts.append(tile(0.70, 0.004, 0.0, trim, "champagne", mid=(0.2,)).move(0.0, -0.072, 0.0015))
    lamp = tile(0.014, 0.005, 0.0, [(0.001, -0.001, "amber"), (0.001, -0.004, "amber")], "amber")
    parts += [lamp.copy().move(a, 0.130, 0.0018) for a in (-0.060, -0.030, 0.0, 0.030, 0.060)]
    knob = disc([(-0.003, 0.021, "touche"), (0.003, 0.021, "touche"), (0.005, 0.0195, "touche"), (0.015, 0.0175, "touche"),
                 (0.017, 0.0155, "champagne"), (0.017, 0.006, "champagne")], 24, base=False)
    small = disc([(-0.003, 0.0125, "touche"), (0.002, 0.0125, "touche"), (0.004, 0.0115, "touche"), (0.011, 0.0105, "touche"),
                  (0.012, 0.0090, "champagne"), (0.012, 0.0035, "champagne")], 16, base=False)
    for a in (-0.30, 0.30):
        parts.append(knob.copy().place((a, -0.107, 0.0), (0, 0, 1), (1, 0, 0), (0, 1, 0)))
        parts.append(small.copy().place((0.83 * a, -0.107, 0.0), (0, 0, 1), (1, 0, 0), (0, 1, 0)))
    for _, a0, a1 in SCREENS:                              # raised bezel round each screen
        parts.append(frame_ring(a1 - a0, SCREEN_B[1] - SCREEN_B[0], 0.006, 0.005, 0.0025, "graphite")
                     .move(0.5 * (a0 + a1), 0.5 * (SCREEN_B[0] + SCREEN_B[1]), 0.0))
    # two rows of toggle switches along the top edge, each a collar and a lever thrown forward
    collar = upright(disc([(-0.002, 0.0065, "dark"), (0.002, 0.0065, "dark"), (0.003, 0.0048, "champagne"),
                           (0.005, 0.0036, "champagne")], 12))
    lever = cord(np.array([[0.0, 0.0, 0.003], [0.0, -0.002, 0.009], [0.0, -0.005, 0.015]]), 0.0017, "champagne")
    toggle = join([collar, lever])
    parts += [toggle.copy().move(s * a, 0.133, 0.0) for a in (0.15, 0.19, 0.23, 0.27, 0.31) for s in (-1.0, 1.0)]
    # housing under the slab, where the pedestal arms come in
    under = tile(0.46, 0.17, 0.05, [(0.004, -0.004, "graphite"), (0.022, -0.040, "graphite")], "graphite", mid=(0.10,))
    parts.append(under.place((0.0, -0.02, -0.074), (-1, 0, 0), (0, 1, 0), (0, 0, -1)))
    return join(parts).place(CONSOLE, EX, EY, EZ)


def pedestal():
    """Y pedestal of the console: a stem rising from the floor parts into two arms, one welded skin.

    Rings are level. The stem's last ring has 20 nodes; each arm takes half of it and the three nodes
    of the saddle arch between them, 14 nodes, and turns into an oval on its way up to the console."""
    oval = lambda ang, rx, ry, n=2.6: np.stack([rx * np.sign(np.cos(ang)) * np.abs(np.cos(ang)) ** (2 / n),
                                                ry * np.sign(np.sin(ang)) * np.abs(np.sin(ang)) ** (2 / n)], axis=-1)
    ang = np.radians([-90.0, -68, -45, -22, -8, 0.0, 8, 22, 45, 68, 90.0, 112, 135, 158, 172, 180.0, 188, 202, 225, 248])
    z_f = -0.84                                            # the stem parts here
    zs = np.array([FLOOR + 0.004, FLOOR + 0.022, FLOOR + 0.06, -1.08, -0.98, -0.90, z_f])
    key = [FLOOR, FLOOR + 0.06, -1.03, z_f]
    stem = np.array([np.column_stack([oval(ang, rx, ry) + (0.0, y), np.full(20, z)]) for z, rx, ry, y in zip(
        zs, hermite(zs, key, [0.082, 0.050, 0.040, 0.082]), hermite(zs, key, [0.060, 0.040, 0.031, 0.031]),
        hermite(zs, key, [-4.990, -4.985, -4.925, -4.900]))])
    saddle = np.array([[0.0, -4.900 + 0.017, z_f + 0.014], [0.0, -4.900, z_f + 0.022], [0.0, -4.900 - 0.017, z_f + 0.014]])
    loop = np.vstack([stem[-1, :11], saddle])              # port arm: front middle, round the side, back middle, saddle arch
    centre = loop[:, :2].mean(axis=0)
    phi = np.unwrap(np.arctan2(loop[:, 1] - centre[1], loop[:, 0] - centre[0]))
    za = np.array([z_f + 0.022, z_f + 0.05, z_f + 0.085, -0.71, -0.66, -0.60, -0.555, -0.525])
    ka = [z_f, -0.70, -0.525]
    arm = [loop]
    for z, w, cx, cy, rx, ry in zip(za, np.clip(hermite(za, [z_f, z_f + 0.09, -0.525], [0.0, 1.0, 1.0]), 0.0, 1.0),
                                    hermite(za, ka, [centre[0], 0.105, 0.185]), hermite(za, ka, [centre[1], -4.885, CONSOLE[1] - 0.025]),
                                    hermite(za, ka, [0.036, 0.024, 0.034]), hermite(za, ka, [0.030, 0.022, 0.032])):
        shape = (1 - w) * (loop[:, :2] - centre) + w * oval(phi, rx, ry, 2.4)
        arm.append(np.column_stack([shape + (cx, cy), z + (1 - w) * (loop[:, 2] - z_f)]))
    arm = np.array(arm)
    twin = arm[:, [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 13, 12, 11]] * (-1.0, 1.0, 1.0)   # starboard arm, wound the same way
    skin = weld(join([loft(stem, "graphite", hard=False), loft(arm, "graphite", caps=(None, (3, 4, 0)), hard=False),
                      loft(twin, "graphite", caps=(None, (3, 4, 0)), hard=False)])).outward()
    foot = tile(0.23, 0.30, 0.04, [(0.004, -0.004, "dark"), (0.004, -0.015, "dark")], "dark")
    return join([skin, foot.move(0.0, -4.985, FLOOR + 0.014)])


def pedal(x):
    """Organ pedal: ribbed plate hinged on a floor bracket, propped by an arm."""
    lean = math.radians(42.0)
    along, normal = np.array([0.0, -math.cos(lean), math.sin(lean)]), np.array([0.0, math.sin(lean), math.cos(lean)])
    hinge = np.array([x, -4.83, FLOOR + 0.032])
    ribs = 0.030 + 0.024 * np.arange(7)
    b = np.concatenate([[0.0, 0.0088, 0.015], (ribs[:, None] + np.array([0.0, 0.003, 0.011, 0.014])).reshape(-1),
                        [0.205, 0.2112, 0.22]])
    aa, bb = lattice(np.array([-0.05, -0.0412, -0.035, 0.035, 0.0412, 0.05]), b, (0.015, 0.015))

    def raised(a, bq):
        on = np.zeros(a.shape, dtype=bool)
        for r in ribs:
            on |= (bq > r + 0.002) & (bq < r + 0.012)
        return np.where(on & (np.abs(a) < 0.036), 0.0032, 0.0)

    tread = plate(aa, bb, [(0.002, -0.002, "acier"), (0.002, -0.006, "acier"), (0.002, -0.014, "dark"),
                           (-0.004, -0.018, "dark")], face="acier", zf=raised, back=0.0)
    top = np.arange(tread.tag["cap0"].start, tread.tag["cap0"].stop)
    tread.m[top[(tread.v[tread.f[top], 2] > 0.001).all(axis=1)]] = "caoutchouc"   # rubber treads on the ribs
    parts = [tread.place(hinge + normal * 0.012 + along * 0.004, (-1, 0, 0), along, normal)]
    # heel rest on the deck behind the hinge: a rubber pad with raised bars
    pad_ = tile(0.10, 0.11, 0.016, rounded(0.006, "dark") + [(0.006, -0.014, "dark")], "caoutchouc")
    parts.append(pad_.move(x, -4.735, FLOOR + 0.014))
    bar_ = tile(0.076, 0.008, 0.003, [(0.0015, -0.0015, "caoutchouc"), (0.0015, -0.004, "caoutchouc")], "caoutchouc")
    parts += [bar_.copy().move(x, -4.735 + d, FLOOR + 0.0165) for d in (-0.036, -0.012, 0.012, 0.036)]
    parts.append(disc([(-0.056, 0.008), (-0.053, 0.011), (0.053, 0.011), (0.056, 0.008)], 12, "dark").move(*hinge))
    bracket = tile(0.10, 0.13, 0.02, [(0.003, -0.003, "dark"), (0.003, -0.012, "dark")], "dark")
    parts.append(bracket.move(x, -4.875, FLOOR + 0.011))
    lug = np.array([rrect(0.07, w, 0.004, 1)[0] for w in (0.030, 0.022)])
    parts.append(tube(np.array([[x, -4.83, FLOOR + 0.006], [x, -4.83, FLOOR + 0.034]]), lug, (1, 3, 1), "dark"))
    head, footing = hinge + along * 0.135 - normal * 0.005, np.array([x, -4.905, FLOOR + 0.008])
    t = np.array([0.0, 0.1, 0.9, 1.0])[:, None]
    sec = np.array([rrect(w, h, 0.005, 1)[0] for w, h in ((0.040, 0.030), (0.030, 0.020), (0.026, 0.018), (0.034, 0.024))])
    parts.append(tube(footing + (head - footing) * t, sec, (1, 3, 1), "graphite"))
    return join(parts)


def upright(piece):
    """Turn a solid of revolution from the X axis to the Z axis."""
    return piece.place((0, 0, 0), (0, 0, 1), (1, 0, 0), (0, 1, 0))


def stick():
    """Side stick in its own frame: origin on the gimbal, grip leaning forward. The engine moves it."""
    boot = upright(disc([(-0.006, 0.034), (0.001, 0.035), (0.006, 0.032), (0.010, 0.027), (0.014, 0.029), (0.018, 0.026),
                         (0.022, 0.021), (0.026, 0.023), (0.030, 0.020), (0.034, 0.015), (0.042, 0.014)], 20, "caoutchouc",
                        base=False, hard=False))
    z = np.array([0.036, 0.044, 0.060, 0.085, 0.110, 0.132, 0.150, 0.166, 0.176])
    keys = [0.036, 0.06, 0.10, 0.135, 0.165, 0.176]
    w = hermite(z, keys, [0.020, 0.030, 0.028, 0.026, 0.036, 0.030])
    d = hermite(z, keys, [0.022, 0.036, 0.034, 0.030, 0.042, 0.034])
    rings = np.array([np.column_stack([rrect(wk, dk, 0.45 * min(wk, dk), 4)[0], np.full(20, zk)]) for zk, wk, dk in zip(z, w, d)])
    rings[..., 1] += -0.16 * (rings[..., 2] - 0.036) - 0.9 * (rings[..., 2] - 0.036) ** 2      # lean and curve forward
    grip = loft(rings, "caoutchouc", caps=((5, 5, 2), (5, 5, 2, 0.006)), hard=False).outward()
    top = rings[-1].mean(axis=0)
    hat = upright(disc([(-0.002, 0.008, "champagne"), (0.004, 0.008, "champagne"), (0.006, 0.006, "amber"),
                        (0.006, 0.003, "amber")], 12))
    trigger = np.array([rrect(0.012, h, 0.003, 1)[0] for h in (0.016, 0.022, 0.018)])
    path = top + np.array([[0.0, -0.012, -0.034], [0.0, -0.026, -0.040], [0.0, -0.034, -0.052]])
    return join([boot, grip, hat.move(top[0], top[1] + 0.010, top[2] + 0.004), tube(path, trigger, (1, 3, 1), "dark")])


def throttle():
    """Throttle lever in its own frame: origin on its pivot (axis X), T grip on top. The engine moves it."""
    sec = np.array([rrect(0.010, w, 0.003, 1)[0] for w in (0.026, 0.024, 0.018, 0.016)])
    lever = tube(np.array([[0.0, 0.0, -0.012], [0.0, 0.0, 0.0], [0.0, 0.0, 0.085], [0.0, 0.0, 0.108]]), sec, (1, 3, 1), "dark")
    grip = disc([(-0.040, 0.007, "caoutchouc"), (-0.037, 0.0125, "caoutchouc"), (-0.031, 0.0155, "caoutchouc"),
                 (0.031, 0.0155, "caoutchouc"), (0.037, 0.0125, "champagne"), (0.040, 0.007, "amber")], 16, hard=False)
    return join([lever, grip.move(0.0, 0.0, 0.112)])


# ---- scene ----------------------------------------------------------------------------------
def palette(mats):
    """Material keys of the interior: the hull library where it has the colour, new ones else.
    Tiling micro-surface maps and the screen placeholders are used when the texture folder has them."""
    def get(name, *args, maps=None, **kw):
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = matlib.principled(name, *args, **kw)
            if maps:
                matlib.textured(mat, maps[0] + "_normal.png", maps[0] + "_roughness.png", tiles=maps[1], strength=maps[2])
        return mat

    def screen(name, image):
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = matlib.principled(name, (0.02, 0.06, 0.09), 0.12, emit=(0.08, 0.40, 0.50), emit_strength=0.5)
            path = os.path.join(matlib.TEXTURES, image)
            if os.path.exists(path):                       # placeholder: the engine draws the live instruments
                nt = mat.node_tree
                bsdf, tex = nt.nodes.get("Principled BSDF"), nt.nodes.new("ShaderNodeTexImage")
                tex.image = bpy.data.images.load(path, check_existing=True)
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = 1.0
        return mat

    return {
        "amber": mats.get("amber") or get("NAV_Lumiere_Ambre", (1.0, 0.45, 0.05), 0.3, emit=(1.0, 0.36, 0.03), emit_strength=1.5),
        "dark": mats.get("dark") or get("NAV_Metal_Sombre", (0.075, 0.08, 0.09), 0.40, 0.8),
        "blanc": mats.get("white") or get("NAV_Email_Blanc", (0.90, 0.89, 0.86), 0.24, coat=0.5),
        "acier": mats.get("titanium") or get("NAV_Metal_Titane", (0.42, 0.43, 0.45), 0.32, 0.9),
        "cuir": get("NAV_Cuir_Ambre", (0.83, 0.56, 0.115), 0.58, maps=("leather", 7.0, 0.6)),
        "cuir_clair": get("NAV_Cuir_Ambre_Clair", (0.86, 0.60, 0.16), 0.60, maps=("leather", 7.0, 0.6)),
        "cuir_noir": get("NAV_Cuir_Graphite", (0.065, 0.065, 0.07), 0.62, maps=("leather", 7.0, 0.5)),
        "passepoil": get("NAV_Cuir_Passepoil", (0.36, 0.20, 0.045), 0.50, maps=("leather", 7.0, 0.4)),
        "sangle": get("NAV_Sangle", (0.085, 0.088, 0.095), 0.86),
        "graphite": get("NAV_Coque_Graphite", (0.11, 0.115, 0.125), 0.42, coat=0.25),
        "champagne": get("NAV_Metal_Champagne", (0.80, 0.68, 0.50), 0.30, 1.0, maps=("metal_brushed", 4.0, 0.2)),
        "habillage": get("NAV_Habillage_Gris", (0.47, 0.45, 0.42), 0.70),
        "habillage_sombre": get("NAV_Habillage_Graphite", (0.105, 0.108, 0.115), 0.62),
        "plafond": get("NAV_Habillage_Plafond", (0.16, 0.162, 0.17), 0.66),
        "plancher": get("NAV_Plancher", (0.115, 0.12, 0.128), 0.55, maps=("deck_tread", 5.0, 0.6)),
        "porte": get("NAV_Habillage_Porte", (0.56, 0.54, 0.50), 0.60),
        "hublot": get("NAV_Hublot", (0.02, 0.035, 0.04), 0.08, coat=1.0),
        "caoutchouc": get("NAV_Caoutchouc", (0.03, 0.03, 0.032), 0.78),
        "console": get("NAV_Console_Noir", (0.02, 0.022, 0.026), 0.22, coat=0.6),
        "touche": get("NAV_Touches", (0.17, 0.175, 0.185), 0.48),
        "ecran_vol": screen("NAV_Ecran_Vol", "screen_flight.png"),
        "ecran_nav": screen("NAV_Ecran_Nav", "screen_nav.png"),
        "ecran_sys": screen("NAV_Ecran_Systemes", "screen_systems.png"),
    }


def emit(name, piece, pal, origin=(0.0, 0.0, 0.0), mesh=None, local=False):
    """Object at origin from a piece given in ship coordinates, or in its own frame if local.
    A given mesh is instanced instead."""
    if mesh is None:
        mesh = bpy.data.meshes.new(name)
        keys = list(dict.fromkeys(piece.m.tolist()))
        mesh.from_pydata((piece.v if local else piece.v - origin).tolist(), [], piece.f.tolist())
        for k in keys:
            mesh.materials.append(pal[k])
        slot = {k: i for i, k in enumerate(keys)}
        mesh.polygons.foreach_set("material_index", np.array([slot[k] for k in piece.m], dtype=np.int32))
        mesh.polygons.foreach_set("use_smooth", np.ones(len(piece.f), dtype=bool))
        mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", piece.uv.astype(np.float32).ravel())
        mesh.update()
        mesh.normals_split_custom_set_from_vertices(vertex_normals(piece).tolist())
    obj = bpy.data.objects.new(name, mesh)
    obj.location = origin
    meshkit.collection(COL).objects.link(obj)
    return obj


def vertex_normals(piece):
    """Vertex normals. Soft pieces: face normals weighted by the corner angle. Hard pieces: by the
    squared face area, so that the large faces stay flat and the bevels carry the turn."""
    p = piece.v[piece.f]
    fn = 0.5 * np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 1])
    area = np.linalg.norm(fn, axis=1, keepdims=True)
    unit = fn / np.maximum(area, 1e-20)
    soft, hard = np.zeros_like(piece.v), np.zeros_like(piece.v)
    for k in range(4):
        a, b = p[:, (k + 1) % 4] - p[:, k], p[:, k - 1] - p[:, k]
        cos = np.einsum("ij,ij->i", a, b) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-20)
        np.add.at(soft, piece.f[:, k], unit * np.arccos(np.clip(cos, -1.0, 1.0))[:, None])
        np.add.at(hard, piece.f[:, k], fn * area)
    n = np.where(piece.hard[:, None], hard, soft)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-20)


def build(mats, grid):
    """grid: the hull's HullGrid (a bare Hull surface is accepted too)."""
    pal = palette(mats)
    skin = Skin(grid)
    objs = []
    hw = deck_width(skin)
    frame, front = prow_frame(skin, hw)
    liner = side_liner(skin, front)
    roof = ceiling(skin)
    s_of = lambda y: skin.maps.s_of_y(np.array([y]))
    arch = lambda z: hg.ARCH_Y - hg.ARCH_RAKE * (hg.CROWN_Z - z)
    ribs = [rib(skin, arch, float(skin.edge(s_of(-3.76), 0.03)[0]), 0.0, 0.076, to_crown=True)]
    for y0 in hg.MULLION_Y:                                # the posts end inside the liners
        post = rib(skin, lambda z, y0=y0: y0 - hg.MULLION_RAKE * (hg.CROWN_Z - z),
                   float(skin.edge(s_of(y0 - 0.08), 0.03)[0]), float(skin.edge(s_of(y0 - 0.02), 0.03, upper=True)[0]), 0.05)
        ribs.append(both(post))
    objs.append(emit("Cabine_Plancher", floor_plate(hw), pal))
    objs.append(emit("Cabine_Cadre_Proue", frame, pal))
    objs.append(emit("Cockpit_Quille", keel_spine(), pal))
    objs.append(emit("Cabine_Habillage", join([liner, roof, services(skin, ROWS), fittings(skin)] + ribs), pal))
    objs.append(emit("Cabine_Cloison_Arriere", join(bulkhead(skin)), pal))
    pax, _ = seat(PASSENGER)
    mesh = None
    for row, y in enumerate(ROWS, start=1):
        for side, x in (("G", 0.66), ("D", -0.66)):
            objs.append(emit(f"Siege_Passager_R{row}_{side}", pax, pal, (x, y, FLOOR), mesh, local=True))
            mesh = objs[-1].data
    mesh.name = "Siege_Passager"
    at = np.array([0.0, Y_PILOT, FLOOR])
    pilot, pod = seat(PILOT)
    objs.append(emit("Siege_Pilote", pilot, pal, at, local=True))
    objs.append(emit("Poste_Pilotage", join([console(), pedestal(), pedal(0.21), pedal(-0.21)]), pal))
    objs.append(emit("Manche", stick(), pal, at + pod * (-1.0, 1.0, 1.0), local=True))             # pilot's right hand
    objs.append(emit("Manette_Gaz", throttle(), pal, at + pod + (0.0, 0.0, -0.030), local=True))    # left hand
    return objs


# ---- the hull seen from inside ----------------------------------------------------------------
class Skin:
    """Inward offsets of the hull, its glazing outline, and the depth of points under the outer skin."""

    def __init__(self, hull):
        """hull: the surface, or a ready hullgrid.HullGrid, which is then reused."""
        self.grid = hull if hasattr(hull, "hull") else hg.HullGrid(hull)
        self.hull = self.grid.hull
        self.maps = self.grid.maps
        self._rings = None
        self._outline = None

    def inner(self, s, t, d):
        """Points d metres inside the skin, along its normal."""
        p, n = self.hull.eval(s, t, normals=True)
        return p - n * np.asarray(d, dtype=float)[..., None]

    def edge(self, st, margin=0.0, upper=False):
        """t, at the stations st, of the line lying margin metres outside the glazing on the skin
        (negative: inside it): along the sill and up the rear edge of the last window, or along the
        window tops if upper. Aft of the last window both lines level out, 27 mm from where they met."""
        m = self.maps
        if self._outline is None:
            g, c = self.grid, self.grid.col
            seq = ([(a, hg.B_SILL) for a in range(c["end"] + 1)]
                   + [(c["end"], b) for b in range(hg.B_SILL - 1, hg.B_ROOF - 1, -1)]
                   + [(a, hg.B_ROOF) for a in range(c["end"] - 1, c["arch"] - 1, -1)])
            ia, ib = np.array(seq).T
            s, t = g.s[ia, ib], g.t[ia, ib]
            line = np.stack([m.lam_of_s(s), t / T1 * m.at(m.gu, s)], axis=1)   # unrolled: length, girth from the top
            tan = np.gradient(line, axis=0)
            nrm = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
            self._outline = (line, nrm / np.linalg.norm(nrm, axis=1, keepdims=True), line[int(np.argmax(line[:, 0]))])
        line, nrm, aft = self._outline
        out = line + margin * nrm
        k = int(np.argmax(out[:, 0]))                                          # the aftmost point parts the two lines
        branch = out[k:][::-1] if upper else out[:k + 1]
        lam = m.lam_of_s(st)
        girth = np.interp(lam, np.maximum.accumulate(branch[:, 0]), branch[:, 1])
        w = hg.smoothstep(aft[0] - 0.14, aft[0] + 0.02, lam)
        girth = (1.0 - w) * girth + w * (aft[1] + (-1.0 if upper else 1.0) * (0.027 + margin))
        return T1 * girth / m.at(m.gu, st)

    def depth(self, pts):
        """Distance of points under the outer skin, negative outside. Exact to about 2 mm near the
        skin; deeper than 0.24 m it is a lower bound."""
        if self._rings is None:
            m = self.maps
            s = np.interp(np.arange(-7.0, float(m.y[-1]), 0.012), m.y, m.s)   # nose to stern
            t = np.concatenate([np.linspace(0.0, T1, 210, endpoint=False), np.linspace(T1, T2, 8, endpoint=False),
                                np.linspace(T2, 1.0, 230)])
            self._rings = self.hull.eval(s[:, None], t[None, :])
        rings = self._rings
        ring_y = rings[:, 0, 1]
        q = np.column_stack([np.abs(pts[:, 0]), pts[:, 1], pts[:, 2]])
        k = np.clip(np.searchsorted(ring_y, q[:, 1]), 0, len(rings) - 1)
        out = np.zeros(len(q))
        for c0 in range(0, len(q), 4000):
            sl = slice(c0, c0 + 4000)
            qq, kk = q[sl], k[sl]
            sec = rings[kk][:, :, [0, 2]]                                   # (n, nt, 2): x, z
            a, b = sec, np.roll(sec, -1, axis=1)                            # the roll closes along the centreline
            x, z = qq[:, None, 0], qq[:, None, 2]
            cross = (a[..., 1] > z) != (b[..., 1] > z)
            x_at = a[..., 0] + (z - a[..., 1]) * (b[..., 0] - a[..., 0]) / np.where(cross, b[..., 1] - a[..., 1], 1.0)
            inside = (np.sum(cross & (x < x_at), axis=1) % 2) == 1
            plane = np.sqrt(((sec - qq[:, None, [0, 2]]) ** 2).sum(axis=2).min(axis=1))
            dist = np.where(plane > 0.30, 0.8 * plane, np.inf)
            near = np.nonzero(plane <= 0.30)[0]
            if len(near):
                best = np.full(len(near), np.inf)
                for j in range(-26, 27):
                    ring = rings[np.clip(kk[near] + j, 0, len(rings) - 1)]
                    best = np.minimum(best, ((ring - qq[near][:, None, :]) ** 2).sum(axis=2).min(axis=1))
                dist[near] = np.sqrt(best)
            out[sl] = np.where(inside, dist, -dist)
        return out


BUDGET = 200000                    # triangles of the module, seats counted once per instance
GEAR_BOX = ((-0.46, 0.46), (-4.50, -2.30), -1.30)   # the nose gear well: x, y and the roof nothing of ours goes under
SKIN_LEAST = {"Cabine_Cadre_Proue": 0.004}           # objects allowed closer to the skin than 50 mm


def gap(skin, pts, y0=-6.95, y1=-3.40):
    """Exact distance of points to the hull skin, the glass included, from a 1 cm sampling of the skin
    between the stations y0 and y1 (the hull is symmetric: points are folded to port)."""
    s = skin.maps.s_of_y(np.arange(y0, y1, 0.01))
    q = skin.hull.eval(s[:, None], np.linspace(0.0, 1.0, 330)[None, :]).reshape(-1, 3)
    p = np.column_stack([np.abs(pts[:, 0]), pts[:, 1], pts[:, 2]])
    out = np.empty(len(p))
    for c in range(0, len(p), 48):
        d2 = (p[c:c + 48] ** 2).sum(axis=1)[:, None] - 2.0 * p[c:c + 48] @ q.T + (q ** 2).sum(axis=1)[None, :]
        out[c:c + 48] = np.sqrt(np.maximum(d2.min(axis=1), 0.0))
    return out


def self_check(objs, hull, verbose=True):
    """Measure the built objects: skin clearance, triangles, n-gons, loose and doubled vertices,
    degenerate faces, edge manifoldness and winding, UVs, left/right seat symmetry; the deck's
    clearance from the glass forward of the seat, and what enters the nose gear well's volume."""
    skin = Skin(hull)
    bpy.context.view_layer.update()                    # world matrices of the objects just made
    report = {"objects": {}, "triangles": 0, "ok": True, "notes": []}
    world, meshes = {}, {}
    shared = ("loose", "doubled", "degenerate", "nonmanifold", "miswound", "open_edges")
    for o in objs:
        me = o.data
        nv, nf = len(me.vertices), len(me.polygons)
        co = np.zeros(nv * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        total = np.zeros(nf, dtype=np.int32)
        me.polygons.foreach_get("loop_total", total)
        loops = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", loops)
        mw = np.array(o.matrix_world)
        world[o.name] = co @ mw[:3, :3].T + mw[:3, 3]
        depth = skin.depth(world[o.name])
        least = SKIN_LEAST.get(o.name, 0.05)
        row = {"triangles": int((total - 2).sum()), "ngons": int((total > 4).sum()), "tris": int((total == 3).sum()),
               "min_depth": float(depth.min()), "shallow": int((depth < least).sum()), "uv": len(me.uv_layers) > 0}
        if me.name not in meshes and (total == 4).all():
            quads = loops.reshape(-1, 4)
            p = co[quads]
            area = 0.5 * np.linalg.norm(np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 1]), axis=1)
            edge = np.linalg.norm(p - np.roll(p, -1, axis=1), axis=2)
            e = np.stack([quads, np.roll(quads, -1, axis=1)], axis=-1).reshape(-1, 2)
            n_dir = np.unique(e[:, 0] * (nv + 1) + e[:, 1], return_counts=True)[1]
            n_und = np.unique(e.min(axis=1) * (nv + 1) + e.max(axis=1), return_counts=True)[1]
            meshes[me.name] = {
                "loose": int(nv - len(np.unique(loops))),
                "doubled": int(nv - len(np.unique(np.round(co / 2e-5).astype(np.int64), axis=0))),
                "degenerate": int(((area < 1e-9) | (edge.min(axis=1) < 1e-6)).sum()),
                "nonmanifold": int((n_und > 2).sum()), "miswound": int((n_dir > 1).sum()),
                "open_edges": int((n_und == 1).sum())}
            uv = np.zeros(len(me.loops) * 2)
            me.uv_layers[0].data.foreach_get("uv", uv)
            slot = np.zeros(nf, dtype=np.int32)
            me.polygons.foreach_get("material_index", slot)
            for i, mat in enumerate(me.materials):
                if mat and mat.name.startswith("NAV_Ecran_"):
                    f_uv = uv.reshape(-1, 4, 2)[slot == i]
                    row["screen_uv_" + mat.name[10:]] = [round(float(f_uv.min()), 3), round(float(f_uv.max()), 3)]
        row.update(meshes.get(me.name, {}))
        report["objects"][o.name] = row
        report["triangles"] += row["triangles"]
        bad = bool(row["ngons"] or row["shallow"] or not row["uv"] or any(row.get(k) for k in shared[:5]))
        report["ok"] &= not bad
        if verbose:
            print("CHECK %-24s tris %6d depth %+.3f shallow %d ngon %d tri %d | loose %s doubled %s degenerate %s "
                  "nonmanifold %s miswound %s open %s%s" % (
                      o.name, row["triangles"], row["min_depth"], row["shallow"], row["ngons"], row["tris"],
                      *[row.get(k) for k in shared], "   <-- FAIL" if bad else ""))
    key = lambda p: np.unique(np.round(p / 1e-4).astype(np.int64), axis=0)
    for name in sorted(world):
        if name.endswith("_G") and name[:-1] + "D" in world:
            a, b = key(world[name] * (-1.0, 1.0, 1.0)), key(world[name[:-1] + "D"])
            if a.shape != b.shape or not (a == b).all():
                report["notes"].append(name + " is not the mirror of its starboard twin")
    for name, row in report["objects"].items():
        for key in [k for k in row if k.startswith("screen_uv_")]:
            report["ok"] &= row[key] == [0.0, 1.0]
            if verbose:
                print("CHECK %s: UVs of NAV_Ecran_%s span %s" % (name, key[10:], row[key]))
    # the deck forward of the seat keeps 0.25 m from the glass; the spine's least distance
    if "Cabine_Plancher" in world:
        p = world["Cabine_Plancher"]
        clear = float(gap(skin, p[p[:, 1] < Y_SEAT_FRONT]).min())
        report["deck_glass"] = clear
        if clear < 0.25:
            report["notes"].append("deck %.3f m from the glass forward of the seat" % clear)
    if "Cockpit_Quille" in world:
        report["spine_glass"] = float(gap(skin, world["Cockpit_Quille"]).min())
    # nothing of ours under the roof of the nose gear well, but the prow frame where the prow line
    # itself crosses the corner of that volume, within 0.12 m of the skin
    (x0, x1), (y0, y1), roof = GEAR_BOX
    report["gear_box"] = {}
    for name, p in world.items():
        inside = (p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1) & (p[:, 2] < roof)
        if inside.any():
            q = p[inside]
            report["gear_box"][name] = dict(vertices=int(inside.sum()), x=float(np.abs(q[:, 0]).min()),
                                            y=float(q[:, 1].max()), z=float(q[:, 2].max()))
            deep = float(skin.depth(q).max())
            if name != "Cabine_Cadre_Proue" or deep > 0.12:
                report["notes"].append("%s enters the nose gear well, %.3f m under the skin" % (name, deep))
    report["ok"] = bool(report["ok"] and not report["notes"] and report["triangles"] <= BUDGET)
    if verbose:
        print("CHECK deck to glass forward of y %.2f: %.3f m; spine to glass %.3f m" % (
            Y_SEAT_FRONT, report.get("deck_glass", float("nan")), report.get("spine_glass", float("nan"))))
        print("CHECK in the nose gear well volume: %s" % report["gear_box"])
        print("CHECK total triangles %d / %d; notes %s; ok %s" % (report["triangles"], BUDGET, report["notes"], report["ok"]))
    return report
