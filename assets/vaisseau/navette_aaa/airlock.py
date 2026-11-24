"""Aft airlock of the Navette AAA: the airstair on the ventral rear hatch, the frame of the opening,
and the airlock from the cabin bulkhead to the stern end of the opening.

build(mats, grid) returns the objects of the collection 07_Sas_Arriere; self_check(objs, grid)
measures them against the hull, the ground and the hatch's swing.

Every part comes from the cabin's quad-mesh kit (interior.py): lofts and plates, rounded edges as
rings, no boolean, no n-gon, no triangle.
- Airstair: laid out in the open pose, where its treads are level, then turned back with the hatch
  into the closed pose it is built in, and keyed with the hatch's own clip. Closed, its front stays
  aft of the sill; every point stays inside the swing radius of the rear frame.
- Frame: the skin's return round the opening, started on the rim nodes: a jamb with a bulb seal,
  then a low coaming. On the hinge side the coaming's rounded top is the nose of the sill.
- Airlock: sections of the hull's inner offset clipped to vertical walls over 45 degree kick panels;
  a deck that rises from the cabin floor to the hinge sill; aft of it the well, open down to the door;
  a rear wall; the aft face of the bulkhead and of its door.
Frame: metres, nose -Y, up +Z, port +X. UVs in metres.
"""
import math

import bpy
import numpy as np

import anim
import hullgrid as hg
import interior as kit
import meshkit
import panels
from surface import T1, T2

COL = "07_Sas_Arriere"
CLIP = "Trappe_Arriere"
W = 0.62                       # half width of the vertical walls
X_DECK = 0.418                 # half width of the deck face
GAP = 0.040                    # deck face edge to the foot of the kick panel: lit edge, then shadow gap
Y_FRONT = kit.Y_BULKHEAD + 0.04    # aft face of the cabin bulkhead
RISE = (2.45, 3.36)            # the deck climbs from the cabin floor to the sill between these stations
Y_SILL = 3.38                  # aft of this the deck is the hinge sill: ribbed metal laid on the frame
R_KICK, R_COVE = 0.05, 0.09    # fillets of the liner: kick panel to wall, wall to ceiling
R_LIP = 0.005                  # half thickness of the coaming
D_TOP, D_FRONT = 0.075, 0.050  # coaming top under the skin: round the opening, and on the hinge side
NODES = (5, 12, 9)             # liner nodes: kick panel, wall, ceiling
STEPS = 8                      # risers of the airstair
X_TREAD, T_STR = 0.35, 0.03    # half width of the treads, thickness of the stringers
E_MIN, NOSE, H_STR = 0.010, 0.020, 0.05   # least body over the door; nosing projection; stringer over the nosings
CLEAR, X_BAND, Y_BAND = 0.06, 0.75, (1.6, 3.7)
BUDGET = 45000


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


# ---- hatch -------------------------------------------------------------------------------------
class Hatch:
    """Hinge line and poses of the rear hatch, from panels.py."""

    def __init__(self, grid):
        self.axis, self.angle, self.pose = panels.hatch_axis(grid), panels.hatch_angle(grid), panels.hatch_pose(grid)
        self.m_open = np.asarray(self.pose(1.0))
        self.m_back = np.linalg.inv(self.m_open)

    def at(self, p, u):
        m = np.asarray(self.pose(u))
        return np.asarray(p) @ m[:3, :3].T + m[:3, 3]

    def open(self, p):
        return np.asarray(p) @ self.m_open[:3, :3].T + self.m_open[:3, 3]

    def back(self, p):
        return np.asarray(p) @ self.m_back[:3, :3].T + self.m_back[:3, 3]


def door_face(grid, x):
    """Inner face of the closed hatch along the half width x: (columns, 3), fore to aft."""
    c0, c1 = grid.col["h0"], grid.col["h1"]
    p = grid.points[c0:c1 + 1, hg.B_WELL:] - grid.normals[c0:c1 + 1, hg.B_WELL:] * panels.THICK
    return np.array([[np.interp(abs(x), col[::-1, 0], col[::-1, i]) for i in range(3)] for col in p])


# ---- frame of the opening ------------------------------------------------------------------------
def frame(grid):
    """Section rings of the frame round the rim (profile points x rim nodes), the segment materials, the
    direction into the opening, and per rim node the coaming's top and the point just behind its back."""
    pts, nrm, inward = grid.rim_loop(grid.col["h0"], grid.col["h1"])
    across = np.cross(nrm, np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0))
    u = unit(across) * np.sign((across * inward).sum(axis=1))[:, None]
    front = pts[:, 1] < hg.HATCH_Y[0] + 0.3
    d_top = np.where(front, D_FRONT + (D_TOP - D_FRONT) * hg.smoothstep(0.30, 0.43, np.abs(pts[:, 0])), D_TOP)
    r = R_LIP
    # (u into the opening, d under the skin, 1 if d counts from the coaming top)
    sec = [(0.0, 0.0, 0), (0.0, 0.018, 0), (0.0010, 0.0196, 0), (0.0017, 0.0230, 0), (0.0017, 0.0290, 0),
           (0.0010, 0.0324, 0), (0.0, 0.034, 0)]
    sec += [(-r + r * math.cos(a), r * math.sin(a) - r, 1) for a in np.radians([0.0, 45.0, 90.0, 135.0, 180.0])]
    sec += [(-2.0 * r, -0.012, 1)]
    keys = ["dark"] + ["caoutchouc"] * 5 + ["white"] * 6           # dark in the door's gap, white reveal over the seal
    rings = np.array([pts + uk * u - (dk + flag * d_top)[:, None] * nrm for uk, dk, flag in sec])
    top = pts - r * u - d_top[:, None] * nrm
    behind = pts - (2.0 * r + 0.002) * u - (d_top - r)[:, None] * nrm
    return round_corners(rings, pts), keys, u, top, behind


def round_corners(rings, pts, turn=8.0, k=3):
    """Split the loop's segments that turn more than `turn` degrees into k: the ring on the skin stays on
    the hull's straight edges, the deeper rings follow a Catmull-Rom curve through their nodes."""
    tan = unit(np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0))
    bend = np.degrees(np.arccos(np.clip((tan * np.roll(tan, -1, axis=0)).sum(axis=1), -1.0, 1.0)))
    out = []
    for ring_no, ring in enumerate(rings):
        p0, p1, p2, p3 = np.roll(ring, 1, axis=0), ring, np.roll(ring, -1, axis=0), np.roll(ring, -2, axis=0)
        loop = []
        for i in range(len(ring)):
            loop.append(ring[i])
            for s in np.arange(1, k if bend[i] > turn else 1) / k:
                if ring_no == 0:
                    loop.append(p1[i] + s * (p2[i] - p1[i]))
                else:
                    loop.append(0.5 * (2.0 * p1[i] + (p2[i] - p0[i]) * s + (2.0 * p0[i] - 5.0 * p1[i] + 4.0 * p2[i] - p3[i]) * s * s
                                       + (3.0 * p1[i] - p0[i] - 3.0 * p2[i] + p3[i]) * s ** 3))
        out.append(loop)
    return np.array(out)


# ---- hull sections -------------------------------------------------------------------------------
def section(skin, y, n=480):
    """Port half section of the hull's inner offset in the plane y, ceiling depth on the upper skin and
    liner depth below: (x, z) from the top centreline round to the keel."""
    m = skin.maps
    t = np.linspace(0.0, 1.0, n)
    d = np.where(t < T1, kit.CEIL, kit.LINER)
    s = np.full(n, float(m.s_of_y(np.array([y]))[0]))
    for _ in range(3):                     # the offset leans with the normal: shift each station to land on y
        _, nrm = skin.hull.eval(s, t, normals=True)
        s = m.s_of_y(y + nrm[:, 1] * d)
    return skin.inner(s, t, d)[:, [0, 2]]


def branches(sec):
    """The ceiling side (top centre to the beam) and the lower side (keel to the beam), x increasing."""
    k = int(np.argmax(sec[:, 0]))
    return sec[:k + 1], sec[k:][::-1]


def liner_ring(sec, xb, zb, drop, pan):
    """Port half ring of the liner: a hidden foot under the deck or behind the coaming, the kick panel
    from (xb, zb) at 45 degrees, the wall at W, the cove and the ceiling to the centreline."""
    ceil, low = branches(sec)
    zz = zb + np.linspace(0.0, 0.8, 500)
    x = np.minimum(xb + (zz - zb), np.interp(zz, low[:, 1], low[:, 0]))
    k = int(np.argmax(x >= W))
    z1 = zz[k - 1] + (W - x[k - 1]) * (zz[k] - zz[k - 1]) / (x[k] - x[k - 1])
    lower = np.vstack([np.column_stack([x[:k], zz[:k]]), [W, z1]])
    z2 = float(np.interp(W, ceil[:, 0], ceil[:, 1]))
    wall = np.column_stack([np.full(80, W), np.linspace(z1, z2, 80)])
    xc = np.linspace(W, 0.0, 160)
    top = np.column_stack([xc, np.interp(xc, ceil[:, 0], ceil[:, 1])])
    line, s1 = hg.fillet(lower, wall, R_KICK)
    line, s2 = hg.fillet(line, top, R_COVE)
    na, nb, nc = NODES
    pos = np.concatenate([s1 * hg.graded(na, 1.0, 0.7), s1 + (s2 - s1) * hg.graded(nb, 0.7, 0.35)[1:],
                          s2 + (hg.arclen(line)[-1] - s2) * hg.graded(nc, 0.5, 1.0)[1:]])
    vis = hg.at_arclen(line, pos)
    vis[-1, 0] = 0.0
    foot = np.array([(xb - pan, zb - drop), (xb - 0.3 * pan, zb - drop), (xb, zb - 0.55 * drop)])
    return np.vstack([foot, vis])


def ring_keys():
    """Materials of the half ring's segments: dark foot and kick panel, wall, cove light, ceiling."""
    na, nb, nc = NODES
    return ["habillage_sombre"] * (3 + na) + ["habillage"] * (nb - 1) + ["amber"] + ["plafond"] * nc


# ---- airlock -----------------------------------------------------------------------------------
def stations(skin, top, behind, z_s):
    """Liner stations along the ship, (y, foot x, foot z, hidden drop, hidden pan), and their sections.

    Forward of the opening the foot of the kick panel runs in the deck's shadow gap, at the height of
    the deck's edge: the deck dishes up at its sides where the hull's offset climbs above it. Round the
    opening the foot runs behind the coaming. The last station closes on the rear wall, just aft of the
    coaming's back. The first and last stations stand 12 mm beyond the end walls, so that the walls' edges
    lie on the liner. Also returns the deck's edge height law, the deck's height law, the rear wall's
    station and the rim index where its foot leaves the corner."""
    port = np.arange(len(behind) // 2 + 1)
    zf = lambda y: kit.FLOOR + (z_s - kit.FLOOR) * hg.smoothstep(RISE[0], RISE[1], y)
    ys = np.concatenate([[Y_FRONT - 0.012], np.linspace(Y_FRONT, 2.35, 12)[1:], np.linspace(2.35, 3.36, 15)[1:],
                         np.linspace(3.36, 3.47, 6)[1:]])
    rows, secs, edge = [], [], []
    xb = X_DECK + GAP
    for y in ys:
        sec = section(skin, y)
        low = branches(sec)[1]
        zb = max(float(zf(y)), float(np.interp(xb, low[:, 0], low[:, 1])) + 0.004)
        room = zb - float(np.interp(xb - 0.05, low[:, 0], low[:, 1])) - 0.002
        drop = float(np.clip(room, 0.006, 0.04))
        rows.append((y, xb, zb, drop, max(1.25 * drop, GAP + 0.003)))   # the pan always closes the shadow gap
        secs.append(sec)
        edge.append((y, zb))
    y_wall = float(behind[port, 1].max()) + 0.003
    last, y_prev = None, ys[-1] + 0.012
    side = port[(behind[port, 1] > 3.54) & (behind[port, 1] < 4.0)]
    x_side = float(behind[side, 0].max())
    for i in port:                                         # round the corner and along the side, y rising
        y = float(behind[i, 1])
        if behind[i, 0] < X_DECK or y < y_prev or y > y_wall - 0.012:
            continue
        # round the front corner the foot runs straight on from the deck's shadow gap; its pan reaches under
        # the coaming, so the kick panel does not fold where the coaming turns
        x_run = xb + (x_side - xb) * float(hg.smoothstep(ys[-1], 3.56, y)) if y < 3.56 else 0.0
        x_foot = max(float(behind[i, 0]), x_run)
        rows.append((y, x_foot, float(behind[i, 2]), 0.007, x_foot - float(behind[i, 0]) + 0.004))
        secs.append(section(skin, y))
        if last is None:                                   # the deck's corner rises to the liner's foot there
            edge.append((y, float(behind[i, 2])))
        y_prev, last = y + 0.03, i
    corner = port[(port > last) & (behind[port, 1] > y_wall - 0.012)][0]
    rows.append((y_wall + 0.008, float(behind[corner, 0]), float(behind[corner, 2]), 0.003, 0.004))
    secs.append(section(skin, y_wall + 0.008))
    return rows, secs, np.array(edge).T, zf, y_wall, corner


def liner(rows, secs):
    """Walls and ceiling of the airlock, both sides welded on the centreline. Also returns the rings."""
    rings = np.array([np.column_stack([r[:, 0], np.full(len(r), row[0]), r[:, 1]])
                      for row, sec in zip(rows, secs) for r in [liner_ring(sec, *row[1:])]])
    half = kit.loft(rings, closed=False, hard=False, colmat=ring_keys())
    half.facing((-1.0, 0.0, 0.0), face=(len(rings) // 2) * (rings.shape[1] - 1) + 3 + NODES[0] + 4)
    return kit.weld(kit.join([half, half.mirror()])), rings


def deck(zf, edge, top):
    """Deck from the bulkhead to the coaming on the hinge side: plancher on the floor, dished at its
    sides where the hull climbs; aft of Y_SILL a grooved metal sill. Its aft edge follows the coaming."""
    port = np.arange(len(top) // 2 + 1)
    front = port[top[port, 1] < hg.HATCH_Y[0]]                 # coaming tops on the hinge side, centre first
    ah = np.array([0.0, 0.10, 0.18, 0.25, 0.30, 0.34, 0.37, 0.39, 0.405, X_DECK])
    a = np.concatenate([-ah[:0:-1], ah])
    rows = np.concatenate([np.linspace(Y_FRONT + 0.002, RISE[0], 10), np.linspace(RISE[0], Y_SILL, 16)[1:]])
    lines = [(c + o, o in (-0.02, 0.02)) for c in (0.25, 0.5, 0.75) for o in (-0.035, -0.02, 0.02, 0.035)]
    frac = np.array([f for f, _ in lines] + [0.92, 1.0])
    sunk = np.array([g for _, g in lines] + [False, False])
    y_aft = np.interp(np.abs(a), top[front, 0], top[front, 1]) - 0.0015
    bb = np.vstack([np.broadcast_to(rows[:, None], (len(rows), len(a))), Y_SILL + frac[:, None] * (y_aft - Y_SILL)])
    aa = np.broadcast_to(a, bb.shape).copy()
    dish = hg.smoothstep(0.22, X_DECK + 0.01, np.abs(aa))     # the sides curl up where the hull climbs
    zz = zf(bb) + (np.interp(bb, edge[0], edge[1]) - zf(bb)) * dish
    zz[len(rows):] -= 0.0018 * sunk[:, None] * (1.0 - dish[len(rows):])
    zz[-1] = np.minimum(zz[-1], np.interp(np.abs(a), top[front, 0], top[front, 2]) - 0.002)   # under the coaming's top
    nb, na = bb.shape[0] - 1, bb.shape[1] - 1
    jj, ii = kit.border(na, nb)
    ze = zz[jj, ii]
    steps = [(0.0025, ze - 0.0025, "dark"), (0.004, ze - 0.009, "dark"), (0.004, ze - 0.026, "dark")]
    piece = kit.plate(aa, bb, steps, face="plancher", zf=lambda _a, _b: zz)
    kit.planar(piece, "cap0", (1, 0, 0), (0, 1, 0))
    cap = piece.tag["cap0"]
    mid = piece.v[piece.f[cap]].mean(axis=1)
    piece.m[cap.start + np.nonzero(mid[:, 1] > Y_SILL)[0]] = "acier"
    return piece


def deck_lights(zf, edge):
    """Amber line in the shadow gap along each side of the deck, from the bulkhead to the rise."""
    ys = np.linspace(Y_FRONT + 0.012, RISE[1] - 0.10, 40)
    z = np.maximum(zf(ys), np.interp(ys, edge[0], edge[1])) - 0.011
    path = np.column_stack([np.full(len(ys), X_DECK + 0.029), ys, z])
    path = np.vstack([path[:1] - (0.0, 0.004, 0.0), path, path[-1:] + (0.0, 0.004, 0.0)])
    full, small = kit.rrect(0.007, 0.007, 0.0025, 1)[0], kit.rrect(0.004, 0.003, 0.001, 1)[0]
    sec = np.array([small] + [full] * len(ys) + [small])
    return kit.both(kit.tube(path, sec, (1, 3, 1), "amber", right=(1.0, 0.0, 0.0)))


def end_wall(ring, line, y, face_dir):
    """Plate closing the airlock at the station y. ring: the port half ring's visible part (x, z), from
    the foot of the kick panel to the centreline; line: (x, z) of its foot from port to starboard."""
    na, nb, _ = NODES
    k_c = na + nb                                              # ring node at the cove: grid corners
    n_top = len(ring) - 1 - k_c
    assert len(line) - 1 == 2 * n_top, (len(line), n_top)
    flip = np.array([-1.0, 1.0])
    loop = np.vstack([line[:-1], (ring * flip)[:-1], ring[::-1][:-1]])
    inner = loop.mean(axis=0) + (loop - loop.mean(axis=0)) * 0.994          # a short hidden band behind the face
    ring3 = lambda yy, lp: np.column_stack([lp[:, 0], np.full(len(lp), yy), lp[:, 1]])
    piece = kit.loft(np.array([ring3(y, loop), ring3(y - 0.004 * face_dir, inner)]), "habillage",
                     caps=((2 * n_top, k_c, 0), None))
    piece.facing((0.0, face_dir, 0.0), face=piece.tag["cap0"].start)
    kit.planar(piece, "cap0", (1, 0, 0), (0, 0, 1))
    return piece


def door_back(z_floor):
    """The cabin door seen from the airlock: frame, leaf, porthole, handle, kick plate, sign."""
    def on_back(piece, x, z, proud):
        return piece.place((x, Y_FRONT + proud, z), (-1, 0, 0), (0, 0, 1), (0, 1, 0))

    top = 0.62
    path = kit.Path2([(-0.43, z_floor - 0.01), (-0.43, top), (0.43, top), (0.43, z_floor - 0.01)], [0, 0.17, 0.17, 0])
    st = np.concatenate([np.linspace(a, b, n)[:-1] for a, b, n in zip(path.marks[:-1], path.marks[1:], (4, 6, 3, 6, 4))]
                        + [[path.length]])
    xz = path.at(st)[0]
    parts = [kit.tube(np.column_stack([xz[:, 0], np.full(len(st), Y_FRONT + 0.008), xz[:, 1]]),
                      kit.rrect(0.026, 0.052, 0.007, 1)[0], (1, 3, 1), "habillage_sombre", right=(0.0, 1.0, 0.0))]
    hgt = top - 0.03 - z_floor
    leaf = kit.plate(*kit.lattice(np.array([0.0, 0.20, 0.396 - 0.14, 0.396 - 0.586 * 0.14, 0.396]),
                                  np.array([0.0, 0.3, 0.75, 1.2, hgt - 0.14, hgt - 0.586 * 0.14, hgt]), (0.0, 0.14)),
                     [(0.003, -0.003, "porte"), (0.003, -0.014, "porte")], face="porte")
    parts.append(on_back(leaf, 0.0, z_floor - 0.004, 0.012))
    rim = [(0.003, -0.003, "dark"), (0.003, -0.008, "dark")]
    parts.append(on_back(kit.tile(0.18, 0.46, 0.089, rim, "dark", n=4), 0.0, -0.02, 0.017))
    parts.append(on_back(kit.tile(0.13, 0.41, 0.064, [(0.002, -0.002, "hublot"), (0.002, -0.006, "hublot")], "hublot",
                                  n=4), 0.0, -0.02, 0.0185))
    parts.append(on_back(kit.tile(0.66, 0.15, 0.02, [(0.002, -0.002, "champagne"), (0.002, -0.006, "champagne")],
                                  "champagne", mid=(0.15,)), 0.0, z_floor + 0.11, 0.0155))
    parts.append(on_back(kit.tile(0.05, 0.17, 0.024, rim, "dark", n=3), 0.31, -0.33, 0.0175))
    grip = kit.Path2([(0.0, 0.0), (0.045, 0.0), (0.045, -0.115)], [0, 0.018, 0])
    st = np.concatenate([[0.0], np.linspace(grip.marks[1], grip.marks[2], 5), [grip.length - 0.01, grip.length]])
    g = grip.at(st)[0]
    ang = np.arange(12) * math.pi / 6
    lever = 0.0095 * np.stack([np.cos(ang), np.sin(ang)], axis=1) * np.concatenate([np.ones(len(st) - 1), [0.7]])[:, None, None]
    parts.append(kit.tube(np.column_stack([np.full(len(st), 0.31), Y_FRONT + 0.012 + g[:, 0], -0.28 + g[:, 1]]), lever,
                          (3, 3, 0), "champagne", right=(1.0, 0.0, 0.0), hard=False))
    parts.append(on_back(kit.tile(0.30, 0.056, 0.014, [(0.003, -0.003, "dark"), (0.003, -0.016, "dark")], "dark"),
                         0.0, top + 0.105, 0.014))
    parts.append(on_back(kit.tile(0.25, 0.026, 0.008, [(0.0015, -0.0015, "amber"), (0.0015, -0.004, "amber")], "amber"),
                         0.0, top + 0.105, 0.0165))
    return kit.join(parts)


def on_wall(piece, y, z, proud):
    """Set a plate (its frame: along the ship, up, out of the wall) on the port wall."""
    return piece.place((W - proud, y, z), (0, -1, 0), (0, 0, 1), (-1, 0, 0))


def fittings():
    """Flush lockers on the corridor walls and grab handles by the sill, port side."""
    parts = []
    seam = [(0.0025, -0.0025, "habillage_sombre"), (0.0025, -0.012, "habillage_sombre")]
    for y in (0.42, 1.06, 1.70):
        parts.append(on_wall(kit.tile(0.56, 1.02, 0.035, seam, "habillage", mid=(0.20,)), y, -0.30, 0.002))
        parts.append(on_wall(kit.tile(0.11, 0.028, 0.012, [(0.002, -0.002, "dark"), (0.002, -0.010, "dark")], "dark"),
                             y, 0.12, 0.004))
        parts.append(on_wall(kit.tile(0.016, 0.016, 0.006, [(0.001, -0.001, "amber"), (0.001, -0.004, "amber")], "amber"),
                             y + 0.20, 0.12, 0.004))
    ang = np.arange(12) * math.pi / 6
    sec = 0.0125 * np.stack([np.cos(ang), np.sin(ang)], axis=1)
    for y, z0, z1 in ((3.12, -0.62, 0.02), (3.86, -0.52, 0.08)):
        grip = kit.Path2([(0.0, z0 - 0.04), (0.06, z0), (0.06, z1), (0.0, z1 + 0.04)], [0, 0.03, 0.03, 0])
        st = np.unique(np.concatenate([np.linspace(a, b, 6) for a, b in zip(grip.marks[:-1], grip.marks[1:])]))
        oz = grip.at(st)[0]
        path = np.column_stack([W + 0.004 - oz[:, 0], np.full(len(st), y), oz[:, 1]])
        parts.append(kit.tube(path, sec, (3, 3, 0), "acier", right=(0.0, 1.0, 0.0), hard=False))
    return kit.join(parts)


def rear_panel(y_wall):
    """Flush service panel on the rear wall, two latches and an amber placard over it."""
    on_rear = lambda piece, x, z, proud: piece.place((x, y_wall - proud, z), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    seam = [(0.0025, -0.0025, "habillage_sombre"), (0.0025, -0.012, "habillage_sombre")]
    parts = [on_rear(kit.tile(0.46, 0.54, 0.04, seam, "habillage", mid=(0.12,)), 0.0, -0.13, 0.002)]
    for x in (-0.16, 0.16):
        parts.append(on_rear(kit.tile(0.028, 0.05, 0.01, [(0.002, -0.002, "champagne"), (0.002, -0.006, "champagne")],
                                      "champagne"), x, 0.09, 0.0045))
    parts.append(on_rear(kit.tile(0.22, 0.022, 0.008, [(0.0015, -0.0015, "amber"), (0.0015, -0.004, "amber")], "amber"),
                         0.0, 0.20, 0.003))
    return kit.join(parts)


# ---- airstair ----------------------------------------------------------------------------------
def stair_plan(grid, hatch, z_s, rings):
    """Layout of the airstair in the open pose: tread heights, nosings, front, and the limits it keeps."""
    ay, az = hatch.axis[1], hatch.axis[2]
    pts = rings.reshape(-1, 3)
    rear = pts[pts[:, 1] > 5.0]
    radius = np.hypot(rear[:, 1] - ay, rear[:, 2] - az)
    # the swing turns about X: treads and stringers each keep clear of the rear frame at their own x
    r_swing, r_str = (float(radius[np.abs(rear[:, 0]) <= x + 0.012].min()) - 0.012 for x in (X_TREAD, X_TREAD + T_STR))
    near = pts[(np.abs(pts[:, 0]) <= X_TREAD + T_STR + 0.012) & (pts[:, 1] < 3.6) & (pts[:, 2] > z_s - 0.008)]
    y_lim = float(near[:, 1].max()) + 0.008
    xs = np.linspace(0.0, X_TREAD + T_STR, 13)
    ramps = [hatch.open(door_face(grid, x))[:, 1:] for x in xs]
    yy = np.linspace(3.45, 5.80, 941)
    hi = np.max([np.interp(yy, r[:, 0], r[:, 1], right=np.nan) for x, r in zip(xs, ramps) if x <= X_TREAD + 0.003], axis=0)
    y_end = min(float(r[-1, 0]) for r in ramps)
    rise = (z_s - panels.GROUND) / STEPS
    z = panels.GROUND + rise * np.arange(1, STEPS + 1)
    need = [float(yy[int(np.argmax(hi <= zk - E_MIN))]) for zk in z[:-1]]       # inner corner of tread k: y at least
    for going in np.arange(0.265, 0.199, -0.0025):
        y_land = max(need[k] + NOSE - (STEPS - 2 - k) * going for k in range(STEPS - 1))
        y_first = y_land + (STEPS - 1) * going
        if math.hypot(y_first - ay, z[0] - az) <= r_swing - 0.004:
            break
    else:
        raise RuntimeError("no airstair fits the hatch")
    nosing = y_land + going * np.arange(STEPS - 1, -1, -1)                    # tread 1 .. landing
    rn, front = 0.012, 3.5                     # the landing's front: once closed it stands aft of y_lim
    for _ in range(2):
        nose = np.array([[0.0, front + rn - rn * math.cos(a), z_s - rn + rn * math.sin(a)]
                         for a in np.linspace(0.0, 0.5 * math.pi, 7)])
        front += (y_lim - hatch.back(nose)[:, 1].min()) / math.cos(hatch.angle) + 1e-4
    return dict(z=z, rise=rise, going=going, nosing=nosing, front=front, rn=rn, r_swing=r_swing, r_str=r_str,
                y_lim=y_lim, y_end=y_end, ramps=ramps, xs=xs)


def ramp_at(plan, x):
    """The door's inner face in the open pose along the half width x: (y, z), fore to aft."""
    xs = plan["xs"]
    k = int(np.clip(np.searchsorted(xs, abs(x)), 1, len(xs) - 1))
    w = (abs(x) - xs[k - 1]) / (xs[k] - xs[k - 1])
    return (1.0 - w) * plan["ramps"][k - 1] + w * plan["ramps"][k]


def swing_y(plan, hatch, z, inset, key="r_swing"):
    """Aft limit of the airstair at the height z, open pose: the swing circle of the rear frame."""
    ay, az = hatch.axis[1], hatch.axis[2]
    return ay + math.sqrt(max((plan[key] - inset) ** 2 - (z - az) ** 2, 0.0))


def step_profile(plan, hatch, ramp):
    """Closed side profile of the step body over one ramp line, open pose (y, z), and the material of each
    segment: landing and seven treads with ribs and nosings, risers, the raked bottom riser, the base."""
    z, nos, rn, front = plan["z"], plan["nosing"], plan["rn"], plan["front"]
    pts, keys = [], []

    def add(p, key):
        pts.append(p)
        keys.append(key)

    def ribs(y0, y1, zk):
        """Tread top from y0 to y1 at zk: anti-slip ribs, plancher between them."""
        n = max(int((y1 - y0) / 0.048), 1)
        for c in y0 + (y1 - y0) * (np.arange(n) + 0.5) / n:
            add((c - 0.0065, zk), "acier")
            add((c - 0.0040, zk + 0.0025), "acier")
            add((c + 0.0040, zk + 0.0025), "acier")
            add((c + 0.0065, zk), "plancher")

    def nosing(yn, zk, last=False):
        add((yn - 0.034, zk), "champagne")
        for a in np.radians([0.0, 30.0, 60.0, 90.0]):
            add((yn - rn + rn * math.sin(a), zk - rn + rn * math.cos(a)), "champagne")
        add((yn, zk - 0.026), "habillage_sombre")
        add((yn - 0.006, zk - 0.032), "habillage_sombre")
        if not last:
            add((yn - NOSE, zk - 0.032), "habillage_sombre")

    base = lambda y: float(np.interp(y, ramp[:, 0], ramp[:, 1])) - 0.002
    rf = float(np.clip(0.5 * (z[-1] - base(front)), 0.0012, rn))   # at the hinge the landing is a thin wedge
    add((front, base(front)), "habillage_sombre")
    for a in np.radians([0.0, 30.0, 60.0]):
        add((front + rf - rf * math.cos(a), z[-1] - rf + rf * math.sin(a)), "champagne")
    add((front + rf, z[-1]), "plancher")
    ribs(front + rn + 0.02, nos[-1] - 0.04, z[-1])
    for k in range(STEPS - 1, 0, -1):                          # landing nosing, then treads 7 .. 1
        nosing(nos[k], z[k])
        add((nos[k] - NOSE, z[k - 1]), "plancher")
        ribs(nos[k] - NOSE + 0.012, nos[k - 1] - 0.04, z[k - 1])
    nosing(nos[0], z[0], last=True)
    y_foot = min(swing_y(plan, hatch, base(plan["y_end"]), 0.010), plan["y_end"] - 0.006)
    for zk in np.linspace(z[0] - 0.034, base(y_foot) + 0.008, 4):     # raked bottom riser, inside the swing circle
        add((min(nos[0] - 0.010, swing_y(plan, hatch, zk, 0.010)), zk), "habillage_sombre")
    for y in np.linspace(y_foot, front, 14)[:-1]:
        add((y, base(y)), "dark")
    return np.array(pts), keys


def stringer_outline(plan, hatch, ramp, nu=30, nv=5):
    """Side outline of a stringer, open pose (y, z), counter-clockwise as the four sides of a quad grid:
    base on the door from the front, rear end on the swing circle, top over the nosings, and the front cut
    that stands aft of the sill once closed."""
    z, nos = plan["z"], plan["nosing"]
    ay, az, al = hatch.axis[1], hatch.axis[2], hatch.angle
    slope = plan["rise"] / plan["going"]
    top = lambda y: z[-1] + H_STR - (y - nos[-1]) * slope
    cut = lambda zz: ay + ((plan["y_lim"] - ay) + (zz - az) * math.sin(al)) / math.cos(al) + 0.002
    base = lambda y: np.interp(y, ramp[:, 0], ramp[:, 1]) - 0.002
    y0 = plan["front"]
    for _ in range(6):
        y0 = cut(float(base(y0)))
    lo, hi = y0, nos[-1]                                       # peak: the cut meets the top line
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if cut(top(mid)) > mid else (lo, mid)
    y_peak = 0.5 * (lo + hi)
    swing = lambda zz: swing_y(plan, hatch, zz, 0.006, "r_str")
    lo, hi = nos[0] - 0.05, nos[0] + 0.15                     # rear: the top line meets the swing circle
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if swing(top(mid)) > mid else (lo, mid)
    y_back = 0.5 * (lo + hi)
    y_foot = min(swing(float(base(plan["y_end"]))), plan["y_end"] - 0.006)
    zr = np.linspace(top(y_back), float(base(y_foot)), 60)
    rear = np.column_stack([[swing(v) for v in zr], zr])
    rear[-1, 0] = y_foot
    zc = np.linspace(float(base(y0)), top(y_peak), 60)
    front_cut = np.column_stack([[cut(v) for v in zc], zc])
    yt = np.linspace(y_peak, y_back, 200)
    line, s_peak = hg.fillet(front_cut, np.column_stack([yt, top(yt)]), 0.05)
    line, s_back = hg.fillet(line, rear, 0.025)
    yb = np.linspace(y0, y_foot, 300)
    sole = np.column_stack([yb, base(yb)])
    sole = hg.at_arclen(sole, np.linspace(0.0, hg.arclen(sole)[-1], nu + 1))
    up_front = hg.at_arclen(line, np.linspace(0.0, s_peak, nv + 1))
    crest = hg.at_arclen(line, np.linspace(s_peak, s_back, nu + 1))
    down_rear = hg.at_arclen(line, np.linspace(s_back, hg.arclen(line)[-1], nv + 1))
    loop = np.vstack([sole[:-1], down_rear[::-1][:-1], crest[::-1][:-1], up_front[::-1][:-1]])
    return loop, (nu, nv)


def stair(plan, hatch):
    """The airstair in the open pose: step body, two stringers with their amber lines."""
    rings, keys = [], None
    for x in (-X_TREAD - 0.002, -0.24, -0.12, 0.0, 0.12, 0.24, X_TREAD + 0.002):
        prof, keys = step_profile(plan, hatch, ramp_at(plan, x))
        rings.append(np.column_stack([np.full(len(prof), x), prof]))
    body = kit.loft(np.array(rings), closed=True, colmat=keys)
    body.facing((0.0, 0.0, 1.0), face=3 * len(keys) + keys.index("plancher"))
    outline, (nu, nv) = stringer_outline(plan, hatch, ramp_at(plan, X_TREAD + 0.5 * T_STR))
    n2 = kit.loop_normals(outline)
    sole = np.arange(len(outline)) <= nu                       # on the door: no rounding, the door's own height
    r = 0.006
    faces = [(r * (1.0 - math.sin(a)), X_TREAD + T_STR - r * (1.0 - math.cos(a))) for a in np.radians([0.0, 45.0, 90.0])]
    faces += [(r * (1.0 - math.sin(a)), X_TREAD + r * (1.0 - math.cos(a))) for a in np.radians([90.0, 45.0, 0.0])]
    srings = []
    for inset, x in faces:
        ring = outline - n2 * (inset * ~sole)[:, None]
        ramp = ramp_at(plan, x)
        ring[sole, 1] = np.interp(ring[sole, 0], ramp[:, 0], ramp[:, 1]) - 0.002
        srings.append(np.column_stack([np.full(len(ring), x), ring]))
    srings = np.array(srings)
    plate = kit.loft(srings, "white", caps=((nu, nv, 0), (nu, nv, 0))).outward()
    nos, z = plan["nosing"], plan["z"]
    slope = plan["rise"] / plan["going"]
    ys = np.linspace(nos[-1] - 0.05, nos[0] - 0.01, 30)
    path = np.column_stack([np.full(len(ys), X_TREAD - 0.0005), ys, z[-1] + H_STR - 0.017 - (ys - nos[-1]) * slope])
    along = np.array([0.0, 0.003, -0.003 * slope])
    path = np.vstack([path[:1] - along, path, path[-1:] + along])
    full, small = kit.rrect(0.004, 0.010, 0.0015, 1)[0], kit.rrect(0.002, 0.006, 0.0008, 1)[0]
    light = kit.tube(path, np.array([small] + [full] * len(ys) + [small]), (1, 3, 1), "amber", right=(1.0, 0.0, 0.0))
    return kit.join([body, kit.both(kit.join([plate, light]))])


# ---- build -------------------------------------------------------------------------------------
def emit(name, piece, pal):
    """The kit's emit, moved into this module's collection."""
    obj = kit.emit(name, piece, pal)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    meshkit.collection(COL).objects.link(obj)
    return obj


def layout(grid):
    """Everything the parts and the check share: frame, sections, liner rings, stair plan."""
    skin, hatch = kit.Skin(grid), Hatch(grid)
    rings_f, keys_f, u, top, behind = frame(grid)
    z_s = float(top[0, 2])
    rows, secs, edge, zf, y_wall, corner = stations(skin, top, behind, z_s)
    return dict(skin=skin, hatch=hatch, rings_f=rings_f, keys_f=keys_f, u=u, top=top, behind=behind, z_s=z_s,
                rows=rows, secs=secs, edge=edge, zf=zf, y_wall=y_wall, corner=corner,
                plan=stair_plan(grid, hatch, z_s, rings_f))


def ring_at(rings, y):
    """Visible half ring (x, z) of the liner at the station y, on its faces between two stations."""
    ys = rings[:, 0, 1]
    k = int(np.clip(np.searchsorted(ys, y), 1, len(ys) - 1))
    w = (y - ys[k - 1]) / (ys[k] - ys[k - 1])
    return ((1.0 - w) * rings[k - 1] + w * rings[k])[3:][:, [0, 2]]


def build(mats, grid):
    pal = dict(kit.palette(mats))
    pal.update(white=mats["white"], teal=mats["teal"])
    lay = layout(grid)
    fr = kit.loft(lay["rings_f"], lay["keys_f"], closed=True, hard=True)
    fr.facing(lay["u"][0], face=0)                             # the jamb looks into the opening
    lin, rings_l = liner(lay["rows"], lay["secs"])
    # rear wall: its foot follows the coaming behind the rear edge, from the corner to the centreline
    behind, corner = lay["behind"], lay["corner"]
    n_top = rings_l.shape[1] - 4 - NODES[0] - NODES[1]
    last = ring_at(rings_l, lay["y_wall"])
    line = np.vstack([last[:1], behind[corner:len(behind) // 2 + 1][:, [0, 2]]])
    line = np.vstack([line, (line[:-1] * (-1.0, 1.0))[::-1]])
    line = hg.at_arclen(line, np.linspace(0.0, hg.arclen(line)[-1], 2 * n_top + 1))
    rear = end_wall(last, line, lay["y_wall"], -1.0)
    first = ring_at(rings_l, Y_FRONT)
    sill = np.column_stack([np.linspace(first[0, 0], -first[0, 0], 2 * n_top + 1), np.full(2 * n_top + 1, first[0, 1] - 0.003)])
    fwd = end_wall(first, sill, Y_FRONT, 1.0)
    objs = [emit("Sas_Cadre_Trappe", fr, pal),
            emit("Sas_Plancher", kit.join([deck(lay["zf"], lay["edge"], lay["top"]), deck_lights(lay["zf"], lay["edge"])]), pal),
            emit("Sas_Habillage", kit.join([lin, rear, fwd, kit.both(fittings()), rear_panel(lay["y_wall"])]), pal),
            emit("Sas_Cloison_Porte", door_back(kit.FLOOR), pal)]
    steps = stair(lay["plan"], lay["hatch"])
    steps.v = lay["hatch"].back(steps.v)
    obj = emit("Sas_Escalier", steps, pal)
    anim.bake(obj, CLIP, lay["hatch"].pose)
    objs.append(obj)
    spare = bpy.data.collections.get(kit.COL)
    if spare is not None and not spare.objects and not spare.children:
        bpy.data.collections.remove(spare)
    p = lay["plan"]
    print("AIRLOCK_PLAN risers %d x %.4f m, going %.4f m, landing %.3f..%.3f, first nosing %.3f, swing r %.3f, "
          "front limit %.3f, sill %.4f" % (STEPS, p["rise"], p["going"], p["front"], p["nosing"][-1], p["nosing"][0],
                                            p["r_swing"], p["y_lim"], lay["z_s"]))
    return objs


# ---- check -------------------------------------------------------------------------------------
def world_points(obj):
    co = np.zeros(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", co)
    mw = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def nearest(a, b, chunk=256):
    """Least distance from each point of a to the point set b."""
    out = np.empty(len(a))
    bb = (b ** 2).sum(axis=1)[None, :]
    for c in range(0, len(a), chunk):
        p = a[c:c + chunk]
        out[c:c + chunk] = np.sqrt(np.maximum(((p ** 2).sum(axis=1)[:, None] - 2.0 * p @ b.T + bb).min(axis=1), 0.0))
    return out


def wall_margin(rings, pts):
    """Room left between points and the liner's kick panels and walls, in the sections of the stations:
    the liner's half width at the point's height minus |x|. Points under a station's foot get +inf."""
    ys = rings[:, 0, 1]
    out = np.full(len(pts), np.inf)
    for n, (x, y, z) in enumerate(pts):
        if y < ys[0] or y > ys[-1]:
            continue
        k = int(np.clip(np.searchsorted(ys, y), 1, len(ys) - 1))
        w = (y - ys[k - 1]) / (ys[k] - ys[k - 1])
        half = []
        for r in (rings[k - 1], rings[k]):
            vis = r[3:3 + NODES[0] + NODES[1] + 1]             # foot of the kick panel up to the cove
            if z < vis[0, 2]:
                half = None
                break
            half.append(np.interp(z, vis[:, 2], vis[:, 0], right=-np.inf))
        if half is not None:
            out[n] = (1.0 - w) * half[0] + w * half[1] - abs(x)
    return out


def self_check(objs, grid, verbose=True):
    """Measure the module: mesh soundness and triangles (the cabin kit's own check), clearance under the
    skin, the band left to the thruster ducts, the open hatch and airstair against the ground, the airstair
    against the frame, the deck and the liner, closed and all along the swing, and the keys of its pose."""
    base = kit.self_check(objs, grid, verbose=False)            # mesh soundness; its depth stops at y = 1.2
    lay = layout(grid)
    skin, hatch = lay["skin"], lay["hatch"]
    bpy.context.view_layer.update()
    pts = {o.name: world_points(o) for o in objs}
    rep = {"objects": {}, "notes": [], "triangles": base["triangles"]}
    # height of the airstair over the closed hatch's inner face, which it stands on
    closed = pts["Sas_Escalier"]
    xs_d = np.linspace(0.0, X_TREAD + T_STR + 0.01, 40)
    faces_d = [door_face(grid, x) for x in xs_d]
    k_d = np.clip(np.searchsorted(xs_d, np.abs(closed[:, 0])), 1, len(xs_d) - 1)
    w_d = np.clip((np.abs(closed[:, 0]) - xs_d[k_d - 1]) / xs_d[1], 0.0, 1.0)
    at = lambda i, p: np.interp(p[1], faces_d[i][:, 1], faces_d[i][:, 2])
    over = closed[:, 2] - np.array([(1.0 - w) * at(k - 1, p) + w * at(k, p) for p, k, w in zip(closed, k_d, w_d)])
    rep["stair_over_door"] = float(over.min())
    soundness = ("ngons", "tris", "loose", "doubled", "degenerate", "nonmanifold", "miswound")
    for name, p in pts.items():
        row = {k: base["objects"][name].get(k) for k in ("triangles",) + soundness + ("open_edges", "uv")}
        depth = skin.depth(p)
        row["min_depth"] = float(depth.min())
        if name == "Sas_Plancher":                     # the hinge sill lies on the frame
            row["min_depth_floor"] = float(depth[p[:, 1] < Y_SILL - 0.01].min())
            row["shallow"] = int((depth[p[:, 1] < Y_SILL - 0.01] < CLEAR).sum())
        elif name == "Sas_Escalier":                   # its base, 15 mm high, stands on the hatch's inner face
            row["shallow"] = int(((depth < CLEAR) & (over > 0.015)).sum())
            row["min_depth_above_base"] = float(depth[over > 0.015].min())
        elif name != "Sas_Cadre_Trappe":               # the frame starts on the skin
            row["shallow"] = int((depth < CLEAR).sum())
        band = (p[:, 1] > Y_BAND[0]) & (p[:, 1] < Y_BAND[1])
        row["x_band"] = float(np.abs(p[band, 0]).max()) if band.any() else 0.0
        rep["objects"][name] = row
        bad = [k for k in soundness if row.get(k)] + (["shallow"] if row.get("shallow") else [])
        bad += ["x_band"] if row["x_band"] > X_BAND else []
        bad += ["uv"] if not row["uv"] else []
        if bad:
            rep["notes"].append("%s: %s" % (name, ", ".join(bad)))
        if verbose:
            print("CHECK %-18s tris %6d depth %+.3f shallow %s |x| in band %.3f | ngon %s tri %s loose %s doubled %s "
                  "degenerate %s nonmanifold %s miswound %s open %s" % (
                      name, row["triangles"], row["min_depth"], row.get("shallow", "-"), row["x_band"],
                      *[row[k] for k in soundness], row["open_edges"]))
    stair_obj = next(o for o in objs if o.name == "Sas_Escalier")
    # the baked keys: the last frame of the clip is the open pose
    scene = bpy.context.scene
    scene.frame_set(anim.CLIPS[CLIP])
    keyed = np.array(stair_obj.matrix_world)
    scene.frame_set(0)
    rep["key_error"] = float(np.abs(keyed - hatch.m_open).max())
    opened = hatch.open(closed)
    rep["stair_ground"] = float(opened[:, 2].min() - panels.GROUND)
    door = bpy.data.objects.get("Trappe_Arriere")
    if door is not None:
        rep["door_ground"] = float(hatch.open(world_points(door))[:, 2].min() - panels.GROUND)
    # treads level once open: every face of the tread surfaces (plancher) between the ribs
    me = stair_obj.data
    slot = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", slot)
    nrm = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3) @ hatch.m_open[:3, :3].T
    tread = np.isin(slot, [i for i, m in enumerate(me.materials) if m and m.name.startswith("NAV_Plancher")])
    rep["tread_tilt_deg"] = float(np.degrees(np.arccos(np.clip(nrm[tread, 2], -1.0, 1.0))).max())
    # the airstair against the fixed parts, closed and along the swing
    fixed = np.vstack([pts[n] for n in ("Sas_Cadre_Trappe", "Sas_Plancher") if n in pts])
    rings = np.array([np.column_stack([r[:, 0], np.full(len(r), row[0]), r[:, 1]])
                      for row, sec in zip(lay["rows"], lay["secs"]) for r in [liner_ring(sec, *row[1:])]])
    sample = closed[::3]
    gaps, margins = [], []
    for u in np.linspace(0.0, 1.0, 13):
        p = hatch.at(sample, u)
        inside = p[:, 2] > -2.0
        gaps.append(float(nearest(p, fixed).min()))
        margins.append(float(wall_margin(rings, p[inside & (p[:, 1] > 3.3)]).min()) if (inside & (p[:, 1] > 3.3)).any() else np.inf)
    rep["stair_fixed_gap"] = min(gaps)
    rep["stair_fixed_gap_closed"] = gaps[0]
    rep["stair_wall_margin"] = min(margins)
    rep["stair_front_closed"] = float(closed[:, 1].min())
    rep["stair_rear_closed"] = float(closed[:, 1].max())
    rep["rear_wall"] = float(lay["y_wall"])
    for key, ok in (("key_error", rep["key_error"] < 1e-4), ("stair_ground", rep["stair_ground"] > 0.0),
                    ("stair_over_door", rep["stair_over_door"] > -0.0045),
                    ("door_ground", rep.get("door_ground", 1.0) > 0.0), ("tread_tilt_deg", rep["tread_tilt_deg"] < 0.5),
                    ("stair_fixed_gap", rep["stair_fixed_gap"] > 0.003), ("stair_wall_margin", rep["stair_wall_margin"] > 0.01),
                    ("stair_rear_closed", rep["stair_rear_closed"] < rep["rear_wall"] - 0.01),
                    ("triangles", rep["triangles"] <= BUDGET)):
            if not ok:
                rep["notes"].append(key)
    p = lay["plan"]
    rep["plan"] = dict(risers=STEPS, rise=p["rise"], going=p["going"], landing=(p["front"], p["nosing"][-1]),
                       nosings=p["nosing"].tolist(), sill=lay["z_s"], width=2 * X_TREAD)
    rep["ok"] = not rep["notes"]
    if verbose:
        print("CHECK airstair: %d risers of %.4f m, going %.4f m, treads %.2f m wide, landing %.3f..%.3f m, sill z %.4f" % (
            STEPS, p["rise"], p["going"], 2 * X_TREAD, p["front"], p["nosing"][-1], lay["z_s"]))
        print("CHECK open: stair %.4f m and door %s m over the ground; tread tilt %.3f deg; key error %.1e; "
              "closed, the stair's base %.4f m off the door's inner face" % (
                  rep["stair_ground"], "%.4f" % rep["door_ground"] if "door_ground" in rep else "n/a",
                  rep["tread_tilt_deg"], rep["key_error"], rep["stair_over_door"]))
        print("CHECK swing: least gap to the frame and deck %.4f m (closed %.4f); room to the liner %.4f m; "
              "closed y %.3f..%.3f, rear wall %.3f" % (rep["stair_fixed_gap"], rep["stair_fixed_gap_closed"],
                                                       rep["stair_wall_margin"], rep["stair_front_closed"],
                                                       rep["stair_rear_closed"], rep["rear_wall"]))
        print("CHECK total triangles %d / %d; notes %s; ok %s" % (rep["triangles"], BUDGET, rep["notes"], rep["ok"]))
    return rep
