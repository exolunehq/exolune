"""Canopy frames of the Navette AAA: seal, amber trim, arch hoop, mullions, and the bosses of both poles.

Every member is a profile swept along a line of the hull skin, so it follows the surface exactly.
"""
import math

import bpy
import numpy as np

import hullgrid as hg
import meshkit
from surface import T1

FLIP = np.array([-1.0, 1.0, 1.0])


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def sweep(name, path, normal, profile, col, materials, slot=None, across=None, cap=True, sharp_deg=40.0,
          closed=False, ribbon=False):
    """Sweep a 2D profile along a skin line.

    path, normal: (n, 3) points and outward skin normals.
    profile: (k, 2) of (across, up) in metres, or (n, k, 2) to vary it along the path.
    across: (n, 3) optional direction that positive "across" must follow (for example towards the glass).
    slot: (k,) material slot of each profile segment.
    closed: also build the profile's last-to-first segment (a free-standing body, not a strip on the skin).
    ribbon: a flat strip; its faces are wound to look along the skin normal.
    """
    path, normal, profile = np.asarray(path, float), unit(np.asarray(normal, float)), np.asarray(profile, float)
    n = len(path)
    stations = profile if profile.ndim == 3 else np.broadcast_to(profile, (n,) + profile.shape)
    profile = stations[n // 2]                 # one profile per path point is allowed; the middle one leads
    k = len(profile)
    loop = n > 3 and np.allclose(path[0], path[-1], atol=1e-7)     # a closed path: its ends are one point
    if loop:
        path, normal, stations = path[:-1], normal[:-1], stations[:-1]
        across = None if across is None else np.asarray(across, float)[:-1]
        n -= 1
        cap = False
        tan = unit(np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0))
    else:
        tan = np.empty_like(path)
        tan[1:-1] = path[2:] - path[:-2]
        tan[0], tan[-1] = path[1] - path[0], path[-1] - path[-2]
        tan = unit(tan)
    side = np.cross(normal, tan)
    if across is not None:
        side = np.where((side * across).sum(axis=1, keepdims=True) < 0.0, -side, side)
    side = unit(side)
    up = unit(np.cross(tan, side))
    up = np.where((up * normal).sum(axis=1, keepdims=True) < 0.0, -up, up)
    # At a corner the section plane lies askew: widen it there, so the strip keeps its width.
    mitre = 2.0 / np.maximum(np.linalg.norm(unit(np.roll(path, -1, axis=0) - path) + unit(path - np.roll(path, 1, axis=0)),
                                            axis=1), 1.2)
    if not loop:
        mitre[0] = mitre[-1] = 1.0
    verts = (path[:, None, :] + side[:, None, :] * stations[:, :, 0:1] * mitre[:, None, None]
             + up[:, None, :] * stations[:, :, 1:2])
    idx = np.arange(n * k).reshape(n, k)
    # The profile's last-to-first segment lies under the skin: it is never built.
    faces, face_slot = [], []
    rows_a = idx if loop else idx[:-1]
    rows_b = np.roll(idx, -1, axis=0) if loop else idx[1:]
    for j in range(k if closed else k - 1):
        quads = np.stack([rows_a[:, j], rows_b[:, j], rows_b[:, (j + 1) % k], rows_a[:, (j + 1) % k]], axis=1)
        faces.extend(quads.tolist())
        face_slot.extend([0 if slot is None else int(slot[j])] * len(rows_a))
    if cap:                                   # close both ends with quads across the profile
        for ring in (idx[0], idx[-1][::-1]):
            for j in range(k // 2 - 1):
                faces.append([int(ring[j]), int(ring[j + 1]), int(ring[k - 2 - j]), int(ring[k - 1 - j])])
                face_slot.append(0 if slot is None else int(slot[0]))
    # Outward winding: the frame's handedness against the profile's turning sense.
    handed = float(np.dot(np.cross(tan[n // 2], side[n // 2]), up[n // 2]))
    area = 0.5 * float(np.sum(profile[:-1, 0] * profile[1:, 1] - profile[1:, 0] * profile[:-1, 1])
                       + profile[-1, 0] * profile[0, 1] - profile[0, 0] * profile[-1, 1])
    if handed * area > 0.0:
        faces = [f[::-1] for f in faces]
    length = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    girth = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(profile, axis=0), axis=1))])
    uvs = np.stack(np.broadcast_arrays(length[:, None], girth[None, :]), axis=-1).reshape(-1, 2)
    guide = np.repeat(up, k, axis=0) if ribbon else None
    obj = meshkit.mesh_object(name, verts.reshape(-1, 3), faces, col, materials=materials,
                              face_mats=np.array(face_slot), uvs=uvs, orient=guide)
    obj.data.set_sharp_from_angle(angle=math.radians(sharp_deg))
    return obj


def rounded_strip(half_hull, half_glass, height, sink=0.002, bevel=0.0025):
    """Low strip with bevelled shoulders: 'across' runs from the hull side (negative) to the glass side."""
    return np.array([(-half_hull, -sink), (-half_hull, height - bevel), (-half_hull + bevel, height),
                     (half_glass - bevel, height), (half_glass, height - bevel), (half_glass, -sink)])


def _mirror_path(points, normals, extra=None):
    """Port path, then its starboard twin walked back, sharing the centreline node the port path ends on."""
    p = np.vstack([points, (points[:-1] * FLIP)[::-1]])
    n = np.vstack([normals, (normals[:-1] * FLIP)[::-1]])
    if extra is None:
        return p, n
    return p, n, np.vstack([extra, (extra[:-1] * FLIP)[::-1]])


def outline_path(grid):
    """Glazing outline on the port side, from the keel to the crown of the arch.

    It climbs the prow, turns aft along the sill, rounds the last window and comes back along the
    window tops to the arch. Returns points, normals, the in-skin direction towards the glass at
    every node, and the index of the last sill node.
    """
    c = grid.col
    arch, end = c["arch"], c["end"]
    seq = [(arch, b, arch - 1, b) for b in range(hg.B_MAX, hg.B_SILL, -1)]
    seq.append((arch, hg.B_SILL, arch - 1, hg.B_SILL - 1))         # the hull's corner: glass on three sides
    seq += [(a, hg.B_SILL, a if a < end else a - 1, hg.B_SILL - 1) for a in range(arch + 1, end + 1)]
    k_sill = len(seq) - 1
    seq += [(end, b, end - 1, b if b > hg.B_ROOF else b + 1) for b in range(hg.B_SILL - 1, hg.B_ROOF - 1, -1)]
    seq += [(a, hg.B_ROOF, a if a > arch else a - 1, hg.B_ROOF + 1) for a in range(end - 1, arch - 1, -1)]
    seq += [(arch, b, arch - 1, b) for b in range(hg.B_ROOF - 1, -1, -1)]
    ia, ib, ja, jb = np.array(seq).T
    pts, nrm = grid.points[ia, ib], grid.normals[ia, ib]
    return pts, nrm, grid.points[ja, jb] - pts, k_sill


def post_path(grid, y_of_z, to_centre):
    """A raked post on the upper skin from the sill up, to the window top or to the centreline."""
    m, hull = grid.maps, grid.hull
    s = float(m.s_of_y(y_of_z(-0.6)))
    t_low = None
    pts = []
    # the post foot: where the raked line meets the sill
    for _ in range(30):
        y = float(m.at(m.y, s))
        z = float(hg.z_sill(y))
        s = float(m.s_of_y(y_of_z(z)))
    y = float(m.at(m.y, s))
    t_foot = float(hull.t_of_z(np.array([s]), np.array([float(hg.z_sill(y))]))[0])
    if to_centre:
        t_end = 0.0
    else:
        s_top = s
        for _ in range(30):
            y_top = float(m.at(m.y, s_top))
            s_top = float(m.s_of_y(y_of_z(float(hg.z_window_top(y_top)))))
        y_top = float(m.at(m.y, s_top))
        t_end = float(hull.t_of_z(np.array([s_top]), np.array([float(hg.z_window_top(y_top))]))[0])
    tt = np.linspace(t_foot, t_end, 90)
    ss = np.full(tt.shape, s)
    for _ in range(12):                               # the section through each height of the raked line
        z = hull.eval(ss, tt)[:, 2]
        ss = m.s_of_y(y_of_z(z))
    return hull.eval(ss, tt, normals=True)


def canopy(grid, mats):
    col = "03_Verriere"
    pts, nrm, to_glass, k_sill = outline_path(grid)
    path, normal, across = _mirror_path(pts, nrm, to_glass)        # closed: keel, port, crown, starboard, keel
    objs = []
    # Black seal over the glass edge, all round.
    objs.append(sweep("Verriere_Joint", path, normal, rounded_strip(0.011, 0.011, 0.0035), col, [mats["rubber"]],
                      across=across))
    # Amber line on the hull side of the seal, along the rear edge, the top edge and the roof front.
    trim = rounded_strip(0.021, -0.012, 0.0028, bevel=0.0012)
    lo, hi = k_sill - 4, len(path) - (k_sill - 4)
    lines = [sweep("Lisere_Toit", path[lo:hi], normal[lo:hi], trim, col, [mats["amber"]], across=across[lo:hi], cap=True)]
    # The same line parts the teal prow band from the white flank, from sill to sill under the keel.
    p2 = grid.col["p2"]
    rows = np.arange(hg.B_SILL, hg.B_MAX + 1)
    pp, pn, pa = _mirror_path(grid.points[p2, rows], grid.normals[p2, rows],
                              grid.points[p2 - 1, rows] - grid.points[p2, rows])
    lines.append(sweep("Lisere_Proue", pp, pn, rounded_strip(0.0045, 0.0045, 0.0028, bevel=0.0012), col,
                       [mats["amber"]], across=pa, cap=True))
    objs.append(meshkit.join(lines, "Verriere_Lisere"))
    # Arch hoop from sill to sill over the crown, and three mullions per side.
    hoop_profile = np.array([(-0.036, -0.002), (-0.036, 0.007), (-0.029, 0.013), (-0.010, 0.013), (-0.008, 0.011),
                             (0.008, 0.011), (0.010, 0.013), (0.029, 0.013), (0.036, 0.007), (0.036, -0.002)])
    arch = lambda z: hg.ARCH_Y - hg.ARCH_RAKE * (hg.CROWN_Z - z)
    p, n = post_path(grid, arch, True)
    hp, hn = _mirror_path(p, n)
    # Each foot narrows to the width of the seal it lands on.
    run = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(hp, axis=0), axis=1))])
    foot = 0.32 + 0.68 * hg.smoothstep(0.0, 0.16, np.minimum(run, run[-1] - run))
    hoop = hoop_profile[None, :, :] * np.stack([foot, 0.45 + 0.55 * foot], axis=1)[:, None, :]
    objs.append(sweep("Verriere_Arceau", hp, hn, hoop, col, [mats["dark"]], cap=True))
    post_profile = np.array([(-0.020, -0.002), (-0.020, 0.005), (-0.015, 0.009), (0.015, 0.009), (0.020, 0.005),
                             (0.020, -0.002)])
    parts = []
    for k, y0 in enumerate(hg.MULLION_Y):
        f = lambda z, y0=y0: y0 - hg.MULLION_RAKE * (hg.CROWN_Z - z)
        p, n = post_path(grid, f, False)
        for sign in (1.0, -1.0):
            scale = np.array([sign, 1.0, 1.0])
            parts.append(sweep(f"Verriere_Montant_{k}_{'G' if sign > 0 else 'D'}", p * scale, n * scale,
                               post_profile, col, [mats["dark"]], cap=True))
    objs.append(meshkit.join(parts, "Verriere_Montants"))
    return objs


def boss(grid, mats, name, mat, stern=False, s_skirt=1.75, s_rim=1.0, n=16, power=2.6):
    """Cap over a pole of the hull, where every line of the skin converges.

    The hull's own tip is a small blunt lens. The cap gives it a designed end: a superellipse
    dome, joined to the skin by a short skirt that takes the hull's section. The dome is a square
    grid mapped to the disc, so it has no pole of its own. s_skirt and s_rim count from the pole.
    """
    hull = grid.hull
    tip, out = (hull.stern_tip, 1.0) if stern else (hull.tip, -1.0)
    if stern:
        s_skirt, s_rim = hull.s_max - s_skirt, hull.s_max - s_rim
    n_ring = 4 * n
    theta = np.arange(n_ring) / n_ring * 2.0 * np.pi           # 0 on top, growing to port

    def section(s_at, lift):
        """Hull ring at s_at, lifted off the skin, sampled by angle round its own centre."""
        t = np.linspace(0.0, 1.0, 500)
        half, nrm = hull.eval(np.full(t.shape, s_at), t, normals=True)
        half = half + nrm * lift
        ring = np.vstack([half, (half[1:-1] * FLIP)[::-1]])
        centre = np.array([0.0, float(half[:, 1].mean()), 0.5 * (half[0, 2] + half[-1, 2])])
        ang = np.unwrap(np.arctan2(ring[:, 0], ring[:, 2] - centre[2]))
        return np.stack([np.interp(theta, ang, ring[:, k], period=2.0 * np.pi) for k in range(3)], axis=-1), centre

    skirt, _ = section(s_skirt, 0.0005)
    inner, centre = section(s_rim, 0.0)
    a = np.abs(inner[:, 0]).max() + 0.012
    b = 0.5 * (inner[:, 2].max() - inner[:, 2].min()) + 0.012

    def oval(ang, scale=1.0):
        """Superellipse rim of the dome, in the plane of the hull's first ring."""
        c, sn = np.cos(ang), np.sin(ang)
        r = (np.abs(sn / a) ** power + np.abs(c / b) ** power) ** (-1.0 / power)
        return np.stack([scale * r * sn, np.full(np.shape(ang), centre[1]), centre[2] + scale * r * c], axis=-1)

    rim = oval(theta)
    mid = 0.5 * (skirt + rim) + (rim - centre) / np.linalg.norm(rim - centre, axis=1, keepdims=True) * 0.004
    rings = np.array([skirt, mid, rim])
    ridx = np.arange(3 * n_ring).reshape(3, n_ring)
    faces = [[ridx[k, i], ridx[k, (i + 1) % n_ring], ridx[k + 1, (i + 1) % n_ring], ridx[k + 1, i]]
             for k in range(2) for i in range(n_ring)]
    verts = rings.reshape(-1, 3)
    # Dome: the disc grid, its boundary welded to the rim ring.
    g = np.linspace(-1.0, 1.0, n + 1)
    u, v = np.meshgrid(g, g, indexing="ij")
    du, dv = u * np.sqrt(1.0 - 0.5 * v * v), v * np.sqrt(1.0 - 0.5 * u * u)
    rho = np.clip(np.hypot(du, dv), 0.0, 1.0)
    ang = np.mod(np.arctan2(du, dv), 2.0 * np.pi)
    depth = abs(tip[1] - centre[1]) + 0.02
    dome = oval(ang, rho)
    dome[..., 1] = centre[1] + out * depth * np.clip(1.0 - rho ** 2.4, 0.0, 1.0) ** 0.6
    did = np.full((n + 1, n + 1), -1, dtype=np.int64)
    edge = np.zeros((n + 1, n + 1), dtype=bool)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    did[edge] = ridx[2, np.rint(ang[edge] / (2.0 * np.pi) * n_ring).astype(int) % n_ring]
    did[~edge] = len(verts) + np.arange(int((~edge).sum()))
    verts = np.vstack([verts, dome[~edge]])
    guide = verts - (centre - np.array([0.0, 0.25 * out, 0.0]))
    skirt_faces = meshkit.wind(verts, faces, guide)
    dome_faces = meshkit.wind(verts, meshkit.grid_faces(did), guide)
    slots = [0] * len(skirt_faces) + [1] * len(dome_faces)
    return meshkit.mesh_object(name, verts, skirt_faces + dome_faces, "01_Exterieur_Coque",
                               materials=[mats["dark"], mat], face_mats=np.array(slots))


def opening_returns(grid, mats, depth=0.054):
    """Inward return of the hull skin round the canopy opening: the skin gets a visible thickness."""
    pts, nrm, to_glass, _ = outline_path(grid)
    path, normal, across = _mirror_path(pts, nrm, to_glass)
    verts = np.vstack([path, path - normal * depth])
    n = len(path)
    faces = [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
    return meshkit.mesh_object("Verriere_Feuillure", verts, faces, "03_Verriere", materials=[mats["dark"]],
                               orient=np.vstack([across, across]))
