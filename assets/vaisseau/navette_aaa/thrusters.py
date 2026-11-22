"""Side thrusters of the Navette AAA: flush mouths that keep the hull profile.

The mouth is a hole of the hull grid. Its blades are strips of the same skin, so they continue the
profile across the opening. Behind them a duct runs forward and inward: lip, walls, liner, inner
louvres and the amber light of the concept.
"""
import math

import numpy as np

import frames
import hullgrid as hg
import meshkit

DUCT_DIR = np.array([-0.60, -0.72, 0.28])      # port duct: inward, forward, slightly up
DUCT_DEPTH = 0.52
LIP_R = 0.014
BLADE_DEPTH, BLADE_TIP = 0.27, 0.007
FLIP = frames.FLIP


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def mouth_loop(grid):
    """Nodes round the port mouth: top row aft, rear column down, bottom row forward, front column up.

    Returns points, normals and the in-skin direction pointing out of the hole.
    """
    c0, c1 = grid.col["c0"], grid.col["c1"]
    r0, r1 = hg.B_CAV0, hg.B_CAV1
    seq = ([(a, r0, 0, -1) for a in range(c0, c1)] + [(c1, b, 1, 0) for b in range(r0, r1)]
           + [(a, r1, 0, 1) for a in range(c1, c0, -1)] + [(c0, b, -1, 0) for b in range(r1, r0, -1)])
    corners = {(c0, r0): (-1, -1), (c1, r0): (1, -1), (c1, r1): (1, 1), (c0, r1): (-1, 1)}
    pts, nrm, out = [], [], []
    for a, b, da, db in seq:
        da, db = corners.get((a, b), (da, db))
        p, n = grid.points[a, b], grid.normals[a, b]
        e = grid.points[a + da, b + db] - p
        e = e - n * np.dot(e, n)
        pts.append(p); nrm.append(n); out.append(e / np.linalg.norm(e))
    return np.array(pts), np.array(nrm), np.array(out), seq


def lip_arc(pts, out, d, arc_n=5):
    """Rings of the rounded lip: an arc from the skin tangent (heading into the hole) to the duct direction."""
    u0 = -out
    m = unit(d[None, :] - u0 * (u0 @ d)[:, None])
    theta = np.arccos(np.clip(u0 @ d, -1.0, 1.0))
    return [pts + LIP_R * (m * (1.0 - np.cos(theta * k / arc_n))[:, None] + u0 * np.sin(theta * k / arc_n)[:, None])
            for k in range(arc_n + 1)]


def duct(grid, mats, sign):
    """Lip, duct walls and liner of one mouth, as one mesh."""
    pts, nrm, out, seq = mouth_loop(grid)
    d = unit(DUCT_DIR)
    n_loop = len(pts)
    arc_n = 5
    rings = lip_arc(pts, out, d, arc_n)
    lip_end = rings[-1] - pts
    depths = [0.07, 0.17, BLADE_DEPTH + 0.03, 0.40, DUCT_DEPTH]
    for tau in depths:                                # the lip offset fades: the liner copies the skin
        rings.append(pts + lip_end * (1.0 - tau / DUCT_DEPTH) + d * tau)
    rings = np.array(rings)                           # (rings, loop, 3)
    k_n = len(rings)
    idx = np.arange(k_n * n_loop).reshape(k_n, n_loop)
    faces, slots = [], []
    for k in range(k_n - 1):
        for i in range(n_loop):
            j = (i + 1) % n_loop
            faces.append([idx[k, i], idx[k, j], idx[k + 1, j], idx[k + 1, i]])
            slots.append(0 if k < arc_n else 1)       # painted lip, then dark duct
    guide = np.tile(-out, (k_n, 1))
    verts = rings.reshape(-1, 3)

    # Liner: the mouth's own node grid pushed to the bottom of the duct.
    c0, c1 = grid.col["c0"], grid.col["c1"]
    r0, r1 = hg.B_CAV0, hg.B_CAV1
    back = grid.points[c0:c1 + 1, r0:r1 + 1] + d * DUCT_DEPTH
    na, nb = back.shape[:2]
    base = len(verts)
    loop_of = {(a, b): i for i, (a, b, _, _) in enumerate(seq)}
    back_idx = np.zeros((na, nb), dtype=np.int64)
    extra = []
    for ia in range(na):
        for ib in range(nb):
            key = (c0 + ia, r0 + ib)
            if key in loop_of:                        # the liner's rim is the duct's last ring
                back_idx[ia, ib] = idx[-1, loop_of[key]]
            else:
                back_idx[ia, ib] = base + len(extra)
                extra.append(back[ia, ib])
    verts = np.vstack([verts, np.array(extra)])
    guide = np.vstack([guide, np.tile(-d, (len(extra), 1))])
    liner = meshkit.grid_faces(back_idx).tolist()
    slots += [2] * len(liner)
    scale = np.array([sign, 1.0, 1.0])
    faces = meshkit.wind(verts * scale, faces, guide * scale) + meshkit.wind(verts * scale, liner, guide * scale)
    obj = meshkit.mesh_object(f"Tuyere_Conduit_{'G' if sign > 0 else 'D'}", verts * scale, faces,
                              "01_Exterieur_Coque", materials=[mats["teal"], mats["duct"], mats["core"]],
                              face_mats=np.array(slots))
    obj.data.set_sharp_from_angle(angle=math.radians(50.0))
    return obj


def blades(grid, mats, sign):
    """The blades: bodies behind the skin strips, tapering along the duct."""
    c0, c1 = grid.col["c0"], grid.col["c1"]
    d = unit(DUCT_DIR)
    parts = []
    for k, (r_up, r_lo) in enumerate(grid.blade_rows):
        up, lo = grid.points[c0:c1 + 1, r_up], grid.points[c0:c1 + 1, r_lo]
        mid = 0.5 * (up + lo)
        width = np.linalg.norm(lo - up, axis=1).mean()
        across = unit(lo - up)
        w0, w1, e = 0.5 * width, 0.5 * BLADE_TIP, 0.003
        # The blade dies into the rear ramp: its depth fades over the last third of the mouth.
        run = np.linspace(0.0, 1.0, len(mid))
        depth = BLADE_DEPTH * (0.06 + 0.94 * (1.0 - hg.smoothstep(0.62, 1.0, run)))
        depth *= 0.35 + 0.65 * hg.smoothstep(0.0, 0.10, run)
        feather = 1.0 - 0.8 * hg.smoothstep(0.90, 1.0, run)        # the rear tip thins into the lip
        # (across, up): 'up' is against the duct direction, so the blade grows towards negative up.
        profile = np.stack([np.array([(-w0 * f, -e), (-w0 * f + e * f, 0.0), (w0 * f - e * f, 0.0), (w0 * f, -e),
                                      (w1 * f, -dep + e), (w1 * f - e * f, -dep), (-w1 * f + e * f, -dep),
                                      (-w1 * f, -dep + e)])
                            for dep, f in zip(depth, feather)])
        scale = np.array([sign, 1.0, 1.0])
        parts.append(frames.sweep(f"Aube_{k}", mid * scale, np.tile(-d * scale, (len(mid), 1)), profile,
                                  "01_Exterieur_Coque", [mats["blade"]], across=across * scale, cap=True,
                                  closed=True))
    return meshkit.join(parts, f"Tuyere_Aubes_{'G' if sign > 0 else 'D'}")


def light(grid, mats, sign):
    """Amber line inside the lip, along the top and down the front edge, as in the concept."""
    pts, nrm, out, seq = mouth_loop(grid)
    d = unit(DUCT_DIR)
    c0, c1 = grid.col["c0"], grid.col["c1"]
    n_top = c1 - c0
    n_side = hg.B_CAV1 - hg.B_CAV0
    # front column (walked upwards at the end of the loop), then the top row aft
    order = list(range(len(seq) - n_side + 3, len(seq))) + list(range(0, n_top - 2))
    wall = lip_arc(pts, out, d)[-1]                    # the duct wall behind the lip
    path = wall[order] + d * 0.022                     # just inside the lip: it reads from outside
    scale = np.array([sign, 1.0, 1.0])
    profile = np.array([(-0.010, -0.002), (-0.010, 0.005), (-0.006, 0.009), (0.006, 0.009), (0.010, 0.005),
                        (0.010, -0.002)])
    return frames.sweep(f"Tuyere_Lumiere_{'G' if sign > 0 else 'D'}", path * scale, -out[order] * scale, profile,
                        "01_Exterieur_Coque", [mats["amber_strong"]], cap=True)


def build(grid, mats):
    objs = []
    for sign in (1.0, -1.0):
        objs += [duct(grid, mats, sign), blades(grid, mats, sign), light(grid, mats, sign)]
    return objs
