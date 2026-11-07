"""La forme du vaisseau, variante N : le dessus creusé sous la verrière, la bulle en goutte et ses seuils.

Une seule source pour design_v2.py, details_v3.py et controle_geometrie.py. Le moteur en recopie les nombres
(Ship.hlsli, ShipCanopy) : la goutte, la bulle et les trois facettes du dessus.
Repère du vaisseau : nez vers -Y, haut +Z, gauche du pilote +X, en mètres.
"""
import math
from mathutils import Vector

apex = Vector((0, -7.18, 0)); top = Vector((0, 2.3375, 2.10)); chine = Vector((3.10, 2.59525, .038))
F, S, A, V = .332, .692, .788, .437   # repères de l'ancienne verrière, en (u, v) des facettes du dessus
Z = Vector((0, 0, 1))

def point_plan(u, v, side=1):
    # Point des facettes du dessus d'origine : u de la pointe à la poupe, v de l'arête à la chine.
    p = apex.lerp(top.lerp(chine, v), u); p.x *= side; return p

def plan_uw(x, y):
    # (u, w = u v) d'un point du plan, sur la facette de son côté : x = 3,1 w, y linéaire en u et w.
    w = abs(x) / chine.x
    return (y - apex.y - (chine.y - top.y) * w) / (top.y - apex.y), w

# Le creux : l'arête garde sa pente jusqu'au nez de l'ancienne verrière F, s'aplatit jusqu'à A, CREUX plus bas,
# puis remonte au sommet de la poupe, qui ne bouge pas. Trois facettes de chaque côté, en éventail depuis le coin
# de chine de la poupe : les plis partent de F et de A vers ce coin.
CREUX = .329
Fr = point_plan(F, 0); Ar = point_plan(A, 0) - Vector((0, 0, CREUX))
def _plan(a, b, c):
    n = (b - a).cross(c - a).normalized(); n = n if n.z > 0 else -n; return n, n.dot(a)
FACETTES = {s: [_plan(apex, Fr, c), _plan(Fr, Ar, c), _plan(Ar, top, c)]
            for s, c in ((1, chine), (-1, Vector((-chine.x, chine.y, chine.z))))}

def dessus_z(x, y):
    # Le dessus : la facette du nez devant le pli de F, celle de la verrière entre les plis, celle de l'arrière
    # derrière le pli de A. Pli de F convexe, pli de A rentrant : max(min(nez, verrière), arrière).
    h = [(k - n.x * x - n.y * y) / n.z for n, k in FACETTES[1 if x >= 0 else -1]]
    return max(min(h[0], h[1]), h[2])

def facette(u, w):
    # 0 devant le pli de F, 1 entre les plis, 2 derrière le pli de A ; plis droits en (u, w).
    if u - (1 - A) * w - A > 1e-9: return 2
    if u - (1 - F) * w - F > 1e-9: return 1
    return 0

def normale(region, side):
    return FACETTES[side][region][0].copy()

# La goutte de la verrière, en plan : deux demi-ellipses jointes au plus large, sans aucune pointe.
GY0, GYC, GY1, GW, GZT = -3.72, -1.45, .52, .80, 1.48
def goutte(y):
    if y <= GY0 or y >= GY1: return 0.0
    a = GYC - GY0 if y < GYC else GY1 - GYC
    return GW * math.sqrt(max(0.0, 1 - ((y - GYC) / a) ** 2))

def goutte_angle(t):
    # t = 0 à la queue, pi / 2 au plus large à gauche (+X), pi au nez.
    a = GY1 - GYC if math.cos(t) > 0 else GYC - GY0
    return GW * math.sin(t), GYC + a * math.cos(t)

def normale_goutte(t):
    # Normale sortante du contour, horizontale.
    a = GY1 - GYC if math.cos(t) > 0 else GYC - GY0
    return Vector((math.sin(t) / GW, math.cos(t) / a, 0)).normalized()

def seuil(t):
    x, y = goutte_angle(t); return Vector((x, y, dessus_z(x, y)))

def bulle_dessus(y):
    # Le sommet de la bulle, de son nez à sa queue, posés sur le dessus ; plus haut au plus large.
    zf, zr = dessus_z(0, GY0), dessus_z(0, GY1)
    if y < GYC: return zf + (GZT - zf) * math.sin(.5 * math.pi * (y - GY0) / (GYC - GY0)) ** .7
    return zr + (GZT - zr) * math.cos(.5 * math.pi * (y - GYC) / (GY1 - GYC)) ** .9

BOMBE = .55   # section : 1 - s², à cette puissance ; sous 1, des flancs pleins, presque verticaux au pied
def bulle_z(x, y):
    # Hauteur de la bulle au-dessus du point (x, y), None hors de la goutte.
    h = goutte(y)
    if h <= 1e-6 or abs(x) >= h: return None
    ze = dessus_z(h, y); zt = max(bulle_dessus(y), ze)
    return ze + (zt - ze) * (1 - (x / h) ** 2) ** BOMBE

def bulle_x(y, z):
    # Demi-largeur intérieure de la bulle à la hauteur z ; la goutte même sous le seuil.
    h = goutte(y)
    if h <= 1e-6: return 0.0
    ze = dessus_z(h, y); zt = max(bulle_dessus(y), ze)
    if z <= ze or zt - ze < 1e-6: return h
    q = min(1.0, (z - ze) / (zt - ze)); return h * math.sqrt(max(0.0, 1 - q ** (1 / BOMBE)))

# Les parois de la cuve descendent du seuil, évasées de LEAN vers le plancher.
LEAN = .08
def descente(t):
    return (normale_goutte(t) * LEAN - Z).normalized()

# Pourtour de la verrière, entre la goutte et la découpe des tôles ; la découpe est un polygone convexe.
ANNEAU = .15
def decoupe(k=13):
    # Côté gauche (x >= 0), de la queue au nez : la goutte poussée de ANNEAU le long de sa normale.
    pts = []
    for i in range(k):
        t = math.pi * i / (k - 1); x, y = goutte_angle(t); n = normale_goutte(t)
        pts.append((max(0.0, x + n.x * ANNEAU), y + n.y * ANNEAU))
    return pts

def dans_decoupe(x, y, marge=0.0):
    # Le point du plan est-il dans la découpe (des deux côtés), à marge près ?
    p = decoupe(); x = abs(x)
    if not (p[-1][1] - marge <= y <= p[0][1] + marge): return False
    for (x0, y0), (x1, y1) in zip(p, p[1:]):
        if min(y0, y1) <= y <= max(y0, y1) and abs(y1 - y0) > 1e-9:
            return x <= x0 + (x1 - x0) * (y - y0) / (y1 - y0) + marge
    return False

if __name__ == '__main__':
    # Contrôle : la bulle sort du dessus au seuil, son sommet est GZT, la découpe entoure la goutte.
    for y in (-3.0, GYC, -.5, .3):
        h = goutte(y); assert abs(bulle_z(h * .9999, y) - dessus_z(h, y)) < .02, y
        assert dans_decoupe(h, y) and not dans_decoupe(h + ANNEAU + .05, y), y
    assert abs(bulle_z(0, GYC) - GZT) < 1e-6
    print('forme OK', 'creux', CREUX, 'sommet de bulle', GZT)
