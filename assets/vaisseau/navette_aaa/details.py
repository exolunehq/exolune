"""Hull details of the Navette AAA: seams, lights, the flank light slot, the dorsal radiator panels.

Every detail lies on the skin: it is swept along grid lines or mapped from a small side-view chart.
"""
import math

import bmesh
import bpy
import numpy as np

import frames
import hullgrid as hg
import meshkit
from surface import T1, T2

FLIP = frames.FLIP
COL = "01_Exterieur_Coque"


def _both(make):
    """Run a port-side builder for both sides: make(sign) -> object."""
    return [make(1.0), make(-1.0)]


def _col_at(grid, y):
    return int(np.argmin(np.abs(grid.points[:, hg.B_E1, 1] - y)))


def _ribbon(name, pts, nrm, width, height, mat, sign=1.0, col=COL):
    scale = np.array([sign, 1.0, 1.0])
    profile = np.array([(-0.5 * width, height), (0.5 * width, height)])
    return frames.sweep(name, pts * scale, nrm * scale, profile, col, [mat], cap=False, ribbon=True)


def seams(grid, mats):
    """Panel breaks: sealed gaps along chosen lines of the skin grid."""
    c, parts = grid.col, []
    cells = grid.cells()
    open_cell = cells["glass"] | cells["mouth"] | cells["socket"] | cells["doors"] | cells["hatch"]
    width, lift = 0.0035, 0.0006

    def run(index_pairs, tag):
        """One ribbon per stretch of a grid line that stays on the opaque skin."""
        stretch = []
        for a, b, free in index_pairs:
            if free:
                stretch.append((a, b))
            elif stretch:
                flush(stretch, tag)
                stretch = []
        flush(stretch, tag)

    def flush(stretch, tag):
        if len(stretch) < 3:
            return
        ia, ib = np.array(stretch).T
        for sign in (1.0, -1.0):
            parts.append(_ribbon(f"Joint_{tag}_{len(parts)}", grid.points[ia, ib], grid.normals[ia, ib],
                                 width, lift, mats["seam"], sign))

    def col_free(a, b):
        """A column node is on the opaque skin if neither cell beside it along the row is an opening."""
        b0, b1 = max(b - 1, 0), min(b, grid.nb - 2)
        a0, a1 = max(a - 1, 0), min(a, grid.na - 2)
        return not (open_cell[a0, b0] or open_cell[a0, b1] or open_cell[a1, b0] or open_cell[a1, b1])

    y_col = lambda y: _col_at(grid, y)
    rings = [c["w1"] + 3, c["end"] + 9, c["c0"] - 14, c["c1"] + 12, y_col(4.75), y_col(5.72)]
    for a in rings:
        run([(a, b, col_free(a, b)) for b in range(1, grid.nb - 1)], f"C{a}")
    rows = [(hg.B_SILL, c["end"] + 2, y_col(5.72)), (21, c["end"] + 9, y_col(5.72)),
            (hg.B_BELT1 + 8, c["w0"] - 1, c["c1"] + 12)]
    for b, a0, a1 in rows:
        run([(a, b, col_free(a, b)) for a in range(a0, a1 + 1)], f"R{b}")
    return meshkit.join(parts, "Coque_Joints")


def belt_light(grid, mats):
    """Amber line under the teal belt, from the prow to the thrusters, as in the concept."""
    a0, a1 = grid.col["p2"] + 2, grid.col["c0"] - 4
    pts, nrm = grid.points[a0:a1, hg.B_BELT1], grid.normals[a0:a1, hg.B_BELT1]
    profile = np.array([(-0.007, -0.001), (-0.007, 0.002), (-0.004, 0.0035), (0.004, 0.0035), (0.007, 0.002),
                        (0.007, -0.001)])
    parts = [frames.sweep(f"Lum_{k}", pts * s, nrm * s, profile, COL, [mats["amber"]], cap=True)
             for k, s in enumerate((np.array([1.0, 1.0, 1.0]), FLIP))]
    return meshkit.join(parts, "Coque_Lumiere_Ceinture")


def _chart_points(grid, yd, lift, lower=True):
    """Skin points and normals of chart coordinates: (y, depth below E2) or (y, z) on the upper skin."""
    m = grid.maps
    lam, t = (m.lower if lower else m.upper)(np.asarray(yd, dtype=float).reshape(-1, 2))
    pts, nrm = grid.hull.eval(m.s_of_lam(lam), t, normals=True)
    return (pts + nrm * lift).reshape(np.shape(yd)[:-1] + (3,)), nrm.reshape(np.shape(yd)[:-1] + (3,))


def _pill(y0, y1, height, n_side=60, n_end=10):
    """Closed outline (y, v) of a pill from y0 to y1, height tall, centred on v = 0; the first point is repeated."""
    r = 0.5 * height
    ang = np.linspace(-0.5 * np.pi, 0.5 * np.pi, n_end)
    top = np.stack([np.linspace(y0 + r, y1 - r, n_side), np.full(n_side, r)], axis=1)
    right = np.stack([y1 - r + r * np.cos(ang), -r * np.sin(ang)], axis=1)
    bottom = np.stack([np.linspace(y1 - r, y0 + r, n_side), np.full(n_side, -r)], axis=1)
    left = np.stack([y0 + r - r * np.cos(ang), r * np.sin(ang)], axis=1)
    loop = np.vstack([top, right[1:], bottom[1:], left[1:]])
    return np.vstack([loop, loop[:1]])


def slot(grid, mats, name, y0, y1, base, height, frame_mat, bed_mat, dashes=0):
    """Rounded slot on the upper skin of both flanks: a frame, a bed just proud of the skin, amber dashes.

    base(y): height of the slot's centre line in side view. The frame narrows with small slots.
    """
    r = 0.5 * height
    loop = _pill(y0, y1, height, n_side=max(12, int((y1 - y0) / 0.025)))
    chart = lambda yo: np.stack([yo[..., 0], base(yo[..., 0]) + yo[..., 1]], axis=-1)
    k = min(1.0, height / 0.085)
    frame = np.array([(-0.012, -0.0002), (-0.012, 0.003), (-0.009, 0.005), (0.006, 0.005), (0.009, 0.003),
                      (0.009, 0.0005)]) * np.array([k, 0.5 + 0.5 * k])

    def side(sign):
        scale = np.array([sign, 1.0, 1.0])
        pts, nrm = _chart_points(grid, chart(loop), 0.0, lower=False)
        centre = _chart_points(grid, chart(np.array([[0.5 * (y0 + y1), 0.0]])), 0.0, lower=False)[0][0]
        ring = frames.sweep(f"{name}_Cadre", pts * scale, nrm * scale, frame, COL, [frame_mat],
                            across=(centre[None, :] - pts) * scale, cap=False)
        u = np.linspace(y0 + 0.2 * r, y1 - 0.2 * r, max(8, int((y1 - y0) / 0.022)))
        v = np.linspace(-0.78 * r, 0.78 * r, 4)
        bed, bed_n = _chart_points(grid, chart(np.stack(np.meshgrid(u, v, indexing="ij"), axis=-1)), 0.0008,
                                   lower=False)
        idx = np.arange(bed.shape[0] * bed.shape[1]).reshape(bed.shape[:2])
        parts = [ring, meshkit.mesh_object(f"{name}_Fond", bed.reshape(-1, 3) * scale, meshkit.grid_faces(idx), COL,
                                           materials=[bed_mat], normals=bed_n.reshape(-1, 3) * scale)]
        prof = np.array([(-0.011, -0.0005), (-0.011, 0.0015), (-0.008, 0.003), (0.008, 0.003), (0.011, 0.0015),
                         (0.011, -0.0005)])
        for j in range(dashes):
            a = y0 + 0.16 + j * (y1 - y0 - 0.32) / dashes
            line = np.stack([np.linspace(a, a + 0.17, 12), np.zeros(12)], axis=1)
            p, n = _chart_points(grid, chart(line), 0.0012, lower=False)
            parts.append(frames.sweep(f"{name}_Trait_{j}", p * scale, n * scale, prof, COL, [mats["amber"]], cap=True))
        return meshkit.join(parts, f"{name}_{'G' if sign > 0 else 'D'}")

    return _both(side)


def flank_slot(grid, mats, y0=-2.95, y1=-1.40, drop=0.19, height=0.085):
    """Light slot on the flank, parallel to the window sill: teal frame, dark bed, amber dashes."""
    return slot(grid, mats, "Coque_Fente", y0, y1, lambda y: hg.z_sill(y) - drop, height, mats["teal"], mats["dark"],
                dashes=6)


def button(grid, mats, name, y, z, r=0.017):
    """Round flush sensor on the upper skin of both flanks: a bezel ring round a dark face."""
    p, n = _chart_points(grid, np.array([[y, z]]), 0.0, lower=False)
    p, n = p[0], n[0]
    e1 = np.cross(n, (0.0, 0.0, 1.0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    k = 6
    g = np.linspace(-1.0, 1.0, k + 1)
    u, v = np.meshgrid(g, g, indexing="ij")
    du, dv = u * np.sqrt(1.0 - 0.5 * v * v), v * np.sqrt(1.0 - 0.5 * u * u)     # a square grid on a disc
    face = p + (du[..., None] * e1 + dv[..., None] * e2) * 0.62 * r + n * 0.0012
    theta = np.linspace(0.0, 2.0 * np.pi, 33)
    circle = p + 0.82 * r * (np.cos(theta)[:, None] * e1 + np.sin(theta)[:, None] * e2)
    circle[-1] = circle[0]
    bezel = np.array([(-0.22 * r, -0.001), (-0.22 * r, 0.002), (-0.12 * r, 0.0028), (0.12 * r, 0.0028),
                      (0.22 * r, 0.002), (0.22 * r, -0.001)])
    idx = np.arange((k + 1) ** 2).reshape(k + 1, k + 1)
    objs = []
    for sign in (1.0, -1.0):
        scale = np.array([sign, 1.0, 1.0])
        tag = "G" if sign > 0 else "D"
        disc = meshkit.mesh_object(f"{name}_Face_{tag}", face.reshape(-1, 3) * scale, meshkit.grid_faces(idx), COL,
                                   materials=[mats["dark"]], orient=np.tile(n * scale, ((k + 1) ** 2, 1)))
        ring = frames.sweep(f"{name}_Cerclage_{tag}", circle * scale, np.tile(n * scale, (len(circle), 1)), bezel, COL,
                            [mats["titanium"]], across=(p[None, :] - circle) * scale, cap=False)
        objs.append(meshkit.join([disc, ring], f"{name}_{tag}"))
    return objs


def small_details(grid, mats):
    """The concept's small parts aft of the windows: a vent high ahead of the fin and the plate behind
    it, an access panel above the shoulder, and two static ports on each flank."""
    high = lambda y: 0.50 - 0.02 * (y - 0.10)
    objs = slot(grid, mats, "Coque_Event", 0.10, 0.62, high, 0.050, mats["dark"], mats["panel"])
    objs += slot(grid, mats, "Coque_Plaque", 0.70, 0.96, high, 0.034, mats["seam"], mats["belly"])
    objs += slot(grid, mats, "Coque_Trappe_Service", 0.25, 0.60, lambda y: np.full(np.shape(y), -0.17), 0.050,
                 mats["seam"], mats["belly"])
    objs += button(grid, mats, "Coque_Prise_Statique_Av", -0.32, 0.00)
    objs += button(grid, mats, "Coque_Prise_Statique_Ar", 1.40, 0.10)
    return objs


def nav_lights(grid, mats):
    """Port red and starboard green lenses set in the shoulder face at the widest point."""
    objs = []
    a = _col_at(grid, 2.35)
    t_mid = 0.5 * (T1 + T2)
    s0 = float(grid.s[a, hg.B_E1])
    n = 10
    g = np.linspace(-1.0, 1.0, n + 1)
    u, v = np.meshgrid(g, g, indexing="ij")
    du, dv = u * np.sqrt(1.0 - 0.5 * v * v), v * np.sqrt(1.0 - 0.5 * u * u)     # a square grid on a disc
    radius = np.clip(np.hypot(du, dv), 0.0, 1.0)
    pts, nrm = grid.hull.eval(s0 + du * 0.24, t_mid + dv * 0.36 * (T2 - T1), normals=True)
    lens = pts + nrm * (0.011 * np.sqrt(1.0 - radius ** 2) - 0.0006)[..., None]
    idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    rim = np.concatenate([idx[:, 0], idx[-1, 1:], idx[-2::-1, -1], idx[0, -2:0:-1], idx[:1, 0]])
    bezel = np.array([(-0.007, -0.001), (-0.007, 0.003), (-0.004, 0.005), (0.003, 0.005), (0.005, 0.003),
                      (0.005, -0.002)])
    centre = pts.reshape(-1, 3).mean(axis=0)
    for sign, mat in ((1.0, mats["nav_red"]), (-1.0, mats["nav_green"])):
        scale = np.array([sign, 1.0, 1.0])
        side = "G" if sign > 0 else "D"
        glass = meshkit.mesh_object(f"Feu_Lentille_{side}", lens.reshape(-1, 3) * scale, meshkit.grid_faces(idx), COL,
                                    materials=[mat], orient=nrm.reshape(-1, 3) * scale)
        rp, rn = pts.reshape(-1, 3)[rim], nrm.reshape(-1, 3)[rim]
        ring = frames.sweep(f"Feu_Cerclage_{side}", rp * scale, rn * scale, bezel, COL, [mats["dark"]],
                            across=(centre[None, :] - rp) * scale, cap=False)
        objs.append(meshkit.join([glass, ring], f"Feu_Nav_{side}"))
    return objs


def radiators(grid, mats, y0=3.65, y1=5.80, x0=0.50, x1=1.12):
    """Dorsal radiator panels beside the fin: a teal glazed plate with a frame and fine slats."""
    m, hull = grid.maps, grid.hull
    ny, nx = 60, 9
    ys = np.linspace(y0, y1, ny)
    taper = 1.0 - 0.30 * (ys - y0) / (y1 - y0)                 # the panel narrows with the deck
    fr = np.linspace(0.0, 1.0, nx)
    xs = x0 * taper[:, None] + (x1 - x0) * taper[:, None] * fr[None, :] + 0.10 * (1 - taper[:, None])
    s = m.s_of_y(ys)
    # the upper-skin parameter where the section reaches each x
    t = np.zeros((ny, nx))
    lo, hi = np.zeros((ny, nx)), np.full((ny, nx), T1)
    ss = np.repeat(s[:, None], nx, axis=1)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        below = hull.eval(ss, mid)[..., 0] < xs
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    t = 0.5 * (lo + hi)
    pts, nrm = hull.eval(ss, t, normals=True)

    def side(sign):
        scale = np.array([sign, 1.0, 1.0])
        plate = pts + nrm * 0.0015
        idx = np.arange(ny * nx).reshape(ny, nx)
        parts = [meshkit.mesh_object("Rad_Plaque", plate.reshape(-1, 3) * scale, meshkit.grid_faces(idx),
                                     "02_Exterieur_Appendices", materials=[mats["panel"]],
                                     normals=nrm.reshape(-1, 3) * scale)]
        loop = np.concatenate([np.arange(ny) * nx, (ny - 1) * nx + np.arange(1, nx),
                               np.arange(ny - 2, -1, -1) * nx + nx - 1, np.arange(nx - 2, -1, -1)])   # closed
        lp, ln = pts.reshape(-1, 3)[loop], nrm.reshape(-1, 3)[loop]
        centre = pts.reshape(-1, 3).mean(axis=0)
        frame = np.array([(-0.014, -0.001), (-0.014, 0.004), (-0.010, 0.007), (0.008, 0.007), (0.012, 0.004),
                          (0.012, -0.001)])
        parts.append(frames.sweep("Rad_Cadre", lp * scale, ln * scale, frame, "02_Exterieur_Appendices",
                                  [mats["teal"]], across=(centre[None, :] - lp) * scale, cap=False))
        slat = np.array([(-0.006, 0.001), (-0.004, 0.006), (0.004, 0.006), (0.006, 0.001)])
        for k in range(3, ny - 2, 3):
            parts.append(frames.sweep(f"Rad_Lame_{k}", plate[k, 1:-1] * scale, nrm[k, 1:-1] * scale, slat,
                                      "02_Exterieur_Appendices", [mats["dark"]], cap=True))
        return meshkit.join(parts, f"Radiateur_Dorsal_{'G' if sign > 0 else 'D'}")

    return _both(side)


def spine_strake(grid, mats, y0=-1.7, y1=2.6):
    """Teal apron on the spine: the fin's leading panel flows forward onto the hull, as in the concept."""
    m, hull = grid.maps, grid.hull
    ny, nx = 70, 9
    ys = np.linspace(y0, y1, ny)
    width = 0.008 + 0.30 * hg.smoothstep(y0, 0.9, ys) ** 1.3 * (1.0 - 0.88 * hg.smoothstep(1.5, y1, ys))
    xs = np.abs(np.linspace(-1.0, 1.0, nx))[None, :] * width[:, None]
    ss = np.repeat(m.s_of_y(ys)[:, None], nx, axis=1)
    lo, hi = np.zeros((ny, nx)), np.full((ny, nx), T1)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        below = hull.eval(ss, mid)[..., 0] < xs
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    pts, nrm = hull.eval(ss, 0.5 * (lo + hi), normals=True)
    left = np.arange(nx) < nx // 2
    pts[:, left] *= FLIP
    nrm[:, left] *= FLIP
    pts = pts + nrm * 0.0007
    idx = np.arange(ny * nx).reshape(ny, nx)
    return meshkit.mesh_object("Coque_Arete_Dorsale", pts.reshape(-1, 3), meshkit.grid_faces(idx), COL,
                               materials=[mats["teal"]], normals=nrm.reshape(-1, 3))


def marking(grid, mats, text="EXOLUNE  NX-04", height=0.115, y0=0.02, z0=0.17):
    """Registration painted on both upper flanks, read from outside on each side."""
    curve = bpy.data.curves.new("Marquage", type="FONT")
    curve.body, curve.size, curve.resolution_u = text, height, 6
    probe = bpy.data.objects.new("Marquage", curve)
    bpy.context.scene.collection.objects.link(probe)
    me = bpy.data.meshes.new_from_object(probe.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(probe, do_unlink=True)
    bpy.data.curves.remove(curve)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    for _ in range(2):                                   # short edges, so the letters follow the skin
        long_edges = [e for e in bm.edges if e.calc_length() > 0.035]
        if long_edges:
            bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    flat = np.array([(v.co.x, v.co.y) for v in bm.verts])
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    length = flat[:, 0].max()
    objs = []
    for sign in (1.0, -1.0):
        along = flat[:, 0] if sign > 0 else length - flat[:, 0]      # starboard reads towards the nose
        yz = np.stack([y0 + along, z0 + flat[:, 1] - 0.04 * along], axis=1)
        pts, nrm = _chart_points(grid, yz, 0.0008, lower=False)
        scale = np.array([sign, 1.0, 1.0])
        objs.append(meshkit.mesh_object(f"Marquage_{'G' if sign > 0 else 'D'}", pts * scale, faces, COL,
                                        materials=[mats["teal"]], normals=nrm * scale))
    return objs


def hatch_light(grid, mats):
    """Amber line along both sides of the rear hatch, on the hull: it shows the way in."""
    c = grid.col
    a = np.arange(c["h0"] + 3, c["h1"] - 2)
    pts, nrm = grid.points[a, hg.B_WELL - 1], grid.normals[a, hg.B_WELL - 1]
    profile = np.array([(-0.006, -0.001), (-0.006, 0.002), (-0.0035, 0.003), (0.0035, 0.003), (0.006, 0.002),
                        (0.006, -0.001)])
    parts = [frames.sweep(f"Lum_{k}", pts * s, nrm * s, profile, COL, [mats["amber"]], cap=True)
             for k, s in enumerate((np.array([1.0, 1.0, 1.0]), FLIP))]
    return meshkit.join(parts, "Coque_Lumiere_Trappe")


def build(grid, mats):
    objs = [seams(grid, mats), belt_light(grid, mats), hatch_light(grid, mats), spine_strake(grid, mats)]
    objs += marking(grid, mats)
    objs += flank_slot(grid, mats) + nav_lights(grid, mats) + radiators(grid, mats) + small_details(grid, mats)
    return objs
