"""Les textures du chasseur, peintes dans un atlas unique sur sa deuxième UV (UVDetail) : couleur, métal-rugosité,
normale et occlusion.

Usage : python textures_chasseur.py   (Python 3, numpy et Pillow, sans Blender) ; design_chasseur.py lit les images.
La peinture suit les pans de forme_chasseur.py : tôles bordées de joints et de rivets, décalées d'une bande à l'autre ;
bande orange du chanfrein, panneaux bleus du nez et des joues, bande bleue diagonale des épaules, ventre plus sombre ;
éclats aux arêtes, coulures vers l'arrière, suie à la poupe. L'atlas tient la demi-coque, en miroir pour les deux côtés,
le dessus et le dessous d'une aile, en miroir aussi, et un nuancier pour les petites pièces.
"""
import math, os
import numpy as np
import forme_chasseur as F

ROOT = os.path.dirname(os.path.abspath(__file__))
# --- L'atlas, en UV de Blender : v = 0 en bas de l'image.
N = 4096
ECH = .098                                     # unités UV par mètre : 401 px/m
COQUE = (.01, .01)                             # u = u0 + ECH d ; v = v0 + ECH s, s l'abscisse sur la demi-section depuis l'axe
AILE_D0, AILE_X0 = 4.62, 1.10
AILE_HAUT, AILE_BAS = (.01, .43), (.01, .67)   # u = u0 + ECH (d - AILE_D0) ; v = v0 + ECH (x - AILE_X0)
TEINTES = ('gris', 'bleu', 'orange', 'metal', 'tuyere', 'ventre', 'noir', 'ceramique')
# Les capots déroulés : u le long de d, v autour de la section depuis son point le plus haut, à 0,9 fois l'échelle.
ECH_CAPOT = ECH * .9
CAPOTS = {'moteur': ((.52, .72), 8.5), 'petit': ((.665, .72), 7.4), 'prise': ((.80, .72), 5.0)}   # (u0, v0), d d'origine
def uv_capot(nom, d, s):
    (u0, v0), d0 = CAPOTS[nom]; return (u0 + ECH_CAPOT * (d - d0), v0 + ECH_CAPOT * s)
def case(nom):
    # Rectangle (u0, v0, u1, v1) d'une teinte du nuancier, à droite de l'aile.
    k = TEINTES.index(nom); i, j = k % 4, k // 4
    return (.52 + i * .118, .43 + j * .14, .63 + i * .118, .56 + j * .14)

# Peintures linéaires, proches du concept : métal gris clair peint, bleu pétrole, orange de signalisation.
GRIS, BLEU, ORANGE, VENTRE = (.31, .31, .305), (.03, .095, .14), (.56, .155, .023), (.23, .23, .225)
INTERIEUR = (.01, .893, .50, .995)   # u0, v0, u1, v1 : la tôlerie du cockpit
ANTHRACITE, ROUILLE, SALE = (.055, .058, .062), (.17, .085, .04), (.10, .085, .06)
COULEURS = {'gris': GRIS, 'bleu': BLEU, 'orange': ORANGE, 'metal': (.11, .11, .115), 'tuyere': (.16, .14, .12),
            'ventre': VENTRE, 'noir': (.02, .02, .022), 'ceramique': (.07, .07, .072)}
RUGO_METAL = {'gris': (.66, 0), 'bleu': (.62, 0), 'orange': (.6, 0), 'metal': (.38, .85), 'tuyere': (.32, .9),
              'ventre': (.6, 0), 'noir': (.7, .2), 'ceramique': (.72, 0)}

def bruit(rng, n, echelles):
    # Bruit lisse périodique : somme d'ondes de basses fréquences.
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) * (2 * np.pi / n); out = np.zeros((n, n), np.float32)
    for k in echelles:
        for _ in range(6):
            kx, ky = rng.integers(-k, k + 1, 2); out += rng.uniform(.4, 1) * np.cos(kx * xx + ky * yy + rng.uniform(0, 6.3)).astype(np.float32)
    return out / max(1e-6, np.abs(out).max())

def bruit_valeur(rng, n, cu, cv, octaves=3):
    # Bruit de valeur : grilles aléatoires agrandies en bicubique, cellules de cu x cv pixels, octaves de 4 en 4 ; dans [-1, 1].
    from PIL import Image
    out = np.zeros((n, n), np.float32); amp, tot = 1.0, 0.0
    for _ in range(octaves):
        g = rng.random((max(2, n // cv), max(2, n // cu))).astype(np.float32)
        out += amp * (np.asarray(Image.fromarray(g, mode='F').resize((n, n), Image.BICUBIC)) - .5); tot += amp
        amp *= .5; cu = max(2, cu // 4); cv = max(2, cv // 4)
    return np.clip(out / tot * 2.6, -1, 1)

def generer():
    rng = np.random.default_rng(31)
    v_px = (np.arange(N) + .5) / N                       # v de chaque rangée, de bas en haut
    couleur = np.zeros((N, N, 3), np.float32) + .25; haut = np.zeros((N, N), np.float32)
    rugo = np.full((N, N), .6, np.float32); metal = np.zeros((N, N), np.float32); occ = np.ones((N, N), np.float32)
    tache = bruit(rng, N, (3, 7, 15)); grain = bruit(rng, N, (40, 90)); usure = bruit(rng, N, (5, 11))
    trainee = bruit(rng, N, (60,)); trainee = np.clip(trainee, 0, None)
    jointure = np.zeros((N, N), np.float32); peint = np.zeros((N, N), bool)   # proximité des joints ; texels peints

    def rivets_et_joints(col, s, dd, joints_s, cadres_par_bande):
        # Relief et occlusion d'une colonne : joints creux de 4 mm, rivets de 9 mm à 2 cm des joints, tous les 12 cm.
        h = np.zeros_like(s); o = np.ones_like(s); bande = np.searchsorted(joints_s, s) - 1
        dj = np.min(np.abs(s[:, None] - joints_s[None, :]), axis=1)
        for j in range(len(joints_s) - 1):
            m = bande == j
            if not m.any(): continue
            for f in cadres_par_bande(j):
                dj[m] = np.minimum(dj[m], abs(dd - f))
        joint = np.clip(1 - dj / .003, 0, 1); halo = np.clip(1 - dj / .02, 0, 1)
        h -= .0015 * joint; o *= (1 - .7 * joint) * (1 - .12 * halo)
        # Rivets le long des joints longitudinaux : une rangée de chaque côté, au pas de 12 cm en d.
        ph = (dd / .15) % 1; rd = min(ph, 1 - ph) * .15
        for g in joints_s:
            for e in (-.025, .025):
                r = np.hypot(s - (g + e), rd); dome = np.clip(1 - (r / .007) ** 2, 0, 1)
                h += .0008 * np.sqrt(dome); o *= 1 - .45 * np.clip(1 - np.abs(r - .007) / .0025, 0, 1)
        # Rivets le long des cadres de chaque bande, au pas de 12 cm en s.
        for j in range(len(joints_s) - 1):
            m = bande == j
            if not m.any(): continue
            for f in cadres_par_bande(j):
                for e in (-.025, .025):
                    if abs(dd - (f + e)) > .007: continue
                    ss = s[m] - joints_s[j]; ph2 = (ss / .15) % 1; r = np.hypot(dd - (f + e), np.minimum(ph2, 1 - ph2) * .15)
                    dome = np.clip(1 - (r / .007) ** 2, 0, 1); h[m] += .0007 * np.sqrt(dome)
        return h, o, bande, dj, halo

    # --- La demi-coque, colonne par colonne : chaque colonne est une section, d fixe.
    CADRES = [0.0, .55, 1.1, 1.65, 2.3, 2.9, 3.5, 4.1, 4.75, 5.4, 6.05, 6.7, 7.4, 8.05, 8.7, 9.35, 10.0]
    # Le tour du verre en plan, (|x|, d) : les flancs de la bulle, puis sa queue ronde.
    TOUR = np.array([(F.bulle_l(dd), dd) for dd in np.linspace(F.V0, F.VW, 120)] + [(F.x_cadre(dd), dd) for dd in np.linspace(F.VW, F.VF, 80)])
    k0 = F.NDESSUS - 1
    # La bande orange quitte le chanfrein 30 cm avant le plus large de la bulle : sa largeur, comptée depuis le verre,
    # passe de celle du chanfrein à 14 cm en 60 cm.
    D_ORANGE = F.VW - .30; L0 = F.chine_x(D_ORANGE) - F.bulle_l(D_ORANGE)
    def largeur_orange(d):
        t = min(1.0, max(0.0, (d - D_ORANGE) / .6)); t = t * t * (3 - 2 * t); return L0 + (.14 - L0) * t
    SECTIONS = []
    for dd in F.ANNEAUX_D:
        Hs = np.array(F.demi_section(dd)); As = np.concatenate(([0.0], np.cumsum(np.hypot(*np.diff(Hs, axis=0).T)))); SECTIONS.append((Hs, As))
    for c in range(N):
        u = (c + .5) / N; d = (u - COQUE[0]) / ECH
        if not 0 <= d <= 10: continue
        i_ = min(max(int(np.searchsorted(F.ANNEAUX_D, d)) - 1, 0), len(F.ANNEAUX_D) - 2); d0_, d1_ = F.ANNEAUX_D[i_], F.ANNEAUX_D[i_ + 1]
        tt = (d - d0_) / (d1_ - d0_); (H0, A0), (H1, A1) = SECTIONS[i_], SECTIONS[i_ + 1]
        H = [tuple(p) for p in H0 * (1 - tt) + H1 * tt]; A = A0 * (1 - tt) + A1 * tt   # comme le maillage entre ses anneaux
        rows = np.nonzero((v_px >= COQUE[1]) & (v_px <= COQUE[1] + ECH * A[-1]))[0]
        if not len(rows): continue
        s = (v_px[rows] - COQUE[1]) / ECH; k = np.clip(np.searchsorted(A, s) - 1, 0, len(H) - 2)
        t = (s - A[k]) / np.maximum(A[k + 1] - A[k], 1e-9); Hx = np.array([p[0] for p in H]); Hz = np.array([p[1] for p in H])
        x = Hx[k] + t * (Hx[k + 1] - Hx[k]); z = Hz[k] + t * (Hz[k + 1] - Hz[k]); y = F.Y(d)
        # Joints longitudinaux : l'axe, la ligne haute (arête d'échine derrière M), la diagonale, les arêtes du chanfrein,
        # la chine, la chine basse, le coin du ventre ; et une ligne au milieu des pans larges.
        terrasse = F.D_K < d < F.D_M
        lignes = [0.0, A[k0 + 2], A[k0 + 3], A[k0 + 4], A[-1]] + ([] if terrasse and d > 5.33 else [A[k0], A[k0 + 1]])   # le chanfrein de 1,5 cm sans joints
        if d > F.VF: lignes.append(A[F.N1])
        if terrasse and d > F.D_K + .1: lignes.append(A[F.N1 + F.N2])
        for a0, a1 in ((A[k0 + 2], A[k0 + 3]), (A[k0 + 4], A[-1]), (A[k0 + 3], A[k0 + 4])):
            n = int((a1 - a0) / .42)
            lignes += [a0 + (a1 - a0) * i / (n + 1) for i in range(1, n + 1)]
        a0 = A[F.N1 + F.N2] if terrasse else (A[F.N1] if d > F.VF else 0.0)
        if A[k0] - a0 > .5 and not (F.VW - .2 < d < F.VF + .4): lignes.append(.5 * (a0 + A[k0]))   # pas derrière la bulle, où s ondule
        lignes = np.array(sorted(set(round(v, 5) for v in lignes)))
        def cadres(j):
            # Les cadres de la bande j : décalés d'une demi-baie une bande sur deux, plus un joint tiré au hasard.
            base = CADRES if j % 2 == 0 else [.5 * (a + b) for a, b in zip(CADRES, CADRES[1:])]
            return [f for f in base if abs(f - d) < .05]
        h, o, bande, dj, halo = rivets_et_joints(c, s, d, lignes, cadres)
        # Trappes d'accès : une tôle sur sept du flanc et du dessous, si elle est assez grande ; cadre gravé à 4 cm du bord,
        # fond plus sombre, quatre vis.
        trappe = np.zeros(len(s), bool)
        for j in range(len(lignes) - 1):
            m = bande == j; sj0, sj1 = lignes[j], lignes[j + 1]
            if not m.any() or sj1 - sj0 < .22: continue
            base = CADRES if j % 2 == 0 else [.5 * (a + b) for a, b in zip(CADRES, CADRES[1:])]
            i = int(np.searchsorted(base, d)) - 1
            if not 0 <= i < len(base) - 1 or base[i + 1] - base[i] < .4: continue
            f0, f1 = base[i] + .045, base[i + 1] - .045
            if (math.sin(j * 7.13 + i * 3.71) * 43758.5453) % 1 > .16 or not f0 < d < f1: continue
            mm = np.nonzero(m)[0]; mm = mm[(s[mm] > sj0 + .045) & (s[mm] < sj1 - .045) & (k[mm] >= k0 + 2)]
            if not len(mm): continue
            dc = np.minimum(np.minimum(s[mm] - sj0 - .045, sj1 - .045 - s[mm]), min(d - f0, f1 - d))
            ligne_t = np.clip(1 - dc / .0022, 0, 1); h[mm] -= .0012 * ligne_t; o[mm] *= 1 - .6 * ligne_t; trappe[mm] = True
            for vs in (sj0 + .065, sj1 - .065):
                for vd in (f0 + .02, f1 - .02):
                    r = np.hypot(s[mm] - vs, d - vd); o[mm] *= 1 - .5 * np.clip(1 - r / .006, 0, 1)
        # Grilles d'aération à lames : sur le panneau bleu du nez, sous la bulle, sur le dos derrière la bulle.
        for (g0, g1, sa, sb) in ((1.45, 1.85, A[k0 + 2] + .05, A[k0 + 2] + .14), (3.45, 3.95, A[k0 + 2] + .06, A[k0 + 2] + .14),
                                 (6.25, 6.55, .12, .26)):
            if g0 < d < g1:
                mm = (s > sa) & (s < sb)
                lame = (((s[mm] - sa) / .012) % 1); h[mm] = -.004 + .003 * (lame < .55); o[mm] *= .35 + .4 * (lame < .55)
                trappe[mm] = True
        # La peinture par pan.
        teinte = np.tile(np.array(GRIS, np.float32), (len(rows), 1)); seg = k
        sous = np.array([F.sous_verre(xi, d) for xi in x]) if F.V0 < d < F.VF + .05 else np.zeros(len(x), bool)
        dessus = seg < k0
        if terrasse:   # la bande bleue, sur la terrasse entre la diagonale et l'arête d'épaule
            tc = (s - A[F.N1 + F.N2]) / max(A[k0] - A[F.N1 + F.N2], 1e-6)
            teinte[(seg >= F.N1 + F.N2) & (seg < k0) & F.dans_bande(d, tc)] = BLEU
            if F.dans_bande(d, 1.0): teinte[(seg == k0) | (seg == k0 + 1)] = BLEU   # le petit chanfrein sous l'arête, avec elle
        if F.V0 - .15 < d < F.VF + .2:   # autour du verre, 5,5 cm d'anthracite ; au coin de la bulle, le chanfrein orange
            m = (seg <= k0 + 1) & ~sous    # se resserre et file en bande de queue, d'un seul tenant
            if m.any():
                dist = np.min(np.hypot(np.abs(x[m])[:, None] - TOUR[None, :, 0], d - TOUR[None, :, 1]), axis=1); idx = np.nonzero(m)[0]
                if d >= D_ORANGE: teinte[idx[(dist >= .055) & (dist < largeur_orange(d))]] = ORANGE
                teinte[idx[dist < .055]] = ANTHRACITE
        if .2 < d < D_ORANGE: teinte[(seg == k0) | (seg == k0 + 1)] = ORANGE   # tout le chanfrein, jusqu'au coin de la bulle
        flanc = seg == k0 + 2
        if 1.1 < d < 2.3 or 5.4 < d < 7.4: teinte[flanc] = BLEU
        teinte[seg >= k0 + 3] = VENTRE
        # Ton de chaque tôle, usure aux arêtes vives et aux joints, coulures vers l'arrière, suie de poupe.
        ton = 1 + .11 * np.sin(bande * 12.9898 + np.floor(d / .6) * 78.233 + 1.7) * np.cos(bande * 4.1 + np.floor(d / .6))
        vives = [A[k0], A[k0 + 2], A[k0 + 3]] + ([A[F.N1], A[F.N1 + F.N2]] if terrasse else [])
        bord_vif = np.min(np.abs(s[:, None] - np.array(vives)[None, :]), axis=1)
        eclat = ((np.clip(1 - bord_vif / .012, 0, 1) * (usure[rows, c] > .1)) + np.clip(1 - dj / .006, 0, 1) * (grain[rows, c] > .55) * .7) > .5
        coulure = trainee[rows, c] * np.clip((z - .9) / -.6, 0, 1) * .12
        suie = np.clip((d - 9.2) / .8, 0, 1) * .35
        mod = (ton * (1 + .12 * tache[rows, c] + .03 * usure[rows, c] + .006 * grain[rows, c]) * (1 - coulure) * (1 - suie) * (.3 + .7 * o))[:, None]   # joints encrassés
        mod[trappe] *= .82
        rgb = teinte * mod; rgb[eclat] = rgb[eclat] * .4 + .6 * np.array((.36, .36, .36), np.float32)
        couleur[rows, c] = rgb; haut[rows, c] = h; occ[rows, c] = o; jointure[rows, c] = halo; peint[rows, c] = True
        rugo[rows, c] = np.where(eclat, .35, .66 + .06 * tache[rows, c] + coulure); metal[rows, c] = np.where(eclat, .75, 0)

    # --- Le dessus et le dessous d'une aile, en plan : nervures à x fixe, longerons à fractions de corde.
    for (u0, v0), dessous in ((AILE_HAUT, False), (AILE_BAS, True)):
        for c in range(N):
            u = (c + .5) / N; d = AILE_D0 + (u - u0) / ECH
            rows = np.nonzero((v_px >= v0) & (v_px <= v0 + ECH * 2.25))[0]
            if not (4.6 < d < 9.45) or not len(rows): continue
            x = AILE_X0 + (v_px[rows] - v0) / ECH; xc = np.clip(x, 1.15, 3.30)
            a = 4.97 + (xc - 1.43) * .957; b = np.minimum(7.23 + (3.30 - xc), 9.40); f = (d - a) / np.maximum(b - a, 1e-6)
            dedans = (x >= 1.15) & (x <= 3.30) & (f >= -.01) & (f <= 1.01)
            if not dedans.any(): continue
            dist = np.full(len(x), 9.0)
            for xr in (1.45, 1.80, 2.15, 2.50, 2.85, 3.15): dist = np.minimum(dist, np.abs(x - xr))
            for fl in (.12, .30, .55, 1 - F.CORDE_ELEVON): dist = np.minimum(dist, np.abs(f - fl) * (b - a))
            joint = np.clip(1 - dist / .003, 0, 1); halo = np.clip(1 - dist / .02, 0, 1); h = -.0015 * joint; o = (1 - .7 * joint) * (1 - .12 * halo)
            ph = (d / .15) % 1; rd = min(ph, 1 - ph) * .15
            for xr in (1.45, 1.80, 2.15, 2.50, 2.85, 3.15):
                for e in (-.025, .025):
                    r = np.hypot(x - (xr + e), rd); h += .0007 * np.sqrt(np.clip(1 - (r / .007) ** 2, 0, 1))
            teinte = np.tile(np.array(GRIS, np.float32), (len(rows), 1))
            yv = F.Y(d)
            if not dessous:
                teinte[(x < 2.3) & (yv < F.Y(7.4))] = BLEU
                o_band = .51 * x + 1.2 * yv; teinte[(o_band > 3.666) & (o_band < 4.186) & (x > 1.9)] = ORANGE
            else:
                teinte[:] = VENTRE
            ton = 1 + .03 * np.sin(np.floor(x / .35) * 12.9898 + np.floor(f * 4) * 78.233)
            rgb = teinte * (ton * (1 + .09 * tache[rows, c]) * (.3 + .7 * o))[:, None]
            couleur[rows[dedans], c] = rgb[dedans]; haut[rows[dedans], c] = h[dedans]; occ[rows[dedans], c] = o[dedans]
            jointure[rows[dedans], c] = halo[dedans]; peint[rows[dedans], c] = True
            rugo[rows[dedans], c] = .66 + .05 * tache[rows[dedans], c]; metal[rows[dedans], c] = 0

    # --- Les capots déroulés : tôles de 40 cm en d, joints sur une arête sur deux du polygone, rivets ; la poupe chauffée.
    import forme_chasseur as Fc
    for nom, perim, longueur in (('moteur', 12 * 2 * .47 * math.sin(math.pi / 12), 1.5), ('petit', 12 * 2 * .28 * math.sin(math.pi / 12), 1.4),
                                 ('prise', 2.0, 1.85)):
        (u0, v0), d0 = CAPOTS[nom]; cs = np.arange(int(u0 * N), int((u0 + ECH_CAPOT * longueur) * N)); rs = np.arange(int(v0 * N), int((v0 + ECH_CAPOT * perim) * N))
        dd = d0 + ((cs + .5) / N - u0) / ECH_CAPOT; ss = ((rs + .5) / N - v0) / ECH_CAPOT
        D_, S_ = np.meshgrid(dd, ss); pas_s = perim / 6 if nom != 'prise' else perim / 4
        dist = np.minimum(np.abs(((D_ - d0) / .4 + .5) % 1 - .5) * .4, np.abs((S_ / pas_s + .5) % 1 - .5) * pas_s)
        joint = np.clip(1 - dist / .003, 0, 1); halo = np.clip(1 - dist / .02, 0, 1); h = -.0015 * joint; o = (1 - .7 * joint) * (1 - .12 * halo)
        for e in (-.025, .025):
            for per, coord, pas in ((.4, D_ - d0, S_), (pas_s, S_, D_ - d0)):
                lig = np.abs((coord / per + .5) % 1 - .5) * per; r = np.hypot(lig - abs(e), np.abs((pas / .15 + .5) % 1 - .5) * .15)
                dome = np.clip(1 - (r / .007) ** 2, 0, 1); h += .0008 * np.sqrt(dome); o *= 1 - .4 * np.clip(1 - np.abs(r - .007) / .0025, 0, 1)
        teinte = np.array(BLEU if nom == 'prise' else GRIS, np.float32)
        rgb = teinte * ((1 + .12 * tache[np.ix_(rs, cs)]) * (.3 + .7 * o))[..., None]
        if nom == 'moteur':   # chauffe : bronze puis bleu nuit sur les 30 derniers cm, suie
            t = np.clip((D_ - 9.7) / .3, 0, 1)[..., None]
            rgb = rgb * (1 - .55 * t) + np.array((.10, .07, .05), np.float32) * .55 * t
        couleur[np.ix_(rs, cs)] = rgb; haut[np.ix_(rs, cs)] = h; occ[np.ix_(rs, cs)] = o
        jointure[np.ix_(rs, cs)] = halo; peint[np.ix_(rs, cs)] = True
        rugo[np.ix_(rs, cs)] = .66 + .05 * tache[np.ix_(rs, cs)]; metal[np.ix_(rs, cs)] = 0

    # --- La tôlerie du cockpit, en haut à gauche de l'atlas : panneaux de 30 x 20 cm décalés d'un rang à l'autre, joints
    # fins, une vis à chaque coin, un ton par panneau ; ni rouille ni crasse (hors de l'usure de la coque).
    cs = np.arange(int(INTERIEUR[0] * N), int(INTERIEUR[2] * N)); rs = np.nonzero((v_px >= INTERIEUR[1]) & (v_px <= INTERIEUR[3]))[0]
    A_, B_ = np.meshgrid(((cs + .5) / N - INTERIEUR[0]) / ECH, (v_px[rs] - INTERIEUR[1]) / ECH)
    rang = np.floor(B_ / .20); aa = A_ + .15 * (rang % 2); col = np.floor(aa / .30)
    fa, fb = (aa / .30) % 1, (B_ / .20) % 1; da, db = np.minimum(fa, 1 - fa) * .30, np.minimum(fb, 1 - fb) * .20
    joint = np.clip(1 - np.minimum(da, db) / .0015, 0, 1); h = -.0009 * joint; o = 1 - .55 * joint
    r = np.hypot(da - .016, db - .016); vis = np.clip(1 - r / .003, 0, 1); h += .0005 * vis; o *= 1 - .35 * np.clip(1 - np.abs(r - .003) / .0012, 0, 1)
    ton = 1 + .05 * np.sin(col * 12.9898 + rang * 78.233)
    rgb = np.array((.118, .126, .135), np.float32) * (ton * (.45 + .55 * o) * (1 + .03 * tache[np.ix_(rs, cs)]))[..., None]
    couleur[np.ix_(rs, cs)] = rgb; haut[np.ix_(rs, cs)] = h; occ[np.ix_(rs, cs)] = o
    rugo[np.ix_(rs, cs)] = .52 + .04 * tache[np.ix_(rs, cs)]; metal[np.ix_(rs, cs)] = .35

    # --- Le nuancier : une teinte unie, un grain léger.
    for nom in TEINTES:
        u0, v0, u1, v1 = case(nom); cs = slice(int(u0 * N), int(u1 * N)); rs = slice(int(v0 * N), int(v1 * N))
        couleur[rs, cs] = np.array(COULEURS[nom], np.float32) * (1 + .04 * tache[rs, cs] + .015 * grain[rs, cs])[..., None]
        rg, mt = RUGO_METAL[nom]; rugo[rs, cs] = rg + .04 * tache[rs, cs]; metal[rs, cs] = mt

    # --- L'usure : marbrure à trois échelles, stries le long de d, crasse au bord des joints là où le bruit de saleté le
    # veut, éclats jusqu'au métal au ras des joints, rayures claires.
    from PIL import Image, ImageDraw, ImageFilter
    marbre = bruit_valeur(rng, N, 256, 256); stries = bruit_valeur(rng, N, 480, 5, 2); salete = bruit_valeur(rng, N, 64, 64)
    im = Image.new('L', (N, N), 0); dr = ImageDraw.Draw(im)
    for _ in range(2500):
        x0, y0 = rng.uniform(0, N, 2); a = rng.uniform(0, np.pi); L = rng.uniform(6, 50)
        dr.line([(x0, y0), (x0 + L * np.cos(a), y0 + L * np.sin(a))], fill=int(rng.uniform(70, 200)), width=1)
    rayures = np.asarray(im, np.float32) / 255
    crasse = jointure * np.clip(.4 + .6 * salete, 0, 1)
    mod = (1 + .18 * marbre) * (1 + .05 * stries) * (1 - .45 * crasse)
    couleur = np.where(peint[..., None], couleur * mod[..., None], couleur)
    eclats = peint & (jointure > .55) & (salete > .5)
    couleur[eclats] = couleur[eclats] * .35 + .65 * np.array((.42, .42, .42), np.float32); rugo[eclats] = .32; metal[eclats] = .8
    ray = peint & (rayures > .1)
    couleur[ray] += (.07 * rayures[ray])[:, None]; rugo[ray] = np.minimum(rugo[ray], .66 - .25 * rayures[ray])
    rugo = np.where(peint, rugo + .06 * crasse + .03 * marbre, rugo)
    # La salissure du concept : crasse brune au bord des joints, voile de poussière par grandes plaques.
    voile = np.clip(salete, 0, 1) * peint
    couleur = couleur * (1 - .22 * crasse - .10 * voile)[..., None] + np.array(SALE, np.float32) * (.22 * crasse + .06 * voile)[..., None]
    # Les têtes de rivet, seules bosses de la peau : sombres, rouillées, une auréole de rouille autour.
    tete = np.where(peint, np.clip(haut / .0006, 0, 1), 0).astype(np.float32)
    aureole = np.asarray(Image.fromarray((tete * 255).astype(np.uint8), mode='L').filter(ImageFilter.GaussianBlur(4)), np.float32) / 255 * peint
    couleur = couleur * (1 - .6 * tete)[..., None] + np.array(ROUILLE, np.float32) * (.5 * tete)[..., None]
    couleur = couleur * (1 - .25 * aureole)[..., None] + np.array(ROUILLE, np.float32) * (.18 * aureole)[..., None]

    # --- Normale en espace tangent : +x vers +u (vers la poupe), +y vers +v (s croissant), convention OpenGL.
    px = 1 / (ECH * N)
    gu = (np.roll(haut, -1, 1) - np.roll(haut, 1, 1)) / (2 * px); gv = (np.roll(haut, -1, 0) - np.roll(haut, 1, 0)) / (2 * px)
    n = np.stack((-gu, -gv, np.ones_like(haut)), -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    from PIL import Image   # Blender lit la disposition de l'atlas sans Pillow
    def ecrire(nom, arr, srgb, taille):
        a = np.clip(arr, 0, 1)
        if srgb: a = np.where(a <= .0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - .055)
        im = Image.fromarray((np.flipud(a) * 255 + .5).astype(np.uint8))
        if taille != N: im = im.resize((taille, taille), Image.LANCZOS)
        im.save(os.path.join(ROOT, nom)); print('écrit', nom, taille)
    ecrire('chasseur_couleur.png', couleur, True, N)
    ecrire('chasseur_normale.png', n * .5 + .5, False, N)
    ecrire('chasseur_occlusion.png', np.repeat(occ[..., None], 3, -1), False, 2048)
    ecrire('chasseur_metal_rugosite.png', np.stack((np.ones_like(rugo), rugo, metal), -1), False, 2048)

if __name__ == '__main__':
    generer()
