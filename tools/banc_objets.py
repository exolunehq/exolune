# Objects bench (docs/spec-objets-proximite.md): the objects near the camera, stones and grass tufts.
#
# python tools/banc_objets.py <exe> <out folder> [recensement] [ecart] [pop] [photos] [--avant <exe>]
#
# - recensement: the placement's rules, measured without the camera's say. On 23 sites, the quality bench's sites of rock,
#   scree, bare soil and sand (seed 1) and ours, the engine records every cell of every slice's window around the
#   camera, kept or not (MYPLANETENGINE_OBJECT_CENSUS, <capture>.recensement): its ground (m^2), its slope, the slope
#   over OBJECT_LANDFORM m uphill and the curvature there, the patches' field, the shares of scree, sand, bare soil and
#   grass, the object's class and width. Per ground against the reference photos' counts, per band of slope, per form of
#   the ground (hollow, flat, crest, slope foot): objects per m^2, the share of the ground they cover, the share of the
#   large; and the patchiness, in cells of 20 m. With --avant, the same for another build of the same census records,
#   its cells given the curvature this one measures.
# - ecart: along an approach, from 200 m to 1.5 m above the ground, the gap between the objects' feet, on the exact
#   ground, and the ground the mesh draws, measured by the engine for every object placed (its title, written next to
#   each capture): mean, largest drop under a foot against its burial depth, largest rise over it against its visible
#   height, largest gap on screen in pixels.
# - pop: a descent from 40 m to 3 m in steps of 1.5 %. The engine lists each capture's objects, named by their seed,
#   with their width on screen (<capture>.objets, MYPLANETENGINE_OBJECT_LIST). An object that shows up between two steps, away from the screen's
#   edges, pops by its width at that step; one already there grows by its change of width. The largest of each, with the
#   objects growing out of the ground and with them showing up whole at their size (MYPLANETENGINE_OBJECT_POP, the
#   reference); and a strip of the colour view at six steps.
# - photos: the views at human height, looking ahead, beside the reference photos (docs/images/cible-sol-*.jpg), each under
#   a sun high over it: comparaison.png.
import os, re, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# The reference photos, and the views set beside them, those of tools/tests/2026-10-24-objets.txt: label, height above the
# ground (m), latitude, longitude, pitch down, heading, the sun's latitude and longitude.
PHOTOS = [("cible-sol-sable-cailloux.jpg", "Photo : sable et cailloux"), ("cible-sol-herbe-rochers.jpg", "Photo : herbe et rochers")]
VIEWS = [("Sable caillouteux", 1.7, 14.76352, 41.20766, 8.0, 0.0, "44.76 61.21"),
         ("Sable sans débris, près de la côte", 1.7, -31.44682, 140.61862, 8.0, 117.0, "-1.45 160.62"),
         ("Herbe et rochers", 1.7, -10.10836, 77.64546, 8.0, 30.0, "19.89 97.65"),
         ("Prairie sèche sans débris", 1.7, 10.17878, 3.59027, 8.0, 120.0, "40.18 23.59"),
         ("Sol nu caillouteux", 1.7, -3.48827, -37.91853, 8.0, 270.0, "26.51 -17.92"),
         ("Pente d'éboulis", 1.7, 10.51553, -44.46514, 8.0, 300.0, "40.52 -24.47")]
SUN = "10 70"
# The approach's and the descent's sites: name: latitude, longitude, heading, the sun's latitude and longitude. Scree and a
# cliff's foot under the sun at "10 70", and the views' sand, grass and bare soil.
SITES = dict(eboulis=(1.08821, 110.6722, 45.0, SUN), falaise=(-0.23076, 118.41645, 61.0, SUN),
             **{name: (VIEWS[i][2], VIEWS[i][3], VIEWS[i][5], VIEWS[i][6]) for name, i in (("sable", 0), ("herbe", 2), ("solnu", 4))})
HEIGHTS = [200.0, 100.0, 50.0, 25.0, 12.0, 6.0, 3.0, 1.5]
TITLE = re.compile(r"objets (\d+) pierres, (\d+) touffes sur (\d+) candidats \| .cart au sol : moyen ([\d.]+) mm, sous un pied ([\d.]+) mm \((\d+) % de "
                   r"l'enfouissement, (\d+) flottent\), dessus ([\d.]+) mm \((\d+) % du visible\), ([\d.]+) px au plus")


def run(exe, jobs, path, extra=None):
    # One engine run for every job, "out.bmp view height latitude longitude pitch heading"; returns each job's title.
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=SUN, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")
    env.update(extra or {})
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE", "MYPLANETENGINE_OBJECT_POP",
              "MYPLANETENGINE_OBJECT_LIST", "MYPLANETENGINE_OBJECT_CENSUS"):
        if not extra or k not in extra:
            env.pop(k, None)
    subprocess.run([exe], env=env, timeout=1800)
    titles = []
    for j in jobs:
        t = j[0] + ".txt"
        titles.append(open(t, encoding="utf-8").read() if os.path.exists(t) else "")
        if os.path.exists(t):
            os.remove(t)
    return titles


# The census's sites: the quality bench's of rock, scree, bare soil and sand (tools/banc_qualite.py, 30 sites, seed 1), and ours.
CENSUS_SITES = [(-5.05673, -166.69451, 180.0), (-37.40219, 14.81078, 45.0), (-45.37183, -146.30873, 135.0), (21.50447, -121.053, 315.0),
                (-45.39741, -84.94977, 315.0), (1.08821, 110.6722, 45.0), (1.35478, -137.48212, 225.0), (17.9226, -115.98272, 90.0),
                (-14.85009, 133.15226, 90.0), (4.72962, -146.52288, 45.0), (44.85101, -146.84797, 0.0), (50.44742, -161.21655, 0.0),
                (-47.0318, 94.59578, 0.0), (-12.97123, 20.15317, 0.0), (27.69221, 20.35421, 0.0), (-23.14019, 4.84842, 315.0),
                (-25.8645, 27.25386, 315.0), (-30.90186, 100.28893, 315.0), (-9.09995, 44.31376, 315.0), (-21.50138, -151.2207, 315.0),
                (-14.9635, 119.991, 0.0), (-0.23076, 118.41645, 61.0), (6.00171, 112.4155, 49.0)]
STONE_OCTAVES = list(range(-5, 1))  # OBJECT_OCTAVES
TUFT_OCTAVES = [-3, -2]  # TUFT_OCTAVES
SLOPES = [0, 10, 20, 30, 35, 40, 50, 90]  # degrees
FORMS = [("creux", 0.008, 1.0), ("plat", -0.008, 0.008), ("bombé", -1.0, -0.008)]  # Laplacian of the height over 16 m, 1/m
CELL = 20.0  # m, the patchiness's cells
# The reference photos (docs/images/cible-sol-*.jpg), counted in a foreground patch of known size (docs/spec-objets-proximite.md):
# sand, pebbles per m^2 by octave of width, the 1.5 cm octave under-counted; grass, tufts per m^2 and rocks of 20 cm to
# 1 m per m^2 in a rocky patch.
PHOTO_PEBBLES = {-5: "16", -4: "6", -3: "0,5", -2: "0", -1: "0", 0: "0"}
# Where the stoniness field is read over many places, its regions being of 0.5 to 32 km: 120 points drawn over the
# planet, the land among them.
PRESENCE_SITES = [(float(np.degrees(np.arcsin(z))), float(lon), 0.0) for z, lon in
                  zip(np.random.default_rng(7).uniform(-0.9, 0.9, 120), np.random.default_rng(8).uniform(-180, 180, 120))]
PHOTO_TUFTS = "6 à 15 ; 30 à 60 %"
PHOTO_GRASS_ROCKS = "2"


def census_records(exe, out, sites=None, land=True, step=1):
    # Every cell of every slice's window around each site, its record as ObjectPlacement.hlsl writes it in the census;
    # one in `step`.
    sites = sites or CENSUS_SITES
    jobs = [(os.path.join(out, f"recensement_{i}.bmp"), "objects", 2.0, lat, lon, 35.0, h) for i, (lat, lon, h) in enumerate(sites)]
    run(exe, jobs, os.path.join(out, "jobs.txt"), {"MYPLANETENGINE_OBJECT_CENSUS": "1"})
    parts = []
    for i, job in enumerate(jobs):
        path = job[0] + ".recensement"
        if os.path.exists(path):
            r = np.fromfile(path, np.float32).reshape(-1, 16)[::step]
            parts.append(np.hstack([r, np.full((len(r), 1), i, np.float32)]))
            os.remove(path)
        if os.path.exists(job[0]):
            os.remove(job[0])
    r = np.vstack(parts)
    if land:
        r = r[r[:, 11] > 0.0]
    packed = np.ascontiguousarray(r[:, 15]).view(np.uint32)
    lat, lon = np.degrees(np.arcsin(np.clip(r[:, 9], -1, 1))), np.degrees(np.arctan2(r[:, 10], r[:, 8]))
    s = np.round(r[:, 7]).astype(int)
    stone = s < len(STONE_OCTAVES)
    octave = np.where(stone, STONE_OCTAVES[0] + s, TUFT_OCTAVES[0] + s - len(STONE_OCTAVES))
    return {"slope": np.degrees(np.arctan(r[:, 0])), "uphill": np.degrees(np.arctan(np.maximum(r[:, 1], 0.0))), "area": r[:, 2],
            "width": r[:, 3], "scree": r[:, 4], "sand": r[:, 5], "soil": r[:, 6], "bare": r[:, 5] + r[:, 6], "grass": r[:, 12],
            "kept": r[:, 13] > 0.0, "stone": stone, "octave": octave, "curvature": r[:, 14],
            "patches": (packed & 0xFFFF).astype(np.uint16).view(np.float16).astype(np.float32),
            "presence": (packed >> 16).astype(np.uint16).view(np.float16).astype(np.float32),
            "elevation": r[:, 11], "site": r[:, 16].astype(int), "latitude": lat, "longitude": lon,
            "key": [(t, o, int(round(a * 1e7)), int(round(b * 1e7))) for t, o, a, b in zip(stone, octave, lat, lon)]}


def borrow(before, after):
    # The cells are the same in both censuses, the lattice's: the before's take the after's curvature, the form being
    # measured by the after's engine only; cells found in one census only are left out.
    index = {k: i for i, k in enumerate(after["key"])}
    pairs = [(i, index[k]) for i, k in enumerate(before["key"]) if k in index]
    mine, theirs = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    c = {k: v[mine] for k, v in before.items() if k != "key"}
    c["curvature"] = after["curvature"][theirs]
    return c


def densities(c, mask, stone=True):
    # Per octave of the class, over the ground the mask selects: objects per m^2, the share they cover (a footprint of
    # 0.68 width^2), the ground.
    rows = {}
    for o in STONE_OCTAVES if stone else TUFT_OCTAVES:
        sel = mask & (c["stone"] == stone) & (c["octave"] == o)
        ground = c["area"][sel].sum()
        kept = sel & c["kept"]
        rows[o] = (kept.sum() / max(ground, 1e-9), (0.68 * c["width"][kept] ** 2).sum() / max(ground, 1e-9), ground)
    return rows


def summary(c, mask, stone=True):
    # Over the ground the mask selects, all octaves of the class summed: objects per m^2, cover, and the cover's share of
    # 50 cm and more.
    d = densities(c, mask, stone)
    cover = sum(v[1] for v in d.values())
    return sum(v[0] for v in d.values()), cover, sum(d[o][1] for o in (-1, 0) if o in d) / max(cover, 1e-9)


def patchiness(c, mask, octaves=(-2, -1, 0), radius=56.0):
    # Per site, within `radius` m of it, where every octave of 25 cm and more is counted: the stones of those octaves in
    # cells of CELL m. The share of the cells that hold half of them (half of the cells for a uniform cover, a few for
    # patches); and the index of dispersion, the counts' variance over their mean (1 for stones thrown at random).
    shares, dispersions = [], []
    for s in range(len(CENSUS_SITES)):
        lat0, lon0 = CENSUS_SITES[s][0], CENSUS_SITES[s][1]
        sel = mask & c["stone"] & (c["site"] == s) & np.isin(c["octave"], octaves)
        x = (c["longitude"][sel] - lon0) * 111320.0 * np.cos(np.radians(lat0))
        y = (c["latitude"][sel] - lat0) * 111320.0
        inside = np.hypot(x, y) < radius
        if inside.sum() == 0:
            continue
        cells = np.floor(x[inside] / CELL).astype(int) * 1000 + np.floor(y[inside] / CELL).astype(int)
        kept = c["kept"][sel][inside]
        keys = np.unique(cells)
        stones = np.array([kept[cells == k].sum() for k in keys])
        if stones.sum() < 20 or len(keys) < 8:
            continue
        ordered = np.sort(stones)[::-1]
        shares.append(np.searchsorted(np.cumsum(ordered), 0.5 * stones.sum()) / len(keys) + 1.0 / len(keys))
        dispersions.append(stones.var() / max(stones.mean(), 1e-9))
    if not shares:
        return float("nan"), float("nan"), 0
    return float(np.median(shares)), float(np.median(dispersions)), len(shares)


GROUNDS = [("sable et sol nu", "bare"), ("herbe", "grass"), ("éboulis", "scree")]


def census_tables(after, before=None):
    # The report: each measure after, and before when given.
    both = [("après", after)] + ([("avant", before)] if before is not None else [])
    names = " | ".join(name for name, _ in both)
    lines = ["**Par sol, là où il est caillouteux, au regard des photos :** pierres par m² ; part du sol couverte, sur le sol dont "
             "la part dépasse 0,5 et où le champ de pierrosité dépasse 0,5. La photo compte une tache de premier plan : la "
             "moyenne du moteur varie de 0,4 à 1,6 fois d'un amas à l'autre, les rochers de l'herbe de 0 à 3,8 fois d'une "
             "tache à l'autre.", "",
             "| largeur | " + " | ".join(f"{g} ({names})" for g, _ in GROUNDS) + " | photo, sable |",
             "|---|" + "---|" * (len(GROUNDS) + 1)]
    tables = {key: [densities(c, (c[key] > 0.5) & (c["presence"] > 0.5)) for _, c in both] for _, key in GROUNDS}
    for o in STONE_OCTAVES:
        cells = [" / ".join(f"{d[o][0]:.3g} ; {100 * d[o][1]:.2f} %" for d in tables[key]) for _, key in GROUNDS]
        lines.append(f"| {100 * 2.0 ** o:.3g} à {200 * 2.0 ** o:.3g} cm | " + " | ".join(cells) + f" | {PHOTO_PEBBLES[o]} |")
    rocks = []
    for _, c in both:
        sel = (c["grass"] > 0.5) & (c["patches"] > 0.0) & (c["presence"] > 0.5)
        d = densities(c, sel)
        rocks.append(f"{d[-2][0] + d[-1][0] + 0.415 * d[-3][0]:.2f}")
    lines += ["", f"**Rochers de l'herbe, 20 cm à 1 m, dans les taches :** {' / '.join(rocks)} par m² ({names}) ; photo {PHOTO_GRASS_ROCKS}.", "",
              f"**Touffes :** par m² ; part couverte ({names})", "", "| sol | touffes | photo, herbe |", "|---|---|---|"]
    for g, key in GROUNDS[:2]:
        cells = []
        for _, c in both:
            n, cover, _ = summary(c, c[key] > 0.5, stone=False)
            cells.append(f"{n:.2f} ; {100 * cover:.0f} %")
        lines.append(f"| {g} | {' / '.join(cells)} | {PHOTO_TUFTS if key == 'grass' else ''} |")
    lines += ["", f"**Pierres par pente :** par m² ; part couverte ; part des 50 cm et plus ({names})", "",
              "| pente | sol | " + names + " |", "|---|---|" + "---|" * len(both)]
    for lo, hi in zip(SLOPES, SLOPES[1:]):
        cells = []
        for _, c in both:
            n, cover, large = summary(c, (c["slope"] >= lo) & (c["slope"] < hi))
            cells.append(f"{n:.3f} ; {100 * cover:.2f} % ; {100 * large:.0f} %")
        share = ((after["slope"] >= lo) & (after["slope"] < hi) & after["stone"]).sum() / max(after["stone"].sum(), 1)
        lines.append(f"| {lo} à {hi}° | {100 * share:.0f} % | " + " | ".join(cells) + " |")
    lines += ["", f"**Pierres par forme du sol,** laplacien de la hauteur sur 16 m ; le pied des pentes, sol de moins de 20° sous plus de 40° :"
              f" par m² ; part couverte ; part des 50 cm et plus ({names})", "",
              "| forme | sol | " + names + " |", "|---|---|" + "---|" * len(both)]
    forms = [(name, lambda c, lo=lo, hi=hi: (c["curvature"] > lo) & (c["curvature"] <= hi)) for name, lo, hi in FORMS]
    forms.append(("pied de pente", lambda c: (c["slope"] < 20.0) & (c["uphill"] > 40.0)))
    for name, mask in forms:
        cells = []
        for _, c in both:
            n, cover, large = summary(c, mask(c))
            cells.append(f"{n:.3f} ; {100 * cover:.2f} % ; {100 * large:.0f} %")
        share = (mask(after) & after["stone"]).sum() / max(after["stone"].sum(), 1)
        lines.append(f"| {name} | {100 * share:.1f} % | " + " | ".join(cells) + " |")
    lines += ["", f"**Les taches,** pierres de 25 cm et plus, cellules de {CELL:.0f} m, à moins de 56 m de chaque lieu : la part des"
              " cellules qui tient la moitié des pierres (50 % si la couverture est uniforme) ; l'indice de dispersion, variance"
              " sur moyenne des comptes (1 pour un semis au hasard) ; médianes sur les lieux qui ont au moins 20 pierres", "",
              "| sol | " + names + " |", "|---|" + "---|" * len(both)]
    for title, mask in (("tout le sol", lambda c: np.ones_like(c["kept"])), ("sol doux, moins de 10°", lambda c: c["slope"] < 10.0)):
        cells = []
        for _, c in both:
            share, dispersion, sites = patchiness(c, mask(c))
            cells.append(f"{100 * share:.0f} % ; {dispersion:.1f} ; {sites} lieux")
        lines.append(f"| {title} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def presence(c):
    # Per ground, the share of the ground where no debris lies at all, the stoniness field nil; over the stones' cells.
    rows = []
    for g, mask in [("tout le sol", np.ones_like(c["kept"]))] + [(g, c[key] > 0.5) for g, key in GROUNDS]:
        sel = mask & c["stone"]
        ground = c["area"][sel]
        rows.append(f"| {g} | {100 * ground[c['presence'][sel] <= 0.0].sum() / max(ground.sum(), 1e-9):.0f} % | "
                    f"{len(np.unique(c['site'][sel]))} |")
    return rows


def recensement(exe, out, before_exe=None):
    wide = census_records(exe, out, PRESENCE_SITES, step=8)
    lines = ["**Où il n'y a aucun débris,** le champ de pierrosité nul, part du sol, sur les terres de 120 points tirés sur la planète :",
             "", "| sol | sans débris | lieux |", "|---|---|---|"] + presence(wide) + [""]
    print("\n".join(lines), flush=True)
    after = census_records(exe, out)
    before = borrow(census_records(before_exe, out), after) if before_exe else None
    after = {k: v for k, v in after.items() if k != "key"}
    stones = after["stone"]
    text = "\n".join(lines) + "\n" + census_tables(after, before) + (f"\n\nLe champ des taches : moyenne {after['patches'][stones].mean():.2f} (1 voulu), "
                                           f"nul sur {100 * (after['patches'][stones] <= 0).mean():.0f} % du sol.")
    print(text, flush=True)
    return text


def ecart(exe, out):
    rows = ["| lieu | hauteur | objets | écart moyen | sous un pied, max | part de l'enfouissement | flottent | dessus, max | part du visible | à l'écran, max |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for name, (lat, lon, heading, sun) in SITES.items():
        jobs = [(os.path.join(out, f"ecart_{name}_{h:g}.bmp"), "-", h, lat, lon, 35.0, heading) for h in HEIGHTS]
        for job, title in zip(jobs, run(exe, jobs, os.path.join(out, "jobs.txt"), {"MYPLANETENGINE_SUN": sun})):
            m = TITLE.search(title)
            if os.path.exists(job[0]):
                os.remove(job[0])
            if not m:
                rows.append(f"| {name} | {job[2]:g} m | ? | | | | | | | |")
                continue
            n, _, _, mean, below, burial, floating, above, visible, px = m.groups()
            rows.append(f"| {name} | {job[2]:g} m | {n} | {float(mean):.1f} mm | {float(below):.0f} mm | {burial} % | {floating} | "
                        f"{float(above):.0f} mm | {visible} % | {float(px):.2f} px |")
        print(rows[-1], flush=True)
    return "\n".join(rows)


def objects(path):
    # The objects of a capture: seed -> (width on screen in px, x, y on screen from -1 to 1).
    if not os.path.exists(path):
        return {}
    rows = np.fromfile(path, np.float32).reshape(-1, 4)
    os.remove(path)
    return {int(s): (w, x, y) for s, (_, w, x, y) in zip(rows[:, 0].view(np.uint32), rows)}


def pops(frames, edge=0.95):
    # Over the descent: the objects that show up away from the screen's edges, their widths as they do, and the largest
    # growth of one already there, from one step to the next (px).
    shown, growth = [], [0.0]
    for before, now in zip(frames, frames[1:]):
        for seed, (w, x, y) in now.items():
            if seed in before:
                growth.append(w - before[seed][0])
            elif abs(x) < edge and abs(y) < edge:
                shown.append(w)
    return np.array(shown or [0.0]), max(growth)


def pop(exe, out):
    steps = int(np.log(40.0 / 3.0) / np.log(1.015)) + 1
    heights = [40.0 / 1.015 ** i for i in range(steps)]
    rows = ["| lieu | étapes | apparitions | largeur à l'apparition, médiane / max | plus forte croissance d'une étape | référence, apparition entière : médiane / max |",
            "|---|---|---|---|---|---|"]
    strips = []
    for name, (lat, lon, heading, sun) in SITES.items():
        result = {}
        for mode, extra in (("croissance", {"MYPLANETENGINE_OBJECT_LIST": "1", "MYPLANETENGINE_SUN": sun}),
                            ("entiere", {"MYPLANETENGINE_OBJECT_LIST": "1", "MYPLANETENGINE_OBJECT_POP": "1", "MYPLANETENGINE_SUN": sun})):
            jobs = [(os.path.join(out, f"pop_{name}_{mode}_{i:03d}.bmp"), "objects", h, lat, lon, 35.0, heading)
                    for i, h in enumerate(heights)]
            run(exe, jobs, os.path.join(out, "jobs.txt"), extra)
            frames = []
            for job in jobs:
                frames.append(objects(job[0] + ".objets"))
                if os.path.exists(job[0]):
                    os.remove(job[0])
            result[mode] = pops(frames)
        (shown, growth), (whole, _) = result["croissance"], result["entiere"]
        rows.append(f"| {name} | {steps} | {len(shown)} | {np.median(shown):.2f} / {shown.max():.2f} px | {growth:.2f} px | "
                    f"{np.median(whole):.2f} / {whole.max():.2f} px |")
        print(rows[-1], flush=True)
        # The colour view at six steps of the descent, side by side.
        picks = [int(round(k * (steps - 1) / 5)) for k in range(6)]
        jobs = [(os.path.join(out, f"strip_{name}_{i:03d}.bmp"), "-", heights[i], lat, lon, 35.0, heading) for i in picks]
        run(exe, jobs, os.path.join(out, "jobs.txt"), {"MYPLANETENGINE_SUN": sun})
        tiles = []
        for job in jobs:
            img = cv2.imread(job[0])
            tiles.append(cv2.resize(img, (426, 240)) if img is not None else np.zeros((240, 426, 3), np.uint8))
            cv2.putText(tiles[-1], f"{name} {job[2]:.1f} m", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            if os.path.exists(job[0]):
                os.remove(job[0])
        strips.append(np.hstack(tiles))
    cv2.imwrite(os.path.join(out, "descente.png"), np.vstack(strips))
    return "\n".join(rows)


TILE = (640, 360)


def tile(img, label):
    # A tile of the sheet: the image fitted in TILE on black, its label.
    img.thumbnail(TILE)
    t = Image.new("RGB", TILE)
    t.paste(img, ((TILE[0] - img.width) // 2, (TILE[1] - img.height) // 2))
    draw = ImageDraw.Draw(t)
    font = ImageFont.truetype("arial.ttf", 18)
    draw.rectangle((0, 0, draw.textlength(label, font=font) + 12, 26), fill=(0, 0, 0))
    draw.text((6, 3), label, font=font, fill=(255, 255, 255))
    return t


def photos(exe, out):
    # Each view under its own sun; the sheet: the sand photo beside stony sand and sand without debris, the grass photo
    # beside grass with rocks and a meadow without debris; then the bare soil and the scree.
    shots = []
    for i, (label, h, lat, lon, pitch, heading, sun) in enumerate(VIEWS):
        job = (os.path.join(out, f"vue_{i}.bmp"), "-", h, lat, lon, pitch, heading)
        title = run(exe, [job], os.path.join(out, "jobs.txt"), {"MYPLANETENGINE_SUN": sun})[0]
        m = TITLE.search(title)
        counts = f" : {m.group(1)} pierres, {m.group(2)} touffes" if m else ""
        shots.append(tile(Image.open(job[0]).convert("RGB"), label + counts))
        os.remove(job[0])
    images = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "images")
    refs = [tile(Image.open(os.path.join(images, name)).convert("RGB"), label) for name, label in PHOTOS]
    sheet = Image.new("RGB", (3 * TILE[0], 3 * TILE[1]))
    for k, t in enumerate([refs[0], shots[0], shots[1], refs[1], shots[2], shots[3], shots[4], shots[5]]):
        sheet.paste(t, ((k % 3) * TILE[0], (k // 3) * TILE[1]))
    path = os.path.join(out, "comparaison.png")
    sheet.save(path)
    return f"![Comparaison]({path})"


if __name__ == "__main__":
    exe, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    before = sys.argv[sys.argv.index("--avant") + 1] if "--avant" in sys.argv else None
    modes = [m for m in sys.argv[3:] if m in ("recensement", "ecart", "pop", "photos")] or ["recensement", "ecart", "pop", "photos"]
    os.makedirs(out, exist_ok=True)
    report = []
    if "recensement" in modes:
        report += ["## Recensement : tailles, pentes, formes et taches", "", recensement(exe, out, before and os.path.abspath(before)), ""]
    if "ecart" in modes:
        report += ["## Écart entre le pied des objets et le sol du maillage", "", ecart(exe, out), ""]
    if "pop" in modes:
        report += ["## Apparition le long d'une descente", "", pop(exe, out), ""]
    if "photos" in modes:
        report += ["## À hauteur d'homme, à côté des photos", "", photos(exe, out), ""]
    open(os.path.join(out, "rapport.md"), "w", encoding="utf-8").write("\n".join(report))
    print(os.path.join(out, "rapport.md"))
