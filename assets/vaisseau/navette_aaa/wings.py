"""Telescopic wings of the Navette AAA: the shoulder crest slides out and the skin follows it.

The crest above each thruster moves outwards by the span law. The shoulder band (E1 to E2)
moves as one piece; the upper flank, and the band down to the thruster's lip, stretch with it.
In plan the crest draws a rounded delta: it leaves the fuselage tangentially, reaches its span
at the tip, and rounds off into the trailing edge. Between the tip stations the crest moves
rigidly: the navigation lights ride there.

The extension is a shape key "Aile" of the hull skin and of its seams, keyed over the clip
"Ailes" together with the lights. The same principle drives the Navette in the game: rigid
slides, and a skin that carries the displacement.
"""
import copy

import bpy
import numpy as np

import anim
import hullgrid as hg

SPAN = 1.50                                  # outward travel of the crest at the tip, metres
Y_ROOT, Y_TIP0, Y_TIP1, Y_TRAIL = 0.60, 4.30, 5.00, 5.80   # leading edge root, tip, trailing edge root
ROW_TOP, ROW_LOW = 28, 41                    # the stretch fades out at these rows: upper flank, thruster lip
STAGE_ROWS = (33, 40)                        # seams that mark the telescopic stages, over and under the wing
Y_LIGHT = 0.5 * (Y_TIP0 + Y_TIP1)            # the navigation lights sit on the rigid tip


def span_law(y):
    """Outward travel of the crest at station y, as a share of SPAN: a rounded delta in plan."""
    y = np.asarray(y, dtype=float)
    u = np.clip((y - Y_ROOT) / (Y_TIP0 - Y_ROOT), 0.0, 1.0)
    lead = u * u * (3.0 - 2.0 * u)                                   # tangent to the fuselage at both ends
    v = np.clip((y - Y_TIP1) / (Y_TRAIL - Y_TIP1), 0.0, 1.0)
    trail = np.sqrt(np.clip(1.0 - v ** 2.2, 0.0, 1.0))               # a round tip, then a steep trailing edge
    return np.where(y < Y_TIP1, lead, trail)


def row_weight(b):
    """Share of the crest's travel taken by grid row b: 1 on the shoulder band, easing to 0 above and below."""
    b = np.asarray(b, dtype=float)
    up = np.clip((b - ROW_TOP) / (hg.B_E1 - ROW_TOP), 0.0, 1.0)
    low = np.clip((ROW_LOW - b) / (ROW_LOW - hg.B_E2), 0.0, 1.0)
    w = np.where(b < hg.B_E1, up, np.where(b > hg.B_E2, low, 1.0))
    return w * w * (3.0 - 2.0 * w)


def extend(grid, u):
    """Move the port half grid to wing extension u in [0, 1], in place; recompute the moved normals."""
    if u <= 0.0:
        return
    y = grid.points[:, hg.B_E1, 1]
    travel = u * SPAN * span_law(y)[:, None] * row_weight(np.arange(grid.nb))[None, :]
    moved = travel > 1e-6
    grid.points[..., 0] += travel
    p = grid.points
    n = np.cross(np.gradient(p, axis=1), np.gradient(p, axis=0))
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-12)
    n = np.where((n * grid.normals).sum(axis=2, keepdims=True) < 0.0, -n, n)
    grid.normals[moved] = n[moved]


def columns(grid):
    """Grid columns of the wing's root and trailing edge, along the shoulder."""
    y = grid.points[:, hg.B_E1, 1]
    return int(np.searchsorted(y, Y_ROOT)), int(np.searchsorted(y, Y_TRAIL))


def under_cells(grid):
    """Cells of the wing's underside, between the shoulder's lower edge and the thruster's lip: teal."""
    a0, a1 = columns(grid)
    mask = np.zeros((grid.na - 1, grid.nb - 1), dtype=bool)
    mask[a0:a1, hg.B_E2:ROW_LOW] = True
    return mask


def build(grid, morphs, lights):
    """Key the wings over the clip "Ailes".

    morphs: (object, maker) pairs; maker(grid) builds the object again on a grid. The twin built
    on the fully extended grid becomes the object's shape key "Aile", and is then removed.
    lights: objects on the rigid tip stations, keyed by translation, outwards on their side.
    """
    out = copy.copy(grid)
    out.points, out.normals = grid.points.copy(), grid.normals.copy()
    extend(out, 1.0)
    for obj, maker in morphs:
        twin = maker(out)
        co = np.zeros(len(twin.data.vertices) * 3)
        twin.data.vertices.foreach_get("co", co)
        assert len(co) == 3 * len(obj.data.vertices), f"{obj.name}: its twin has another topology"
        mesh = twin.data
        bpy.data.objects.remove(twin, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        obj.shape_key_add(name="Basis", from_mix=False)
        obj.shape_key_add(name="Aile", from_mix=False).data.foreach_set("co", co)
        anim.bake_value(obj.data.shape_keys, 'key_blocks["Aile"].value', "Ailes", anim.ease)
    for obj in lights:
        co = np.zeros(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", co)
        side = 1.0 if co.reshape(-1, 3)[:, 0].mean() > 0.0 else -1.0
        anim.bake(obj, "Ailes", lambda u, side=side: anim.shift((side * SPAN * anim.ease(u), 0.0, 0.0)))
