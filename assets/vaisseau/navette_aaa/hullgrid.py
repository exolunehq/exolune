"""Structured quad grid of the half hull, conformed to its openings.

One grid of nodes (a along the length, b around the half section) covers the whole skin.
Feature outlines (canopy, thruster mouth, shoulder, belt, gear well, hatch) pin nodes on index
lines; a harmonic fill places every other node. Openings are then index rectangles: no boolean,
quads only.

Design curves are given in side view (y, z) on the upper skin, in (y, d) on the lower skin, d
being the distance along the section below the shoulder edge E2, and in (y, x) on the belly.
Only numpy is needed.
"""
import numpy as np

from surface import Hull, T1, T2, blueprint_y, nose_y, smoothstep

# ---- index layout ---------------------------------------------------------------------------
B_ROOF, B_SILL = 7, 31                    # window top and sill rows
B_E1, B_E2 = 36, 39                       # shoulder edges; one bevel row on each side of both
B_CAV0 = 42                               # thruster mouth, upper lip row
BLADES = 4                                # blades of the mouth: 1 cell each, 2 cells per gap
B_CAV1 = B_CAV0 + 2 * (BLADES + 1) + BLADES
B_BELT0, B_BELT1 = B_CAV1 + 2, B_CAV1 + 5
B_MAX = 84
B_WELL = B_MAX - 8                        # side edge of the openings cut across the keel, inboard edge of the main wells
B_MAIN_OUT, B_MAIN_MID = B_WELL - 10, B_WELL - 5    # main wells: outboard edge, and the split between their doors

# ---- design, metres -------------------------------------------------------------------------
BEVEL = 0.012                             # half width of the rounded shoulder edges
RIM = 0.10                                # least width of the hull rim under the glass, along the skin
ARCH_Y, ARCH_RAKE, CROWN_Z = -3.60, 0.10, 0.74
MULLION_Y, MULLION_RAKE = (-2.72, -1.93, -1.17), 0.06
WIN_TOP_Y0, WIN_TOP_Z0, WIN_TOP_DROP, WIN_TOP_POW = -3.61, 0.66, 0.39, 1.15
WIN_REAR_TOP_Y, WIN_REAR_TIP_Y = -0.45, -0.85
R_TIP, R_TOP_REAR, R_ROOF = 0.045, 0.20, 0.06
CAV_D0, CAV_GAP, CAV_BLADE = 0.085, 0.105, 0.022     # lip depth below E2, gap and blade widths
CAV_Y = (1.82, 2.08, 3.52, 3.22)          # front-bottom, front-top, rear-top, rear-bottom
R_CAV = 0.07
BELT_WIDTH = 0.16                         # width of the teal belt along the skin
PROW_KEEL_Y = float(nose_y(-4.75))       # where the nose glazing ends on the keel: the hull's prow
PROW_BAND = 0.20                          # width on the keel of the teal band behind the glazing
NOSE_WELL_Y, NOSE_WELL_SPLIT = (-4.36, -2.36), -3.29   # nose gear well: front and aft doors, one leaf per side
NOSE_WELL_HALF, R_WELL = 0.37, 0.06
MAIN_WELL_Y, MAIN_WELL_SPLIT = (0.60, 2.55), 1.40      # main gear wells, one each side: front and aft doors
MAIN_WELL_X = (0.68, 1.52)                             # their inboard and outboard edges on the belly
MAIN_WELL_X_SPLIT = 1.10                               # where their outer and inner doors meet
HATCH_Y, HATCH_HALF, R_HATCH = (3.50, 6.05), 0.45, 0.08  # ventral rear hatch, hinged on its front edge
BELT_KEYS = ((float(nose_y(-5.4)), -1.36), (float(nose_y(-4.6)), -1.33), (-2.0, -1.24), (0.0, -1.16), (1.9, -1.085), (2.7, -1.06),
             (3.3, -0.88), (3.9, -0.68), (5.0, -0.59), (6.7, -0.50))    # belt top in side view: (y, z)


def smootherstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def z_sill(y):
    """Lower edge of the glazing in side view: nose lip, rise behind the cheek, then a gentle climb.

    Drawn on the validated form's stations, so it follows the shortened nose.
    """
    y = blueprint_y(y)
    u = np.clip((y + 3.9) / 0.9, 0.0, 1.0)
    ramp = 0.9 * (u ** 3 - 0.5 * u ** 4) + np.maximum(y + 3.0, 0.0)
    return -1.18 + 0.46 * smootherstep(-5.04, -3.46, y) + 0.118 * ramp


def z_belt(y):
    """Upper edge of the teal belt in side view: the keys joined by a smooth curve."""
    ky, kz = np.array(BELT_KEYS).T
    dense = np.linspace(ky[0], ky[-1], 1200)
    line = np.interp(dense, ky, kz)
    kernel = np.exp(-0.5 * (np.arange(-90, 91) / 30.0) ** 2)
    line = np.convolve(np.pad(line, 90, mode="edge"), kernel / kernel.sum(), mode="valid")
    return np.interp(y, dense, line)


def z_window_top(y):
    u = np.clip((np.asarray(y, dtype=float) - WIN_TOP_Y0) / (WIN_REAR_TOP_Y - WIN_TOP_Y0), 0.0, 1.0)
    return WIN_TOP_Z0 - WIN_TOP_DROP * u ** WIN_TOP_POW


def arclen(p):
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])


def at_arclen(p, pos):
    a = arclen(p)
    return np.stack([np.interp(pos, a, p[:, k]) for k in range(p.shape[1])], axis=-1)


def fillet(before, after, r, n=24):
    """Join two polylines meeting at a corner by an arc of radius r.

    before ends and after starts at the corner. Returns (polyline, arc length at the arc's middle).
    """
    la, lb = arclen(before), arclen(after)
    u_in = before[-1] - at_arclen(before, la[-1] - min(r, la[-1] * 0.5))
    u_out = at_arclen(after, min(r, lb[-1] * 0.5)) - after[0]
    u_in, u_out = u_in / np.linalg.norm(u_in), u_out / np.linalg.norm(u_out)
    turn = np.arccos(np.clip(np.dot(u_in, u_out), -1.0, 1.0))
    d = r * np.tan(0.5 * turn)
    a = at_arclen(before, la[-1] - d)
    b = at_arclen(after, d)
    side = np.sign(u_in[0] * u_out[1] - u_in[1] * u_out[0])
    centre = a + r * side * np.array([-u_in[1], u_in[0]])
    start = np.arctan2(a[1] - centre[1], a[0] - centre[0])
    phi = start + side * np.linspace(0.0, turn, n)
    arc = centre + r * np.stack([np.cos(phi), np.sin(phi)], axis=1)
    arc += (b - arc[-1]) * np.linspace(0.0, 1.0, n)[:, None]       # close the small tangent mismatch
    head = before[la < la[-1] - d]
    tail = after[lb > d]
    line = np.vstack([head, arc, tail])
    return line, float(arclen(np.vstack([head, arc[:n // 2 + 1]]))[-1])


def graded(n, tight_start=1.0, tight_end=1.0):
    """n + 1 fractions from 0 to 1; cells shrink to the given ratio of the mean towards each end."""
    k = np.arange(n)
    w = 1.0 + (tight_start - 1.0) * np.exp(-k / 2.2) + (tight_end - 1.0) * np.exp(-(n - 1 - k) / 2.2)
    return np.concatenate([[0.0], np.cumsum(w) / w.sum()])


def solve(u, fixed, sweeps=6000, omega=1.9, tol=2e-7, along=1.0):
    """Harmonic fill by red-black over-relaxation. Fixed nodes keep their value; borders are free.

    along < 1 weakens the coupling between columns: rows then follow their neighbours above and
    below first, which keeps them ordered where two held rows come close.
    """
    u = u.copy()
    ii, jj = np.indices(u.shape)
    colours = [~fixed & ((ii + jj) % 2 == c) for c in (0, 1)]
    for k in range(sweeps):
        change = 0.0
        for m in colours:
            p = np.pad(u, 1, mode="edge")
            mean = (along * (p[:-2, 1:-1] + p[2:, 1:-1]) + p[1:-1, :-2] + p[1:-1, 2:]) / (2.0 + 2.0 * along)
            delta = omega * (mean[m] - u[m])
            u[m] += delta
            change = max(change, float(np.abs(delta).max()) if delta.size else 0.0)
        if change < tol:
            break
    return u


class Maps:
    """Tables along the length: y, the length along the beam line, the three girths."""

    def __init__(self, hull, n=1600):
        self.hull = hull
        self.s = np.linspace(0.0, hull.s_max, n)
        beam = hull.eval(self.s, T1)
        self.y = beam[:, 1]
        self.lam = arclen(beam)
        tu, tf, tl = np.linspace(0, T1, 160), np.linspace(T1, T2, 8), np.linspace(T2, 1, 200)
        girth = lambda t: np.linalg.norm(np.diff(hull.eval(self.s[:, None], t[None, :]), axis=1), axis=2).sum(axis=1)
        self.gu, self.gf, self.gl = girth(tu), girth(tf), girth(tl)

    def s_of_y(self, y):
        return np.interp(y, self.y, self.s)

    def lam_of_s(self, s):
        return np.interp(s, self.s, self.lam)

    def s_of_lam(self, lam):
        return np.interp(lam, self.lam, self.s)

    def at(self, table, s):
        return np.interp(s, self.s, table)

    def upper(self, yz):
        """(lam, t) of side-view points on the upper skin."""
        s = self.s_of_y(yz[:, 0])
        return self.lam_of_s(s), self.hull.t_of_z(s, yz[:, 1], upper=True)

    def lower(self, yd):
        """(lam, t) of points given by y and the distance d below the shoulder edge E2."""
        s = self.s_of_y(yd[:, 0])
        return self.lam_of_s(s), T2 + yd[:, 1] / self.at(self.gl, s) * (1.0 - T2)

    def belly(self, yx):
        """(lam, t) of points of the lower skin given by y and their distance x from the centreline."""
        s = self.s_of_y(yx[:, 0])
        lo, hi = np.full(s.shape, T2), np.ones(s.shape)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            wide = self.hull.eval(s, mid)[:, 0] > yx[:, 1]
            lo, hi = np.where(wide, mid, lo), np.where(wide, hi, mid)
        return self.lam_of_s(s), 0.5 * (lo + hi)


def canopy_outline():
    """Side-view outline of the side glazing aft of the arch, with rounded corners.

    Returns the pieces between corner middles: sill, rear edge, top edge, arch up to the crown.
    """
    arch = lambda z: ARCH_Y - ARCH_RAKE * (CROWN_Z - z)
    y_sill0 = -3.75
    for _ in range(20):                                    # the arch foot on the sill
        y_sill0 = float(arch(z_sill(y_sill0)))
    ys = np.linspace(y_sill0, WIN_REAR_TIP_Y, 900)
    sill = np.stack([ys, z_sill(ys)], axis=1)
    tip = sill[-1]
    top_rear = np.array([WIN_REAR_TOP_Y, float(z_window_top(WIN_REAR_TOP_Y))])
    rear = tip + (top_rear - tip) * np.linspace(0.0, 1.0, 400)[:, None]
    yt = np.linspace(WIN_REAR_TOP_Y, WIN_TOP_Y0, 900)
    top = np.stack([yt, z_window_top(yt)], axis=1)
    zc = np.linspace(WIN_TOP_Z0, CROWN_Z, 60)
    up = np.stack([arch(zc), zc], axis=1)
    top[-1] = up[0]

    line, s_tip = fillet(sill, rear, R_TIP)
    n_head = len(line)
    line2, s_tr = fillet(line, top, R_TOP_REAR)
    line3, s_roof = fillet(line2, up, R_ROOF)
    a = arclen(line3)
    cut = lambda s0, s1: at_arclen(line3, np.linspace(s0, s1, 600))
    return {"sill": cut(0.0, s_tip), "rear": cut(s_tip, s_tr), "top": cut(s_tr, s_roof),
            "arch_top": cut(s_roof, a[-1]),
            "mullion": [lambda z, y0=y0: y0 - MULLION_RAKE * (CROWN_Z - z) for y0 in MULLION_Y],
            "arch": arch}


def keel_opening(y0, y1, half, r):
    """Port half of a rounded rectangle centred on the keel, in the belly chart (y, x).

    Returns its three pieces between corner middles: front edge from the keel out, side edge
    running aft, rear edge back to the keel.
    """
    front = np.stack([np.full(200, y0), np.linspace(0.0, half, 200)], axis=1)
    side = np.stack([np.linspace(y0, y1, 600), np.full(600, half)], axis=1)
    rear = np.stack([np.full(200, y1), np.linspace(half, 0.0, 200)], axis=1)
    line, s0 = fillet(front, side, r)
    line, s1 = fillet(line, rear, r)
    cut = lambda a, b: at_arclen(line, np.linspace(a, b, 400))
    return {"front": cut(0.0, s0), "side": cut(s0, s1), "rear": cut(s1, arclen(line)[-1])}


def rounded_loop(corners, r, n=40):
    """Sides of a closed polygon with rounded corners, each from one corner's middle to the next.

    Side k leaves the middle of corner k and reaches the middle of corner k + 1.
    """
    c = np.asarray(corners, dtype=float)
    k_n = len(c)
    arcs = []
    for k in range(k_n):
        u_in = c[k] - c[k - 1]
        u_out = c[(k + 1) % k_n] - c[k]
        u_in, u_out = u_in / np.linalg.norm(u_in), u_out / np.linalg.norm(u_out)
        turn = np.arccos(np.clip(np.dot(u_in, u_out), -1.0, 1.0))
        side = np.sign(u_in[0] * u_out[1] - u_in[1] * u_out[0])
        start_pt = c[k] - u_in * r * np.tan(0.5 * turn)
        centre = start_pt + r * side * np.array([-u_in[1], u_in[0]])
        phi = np.arctan2(start_pt[1] - centre[1], start_pt[0] - centre[0]) + side * np.linspace(0.0, turn, 2 * n + 1)
        arcs.append(centre + r * np.stack([np.cos(phi), np.sin(phi)], axis=1))
    return [np.vstack([arcs[k][n:], arcs[(k + 1) % k_n][:n + 1]]) for k in range(k_n)]


class HullGrid:
    def __init__(self, hull=None):
        self.hull = hull or Hull()
        m = self.maps = Maps(self.hull)
        cav_d1 = CAV_D0 + (BLADES + 1) * CAV_GAP + BLADES * CAV_BLADE
        self.cav_d = (CAV_D0, cav_d1)

        # ---- columns: feature stations and the number of cells between them ------------------
        can = canopy_outline()
        lam_y = lambda y: float(m.lam_of_s(m.s_of_y(y)))
        # The prow drags the columns behind the arch forward on the keel: the band column p2 and the
        # well columns w0, ws, w1 are counted in cells, and placed by their pins on the lower skin.
        marks = [("cap", 0.045), ("nose", lam_y(float(nose_y(-6.20)))), ("arch", lam_y(can["sill"][0, 0])),
                 ("p2", None), ("w0", None), ("ws", None),
                 ("m1", lam_y(MULLION_Y[0] - 0.08)), ("w1", None), ("m2", lam_y(MULLION_Y[1] - 0.08)),
                 ("m3", lam_y(MULLION_Y[2] - 0.08)), ("end", lam_y(-0.66)),
                 ("g0", lam_y(MAIN_WELL_Y[0])), ("gs", lam_y(MAIN_WELL_SPLIT)),
                 ("c0", lam_y(0.5 * (CAV_Y[0] + CAV_Y[1]))), ("g1", lam_y(MAIN_WELL_Y[1])),
                 ("c1", lam_y(0.5 * (CAV_Y[2] + CAV_Y[3]))),
                 ("h0", lam_y(HATCH_Y[0])), ("h1", lam_y(HATCH_Y[1])),
                 ("stern", float(m.lam[-1]) - 0.045)]
        size = {"cap": 0.032, "nose": 0.062, "m3": 0.045, "c0": 0.058, "g1": 0.058}
        cells_after = {"arch": 3, "p2": 2, "w0": 18, "ws": 6, "m1": 8, "w1": 5}
        known = [(k, lam0) for k, (_, lam0) in enumerate(marks) if lam0 is not None]
        for (k0, lam0), (k1, lam1) in zip(known[:-1], known[1:]):       # counted columns: spread between their neighbours
            if k1 == k0 + 1:
                continue
            count = np.cumsum([0] + [cells_after[marks[k][0]] for k in range(k0, k1)])
            for k in range(k0 + 1, k1):
                marks[k] = (marks[k][0], lam0 + (lam1 - lam0) * count[k - k0] / count[-1])
        col, lam_default, a, step = {}, [], 0, 0.065
        for (name, lam0), (_, lam1) in zip(marks[:-1], marks[1:]):
            step = size.get(name, 0.064)
            n = cells_after.get(name) or max(2, int(round((lam1 - lam0) / step)))
            col[name] = a
            lam_default.extend(np.linspace(lam0, lam1, n, endpoint=False))
            a += n
        col["stern"] = a
        lam_default.append(marks[-1][1])
        self.col = col
        na, nb = a + 1, B_MAX + 1
        lam = np.repeat(np.array(lam_default)[:, None], nb, axis=1)
        t = np.zeros((na, nb))
        fix_l = np.zeros((na, nb), dtype=bool)
        fix_t = np.zeros((na, nb), dtype=bool)
        fix_l[0], fix_l[-1], fix_l[col["nose"]] = True, True, True

        def pin(a_idx, b_idx, lam_v, t_v):
            lam[a_idx, b_idx], t[a_idx, b_idx] = lam_v, t_v
            fix_l[a_idx, b_idx] = fix_t[a_idx, b_idx] = True

        def pin_lam(a_idx, b_idx, lam_v):
            """Hold a node's station only: its place round the section stays with the row laws."""
            lam[a_idx, b_idx] = lam_v
            fix_l[a_idx, b_idx] = True

        def spread(line, to_lt, n, tight):
            """n + 1 nodes along a design line, spaced by true length on the skin."""
            dense = at_arclen(line, np.linspace(0.0, arclen(line)[-1], 800))
            lam_d, t_d = to_lt(dense)
            length = arclen(self.hull.eval(m.s_of_lam(lam_d), t_d))
            pos = graded(n, *tight) * length[-1]
            return np.interp(pos, length, lam_d), np.interp(pos, length, t_d)

        def pin_row(b, a0, a1, line, to_lt, tight=(1.0, 1.0)):
            pin(np.arange(a0, a1 + 1), b, *spread(line, to_lt, a1 - a0, tight))

        def pin_col(a_idx, b0, b1, line, to_lt, tight=(1.0, 1.0)):
            pin(a_idx, np.arange(b0, b1 + 1), *spread(line, to_lt, b1 - b0, tight))

        # ---- canopy: sill and top edge split at the mullions, raked rear edge, arch --------
        def split(line, y_marks):
            """Cut a side-view line at the mullion crossings (the line runs fore to aft)."""
            cuts = [0]
            for f in y_marks:
                cuts.append(int(np.argmin(np.abs(line[:, 0] - f(line[:, 1])))))
            cuts.append(len(line) - 1)
            return [line[c0:c1 + 1] for c0, c1 in zip(cuts[:-1], cuts[1:])]

        stations = [col["arch"], col["m1"], col["m2"], col["m3"], col["end"]]
        for b, line, corner in ((B_SILL, can["sill"], 0.45), (B_ROOF, can["top"][::-1], 0.6)):
            parts = split(line, can["mullion"])
            for k, part in enumerate(parts):
                tight = (0.5 if (k == 0 and b == B_ROOF) else 1.0, corner if k == len(parts) - 1 else 1.0)
                pin_row(b, stations[k], stations[k + 1], part, m.upper, tight)
        pin_col(col["end"], B_ROOF, B_SILL, can["rear"][::-1], m.upper, (0.5, 0.45))
        # The roof's front edge climbs the arch to the centreline: cut it where it reaches the crown.
        up = can["arch_top"]
        crown = up[-1] + (up[-1] - up[-2]) / np.linalg.norm(up[-1] - up[-2]) * np.linspace(0.0, 0.6, 400)[:, None]
        up = np.vstack([up, crown[1:]])
        t_up = m.upper(up)[1]
        up = up[:int(np.argmax(t_up < 1e-4)) + 1]
        pin_col(col["arch"], 0, B_ROOF, up[::-1], m.upper, (1.0, 0.5))
        for name, f in zip(("arch", "m1", "m2", "m3"), [can["arch"]] + can["mullion"]):
            # a raked straight post from the top edge down to the sill
            zs = np.linspace(1.0, -1.2, 4000)
            post = np.stack([f(zs), zs], axis=1)
            z_hi = can["top"][-1, 1] if name == "arch" else z_window_top(post[:, 0])
            post = post[(post[:, 1] < z_hi - 1e-4) & (post[:, 1] > z_sill(post[:, 0]) + 1e-4)]
            lam_p, t_p = spread(post, m.upper, B_SILL - B_ROOF, (1.0, 1.0))
            pin(col[name], np.arange(B_ROOF + 1, B_SILL), lam_p[1:-1], t_p[1:-1])

        # ---- thruster mouth and its painted frame, in (y, d) under the shoulder ----------------
        d0, d1 = self.cav_d
        self.mouth = rounded_loop([(CAV_Y[0], d1), (CAV_Y[3], d1), (CAV_Y[2], d0), (CAV_Y[1], d0)], R_CAV)
        bottom, rear, top, front = self.mouth
        c0, c1 = col["c0"], col["c1"]
        pin_row(B_CAV1, c0, c1, bottom, m.lower, (0.5, 0.5))
        pin_row(B_CAV0, c0, c1, top[::-1], m.lower, (0.5, 0.5))
        rows, depth = [B_CAV0], [d0]
        for k in range(BLADES):
            rows += [rows[-1] + 2, rows[-1] + 3]
            depth += [depth[-1] + CAV_GAP, depth[-1] + CAV_GAP + CAV_BLADE]
        rows.append(B_CAV1)
        depth.append(d1)
        self.blade_rows = [(rows[1 + 2 * k], rows[2 + 2 * k]) for k in range(BLADES)]
        for a_idx, line in ((c0, front), (c1, rear)):
            # the side of the mouth, cut at the blade edges so that each blade lands on its rows
            order = np.argsort(line[:, 1])
            d_lo, d_hi = line[order[0], 1], line[order[-1], 1]
            for ra, rb, da, db in zip(rows[:-1], rows[1:], depth[:-1], depth[1:]):
                dd = np.clip(np.linspace(da, db, rb - ra + 1), d_lo, d_hi)
                seg = np.stack([np.interp(dd, line[order, 1], line[order, 0]), dd], axis=1)
                inner = slice(1, None) if ra == B_CAV0 else slice(None)
                inner = slice(inner.start, -1) if rb == B_CAV1 else inner
                lam_s, t_s = m.lower(seg)
                pin(a_idx, np.arange(ra, rb + 1)[inner], lam_s[inner], t_s[inner])
        self.col_bezel = (c0 - 2, c1 + 2)

        # ---- openings across the keel, in (y, x) on the belly: nose gear well, rear hatch ------
        well = keel_opening(*NOSE_WELL_Y, NOSE_WELL_HALF, R_WELL)
        k_split = int(np.argmin(np.abs(well["side"][:, 0] - NOSE_WELL_SPLIT)))
        well["side"][k_split, 0] = NOSE_WELL_SPLIT
        split = np.stack([np.full(60, NOSE_WELL_SPLIT), np.linspace(NOSE_WELL_HALF, 0.0, 60)], axis=1)
        pin_col(col["w0"], B_WELL, B_MAX, well["front"][::-1], m.belly, (0.35, 1.0))
        pin_row(B_WELL, col["w0"], col["ws"], well["side"][:k_split + 1], m.belly, (0.35, 1.0))
        pin_col(col["ws"], B_WELL, B_MAX, split, m.belly)
        pin_row(B_WELL, col["ws"], col["w1"], well["side"][k_split:], m.belly, (1.0, 0.35))
        pin_col(col["w1"], B_WELL, B_MAX, well["rear"], m.belly, (0.35, 1.0))
        hatch = keel_opening(*HATCH_Y, HATCH_HALF, R_HATCH)
        pin_col(col["h0"], B_WELL, B_MAX, hatch["front"][::-1], m.belly, (0.35, 1.0))

        # ---- main gear wells, off the keel: a rounded rectangle split fore and aft, and in and out ----
        (y0, y1), (x_in, x_out) = MAIN_WELL_Y, MAIN_WELL_X
        outer, rear, inner, front = rounded_loop([(y0, x_out), (y1, x_out), (y1, x_in), (y0, x_in)], R_WELL)
        g0, gs, g1 = col["g0"], col["gs"], col["g1"]
        cut = lambda line: int(np.argmin(np.abs(line[:, 0] - MAIN_WELL_SPLIT)))
        inner = inner[::-1]                                          # both long edges run aft
        for b, line in ((B_MAIN_OUT, outer), (B_WELL, inner)):
            k = cut(line)
            line[k, 0] = MAIN_WELL_SPLIT
            pin_row(b, g0, gs, line[:k + 1], m.belly, (0.35, 1.0))
            pin_row(b, gs, g1, line[k:], m.belly, (1.0, 0.35))
        pin_col(g0, B_MAIN_OUT, B_WELL, front[::-1], m.belly, (0.35, 0.35))
        pin_col(g1, B_MAIN_OUT, B_WELL, rear, m.belly, (0.35, 0.35))
        across = np.stack([np.full(60, MAIN_WELL_SPLIT), np.linspace(x_out, x_in, 60)], axis=1)
        lam_c, t_c = spread(across, m.belly, B_WELL - B_MAIN_OUT, (1.0, 1.0))
        pin(gs, np.arange(B_MAIN_OUT + 1, B_WELL), lam_c[1:-1], t_c[1:-1])
        x_mid = MAIN_WELL_X_SPLIT
        along = np.stack([np.linspace(y0, y1, 400), np.full(400, x_mid)], axis=1)
        for a0, a1, piece in ((g0, gs, along[along[:, 0] <= MAIN_WELL_SPLIT]), (gs, g1, along[along[:, 0] >= MAIN_WELL_SPLIT])):
            lam_r, t_r = spread(piece, m.belly, a1 - a0, (1.0, 1.0))
            pin(np.arange(a0 + 1, a1), B_MAIN_MID, lam_r[1:-1], t_r[1:-1])
        pin_row(B_WELL, col["h0"], col["h1"], hatch["side"], m.belly, (0.35, 0.35))
        pin_col(col["h1"], B_WELL, B_MAX, hatch["rear"], m.belly, (0.35, 1.0))

        # ---- rows held along the whole length ------------------------------------------------
        s_def = m.s_of_lam(lam[:, 0])
        self._row_laws = []

        def hold(b, law, a0=0, a1=na - 1):
            self._row_laws.append((b, law, a0, a1))

        def sill_t(s):
            """Glass edge: a rim of constant width above E1 round the nose, the side-view law aft.

            Aft, the law never comes closer to E1 than the rim.
            """
            gu, y = m.at(m.gu, s), m.at(m.y, s)
            t_rim = T1 * (1.0 - np.minimum(RIM, 0.28 * gu) / gu)
            t_law = self.hull.t_of_z(s, z_sill(y))
            t_aft = 0.5 * (t_law + t_rim - np.sqrt((t_law - t_rim) ** 2 + 0.012 ** 2))
            w = smoothstep(*nose_y([-5.3, -4.3]), y)
            return (1.0 - w) * t_rim + w * t_aft

        hold(B_SILL, sill_t, 0, col["arch"] - 1)
        bevel_l = lambda s: BEVEL * self.hull_sharp(s) + (1 - self.hull_sharp(s)) * m.at(m.gl, s) / (B_MAX - B_E2)
        face = lambda s: np.minimum(BEVEL * self.hull_sharp(s) + (1 - self.hull_sharp(s)) * m.at(m.gf, s) / 3,
                                    m.at(m.gf, s) / 3)

        def e1_bevel(s):
            """Bevel row above E1; under the glass it shares the rim evenly with the rows above it."""
            gu = m.at(m.gu, s)
            width = BEVEL * self.hull_sharp(s) + (1 - self.hull_sharp(s)) * gu / B_E1
            rim = (T1 - np.minimum(sill_t(s), T1)) * gu / T1 / (B_E1 - B_SILL)
            return T1 - np.minimum(width, np.where(m.at(m.y, s) < -0.9, rim, width)) / gu * T1

        hold(B_E1 - 1, e1_bevel)
        hold(B_E1, lambda s: np.full(np.shape(s), T1))
        hold(B_E1 + 1, lambda s: T1 + face(s) / m.at(m.gf, s) * (T2 - T1))
        hold(B_E2 - 1, lambda s: T2 - face(s) / m.at(m.gf, s) * (T2 - T1))
        hold(B_E2, lambda s: np.full(np.shape(s), T2))
        hold(B_E2 + 1, lambda s: T2 + bevel_l(s) / m.at(m.gl, s) * (1 - T2))

        def belt(width, share):
            """Belt line: a share of the girth round the nose, a side-view height along the body,
            then a constant share of the girth along the tail, whose underside is too flat for heights.

            The rows between E2 and the belt keep at least 17 mm each.
            """
            def side(s):
                gl = m.at(m.gl, s)
                t_law = self.hull.t_of_z(s, z_belt(m.at(m.y, s)), upper=False)
                t_min = T2 + (B_BELT0 - B_E2) * 0.017 / gl * (1.0 - T2)
                t_top = 0.5 * (t_law + t_min + np.sqrt((t_law - t_min) ** 2 + 0.004 ** 2))
                return t_top + width / gl * (1.0 - T2)

            tail = float(side(m.s_of_y(np.array([4.6]))[0]))

            def law(s):
                y = m.at(m.y, s)
                w_nose, w_tail = smoothstep(*nose_y([-5.3, -4.4]), y), smoothstep(4.6, 5.6, y)
                body = (1.0 - w_tail) * side(s) + w_tail * tail
                return (1.0 - w_nose) * (T2 + share * (1.0 - T2)) + w_nose * body
            return law

        hold(B_BELT0, belt(0.0, (B_BELT0 - B_E2) / (B_MAX - B_E2)))
        hold(B_BELT1, belt(BELT_WIDTH, (B_BELT1 - B_E2) / (B_MAX - B_E2)))

        # ---- prow: the nose glazing ends on the arch column, swept forward down to the keel ----
        # Below the sill the column holds its stations only. Each node's place round the section is
        # taken from the row laws, and gives its share w of the girth from the sill to the keel.
        knots = [B_SILL] + [b for b, _, a0, _ in self._row_laws if a0 == 0 and b != B_SILL] + [B_MAX]
        laws = {b: law for b, law, a0, _ in self._row_laws if a0 == 0}
        laws[B_MAX] = lambda s: np.ones(np.shape(s))
        rows = np.arange(B_SILL + 1, B_MAX + 1)
        y_foot = float(can["sill"][0, 0])

        def sweep_column(a_idx, y_of_w):
            s_b = np.full(len(rows), float(m.s_of_y(y_foot)))
            for _ in range(6):
                t_k = np.stack([laws[b](s_b) for b in knots], axis=1)             # (rows, knots)
                t_b = np.array([np.interp(b, knots, t_k[i]) for i, b in enumerate(rows)])
                frac = np.linspace(0.0, 1.0, 240)
                tt = t_k[:, :1] + (1.0 - t_k[:, :1]) * frac[None, :]
                length = np.concatenate([np.zeros((len(rows), 1)), np.cumsum(np.linalg.norm(np.diff(
                    self.hull.eval(s_b[:, None], tt), axis=1), axis=2), axis=1)], axis=1)
                w = np.array([np.interp(t_b[i], tt[i], length[i]) / length[i, -1] for i in range(len(rows))])
                s_b = m.s_of_y(y_of_w(w, length[:, -1]))
            pin_lam(a_idx, rows, m.lam_of_s(s_b))

        def prow_y(w, girth):
            lead = ARCH_RAKE * girth / (y_foot - PROW_KEEL_Y)                      # leaves the sill along the arch
            return y_foot + (PROW_KEEL_Y - y_foot) * ((w ** 3 - 2 * w ** 2 + w) * lead + 3 * w ** 2 - 2 * w ** 3)

        band0 = float(m.at(m.y, m.s_of_lam(lam[col["p2"], B_SILL]))) - y_foot      # the band's width on the sill
        sweep_column(col["arch"], prow_y)
        sweep_column(col["p2"], lambda w, girth: prow_y(w, girth) + band0 + (PROW_BAND - band0) * smoothstep(0.0, 0.7, w))
        t[:, 0], t[:, -1] = 0.0, 1.0
        fix_t[:, 0] = fix_t[:, -1] = True

        # ---- fill ----------------------------------------------------------------------------
        b_frac = np.linspace(0.0, 1.0, nb)[None, :]
        guess = np.where(fix_t, t, b_frac)
        for b, law, a0, a1 in self._row_laws:
            guess[a0:a1 + 1, b] = law(s_def[a0:a1 + 1])
        lam = solve(lam, fix_l)
        s = m.s_of_lam(lam)
        for b, law, a0, a1 in self._row_laws:
            free = ~fix_t[a0:a1 + 1, b]
            t[a0:a1 + 1, b][free] = law(s[a0:a1 + 1, b])[free]
            fix_t[a0:a1 + 1, b] = True
        t = solve(np.where(fix_t, t, guess), fix_t, along=0.3)
        self.lam, self.s, self.t = lam, s, t
        self.na, self.nb = na, nb
        self.points, self.normals = self.hull.eval(s, t, normals=True)
        self._round_shoulder()
        step = np.linalg.norm(np.diff(self.points, axis=1), axis=2)
        self.girth = np.concatenate([np.zeros((na, 1)), np.cumsum(step, axis=1)], axis=1)

    def hull_sharp(self, s):
        sharp = np.concatenate([[0.0], self.hull.sharp])
        return np.interp(s, np.arange(len(sharp)), sharp)

    def _round_shoulder(self):
        """Cut the two shoulder edges into two-facet bevels and give them blended normals."""
        p, n = self.points, self.normals
        eps = 1e-5
        for b, t_edge in ((B_E1, T1), (B_E2, T2)):
            s = self.s[:, b]
            _, n_before = self.hull.eval(s, np.full(s.shape, t_edge - eps), normals=True)
            _, n_after = self.hull.eval(s, np.full(s.shape, t_edge + eps), normals=True)
            mean = n_before + n_after
            n[:, b] = mean / np.linalg.norm(mean, axis=1, keepdims=True)
            p[:, b] = 0.25 * p[:, b - 1] + 0.5 * p[:, b] + 0.25 * p[:, b + 1]

    # ---- cell classes ---------------------------------------------------------------------
    def cells(self):
        """Boolean masks (na-1, nb-1) of the cell classes."""
        c = self.col
        z = lambda: np.zeros((self.na - 1, self.nb - 1), dtype=bool)
        glass = z()
        glass[:c["arch"], :] = True                              # the whole nose is a glass bubble
        glass[c["arch"]:c["end"], B_ROOF:B_SILL] = True
        doors, hatch = z(), z()
        for a0, a1, b0, b1 in self.door_leaves().values():       # gear doors, cut from the skin
            doors[a0:a1, b0:b1] = True
        hatch[c["h0"]:c["h1"], B_WELL:] = True                   # rear hatch, one panel across the keel
        prow = z()                                               # teal band behind the nose glazing
        prow[c["arch"]:c["p2"], B_SILL:] = True
        mouth = z()
        mouth[c["c0"]:c["c1"], B_CAV0:B_CAV1] = True
        blades = z()
        for b0, b1 in self.blade_rows:
            blades[c["c0"]:c["c1"], b0:b1] = True
        bezel = z()
        bezel[self.col_bezel[0]:self.col_bezel[1], B_E2 + 1:B_BELT0] = True
        belt = z()
        belt[:, B_BELT0:B_BELT1] = True
        belly = z()
        belly[:, B_BELT1:] = True
        aft = z()                               # the tail's underside, teal from the belt down
        aft[self.col_bezel[1]:, B_BELT0:] = True
        belly &= ~aft
        belt |= aft
        return {"glass": glass, "mouth": mouth, "blades": blades, "doors": doors,
                "hatch": hatch, "bezel": bezel & ~mouth, "belt": belt, "prow": prow, "belly": belly}

    def door_leaves(self):
        """Gear door leaves of the port half, as cell ranges (a0, a1, b0, b1): the nose well's two
        leaves span from its side edge to the keel; each main well has four, front and aft, out and in."""
        c = self.col
        return {"Avant_Av": (c["w0"], c["ws"], B_WELL, B_MAX), "Avant_Ar": (c["ws"], c["w1"], B_WELL, B_MAX),
                "Principal_Av_Ext": (c["g0"], c["gs"], B_MAIN_OUT, B_MAIN_MID),
                "Principal_Av_Int": (c["g0"], c["gs"], B_MAIN_MID, B_WELL),
                "Principal_Ar_Ext": (c["gs"], c["g1"], B_MAIN_OUT, B_MAIN_MID),
                "Principal_Ar_Int": (c["gs"], c["g1"], B_MAIN_MID, B_WELL)}

    def side_rim_loop(self, a0, a1, b0, b1):
        """Nodes round a port opening between columns a0..a1 and rows b0..b1, off the keel: a closed
        loop, the first node not repeated. Returns points, normals and, in the skin, the direction
        into the opening."""
        seq = ([(a, b0, a, b0 + 1) for a in range(a0, a1)] + [(a1, b, a1 - 1, b) for b in range(b0, b1)]
               + [(a, b1, a, b1 - 1) for a in range(a1, a0, -1)] + [(a0, b, a0 + 1, b) for b in range(b1, b0, -1)])
        corner = {(a0, b0): (a0 + 1, b0 + 1), (a1, b0): (a1 - 1, b0 + 1), (a1, b1): (a1 - 1, b1 - 1),
                  (a0, b1): (a0 + 1, b1 - 1)}
        seq = [(a, b) + corner.get((a, b), (ja, jb)) for a, b, ja, jb in seq]
        ia, ib, ja, jb = np.array(seq).T
        pts, nrm = self.points[ia, ib], self.normals[ia, ib]
        inward = self.points[ja, jb] - pts
        inward -= nrm * (inward * nrm).sum(axis=1, keepdims=True)
        inward /= np.linalg.norm(inward, axis=1, keepdims=True)
        return pts, nrm, inward

    def rim_loop(self, a0, a1, b0=B_WELL):
        """Nodes round an opening cut across the keel between columns a0 and a1, up to row b0.

        The loop leaves the keel at a0, runs round the port side to the keel at a1 and comes back
        on starboard; the first node is not repeated. Returns points, normals and, in the skin,
        the direction into the opening.
        """
        seq = ([(a0, b, a0 + 1, b) for b in range(B_MAX, b0, -1)] + [(a0, b0, a0 + 1, b0 + 1)]
               + [(a, b0, a, b0 + 1) for a in range(a0 + 1, a1)] + [(a1, b0, a1 - 1, b0 + 1)]
               + [(a1, b, a1 - 1, b) for b in range(b0 + 1, B_MAX + 1)])
        ia, ib, ja, jb = np.array(seq).T
        pts, nrm = self.points[ia, ib], self.normals[ia, ib]
        inward = self.points[ja, jb] - pts
        inward[0], inward[-1] = (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)
        inward -= nrm * (inward * nrm).sum(axis=1, keepdims=True)
        inward /= np.linalg.norm(inward, axis=1, keepdims=True)
        flip = np.array([-1.0, 1.0, 1.0])
        both = lambda v: np.vstack([v, (v[1:-1] * flip)[::-1]])
        return both(pts), both(nrm), both(inward)


if __name__ == "__main__":
    g = HullGrid()
    print("grid", g.na, "x", g.nb, "columns", g.col)
    e_a = np.linalg.norm(np.diff(g.points, axis=0), axis=2)
    e_b = np.linalg.norm(np.diff(g.points, axis=1), axis=2)
    print(f"cells along: {e_a.min() * 100:.1f}..{e_a.max() * 100:.1f} cm, around: {e_b.min() * 100:.2f}..{e_b.max() * 100:.1f} cm")
    d_s = np.diff(g.s, axis=0)
    d_t = np.diff(g.t, axis=1)
    print("monotone along:", bool((d_s > 0).all()), " around:", bool((d_t > 0).all()),
          " min dt", float(d_t.min()), " min ds", float(d_s.min()))
