"""Doors cut out of the hull skin: the gear doors and the ventral rear hatch.

A door is made of the hull's own cells, so it closes flush. It gets an edge return and an inner
face, and stands a narrow gap off the opening. Hinge lines and poses are given for the animation.
"""
import math

import numpy as np

import anim
import hullgrid as hg
import meshkit

GROUND = -0.3665 * 7.2                    # the pad soles rest here
THICK, GAP = 0.045, 0.0025                # door thickness, and its gap to the hull all round
COL = "06_Trappes"


def skin_panel(grid, name, mask, side, paint, inner):
    """Door from the cells `mask` (na-1, nb-1) of the half grid.

    side: +1 port leaf, -1 starboard leaf, 0 one panel across the keel (the mask must reach it).
    The outer face keeps the hull's normals, so the closed door shades as the skin round it.
    """
    na, nb = grid.na, grid.nb
    ia, ib = np.nonzero(mask)
    quads = np.stack([ia * nb + ib, (ia + 1) * nb + ib, (ia + 1) * nb + ib + 1, ia * nb + ib + 1], axis=1)
    uv_half = np.stack([grid.lam, grid.girth], axis=-1).reshape(-1, 2)
    pts, nrm = grid.points.reshape(-1, 3), grid.normals.reshape(-1, 3)
    flip = np.array([-1.0, 1.0, 1.0])
    if side == 0:                         # both halves, welded on the keel row
        keel = np.arange(na) * nb + nb - 1
        twin = np.arange(na * nb) + na * nb
        twin[keel] = keel
        quads = np.vstack([quads, twin[quads]])
        pts, nrm = np.vstack([pts, pts * flip]), np.vstack([nrm, nrm * flip])
        uv_half = np.vstack([uv_half, uv_half * (1.0, -1.0)])
    elif side < 0:
        pts, nrm = pts * flip, nrm * flip
    used = np.unique(quads)
    remap = np.full(len(pts), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    return shell(name, pts[used], nrm[used], remap[quads], uv_half[used], paint, inner, COL, THICK)


def shell(name, pts, nrm, quads, uv, paint, inner, col, thick):
    """Thick panel from a sheet of quads: outer face with the given normals, edge return, inner face.

    thick: one depth, or one per node. uv: one per node, or None for box UVs.
    """
    pts, quads = np.array(pts, dtype=float), np.asarray(quads, dtype=np.int64)
    n = len(pts)
    thick = np.broadcast_to(np.asarray(thick, dtype=float), (n,))[:, None]

    # Boundary: the edges used by one face. Its nodes step in by the gap, towards the faces they belong to.
    edges = np.sort(np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)]), axis=1)
    uniq, count = np.unique(edges, axis=0, return_counts=True)
    border = uniq[count == 1]
    centre = pts[quads].mean(axis=1)
    pull = np.zeros((n, 3))
    for k in range(4):
        np.add.at(pull, quads[:, k], centre - pts[quads[:, k]])
    pull -= nrm * (pull * nrm).sum(axis=1, keepdims=True)
    pull /= np.maximum(np.linalg.norm(pull, axis=1, keepdims=True), 1e-12)
    rim = np.unique(border)
    pts[rim] += pull[rim] * GAP

    # Edge return and inner face.
    top = np.full(n, -1, dtype=np.int64)
    top[rim] = n + np.arange(len(rim))
    bottom = top + len(rim)
    inner_id = np.arange(n) + n + 2 * len(rim)
    verts = np.vstack([pts, pts[rim], pts[rim] - nrm[rim] * thick[rim], pts - nrm * thick])
    normals = np.vstack([nrm, -pull[rim], -pull[rim], -nrm])
    uvs = None if uv is None else np.vstack([uv, uv[rim], uv[rim], uv])
    faces = quads.tolist()
    faces += [[top[a], top[b], bottom[b], bottom[a]] for a, b in border]
    faces += inner_id[quads][:, ::-1].tolist()
    slots = [0] * len(quads) + [1] * (len(border) + len(quads))
    return meshkit.mesh_object(name, verts, faces, col, materials=[paint, inner], face_mats=np.array(slots),
                               normals=normals, uvs=uvs)


def gear_doors(grid):
    """Every gear door leaf: name -> (two points of its hinge line, fore then aft).

    A leaf hinges on its long edge away from the opening's middle: the nose leaves on the well's
    side, the main leaves on the well's outboard or inboard edge. Starboard leaves end in _D.
    """
    out = {}
    for key, (a0, a1, b0, b1) in grid.door_leaves().items():
        b = b0 if key.startswith("Avant") or key.endswith("Ext") else b1
        for tag, sign in (("G", 1.0), ("D", -1.0)):
            scale = np.array([sign, 1.0, 1.0])
            out[f"Trappe_Train_{key}_{tag}"] = (grid.points[a0 + 1, b] * scale, grid.points[a1 - 1, b] * scale)
    return out


def hatch_axis(grid):
    """A point of the rear hatch's hinge line, which runs along X under its front edge."""
    front = grid.points[grid.col["h0"], hg.B_WELL:]
    return np.array([0.0, float(front[-1, 1]), float(front[:, 2].min()) - 0.002])


def hatch_angle(grid):
    """Opening angle of the rear hatch, radians: its rear edge comes down to the ground."""
    axis = hatch_axis(grid)
    tip = grid.points[grid.col["h1"], hg.B_MAX] - axis
    lo, hi = 0.0, 0.5 * math.pi
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        z = axis[2] - tip[1] * math.sin(mid) + tip[2] * math.cos(mid)
        lo, hi = (mid, hi) if z > GROUND + 0.012 else (lo, mid)
    return 0.5 * (lo + hi)


def hatch_pose(grid):
    """Pose of the rear hatch and of everything it carries: closed at u = 0, on the ground at u = 1."""
    axis, angle = hatch_axis(grid), hatch_angle(grid)
    return lambda u: anim.about(axis, (1.0, 0.0, 0.0), -angle * anim.ease(u))


def build(grid, mats):
    """The doors, built closed. The gear module keys the gear doors; the hatch is keyed here."""
    cells = grid.cells()
    doors = []
    for key, (a0, a1, b0, b1) in grid.door_leaves().items():
        mask = np.zeros_like(cells["doors"])
        mask[a0:a1, b0:b1] = True
        for tag, sign in (("G", 1.0), ("D", -1.0)):
            doors.append(skin_panel(grid, f"Trappe_Train_{key}_{tag}", mask, sign, mats["belly"], mats["dark"]))
    hatch = skin_panel(grid, "Trappe_Arriere", cells["hatch"], 0, mats["teal"], mats["dark"])
    anim.bake(hatch, "Trappe_Arriere", hatch_pose(grid))
    return doors + [hatch]
