"""Hull surface of the Navette AAA, rebuilt from the validated section blueprint.

The blueprint holds 41 half-sections sampled by polar angle. Here each section is
re-parametrised on its two shoulder edges E1 and E2, so the shoulder stays on one
parameter line from nose to stern:

    t in [0, T1]   upper skin, top centreline to the upper shoulder edge E1
    t in [T1, T2]  shoulder face, E1 to E2
    t in [T2, 1]   lower skin, E2 to the bottom centreline

Along the length the parameter s is the control-station index; station 0 is the nose pole and
the last one the stern pole. Frame: metres, nose -Y, up +Z, port +X. Only numpy is needed.
"""
import json
import os

import numpy as np

SCALE = 7.2
HERE = os.path.dirname(os.path.abspath(__file__))

NU, NL = 24, 28          # control spans of the upper and lower skins
T1, T2 = 0.47, 0.50      # parameters of the two shoulder edges
LAST_STATION = 38        # the blueprint's last two rings are extrapolated: the stern is designed
STERN_START_Y, STERN_END_Y = 5.50, 6.79      # the hull closes on itself between these: a rounded stern
STERN_ANGLES = (11.25, 22.5, 33.75, 45.0, 56.25, 67.5, 78.75, 85.0)   # closing rings, degrees to the pole
STERN_BLEND = (0.0, 0.0, 0.0, 0.10, 0.30, 0.60, 0.90, 1.0)            # share of clean oval in each
NOSE_TIP_Y = -0.9515 * SCALE
SHARP_Y0, SHARP_Y1 = 0.55, 1.75   # the shoulder turns from a soft bulge into a crisp edge
FACE_MIN = 0.030         # least height of the shoulder face, metres
NOSE_BLEND = (1.0, 0.85, 0.55, 0.25, 0.08)   # share of clean oval in the first rings of the nose


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _cr_weights(u):
    """Uniform Catmull-Rom weights and their derivatives for a local parameter u in [0, 1]."""
    u2, u3 = u * u, u * u * u
    w = np.stack([-0.5 * u3 + u2 - 0.5 * u, 1.5 * u3 - 2.5 * u2 + 1.0,
                  -1.5 * u3 + 2.0 * u2 + 0.5 * u, 0.5 * u3 - 0.5 * u2], axis=-1)
    d = np.stack([-1.5 * u2 + 2.0 * u - 0.5, 4.5 * u2 - 5.0 * u,
                  -4.5 * u2 + 4.0 * u + 0.5, 1.5 * u2 - u], axis=-1)
    return w, d


def _resample(points, n, ghost_start, ghost_end):
    """n + 1 points at equal arc length along a Catmull-Rom curve through the polyline."""
    pts = np.vstack([ghost_start, points, ghost_end])
    dense = []
    sub = 12
    for k in range(1, len(pts) - 2):
        u = np.linspace(0.0, 1.0, sub, endpoint=False)
        w, _ = _cr_weights(u)
        dense.append(w @ pts[k - 1:k + 3])
    dense = np.vstack(dense + [points[-1][None, :]])
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    target = np.linspace(0.0, arc[-1], n + 1)
    return np.stack([np.interp(target, arc, dense[:, 0]), np.interp(target, arc, dense[:, 1])], axis=1)


def _shoulder(pts, y):
    """Indices and positions of the two shoulder edges of one blueprint half-section."""
    ka = int(np.argmax(pts[10:39, 0])) + 10
    d = np.diff(pts, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = np.abs(np.degrees(np.unwrap(np.diff(ang))))        # turn[k-1] is the turn at vertex k
    k1 = k2 = ka
    if y > SHARP_Y0:
        thr = 22.0
        if turn[ka - 2] > thr and pts[ka - 1, 0] > pts[ka, 0] - 0.20:
            k1 = ka - 1
        if turn[ka] > thr and pts[ka + 1, 0] > pts[ka, 0] - 0.20:
            k2 = ka + 1
    e1, e2 = pts[k1].copy(), pts[k2].copy()
    if k1 == k2:                                              # one vertex: open a face around it
        up = pts[k1 - 1] - pts[k1]
        dn = pts[k2 + 1] - pts[k2]
        face = _face_min(pts)
        e1 = pts[k1] + up / np.linalg.norm(up) * (face * 0.5)
        e2 = pts[k2] + dn / np.linalg.norm(dn) * (face * 0.5)
    return k1, k2, e1, e2


def _oval_section(section, face, power=2.35):
    """Superellipse half-section with the extents of the given one, in the same point layout."""
    top, bottom, beam = section[0, 1], section[-1, 1], section[:, 0].max()
    centre, half = 0.5 * (top + bottom), 0.5 * (top - bottom)
    delta = 0.5 * face / half

    def arc(phi0, phi1, n):
        phi = np.linspace(phi0, phi1, 400)
        x = beam * np.abs(np.sin(phi)) ** (2.0 / power)
        z = centre + half * np.sign(np.cos(phi)) * np.abs(np.cos(phi)) ** (2.0 / power)
        length = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(z)))])
        pos = np.linspace(0.0, length[-1], n + 1)
        return np.stack([np.interp(pos, length, x), np.interp(pos, length, z)], axis=1)

    return np.vstack([arc(0.0, 0.5 * np.pi - delta, NU), arc(0.5 * np.pi + delta, np.pi, NL)])


def _face_min(pts):
    """Least height of the shoulder face: 3 cm, less on the small sections of the nose."""
    girth = np.linalg.norm(np.diff(pts, axis=0), axis=1).sum()
    return min(FACE_MIN, 0.035 * girth)


FAIR_LENGTH, FAIR_SECTION = 1.0, 1.0      # stiffness of the fairing along the length and round the section


def _fair(q, ys, sharp):
    """Fair the control net in place: a penalised fit that keeps the long forms.

    The source mesh was sculpted and carries lumps of about a metre. The fit resists changes of
    curvature (third differences) from station to station and round each skin, so parabolic forms
    such as the nose survive untouched. Where the shoulder is a crisp edge, its two lines stay
    put and the skins are fitted between them; forward of that, the section is one smooth curve
    and the fit runs across the shoulder. Returns the largest move in metres.
    """
    before = q.copy()
    n, m = q.shape[:2]
    d3 = np.zeros((n - 3, n))
    for i in range(n - 3):
        d3[i, i:i + 4] = (-1.0, 3.0, -3.0, 1.0)
    along = d3.T @ d3 * FAIR_LENGTH

    def third(lo, hi):
        """Third-difference penalty inside one skin, columns lo..hi inclusive."""
        d = np.zeros((hi - lo - 2, m))
        for k in range(lo, hi - 2):
            d[k - lo, k:k + 4] = (-1.0, 3.0, -3.0, 1.0)
        return d.T @ d

    around = (third(0, NU) + third(NU + 1, m - 1)) * FAIR_SECTION
    system = np.kron(np.eye(n), np.eye(m) + around) + np.kron(along, np.eye(m))
    # Across the shoulder: third divided differences on the true spacings, where it is smooth.
    length = lambda a, b: np.linalg.norm(q[:, a] - q[:, b], axis=1)
    for first in (NU - 2, NU - 1, NU):
        cols = np.arange(first, first + 4)
        steps = np.stack([length(cols[k], cols[k + 1]) for k in range(3)], axis=1)
        u = np.concatenate([np.zeros((n, 1)), np.cumsum(steps, axis=1)], axis=1)
        mean = steps.mean(axis=1)
        for i in range(n):
            coef = np.array([1.0 / np.prod([u[i, k] - u[i, l] for l in range(4) if l != k]) for k in range(4)])
            coef *= 6.0 * mean[i] ** 3 * np.sqrt((1.0 - sharp[i]) * FAIR_SECTION)
            idx = i * m + cols
            system[np.ix_(idx, idx)] += np.outer(coef, coef)
    pin = 1e7
    for axis in (0, 1):
        rhs = q[:, :, axis].reshape(-1).copy()
        mat = system.copy()
        for j in (NU, NU + 1):                            # a crisp shoulder is already fair: it stays
            idx = np.arange(n) * m + j
            mat[idx, idx] += pin * sharp
            rhs[idx] += pin * sharp * q[:, j, axis]
        if axis == 0:                                     # both centrelines stay at x = 0
            for j in (0, m - 1):
                idx = np.arange(n) * m + j
                mat[idx, idx] += pin
                rhs[idx] = 0.0
        q[:, :, axis] = np.linalg.solve(mat, rhs).reshape(n, m)
    q[:, 0, 0] = q[:, -1, 0] = 0.0
    return float(np.linalg.norm(q - before, axis=2).max())


class Hull:
    def __init__(self, path=os.path.join(HERE, "blueprint.json")):
        bp = json.load(open(path, "r", encoding="utf-8"))
        secs = bp["sections"][:LAST_STATION + 1]
        ys = np.array([s["y"] for s in secs]) * SCALE
        raw = np.array([s["pts"] for s in secs]) * SCALE          # (n, 49, 2): x, z
        self.blueprint_y, self.blueprint_pts = ys, raw
        n = len(ys)

        edges = [_shoulder(raw[i], ys[i]) for i in range(n)]
        e1 = np.array([e[2] for e in edges])
        e2 = np.array([e[3] for e in edges])
        # The polar sampling quantises the shoulder. Fair the height of both edges and their
        # inset from the beam along the length; the beam itself stays the blueprint's.
        beam = raw[:, 10:39, 0].max(axis=1)
        inset = np.stack([beam - e1[:, 0], beam - e2[:, 0]], axis=1)
        height = np.stack([e1[:, 1], e2[:, 1]], axis=1)
        for _ in range(3):
            for a in (inset, height):
                a[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
        inset -= inset.min(axis=1, keepdims=True)
        e1 = np.stack([beam - inset[:, 0], height[:, 0]], axis=1)
        e2 = np.stack([beam - inset[:, 1], height[:, 1]], axis=1)
        gap = e1 - e2
        length = np.linalg.norm(gap, axis=1)
        least = np.array([_face_min(raw[i]) for i in range(n)])
        short = length < least
        e2[short, 1] = e1[short, 1] - np.sqrt(np.maximum(least[short] ** 2 - gap[short, 0] ** 2, 0.0))

        q = np.zeros((n, NU + NL + 2, 2))
        for i in range(n):
            k1, k2 = edges[i][0], edges[i][1]
            mirror = lambda p: np.array([-p[0], p[1]])
            up = np.vstack([raw[i, :k1], e1[i]])
            # Drop blueprint points closer to the new edge than a third of a span: they kink the fit.
            while len(up) > 3 and np.linalg.norm(up[-2] - up[-1]) < 0.035:
                up = np.delete(up, -2, axis=0)
            lo = np.vstack([e2[i], raw[i, k2 + 1:]])
            while len(lo) > 3 and np.linalg.norm(lo[1] - lo[0]) < 0.035:
                lo = np.delete(lo, 1, axis=0)
            q[i, :NU + 1] = _resample(up, NU, mirror(up[1]), 2.0 * up[-1] - up[-2])
            q[i, NU + 1:] = _resample(lo, NL, 2.0 * lo[0] - lo[1], mirror(lo[-2]))
        # The source tip is a ragged lens: the first rings blend to a clean superellipse of the same extents.
        for i, w in enumerate(NOSE_BLEND):
            q[i] = (1.0 - w) * q[i] + w * _oval_section(q[i], _face_min(raw[i]))
        self.sharp = smoothstep(SHARP_Y0, SHARP_Y1, ys)
        self.fairing = _fair(q, ys, self.sharp)

        # Stern: no engine there. From STERN_START_Y the section shrinks about its own middle by the
        # cosine of an angle that reaches the pole, so the hull ends rounded in plan and in profile.
        keep = int(np.searchsorted(ys, STERN_START_Y))
        ang = np.radians(STERN_ANGLES)
        y_c = STERN_START_Y + (STERN_END_Y - STERN_START_Y) * np.sin(ang)
        k = np.clip(np.searchsorted(ys, y_c) - 1, 0, n - 2)
        w = np.clip((y_c - ys[k]) / (ys[k + 1] - ys[k]), 0.0, 1.0)[:, None, None]
        closing = (1.0 - w) * q[k] + w * q[k + 1]
        mid = 0.5 * (closing[:, :1, 1] + closing[:, -1:, 1])
        closing[:, :, 0] *= np.cos(ang)[:, None]
        closing[:, :, 1] = mid + (closing[:, :, 1] - mid) * np.cos(ang)[:, None]
        for i, share in enumerate(STERN_BLEND):
            closing[i] = (1.0 - share) * closing[i] + share * _oval_section(closing[i], FACE_MIN * np.cos(ang[i]))
        q = np.concatenate([q[:keep], closing])
        ys = np.concatenate([ys[:keep], y_c])
        self.sharp = np.concatenate([self.sharp[:keep], self.sharp[keep - 1] * (1.0 - np.array(STERN_BLEND))])
        n = len(ys)

        # Control stations: nose pole, the rings, stern pole. Past each pole lies the opposite meridian.
        z_tip = 0.5 * (raw[0, 0, 1] + raw[0, -1, 1])
        self.tip = np.array([0.0, NOSE_TIP_Y, z_tip])
        self.stern_tip = np.array([0.0, STERN_END_Y, float(0.5 * (q[-1, 0, 1] + q[-1, -1, 1]))])
        ctrl = np.zeros((n + 4, q.shape[1], 3))
        ctrl[2:-2, :, 0], ctrl[2:-2, :, 2] = q[:, :, 0], q[:, :, 1]
        ctrl[2:-2, :, 1] = ys[:, None]
        for pole, ghost, ring, tip in ((1, 0, 0, self.tip), (-2, -1, -1, self.stern_tip)):
            ctrl[pole] = tip
            ctrl[ghost, :, 0] = -q[ring, :, 0]
            ctrl[ghost, :, 1] = ys[ring]
            ctrl[ghost, :, 2] = 2.0 * tip[2] - q[ring, :, 1]
        sharp = np.concatenate([[0.0, 0.0], self.sharp, [0.0, 0.0]])[:, None, None]

        j1, j2 = NU, NU + 1
        flip = np.array([-1.0, 1.0, 1.0])
        lerp = lambda a, b, w: a * (1.0 - w) + b * w
        up = ctrl[:, :j1 + 1]
        fa = ctrl[:, j1:j2 + 1]
        lo = ctrl[:, j2:]
        self.patches = [
            np.concatenate([up[:, 1:2] * flip, up,
                            lerp(ctrl[:, j1 + 1:j1 + 2], 2.0 * up[:, -1:] - up[:, -2:-1], sharp)], axis=1),
            np.concatenate([lerp(ctrl[:, j1 - 1:j1], 2.0 * fa[:, :1] - fa[:, 1:], sharp), fa,
                            lerp(ctrl[:, j2 + 1:j2 + 2], 2.0 * fa[:, 1:] - fa[:, :1], sharp)], axis=1),
            np.concatenate([lerp(ctrl[:, j2 - 1:j2], 2.0 * lo[:, :1] - lo[:, 1:2], sharp), lo,
                            lo[:, -2:-1] * flip], axis=1),
        ]
        self.spans = [NU, 1, NL]
        self.bounds = [0.0, T1, T2, 1.0]
        self.s_max = float(n + 1)            # s = 0 is the nose pole, s = 1 + i is ring i, s_max the stern pole
        self.station_y = np.concatenate([[NOSE_TIP_Y], ys, [STERN_END_Y]])

    def eval(self, s, t, normals=False):
        """Points (..., 3) for parameter arrays s in [0, s_max] and t in [0, 1]."""
        s = np.clip(np.asarray(s, dtype=float), 0.0, self.s_max)
        t = np.clip(np.asarray(t, dtype=float), 0.0, 1.0)
        s, t = np.broadcast_arrays(s, t)
        out = np.zeros(s.shape + (3,))
        ds = np.zeros_like(out)
        dt = np.zeros_like(out)
        i0 = np.minimum(np.floor(s).astype(int), int(self.s_max) - 1)
        ws, wds = _cr_weights(s - i0)
        for patch, span, t0, t1 in zip(self.patches, self.spans, self.bounds[:-1], self.bounds[1:]):
            m = (t >= t0) & (t <= t1) if t1 == 1.0 else (t >= t0) & (t < t1)
            if not m.any():
                continue
            u = (t[m] - t0) / (t1 - t0) * span
            j0 = np.minimum(np.floor(u).astype(int), span - 1)
            wt, wdt = _cr_weights(u - j0)
            ii = i0[m][:, None] + np.arange(4)[None, :]
            jj = j0[:, None] + np.arange(4)[None, :]
            c = patch[ii[:, :, None], jj[:, None, :]]                 # (m, 4, 4, 3)
            out[m] = np.einsum("ma,mb,mabc->mc", ws[m], wt, c)
            if normals:
                ds[m] = np.einsum("ma,mb,mabc->mc", wds[m], wt, c)
                dt[m] = np.einsum("ma,mb,mabc->mc", ws[m], wdt, c) * (span / (t1 - t0))
        if not normals:
            return out
        nrm = np.cross(dt, ds)
        length = np.linalg.norm(nrm, axis=-1, keepdims=True)
        pole = length[..., 0] < 1e-9
        nrm = nrm / np.maximum(length, 1e-12)
        nrm[pole] = np.array([0.0, -1.0, 0.0])
        nrm[pole & (s > 0.5 * self.s_max)] = np.array([0.0, 1.0, 0.0])
        return out, nrm

    def s_of_y(self, y, t=0.25):
        """Station parameter whose section lies at the given y, on the parameter line t."""
        y = np.asarray(y, dtype=float)
        lo = np.zeros(y.shape)
        hi = np.full(y.shape, self.s_max)
        tt = np.broadcast_to(np.asarray(t, dtype=float), y.shape)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            below = self.eval(mid, tt)[..., 1] < y
            lo = np.where(below, mid, lo)
            hi = np.where(below, hi, mid)
        return 0.5 * (lo + hi)

    def t_of_z(self, s, z, upper=True):
        """Parameter t where the section at s crosses the height z, on the chosen skin."""
        s = np.asarray(s, dtype=float)
        z = np.broadcast_to(np.asarray(z, dtype=float), s.shape)
        lo = np.zeros(s.shape) if upper else np.full(s.shape, T2)
        hi = np.full(s.shape, T1) if upper else np.ones(s.shape)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            above = self.eval(s, mid)[..., 2] > z
            lo = np.where(above, mid, lo)
            hi = np.where(above, hi, mid)
        return 0.5 * (lo + hi)


def self_check():
    """The rebuilt surface must stay on the blueprint: print the deviation per zone."""
    hull = Hull()
    s = np.linspace(0.0, hull.s_max, 400)
    t = np.linspace(0.0, 1.0, 600)
    grid = hull.eval(s[:, None], t[None, :])
    assert np.isfinite(grid).all()
    worst = 0.0
    for i, y in enumerate(hull.blueprint_y):
        if y > STERN_START_Y:                # the stern is designed: it leaves the blueprint
            break
        ring = hull.eval(np.full(1500, 1.0 + i), np.linspace(0.0, 1.0, 1500))[:, [0, 2]]
        d = np.linalg.norm(hull.blueprint_pts[i][:, None, :] - ring[None, :, :], axis=2).min(axis=1)
        worst = max(worst, d.max())
        if d.max() > 0.02:
            print(f"ring {i:2d} y={y:+6.2f}  max {d.max() * 100:5.1f} cm at k={int(d.argmax())}")
    x = np.abs(grid[..., 0])
    print(f"worst blueprint deviation {worst * 100:.1f} cm; beam {2 * x.max():.3f} m; "
          f"y {grid[..., 1].min():.3f}..{grid[..., 1].max():.3f}; z {grid[..., 2].min():.3f}..{grid[..., 2].max():.3f}")
    _, nrm = hull.eval(s[1:, None], t[None, :], normals=True)
    centre = np.array([0.0, 0.0, -0.4])
    outward = (nrm * (grid[1:] - centre)).sum(axis=-1)
    print(f"normals pointing outward: {(outward > 0).mean() * 100:.1f} %")


if __name__ == "__main__":
    self_check()
