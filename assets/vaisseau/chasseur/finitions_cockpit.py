"""Serviceable cockpit fittings, attached to the existing industrial assembly.

The visible support is sampled directly for grilles and access covers. Hoses
terminate in connectors, straps in anchors, and seat fittings in its chassis.
"""
import math
import bpy
from mathutils import Vector
from encastrements import logement, annoter, finaliser

X, YAXIS, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def construire(g, c):
    F, Y, Piece, cockpit = (g[k] for k in ('F', 'Y', 'Piece', 'cockpit'))
    from cockpit_chasseur import rect
    pave, tige, tour, loft = (c[k] for k in ('pave', 'tige', 'tour', 'loft_c'))
    metal, rubber, paint, graphite = g['BROSSE'], g['CAOUTCHOUC'], g['TOLE_INT'], c['GRAPHITE']
    white, webbing, leather = c['BLANC'], c['SANGLE'], c['CUIR']
    PL, dos, Vb, Nb = g['PLANCHER'], c['dos'], c['Vb'], c['Nb']
    yellow = g['material']('Jeu | Poignee secours', (.65, .33, .035), .0, .56)
    seam = g['material']('Jeu | Fil couture', (.19, .20, .19), .0, .88)

    def screw(pc, p, U, V, N, r=.004):
        tour(pc, p, N, [(r*1.3, 0), (r*1.3, .0007), (r, .0014)], metal, 8)
        pave(pc, p+N*.0015, U, V, N, r*1.4, .0009, .0002, rubber)

    def line(pc, points, radius, mat, sides=8):
        # Mitered rings share vertices: a bent hose has no gaps between cylinders.
        points = [Vector(p) for p in points]
        rings = []
        previous = None
        for i, p in enumerate(points):
            tangent = (points[min(i+1, len(points)-1)]-points[max(0, i-1)]).normalized()
            u = tangent.orthogonal().normalized() if previous is None else (previous-tangent*previous.dot(tangent)).normalized()
            v = tangent.cross(u); previous = u
            rings.append([p+radius*(u*math.cos(k*2*math.pi/sides)+v*math.sin(k*2*math.pi/sides)) for k in range(sides)])
        loft(pc, rings, mat)

    def fitted_cover(name, support, center, U, V, N, w, h, grille=False, recessed=False):
        pc = Piece(name, cockpit)
        mounting = None
        if recessed:
            hit, center, normal, _ = support.ray_cast(center+N*.10, -N, distance=.20)
            assert hit, name
            N = normal if normal.dot(N)>0 else -normal
            V = (V-N*V.dot(N)).normalized(); U = V.cross(N).normalized()
            mounting = logement(g, support, center, U, V, N, w, h, .012)
            mounting['mounting_mode'] = 'recessed-cover'
            center -= N*.0035
        corners = [] if recessed else rect(center, U, V, w, h)
        contact = []
        for p in corners:
            hit, q, _, _ = support.ray_cast(p+N*.35, -N, distance=.70)
            if not hit:
                raise ValueError(f'{name}: missing mounting surface')
            contact.append(q)
        if not recessed:
            lift = max((q-p).dot(N) for p, q in zip(corners, contact))+.003
            center = center+N*lift
            top = rect(center, U, V, w, h)
            loft(pc, [[p-N*.001 for p in contact], top], graphite)
        pave(pc, center, U, V, N, w-.004, h-.004, .002, paint, .001)
        if grille:
            pave(pc, center+N*.002, U, V, N, w-.022, h-.024, .0008, rubber)
            count = max(4, int((w-.03)/.013))
            for i in range(count):
                pos = center+U*((i+.5)/count-.5)*(w-.03)+N*.003
                pave(pc, pos, U, V, N, .003, h-.024, .002, graphite, .0005)
        for a in (-1, 1):
            for b in (-1, 1):
                screw(pc, center+U*a*(w/2-.007)+V*b*(h/2-.007)+N*.002, U, V, N, .0024)
        obj = pc.fin(35)
        if mounting:
            annoter(obj, mounting); obj['fascia_depth'] = -.0015
        else:
            obj['support_mesh'] = support.name; obj['support_normal'] = list(N)
            obj['support_contacts'] = [v for p in contact for v in p]
        return center

    # Defogging vents lie on the coaming and remain below the forward sightline.
    dashboard = bpy.data.objects['Pupitre | auvent']
    for s in (-1, 1):
        fitted_cover(f'Finition | desembueur {s}', dashboard, Vector((s*.29, Y(3.38), .82)), X, YAXIS, Z, .28, .075, True)

    # Console service panels, cable ducts and knee trim follow its actual facets.
    for s in (-1, 1):
        support = bpy.data.objects['Console | '+('gauche' if s>0 else 'droite')]
        N, U, V = -s*X, s*YAXIS, Z
        def inner(d, z):
            profile = c['profil_xz'](d)
            t = max(0, min(1, (z-profile[5][1])/(profile[4][1]-profile[5][1])))
            x = profile[5][0]+t*(profile[4][0]-profile[5][0])
            return Vector((s*x, Y(d), z))
        for i, d in enumerate((3.98, 4.78)):
            fitted_cover(f'Finition | acces console {s} {i}', support, inner(d, .37), U, V, N, .26, .15, i==0, recessed=True)
        pc = Piece(f'Finition | raccords console {s}', cockpit)
        # Continuous soft knee rail and a lower return at the floor.
        for z, radius, mat in ((.535, .012, rubber), (PL+.025, .009, paint)):
            points = [inner(3.82+i*(4.93-3.82)/24, z)+N*.002 for i in range(25)]
            line(pc, points, radius, mat)
        # Restrained electrical harness with bolted P-clips, never loose wire ends.
        path = [inner(3.88+i*.058, .215)+N*.022 for i in range(17)]
        line(pc, path, .0075, rubber)
        for p in (path[0], path[-1]):
            base = p-N*.022
            tour(pc, base, N, [(.018, 0), (.018, .005), (.012, .007), (.012, .023)], metal, 10)
        for i in (3, 8, 13):
            p = path[i]
            tige(pc, p-YAXIS*.006, p+YAXIS*.006, .010, metal, 10, bouts=(True, True))
            foot = p-N*.022+Z*.018
            pave(pc, foot, U, V, N, .022, .026, .004, metal, .002)
            screw(pc, foot+N*.004, U, V, N, .003)
            tige(pc, foot+N*.006, p+Z*.007, .003, metal, 6, bouts=(True, True))
        # Sill trim is tied to the tub, with positive canopy latch housings.
        for d in (3.88, 4.47):
            z = F.pont(d)-.047; x = c['paroi'](d, z)
            base = Vector((s*x, Y(d), z))
            pave(pc, base, U, Z, N, .10, .042, .028, graphite, .004)
            pave(pc, base+N*.028, U, Z, N, .068, .021, .006, metal, .003)
            for a in (-1, 1): screw(pc, base+U*a*.041+N*.028, U, Z, N, .0026)
            pave(pc, base+N*.035, U, Z, N, .020, .005, .0007, yellow)
        pc.fin(35)

    # Dashboard lower edge has a bolted return, a central grip and service bosses.
    pc = Piece('Finition | traverse pupitre', cockpit)
    Nm, Vm, Um = c['Nm'], c['Vm'], c['Um']
    for s in (-1, 1):
        p = c['mip'](s*.40, .012)+Nm*.002
        pave(pc, p, Um, Vm, Nm, .18, .020, .007, graphite, .003)
        for a in (-1, 1): screw(pc, p+Um*a*.074+Nm*.007, Um, Vm, Nm, .003)
    pc.fin(35)

    # Seat rails, cushion welts, stitch rows and four anchored restraint straps.
    pc = Piece('Finition | siege et harnais', cockpit)
    da, zc, buckle = c['da'], c['zc'], c['boucle']
    for s in (-1, 1):
        for d in (da-.31, da+.21):
            p = Vector((s*.17, Y(d), PL+.007))
            pave(pc, p, X, YAXIS, Z, .075, .07, .014, graphite, .003)
            screw(pc, p+Z*.014, X, YAXIS, Z, .005)
        # Upper anchor cap and lower belt continuation to the central buckle.
        anchor = dos(s*.10, .705, .029)
        pave(pc, anchor, X, Vb, Nb, .067, .038, .009, metal, .003)
        screw(pc, anchor+Nb*.009, X, Vb, Nb, .003)
        route = [dos(s*.075, .22, .026), dos(s*.065, .10, .030),
                 Vector((s*.055, Y(da-.10), zc(da-.10)+.028)), buckle+X*s*.028+Z*.010]
        for a, b in zip(route, route[1:]):
            tangent = (b-a).normalized(); n = Nb if (b-a).z<-.06 else Z
            u = tangent.cross(n).normalized()
            pave(pc, (a+b)/2, u, tangent, u.cross(tangent), .045, (b-a).length+.002, .004, webbing)
        # Welts follow the rounded bolsters; small stitches follow each centre pad.
        welt = [dos(s*.151, .035+k*.625/24, .018) for k in range(25)]
        line(pc, welt, .002, leather, 6)
        for height in (.10, .235, .37, .505):
            for k in range(12):
                p = dos(-.102+k*.0185, height+.045*s, .017)
                pave(pc, p, X, Vb, Nb, .007, .0008, .0006, seam)
        for k in range(21):
            p = dos(s*.093, .245+k*.021, .025)
            pave(pc, p, X, Vb, Nb, .0008, .008, .0007, seam)
        # Lap-belt lug is bolted into the bucket, below the cushion lip.
        p = Vector((s*.23, Y(da-.06), zc(da-.06)+.045))
        pave(pc, p, X, YAXIS, Z, .044, .040, .008, metal, .004)
        screw(pc, p+Z*.008, X, YAXIS, Z, .004)
    # Quarter-turn buckle and a guarded emergency pull handle on the seat base.
    tour(pc, buckle+Z*.012, Z, [(.027, 0), (.027, .006), (.021, .009)], graphite, 16)
    pave(pc, buckle+Z*.022, X, YAXIS, Z, .032, .009, .002, metal, .001)
    hbase = Vector((0, Y(da-.37), .26))
    for s in (-1, 1):
        p = hbase+X*s*.055
        pave(pc, p+YAXIS*.016, X, Z, -YAXIS, .033, .040, .023, graphite, .004)
    handle = [hbase+Vector((-.055, 0, 0)), hbase+Vector((-.059,-.020,.018)),
              hbase+Vector((-.045,-.038,.034)), hbase+Vector((.045,-.038,.034)),
              hbase+Vector((.059,-.020,.018)), hbase+Vector((.055,0,0))]
    line(pc, handle, .006, yellow, 10)
    for x in (-.031, -.006, .019):
        tige(pc, hbase+Vector((x,-.038,.034)), hbase+Vector((x+.010,-.038,.034)), .0063, rubber, 10)
    pc.fin(35)

    # Printed plates share the existing label atlas; no extra colour texture.
    module = c['module']
    module('identite', Vector((0, Y(4.98)-.003, .43)), X, Z, -YAXIS)
    module('secours', Vector((.39, Y(4.98)-.003, .64)), X, Z, -YAXIS)
    module('oxygene', Vector((-.39, Y(4.98)-.003, .64)), X, Z, -YAXIS)
    for side in (-1, 1):
        module('immatriculation', Vector((side*F.sil(2.18), Y(2.18), .43)),
               side*YAXIS, Z, side*X, surface=bpy.data.objects['Coque | peau'])

    # Two-segment edge highlights on visible structural housings, in real mm.
    finaliser()
    for name in ('Console | gauche', 'Console | droite', 'Pupitre | chassis', 'Cockpit | cloison'):
        obj = bpy.data.objects[name]
        bevel = obj.modifiers.new('Manufactured edge 1.5 mm', 'BEVEL')
        bevel.width = .0015; bevel.segments = 2; bevel.limit_method = 'ANGLE'; bevel.angle_limit = math.radians(35)
        bevel.harden_normals = True
