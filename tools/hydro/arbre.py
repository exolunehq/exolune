"""The 'arbre' variant of etude_relief.py: a drained hierarchical tree under the 20 km level 0, after Dendry's principle
(Gaillard et al. 2019, from the paper's principles only). CPU prototype; the engine is untouched.

- Frame: a fixed tangent plane at the site centre, gnomonic, in metres, x east, y north. Every lattice is anchored there.
- Level 0: the engine's level-0 links, built as erosion_valleys builds them (no turbulence warp), as polylines with stage.
- Levels k = 1..6, spacing S0 / 2^k: one jittered keypoint per cell, joined by a straight branch to the nearest point of
  the coarser tree within ATTACH s_k. Its altitude follows the no-erosion relief filtered at s_k, clamped so that every
  branch runs downhill and climbs slower than the wall it joins.
- Relief: smooth minimum of cones, stage + wall x distance, over the branches within 2 s_k of the point, each steepened
  beyond s_k so the cutoff leaves no step; the no-erosion detail below NOISE[0] fades in away from channels. Water: channels of physical width on levels 0 to 2.
- A window rebuilds its tree from the lattice within reach(k) of itself, the margin a per-point evaluation would need, so
  the same tree appears in every window size; the metric tree_vs_40km_m checks it.
"""
import numpy as np

import cp
from hydro import N8

# Every constant is a choice of this prototype.
S0, LEVELS = 20000.0, 6           # level-0 spacing (m); s_k = S0 / 2^k, 10 km down to 312 m
JITTER, ATTACH = 0.4, 2.0         # keypoint jitter (share of s_k); attach and height search radius (in s_k)
FLINT = (0.015, 0.45)             # channel slope at level 1, concavity: S_k = S_1 (s_k / s_1)^(-2 theta), area ~ s_k^2
SLOPE = (0.05, 4.0)               # a branch climbs between 0.05 S_k and 4 S_k
TRIB = 0.7                        # and never faster than 0.7 x the wall it joins, so it stays carved into that wall
LOWEST = False                    # attach to the nearest point (Dendry); True: to the lowest coarser cone (experiment)
WALL = (3.0, 0.08, 0.9, 1250.0, 625.0)  # wall = clip(3 |grad relief|, 0.08, 0.9) at the segment's middle; lattice (m),
                                        # relief filter cell (m)
RIM = 4.0                         # beyond s_k a level-k cone steepens by RIM (d - s_k)^2 / s_k: no step at the 2 s_k cutoff
ROUND = 0.5                       # smooth-min width = ROUND x wall x distance to the nearest branch: 0 in channels
NOISE = (100.0, 300.0)            # no-erosion detail of the cells below 100 m (wavelengths under 200-400 m), faded in over 300 m
RUNOFF = 1.6e-8                   # m/s, 0.5 m/yr: discharge of levels 1-2 = RUNOFF s_k^2
CURVE, WATER_LEVELS = 16, 3       # straight pieces per level-0 curve; levels drawn with water
X0, Y0, X1, Y1, Z0, Z1, Q0, Q1, LEV, CUR, WAL = range(11)  # segment columns: upstream end, downstream end, log2
                                                           # discharge, level, level-0 curve, wall slope


def spacing(k):
    return S0 / 2.0 ** k


def flint(k):
    return FLINT[0] * (spacing(k) / spacing(1)) ** (-2.0 * FLINT[1])


def reach(k):
    """Radius (m) within which level-k keypoints matter to a sample: their branch reaches its height search, or the
    attachment search of a finer keypoint that matters. Level 0: also its own height radius."""
    if k == 0:
        return max(reach(1) + ATTACH * spacing(1), ATTACH * S0)
    if k == LEVELS:
        return 2.0 * ATTACH * spacing(k)
    return reach(k + 1) + ATTACH * spacing(k + 1) + ATTACH * spacing(k)


class Frame:
    """The site's tangent plane, as cp.window builds its grid: window points map to exact grid coordinates."""

    def __init__(self, centre):
        c = centre / np.linalg.norm(centre)
        e = np.cross(c, [0.0, 1.0, 0.0])
        e /= np.linalg.norm(e)
        self.c, self.e, self.n = c, e, np.cross(e, c)

    def sphere(self, xy):
        p = self.c + (xy[:, :1] * self.e + xy[:, 1:] * self.n) / cp.R
        return p / np.linalg.norm(p, axis=1, keepdims=True)

    def plane(self, p):
        return cp.R * np.stack((p @ self.e, p @ self.n), 1) / (p @ self.c)[:, None]


class Wall:
    """Wall slope from the local relief amplitude: the no-erosion relief's gradient on a lattice anchored in the frame,
    central differences only, read bilinearly."""

    def __init__(self, frame, half):
        s = WALL[3]
        self.i0 = int(np.floor(-half / s)) - 1
        g = np.arange(self.i0, int(np.ceil(half / s)) + 2) * s
        x, y = np.meshgrid(g, g)
        z = cp.elevation(cp.Ctx(WALL[4]), frame.sphere(np.stack((x.ravel(), y.ravel()), 1)), valleys=False).reshape(x.shape)
        gy, gx = np.gradient(z, s)
        self.w = np.clip(WALL[0] * np.hypot(gx, gy), WALL[1], WALL[2])
        self.evaluations = z.size

    def __call__(self, xy):
        u = xy / WALL[3] - self.i0
        i = np.clip(np.floor(u).astype(int), 1, self.w.shape[0] - 3)
        f = u - i
        w = self.w
        top = w[i[:, 1], i[:, 0]] * (1 - f[:, 0]) + w[i[:, 1], i[:, 0] + 1] * f[:, 0]
        bottom = w[i[:, 1] + 1, i[:, 0]] * (1 - f[:, 0]) + w[i[:, 1] + 1, i[:, 0] + 1] * f[:, 0]
        return top * (1 - f[:, 1]) + bottom * f[:, 1]


def level0(frame, radius):
    """The level-0 curves within radius of the centre, as polylines: (segments, monotonicity violations, curves)."""
    words, n = cp.erosion_map()
    face, x = cp._elocate(frame.c[None], n)
    m = int(radius / (2.0 * cp.R / n)) + 3
    o = np.stack(np.meshgrid(np.arange(-m, m + 1), np.arange(-m, m + 1)), -1).reshape(-1, 2)
    r = np.unique(cp._ecell(np.repeat(face, len(o)), np.floor(x).astype(np.int64) + o, n))
    node = lambda c: frame.plane(cp._enode(c, n).astype(np.float64))
    lv, _, q, _, bits = cp._eread(words, r)
    b = node(r)
    outlet = (bits & (cp._SEA | cp._LAKE)) != 0
    down = ((bits & cp._HAS_RECEIVER) != 0) & ~outlet
    rr = cp._eneighbour(r, bits & 7, n)
    lv2, _, q2, _, _ = cp._eread(words, rr)
    end = np.where(down[:, None], 0.5 * (b + node(rr)), b)
    z_end, q_end = np.where(down, 0.5 * (lv + lv2), lv), np.where(down, np.sqrt(q * q2), q)
    inflows = (bits >> 4) & 255
    curves = []
    for k in range(9):
        sel = ((inflows >> k) & 1) == 1 if k < 8 else (inflows == 0) & ~outlet
        if not sel.any():
            continue
        if k < 8:
            u = cp._eneighbour(r[sel], np.full(sel.sum(), k), n)
            lu, _, qu, _, _ = cp._eread(words, u)
            a, za, qa = 0.5 * (node(u) + b[sel]), 0.5 * (lu + lv[sel]), np.sqrt(qu * q[sel])
        else:
            a, za, qa = b[sel], lv[sel], q[sel]
        curves.append((a, b[sel], end[sel], za, lv[sel], z_end[sel], qa, q[sel], q_end[sel]))
    a, b, c, za, zb, zc, qa, qb, qc = (np.concatenate(v) for v in zip(*curves))
    violations = int(np.sum((za < zb - 1e-6) | (zb < zc - 1e-6)))
    t = np.linspace(0.0, 1.0, CURVE + 1)[None, :]
    bez = lambda u, v, w: (1 - t) ** 2 * u + 2 * (1 - t) * t * v + t * t * w
    px, py = (bez(a[:, i:i + 1], b[:, i:i + 1], c[:, i:i + 1]) for i in (0, 1))
    z, lq = bez(za[:, None], zb[:, None], zc[:, None]), bez(*(np.log2(np.maximum(v, 1e-9))[:, None] for v in (qa, qb, qc)))
    curve = np.repeat(np.arange(len(a))[:, None], CURVE, 1)
    seg = np.stack([px[:, :-1], py[:, :-1], px[:, 1:], py[:, 1:], z[:, :-1], z[:, 1:], lq[:, :-1], lq[:, 1:],
                    np.zeros_like(curve), curve, np.zeros_like(px[:, 1:])], -1).reshape(-1, 11)
    return seg, violations, len(a)


def lattice(k, half):
    """Level k's keypoints in the cells covering [-half, half]^2: one per cell, jittered by a hash of (k, cell)."""
    s = spacing(k)
    i = np.arange(np.floor(-half / s), np.ceil(half / s)).astype(np.int64)
    I, J = (v.ravel() for v in np.meshgrid(i, i))
    h = cp._mix(((I * 0x8DA6B343 ^ J * 0xD8163841 ^ k * 0xCB1AB31F ^ cp.PLANET_SEED * 0x165667B1) & 0xFFFFFFFF).astype(np.uint32))
    j = np.stack((h & 0xFFFF, h >> 16), 1) / 65535.0 - 0.5
    return (np.stack((I, J), 1) + 0.5 + 2.0 * JITTER * j) * s


def distance(p, s):
    """Distance (m, C) from points p (m, 2) to segments s (C, 11), and the parameter of the nearest point."""
    ex, ey = s[:, X1] - s[:, X0], s[:, Y1] - s[:, Y0]
    dx, dy = p[:, :1] - s[:, X0], p[:, 1:] - s[:, Y0]
    t = np.clip((dx * ex + dy * ey) / np.maximum(ex * ex + ey * ey, 1e-12), 0.0, 1.0)
    return np.hypot(dx - t * ex, dy - t * ey), t


def blocks(p, seg, radius, size):
    """Points grouped in square blocks; per block, the segments whose box grown by radius (per segment) meets it, their
    distances, parameters, and which boxes hold each point (the tests a culled search makes)."""
    lo = np.minimum(seg[:, [X0, Y0]], seg[:, [X1, Y1]]) - radius[:, None]
    hi = np.maximum(seg[:, [X0, Y0]], seg[:, [X1, Y1]]) + radius[:, None]
    if not len(p):
        return
    key = np.floor(p / size).astype(np.int64)
    order = np.lexsort((key[:, 1], key[:, 0]))
    _, start = np.unique(key[order], axis=0, return_index=True)
    for idx in np.split(order, start[1:]):
        q = p[idx]
        c = np.flatnonzero(((lo <= q.max(0)) & (hi >= q.min(0))).all(1))
        d, t = distance(q, seg[c])
        held = ((lo[c][None] <= q[:, None]) & (hi[c][None] >= q[:, None])).all(2)
        yield idx, c, d, t, held


def tested(seg, c, held):
    """Per point: segment tests on levels >= 1, and distinct level-0 curves tested."""
    zero = seg[c, LEV] == 0
    ids = np.sort(np.where(held & zero, seg[c, CUR], -1.0), 1)
    curves = (ids[:, :1] >= 0).sum(1) + ((np.diff(ids, axis=1) != 0) & (ids[:, 1:] >= 0)).sum(1)
    return (held & ~zero).sum(1), curves


def build(frame, half):
    """The tree for a window of half-size half (m): segments (N, 11), the keypoints per level, and counters."""
    seg, violations, curves = level0(frame, half + reach(0))
    wall = Wall(frame, half + reach(1) + spacing(1))
    seg[:, WAL] = wall(0.5 * (seg[:, [X0, Y0]] + seg[:, [X1, Y1]]))
    stats = dict(level0_curves=curves, level0_uphill=violations, fallbacks=0, cap_conflicts=0, dropped_sea=0,
                 relief_evaluations=wall.evaluations)
    kps = []
    for k in range(1, LEVELS + 1):
        s, radius = spacing(k), ATTACH * spacing(k)
        P = P_all = lattice(k, half + reach(k))
        rel = cp.elevation(cp.Ctx(s), frame.sphere(P), valleys=False)
        stats["relief_evaluations"] += len(P)
        tests = np.zeros((len(P), 2), int)
        A, zA, L, cap = np.zeros((len(P), 2)), np.zeros(len(P)), np.full(len(P), np.inf), np.full(len(P), np.inf)
        wA = np.zeros(len(P))
        land = np.flatnonzero(rel > 0.0)
        stats["dropped_sea"] += len(P) - len(land)
        for idx, c, d, t, held in blocks(P[land], seg, np.full(len(seg), radius), 8.0 * s):
            tests[land[idx]] = np.stack(tested(seg, c, held), 1)
            d = np.where(d <= radius, d, np.inf)
            z = seg[c, Z0] + t * (seg[c, Z1] - seg[c, Z0])
            cone = z + TRIB * seg[c, WAL] * d  # the coarser surface a branch may not rise above
            j = (cone if LOWEST else d).argmin(1)
            row = np.arange(len(idx))
            g = land[idx]
            L[g], zA[g], wA[g], cap[g] = d[row, j], z[row, j], seg[c[j], WAL], cone.min(1)
            A[g] = seg[c[j], X0:Y0 + 1] + t[row, j, None] * (seg[c[j], X1:Y1 + 1] - seg[c[j], X0:Y0 + 1])
        # Nothing within reach: join level k-1's nearest anyway (or any coarser level's) and count it.
        far = land[~np.isfinite(L[land])]
        if len(far):
            pool = seg[seg[:, LEV] == k - 1] if (seg[:, LEV] == k - 1).any() else seg
            d, t = distance(P[far], pool)
            j, row = d.argmin(1), np.arange(len(far))
            L[far] = d[row, j]
            zA[far], wA[far] = pool[j, Z0] + t[row, j] * (pool[j, Z1] - pool[j, Z0]), pool[j, WAL]
            A[far] = pool[j, X0:Y0 + 1] + t[row, j, None] * (pool[j, X1:Y1 + 1] - pool[j, X0:Y0 + 1])
            stats["fallbacks"] += len(far)
        ok = np.isfinite(L) & (L > 1.0)
        P, A, zA, L, cap, rel, wA = P[ok], A[ok], zA[ok], L[ok], cap[ok], rel[ok], wA[ok]
        smin = SLOPE[0] * flint(k)
        smax = np.maximum(np.minimum(SLOPE[1] * flint(k), TRIB * wA), smin)
        zP = zA + np.clip((rel - zA) / L, smin, smax) * L
        stats["cap_conflicts"] += int(np.sum(cap < zA + smin * L))
        zP = np.maximum(np.minimum(zP, cap), zA + smin * L)
        lq = np.full(len(P), np.log2(RUNOFF * spacing(k) ** 2))
        new = np.stack([P[:, 0], P[:, 1], A[:, 0], A[:, 1], zP, zA, lq, lq, np.full(len(P), k), np.full(len(P), -1),
                        wall(0.5 * (P + A))], 1)
        seg = np.concatenate([seg, new])
        kps.append((P_all, tests))
    return dict(seg=seg, wall=wall, keypoints=kps, stats=stats)


def smin(a, b, k):
    h = np.clip(k - np.abs(a - b), 0.0, None) / np.maximum(k, 1e-9)
    return np.minimum(a, b) - h * h * k / 4.0


@np.errstate(invalid="ignore")  # inf - inf where no branch is in reach, masked
def surface(tree, xy, cell):
    """Tree relief G, distance to the nearest branch, channel bed and water level (inf where dry), tests per sample, and
    whether the lowest cone lies in its rim, beyond s_k from its branch."""
    seg, w = tree["seg"], tree["wall"](xy)
    radius = np.where(seg[:, LEV] == 0, ATTACH * S0, ATTACH * S0 / 2.0 ** seg[:, LEV])
    box = max(cell, cp.CREASE_MIN_CELL)
    N = len(xy)
    G, near, bed, level, rim = np.zeros(N), np.zeros(N), np.full(N, np.inf), np.full(N, np.inf), np.zeros(N, bool)
    tests = np.zeros((N, 2), int)
    for idx, c, d, t, held in blocks(xy, seg, radius, 32.0 * cell):
        tests[idx] = np.stack(tested(seg, c, held), 1)
        d = np.where(d <= radius[c], d, np.inf)
        z = seg[c, Z0] + t * (seg[c, Z1] - seg[c, Z0])
        r = radius[c]
        cone = z + seg[c, WAL] * d + RIM * np.maximum(d - 0.5 * r, 0.0) ** 2 / (0.5 * r)
        lowest = cone.argmin(1)
        rim[idx] = d[np.arange(len(idx)), lowest] > 0.5 * r[lowest]
        zero = seg[c, LEV] == 0
        vals = np.concatenate([np.where(zero, cone, np.inf).min(1, keepdims=True), cone[:, ~zero]], 1)
        if vals.shape[1] > 4:
            vals = np.partition(vals, 3, axis=1)[:, :4]
        vals = np.sort(vals, 1)
        near[idx] = d.min(1)
        k = ROUND * w[idx] * near[idx]
        g = vals[:, 0]
        for i in range(1, vals.shape[1]):
            g = np.where(np.isfinite(vals[:, i]), smin(g, vals[:, i], k), g)
        G[idx] = g
        reach_w = np.maximum(1.0, 2.4 * np.sqrt(2.0 ** np.maximum(seg[c, Q0], seg[c, Q1]))) + box
        i, j = np.nonzero((seg[c, LEV] < WATER_LEVELS)[None] & (d < reach_w[None]))
        q = 2.0 ** (seg[c[j], Q0] + t[i, j] * (seg[c[j], Q1] - seg[c[j], Q0]))
        cut = cp.erosion_river_cut(d[i, j], q, box)
        wet = cut > 0.0
        np.minimum.at(bed, idx[i[wet]], z[i, j][wet] - cut[wet])
        np.minimum.at(level, idx[i[wet]], z[i, j][wet])
    return G, near, bed, level, tests, rim


def d8_leaks(z, wet):
    """Wet cells, off the border, whose steepest D8 descent on z leaves the water for a dry cell."""
    n, m = z.shape
    zp, wp = np.pad(z, 1, constant_values=np.inf), np.pad(wet, 1)
    best, leak = np.zeros(z.shape), np.zeros(z.shape, bool)
    for di, dj in N8:
        s = (z - zp[1 + di:n + 1 + di, 1 + dj:m + 1 + dj]) / np.hypot(di, dj)
        better = s > best
        best, leak = np.where(better, s, best), np.where(better, ~wp[1 + di:n + 1 + di, 1 + dj:m + 1 + dj], leak)
    leak &= wet
    leak[[0, -1]], leak[:, [0, -1]] = False, False
    return leak


def channel_metrics(tree, z, water, sea, cell):
    """Drawn water length that is dry (gap or leak) on levels 0-2, and the share of level-0 cross-sections whose lowest
    point lies within one cell of the channel line."""
    n = z.shape[0]
    half = 0.5 * n * cell
    seg = tree["seg"]
    lo, hi = np.minimum(seg[:, [X0, Y0]], seg[:, [X1, Y1]]), np.maximum(seg[:, [X0, Y0]], seg[:, [X1, Y1]])
    seg = seg[(seg[:, LEV] < WATER_LEVELS) & (lo < half).all(1) & (hi > -half).all(1)]
    wet = water > 0.0
    bad = ~wet | d8_leaks(z, wet)
    length = np.hypot(seg[:, X1] - seg[:, X0], seg[:, Y1] - seg[:, Y0])
    m = np.maximum(np.ceil(length / (0.5 * cell)).astype(int), 1)
    rep = np.repeat(np.arange(len(seg)), m)
    u = (np.arange(len(rep)) - np.repeat(np.cumsum(m) - m, m) + 0.5) / m[rep]
    s = seg[rep]
    x, y = s[:, X0] + u * (s[:, X1] - s[:, X0]), s[:, Y0] + u * (s[:, Y1] - s[:, Y0])
    col, row = np.floor((x + half) / cell).astype(int), np.floor((half - y) / cell).astype(int)
    keep = (col >= 2) & (col < n - 2) & (row >= 2) & (row < n - 2)
    keep[keep] &= ~sea[row[keep], col[keep]]
    k0 = keep & (s[:, LEV] == 0)
    out = dict(water_length_km=float(np.sum(keep) * 0.5 * cell / 1000.0),
               dry_share=float(bad[row[keep], col[keep]].mean()) if keep.any() else None,
               dry_share_level0=float(bad[row[k0], col[k0]].mean()) if k0.any() else None)
    # Across level-0 channels: the lowest point of a +-4 cell transect, bilinear, every 4 cells along the line.
    pick = np.flatnonzero(k0 & (col >= 6) & (col < n - 6) & (row >= 6) & (row < n - 6))[::8]
    if len(pick):
        s = s[pick]
        e = np.stack((s[:, X1] - s[:, X0], s[:, Y1] - s[:, Y0]), 1)
        e /= np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-9)
        o = np.arange(-4, 5) * cell
        tx, ty = x[pick, None] - e[:, 1:] * o, y[pick, None] + e[:, :1] * o
        fc, fr = (tx + half) / cell - 0.5, (half - ty) / cell - 0.5
        c0, r0 = np.clip(np.floor(fc).astype(int), 0, n - 2), np.clip(np.floor(fr).astype(int), 0, n - 2)
        a, b = fc - c0, fr - r0
        h = (z[r0, c0] * (1 - a) + z[r0, c0 + 1] * a) * (1 - b) + (z[r0 + 1, c0] * (1 - a) + z[r0 + 1, c0 + 1] * a) * b
        out["level0_floor_on_line_share"] = float(np.mean(np.abs(o[h.argmin(1)]) <= cell))
    return out


def per_sample_cost(tree, xy, tests):
    """What a per-point evaluation of a sample would do: rebuild every keypoint within reach(k), each with a relief
    evaluation and its attachment tests, then the height tests. Mean over 16 samples spread over the window."""
    pick = np.random.default_rng(0).choice(len(xy), 16, replace=False)
    rows = []
    for x in xy[pick]:
        att, ev = np.zeros(2), 0
        for k, (P, t) in enumerate(tree["keypoints"], 1):
            inside = (np.abs(P - x) <= reach(k)).all(1)
            att += t[inside].sum(0)
            ev += inside.sum()
        rows.append((att[0], att[1], ev))
    att_seg, att_curves, evaluations = np.mean(rows, 0)
    h = tests[pick].mean(0)
    return dict(tests_attach_segments=float(att_seg), tests_attach_level0_curves=float(att_curves),
                tests_height_segments=float(h[0]), tests_height_level0_curves=float(h[1]),
                keypoints_relief_evaluations=float(evaluations))


_REFERENCE = {}


def relief(points, cell):
    """The variant: (height, water depth, extra metrics) for a cp.window grid."""
    n = int(round(np.sqrt(len(points))))
    frame = Frame(points.sum(0))
    half, xy = 0.5 * n * cell, frame.plane(points)
    tree = build(frame, half)
    G, near, bed, level, tests, rim = surface(tree, xy, cell)
    sans = cp.elevation(cp.Ctx(cell), points, extra=True, valleys=False)
    h0 = sans["elev"]
    noise = 0.0
    if cell < NOISE[0]:
        noise = (h0 - cp.elevation(cp.Ctx(NOISE[0]), points, valleys=False)) * cp._smooth(0.0, NOISE[1], near)
    h = np.minimum(G + noise, bed)
    sea = (sans["water_depth"] > 0.0) & (h0 < h)
    h = np.where(sea, h0, h)
    water = np.where(sea, sans["water_depth"], np.where(np.isfinite(level), np.maximum(level - h, 0.0), 0.0))
    extra = dict(tree.get("stats"), segments=int(len(tree["seg"])), rim_share=float(rim.mean()))
    extra.update(channel_metrics(tree, h.reshape(n, n), water.reshape(n, n), sea.reshape(n, n), cell))
    extra.update(per_sample_cost(tree, xy, tests))
    key = tuple(np.round(frame.c, 12))
    if half >= 20000.0 - 1e-6:
        _REFERENCE[key] = tree
    else:
        if key not in _REFERENCE:
            _REFERENCE[key] = build(frame, 20000.0)
        extra["tree_vs_40km_m"] = float(np.abs(G - surface(_REFERENCE[key], xy, cell)[0]).max())
    return h, water, extra


if __name__ == "__main__":
    # Every branch runs downhill; a small window's own tree gives the same relief as a larger window's tree.
    from verifie_lames import direction
    frame = Frame(direction(-7.138614, 122.604860))
    small, large = build(frame, 300.0), build(frame, 1250.0)
    assert np.all(large["seg"][large["seg"][:, LEV] > 0, Z0] >= large["seg"][large["seg"][:, LEV] > 0, Z1])
    xy = frame.plane(cp.window(frame.c, 600.0, 32))
    a, b = surface(small, xy, 600.0 / 32)[0], surface(large, xy, 600.0 / 32)[0]
    assert np.abs(a - b).max() < 1e-6, np.abs(a - b).max()
    print("ok", small["stats"])
