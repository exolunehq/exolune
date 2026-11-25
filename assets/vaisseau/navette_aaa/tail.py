"""Tail of the Navette AAA: the dorsal fin seated on the hull. The stern is the hull's own closure."""
import math

import numpy as np

import anim
import frames
import meshkit
import panels
from surface import T1

FLIP = np.array([-1.0, 1.0, 1.0])

# Fin stations from the validated form: z, leading edge y, trailing edge y, half thickness, teal chord share.
FIN = np.array([
    (0.407, -0.910, 5.200, 0.333, 0.415),      # extrapolated below the skin, so the root always reaches it
    (0.684, 0.000, 5.184, 0.302, 0.36), (0.936, 0.828, 5.170, 0.274, 0.31), (1.116, 1.584, 5.213, 0.245, 0.27),
    (1.332, 2.218, 5.364, 0.223, 0.24), (1.584, 2.750, 5.587, 0.209, 0.23), (1.872, 3.298, 5.825, 0.202, 0.22),
    (2.160, 3.859, 6.070, 0.194, 0.22), (2.362, 4.234, 6.228, 0.187, 0.22),
    # the horizontal cap on top, reaching aft of the trailing edge
    (2.430, 4.300, 6.640, 0.215, 0.22), (2.520, 4.520, 6.800, 0.235, 0.22), (2.606, 4.790, 6.780, 0.200, 0.22),
    (2.655, 5.050, 6.600, 0.125, 0.22), (2.672, 5.300, 6.380, 0.040, 0.22)])
N_TEAL, N_LINE, N_WHITE = 9, 1, 24            # chordwise cells per side: teal, amber line, white
LINE_WIDTH = 0.022
N_SPAN, SPAN_POWER = 46, 0.82                 # span rows, bunched towards the cap
BRAKE_Z = (1.36, 2.20)                        # their span, as heights on the hinge line
BRAKE_ANGLE = math.radians(38.0)              # each panel swings out by this much


def _cr(p0, p1, p2, p3, u):
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def _station(v):
    """Fin station row at span parameter v in [0, len(FIN) - 1], by Catmull-Rom."""
    v = float(np.clip(v, 0.0, len(FIN) - 1))
    i = min(int(v), len(FIN) - 2)
    rows = [FIN[max(i - 1, 0)], FIN[i], FIN[i + 1], FIN[min(i + 2, len(FIN) - 1)]]
    return _cr(*rows, v - i)


def _thickness(u):
    """Half thickness of the fin section at chord fraction u, 1 at its thickest."""
    u = np.clip(u, 0.0, 1.0)
    naca = 5.0 * (0.2969 * np.sqrt(u) - 0.1260 * u - 0.3516 * u ** 2 + 0.2843 * u ** 3 - 0.1015 * u ** 4)
    return (naca + 0.04 * (1.0 - np.abs(2.0 * u - 1.0))) / 0.598


def _white(x):
    """Share of the white chord at x in [0, 1]: cells bunch at both ends, the trailing edge rounds the cap."""
    return 0.6 * x + 0.2 * (1.0 - np.cos(np.pi * x))


def _chord_fractions(share, chord):
    """Chord fractions of one side: the teal part bunched at the leading edge, the amber line, the white."""
    k = np.arange(N_TEAL + 1) / N_TEAL
    teal = share * (1.0 - np.cos(0.5 * np.pi * k))
    line = share + LINE_WIDTH / chord
    white = line + (1.0 - line) * _white(np.arange(1, N_WHITE + 1) / N_WHITE)
    return np.concatenate([teal, [line], white])


# the airbrake panels hinge on the chord column nearest 54 % of the white chord, and reach the trailing edge
BRAKE_COL = N_TEAL + 1 + int(np.argmin(np.abs(_white(np.arange(1, N_WHITE + 1) / N_WHITE) - 0.536))) + 1


def fin(hull, maps, mats):
    n_side = N_TEAL + N_LINE + N_WHITE
    v_top = len(FIN) - 1

    def point(k, v):
        """Port-side point of chord column k at span parameter v."""
        z, y0, y1, half, share = _station(v)
        u = _chord_fractions(share, y1 - y0)[k]
        return np.array([half * _thickness(u), y0 + u * (y1 - y0), z])

    def hull_top(x, y, with_normal=False):
        """Height of the upper skin above the point (x, y); optionally its normal too."""
        s = maps.s_of_y(np.array([y]))
        lo, hi = 0.0, T1
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if hull.eval(s, np.array([mid]))[0, 0] < abs(x):
                lo = mid
            else:
                hi = mid
        p, n = hull.eval(s, np.array([0.5 * (lo + hi)]), normals=True)
        return (float(p[0, 2]), n[0]) if with_normal else float(p[0, 2])

    def meet(k, inside):
        """Span parameter where chord column k crosses the skin, 'inside' metres under it."""
        lo, hi = 0.0, 6.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            p = point(k, mid)
            if p[2] < hull_top(p[0], min(p[1], hull.station_y[-1] - 0.01)) - inside:
                lo = mid
            else:
                hi = mid
        return hi

    # Root: each chord column starts where it meets the hull, 2 cm inside the skin.
    root = np.array([meet(k, 0.02) for k in range(n_side + 1)])
    span = (np.arange(N_SPAN + 1) / N_SPAN) ** SPAN_POWER
    port = np.array([[point(k, root[k] + (v_top - root[k]) * f) for f in span] for k in range(n_side + 1)])
    # Loop round the section: port leading edge -> trailing edge, then starboard back to the leading
    # edge, which lies on the centre plane and closes the loop.
    ring = np.concatenate([port, (port[1:] * FLIP)[::-1]], axis=0)            # P0..P24, S24..S1
    n_ring = len(ring)
    stbd = lambda k: n_ring - k                                               # ring index of starboard column k
    idx = np.arange(n_ring * (N_SPAN + 1)).reshape(n_ring, N_SPAN + 1)
    # Airbrake: the rear of both sides between two span rows opens as a pair of panels.
    r0, r1 = (int(np.argmin(np.abs(port[BRAKE_COL, :, 2] - z))) for z in BRAKE_Z)
    faces, slots = [], []
    for i in range(n_ring):
        j = (i + 1) % n_ring
        cell = i if i < n_side else (-1 if i == n_side else n_ring - 1 - i)   # chord cell on its side; -1 is the blunt trailing edge
        slot = 0 if cell < 0 else (1 if cell < N_TEAL else (2 if cell < N_TEAL + N_LINE else 0))
        for r in range(N_SPAN):
            if r0 <= r < r1 and (cell < 0 or cell >= BRAKE_COL):
                continue
            faces.append([idx[i, r], idx[j, r], idx[j, r + 1], idx[i, r + 1]])
            slots.append(slot)
    # The bay behind the panels: a spar across the hinge lines and a rib at each end.
    for r in range(r0, r1):
        faces.append([idx[BRAKE_COL, r], idx[stbd(BRAKE_COL), r], idx[stbd(BRAKE_COL), r + 1], idx[BRAKE_COL, r + 1]])
        slots.append(3)
    for r in (r0, r1):
        for k in range(BRAKE_COL, n_side):
            faces.append([idx[k, r], idx[k + 1, r], idx[stbd(k + 1), r], idx[stbd(k), r]])
            slots.append(3)
    verts = ring.reshape(-1, 3)
    # Tip: the last station is a thin lens; close it with quads across the two sides.
    for i in range(1, n_side):
        faces.append([idx[i, -1], idx[i + 1, -1], idx[stbd(i + 1), -1], idx[stbd(i), -1]])
        slots.append(1 if i < N_TEAL else 0)
    faces.append([idx[0, -1], idx[1, -1], idx[stbd(1), -1]])
    slots.append(1)
    # Outward guide: away from each section's own centre; the tip row also looks up. The bay's walls
    # are wound apart: spar looking aft, ribs looking into the bay.
    guide = ring - ring.mean(axis=0, keepdims=True)
    guide[:, -1, 2] += 2.0
    n_skin = len(faces) - (r1 - r0) - 2 * (n_side - BRAKE_COL) - (n_side - 1) - 1
    n_bay = (r1 - r0) + 2 * (n_side - BRAKE_COL)
    flat = guide.reshape(-1, 3)
    aft, up = np.tile([0.0, 1.0, 0.0], (len(flat), 1)), np.tile([0.0, 0.0, 1.0], (len(flat), 1))
    k_s, k_b = n_skin + (r1 - r0), n_skin + (r1 - r0) + (n_side - BRAKE_COL)
    wound = (meshkit.mesh_faces(verts, faces[:n_skin], flat) + meshkit.wind(verts, faces[n_skin:k_s], aft)
             + meshkit.wind(verts, faces[k_s:k_b], up) + meshkit.wind(verts, faces[k_b:n_skin + n_bay], -up)
             + meshkit.mesh_faces(verts, faces[n_skin + n_bay:], flat))
    obj = meshkit.mesh_object("Derive_Dorsale", verts, wound, "02_Exterieur_Appendices",
                              materials=[mats["white"], mats["teal"], mats["amber_paint"], mats["dark"]],
                              face_mats=np.array(slots))
    obj.data.set_sharp_from_angle(angle=math.radians(50.0))
    brakes = airbrake(port, r0, r1, mats)

    # Root fairing: a hollow fillet swept round the line where the fin leaves the skin.
    foot = np.array([point(k, meet(k, 0.0)) for k in range(n_side + 1)])
    up = np.array([hull_top(p[0], min(p[1], hull.station_y[-1] - 0.01), True)[1] for p in foot])
    out = foot - foot.mean(axis=0)
    out[:, 2] = 0.0
    out[:, 1] *= 0.15                                   # mostly sideways, a little fore and aft at the ends
    # Open at the leading edge, where the fin leaves the skin at a grazing angle: the fillet starts aft of it.
    lead = 4
    both = lambda a: np.vstack([a[lead:], (a[lead:-1] * FLIP)[::-1]])
    path, normal, across = both(foot), both(up), both(out)
    k_side = np.concatenate([np.arange(lead, n_side + 1), np.arange(n_side - 1, lead - 1, -1)])
    fade = np.clip(np.minimum(k_side - lead, n_side - k_side) / 5.0, 0.0, 1.0)
    fade = fade * fade * (3.0 - 2.0 * fade)
    profile = []
    for f in fade:
        r = 0.004 + 0.05 * f
        arc = [(r * (1.0 - math.sin(a)), r * (1.0 - math.cos(a))) for a in np.linspace(0.5 * math.pi, 0.0, 5)]
        profile.append([(-0.004, r + 0.012)] + arc + [(r + 0.012, -0.004)])
    profile = np.array(profile)
    fairing = frames.sweep("Derive_Carenage", path, normal, profile, "02_Exterieur_Appendices", [mats["white"]],
                           across=across, cap=False, sharp_deg=60.0)
    return [obj, fairing] + brakes


def _strut(name, a, b, radius, mat, n=12):
    """Closed cylinder from a to b, with a quad-fan-free cap: the ends are rings joined by a strip."""
    axis = (b - a) / np.linalg.norm(b - a)
    side = np.cross(axis, (0.0, 0.0, 1.0))
    side /= np.linalg.norm(side)
    up = np.cross(side, axis)
    ang = np.arange(n) * 2.0 * math.pi / n
    circle = np.cos(ang)[:, None] * side + np.sin(ang)[:, None] * up
    rings = np.array([a + 0.55 * radius * circle, a + radius * circle, b + radius * circle, b + 0.55 * radius * circle])
    idx = np.arange(4 * n).reshape(4, n)
    faces = [[idx[k, i], idx[k, (i + 1) % n], idx[k + 1, (i + 1) % n], idx[k + 1, i]] for k in range(3) for i in range(n)]
    for ring in (idx[0][::-1], idx[3]):                    # each end: quads across the inner ring
        faces += [[ring[i], ring[i + 1], ring[n - 2 - i], ring[n - 1 - i]] for i in range(n // 2 - 1)]
    verts = rings.reshape(-1, 3)
    guide = verts - 0.5 * (a + b)
    obj = meshkit.mesh_object(name, verts, faces, "02_Exterieur_Appendices", materials=[mat], orient=guide)
    obj.data.set_sharp_from_angle(angle=math.radians(40.0))
    return obj


def _aim(pivot, old, new):
    """4x4 turning about pivot so that the direction old becomes new."""
    old, new = old / np.linalg.norm(old), new / np.linalg.norm(new)
    axis = np.cross(old, new)
    if np.linalg.norm(axis) < 1e-9:
        return np.eye(4)
    return anim.about(pivot, axis, math.atan2(np.linalg.norm(axis), float(old @ new)))


def airbrake(port, r0, r1, mats):
    """Split airbrake: the two panels of the fin's rear, each with the strut that opens it.

    A panel is the fin's own skin between the hinge column and the trailing edge. It thins to
    nothing on the hinge line, so it can swing out without fouling the spar behind it.
    """
    n_side = port.shape[0] - 1
    nodes = port[BRAKE_COL:, r0:r1 + 1]                                     # (chord, span, 3), port side
    nc, nr = nodes.shape[:2]
    du, dv = np.gradient(nodes, axis=0), np.gradient(nodes, axis=1)
    nrm = np.cross(dv, du)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    nrm = np.where(nrm[..., :1] < 0.0, -nrm, nrm)
    grown = np.minimum(np.linalg.norm(nodes - nodes[:1], axis=2) / 0.22, 1.0)    # thickens over 22 cm from the hinge
    thick = np.maximum(np.minimum(0.045, 0.75 * nodes[..., 0]) * grown * grown * (3.0 - 2.0 * grown), 0.002)
    k_c = int(np.argmin(np.abs(np.linalg.norm(nodes[:, nr // 2] - nodes[0, nr // 2], axis=1) - 0.60)))  # strut head
    gid = np.arange(nc * nr).reshape(nc, nr)
    quads = meshkit.grid_faces(gid)
    hinge = nodes[0, 0], nodes[0, -1]
    mid = nodes[nc // 2, nr // 2]
    # Both struts push from one post standing aft of the spar on the centre plane.
    spar = 0.5 * (hinge[0] + hinge[1]) * np.array([0.0, 1.0, 1.0])
    chord = (nodes[-1, nr // 2] - nodes[0, nr // 2]) * np.array([0.0, 1.0, 1.0])
    anchor = spar + chord / np.linalg.norm(chord) * 0.30
    objs = [_strut("Aerofrein_Support", spar - chord * 0.01, anchor + chord / np.linalg.norm(chord) * 0.02, 0.014,
                   mats["dark"])]
    for tag, sign in (("G", 1.0), ("D", -1.0)):
        scale = np.array([sign, 1.0, 1.0])
        a, b = hinge[0] * scale, hinge[1] * scale
        panel = panels.shell(f"Aerofrein_{tag}", nodes.reshape(-1, 3) * scale, nrm.reshape(-1, 3) * scale, quads,
                             None, mats["white"], mats["titanium"], "02_Exterieur_Appendices", thick.reshape(-1))
        # the panel opens away from the centre plane: pick the turning sense that does so
        turn = BRAKE_ANGLE if (anim.about(a, b - a, 0.1) @ np.append(mid * scale, 1.0))[0] * sign > mid[0] else -BRAKE_ANGLE
        pose = lambda u, a=a, b=b, turn=turn: anim.about(a, b - a, turn * anim.ease(u))
        anim.bake(panel, "Aerofrein", pose)
        # strut: from the spar, inside the bay, to the panel's inner face
        foot = anchor + np.array([0.012 * sign, 0.0, 0.0])
        head = (nodes[k_c, nr // 2] - nrm[k_c, nr // 2] * (thick[k_c, nr // 2] + 0.016)) * scale
        reach = lambda u: (pose(u) @ np.append(head, 1.0))[:3]
        split = foot + (head - foot) * 0.55
        body = _strut(f"Aerofrein_Verin_{tag}", foot, split + (head - foot) * 0.10, 0.022, mats["dark"])
        rod = _strut(f"Aerofrein_Tige_{tag}", foot + (head - foot) * 0.12, head, 0.011, mats["titanium"])
        anim.bake(body, "Aerofrein", lambda u, foot=foot, head=head, reach=reach: _aim(foot, head - foot, reach(u) - foot))
        anim.bake(rod, "Aerofrein", lambda u, foot=foot, head=head, reach=reach:
                  anim.shift(reach(u) - head) @ _aim(head, head - foot, reach(u) - foot))
        objs += [panel, body, rod]
    return objs
