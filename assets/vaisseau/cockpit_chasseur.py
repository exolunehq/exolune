"""Le cockpit du chasseur : la verrière dégagée, tout l'équipement sous le seuil du verre.

Pupitre bas à trois écrans et bandeau d'alarmes, pont antireflet jusqu'au nez de la bulle ; consoles latérales à pan
incliné et tablette, aux plaques sérigraphiées de modules_cockpit.py (atlas plaques.png, textures_cockpit.py) ; palonnier ;
manche et manette des gaz animés (pieces_mobiles.py) ; siège baquet à appui-tête, bourrelets, piqûres et harnais, d'après
le concept. Appelé par design_chasseur.py : construire(globals()).

Repère du vaisseau : nez vers -Y, haut +Z, gauche du pilote +X ; d est la distance à la pointe du nez.
"""
import math
import bpy
from mathutils import Vector
import modules_cockpit as mc
from encastrements import logement, annoter
import panneaux_cockpit as contours

X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
# L'oeil est en d 4,40 ; le dossier passe 26 cm derrière lui, l'appui-tête juste derrière le casque, incliné de 18° ; le manche entre les genoux, à portée
# de main ; le pupitre sous la ligne de visée qui rase le nez de la bulle.
D_DOS, Z_DOS, INCL = 4.66, 1.00, math.radians(18)   # un point du dos à hauteur d'épaule, l'inclinaison
D_MANCHE, D_PEDALES, D_PUPITRE = 3.95, 3.43, 3.60
Z_TABLETTE = .56

def rect(c, U, V, su, sv): return [c - U * su / 2 - V * sv / 2, c + U * su / 2 - V * sv / 2, c + U * su / 2 + V * sv / 2, c - U * su / 2 + V * sv / 2]
def cercle(c, U, V, r, n): return [c + (U * math.cos(2 * math.pi * i / n) + V * math.sin(2 * math.pi * i / n)) * r for i in range(n)]

def construire(g):
    F, Y, Piece, nuancier, material, image, cockpit = (g[k] for k in ('F', 'Y', 'Piece', 'nuancier', 'material', 'image', 'cockpit'))
    GARNITURE, BROSSE, CAOUTCHOUC, ECRANS, PL = g['GARNITURE'], g['BROSSE'], g['CAOUTCHOUC'], g['ECRANS'], g['PLANCHER']
    CUVE, CUVE_UNIE, uv_int = g['TOLE_INT'], g['CUVE'], g['uv_interieur']   # la tôlerie du cockpit ; l'uni pour les petites pièces
    Yv = lambda d: Vector((0, Y(d), 0))
    plaques = material('Jeu | plaques', (1, 1, 1), .05, .62); nt = plaques.node_tree
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = image('plaques.png', False); nt.links.new(tx.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    LENS = material('Jeu | Voyant eteint', (.035, .032, .026), 0, .25)
    LIT = {None: LENS, 'amber': material('Jeu | Voyant ambre', (1.0, .28, .025), .05, .38, 1.6),
           'cyan': material('Jeu | Affichage cyan', (.025, .52, .74), .05, .35, 2.0), 'red': material('Jeu | Signal rouge', (.8, .025, .012), .05, .42, 1.5)}
    BLANC = material('Jeu | Marquage clair', (.63, .68, .65), .2, .64)
    SURETE = material('Jeu | Plastique securite', (.32, .018, .012), .05, .42)
    GRAPHITE = material('Jeu | Ceramique graphite', (.055, .075, .082), .55, .56)
    ANTIREFLET = material('Jeu | Antireflet', (.028, .032, .035), 0, .92)
    CUIR = material('Jeu | Cuir', (.068, .073, .078), .02, .70)
    SANGLE = material('Jeu | Sangle', (.030, .034, .038), 0, .85)
    BOUCLE = material('Jeu | Boucle cuir', (.42, .25, .12), .05, .6)

    def loft_c(pc, rings, m, teinte='metal', bouts=(True, True), uv0=None, side_materials=None):
        # Comme loft de design_chasseur, avec des UV de plaque au besoin (uv0 : point -> uv).
        rings = [[Vector(p) for p in r] for r in rings]; ctr = [sum(r, Vector()) / len(r) for r in rings]
        uvs = (lambda q: [uv0(p) for p in q]) if uv0 else (lambda q: None)
        def f(q, material=m, **k):
            if material is CUVE: pc.face(q, material, *uv_int(q), **k)
            else: pc.face(q, material, nuancier(q, teinte), uvs(q), **k)
        for (a, ca), (b, cb) in zip(zip(rings, ctr), zip(rings[1:], ctr[1:])):
            for i in range(len(a)):
                j = (i + 1) % len(a)
                f([a[i], a[j], b[j], b[i]], material=(side_materials or {}).get(i, m), dehors_de=(ca + cb) / 2)
        if bouts[0]: f(rings[0], n=ctr[0] - ctr[1])
        if bouts[1]: f(rings[-1], n=ctr[-1] - ctr[-2])
    def tige(pc, a, b, r, m, n=8, r2=None, bouts=(False, True), teinte='metal'):
        a, b = Vector(a), Vector(b); N = (b - a).normalized(); U = N.orthogonal().normalized(); V = N.cross(U)
        loft_c(pc, [cercle(a, U, V, r, n), cercle(b, U, V, r if r2 is None else r2, n)], m, teinte, bouts)
    def tour(pc, c, N, profil, m, n=12, bouts=(False, True)):
        # Profil (rayon, hauteur) le long de N.
        N = Vector(N).normalized(); U = N.orthogonal().normalized(); V = N.cross(U)
        loft_c(pc, [cercle(c + N * h, U, V, r, n) for r, h in profil], m, 'metal', bouts)
    def pave(pc, c, U, V, N, su, sv, sn, m, ch=0.0, teinte='metal'):
        # Pavé posé par sa base en c ; ch chanfreine les arêtes du dessus.
        c = Vector(c); U, V, N = Vector(U).normalized(), Vector(V).normalized(), Vector(N).normalized()
        an = [rect(c, U, V, su, sv)] + ([rect(c + N * (sn - ch), U, V, su, sv), rect(c + N * sn, U, V, su - 2 * ch, sv - 2 * ch)] if ch else [rect(c + N * sn, U, V, su, sv)])
        loft_c(pc, an, m, teinte)

    # --- La cuve : demi-largeur de la paroi à (d, z), réglée du seuil du verre au plancher (design_chasseur.py).
    def bord_verre(dg):
        x = F.bulle_l(dg) if dg <= F.VW else F.x_cadre(dg); return x, F.bulle(.999 * x, dg)
    def paroi(d, z):
        def point(dg):
            x, zs = bord_verre(dg); t = (zs - z) / (zs - PL); df = 3.40 + (dg - F.V0) / (F.VF - F.V0) * 1.70
            return dg + t * (df - dg), x + t * (.82 * x - x)
        lo, hi = F.V0 + .02, F.VF - .01
        for _ in range(40):
            m = .5 * (lo + hi)
            if point(m)[0] < d: lo = m
            else: hi = m
        return point(lo)[1]

    # --- Les plaques sérigraphiées : plaque à chants teintés, quatre fixations, commandes posées sur leur légende.
    rects = mc.atlas(); TA, K = mc.ATLAS, mc.ECHELLE
    tx0, ty0, _, _ = rects[mc.TEINTE]; tu, tv = (tx0 + 16) / TA, 1 - (ty0 + 16) / TA
    def uv_teinte(p): return (tu + (p.x * 7.1 + p.y * 3.3) % .006 - .003, tv + (p.z * 6.7 + p.y * 2.9) % .006 - .003)
    def equip(pc, it, haut, U, V, N, k):
        kind = it[0]
        if kind in ('line', 'box', 'slot', 'text', 'mark', 'sector', 'trace'): return
        _, u, v, label, *opt = it; opt = opt[0] if opt else None; P = haut(u, v)
        if kind in ('tog', 'gtog'):
            tige(pc, P, P + N * .004, .0055, BROSSE, 6)
            bout = P + N * .022 + V * (.007 if k % 3 else -.007)
            tige(pc, P + N * .004, bout, .0022, BROSSE, 6, .0016); tige(pc, bout, bout + (bout - P).normalized() * .004, .003, BROSSE, 6)
            if kind == 'gtog':
                a, b = P - U * .012, P + U * .012
                for q in (a, b): tige(pc, q, q + N * .026, .0016, SURETE, 4)
                tige(pc, a + N * .026, b + N * .026, .0016, SURETE, 4, bouts=(True, True))
        elif kind == 'rot':
            tige(pc, P, P + N * .002, .014, CAOUTCHOUC, 10); tige(pc, P + N * .002, P + N * .015, .0095, CAOUTCHOUC, 10, .0082)
            pave(pc, P + N * .015 + V * .003, U, V, N, .0018, .007, .0008, BLANC)
        elif kind == 'push':
            pave(pc, P, U, V, N, .021, .021, .004, CAOUTCHOUC, .001); pave(pc, P + N * .004, U, V, N, .016, .016, .003, LIT[opt])
        elif kind == 'cb':
            tige(pc, P, P + N * .004, .0055, BROSSE, 6); tige(pc, P + N * .004, P + N * .012, .0038, CAOUTCHOUC, 6)
        elif kind == 'lamp':
            pave(pc, P, U, V, N, .030, .016, .003, CAOUTCHOUC); pave(pc, P + N * .003, U, V, N, .026, .012, .002, LIT[opt])
        elif kind == 'tb':
            pave(pc, P, U, V, N, .016, .012, .002, CAOUTCHOUC); pave(pc, P + N * .002, U, V, N, .012, .008, .0008, LENS)
        elif kind == 'key':
            pave(pc, P, U, V, N, .019, .019, .006, CAOUTCHOUC)
        elif kind == 'gauge':
            R = .045
            tour(pc, P, N, [(R + .009, 0), (R + .009, .008), (R + .006, .011), (R, .009), (R, 0)], CAOUTCHOUC, 16, (False, False))
            anneau = cercle(P + N * .003, U, V, R, 16)
            pc.face(anneau, ECRANS[opt], nuancier(anneau, 'metal'), [(.5 + .48 * math.cos(2 * math.pi * i / 16), .5 + .48 * math.sin(2 * math.pi * i / 16)) for i in range(16)], n=N)
        elif kind == 'timer':
            pave(pc, P, U, V, N, .072, .028, .005, CAOUTCHOUC, .001); pave(pc, P + N * .005, U, V, N, .062, .02, .0004, LIT['amber'])
    def module(nom, c, U, V, N, surface=None, encastre=False, contour=None, marge=.012):
        # Instruments are recessed into the common fascia. Exterior plates use
        # fitted sockets sampled around the actual mounting perimeter.
        (w, h), _, items = mc.MODULES[nom]; x0, y0, x1, y1 = rects[nom]
        c = Vector(c); U,V,N = (Vector(a).normalized() for a in (U,V,N))
        pc = Piece('Module | ' + nom, cockpit)
        sw,sh=w,h
        outline=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]
        if contour:
            outline=contours.offset([(Vector(p-c).dot(U),Vector(p-c).dot(V)) for p in contour],marge)
            outline=contours.chamfer(outline,.009)
            left,right=min(p[0] for p in outline),max(p[0] for p in outline)
            bottom,top=min(p[1] for p in outline),max(p[1] for p in outline)
            sw,sh=right-left,top-bottom
            du,dv=(left+right)/2,(bottom+top)/2
            c+=U*du+V*dv; outline=[(x-du,y-dv) for x,y in outline]
        contacts = []
        mounting = None
        if encastre:
            mounting = logement(g, surface, c, U, V, N, sw, sh, contour=outline)
            c -= N*.006
        elif surface:
            bpy.context.view_layer.update()
            corners = rect(c, U, V, w + .012, h + .012)
            perimeter = [a.lerp(b, k/4) for a, b in zip(corners, corners[1:]+corners[:1]) for k in range(4)]
            for p in perimeter:
                hit, location, _, _ = surface.ray_cast(p + N*.35, -N, distance=.7)
                if not hit:
                    raise ValueError(f'{nom}: socket misses {surface.name} at {tuple(p)}')
                contacts.append(location.copy())
            lift = max((q-p).dot(N) for p, q in zip(perimeter, contacts)) + .006
            c += N*lift
            top = [p+N*lift for p in perimeter]
            loft_c(pc, [[q-N*.001 for q in contacts], top], CUVE_UNIE)
            loft_c(pc, [top, [p+N*.001 for p in top]], CAOUTCHOUC)
            c += N*.001
        c = c + N * .0005
        def uv(p):
            q = p - c; return ((x0 + (q.dot(U)/sw+.5)*w*K) / TA, 1 - (y1 - (q.dot(V)/sh+.5)*h*K) / TA)
        an = [[c+U*x+V*y+N*z for x,y in contours.offset(outline,inset)] for z,inset in ((0,0),(.0025,0),(.004,.0015))]
        loft_c(pc, an, plaques, bouts=(False, False), uv0=uv_teinte)
        pc.face(an[-1], plaques, nuancier(an[-1], 'metal'), [uv(p) for p in an[-1]], n=N)
        def haut(u, v, z=.004): return c + U * (u/w-.5)*sw + V * (v/h-.5)*sh + N*z
        fasteners = contours.offset(outline,.008)
        # One fastener per distinct corner; close chamfer corners share one.
        used=[]
        for x,y in fasteners:
            if any(math.hypot(x-a,y-b)<.025 for a,b in used): continue
            used.append((x,y)); p=c+U*x+V*y+N*.004
            tige(pc,p,p+N*.0015,.0032,BROSSE,10)
            pave(pc,p+N*.0016,U,V,N,.004,.0008,.0002,CAOUTCHOUC)
        control_clearance=1.0
        for k,it in enumerate(items):
            start=len(pc.bm.verts); equip(pc,it,haut,U,V,N,k)
            for vertex in list(pc.bm.verts)[start:]:
                q=vertex.co-c; distance=contours.clearance(outline,(q.dot(U),q.dot(V)))
                control_clearance=min(control_clearance,distance)
                if distance < -.0001:
                    raise ValueError(f'{nom}: {it[0]} {it[3]} crosses the fitted panel by {-distance*1000:.1f} mm')
        obj = pc.fin(35)
        if mounting:
            annoter(obj, mounting)
            obj['fascia_depth'] = -.0015
            obj['control_clearance'] = control_clearance
            obj['fitted_panel'] = bool(contour)
        elif surface:
            obj['support_mesh'] = surface.name
            obj['support_normal'] = list(N)
            obj['support_contacts'] = [v for q in contacts for v in q]
        return haut, U, V, N
    def ecran(nom, c, N, surface):
        # Boîtier usiné, six touches de bord, quatre vis ; l'image lit UVMap, u = 0 à gauche du pilote, v = 1 en haut.
        Up = Vector((1, 0, 0)); Vp = N.cross(Up).normalized(); pc = Piece('Ecran | ' + nom, cockpit)
        mounting = logement(g, surface, c, Up, Vp, N, .25, .30, .028)
        c -= N*.020
        f = rect(c + N * .021, Up, Vp, .244, .294); fen = rect(c - Vp * .03 + N * .021, Up, Vp, .20, .20)
        loft_c(pc, [rect(c, Up, Vp, .25, .30), rect(c + N * .018, Up, Vp, .25, .30), f], CAOUTCHOUC, bouts=(False, False))
        for i in range(4):
            j = (i + 1) % 4; q = [f[i], f[j], fen[j], fen[i]]; pc.face(q, CAOUTCHOUC, nuancier(q, 'noir'), n=N)
            # Return the bezel to the recessed display: no open 5mm rim.
            q = [fen[i], fen[j], fen[j]-N*.0055, fen[i]-N*.0055]
            pc.face(q, GRAPHITE, nuancier(q, 'noir'), dehors_de=c)
        for i in range(6):
            q = c + N * .021 + Up * (-.0875 + .035 * i) + Vp * .11
            pave(pc, q, Up, Vp, N, .022, .016, .005, GRAPHITE, .001); pave(pc, q + N * .005, Up, Vp, N, .010, .0016, .0003, BLANC)
        for su in (-.115, .115):
            for sv in (-.14, .14): tige(pc, c + N * .021 + Up * su + Vp * sv, c + N * .0222 + Up * su + Vp * sv, .003, BROSSE, 6)
        q = [c - Vp * .03 + N * .016 - Up * a * .10 - Vp * b * .10 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]; pc.face(q, ECRANS[nom], uv, uv0=uv, n=N)
        obj = pc.fin(35); annoter(obj, mounting); obj['fascia_depth'] = .001

    # --- Le plancher strié, de paroi à paroi.
    pc = Piece('Cockpit | plancher', cockpit)
    for d0, d1 in ((3.45, 3.75), (3.75, 4.05), (4.05, 4.35), (4.35, 4.65), (4.65, 4.95)):
        w0, w1 = paroi(d0, PL + .004) - .002, paroi(d1, PL + .004) - .002
        q = [Vector((-w0, Y(d0), PL + .004)), Vector((w0, Y(d0), PL + .004)), Vector((w1, Y(d1), PL + .004)), Vector((-w1, Y(d1), PL + .004))]
        pc.face(q, GRAPHITE, nuancier(q, 'metal'), n=Z)
        for k in range(1, 6):
            dk = d0 + (d1 - d0) * k / 6; pave(pc, Vector((0, Y(dk), PL + .004)), X, Vector((0, 1, 0)), Z, 2 * min(w0, w1) - .06, .008, .003, CUVE)
    pc.fin(35)

    # --- Le pupitre : plan incliné vers l'oeil, de paroi à paroi. Ses côtés suivent les parois, ses coins touchent le
    # seuil du verre ; au milieu, son haut monte 5 cm au-dessus, sous la ligne de visée. Trois écrans, le bandeau
    # d'alarmes ; le pont antireflet part de son haut et s'appuie sur le bord du verre jusqu'au nez de la bulle.
    Vm = Vector((0, -.261, .965)); Nm = Vector((0, .965, .261)); Um = -X   # Um : droite du lecteur
    haut_p = Vector((0, Y(D_PUPITRE), .845)); bas_p = haut_p - Vm * .40
    def mip(u, v): return bas_p + Um * u + Vm * v
    def dz(p): return p.y - F.NEZ, p.z
    vc = .35
    for _ in range(8): vc = (F.pont(dz(bas_p + Vm * vc)[0]) - bas_p.z) / Vm.z   # le coin, au seuil
    def largeur(v): return paroi(*dz(bas_p + Vm * v)) - .004
    xc = largeur(vc); NA = 32
    # A shallow crown keeps the centre height and lowers the outer shoulders.
    vc -= .035
    def courbe_pupitre(u): return .40-(.40-vc)*(abs(u)/xc)**2
    arc = [bas_p + X * (-xc + 2 * xc * i / NA) + Vm*courbe_pupitre(-xc + 2*xc*i/NA) for i in range(NA+1)]

    # One shared boundary for the dashboard, the curved console return and the
    # wing instruments. The dashboard's outer wall is not usable panel space.
    D0C, D1C, RETURN_WIDTH = 3.84, 4.98, .065
    shelf_width = max(mc.MODULES[name][0][0] for name in ('gaz','clavier'))+.02
    stations = (3.70, 4.24, 4.61, 4.98)
    top_x = [paroi(d, .80)-.016 for d in stations]
    def console_x(d):
        t = (d-stations[0])/(stations[-1]-stations[0])
        return top_x[0]+t*(top_x[-1]-top_x[0])
    def profil_xz(d):
        zt = F.pont(d); xt = paroi(d, zt) - .002; panel = console_x(d)
        inner = panel - .18 - shelf_width
        return [(xt, zt), (panel, .80), (panel-.18, Z_TABLETTE),
                (inner, Z_TABLETTE), (inner-.009, Z_TABLETTE-.012),
                (inner+.025, PL+.05), (paroi(d, PL+.02)-.004, PL+.02)]
    def anneau(d, s): return [Vector((s*x, Y(d), z)) for x,z in profil_xz(d)]
    def anneau_avant(s):
        pts = []
        for k in range(7):
            d = D_PUPITRE
            for _ in range(12):
                x,z = profil_xz(d)[k]; x -= RETURN_WIDTH
                if k < 2: z = min(z, bas_p.z+Vm.z*courbe_pupitre(x)-.002)
                d = D_PUPITRE+(haut_p.z-z)*(-Vm.y/Vm.z)-.004
            pts.append(Vector((s*x, Y(d), z)))
        return pts
    def largeur_visible(v):
        upper,lower = anneau_avant(1)[1:3]
        z = mip(0,v).z
        return lower.x+(upper.x-lower.x)*(z-lower.z)/(upper.z-lower.z)
    def retour_console(s):
        start, end = anneau_avant(s), anneau(D0C,s)
        derivative = [(b-a)/.001 for a,b in zip(anneau(D0C-.001,s),end)]
        controls = []
        for k,(a,b,tangent) in enumerate(zip(start,end,derivative)):
            # Enter along the dashboard face, leave tangent to the console.
            dzdx = Vm.z*(courbe_pupitre(abs(a.x)+.001)-courbe_pupitre(abs(a.x)-.001))/.002 if k<2 else 0.0
            c = a+Vector((s*.045,-.045*dzdx*(-Vm.y/Vm.z),.045*dzdx))
            assert b.y > a.y, 'Console return must advance monotonically from the dashboard'
            controls.append((a,c,b-tangent*min(.065,.45*(b.y-a.y)),b))
        return [[(1-t)**3*a+3*(1-t)**2*t*c+3*(1-t)*t*t*d+t**3*b for a,c,d,b in controls]
                for t in (i/12 for i in range(13))]

    cotes = (0, .1, .2, .3)
    contour = [bas_p + X * largeur(v) + Vm * v for v in cotes] + arc[::-1] + [bas_p - X * largeur(v) + Vm * v for v in reversed(cotes)]
    pc = Piece('Pupitre | chassis', cockpit)
    loft_c(pc, [[p - Nm * .035 for p in contour], contour], CUVE,
           side_materials={i: ANTIREFLET for i in range(len(cotes), len(cotes)+NA)})
    pc.souder()
    dashboard = pc.fin(35)
    pc = Piece('Pupitre | auvent', cockpit)
    # A shallow folded lip continues the dashboard; it is not a round bumper.
    for a,b in zip(arc, arc[1:]):
        pc.face([a-Vm*.007, b-Vm*.007, b+Nm*.005, a+Nm*.005], ANTIREFLET, n=Nm)
    # Start at the chassis back edge, sharing its dark top cap instead of
    # intersecting the 35 mm return with a steeper, overlapping sheet.
    rangs = [[p - Nm * .035 for p in arc]]
    for k in range(1, 6):
        dk = D_PUPITRE - .04 - (D_PUPITRE - .04 - (F.V0 + .012)) * (k - 1) / 4; xe = F.bulle_l(dk) - .002
        rangs.append([Vector((-xe + 2 * xe * i / NA, Y(dk), F.pont(dk) + .025 * (1 - (-1 + 2 * i / NA) ** 2) * (1 - (k - 1) / 4))) for i in range(NA + 1)])
    for ra, rb in zip(rangs, rangs[1:]):
        for i in range(NA):
            q = [ra[i], ra[i + 1], rb[i + 1], rb[i]]; pc.face(q, ANTIREFLET, nuancier(q, 'noir'), n=Z)
    for rang in rangs[2:5]:   # les joints du pont
        for p0, p1 in zip(rang, rang[1:]): pave(pc, p0.lerp(p1, .5), (p1 - p0).normalized(), Vector((0, 1, 0)), Z, (p1 - p0).length, .006, .002, CAOUTCHOUC)
    pc.fin(35)
    alarm_width=min(.72,xc*.79)
    alarm_us=[-alarm_width+2*alarm_width*i/16 for i in range(17)]
    alarm_outline=[mip(u,courbe_pupitre(u)-.057) for u in alarm_us]+[mip(u,courbe_pupitre(u)-.002) for u in reversed(alarm_us)]
    module('alarme',mip(0,.36),Um,Vm,Nm,surface=dashboard,encastre=True,contour=alarm_outline,marge=.007)
    for side,name in ((1,'feux'),(-1,'carbu')):
        wing=[mip(side*.401,.125),mip(side*.401,.326),mip(side*(largeur_visible(.28)-.012),.28),mip(side*(largeur_visible(.20)-.012),.20),mip(side*(largeur_visible(.125)-.012),.125)]
        module(name,mip(side*.5,.23),Um,Vm,Nm,surface=dashboard,encastre=True,contour=wing,marge=.009)
    for u, nom in ((-.26, 'ecran_nav'), (0, 'ecran_vol'), (.26, 'ecran_systemes')): ecran(nom, mip(u, .170), Nm, dashboard)

    # --- Les consoles : le long de chaque paroi, un pan incliné du seuil du verre à la tablette, puis la tablette à
    # hauteur de coude. Elles partent du pupitre, coupées dans son plan, et finissent dans la cloison arrière. Le pan
    # porte une plaque ajustée à son contour, comme la tablette.
    for s in (1, -1):
        pc = Piece('Console | ' + ('gauche' if s > 0 else 'droite'), cockpit)
        shell_stations = [D0C+i*(D1C-D0C)/24 for i in range(25)]
        loft_c(pc, retour_console(s)[:-1]+[anneau(d,s) for d in shell_stations]+[anneau(D1C+.004,s)], CUVE)
        pc.souder()
        support = pc.fin(8)   # The visible shell also defines every instrument pocket.
        def pan(dc):
            a, b = anneau(dc, s)[1:3]
            U = (anneau(dc-s*.001, s)[1]-anneau(dc+s*.001, s)[1]).normalized()
            V = ((a-b)-U*(a-b).dot(U)).normalized(); N = U.cross(V).normalized()
            return a.lerp(b, .5), U, V, N
        def tablette(dc):
            def centre(d):
                a, b = anneau(d, s)[2:4]; return a.lerp(b, .5)
            forward = (centre(dc-.01)-centre(dc+.01)).normalized()
            return centre(dc), forward.cross(Z).normalized(), forward, Z
        front,rear=anneau(D0C+.012,s),anneau(D1C-.008,s)
        # The forward seam follows the dashboard transition, clear of the
        # structural end return; the inner shelf corner has the same sweep.
        front[2]=anneau(D0C+.025,s)[2]
        front[3]=anneau(D0C+.040,s)[3]
        module('flanc_g' if s>0 else 'flanc_d',*pan(4.34),surface=support,encastre=True,
               contour=[front[1],front[2],rear[2],rear[1]])
        for nom in ('gaz',) if s>0 else ('clavier',):
            haut,U,V,N=module(nom,*tablette(4.34),surface=support,encastre=True,
                             contour=[front[2],front[3],rear[3],rear[2]],marge=.010)
            if nom != 'gaz': continue
            # La manette : levier dans la fente sérigraphiée, poignée vers la main.
            pc = Piece('Manette | gaz', cockpit)
            P = haut(.100,.72); tete = P + N * .075 + V * .012
            tige(pc, P - N * .02, tete, .0065, BROSSE, 8)
            tige(pc, tete - U * .006, tete + U * .085, .019, CAOUTCHOUC, 12, bouts=(True, True))
            for k in range(3): tige(pc, tete + U * (.02 + .02 * k), tete + U * (.026 + .02 * k), .0205, GRAPHITE, 12)
            tige(pc, tete + U * .07 + N * .018, tete + U * .07 + N * .026, .0065, SURETE, 8)
            tige(pc, tete + U * .04 + N * .018, tete + U * .04 + N * .023, .005, BROSSE, 8)
            pc.fin(35)

    # --- La cloison derrière le siège : du plancher au seuil, de paroi à paroi ; sa tablette va jusqu'à la paroi arrière,
    # qui monte vers l'arceau. Deux trappes vissées. Les consoles s'y arrêtent.
    zb = F.pont(D1C) - .004; pc = Piece('Cockpit | cloison', cockpit)
    hz = [PL + .02, .3, .5, .7, zb]
    av = [Vector((paroi(D1C, z) - .003, Y(D1C), z)) for z in hz]; av = av + [Vector((-p.x, p.y, p.z)) for p in reversed(av)]
    pc.face(av, CUVE, *uv_int(av), n=(0, -1, 0))
    def regle(dg, z):
        # Le point de la paroi à la hauteur z, sur la génératrice issue du verre en dg.
        x, zs = bord_verre(dg); t = (zs - z) / (zs - PL); df = 3.40 + (dg - F.V0) / (F.VF - F.V0) * 1.70
        return x * (1 - .18 * t), dg + t * (df - dg)
    lo, hi = F.VW, F.VF - .005
    for _ in range(40):
        m = .5 * (lo + hi)
        if regle(m, zb)[1] < D1C: lo = m
        else: hi = m
    bord = [regle(lo + (F.VF - .005 - lo) * k / 10, zb) for k in range(11)]
    tab = [Vector((x - .003, Y(d), zb)) for x, d in bord] + [Vector((-(x - .003), Y(d), zb)) for x, d in reversed(bord)]
    pc.face(tab, CUVE, *uv_int(tab), n=Z)
    for xk in (-.2, .2):
        c = Vector((xk, Y(D1C) - .001, .33)); pave(pc, c, X, Z, Vector((0, -1, 0)), .30, .24, .004, GRAPHITE, .002)
        for a_ in (-1, 1):
            for b_ in (-1, 1): tige(pc, c + X * a_ * .135 + Z * b_ * .105, c + X * a_ * .135 + Z * b_ * .105 - Vector((0, .007, 0)), .006, BROSSE, 6)
    pc.fin(35)

    # --- Le palonnier : pédales articulées au pied de la paroi avant, semelles striées.
    pc = Piece('Pedalier | ensemble', cockpit)
    Vp = Vector((0, -.42, .91)).normalized(); Np = Vector((0, .91, .42)).normalized(); Up = Vp.cross(Np)
    for s in (-1, 1):
        x = s * .15; c = Vector((x, Y(D_PEDALES), PL + .13))
        pave(pc, c, Up, Vp, Np, .10, .22, .016, BROSSE, .003)
        for k in range(4): pave(pc, c + Np * .016 + Vp * (-.075 + .05 * k), Up, Vp, Np, .085, .012, .003, CAOUTCHOUC)
        tige(pc, Vector((x, Y(D_PEDALES + .07), PL + .02)), c - Np * .005 - Vp * .05, .011, BROSSE, 8)
        pave(pc, Vector((x, Y(D_PEDALES + .07), PL)), X, Vector((0, 1, 0)), Z, .07, .06, .04, CUVE, .005)
    pc.fin(35)

    # --- Le manche : carter au plancher, soufflet de caoutchouc (au pied, la pose de pieces_mobiles.py part de sa base),
    # fût, poignée sculptée, gâchette et boutons.
    pc = Piece('Manche | ensemble', cockpit); ym = Y(D_MANCHE); zb = PL + .045
    loft_c(pc, [rect(Vector((0, ym, PL)), X, Vector((0, 1, 0)), .19, .22), rect(Vector((0, ym, zb - .01)), X, Vector((0, 1, 0)), .19, .22),
                rect(Vector((0, ym, zb)), X, Vector((0, 1, 0)), .16, .19)], CUVE, bouts=(False, True))
    tige(pc, Vector((0, ym, zb)), Vector((0, ym, zb + .007)), .075, BROSSE, 16)
    tour(pc, Vector((0, ym, zb + .007)), Z, [(.066, 0), (.069, .010), (.056, .020), (.060, .030), (.049, .040), (.053, .050), (.042, .060),
                                            (.045, .069), (.033, .078), (.021, .085)], CAOUTCHOUC, 16)
    z0 = zb + .085; tige(pc, Vector((0, ym, z0)), Vector((0, ym - .016, z0 + .17)), .014, BROSSE, 10)
    anneaux = [(.0, .0, .019, .018), (.016, .002, .025, .023), (.048, .005, .028, .025), (.080, .008, .027, .024), (.112, .011, .028, .025),
               (.140, .014, .031, .028), (.163, .016, .029, .026), (.175, .018, .021, .019)]
    zg = z0 + .16
    loft_c(pc, [[Vector((math.cos(2 * math.pi * i / 12) * rx, ym - .016 - dy + math.sin(2 * math.pi * i / 12) * ry, zg + h)) for i in range(12)]
                for h, dy, rx, ry in anneaux], CAOUTCHOUC)
    pave(pc, Vector((0, ym - .045, zg + .10)), X, Z, Vector((0, -1, 0)), .018, .03, .01, SURETE, .003)
    tige(pc, Vector((0, ym - .036, zg + .168)), Vector((0, ym - .036, zg + .182)), .009, BROSSE, 10)
    tige(pc, Vector((.021, ym - .026, zg + .158)), Vector((.028, ym - .026, zg + .162)), .005, LIT['red'], 8)
    tige(pc, Vector((0, ym - .020, zg + .176)), Vector((0, ym - .020, zg + .183)), .006, LIT['amber'], 8)
    pc.fin(35)

    # --- Le siège baquet, d'après le concept : dossier et assise à bourrelets ronds, coussins capitonnés, appui-tête
    # rembourré, coque basse de graphite sur glissières, rails d'éjection, harnais à réglages de cuir fauve.
    Vb = Vector((0, math.sin(INCL), math.cos(INCL))); Nb = Vector((0, -math.cos(INCL), math.sin(INCL)))
    J = Vector((0, Y(D_DOS), Z_DOS)) - Vb * ((Z_DOS - .33) / math.cos(INCL))   # pied du dossier, à l'assise
    def dos(u, s, w): return J + X * u + Vb * s + Nb * w
    def bourrelets(W, B):
        # Demi-section d'un coussin à bourrelet rond : (u, w), du milieu plat vers le bord, puis le dessous.
        controls = [(.50 * W, 0), (.60 * W, .012), (.69 * W, .045), (.76 * W, B - .025), (.83 * W, B), (.92 * W, B - .006), (.985 * W, B - .035), (W, .01), (.96 * W, -.06)]
        # Rounded upholstery needs a curved cross-section, not the chamfers of
        # the metal bucket. Interpolate only the bolster, leaving the pad flat.
        result = []
        for i in range(len(controls)-1):
            a, b, d, e = [Vector(controls[max(0,min(j,len(controls)-1))]) for j in (i-1,i,i+1,i+2)]
            for k in range(3):
                t = k/3
                p = .5*((2*b)+(-a+d)*t+(2*a-5*b+4*d-e)*t*t+(-a+3*b-3*d+e)*t*t*t)
                result.append(tuple(p))
        return result+[controls[-1]]
    def miroir(cote, f): return [f(-u, w) for u, w in reversed(cote)] + [f(u, w) for u, w in cote]
    def section_dos(s):
        t = s / .70; W = .25 - .035 * t * t; B = .115 - .05 * max(0.0, t - .55) / .45
        return miroir(bourrelets(W, B), lambda u, w: dos(u, s, w))
    pc = Piece('Siege | ensemble', cockpit)
    loft_c(pc, [section_dos(s) for s in (0.0, .06, .18, .32, .46, .58, .66, .70)], CUIR)
    for sc in (.10, .235, .37, .505): pave(pc, dos(0, sc, 0), X, Vb, Nb, .235, .118, .016, CUIR, .007)   # le capitonnage
    # L'assise : sections en travers, du dossier au bord avant roulé ; deux coussins capitonnés.
    def zc(d): return .33 + (D_DOS - .22 - d) * .07
    da = D_DOS - .22
    def section_assise(d, k=1.0, dz=0.0):
        return miroir(bourrelets(.25, .078 * k), lambda u, w: Vector((u, Y(d), zc(d) + dz + w - (.02 if w < 0 else 0))))
    loft_c(pc, [section_assise(da), section_assise(da - .12), section_assise(da - .26), section_assise(da - .33, .7), section_assise(da - .36, .35, -.03)], CUIR)
    for dk in (da - .085, da - .22): pave(pc, Vector((0, Y(dk), zc(dk))), X, Vector((0, 1, 0)), Z, .235, .125, .014, CUIR, .006)
    # L'appui-tête : bloc à coins arrondis, bord avant roulé, coussin central ; sur deux tiges.
    def rond(c, hu, hs, k):
        radius = min(hu, hs)*k
        return [c+X*(sx*(hu-radius)+radius*math.cos(t))+Vb*(sy*(hs-radius)+radius*math.sin(t))
                for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270))
                for t in [math.radians(start+i*90/4) for i in range(5)]]
    ca = dos(0, .81, 0)
    loft_c(pc, [rond(ca - Nb * .05, .135, .095, .35), rond(ca + Nb * .045, .135, .095, .35), rond(ca + Nb * .07, .115, .075, .35)], CUIR)
    pave(pc, ca + Nb * .07, X, Vb, Nb, .15, .09, .008, CUIR, .004)
    for u in (-.07, .07): tige(pc, dos(u, .66, -.03), dos(u, .74, -.03), .007, BROSSE, 8, bouts=(True, True))
    # La coque : flancs bas le long de l'assise, dos de coque, fond sur glissières, rails d'éjection, coffre du parachute.
    for sx in (-1, 1):
        x = sx * .262
        flanc = [Vector((0, Y(da - .36), PL + .10)), Vector((0, Y(da - .36), zc(da - .36) - .03)), Vector((0, Y(da + .02), zc(da) + .02)), Vector((0, Y(da + .08), PL + .10))]
        loft_c(pc, [[p + X * (x - .006) for p in flanc], [p + X * (x + .006) for p in flanc]], GRAPHITE)
        tige(pc, Vector((x * .66, Y(da + .27), PL)), dos(sx * .17, .98, -.13), .016, BROSSE, 8, bouts=(True, True))
        pave(pc, Vector((sx * .17, Y(da - .05), PL)), X, Vector((0, 1, 0)), Z, .035, .62, .022, BROSSE, .004)
    coque = [dos(-.25, -.02, -.068), dos(.25, -.02, -.068), dos(.215, .70, -.068), dos(-.215, .70, -.068)]
    loft_c(pc, [coque, [p - Nb * .022 for p in coque]], GRAPHITE)
    pave(pc, Vector((0, Y(da - .17), PL + .02)), X, Vector((0, 1, 0)), Z, .44, .40, zc(da - .17) - .10 - PL - .02, GRAPHITE, .01)
    pave(pc, dos(0, .95, -.20), X, Vb, Nb, .30, .16, .12, GRAPHITE, .01)
    # Le harnais : bretelles par-dessus le dossier, ventrale et sous-cutale à la boucle ; réglages en cuir fauve.
    def sangle(a, b, n, w=.045, m=SANGLE):
        v = (b - a).normalized(); u = v.cross(n).normalized(); pave(pc, (a + b) / 2, u, v, u.cross(v), w, (b - a).length, .004, m)
    boucle = Vector((0, Y(da - .17), zc(da - .17) + .018))
    for sx in (-1, 1):
        sangle(dos(sx * .10, .71, .02), dos(sx * .075, .22, .02), Nb)
        sangle(dos(sx * .09, .56, .025), dos(sx * .085, .46, .025), Nb, .052, BOUCLE)
        sangle(Vector((sx * .21, Y(da - .06), zc(da - .06) + .07)), boucle + X * sx * .03, Z)
        sangle(Vector((sx * .19, Y(da - .09), zc(da - .09) + .06)), Vector((sx * .13, Y(da - .12), zc(da - .12) + .03)), Z, .055, BOUCLE)
    sangle(Vector((0, Y(da - .34), zc(da - .34) + .01)), boucle, Z, .04)
    tige(pc, boucle, boucle + Z * .012, .034, BROSSE, 14)
    pc.fin(65)

    import finitions_cockpit
    finitions_cockpit.construire(g, locals())
