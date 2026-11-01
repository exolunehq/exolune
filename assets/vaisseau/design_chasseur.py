"""Le chasseur détaillé, d'après la maquette validée le 2026-10-31 (forme_chasseur.py) : coque continue peinte dans un
atlas unique, bulle et son cadre, ailes à nervure et quatre élevons, prises d'air à lames, capots et quatre tuyères,
feux, jets d'attitude, antennes, écopes ; le cockpit de cockpit_chasseur.py.

Usage : python textures_chasseur.py, puis
        blender -b --factory-startup --python design_chasseur.py [-- --sans-export] [--rendus DOSSIER]
Écrit vaisseau_travail.blend et vaisseau.glb (exporter.py), puis python paquet_moteur.py. Avec --sans-export, rien
n'est écrit dans ce dossier ; --rendus fait les vues de contrôle dans DOSSIER.
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
import forme_chasseur as F, textures_chasseur as T
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SANS_EXPORT = '--sans-export' in ARGS
RENDUS = ARGS[ARGS.index('--rendus') + 1] if '--rendus' in ARGS else None
if RENDUS and not os.path.isabs(RENDUS):
    RENDUS = os.path.abspath(os.path.join(ROOT, '..', '..', RENDUS))
Y = F.Y

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)
sc = bpy.context.scene
ship = bpy.data.collections.new('Spaceship'); sc.collection.children.link(ship)
hull = bpy.data.collections.new('Spaceship_Hull'); ship.children.link(hull)
cockpit = bpy.data.collections.new('Spaceship_Cockpit'); ship.children.link(cockpit)

# --- Matières. La peinture, le métal et l'usure de toutes les pièces peintes viennent de l'atlas (textures_chasseur.py),
# sur UVDetail : un seul matériau « Jeu | Tole ». Les autres sont unis : verre, cuve, feux, foyers, cockpit.
def material(name, color, metallic=0, roughness=.5, emission=None):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Metallic'].default_value = metallic; p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1); p.inputs['Emission Strength'].default_value = emission
    return m
def image(nom, donnees):
    im = bpy.data.images.load(os.path.join(ROOT, nom), check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if donnees else 'sRGB'; im.pack(); return im
sortie = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
sortie.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
def tole():
    m = material('Jeu | Tole', (1, 1, 1), 0, 1); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVDetail'
    def tex(nom, donnees):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = image(nom, donnees); nt.links.new(uv.outputs['UV'], n.inputs['Vector']); return n
    nt.links.new(tex('chasseur_couleur.png', False).outputs['Color'], p.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex('chasseur_metal_rugosite.png', True).outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], p.inputs['Roughness']); nt.links.new(sep.outputs['Blue'], p.inputs['Metallic'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = 'UVDetail'
    nt.links.new(tex('chasseur_normale.png', True).outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = sortie; nt.links.new(tex('chasseur_occlusion.png', True).outputs['Color'], g.inputs['Occlusion'])
    return m
TOLE = tole()
TOLE_INT = material('Jeu | Structure cabine', (.115, .130, .140), .025, .64)
VERRE = material('Jeu | Verriere fumee', (.075, .16, .20), .1, .16); VERRE.diffuse_color = (.075, .16, .20, .22)
VERRE.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = .22; VERRE.surface_render_method = 'BLENDED'; VERRE.use_transparency_overlap = False
CUVE = material('Jeu | Structure graphite', (.055, .068, .075), .6, .46)
FENETRE = material('Jeu | Fenetre capteur', (.01, .012, .016), .2, .08)
FOND = material('Jeu | Fond de poupe', (.065, .065, .07), .3, .68)
TUYERE = material('Jeu | Tuyere', (.07, .065, .06), .9, .35)
CHAUDE = material('Jeu | Tuyere chaude', (.30, .62, 1.0), 0, .4, 2.5)
ECLAT = material('Jeu | Feu a eclats', (1.0, .96, .9), 0, .3, 6.0)
ANTICOL = material('Jeu | Feu anticollision', (1.0, .04, .02), 0, .3, .6)
POS_ROUGE = material('Jeu | Feu de position rouge', (.8, .025, .012), .05, .42, .012)
POS_VERT = material('Jeu | Feu vert', (.02, .6, .12), .05, .4, .012)
GARNITURE = material('Jeu | Garniture', (.13, .15, .16), .05, .78)
BROSSE = material('Jeu | Metal brosse', (.22, .28, .30), .8, .34)
CAOUTCHOUC = material('Jeu | Caoutchouc', (.018, .023, .027), 0, .82)
ECRAN_SOMBRE = material('Jeu | Ecran sombre', (.006, .025, .036), .15, .28)
def image_mat(nom):
    # Les écrans et cadrans : leur image en couleur et en émission ; le moteur les redessine par leur rôle.
    m = material('Jeu | ' + nom, (1, 1, 1), .05, .48, 1.0); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = image(nom + '.png', False)
    nt.links.new(n.outputs['Color'], p.inputs['Base Color']); nt.links.new(n.outputs['Color'], p.inputs['Emission Color']); return m
ECRANS = {k: image_mat(k) for k in ('ecran_nav', 'ecran_vol', 'ecran_systemes', 'jauge_prop', 'jauge_att', 'jauge_alt')}

# --- Pièces : un maillage bmesh, ses matériaux, ses deux UV. UVMap porte les tangentes ; elle suit UVDetail en sens.
class Piece:
    def __init__(self, nom, collection=hull):
        self.nom, self.collection = nom, collection; self.bm = bmesh.new(); self.mats = []
        self.uv0 = self.bm.loops.layers.uv.new('UVMap'); self.uv1 = self.bm.loops.layers.uv.new('UVDetail')
    def mat(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)
    def face(self, pts, m, uv1=None, uv0=None, n=None, dehors_de=None):
        pts = [Vector(p) for p in pts]
        if uv1 is None: uv1 = nuancier(pts, 'gris')
        if uv0 is None: uv0 = [(a / 2, b / 2) for a, b in projection(pts)]
        if n is not None or dehors_de is not None:
            ref = Vector(n) if n is not None else sum(pts, Vector()) / len(pts) - Vector(dehors_de)
            if newell(pts).dot(ref) < 0: pts, uv1, uv0 = pts[::-1], list(uv1)[::-1], list(uv0)[::-1]
        f = self.bm.faces.new([self.bm.verts.new(p) for p in pts]); f.material_index = self.mat(m)
        for loop, a, b in zip(f.loops, uv0, uv1): loop[self.uv0].uv = a; loop[self.uv1].uv = b
        return f
    def souder(self):
        # Soude les sommets, puis oriente les faces d'un même bloc dans un même sens, vers l'extérieur.
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6); bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
    def fin(self, lisse=30):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-6)
        me = bpy.data.meshes.new(self.nom); self.bm.to_mesh(me); self.bm.free()
        for m in self.mats: me.materials.append(m)
        me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(lisse))
        o = bpy.data.objects.new(self.nom, me); self.collection.objects.link(o); return o
def newell(pts):
    n = Vector()
    for a, b in zip(pts, pts[1:] + pts[:1]): n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return n
def uv_interieur(pts):
    # Les grandes faces du cockpit prennent la tôlerie de leur région de l'atlas, à 78 % : u le long de la coque, v en
    # hauteur ou en travers selon l'orientation de la face, ancrés au monde pour que les joints se suivent d'une face à
    # l'autre.
    n = newell([Vector(p) for p in pts]); n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
    if abs(n.z) > .7: ab = [(p[1] + 2.8, p[0] + 1.2) for p in pts]
    elif abs(n.x) >= abs(n.y): ab = [(p[1] + 2.8, p[2]) for p in pts]
    else: ab = [(p[0] + 1.2, p[2]) for p in pts]
    u0, v0 = T.INTERIEUR[:2]
    return [(u0 + T.ECH * a, v0 + T.ECH * .78 * b) for a, b in ab], [(a / 2, .78 * b / 2) for a, b in ab]
def projection(pts):
    # Coordonnées planes d'un polygone, sur le plan des axes le plus proche de sa normale.
    pts = [Vector(p) for p in pts]; n = Vector()
    for a, b in zip(pts, pts[1:] + pts[:1]): n += a.cross(b)
    ax = max(range(3), key=lambda i: abs(n[i])); i, j = [k for k in range(3) if k != ax]
    return [(p[i], p[j]) for p in pts]
def nuancier(pts, teinte):
    # Une teinte du nuancier de l'atlas : petite projection plane au centre de sa case (non dégénérée, pour les tangentes).
    u0, v0, u1, v1 = T.case(teinte); cu, cv = .5 * (u0 + u1), .5 * (v0 + v1)
    return [(cu + .004 * a % .02 - .01, cv + .004 * b % .02 - .01) for a, b in projection(pts)]
def loft_deroule(pc, anneaux, m, capot, bouts=(True, True), teinte_bouts='gris'):
    # Loft dont les faces latérales sont peintes dans l'atlas déroulé du capot : u le long de d, v le tour de la section
    # depuis son point le plus haut ; les bouts gardent une teinte du nuancier.
    anneaux = [[Vector(p) for p in a] for a in anneaux]; ctr = [sum(a, Vector()) / len(a) for a in anneaux]; n = len(anneaux[0])
    def abscisses(a):
        i0 = max(range(n), key=lambda i: a[i].z); acc = {i0: 0.0}; t = 0.0
        for k in range(1, n + 1):
            i, j = (i0 + k - 1) % n, (i0 + k) % n; t += (a[j] - a[i]).length; acc.setdefault(j, t) if k < n else None
        return [acc[i] for i in range(n)], t
    for (a, ca), (b, cb) in zip(zip(anneaux, ctr), zip(anneaux[1:], ctr[1:])):
        (sa, pa), (sb, pb) = abscisses(a), abscisses(b)
        for i in range(n):
            j = (i + 1) % n; q = [a[i], a[j], b[j], b[i]]
            sj_a = sa[j] if sa[j] > sa[i] else pa; sj_b = sb[j] if sb[j] > sb[i] else pb   # la couture
            uv = [T.uv_capot(capot, p.y - F.NEZ, s_) for p, s_ in zip(q, (sa[i], sj_a, sj_b, sb[i]))]
            pc.face(q, m, uv, dehors_de=(ca + cb) / 2)
    if bouts[0]: pc.face(anneaux[0], m, nuancier(anneaux[0], teinte_bouts), n=ctr[0] - ctr[1])
    if bouts[1]: pc.face(anneaux[-1], m, nuancier(anneaux[-1], teinte_bouts), n=ctr[-1] - ctr[-2])
def loft(pc, anneaux, m, teinte='gris', bouts=(True, True)):
    # Anneaux successifs de même nombre de points ; faces tournées vers l'extérieur (à recalculer ensuite).
    anneaux = [[Vector(p) for p in a] for a in anneaux]; faces = []; ctr = [sum(a, Vector()) / len(a) for a in anneaux]
    for (a, ca), (b, cb) in zip(zip(anneaux, ctr), zip(anneaux[1:], ctr[1:])):
        for i in range(len(a)):
            j = (i + 1) % len(a); q = [a[i], a[j], b[j], b[i]]; faces.append(pc.face(q, m, nuancier(q, teinte), dehors_de=(ca + cb) / 2))
    if bouts[0]: faces.append(pc.face(anneaux[0], m, nuancier(anneaux[0], teinte), n=ctr[0] - ctr[1]))
    if bouts[1]: faces.append(pc.face(anneaux[-1], m, nuancier(anneaux[-1], teinte), n=ctr[-1] - ctr[-2]))
    return faces

# --- La coque : la section de forme_chasseur.py, anneau par anneau ; l'atlas la peint en (d, s), s l'abscisse sur la
# demi-section depuis l'axe du dos, la même pour les deux moitiés, en miroir. Le dessus sous le verre est ouvert sur la cuve.
DS = F.ANNEAUX_D
pc = Piece('Coque | peau'); anneaux = []
for d in DS:
    H = F.demi_section(d); A = [0.0]
    for p, q in zip(H, H[1:]): A.append(A[-1] + math.dist(p, q))
    anneaux.append([(x, Y(d), z, a, d) for (x, z), a in zip(H, A)] + [(-x, Y(d), z, a, d) for (x, z), a in reversed(list(zip(H[1:-1], A[1:-1])))])
NA = len(anneaux[0]); KD = F.NDESSUS - 1
def segment(j): return j if j < NA // 2 else NA - 1 - j
uv_coque = lambda a, d: (T.COQUE[0] + T.ECH * d, T.COQUE[1] + T.ECH * a)
# Les sommets du dessus qui tombent sous le verre vont au point le plus proche du bord du verre, à sa hauteur : la peau
# s'arrête net sur le contour, sans trou ni dent ; les faces entièrement dessous s'ouvrent sur la cuve.
CONTOUR = np.array([(F.bulle_l(d), d) for d in np.linspace(F.V0, F.VW, 240)] + [(F.x_cadre(d), d) for d in np.linspace(F.VW, F.VF, 160)])
def sur_bord(p):
    i = int(np.argmin(np.hypot(CONTOUR[:, 0] - abs(p[0]), CONTOUR[:, 1] - p[4]))); x, d = CONTOUR[i]
    return (math.copysign(x, p[0]), Y(d), F.bulle(.999 * x, d))
pos = [[sur_bord(p) if segment(j) < KD and F.sous_verre(abs(p[0]), p[4]) else p[:3] for j, p in enumerate(r)] for r in anneaux]
for (r0, r1), (q0, q1) in zip(zip(anneaux, anneaux[1:]), zip(pos, pos[1:])):
    for j in range(NA):
        k = (j + 1) % NA; q = [r0[j], r0[k], r1[k], r1[j]]
        if segment(j) < KD and all(F.sous_verre(abs(p[0]), p[4]) for p in q): continue
        pc.face([q0[j], q0[k], q1[k], q1[j]], TOLE, [uv_coque(p[3], p[4]) for p in q], [(p[4] / 2, p[3] / 2) for p in q])
# La pointe : un chanfrein de 1 à 2 cm, de la dernière section à un octogone avancé de 2,5 cm ; dans l'octogone, un
# cadre de tôle claire de 1,8 cm et la fenêtre du capteur en retrait de 3 cm. Le chanfrein coud en triangles le bord de
# la section aux huit coins de l'octogone, dans l'ordre de l'angle autour du centre de la face.
bord0 = [Vector(p[:3]) for p in anneaux[0]]; zc = .5 * (min(p.z for p in bord0) + max(p.z for p in bord0))
W8, Z0, Z1, C8 = .145, .17, .36, .04
OCTO = [(W8 - C8, Z1), (W8, Z1 - C8), (W8, Z0 + C8), (W8 - C8, Z0), (C8 - W8, Z0), (-W8, Z0 + C8), (-W8, Z1 - C8), (C8 - W8, Z1)]
octo = [Vector((x, Y(0) - .025, z)) for x, z in OCTO]
tour_h = lambda p: ((90 - math.degrees(math.atan2(p.z - zc, p.x))) % 360) / 360   # fraction de tour, sens horaire depuis le haut
to, tc = [tour_h(p) for p in bord0], [tour_h(p) - 1 for p in octo[-1:]] + [tour_h(p) for p in octo]
oc = octo[-1:] + octo; i = j = 0
while i < len(bord0) or j < len(octo):
    t_o = to[i + 1] if i + 1 < len(bord0) else 1.0; t_c = tc[j + 1] if j + 1 < len(oc) else 2.0
    if i < len(bord0) and (t_o <= t_c or j >= len(octo)): q = [bord0[i], bord0[(i + 1) % len(bord0)], oc[j]]; i += 1
    else: q = [bord0[i % len(bord0)], oc[j + 1], oc[j]]; j += 1
    pc.face(q, TOLE, nuancier(q, 'gris'), n=(0, -1, 0))
pointe = pc.face(octo, FENETRE, nuancier(octo, 'noir'), n=(0, -1, 0))
pc.face([p[:3] for p in anneaux[-1]], FOND, nuancier([p[:3] for p in anneaux[-1]], 'ceramique'), n=(0, 1, 0))
pc.souder()
def teinter(faces, teinte):
    for f in faces:
        f.material_index = pc.mat(TOLE)
        for l in f.loops: l[pc.uv1].uv = nuancier([l.vert.co], teinte)[0]
teinter(bmesh.ops.inset_individual(pc.bm, faces=[pointe], thickness=.018, depth=0)['faces'], 'gris')
teinter(bmesh.ops.inset_individual(pc.bm, faces=[pointe], thickness=.004, depth=-.03)['faces'], 'noir')
coque = pc.fin(12)

# --- La cuve du cockpit : parois du seuil du verre au plancher, évasées de 18 %, plancher à 10 cm.
TOUR = [(F.bulle_l(d), d) for d in np.linspace(F.V0 + .02, F.VW, 60)] + [(F.x_cadre(d), d) for d in np.linspace(F.VW, F.VF - .01, 30)]
TOUR = TOUR + [(-x, d) for x, d in reversed(TOUR)]
PLANCHER = .10
pc = Piece('Cuve | parois', cockpit)
haut = [Vector((x, Y(d), F.bulle(x * .999, d))) for x, d in TOUR]
bas = [Vector((x * .82, Y(3.40 + (d - F.V0) / (F.VF - F.V0) * 1.70), PLANCHER)) for x, d in TOUR]
milieu = Vector((0, Y(4.3), .7))
for i in range(len(TOUR)):
    j = (i + 1) % len(TOUR); q = [haut[i], haut[j], bas[j], bas[i]]; pc.face(q, TOLE_INT, *uv_interieur(q), n=milieu - sum(q, Vector()) / 4)
pc.face(bas, CUVE, n=(0, 0, 1))
pc.fin(40)

# --- La verrière : colonnes c = x / demi-largeur, du nez de la bulle au cadre arrière ; son cadre et son collier.
NC, NR = 64, 52
def d_cadre(c):
    a, b = F.V0 + 1e-6, F.VF
    for _ in range(50):
        m = .5 * (a + b)
        if m < F.cadre(abs(c) * F.bulle_l(m)): a = m
        else: b = m
    return .5 * (a + b)
bg = bmesh.new(); uvg = bg.loops.layers.uv.new('UVMap'); cols = [-1 + 2 * j / NC for j in range(NC + 1)]; dFs = [d_cadre(c) for c in cols]
pole = bg.verts.new((0, Y(F.V0), F.pont(F.V0) + .004)); grille = []
for i in range(1, NR + 1):
    rang = []
    for c, dF in zip(cols, dFs):
        d = F.V0 + (dF - F.V0) * (i / NR) ** 1.8; x = c * F.bulle_l(d); rang.append(bg.verts.new((x, Y(d), F.bulle(x, d) + .004)))
    grille.append(rang)
for j in range(NC): bg.faces.new((pole, grille[0][j + 1], grille[0][j]))
for i in range(NR - 1):
    for j in range(NC): bg.faces.new((grille[i][j], grille[i][j + 1], grille[i + 1][j + 1], grille[i + 1][j]))
for f in bg.faces:
    for l in f.loops: l[uvg].uv = (l.vert.co.y / 2, l.vert.co.x / 2)
bg.normal_update()
if sum(f.normal.z for f in bg.faces) < 0: bmesh.ops.reverse_faces(bg, faces=list(bg.faces))
TOUR_VERRE = ([grille[i][0].co.copy() for i in range(NR - 1, -1, -1)] + [pole.co.copy()] + [grille[i][NC].co.copy() for i in range(NR)]
              + [grille[NR - 1][j].co.copy() for j in range(NC - 1, 0, -1)])
me = bpy.data.meshes.new('Canopy_Glass'); bg.to_mesh(me); bg.free(); me.materials.append(VERRE); me.shade_smooth()
verre = bpy.data.objects.new('Canopy_Glass', me); cockpit.objects.link(verre)

# The rigid retainer follows the glass tangent plane, with a separate thin seal.
M = len(TOUR_VERRE); aire = sum(TOUR_VERRE[k].x * TOUR_VERRE[(k + 1) % M].y - TOUR_VERRE[(k + 1) % M].x * TOUR_VERRE[k].y for k in range(M))
def dehors(k):
    t = TOUR_VERRE[(k + 1) % M] - TOUR_VERRE[k - 1]; return Vector((t.y, -t.x, 0)).normalized() * (1 if aire > 0 else -1)
import cadre_verriere
cadre_verriere.construire(globals())

# --- Les ailes : section à huit points (bord d'attaque, nervure, charnière, culot) ; là où sont les élevons, la partie
# fixe s'arrête à la charnière. Dessus et dessous peints dans l'atlas, en plan.
def aile_points(x, coupe=False, recul=0.0):
    (da, zab), (_, zah), (dn, zn), (db, zbh), (_, zbb), (_, znb) = F.aile_section(x)
    fh = (1 - F.CORDE_ELEVON - F.NERVURE) / (1 - F.NERVURE); dh = da + (1 - F.CORDE_ELEVON) * (db - da) + recul
    zh = zn + (zbh - zn) * fh; zhb = znb + (zbb - znb) * fh
    if coupe: return [(da, zab), (da, zah), (dn, zn), (dh, zh), (dh, zhb), (dn, znb)], ('ba', 'h', 'h', 'charniere', 'b', 'b')
    return [(da, zab), (da, zah), (dn, zn), (dh, zh), (db, zbh), (db, zbb), (dh, zhb), (dn, znb)], ('ba', 'h', 'h', 'h', 'culot', 'b', 'b', 'b')
def uv_aile(p, cote):
    x, d = abs(p[0]), p[1] - F.NEZ; u0, v0 = T.AILE_HAUT if cote == 'h' else T.AILE_BAS
    return (u0 + T.ECH * (d - T.AILE_D0), v0 + T.ECH * (x - T.AILE_X0))
EPS = 1e-4
STATIONS = [(1.15, False)]
for e0, e1 in F.ELEVONS:
    STATIONS += [(e0, False), (e0 + EPS, True)] + [(x, True) for x in (2.05,) if e0 < x < e1] + [(e1 - EPS, True), (e1, False)]
STATIONS += [(x, False) for x in (2.35,)] + [(3.30, False)]
STATIONS = sorted(STATIONS)
def section_aile(x, coupe):
    pts, lab = aile_points(x)
    if coupe:   # le culot avance à la charnière : une face de charnière de 2 mm remplace le bord de fuite
        (dh, zh), (dhb, zhb) = pts[3], pts[6]; pts = pts[:4] + [(dh + .002, zh), (dhb + .002, zhb)] + pts[6:]
    return pts, lab
pc = Piece('Ailes | fixes')
for side in (1, -1):
    secs = [[Vector((side * x, Y(d), z)) for d, z in section_aile(x, c)[0]] for x, c in STATIONS]; lab = aile_points(1.5)[1]
    axe_c = [sum(s_, Vector()) / len(s_) for s_ in secs]
    for (s0, c0), (s1, c1) in zip(zip(secs, axe_c), zip(secs[1:], axe_c[1:])):
        for i in range(8):
            j = (i + 1) % 8; q = [s0[i], s0[j], s1[j], s1[i]]
            uv = [uv_aile(p, lab[i]) for p in q] if lab[i] in ('h', 'b') else nuancier(q, 'ventre' if lab[i] == 'culot' else 'gris')
            pc.face(q, TOLE, uv, dehors_de=(c0 + c1) / 2)
    pc.face(secs[0], TOLE, nuancier(secs[0], 'gris'), n=(-side, 0, 0)); pc.face(secs[-1], TOLE, nuancier(secs[-1], 'metal'), n=(side, 0, 0))
pc.souder(); pc.fin(5)

def poser(o, valeur):
    a = o.data.attributes.new('_POSE', 'FLOAT', 'POINT'); a.data.foreach_set('value', np.full(len(o.data.vertices), valeur, np.float32))
def pivot(nom, point, axe, collection):
    e = bpy.data.objects.new(nom, None); collection.objects.link(e)
    e.location = point; e.rotation_mode = 'QUATERNION'; e.rotation_quaternion = Vector(axe).to_track_quat('Z', 'Y'); e.empty_display_size = .1
# Les élevons : 1 cm de jeu à la charnière et 1,5 cm aux bouts ; pose 3 à 6 dans l'ordre des pivots de paquet_moteur.py.
POSES = {(0, 1): 3, (0, -1): 4, (1, 1): 5, (1, -1): 6}
NOMS = {(0, 1): 'interieur gauche', (0, -1): 'interieur droit', (1, 1): 'exterieur gauche', (1, -1): 'exterieur droit'}
for k, (e0, e1) in enumerate(F.ELEVONS):
    for side in (1, -1):
        pc = Piece('Elevon | ' + NOMS[(k, side)]); x0, x1 = e0 + .015, e1 - .015
        def sec(x):
            pts, _ = aile_points(x); return [pts[3], pts[4], pts[5], pts[6]]   # charnière dessus, culot, charnière dessous
        S0 = [Vector((side * x0, Y(d + (.01 if i in (0, 3) else 0)), z)) for i, (d, z) in enumerate(sec(x0))]
        S1 = [Vector((side * x1, Y(d + (.01 if i in (0, 3) else 0)), z)) for i, (d, z) in enumerate(sec(x1))]
        labs = ('h', 'culot', 'b', 'charniere')
        cm = (sum(S0, Vector()) + sum(S1, Vector())) / 8
        for i in range(4):
            j = (i + 1) % 4; q = [S0[i], S0[j], S1[j], S1[i]]
            pc.face(q, TOLE, [uv_aile(p, labs[i]) for p in q] if labs[i] in ('h', 'b') else nuancier(q, 'metal'), dehors_de=cm)
        c0, c1 = sum(S0, Vector()) / 4, sum(S1, Vector()) / 4
        pc.face(S0, TOLE, nuancier(S0, 'metal'), n=c0 - c1); pc.face(S1, TOLE, nuancier(S1, 'metal'), n=c1 - c0)
        pc.souder(); o = pc.fin(5); poser(o, POSES[(k, side)])
        axe = (S1[0] - S0[0]).normalized(); pivot('Pivot | elevon ' + NOMS[(k, side)], (S0[0] + S1[0]) / 2, axe, hull)

# --- Prises d'air : bouche biaisée à cadre gris biseauté, creux sombre et quatre lames ; joue bleue fondue dans la coque.
def ovale(cx, cz, hw, hh, p, n=16):
    pts = []
    for k in range(n):
        t = 2 * math.pi * (k + .5) / n; c, sn = math.cos(t), math.sin(t)
        pts.append((cx + hw * math.copysign(abs(c) ** (2 / p), c), cz + hh * math.copysign(abs(sn) ** (2 / p), sn)))
    return pts
def douze(cx, cz, r): return [(cx + r * math.cos(2 * math.pi * (k + .5) / 12), cz + r * math.sin(2 * math.pi * (k + .5) / 12)) for k in range(12)]
pc = Piece('Prises | joues'); bouches = []
for side in (1, -1):
    anneaux = []
    for i, (d, q) in enumerate(F.PRISE):
        cx, cz, hw, hh = q[:4]; bx, bz = F.BIAIS_PRISE if i == 0 else (0, 0)
        anneaux.append([Vector((side * x, Y(d + bx * (x - cx) / hw + bz * (z - cz) / hh), z)) for x, z in ovale(*q)])
    anneaux = anneaux[::-1]
    ctr = [sum(a, Vector()) / 16 for a in anneaux]
    loft_deroule(pc, anneaux, TOLE, 'prise', bouts=(True, False), teinte_bouts='bleu')
    bouches.append(pc.face(anneaux[-1], TOLE, nuancier(anneaux[-1], 'gris'), n=ctr[-1] - ctr[-2]))
pc.souder()
bmesh.ops.inset_individual(pc.bm, faces=bouches, thickness=.06, depth=0)
creux = bmesh.ops.inset_individual(pc.bm, faces=bouches, thickness=.006, depth=-.16)['faces']
for f in creux + bouches:
    for l in f.loops: l[pc.uv1].uv = nuancier([l.vert.co], 'noir')[0]
pc.fin(20)
pc = Piece('Prises | lames')
for side in (1, -1):
    d0, (cx, cz, hw, hh, _) = F.PRISE[0]
    for k in range(4):
        z = cz - hh * .62 + k * hh * .41; c = Vector((side * cx, Y(d0 + .12), z)); U = Vector((side, 0, 0)); V = Vector((0, .25, -1)).normalized()
        q0 = [c + U * hw * .78 * s1 + V * .012 * s2 for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        loft(pc, [q0, [p + Vector((0, .05, 0)) for p in q0]], TOLE, 'metal')
pc.souder(); pc.fin(30)

# --- Capots moteurs, capots des petites tuyères, tuyères en profil de tour : lèvre, divergent, foyer chaud au fond.
pc = Piece('Capots | moteurs')
for side in (1, -1):
    loft_deroule(pc, [[Vector((side * x, Y(d), z)) for x, z in douze(*F.MOTEUR_C, r)] for d, r in F.MOTEUR], TOLE, 'moteur', teinte_bouts='tuyere')
    loft_deroule(pc, [[Vector((side * x, Y(d), z)) for x, z in douze(*F.PETIT_C, r)] for d, r in F.PETIT], TOLE, 'petit', teinte_bouts='tuyere')
pc.souder(); pc.fin(20)
def tour(pc, cx, cz, profil, nseg=28):
    prev = None
    for k, (d, r) in enumerate(profil):
        ring = [Vector((cx, Y(d), cz))] if r < 1e-6 else [Vector((cx + r * math.cos(2 * math.pi * s / nseg), Y(d), cz + r * math.sin(2 * math.pi * s / nseg))) for s in range(nseg)]
        if prev is not None:
            m = CHAUDE if k == len(profil) - 1 else TUYERE
            for s in range(nseg):
                if len(prev) == 1: q = [prev[0], ring[s], ring[(s + 1) % nseg]]
                elif len(ring) == 1: q = [prev[s], prev[(s + 1) % nseg], ring[0]]
                else: q = [prev[s], prev[(s + 1) % nseg], ring[(s + 1) % nseg], ring[s]]
                pc.face(q, m, nuancier(q, 'tuyere'))
        prev = ring
    pc.souder()
pc = Piece('Tuyeres | ensemble')
for side in (1, -1):
    tour(pc, side * F.MOTEUR_C[0], F.MOTEUR_C[1], F.GRANDE); tour(pc, side * F.PETIT_C[0], F.PETIT_C[1], F.PETITE)
pc.fin(40)

# --- La grille de poupe entre les capots ; les écopes des épaules ; les antennes ; les feux ; les jets d'attitude.
pc = Piece('Details | peau')
c = Vector((0, Y(10.0), .48)); U, V, N = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
cadre_g = [c + U * .23 * a + V * .2 * b for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
loft(pc, [cadre_g, [p + N * .03 for p in cadre_g]], TOLE, 'metal', (False, False))
pc.face([p + N * .005 for p in cadre_g], TOLE, nuancier(cadre_g, 'noir'), n=N)
for k in range(5):
    q0 = [c + U * .21 * a + V * (-.16 + k * .08 + .012 * b) + N * .02 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    loft(pc, [q0, [p + V * .0 + N * .012 for p in q0]], TOLE, 'metal')
for side in (1, -1):
    secs = []
    for d, h in ((6.9, .05), (7.25, .03), (7.6, .004)):   # sur la terrasse, entre la diagonale et l'arête d'épaule
        x0, x1 = .92, 1.16; t = min(.04, h)
        secs.append([Vector((side * x, Y(d), F.surface_z(x, d) + dz)) for x, dz in ((x0, -.03), (x1, -.03), (x1 - t, h), (x0 + t, h))])
    loft(pc, secs, TOLE, 'bleu', (False, True)); pc.face(secs[0], TOLE, nuancier(secs[0], 'noir'), n=(0, -1, 0))
def lame(pc, d0, z0, haut, corde, epais, vers=1):
    # Antenne en lame effilée : profil en losange, flèche de 40°, bout arrondi par un pan.
    pts = []
    for k, f in enumerate((0, 1)):
        dz = vers * haut * f; dd = .7 * haut * f; c = corde * (1 - .55 * f); e = epais * (1 - .5 * f)
        pts.append([Vector((0, Y(d0 + dd), z0 + dz)), Vector((e, Y(d0 + dd + .4 * c), z0 + dz)), Vector((0, Y(d0 + dd + c), z0 + dz)),
                    Vector((-e, Y(d0 + dd + .4 * c), z0 + dz))])
    loft(pc, pts, TOLE, 'metal', (False, True))
lame(pc, 7.0, F.epine_h(7.0) - .01, .16, .32, .012)
lame(pc, 6.2, F.ventre_z(6.2) + .01, .14, .28, .012, -1)
def lentille(pc, c, n, r, m, saillie=.012):
    # Feu en dôme bas : anneau de 12 points, sommet décalé de la saillie le long de la normale.
    n = Vector(n).normalized(); U = n.orthogonal().normalized(); V = n.cross(U)
    ring = [c + (U * math.cos(2 * math.pi * k / 12) + V * math.sin(2 * math.pi * k / 12)) * r for k in range(12)]
    mid = [c + n * saillie * .7 + (p - c) * .6 for p in ring]; top = c + n * saillie
    for k in range(12):
        j = (k + 1) % 12; bas_ = c - n * .05
        pc.face([ring[k], ring[j], mid[j], mid[k]], m, nuancier([ring[k], ring[j], mid[j]], 'metal'), dehors_de=bas_)
        pc.face([mid[k], mid[j], top], m, nuancier([mid[k], mid[j], top], 'metal'), dehors_de=bas_)
for side, m in ((1, POS_ROUGE), (-1, POS_VERT)):
    a, b = F.aile_corde(3.30); zt = F.aile_zm(3.30)
    lentille(pc, Vector((side * 3.302, Y(a + .12), zt)), (side, 0, 0), .028, m)
    lentille(pc, Vector((side * 3.302, Y(b - .06), zt)), (side, 0, 0), .02, ECLAT)
lentille(pc, Vector((0, Y(6.35), F.epine_h(6.35))), (0, 0, 1), .045, ANTICOL, .03)
lentille(pc, Vector((0, Y(5.6), F.ventre_z(5.6))), (0, 0, -1), .045, ANTICOL, .03)
# Jets d'attitude affleurants : bague et trou sombre ; leurs positions vont dans ShipPlume.hlsli.
JETS = []
def jet(c, n):
    n = Vector(n).normalized(); JETS.append((tuple(round(v, 3) for v in c), tuple(n)))
    U = n.orthogonal().normalized(); V = n.cross(U)
    ring = [c + n * .002 + (U * math.cos(2 * math.pi * k / 10) + V * math.sin(2 * math.pi * k / 10)) * .03 for k in range(10)]
    inner = [c + n * .002 + (p - c - n * .002) * .6 for p in ring]
    for k in range(10):
        j = (k + 1) % 10; q = [ring[k], ring[j], inner[j], inner[k]]; pc.face(q, TOLE, nuancier(q, 'metal'), n=n)
    pc.face(inner, TUYERE, nuancier(inner, 'noir'), n=n)
d = 1.2; jet(Vector((0, Y(d), F.pont(d) + .002)), (0, 0, 1)); jet(Vector((0, Y(d), F.ventre_z(d) - .002)), (0, 0, -1))
for side in (1, -1):
    jet(Vector((side * (F.bas_x(d) + .01), Y(d), .5 * (F.chine_z(d) + F.basse_z(d)))), (side, 0, 0))
    a, b = F.aile_corde(3.05); zt = F.aile_zm(3.05); ep = F.aile_epaisseurs(3.05)
    jet(Vector((side * 3.05, Y(a + .45 * (b - a)), zt + ep[0] * .8)), (0, 0, 1)); jet(Vector((side * 3.05, Y(a + .45 * (b - a)), zt - ep[1] * .8)), (0, 0, -1))
    r = F.MOTEUR[1][1] + (F.MOTEUR[2][1] - F.MOTEUR[1][1]) * .6   # sur le pan latéral du capot moteur, à d 9,6
    jet(Vector((side * (F.MOTEUR_C[0] + r * math.cos(math.pi / 12) + .002), Y(9.6), F.MOTEUR_C[1])), (side, 0, 0))
pc.fin(30)

# --- L'équipement de peau : de petites pièces qui ont une fonction, profilées, posées sur les pans plats ou noyées dans
# la peau (docs/principes.md). Trappes de train et d'accès vissées, ailettes ventrales, lames de chine du nez, carénages
# d'articulation des élevons, ouïes des capots, sondes d'incidence, déperditeurs, feux de formation.
def pave_d(pc, c, U, V, N, su, sv, sn, teinte, ch=0.0, m=None):
    c = Vector(c); U, V, N = Vector(U).normalized(), Vector(V).normalized(), Vector(N).normalized()
    r = lambda o, a, b: [o + U * a * s1 / 2 + V * b * s2 / 2 for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    an = [r(c, su, sv)] + ([r(c + N * (sn - ch), su, sv), r(c + N * sn, su - 2 * ch, sv - 2 * ch)] if ch else [r(c + N * sn, su, sv)])
    loft(pc, an, m or TOLE, teinte)
def cone(pc, a, b, r0, r1, teinte='metal', n=8, m=None):
    a, b = Vector(a), Vector(b); N = (b - a).normalized(); U = N.orthogonal().normalized(); V = N.cross(U)
    loft(pc, [[o + (U * math.cos(2 * math.pi * k / n) + V * math.sin(2 * math.pi * k / n)) * r for k in range(n)] for o, r in ((a, r0), (b, r1))],
         m or TOLE, teinte, (False, True))
def trappe(pc, c, U, V, N, su, sv, teinte='gris'):
    # Joint sombre de 6 mm autour d'une porte en relief de 3 mm, coins chanfreinés, une vis à chaque coin.
    N = Vector(N).normalized(); U, V = Vector(U).normalized(), Vector(V).normalized()
    pave_d(pc, c - N * .002, U, V, N, su + .012, sv + .012, .0028, 'noir')
    pave_d(pc, c - N * .001, U, V, N, su, sv, .004, teinte, .002)
    for a in (-1, 1):
        for b in (-1, 1): cone(pc, c + N * .0025 + U * a * (su / 2 - .02) + V * b * (sv / 2 - .02), c + N * .0045 + U * a * (su / 2 - .02) + V * b * (sv / 2 - .02), .007, .005, n=6)
def flanc(d, f, side):
    # Point du flanc à la fraction f de la chine à la chine basse ; U le long de d, V vers le bas, N dehors.
    def p(dd):
        c, b = Vector((F.chine_x(dd), Y(dd), F.chine_z(dd))), Vector((F.bas_x(dd), Y(dd), F.basse_z(dd))); return c.lerp(b, f), (b - c).normalized()
    P, V = p(d); U = (p(d + .02)[0] - p(d - .02)[0]).normalized(); N = U.cross(V).normalized()
    if N.x < 0: N = -N
    m = Vector((side, 1, 1)); return P * m, U * m, V * m, N * m
def ventre(x, d):
    s = (F.ventre_z(d + .02) - F.ventre_z(d - .02)) / .04; U = Vector((0, 1, s)).normalized()
    return Vector((x, Y(d), F.ventre_z(d))), U, Vector((1, 0, 0)), Vector((0, s, -1)).normalized()
pc = Piece('Details | equipement')
# Les trappes de train sous le ventre : deux portes au nez, deux de chaque côté derrière les prises.
for x in (-.068, .068): trappe(pc, *ventre(x, 1.95), 1.0, .125, 'ventre')
for side in (1, -1):
    for x, w in ((.40, .17), (.60, .17)): trappe(pc, *ventre(side * x, 6.5), 1.10, w, 'ventre')
# Les trappes d'accès des flancs et du pont du nez.
for side in (1, -1):
    for d, f, su, sv in ((3.15, .45, .30, .16), (4.62, .52, .34, .18), (8.05, .45, .30, .14)): trappe(pc, *flanc(d, f, side), su, sv)
s_ = (F.pont(1.57) - F.pont(1.53)) / .04
trappe(pc, Vector((0, Y(1.55), F.pont(1.55))), Vector((0, 1, s_)), Vector((1, 0, 0)), Vector((0, -s_, 1)), .36, .26)
# Les ailettes ventrales : deux petites dérives en flèche sous la poupe, déversées de 20° vers l'extérieur.
for side in (1, -1):
    S = Vector((side * math.sin(math.radians(20)), 0, -math.cos(math.radians(20)))); Te = Vector((0, 1, 0)).cross(S).normalized()
    x0, d0, c0, c1, h, fl = .52, 7.55, 1.15, .48, .24, .55
    racine = [Vector((side * x0, Y(d), F.ventre_z(d) + .015)) for d in (d0, d0 + .4 * c0, d0 + c0, d0 + .4 * c0)]
    racine[1] += Te * .011; racine[3] -= Te * .011
    bout_ = racine[0] + S * h + Vector((0, fl, 0))
    bout = [bout_, bout_ + Vector((0, .4 * c1, 0)) + Te * .006, bout_ + Vector((0, c1, 0)), bout_ + Vector((0, .4 * c1, 0)) - Te * .006]
    loft(pc, [racine, bout], TOLE, 'ventre', (False, True))
# Les lames de chine du nez : le long de la chine basse, effilées aux deux bouts.
for side in (1, -1):
    secs = []
    for d, w in ((.85, .004), (1.15, .03), (1.6, .045), (2.0, .032), (2.3, .004)):
        bx, bz = F.bas_x(d) - .004, F.basse_z(d)
        secs.append([Vector((side * bx, Y(d), bz + .006)), Vector((side * (bx + w), Y(d), bz - .004)), Vector((side * bx, Y(d), bz - .008))])
    loft(pc, secs, TOLE, 'gris')
# Les carénages d'articulation : un fuseau sous chaque élevon, à sa charnière.
for e0, e1 in F.ELEVONS:
    xm = .5 * (e0 + e1); dh, zb = aile_points(xm)[0][6]
    for side in (1, -1):
        anneaux = [[Vector((side * xm + r * math.cos(2 * math.pi * k / 8), Y(dh + dd), zb - .006 + r * .8 * math.sin(2 * math.pi * k / 8))) for k in range(8)]
                   for dd, r in ((-.17, .004), (-.11, .017), (-.04, .023), (.02, .02), (.06, .006))]
        loft(pc, anneaux, TOLE, 'gris')
# Les ouïes des capots moteurs : un cadre et quatre lames sur le pan haut et extérieur de chaque capot.
for side in (1, -1):
    d = 9.45; r = F.MOTEUR[1][1] + (F.MOTEUR[2][1] - F.MOTEUR[1][1]) * (d - 9.0)
    N = Vector((side * math.cos(math.pi / 3), 0, math.sin(math.pi / 3))); c = Vector((side * F.MOTEUR_C[0], Y(d), F.MOTEUR_C[1])) + N * (r * math.cos(math.pi / 12))
    U, V = Vector((0, 1, 0)), Vector((0, 1, 0)).cross(N).normalized()
    pave_d(pc, c - N * .002, U, V, N, .24, .11, .006, 'metal', .002)
    for k in range(4): pave_d(pc, c + N * .003 + U * (-.075 + .05 * k), U, V, N, .012, .09, .006, 'noir', .002)
# Les sondes d'incidence, de part et d'autre de la pointe ; les déperditeurs au bout des ailes ; les feux de formation.
for side in (1, -1):
    P, U, V, N = flanc(.45, .35, side); cone(pc, P - N * .005, P + (N * .35 - U).normalized() * .11, .007, .0018)
    a, b = F.aile_corde(3.20)
    for x in (3.16, 3.26): cone(pc, Vector((side * x, Y(min(7.23 + 3.30 - x, 9.40) - .01), F.aile_zm(x))), Vector((side * x, Y(min(7.23 + 3.30 - x, 9.40) + .07), F.aile_zm(x))), .003, .0015, n=6)
    for d in (.95, 8.65):
        P, U, V, N = flanc(d, .08, side); pave_d(pc, P - N * .001, U, V, N, .22, .012, .003, 'metal', m=POS_VERT)
# Les cloisons d'aile : une lame entre les deux élevons, du bord d'attaque au culot, qui suit le dessus de l'aile.
for side in (1, -1):
    x = .5 * (F.ELEVONS[0][1] + F.ELEVONS[1][0]); (da, _), (_, zah), (dn, zn), (dh, zh), (db, zbh) = aile_points(x)[0][:5]
    secs = []
    for d, z, h in ((da + .03, zah, .008), (dn, zn, .045), (dh, zh, .04), (db - .01, zbh, .012)):
        secs.append([Vector((side * (x - .004), Y(d), z - .004)), Vector((side * x, Y(d), z + h)), Vector((side * (x + .004), Y(d), z - .004))])
    loft(pc, secs, TOLE, 'gris')
def panneau(pc, x0, x1, d0, d1, teinte, saillie=.004):
    # Panneau qui épouse le dessus de la coque (surface_z), en relief, sur un fond sombre qui le déborde de 6 mm.
    P = lambda x, d, dz: Vector((x, Y(d), F.surface_z(abs(x), d) + dz))
    def plaque(xa, xb, da_, db_, dz, teinte_, cotes):
        xs, ds = [xa + (xb - xa) * i / 3 for i in range(4)], [da_ + (db_ - da_) * j / 3 for j in range(4)]
        for i in range(3):
            for j in range(3):
                q = [P(xs[i], ds[j], dz), P(xs[i + 1], ds[j], dz), P(xs[i + 1], ds[j + 1], dz), P(xs[i], ds[j + 1], dz)]; pc.face(q, TOLE, nuancier(q, teinte_), n=(0, 0, 1))
        if not cotes: return
        tour_ = [(x, da_) for x in xs] + [(xb, d) for d in ds[1:]] + [(x, db_) for x in xs[::-1][1:]] + [(xa, d) for d in ds[::-1][1:-1]]
        c = Vector((.5 * (xa + xb), Y(.5 * (da_ + db_)), 0))
        for (xa_, da2), (xb_, db2) in zip(tour_, tour_[1:] + tour_[:1]):
            q = [P(xa_, da2, dz), P(xb_, db2, dz), P(xb_, db2, -.003), P(xa_, da2, -.003)]; pc.face(q, TOLE, nuancier(q, teinte_), dehors_de=Vector((c.x, c.y, q[0].z)))
    e = math.copysign(.006, x1 - x0)
    plaque(x0 - e, x1 + e, d0 - .006, d1 + .006, .0012, 'noir', False)
    plaque(x0, x1, d0, d1, saillie, teinte, True)
# Les aérofreins : deux volets sur le dos, derrière la bulle, avec leur charnière à l'avant.
for side in (1, -1):
    panneau(pc, side * .14, side * .40, 7.55, 8.15, 'gris')
    a, b = Vector((side * .16, Y(7.56), F.surface_z(.16, 7.56) + .004)), Vector((side * .38, Y(7.56), F.surface_z(.38, 7.56) + .004))
    cone(pc, a, b, .006, .006, n=6)
# Deux bouches auxiliaires sur le dos, devant l'antenne : écopes basses, gueule sombre.
for side in (1, -1):
    secs = []
    for d, h in ((5.85, .035), (6.1, .02), (6.35, .003)):
        x0, x1 = .26, .44; t = min(.025, h)
        secs.append([Vector((side * x, Y(d), F.surface_z(x, d) + dz)) for x, dz in ((x0, -.02), (x1, -.02), (x1 - t, h), (x0 + t, h))])
    loft(pc, secs, TOLE, 'gris', (False, True)); pc.face(secs[0], TOLE, nuancier(secs[0], 'noir'), n=(0, -1, 0))
pc.fin(30)

# --- Le cockpit (cockpit_chasseur.py), puis ses pièces mobiles repérées (pieces_mobiles.py).
import cockpit_chasseur, pieces_mobiles
cockpit_chasseur.construire(globals())
pieces_mobiles.marquer(cockpit)
import textures_finitions
textures_finitions.appliquer(globals())

print('JETS', JETS)
TRI = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ship.all_objects if o.type == 'MESH'}
print('TRIANGLES', sum(TRI.values()), sorted(TRI.items(), key=lambda kv: -kv[1]))

# --- Vues de contrôle : trois-quarts du concept, poursuite du jeu, gros plans, pilote ; studio gris et soleil.
def rendre(dossier):
    os.makedirs(dossier, exist_ok=True)
    sol = bpy.data.objects.new('Sol', bpy.data.meshes.new('Sol')); sc.collection.objects.link(sol)
    bs = bmesh.new(); bmesh.ops.create_grid(bs, x_segments=1, y_segments=1, size=40, matrix=Matrix.Translation((0, 0, -2.2))); bs.to_mesh(sol.data); bs.free()
    sol.is_shadow_catcher = True
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('RENDU_SPP', '48')); sc.cycles.use_denoising = True
    sc.render.film_transparent = True; sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -.8   # le gris moyen du concept
    w = bpy.data.worlds.new('Studio'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (.62, .62, .63, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = .9
    sun = bpy.data.objects.new('Soleil', bpy.data.lights.new('Soleil', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 4.0; sun.data.angle = .3; sun.rotation_euler = Vector((-.35, .45, -.82)).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_start = .02
    choix = os.environ.get('RENDU_VUES')
    # Une lumière d'appoint sous la bulle, pour les seules vues du cockpit (rendus de contrôle, pas le modèle).
    lum = bpy.data.objects.new('Lumiere cockpit', bpy.data.lights.new('Lumiere cockpit', 'AREA')); sc.collection.objects.link(lum)
    lum.data.energy = 30; lum.data.size = .7; lum.location = (0, Y(4.1), 1.22)
    def vue(nom, rx, ry):
        if choix and nom not in choix.split(','): return
        lum.hide_render = nom not in ('pilote', 'cockpit', 'siege', 'commandes')
        sc.render.resolution_x, sc.render.resolution_y = rx, ry; sc.render.filepath = os.path.join(dossier, nom + '.png')
        bpy.ops.render.render(write_still=True); print('VUE', nom)
    def viser(pos, cible, lens):
        cam.data.type = 'PERSP'; cam.data.lens = lens; cam.location = pos; cam.rotation_euler = (Vector(cible) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    # Le trois-quarts calé sur le concept (maquette_chasseur.py) : azimut, élévation, distance, focale, visée, roulis.
    phi, eps, dist, f, tx, ty, tz, roll = [.608, .195, 16.302, 79.34, 1.286, -2.147, .154, -.145]
    Tv = Vector((tx, ty, tz)); C = Tv + dist * Vector((math.sin(phi) * math.cos(eps), -math.cos(phi) * math.cos(eps), math.sin(eps)))
    Fw = (Tv - C).normalized(); R = Fw.cross(Vector((0, 0, 1))).normalized(); Uc = R.cross(Fw)
    R, Uc = math.cos(roll) * R + math.sin(roll) * Uc, -math.sin(roll) * R + math.cos(roll) * Uc
    cam.data.type = 'PERSP'; cam.data.lens = f; cam.location = C; cam.rotation_euler = Matrix((R, Uc, -Fw)).transposed().to_euler()
    vue('troisquarts', 1536, 1024)
    viser((0, 15, 6.5), (0, -2, 0), 18 / math.tan(math.radians(30)) / 2 * 1.0); cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = 2 * math.atan(math.tan(math.radians(30)) / 2)
    vue('poursuite', 1280, 720); cam.data.sensor_fit = 'AUTO'
    viser((3.2, -7.6, 1.6), (0, -3.6, .55), 45); vue('nez', 1280, 800)
    viser((4.2, 6.2, 2.6), (.6, 2.6, .55), 40); vue('poupe', 1280, 800)
    viser((3.0, 1.2, 2.4), (1.2, .2, .6), 35); vue('prise', 1280, 800)
    viser((3.6, Y(4.2), -1.9), (.3, Y(5.6), .05), 30); vue('dessous', 1280, 800)
    viser((2.3, Y(3.9), 1.6), (1.0, Y(4.85), .95), 45); vue('jonction', 1280, 800)
    viser(F.OEIL, (0, Y(2.6), .72), 18); vue('pilote', 1280, 800)
    viser((1.5, Y(3.0), 2.3), (0, Y(4.15), .5), 28); vue('cockpit', 1280, 800)
    viser((.62, Y(3.62), 1.0), (0, Y(4.55), .62), 22); vue('siege', 1280, 800)
    viser((-.45, Y(4.75), 1.05), (.15, Y(3.9), .5), 22); vue('commandes', 1280, 800)
    sol.hide_render = True; vue_ortho = lambda nom, loc, rot, s, rx, ry: (setattr(cam.data, 'type', 'ORTHO'), setattr(cam.data, 'ortho_scale', s),
                                                                           setattr(cam, 'location', loc), setattr(cam, 'rotation_euler', rot), vue(nom, rx, ry))
    vue_ortho('dessus', (0, Y(5.07), 20), (0, 0, math.pi / 2), 11.07, 1290, 855)
    vue_ortho('profil', (20, Y(5.07), .69), (math.pi / 2, 0, math.pi / 2), 10.6, 1260, 240)

if not SANS_EXPORT:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'vaisseau_travail.blend'))
if RENDUS: rendre(RENDUS)
if not SANS_EXPORT:
    import exporter
    exporter.exporter(ROOT)
