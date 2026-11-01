"""Détails v3 : des détails légers dehors, de la vie dedans, posés sur la scène de travail sans changer la silhouette.

Usage : blender -b vaisseau_travail.blend --python details_v3.py   (construit, sauve la scène, exporte le GLB)
puis    python paquet_moteur.py

Rejouable : chaque objet créé porte la propriété « v3 » et disparaît au lancement suivant.
Rien d'existant n'est déplacé ; seuls le cœur des trois tuyères et le feu rouge de poupe changent de matériau.

- Dehors : baguettes de chine effilées, tuyères d'attitude percées dans la peau, sonde de nez, feux anticollision, à éclats et
  de formation ; volets de bord de fuite avec carénages d'articulation et déperditeurs ; ailettes ventrales et
  de nez ; écopes NACA, trappe de secours fléchée, poignée et marchepied, chemin antidérapant, phares.
- Dedans : couples sur les parois arrière, faisceaux de câbles bridés, poignées, extincteur, tuyau
  d'oxygène du siège.
Les sorties des propulseurs d'attitude sont imprimées : ShipPlume.hlsli les recopie.
Les quatre volets bougent dans le moteur comme des élevons : attribut _POSE de 3 à 6 et pivots « Pivot | volet … »,
sur le modèle de pieces_mobiles.py.
"""
import bpy, math, os, sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from design_v2 import Piece, block, tube, lathe, _ring, oriented
import numpy as np
import pieces_mobiles
import forme as fm

TAG = 'v3'
for o in list(bpy.data.objects):
    if o.get(TAG): bpy.data.objects.remove(o, do_unlink=True)

cockpit = bpy.data.collections['Spaceship_Cockpit']; details = bpy.data.collections['Spaceship_Details']
M = bpy.data.materials

def matiere(name, color, metallic=0, roughness=.5, emission=None):
    # Créé s'il manque, réglé à chaque lancement : la scène de travail garde les valeurs d'ici.
    m = M.get(name) or M.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1); p.inputs['Emission Strength'].default_value = emission
    return m

mid = M['Jeu | Blindage moyen']; sombre = M['Jeu | Joint encrasse']
edge = M['Jeu | Metal brosse']; dark = M['Jeu | Structure graphite']; graphite = M['Jeu | Ceramique graphite']
rubber = M['Jeu | Caoutchouc']; rouge = M['Jeu | Livree rouge']; accent = M['Jeu | Peinture marquage']
structure = M['Jeu | Structure cockpit']; securite = M['Jeu | Plastique securite']; noir = M['Jeu | Antireflet']
# Rôles lus par le moteur (paquet_moteur.py, ROLES) : leur émission s'anime en vol.
# Une émission de 1 vaut un blanc au soleil. La nuit, l'exposition vaut environ 130 fois celle de midi, mesurée sur
# la capture de nuit, et la courbe du film blanchit ce qui la dépasse. Les feux de position et de formation, vers 0,01,
# restent rouges et verts la nuit et s'effacent en plein jour, comme les vrais. Les éclats et les feux anticollision
# se voient de jour ; la nuit, ils blanchissent.
chaude = matiere('Jeu | Tuyere chaude', (.30, .62, 1.0), 0, .4, 2.5)
eclat = matiere('Jeu | Feu a eclats', (1.0, .96, .9), 0, .3, 6.0)
anticol = matiere('Jeu | Feu anticollision', (1.0, .04, .02), 0, .3, .6)
# Feux de position de la poupe : le rouge quitte le « Signal rouge » des voyants du cockpit, qui garde son éclat.
matiere('Jeu | Feu vert', (.02, .6, .12), .05, .4, .012)
position = matiere('Jeu | Feu de position rouge', (.8, .025, .012), .05, .42, .012)
o = bpy.data.objects['Poupe | cadre et fond']
for k, m in enumerate(o.data.materials):
    if m and m.name == 'Jeu | Signal rouge': o.data.materials[k] = position

def fini(pc):
    o = pc.done(); o[TAG] = 1
    return o

# Le cœur des trois tuyères de poupe suit les gaz : il quitte le cyan des voyants du cockpit.
for i in (1, 2, 3):
    o = bpy.data.objects[f'Tuyere | {i}']
    for k, m in enumerate(o.data.materials):
        if m and m.name == 'Jeu | Affichage cyan': o.data.materials[k] = chaude

# Géométrie d'origine (design_v2.py) : la pyramide, les facettes du dos.
apex = Vector((0, -7.18, 0)); top = Vector((0, 2.3375, 2.10)); chine = Vector((3.10, 2.59525, .038))
bottom = Vector((0, 2.85, -2))
sorties = {}

pe = Piece('Coque | v3 details', details)
def chine_pt(u, s=1, z=0.0): return Vector((s * 3.10 * u, -7.18 + 9.775 * u, z))
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))

# ---------------------------------------------------------------------------------------------------
# Petites pièces de peau sur les facettes, paramétrées comme dans design_v2 : u de la pointe à la poupe,
# v de l'arête dorsale (au ventre, de la joue) vers la chine (au ventre, vers la quille). Les tôles
# affleurent à 12 mm de la peau, les décalques à 12,3 mm. Chaque pièce tient dans une tôle, à l'écart
# des trappes et grilles de design_v2.
low = Vector((3.10, 2.60475, -.038)); cheek = Vector((2.74, 2.6369, -.295))
LEVE = .0123
reprise = M['Jeu | Peinture reprise']
formation = matiere('Jeu | Feu de formation', (.35, .95, .25), 0, .4, .01)
antiderapant = matiere('Jeu | Antiderapant', (.045, .048, .05), 0, .92)
phare = matiere('Jeu | Phare', (.02, .025, .03), .2, .08)
def pt(u, v, side=1, ra=top, rb=chine):
    # Au dessus, le point descend sur sa facette creusée (forme.py), comme dans design_v2.
    p = apex.lerp(ra.lerp(rb, v), u); p.x *= side
    if ra is top and rb is chine: p.z = fm.dessus_z(p.x, p.y)
    return p
def nrm(side, ra=top, rb=chine, u=None, v=None):
    if ra is top and rb is chine: return fm.normale(fm.facette(u, u * v), side)
    n = (ra - apex).cross(rb - apex); n.x *= side; c = (apex + ra + rb) / 3; c.x *= side; n.normalize()
    return n if n.dot(Vector((c.x, 0, c.z))) > 0 else -n
def le_long(v, side, ra=top, rb=chine, u=.9):
    # Le sens de l'écoulement sur la facette, vers la poupe, autour de u.
    return (pt(u + .01, v, side, ra, rb) - pt(u - .01, v, side, ra, rb)).normalized()
def quad(u0, u1, v0, v1, side, ra=top, rb=chine, h=LEVE):
    n = nrm(side, ra, rb, (u0 + u1) / 2, (v0 + v1) / 2)
    return oriented([pt(u, v, side, ra, rb) + n * h for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))], n), n
def decale(pts, n, d):
    # Contour plan convexe, tourné autour de n, décalé de d vers l'intérieur ; d < 0 vers l'extérieur.
    lignes = []
    for i in range(len(pts)):
        e = (pts[(i + 1) % len(pts)] - pts[i]).normalized(); lignes.append((pts[i] + n.cross(e) * d, e))
    out = []
    for (p1, e1), (p2, e2) in zip(lignes[-1:] + lignes[:-1], lignes):
        c = e1.cross(e2); out.append(p1 + e1 * (p2 - p1).cross(e2).dot(c) / c.length_squared)
    return out
def cadre(pc, pts, n, d, mat):
    # Bande entre un contour et son décalage de d vers l'extérieur : joint, liseré.
    o = decale(pts, n, -d)
    for i in range(len(pts)):
        j = (i + 1) % len(pts); pc.face(oriented([pts[i], pts[j], o[j], o[i]], n), mat)
def carenage(pc, c, d, n, L, W, H, mat):
    # Carénage profilé couché sur la peau, de son culot en c vers l'avant sur L : demi-sections elliptiques.
    w = n.cross(d).normalized()
    rings = [[c - d * t * L + (w * math.cos(a) * W / 2 + n * math.sin(a) * H) * s for a in (math.pi * k / 6 for k in range(7))]
             for t, s in ((0, .9), (.12, 1), (.45, 1), (.8, .6), (1, .12))]
    pc.loft(rings, mat, (True, True))
def epaisseur(f):
    # Profil hexagonal : nul aux bords, épais au tiers avant.
    return .5 * f / .3 if f < .3 else .5 - .2 * (f - .3) / .5 if f < .8 else .3 * (1 - f) / .2

# ---------------------------------------------------------------------------------------------------
# Peau : rien ne dépasse en arête vive face à l'écoulement. Baguettes de chine effilées aux deux bouts.
for s in (-1, 1):
    tube(pe, chine_pt(.05, s), chine_pt(.10, s), .004, graphite, 6, .03, (True, False))
    tube(pe, chine_pt(.10, s), chine_pt(.89, s), .03, graphite, 6, caps=(False, False))
    tube(pe, chine_pt(.89, s), chine_pt(.93, s), .03, graphite, 6, .004, (False, True))

def tuyere_rcs(c, n, d, r=.022, suie=3.2):
    # Tuyère d'attitude percée dans la peau, comme sur les navettes : gorge sombre, bague de métal, auréole de suie.
    W = n.cross(d).normalized(); U = W.cross(n)
    rings = [_ring(c + n * h, U, W, r * k, 16) for k, h in ((suie, 0), (1.35, .0002), (1.0, .0004))]
    for (ra_, rb_), m in zip(((rings[0], rings[1]), (rings[1], rings[2])), (sombre, edge)):
        for i in range(16):
            j = (i + 1) % 16; pe.face(oriented([rb_[i], rb_[j], ra_[j], ra_[i]], n), m)
    pe.face(oriented(_ring(c + n * .0006, U, W, r, 16), n), noir)
    return c + n * .0006
# Nez, à 1,6 m de la pointe : deux tuyères de part et d'autre de l'arête dorsale vers le haut, deux de part et
# d'autre de la quille vers le bas, deux de chaque côté, près de la chine, vers l'extérieur. Chaque jet sort entre
# ses deux tuyères (ShipPlume.hlsli).
un = (-5.6 - apex.y) / (top.y - apex.y); ubn = (-5.6 - apex.y) / (bottom.y - apex.y)
haut, bas, cote = [], [], {1: [], -1: []}
for s in (-1, 1):
    nt, nb = nrm(s, u=un, v=.5), nrm(s, cheek, bottom)
    haut.append(tuyere_rcs(pt(un, .05, s) + nt * LEVE, nt, le_long(.05, s, u=un)))
    bas.append(tuyere_rcs(pt(ubn, .95, s, cheek, bottom) + nb * LEVE, nb, le_long(.95, s, cheek, bottom, ubn)))
    cote[s].append(tuyere_rcs(pt(un, .95, s) + nt * LEVE, nt, le_long(.95, s, u=un)))
    cote[s].append(tuyere_rcs(pt(ubn, .05, s, cheek, bottom) + nb * LEVE, nb, le_long(.05, s, cheek, bottom, ubn)))
JETS_NEZ = [((haut[0] + haut[1]) / 2, Z), ((bas[0] + bas[1]) / 2, -Z),
            ((cote[1][0] + cote[1][1]) / 2, X), ((cote[-1][0] + cote[-1][1]) / 2, -X)]
# Pointes de poupe : vers le haut sur le dos près de la chine, vers le bas sur la facette étroite sous la chine,
# vers l'extérieur sur le chant de la chine.
JETS_POUPE = []
for s in (-1, 1):
    nt, nl = nrm(s, u=.955, v=.965), nrm(s, low, cheek)
    up = tuyere_rcs(pt(.955, .965, s) + nt * LEVE, nt, le_long(.965, s, u=.955))
    dn = tuyere_rcs(pt(.955, .5, s, low, cheek) + nl * .001, nl, le_long(.5, s, low, cheek, .955))
    ch = chine_pt(.955, s); Xs = Vector((s, 0, 0))
    out = tuyere_rcs(ch + Xs * .0005, Xs, Y, .018, 1.6)
    JETS_POUPE += [(up, Z), (dn, -Z), (out, Xs)]
JETS = JETS_POUPE[3:] + JETS_POUPE[:3] + JETS_NEZ   # l'ordre de ShipPlume.hlsli : +x d'abord, puis -x, puis le nez

# Feux à éclats blancs sur le cadre de poupe, à côté des feux de position, dans la partie pleine des pointes.
Nr = Vector((0, 1, .125)).normalized(); Zr = Vector((0, -.125, 1)).normalized()
for s in (-1, 1):
    c = Vector((0, 2.6, 0)) + Vector((s * 2.86, 0, 0)) + Nr * .04
    block(pe, c, Vector((1, 0, 0)), Zr, Nr, .04, .03, .012, eclat, .004)
    sorties['eclat' + ('+' if s > 0 else '-')] = c + Nr * .012
# Sonde de nez et son carénage conique.
lathe(pe, apex + Y * .10, -Y, [(.055, 0), (.045, .10), (.022, .22)], edge, 12)
tube(pe, apex - Y * .12, apex - Y * .80, .018, edge, 10, .010)
tube(pe, apex - Y * .80, apex - Y * .90, .006, dark, 8, caps=(False, True))
for k in range(3): tube(pe, apex - Y * (.30 + .12 * k), apex - Y * (.36 + .12 * k), .0175 - .0025 * k, rouge, 10)
# Feux anticollision : dôme rouge sur un socle profilé, sur l'arête dorsale et sous la quille.
SOCLE = [(.085, 0), (.075, .008), (.06, .015), (.047, .02)]; DOME = [(.045, 0), (.04, .02), (.025, .035), (0, .04)]
cd = Vector((0, 2.10, fm.dessus_z(0, 2.10)))   # sur l'arête arrière, derrière le chemin de passage
lathe(pe, cd - Z * .005, Z, SOCLE, dark, 16); lathe(pe, cd + Z * .015, Z, DOME, anticol, 16)
uq = (1.2 - apex.y) / (bottom.y - apex.y); cq = Vector((0, 1.2, uq * bottom.z))
lathe(pe, cq + Z * .005, -Z, SOCLE, dark, 16); lathe(pe, cq - Z * .015, -Z, DOME, anticol, 16)
sorties['anticollision dos'] = cd + Z * .055; sorties['anticollision quille'] = cq - Z * .055

def volet(nom, pose, u0, v0, v1, side, ra, rb, charnieres, deperditeurs=()):
    # Gouverne de bord de fuite : panneau presque affleurant, 2,5 mm au-dessus des tôles et chanfreiné, jeu sombre de 8 mm, carénages
    # d'articulation sur la partie fixe devant la charnière, déperditeurs d'électricité statique au bord de fuite.
    # Le panneau et ses déperditeurs tournent autour de la charnière (ShipPose) ; le jeu et les carénages restent fixes.
    pc = Piece(nom, details); n = nrm(side, ra, rb, (u0 + 1) / 2, (v0 + v1) / 2)
    bord, _ = quad(u0, .997, v0, v1, side, ra, rb)
    cadre(pe, bord, n, .008, sombre)
    pc.loft([[p - n * (LEVE - .006) for p in decale(bord, n, .003)], [p + n * (.0145 - LEVE) for p in decale(bord, n, .009)]], mid, (False, True))
    for v in charnieres:
        d = le_long(v, side, ra, rb, u0)
        carenage(pe, pt(u0, v, side, ra, rb) - d * .012 + n * .009, d, n, .34, .07, .045, mid)
    for v in deperditeurs:
        d = le_long(v, side, ra, rb, .98); a = pt(.99, v, side, ra, rb) + n * .014
        tube(pc, a, a + d * .13, .003, graphite, 6, caps=(False, False)); tube(pc, a + d * .13, a + d * .15, .002, edge, 6)
    o = fini(pc)
    # La charnière : le bord avant du panneau, au dessus des tôles. Un angle positif lève le bord de fuite hors de la peau.
    h0, h1 = pt(u0, v0, side, ra, rb) + n * .012, pt(u0, v1, side, ra, rb) + n * .012
    axe = (h1 - h0).normalized()
    if axe.cross(le_long((v0 + v1) / 2, side, ra, rb, u0)).dot(n) < 0: axe = -axe
    pieces_mobiles.pose(o, np.full(len(o.data.vertices), float(pose)))
    pieces_mobiles.pivot('Pivot | volet ' + nom.split(' | ')[1], (h0 + h1) / 2, axe, details)
    return o
for s in (-1, 1):
    cote = 'gauche' if s > 0 else 'droit'
    # Le volet du dessus reste sur la facette arrière, derrière le pli de A.
    volet('Volet | dessus ' + cote, 3 if s > 0 else 4, .94, .40, .74, s, top, chine, (.46, .58), (.50, .62, .72))
    volet('Volet | dessous ' + cote, 5 if s > 0 else 6, .955, .08, .40, s, cheek, bottom, (.14, .37))

    # Ailette ventrale, normale à la facette basse, en flèche, au tiers arrière.
    n = nrm(s, cheek, bottom); span = Vector((n.x, 0, n.z)).normalized(); d = le_long(.68, s, cheek, bottom, .88)
    T = span.cross(d).normalized(); r0 = pt(.83, .68, s, cheek, bottom); corde = (pt(.93, .68, s, cheek, bottom) - r0).length
    def fp(q, f, e):
        le = (r0 - span * .03).lerp(r0 + span * .38 + d * .45, q)
        return le + d * f * (corde + (.35 - corde) * q) + T * e * (.03 + (.015 - .03) * q)
    sec = lambda q: [fp(q, f, epaisseur(f)) for f in (0, .3, .8, 1)] + [fp(q, f, -epaisseur(f)) for f in (.8, .3)]
    pe.loft([sec(0), sec(1)], mid, (False, True))
    tube(pe, fp(.08, 0, 0), fp(1, 0, 0), .006, edge, 6)

    # Ailette de nez : lame horizontale le long de la chine, bord d'attaque en flèche ; la baguette de chine cache sa racine.
    Xs = Vector((s, 0, 0))
    a, b = chine_pt(.15, s), chine_pt(.31, s); lame = [a, b, b + Xs * .10, chine_pt(.25, s) + Xs * .10]
    pe.loft([[p - Z * .004 for p in lame], [p + Z * .004 for p in lame]], mid, (True, True))

    # Écopes NACA : fond sombre qui s'évase vers l'arrière, lèvre arrondie à demi noyée. Une sur le dos, une au ventre.
    for u0, u1, v, ra, rb in ((.735, .785, .885, top, chine), (.65, .70, .79, cheek, bottom)):
        n = nrm(s, ra, rb, (u0 + u1) / 2, v); d = le_long(v, s, ra, rb, (u0 + u1) / 2); w = n.cross(d).normalized()
        a = pt(u0, v, s, ra, rb) + n * LEVE; b = pt(u1, v, s, ra, rb) + n * LEVE
        pe.face(oriented([a + w * .02, b + w * .055, b - w * .055, a - w * .02], n), noir)
        tube(pe, b - w * .065, b + w * .065, .006, edge, 8, caps=(True, True))

    # Trappe de secours de la verrière, liseré rouge et flèche qui la désigne depuis la chine.
    # Près du pourtour de la bulle, sur la facette de la verrière ; la flèche vient de l'arrière.
    q, n = quad(.66, .71, .47, .53, s)
    pe.face(q, reprise); cadre(pe, q, n, .012, rouge)
    tip = pt(.722, .50, s) + n * LEVE; queue = pt(.775, .50, s) + n * LEVE; e = (tip - queue).normalized(); w = n.cross(e)
    pe.face(oriented([queue + w * .007, queue - w * .007, tip - e * .04 - w * .007, tip - e * .04 + w * .007], n), rouge)
    pe.face(oriented([tip, tip - e * .045 + w * .022, tip - e * .045 - w * .022], n), rouge)
    # Poignée d'accès à trappe poussoir au bord de la chine, marchepied encastré juste dessous, sous la chine : rien ne dépasse.
    q, n = quad(.60, .62, .955, .985, s)
    pe.face(q, reprise); cadre(pe, q, n, .005, sombre)
    q, n = quad(.597, .612, .25, .75, s, low, cheek, .001)
    pe.face(q, noir); cadre(pe, q, n, .006, edge)
    pa, pb = pt(.5995, .5, s, low, cheek), pt(.6095, .5, s, low, cheek)
    tube(pe, pa + n * .004, pb + n * .004, .004, edge, 8, caps=(True, True))   # barre affleurante au fond de l'encoche

    # Feux de formation, bandes électroluminescentes au bord de la chine ; chemin antidérapant le long du dos.
    for u0, u1 in ((.40, .44), (.82, .86)): pe.face(quad(u0, u1, .945, .962, s, h=LEVE + .0008)[0], formation)
    pe.face(quad(.905, .95, .012, .06, s)[0], antiderapant)
    # Phares d'atterrissage sous le nez, près de la quille.
    n = nrm(s, cheek, bottom); c = pt(.44, .95, s, cheek, bottom) + n * LEVE; U = le_long(.95, s, cheek, bottom, .44); W = n.cross(U)
    ring_a, ring_b = _ring(c, U, W, .035, 16), _ring(c, U, W, .045, 16)
    for i in range(16):
        j = (i + 1) % 16; pe.face(oriented([ring_a[i], ring_a[j], ring_b[j], ring_b[i]], n), edge)
    pe.face(oriented(ring_a, n), phare)
fini(pe)

# UV de peinture à l'échelle du monde, une tuile pour 2 m, comme le reste de la coque.
Xr = Vector((1, 0, 0)); Ya = Vector((0, 1, 0))
for o in details.objects:
    if not o.get(TAG) or o.type != 'MESH': continue
    me = o.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        nn = poly.normal; t = Ya - nn * Ya.dot(nn)
        if t.length < .3: t = Xr - nn * nn.x
        t.normalize(); b = nn.cross(t)
        for li in poly.loop_indices:
            p = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (p.dot(t) / 2, p.dot(b) / 2)

# ---------------------------------------------------------------------------------------------------
# Cockpit : parois qui descendent du seuil de la bulle (forme.py), comme dans design_v2.
def plane(p, n): n = n.normalized(); return n, n.dot(p)
sol = plane(Vector((0, -2.65, -.30)), Vector((0, .2, 2.41)))
def fz(y): n, k = sol; return (k - n.y * y) / n.z
def t_de(y, side):
    a = fm.GY1 - fm.GYC if y > fm.GYC else fm.GYC - fm.GY0
    t = math.acos(max(-1.0, min(1.0, (y - fm.GYC) / a))); return t if side > 0 else 2 * math.pi - t
def paroi(y, side):
    # Seuil, descente, normale intérieure de la paroi et sa tangente horizontale, à l'ordonnée y.
    t = t_de(y, side); Q = fm.seuil(t); d = fm.descente(t); n_out = fm.normale_goutte(t)
    tg = Z.cross(n_out); N = tg.cross(d).normalized()
    if N.dot(-n_out) < 0: N = -N
    return Q, d, N, (tg if tg.y > 0 else -tg)
def sur_paroi(y, z, side):
    Q, d, N, U = paroi(y, side); return Q + d * ((Q.z - z) / -d.z)
def jusquau_sol(p, d):
    n, k = sol; return (k - n.dot(p)) / n.dot(d)

ci = Piece('Cockpit | v3 equipement', cockpit)
def faisceau(points, normales):
    # Trois câbles côte à côte, écartés de la paroi, une bride tous les 25 cm.
    for (a, b), N in zip(zip(points, points[1:]), normales):
        d = (b - a).normalized(); V = N.cross(d).normalized()
        for k, (r, m) in enumerate(((.009, rubber), (.012, graphite), (.008, securite))):
            o = N * (.05 + r) + V * (k - 1) * .022
            tube(ci, a + o, b + o, r, m, 6, caps=(False, False))
        L = (b - a).length
        for j in range(max(1, int(L / .25))):
            c = a + d * (j + .5) * L / max(1, int(L / .25))
            block(ci, c, d, V, N, .018, .085, .075, edge, .003)
for s in (-1, 1):
    # Couples en T sur la paroi arrière, derrière la console, du rail au plancher, hors de la trappe (y = -0,30).
    couples = []
    for y in (-.66, -.06):
        Q, d, N, U = paroi(y, s); hq = Q + d * .075; L = jusquau_sol(hq, d); c = hq + d * L / 2
        block(ci, c, U, d, N, .04, L, .035, structure); block(ci, c + N * .035, U, d, N, .075, L, .006, structure)
        for k in range(1, int(L / .12)): tube(ci, hq + d * k * .12 + N * .041 + U * .028, hq + d * k * .12 + N * .045 + U * .028, .004, edge, 6)
        couples.append((hq, d, N))
    # Poignée de maintien sous le rail, au-dessus de la trappe.
    Q, d, N, U = paroi(-.30, s); pg = Q + d * .10
    for e in (-1, 1):
        q = pg + U * e * .10; tube(ci, q, q + N * .055, .011, accent, 8, caps=(True, True))
        block(ci, q, U, d, N, .04, .05, .006, edge, .002)
    tube(ci, pg - U * .10 + N * .055, pg + U * .10 + N * .055, .012, accent, 10, caps=(True, True))
    # Faisceaux : au pied de la paroi avant, sous l'aile, puis derrière la console, jusqu'au fond.
    ys = (-2.28, -1.95, -1.58); av = [sur_paroi(y, fz(y) + .14, s) for y in ys]
    faisceau(av, [paroi(y, s)[2] for y in ys[1:]])
    faisceau([sur_paroi(-1.95, fz(-1.95) + .14, s), sur_paroi(-1.95, .38, s)], [paroi(-1.95, s)[2]])
    ys = (-.80, -.50, -.20, .10); ar = [sur_paroi(y, fz(y) + .20, s) for y in ys]
    faisceau(ar, [paroi(y, s)[2] for y in ys[1:]])
    # Extincteur à droite du pilote, sur la paroi arrière, entre les couples.
    if s < 0:
        Q, d, N, U = paroi(-.36, s); b = Q + d * (jusquau_sol(Q, d) - .40)
        block(ci, b, U, d, N, .08, .34, .008, edge, .002)
        ax = b + N * .055
        tube(ci, ax + d * .16, ax - d * .16, .045, rouge, 16, caps=(True, True))
        for h in (-.10, .10): tube(ci, ax + d * (h - .008), ax + d * (h + .008), .048, edge, 16, caps=(True, True))
        tube(ci, ax - d * .16, ax - d * .20, .018, graphite, 10)
        block(ci, ax - d * .205, U, d, N, .07, .012, .02, graphite, .002)
        tube(ci, ax - d * .19 + U * .02, ax + U * .06 - d * .05, .007, rubber, 6, caps=(True, True))

# Tuyau d'oxygène, du flanc droit du siège au pied de la console droite, en anneaux annelés.
a = Vector((-.285, -1.12, .20)); b = sur_paroi(-1.18, .10, -1) + paroi(-1.18, -1)[2] * .31; m = (a + b) / 2 - Vector((0, 0, .12))
prev = a
for k in range(1, 25):
    t = k / 24; p = a * (1 - t) ** 2 + m * 2 * t * (1 - t) + b * t * t
    tube(ci, prev, p, .016 if k % 2 else .014, rubber, 8, caps=(False, False)); prev = p
tube(ci, a - Vector((.02, 0, 0)), a + Vector((.02, 0, 0)), .02, edge, 10, caps=(True, True))
fini(ci)

for k, v in sorties.items(): print('V3 SORTIE', k, tuple(round(x, 3) for x in v))
for p, d in JETS: print('V3 JET', tuple(round(x, 3) for x in p), tuple(round(x, 3) for x in d))
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.get(TAG))
print('V3 TRIANGLES', tris)

if '--sans-export' not in sys.argv:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'vaisseau_travail.blend'))
    import exporter
    exporter.exporter(ROOT)
