"""La forme du chasseur, validée sur maquettes le 2026-10-31 : une seule source, sans Blender.

Lue par design_chasseur.py (le modèle), controle_geometrie.py (les raccords) et recopiée par le moteur (Ship.hlsli :
la bulle, pour l'eau et le givre ; ShipPlume.hlsli : les tuyères). La cible artistique est la vue de trois quarts du
concept de l'utilisateur ; ses vues de dessus, de profil et d'arrière n'ont servi qu'où elles s'accordent avec elle.
Repère du vaisseau : nez vers -Y, haut +Z, gauche du pilote +X, en mètres ; d est la distance à la pointe du nez.
"""
import math

NEZ = -5.32   # y de la pointe ; la poupe est à d = 10, les lèvres des grandes tuyères à 10,10
def Y(d): return NEZ + d

def courbe(*pts):
    # Interpolation monotone (Fritsch-Carlson) : pas de bosse entre les clés.
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; n = len(pts)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]; s = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [s[0]] + [0.0 if s[i - 1] * s[i] <= 0 else 3 * (h[i - 1] + h[i]) / ((2 * h[i] + h[i - 1]) / s[i - 1] + (h[i] + 2 * h[i - 1]) / s[i])
                  for i in range(1, n - 1)] + [s[-1]]
    def f(x):
        if x <= xs[0]: return ys[0]
        if x >= xs[-1]: return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x); t = (x - xs[i]) / h[i]
        return ((2 * t ** 3 - 3 * t * t + 1) * ys[i] + (t ** 3 - 2 * t * t + t) * h[i] * m[i]
                + (-2 * t ** 3 + 3 * t * t) * ys[i + 1] + (t ** 3 - t * t) * h[i] * m[i + 1])
    return f
def lisse(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)

# --- La coque. Une seule grande arête court de la pointe à la poupe : la chine, au bas de la bande orange, qui passe
# sous la verrière, file au haut de la prise d'air puis remonte en arête d'épaule jusqu'au capot moteur. Au-dessus, le
# pont : il s'élargit de la pointe au tiers avant de la bulle, longe le cadre à 5 cm et finit au coin bas de la bulle.
# Entre les deux, le chanfrein orange. Sous la chine, le flanc, qui devient à l'arrière le pan raide jusqu'à
# l'emplanture ; puis la chine basse, qui file au bord d'attaque de l'aile, le chanfrein bas et le ventre plat. En plan,
# sil est la silhouette.
sil = courbe((0, .19), (1, .43), (2.5, .82), (3.5, 1.10), (4.4, 1.31), (5.0, 1.43), (5.65, 1.50), (7.0, 1.55), (8.5, 1.53), (9.4, 1.32), (10, 1.08))
epaule_x = courbe((4.4, 1.29), (5.2, 1.36), (6.5, 1.37), (7.5, 1.30), (8.5, 1.17), (9.4, 1.06), (10, .98))
def chine_brute(d):
    # La chine des maquettes : au bord de la silhouette, puis l'arête d'épaule. Le pont et la chine s'y règlent.
    t = lisse((d - 4.4) / .8); return (1 - t) * (sil(d) - .02) + t * epaule_x(d)
chine_z_brute = courbe((0, .33), (.3, .37), (1, .41), (2.0, .46), (2.6, .49), (3.0, .51), (3.5, .56), (4.4, .66), (5.0, .80), (5.5, .90),
                 (6.5, .91), (7.5, .92), (8.5, .93), (9.4, .93), (10, .91))
# La chine remontée au bas de la bande orange (image 5) : sa part du chanfrein des maquettes, depuis le bord du pont.
part_chanfrein = courbe((0, .68), (1, .66), (2, .55), (3, .46), (4, .37), (4.75, .38))
def chine_x(d):
    # Derrière le coin bas de la bulle (K), elle suit l'arête d'épaule ; le chanfrein s'y resserre en 58 cm à 1,5 cm,
    # au ras du dessus de la prise d'air.
    if d <= D_K: w = pont_bord(d); return w + part_chanfrein(d) * (chine_brute(d) - w)
    u = lisse((d - D_K) / .58); return arete_x(d) + (1 - u) * EK + u * .015
def chine_z(d):
    if d <= D_K: return pont(d) + part_chanfrein(d) * (chine_z_brute(d) - pont(d))
    u = lisse((d - D_K) / .58); return arete_z(d) - (1 - u) * DK - u * .015
retrait_bas = courbe((0, .04), (4.4, .04), (5.6, .03), (7.0, .02), (10, .02))
def bas_x(d): return sil(d) - retrait_bas(d)
basse_z = courbe((0, .21), (1.5, .19), (3.0, .26), (3.5, .296), (4.0, .326), (4.5, .352), (5.0, .40), (5.6, .44), (6.5, .45), (7.5, .46),
                 (8.5, .46), (10, .46))   # relevée jusqu'au bord d'attaque de l'aile (image 4)
pont = courbe((0, .38), (.3, .45), (1, .53), (2.0, .68), (2.5, .745), (3.0, .76), (3.5, .79), (4.4, .845), (5.0, .90), (5.5, .95),
              (6.5, .94), (7.5, .95), (8.5, .96), (9.4, .96), (10, .94))
ventre_x = courbe((0, .10), (1, .27), (2.5, .56), (3.5, .74), (4.4, .84), (5.0, .90), (5.62, .94), (7.0, 1.0), (8.5, 1.0), (10, .95))
ventre_z = courbe((0, .15), (1, .05), (2.5, -.05), (3.5, -.09), (4.4, -.11), (5.0, -.12), (5.62, -.12), (7.0, -.10), (8.5, -.06), (10, .08))

# --- La bulle. En plan, un nez émoussé de 80 cm qui s'élargit presque en ligne droite jusqu'à 2 m, puis une queue ronde,
# qui est le cadre arrière. Section ronde au-dessus du pont, couronne à 1,41 m.
V0, VW, VF = 2.58, 4.55, 5.5   # nez de la bulle, fin du plus large, queue du cadre sur l'axe
def bulle_l(d):
    if d <= V0: return 0.0
    if d >= VW: return 1.0
    return (1 - .6 * max(0.0, (4.7 - d) / 2.0) ** 1.6) * (1 - max(0.0, (V0 + .2 - d) / .2) ** 2.5) ** .4
def cadre(x): return VW + (VF - VW) * (1 - min(1.0, x) ** 2.3) ** (1 / 2.3)
def x_cadre(d):
    # Demi-largeur du verre sur la queue ronde de la bulle, à la distance d.
    t = min(1.0, max(0.0, (d - VW) / (VF - VW))); return (1 - t ** 2.3) ** (1 / 2.3)
couronne = courbe((V0, .81), (2.9, .97), (3.1, 1.06), (3.5, 1.19), (4.0, 1.30), (4.5, 1.375), (5.0, 1.40), (5.5, 1.41))
def rond(c): return (1 - min(1.0, c) ** 2) ** .55
def bulle(x, d):
    zp, l = pont(d), bulle_l(d)
    return zp + (couronne(d) - zp) * rond(abs(x) / l) if abs(x) < l else zp
def sous_verre(x, d): return abs(x) < bulle_l(d) and d < cadre(abs(x))

# --- L'échine : dessus plat jusqu'à son arête, épaules à pans droits jusqu'à l'arête d'épaule, en pente vers la poupe.
epine_h = courbe((4.8, 1.41), (5.5, 1.41), (6.0, 1.37), (7.1, 1.28), (8.2, 1.16), (9.0, 1.06), (9.8, .98), (10, .96))
epine_a = courbe((4.8, .60), (6.0, .55), (8.0, .50), (10, .42))
largeur_nez = courbe((0, .04), (1, .10), (2.0, .13), (3.2, .16))
def pont_bord(d):
    # Le bord du pont jusqu'au coin bas de la bulle ; prolongé au-delà pour les raccords.
    nez = sil(d) - largeur_nez(d)
    if d < 2.4: return nez
    long = bulle_l(d) + .05
    if d < 3.4: t = lisse((d - 2.4) / 1.0); return (1 - t) * nez + t * long
    if d <= VW: return long
    t = lisse((d - VW) / .85); return (1 - t) * (1.0 + .05) + t * (chine_brute(d) - .03)
def bord(d): return pont_bord(d) if d <= D_K else arete_x(d)

# --- Derrière la bulle, les arêtes des images 4 et 5 de l'utilisateur (2026-10-31). La ligne haute quitte l'arceau à
# 80 cm de l'axe (A) et rejoint l'arête d'échine en M ; la diagonale monte du coin bas du verre (K) vers M ; l'arête
# d'épaule part de K, passe au haut de la prise d'air et remonte au capot. Entre elles : le dos bombé (6 à 13°), le pan
# raide (48 à 57°) et la terrasse (10 à 20°), qui porte la bande bleue ; derrière M, le dos plat et la terrasse. Les
# hauteurs posent les arêtes sur les traits, à la caméra calée du trois-quarts.
D_K, D_M = 4.75, 8.7
D_A = cadre(.80)
XK, ZK = pont_bord(D_K), pont(D_K)
EK, DK = part_chanfrein(D_K) * (chine_brute(D_K) - XK), part_chanfrein(D_K) * (ZK - chine_z_brute(D_K))   # le chanfrein en K
XM, ZM = epine_a(D_M), epine_h(D_M)
arete_x = courbe((D_K, XK), (5.33, 1.45), (6.0, 1.47), (6.8, 1.44), (7.5, 1.30), (8.0, 1.21), (8.5, 1.14), (9.4, 1.03), (10, .95))
arete_z = courbe((D_K, ZK), (5.0, .826), (5.33, .805), (6.8, .805), (7.5, .88), (8.0, .95), (8.5, .96), (9.4, .96), (10, .94))
haut_z = courbe((D_A, bulle(.8 * .999, D_A)), (5.6, 1.228), (6.0, 1.212), (6.5, 1.199), (7.0, 1.187), (7.5, 1.157), (8.0, 1.135),
                (8.5, 1.114), (D_M, ZM))
diag_x = courbe((D_K, 1.0), (5.3, 1.02), (5.92, .976), (6.88, .80), (8.16, .57), (D_M, XM + .025))
diag_z = courbe((D_K, ZK), (5.5, .91), (6.0, .946), (6.5, .972), (7.0, .994), (7.5, 1.023), (8.0, 1.055), (8.5, 1.085),
                (D_M, ZM - (ZM - arete_z(D_M)) * .025 / (arete_x(D_M) - XM)))
def ligne_haute(d):
    # Sur l'arceau jusqu'à A, puis l'arête du dos bombé jusqu'à M, puis l'arête d'échine.
    if d <= D_A: x = x_cadre(d); return x, bulle(.999 * x, d)
    if d >= D_M: return epine_a(d), epine_h(d)
    return .80 + (XM - .80) * (d - D_A) / (D_M - D_A), haut_z(d)
def diagonale(d):
    # Devant K, le bord du verre ; derrière M, 2,5 cm au-delà de l'arête d'échine, sur la terrasse.
    if d <= D_K: return 1.0, pont(d)
    if d >= D_M: a, h = epine_a(d), epine_h(d); return a + .025, h - (h - arete_z(d)) * .025 / (arete_x(d) - a)
    return diag_x(d), diag_z(d)
def epine(x, d):
    h, w = epine_h(d), bord(d); zr = arete_z(d) if d > D_K else pont(d)
    (xu, zu), (xg, zg) = ligne_haute(d), diagonale(d)
    if d >= D_M: return h if x <= xu else h - (h - zr) * min(1.0, (x - xu) / max(1e-3, w - xu))
    if x <= xu: return h - (h - zu) * (x / max(xu, 1e-3)) ** 1.6
    if x <= xg: return zu + (zg - zu) * (x - xu) / max(1e-6, xg - xu)
    return zg + (zr - zg) * min(1.0, (x - xg) / max(1e-3, w - xg))
def dessus(x, d):
    # Sous le verre, la cuve du cockpit ; derrière le cadre, la bulle passe à l'échine en 15 cm, sous le collier.
    x = abs(x); zb = bulle(x, d); f = cadre(x)
    if d < f: return max(pont(d), zb - 2 * (f - d)) if x < bulle_l(d) else pont(d)
    k = lisse((d - f) / .15); return (1 - k) * zb + k * epine(x, d)

# --- La section, demi-coque gauche de x = 0 vers l'extérieur : le dessus en trois tranches (le milieu de la bulle, son
# bord, le pont ; sur l'échine, ses arêtes), le haut et le bas du chanfrein, la chine basse, le coin du ventre, l'axe.
# Les anneaux de la coque, serrés là où la forme tourne vite (pointe, nez et queue de la bulle, coin bas K), lâches
# ailleurs ; plus les bornes des pans peints et des arêtes. Le maillage et l'atlas les partagent.
def _pas(a, b, h): n = max(1, round((b - a) / h)); return [a + (b - a) * i / n for i in range(n)]
ANNEAUX_D = sorted({round(v, 4) for v in [0, .01, .025, .05, .1, .15, .2] + _pas(.3, 2.4, .15) + _pas(2.4, 3.0, .05) + _pas(3.0, 4.5, .1)
                    + _pas(4.5, 5.6, .05) + _pas(5.6, 10.0, .1) + [10.0, 1.1, 2.3, 5.4, 7.4, V0, VW, VF, D_K, D_A, D_M]})
N1, N2, N3 = 8, 8, 5
NDESSUS = N1 + N2 + N3 + 1
ARETES = ('chanfrein orange', 'chine', 'flanc', 'ventre', 'axe')   # étiquette du point qui suit chaque segment après le dessus
def demi_section(d):
    # Derrière la bulle, les colonnes N1 et N1 + N2 suivent la ligne haute et la diagonale : les arêtes restent vives.
    w = bord(d); l = min(bulle_l(d), w)
    if d <= VW: p1 = max(.6 * l, .25 * w); p2 = max(l, min(.95 * w, p1 + .3 * w))
    else: k1 = lisse((d - D_A) / .15); p1 = (1 - k1) * .6 + k1 * ligne_haute(d)[0]; p2 = diagonale(d)[0]
    xs = [p1 * i / N1 for i in range(N1)] + [p1 + (p2 - p1) * i / N2 for i in range(N2)] + [p2 + (w - p2) * i / N3 for i in range(N3 + 1)]
    haut = [(x, dessus(x, d)) for x in xs]; (xw, zw), cx, cz = haut[-1], chine_x(d), chine_z(d)
    return haut + [(xw + .55 * (cx - xw), zw + .55 * (cz - zw)), (cx, cz), (bas_x(d), basse_z(d)), (ventre_x(d), ventre_z(d)), (0.0, ventre_z(d))]
def surface_z(x, d):
    # Hauteur de la coque au-dessus de (x, d), du milieu jusqu'à la chine.
    H = demi_section(d)[:NDESSUS + 2]; x = abs(x)
    for (x0, z0), (x1, z1) in zip(H, H[1:]):
        if x0 <= x <= x1 and x1 > x0: return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return H[-1][1]

# --- L'aile. Épaisseurs : dessus, dessous, culot haut et bas au bord de fuite, face du bord d'attaque. L'emplanture est
# un gant épais à culot droit, qui loge la petite tuyère ; l'aile s'affine jusqu'au saumon. Dièdre négatif de 8°.
AILE = [(1.15, .20, .30, .10, .25, .07), (2.05, .14, .24, .06, .20, .05), (2.35, .10, .08, .015, .015, .03), (3.30, .035, .03, .004, .004, .012)]
NERVURE = .3   # la nervure, à 30 % de la corde
def aile_corde(x):
    # Bord d'attaque en flèche de 44°, bord de fuite à 45° en sens inverse, saumon tronqué ; d du bord d'attaque et de fuite.
    return 4.97 + (x - 1.43) * .957, min(7.23 + (3.30 - x), 9.40)
def aile_zm(x): return .52 - .30 * (x - 1.15) / 2.15
def aile_epaisseurs(x):
    for (x0, *p0), (x1, *p1) in zip(AILE, AILE[1:]):
        if x0 <= x <= x1: return [u + (v - u) * (x - x0) / (x1 - x0) for u, v in zip(p0, p1)]
    return AILE[-1][1:] if x > AILE[-1][0] else AILE[0][1:]
def aile_section(x):
    # (d, z) : bas et haut de la face d'attaque, nervure dessus, culot haut et bas, nervure dessous.
    a, b = aile_corde(x); c = b - a; zm = aile_zm(x); tu, tl, eu, el, le = aile_epaisseurs(x)
    return [(a, zm - le / 2), (a, zm + le / 2), (a + NERVURE * c, zm + tu), (b, zm + eu), (b, zm - el), (a + NERVURE * c, zm - tl)]
# Les élevons : un intérieur et un extérieur par aile, de 22 % de corde, charnière sur le dessus.
ELEVONS = ((1.62, 2.30), (2.38, 3.10)); CORDE_ELEVON = .22

# --- La prise d'air, bouche biaisée vers l'avant et le dehors sous l'arête d'épaule, fondue dans la coque en 1,5 m ;
# sections (d, (cx, cz, demi-largeur, demi-hauteur, exposant de super-ellipse)).
PRISE = [(5.33, (1.52, .58, .32, .21, 9.0)), (6.00, (1.48, .58, .29, .19, 7.0)), (6.80, (1.40, .56, .14, .11, 4.0))]
BIAIS_PRISE = (.26, .06)   # recul de la bouche vers le dehors et vers le haut
# Les capots moteurs à douze pans, tête noyée dans l'épaule ; ceux des petites tuyères dans le gant d'aile.
MOTEUR_C, MOTEUR = (.93, .50), [(8.6, .36), (9.0, .45), (10.0, .47)]
PETIT_C, PETIT = (1.85, .36), [(7.5, .08), (7.9, .20), (8.3, .27), (8.8, .28)]
# Tuyères en profil de tour (d, rayon) : lèvre, divergent, foyer au fond. Rayons de foyer et lèvres pour ShipPlume.
GRANDE = [(9.7, 0), (9.7, .37), (10.10, .36), (10.10, .31), (9.80, .13), (9.80, .09), (9.80, 0)]
PETITE = [(8.6, 0), (8.6, .245), (8.92, .24), (8.92, .20), (8.74, .08), (8.74, .06), (8.74, 0)]

# --- La bande bleue du trois-quarts : sur la terrasse, t allant de la diagonale (0) à l'arête d'épaule (1) ; bord avant
# de d 5,0 à 5,3, bord arrière de M à d 7,5. Marche sur des tableaux numpy.
def dans_bande(d, t): return (D_K < d < D_M) & (5.0 + .3 * t < d) & (d < D_M - 1.2 * t)

# --- Le pilote : l'oeil, celui du moteur (D3DAppShip.cpp, kEyeAhead et kEyeUp), le casque de 13,5 cm.
OEIL = (0.0, -.9192, 1.03); CASQUE = (0.0, -.85, 1.06, .135)

if __name__ == '__main__':
    # Contrôles : la bulle sort du pont, le casque passe dessous, la chine reste sous le pont, l'aile est fermée.
    for d in (3.0, 3.5, 4.0, 4.4, 4.5):
        l = bulle_l(d); assert abs(bulle(l * .9999, d) - pont(d)) < .03, d
        assert bord(d) > l + .03, ('le pont longe la bulle', d)
    garde = bulle(0, 4.4) - (CASQUE[2] + CASQUE[3]); assert garde > .15, garde
    assert OEIL[2] - pont(4.4) > .15, 'oeil au-dessus du seuil'
    for d in [k * .25 for k in range(41)]:
        H = demi_section(d); assert len(H) == NDESSUS + 5
        assert H[NDESSUS + 1][1] < H[NDESSUS - 1][1] + 1e-6, ('chine sous le pont', d)
        assert all(z > -.2 for _, z in H), d
    for x in (1.2, 2.0, 3.0): a, b = aile_corde(x); assert b > a + .4, x
    assert dans_bande(6.5, .5) and not dans_bande(4.9, .5) and not dans_bande(8.5, .5)
    # Derrière la bulle : colonnes rangées, dos moins pentu que le pan raide, terrasse moins pentue que lui.
    pente = lambda a, b: math.degrees(math.atan2(a[1] - b[1], b[0] - a[0]))
    for d in [4.6 + k * .1 for k in range(55)]:
        H = demi_section(d); assert all(q[0] >= p[0] - 1e-9 for p, q in zip(H[:NDESSUS - 1], H[1:NDESSUS])), ('colonnes', d)
        if D_A + .2 < d < D_M - .3:
            U, G, R = H[N1], H[N1 + N2], H[NDESSUS - 1]
            assert pente((0, epine_h(d)), U) < pente(U, G) - 10 and pente(G, R) < pente(U, G) - 15, ('arêtes du dos', d)
    print('forme du chasseur OK : bulle', round(VF - V0, 2), 'x 2.0 m, garde au casque', round(garde, 3), 'm')
