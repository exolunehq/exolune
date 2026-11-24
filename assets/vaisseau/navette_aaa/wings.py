"""Rigid folding wings for the Navette AAA. Dimensions are metres in the ship frame.

The port wing is designed in its docked flight pose. Both panels ride the same two box
spars. The outer panel additionally rotates about the physical, longitudinal hinge pin.
The starboard installation mirrors that entire mechanism.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix

import anim
import meshkit
import wing_bay
from wing_bay import Z, slot_cells

COL = "02_Exterieur_Appendices"
ROOT, HINGE, TIP = 1.845, 2.91, 3.73
PIN_Z = Z + 0.074
TIP_NOSE, TIP_CHORD = 2.82, 1.60
SWEEP, AFT_SLOPE = math.tan(math.radians(44)), 0.405
STOW, OVERTRAVEL = 1.185, 0.35
RAIL_SLOPE = -0.018  # a slight rise inboard keeps the folded stack above the exhaust
SPAR_Y = (2.56, 4.02)
HINGE_GAP = 0.0013
LENS_START, LENS_END, LENS_RADIUS = TIP_NOSE + 0.33, TIP_NOSE + 0.64, 0.015


def travel(u):
    """Offset from flight: extract the folded stack, hold to unfold, then dock inboard."""
    return -STOW + (STOW + OVERTRAVEL) * anim.ease(u, 0.274, 0.49) - OVERTRAVEL * anim.ease(u, 0.76, 0.90)


def wing_pose(sign, outer, u):
    m = anim.shift((sign * (HINGE + travel(u)), 0, PIN_Z + RAIL_SLOPE * travel(u)))
    if outer:
        angle = math.pi * (1 - anim.ease(u, 0.49, 0.76))
        m = m @ anim.about((0, 0, 0), (0, -sign, 0), angle)
    return m


def bake_flight_part(obj, pose):
    """Geometry is in flight coordinates. Store its folded neutral transform and key it."""
    rest = pose(0)
    obj.matrix_world = Matrix(rest.tolist())
    inverse = np.linalg.inv(rest)
    anim.bake(obj, "Ailes", lambda u: pose(u) @ inverse)


def chord(x):
    return TIP_NOSE + SWEEP * (x - TIP), TIP_NOSE + TIP_CHORD - AFT_SLOPE * (x - TIP)


def section_depth(x, f, direction):
    """Cambered enamel skin with a full forward section and a fine trailing edge."""
    high = np.interp(x, (ROOT, HINGE, TIP), (0.094, 0.063, 0.043))
    low = np.interp(x, (ROOT, HINGE, TIP), (0.104, 0.080, 0.059))
    # Broaden the pressure side through mid-chord, retaining the tangent at the leading edge.
    thickness = 10 * (0.2969*np.sqrt(f) - 0.1260*f - 0.3516*f**2 + 0.2843*f**3 - 0.1015*f**4)
    if direction < 0:
        thickness *= 1.0 + 0.07*f*(1-f)
    # A small radius turns into the tip face, without shortening the straight planform.
    t = np.clip((x - (TIP - 0.007)) / 0.007, 0, 1)
    corner = 0.0055 * (1 - np.sqrt(np.maximum(0, 1 - t*t)))
    return ((high if direction > 0 else low) - corner) * thickness


def airfoil(x, y, direction):
    lead, aft = chord(x)
    f = (y-lead) / (aft-lead)
    inside = (f >= 0) & (f <= 1) & (x >= ROOT) & (x <= TIP)
    return np.where(inside, section_depth(x, np.clip(f, 0, 1), direction), 0.0)


def fit_bay(grid):
    wing_bay.fit_bay(grid,airfoil)


def handed_mesh(name, verts, faces, slots, palette, sign, sharp=45):
    faces = faces if sign > 0 else [list(reversed(f)) for f in faces]
    o = meshkit.mesh_object(name, np.asarray(verts) * (sign, 1, 1), faces, COL, materials=palette,
                            face_mats=np.asarray(slots))
    o.data.set_sharp_from_angle(angle=math.radians(sharp))
    return o


def tip_cap(verts, face, yy, top, bottom):
    """A capsule lens and recessed bezel share vertices with the rounded tip face."""
    def point(x, y, z):
        verts.append((x, y, z))
        return len(verts)-1

    rows = []
    for j,y in enumerate(yy):
        if j == 0:
            rows.append([top[j]]*5)
            continue
        centre = np.clip(y, LENS_START+LENS_RADIUS, LENS_END-LENS_RADIUS)
        c = np.clip((y-centre)/LENS_RADIUS, -1, 1)
        if y < LENS_START-1e-8 or y > LENS_END+1e-8:
            rows.append([point(TIP, y, Z)]*5)
            continue
        s = np.sqrt(max(0, 1-c*c))
        if s < 1e-5:
            s = 0
        yi = centre + (LENS_RADIUS-0.0020)*c
        rim_low = point(TIP, y, Z-LENS_RADIUS*s)
        rim_high = point(TIP, y, Z+LENS_RADIUS*s) if s else rim_low
        glass_low = point(TIP-0.0012, yi, Z-(LENS_RADIUS-0.0020)*s)
        glass_high = point(TIP-0.0012, yi, Z+(LENS_RADIUS-0.0020)*s) if s else glass_low
        crown = point(TIP-0.0012+0.00085*s, yi, Z) if s else glass_low
        rows.append([rim_low, glass_low, crown, glass_high, rim_high])
    for j,(first, second) in enumerate(zip(rows, rows[1:])):
        lo = [bottom[j], *first, top[j]]
        hi = [bottom[j+1], *second, top[j+1]]
        for k,material in enumerate((1,2,3,3,2,0)):
            if 0 < k < 5 and not LENS_START < (yy[j]+yy[j+1])/2 < LENS_END:
                continue
            ids = list(dict.fromkeys((lo[k],hi[k],hi[k+1],lo[k+1])))
            if len(ids) >= 3:
                face(ids, material)


def panel(mats, sign, side, outer):
    x0, x1 = (HINGE + HINGE_GAP, TIP) if outer else (ROOT, HINGE - HINGE_GAP)
    xs = np.linspace(x0, x1, 15)
    if outer:
        xs = np.unique(np.r_[xs, TIP - np.array((0.007, 0.004, 0.0016, 0.00035))])
    fs = 0.5 * (1 - np.cos(np.linspace(0, math.pi, 85)))
    # Spar sockets are actual openings in the inner rib. The tip lens has an integral flush bezel.
    nose, tail = chord(x0 if not outer else x1)
    openings = [(y - 0.075, y + 0.075) for y in SPAR_Y] if not outer else [(TIP_NOSE + 0.33, TIP_NOSE + 0.64)]
    stations = [(y - nose) / (tail - nose) for pair in openings for y in pair]
    if outer:
        offset = LENS_RADIUS*np.cos(np.linspace(0, math.pi/2, 10))
        arcs = np.r_[LENS_START+LENS_RADIUS-offset, LENS_END-LENS_RADIUS+offset]
        stations.extend((arcs-nose)/(tail-nose))
    fs = np.unique(np.round(np.r_[fs, stations], 12))
    n = len(fs)
    verts, faces, slots = [], [], []

    def face(ids, slot):
        faces.append(ids)
        slots.append(slot)

    rings = []
    for x in xs:
        lead, aft = chord(x)
        yy = lead + (aft - lead) * fs
        above = section_depth(x, fs, 1)
        below = section_depth(x, fs, -1)
        top = list(range(len(verts), len(verts) + n))
        verts += list(zip([x] * n, yy, Z + above))
        bottom = [top[0]] + list(range(len(verts), len(verts) + n - 1))
        verts += list(zip([x] * (n - 1), yy[1:], Z - below[1:]))
        rings.append((top, bottom))
    for (ta, ba), (tb, bb) in zip(rings, rings[1:]):
        for j in range(n - 1):
            face([ta[j], tb[j], tb[j + 1], ta[j + 1]], 0)
            face([ba[j + 1], bb[j + 1], bb[j], ba[j]], 1)
        face([ta[-1], tb[-1], bb[-1], ba[-1]], 1)
    for end, (x, (top, bottom)) in enumerate(zip((x0, x1), (rings[0], rings[-1]))):
        lead, aft = chord(x)
        yy = lead + (aft - lead) * fs
        if outer and end == 1:
            tip_cap(verts, face, yy, top, bottom)
            continue
        for j in range(n - 1):
            ymid = (yy[j] + yy[j + 1]) / 2
            window = any(a < ymid < b for a, b in openings)
            ids = [bottom[j], bottom[j + 1], top[j + 1], top[j]]
            if j == 0:
                ids.pop()
            if not outer and end == 0 and window:
                continue
            face(ids if end else ids[::-1], 2)
    palette = [mats["white"], mats["teal"], mats["dark"], mats["nav_red" if sign > 0 else "nav_green"]]
    return handed_mesh(f"Aile_{'Saumon' if outer else 'Emplanture'}_{side}", verts, faces, slots, palette, sign)


def axial_part(name, rings, along_y, mats, sign, closed=True, band_slots=None):
    """Ring loft with an optional closed return for a hollow bearing or box section."""
    n = len(rings[0])
    verts = np.asarray(rings).reshape(-1, 3)
    faces, slots = [], []
    for a in range(len(rings) if closed else len(rings) - 1):
        b = (a + 1) % len(rings)
        for j in range(n):
            k = (j + 1) % n
            faces.append([a*n+j, a*n+k, b*n+k, b*n+j])
            slots.append(band_slots[a] if band_slots is not None else int(a == 2 and len(mats) > 1))
    if not closed:
        for a, rev in ((0, True), (len(rings) - 1, False)):
            c = len(verts)
            verts = np.vstack((verts, np.mean(rings[a], axis=0)))
            for j in range(n):
                ids = [a*n+j, a*n+(j+1)%n, c]
                faces.append(ids[::-1] if rev else ids)
                slots.append(0)
    if along_y:
        faces = [f[::-1] for f in faces]
    return handed_mesh(name, verts, faces, slots, mats, sign)


def pin_segment(name, y0, y1, radius, bore, mat, sign):
    phi = np.arange(24) * (2 * math.pi / 24)
    def ring(y, r):
        return np.column_stack((HINGE + r * np.cos(phi), np.full(len(phi), y), PIN_Z + r * np.sin(phi)))
    rings = [ring(y0, radius), ring(y1, radius)]
    if bore:
        rings += [ring(y1, bore), ring(y0, bore)]
    return axial_part(name, rings, True, [mat], sign, bool(bore))


def bearing(name, y0, y1, direction, mats, sign):
    """Form a captive clevis around its bore. The rounded foot beds directly into the moulded skin."""
    phi = np.arange(48) * (2*math.pi / 48)
    rays = np.column_stack((np.cos(phi), np.sin(phi)))
    x_foot = HINGE + direction*0.034
    z_foot = Z + airfoil(x_foot, 0.5*(y0+y1), 1) - 0.004
    foot = np.array((x_foot-HINGE, z_foot-PIN_Z))
    # Common tangents of the two radii give a rounded eye and a taper into the foot.
    support = np.maximum(0.0100, rays @ foot + 0.006)
    radius = (support[None,:] / np.maximum(rays @ rays.T, 1e-8)).min(axis=1)
    def ring(y, r):
        points = rays * np.broadcast_to(r, len(rays))[:,None]
        taper = np.clip((np.linalg.norm(points, axis=1)-0.010) / 0.029, 0, 1)
        middle = (y0+y1)/2
        return np.column_stack((HINGE + points[:,0], middle+(y-middle)*(1-0.23*taper),
                                PIN_Z + points[:,1]))
    bevel, bore = 0.0011, 0.0059
    rings = [ring(y0, radius-bevel), ring(y0+bevel, radius), ring(y1-bevel, radius), ring(y1, radius-bevel),
             ring(y1, 0.0081), ring(y1+0.00015, 0.0077), ring(y1+0.00015, bore+0.0004),
             ring(y1-0.00045, bore), ring(y0+0.00045, bore), ring(y0-0.00015, bore+0.0004),
             ring(y0-0.00015, 0.0077), ring(y0, 0.0081)]
    return axial_part(name, rings, True, [mats["white"], mats["titanium"], mats["dark"]], sign,
                      band_slots=(0,0,0,0,1,1,1,2,1,1,1,0))


def hinge_hardware(mats, sign, outer):
    """Three short bushed clevises on a common axis with individually retained pins."""
    lead, aft = chord(HINGE)
    parts = []
    for f in (0.235, 0.435, 0.665):
        y = lead + f*(aft-lead)
        if outer:
            parts.append(bearing("Oeil_mobile", y-0.0125, y+0.0125, 1, mats, sign))
        else:
            for a,b in ((-0.028,-0.0137), (0.0137,0.028)):
                parts.append(bearing("Chape", y+a, y+b, -1, mats, sign))
            parts.append(pin_segment("Axe_captif", y-0.0285, y+0.0285, 0.00515, 0, mats["blade"], sign))
            for a,b in ((-0.030,-0.0285), (0.0285,0.030)):
                parts.append(pin_segment("Tete_axe", y+a, y+b, 0.0070, 0.0021, mats["titanium"], sign))
    return parts


def lap_joint(mats, sign, side):
    """A scarf under the folding seam blocks a sightline through the joint in flight."""
    f = 0.5*(1-np.cos(np.linspace(0.17, math.pi-0.04, 85)))
    # Feather the return near the nose, where the swept leading edge crosses the moving rib.
    reach = 1.0 - 0.83*np.exp(-(f/0.047)**2)
    clearance = 0.0029 + 0.0017*np.exp(-f/0.06)
    rows = []
    for i, offset in enumerate((-0.0046, -0.002, 0.002, 0.0048)):
        x = HINGE + offset * (reach if offset > 0 else 1)
        lead,aft = chord(x)
        y = lead + (aft-lead)*f
        z = Z - section_depth(x,f,-1) + (0.0006 if i == 0 else -clearance)
        rows.append(np.column_stack((np.broadcast_to(x,y.shape),y,z)))
    p = np.stack(rows,axis=1)
    n = np.tile((0,0,-1.0), (*p.shape[:2],1))
    return wing_bay.sheet("Aile_Recouvrement_" + side,p,n,0.00065,mats["teal"],mats["seam"],sign)


def spars(mats, sign, side):
    """Three running members in each fixed box. Their nested bores keep a running clearance."""
    stages = [(0.674, 1.405, 0.065, 0.025, 0.057, 0.021),
              (0.709, 1.447, 0.055, 0.0195, 0.047, 0.0165),
              (0.746, 1.486, 0.045, 0.015, 0.037, 0.012),
              (0.784, 1.525, 0.035, 0.0105, 0, 0)]
    for i, (x0, x1, w, h, iw, ih) in enumerate(stages):
        members = []
        carried = i == len(stages) - 1
        if carried:
            # This final member and its bonded end fitting are part of the rigid wing root.
            x0 += STOW
            x1 += STOW
        for y in SPAR_Y:
            def ring(x, a, b):
                z = Z + RAIL_SLOPE * (x - (1.525 + STOW))
                return [(x,y-a,z-b),(x,y+a,z-b),(x,y+a,z+b),(x,y-a,z+b)]
            rings = [ring(x0,w,h), ring(x1,w,h)]
            if iw:
                rings += [ring(x1,iw,ih),ring(x0,iw,ih)]
            elif carried:
                shoe_x = x1 + 0.055
                lead, aft = chord(shoe_x)
                fit = (np.array([y - 0.067, y + 0.067]) - lead) / (aft - lead)
                skin = min(section_depth(shoe_x, fit, 1)) - 0.002
                rings += [ring(x1 + 0.014, 0.063, 0.026), ring(shoe_x, 0.067, skin)]
            mat = mats["titanium" if i % 2 else "dark"]
            members.append(axial_part("Longeron", rings, False, [mat, mats["duct"]], sign, bool(iw)))
        if carried:
            return members
        obj = meshkit.join(members, f"Aile_Glissiere_{i}_{side}")
        if i:
            rail = np.array((sign, 0, RAIL_SLOPE))
            anim.bake(obj, "Ailes", lambda u, i=i: anim.shift(rail * ((travel(u) + STOW)*i/3)))


def build(grid, mats):
    grid, datum = wing_bay.installation(grid)
    existing = set(bpy.context.scene.objects)
    shoulder = wing_bay.Shoulder(grid, airfoil)
    for sign, side in ((1, "G"), (-1, "D")):
        shoulder.build(mats, sign, side)
        ends = spars(mats, sign, side)
        for outer in (False, True):
            blade = panel(mats, sign, side, outer)
            hardware = hinge_hardware(mats, sign, outer)
            if not outer:
                hardware.extend(ends)
                hardware.extend(shoulder.saddle(mats, sign, side))
                hardware.append(lap_joint(mats, sign, side))
            obj = meshkit.join([blade, *hardware], blade.name)
            # Put both origins on the bearing. Interpolated rotation then preserves the pin between keys.
            obj.data.transform(Matrix.Translation((-sign * HINGE, 0, -PIN_Z)))
            bake_flight_part(obj, lambda u, outer=outer, sign=sign: wing_pose(sign, outer, u))
    parent = bpy.data.objects.new("Repere_Ailes_Tranche", None)
    bpy.context.scene.collection.objects.link(parent)
    parent.matrix_world = Matrix(datum.tolist())
    for obj in set(bpy.context.scene.objects)-existing-{parent}:
        obj.parent = parent
    bpy.context.view_layer.update()
