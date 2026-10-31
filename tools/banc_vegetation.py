# Vegetation bench (docs/recherche-vegetation.md): trees and shrubs from the climate, the objects near the camera and the
# ground's canopy beyond them.
#
# python tools/banc_vegetation.py <exe> <out folder> <command> [args]
#   vues "<lat lon height pitch heading>; ..." [sun]: colour and forest views of a few places, side by side.
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SUN = "10 70"


def run(exe, jobs, path, sun=SUN, extra=None):
    # One engine run for every job, "out.bmp view height latitude longitude pitch heading"; returns each job's title.
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=sun, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE", "MYPLANETENGINE_OBJECT_POP",
              "MYPLANETENGINE_OBJECT_LIST", "MYPLANETENGINE_OBJECT_CENSUS"):
        env.pop(k, None)
    env.update(extra or {})
    subprocess.run([exe], env=env, timeout=3600, cwd=os.path.dirname(exe))
    titles = []
    for j in jobs:
        t = j[0] + ".txt"
        titles.append(open(t, encoding="utf-8").read() if os.path.exists(t) else "")
        if os.path.exists(t):
            os.remove(t)
    return titles


def sheet(rows, out, w=640, h=360):
    # rows: [[(image path, label), ...], ...]
    width = max(len(r) for r in rows)
    img = Image.new("RGB", (w * width, h * len(rows)), "black")
    d, font = ImageDraw.Draw(img), ImageFont.truetype("arial.ttf", 15)
    for j, row in enumerate(rows):
        for i, (path, label) in enumerate(row):
            if os.path.exists(path):
                img.paste(Image.open(path).convert("RGB").resize((w, h)), (i * w, j * h))
            d.text((i * w + 6, j * h + 4), label, fill="white", font=font)
    img.save(out)


def vues(exe, out, places, sun=SUN, views=("none", "forest")):
    jobs, rows = [], []
    for i, p in enumerate(places):
        lat, lon, height, pitch, heading = (float(x) for x in p.split())
        row = []
        for v in views:
            path = os.path.join(out, f"vue_{i}_{v}.bmp")
            jobs.append((path, v, height, lat, lon, pitch, heading))
            row.append((path, f"{v} {p}"))
        rows.append(row)
    titles = run(exe, jobs, os.path.join(out, "jobs.txt"), sun)
    for (path, *_), t in zip(jobs, titles):
        position = t.split("| position ")[-1].split(" |")[0] if "position" in t else ""
        print(os.path.basename(path), "|", t.split("| objets")[0].split("GPU")[-1][:60], "|", t.split("| plantes")[-1] if "plantes" in t else "",
              "| position", position)
    sheet(rows, os.path.join(out, "vues.png"))


# The biome view (MYPLANETENGINE_VIEW=biome): class k as the linear grey k / 8, written in sRGB; 0 the sea.
BIOMES = ["mer", "toundra et alpin", "boréal", "tempéré humide", "tempéré sec", "tropical humide", "savane et tropical sec", "désert"]
LEVELS = np.array([0.0] + [255.0 * (1.055 * (k / 8.0) ** (1 / 2.4) - 0.055) for k in range(1, 8)])


def classes(path):
    grey = np.asarray(Image.open(path).convert("L"), np.float32)
    return np.abs(grey[..., None] - LEVELS[None, None, :]).argmin(axis=2)


def white(path):
    return np.asarray(Image.open(path).convert("L"), np.float32) > 127.0


def exact(path):
    # The views written as they are, not dithered (biome, temperature, humidity, season, altitude): the linear value of
    # each pixel's sRGB grey.
    c = np.asarray(Image.open(path).convert("L"), np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def releve(exe, out, height=20000.0):
    # A grid of places, straight down from `height`: the canopy's share and the main biome of each, to find the test views.
    jobs, places = [], []
    for lat in range(-60, 61, 10):
        for lon in range(-180, 180, 30):
            for v in ("forest", "biome"):
                jobs.append((os.path.join(out, f"releve_{lat}_{lon}_{v}.bmp"), v, height, lat + 0.37, lon + 0.53, 89.9, 0.0))
            places.append((lat + 0.37, lon + 0.53))
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    rows = []
    for lat, lon in places:
        f, b = (os.path.join(out, f"releve_{round(lat - 0.37)}_{round(lon - 0.53)}_{v}.bmp") for v in ("forest", "biome"))
        if not (os.path.exists(f) and os.path.exists(b)):
            continue
        c, w = classes(b), white(f)
        land = c > 0
        main = np.bincount(c[land], minlength=8).argmax() if land.any() else 0
        rows.append((lat, lon, land.mean(), w[land].mean() if land.any() else 0.0, main))
        os.remove(f), os.remove(b)
    print("| latitude | longitude | terre | canopée | biome |")
    print("|---|---|---|---|---|")
    for lat, lon, land, cover, main in rows:
        if land > 0.3:
            print(f"| {lat:.2f} | {lon:.2f} | {100 * land:.0f} % | {100 * cover:.0f} % | {BIOMES[main]} |")


def biomes(exe, out, height=4000e3):
    # The cover by biome, over the planet seen from orbit, straight down on eight sides: the share of the forest view's
    # white pixels (trees and shrubs) and of the trees view's among each class's.
    sides = [(0.0, 0.0), (0.0, 90.0), (0.0, 180.0), (0.0, -90.0), (60.0, 45.0), (-60.0, -135.0), (45.0, -120.0), (-45.0, 60.0)]
    views = ("forest", "trees", "biome")
    jobs = [(os.path.join(out, f"biome_{i}_{v}.bmp"), v, height, lat, lon, 89.9, 0.0) for i, (lat, lon) in enumerate(sides) for v in views]
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    count, woody, trees = np.zeros(8), np.zeros(8), np.zeros(8)
    for i in range(len(sides)):
        f, t, b = (os.path.join(out, f"biome_{i}_{v}.bmp") for v in views)
        if not all(os.path.exists(x) for x in (f, t, b)):
            continue
        c, wf, wt = classes(b), white(f), white(t)
        # The disc's middle only: far from its rim, where a pixel spans more than one biome.
        h, wd = c.shape
        yy, xx = np.mgrid[0:h, 0:wd]
        keep = (yy - h / 2) ** 2 + (xx - wd / 2) ** 2 < (0.3 * h) ** 2
        for k in range(1, 8):
            m = keep & (c == k)
            count[k] += m.sum()
            woody[k] += wf[m].sum()
            trees[k] += wt[m].sum()
    print("| biome | part des terres | couvert ligneux | dont arbres |")
    print("|---|---|---|---|")
    for k in range(1, 8):
        n = max(count[k], 1)
        print(f"| {BIOMES[k]} | {100 * count[k] / max(count[1:].sum(), 1):.1f} % | {100 * woody[k] / n:.1f} % | {100 * trees[k] / n:.1f} % |")


# Forests of each kind, and a sun high over each: latitude, longitude, the sun's latitude and longitude (tools/tests/2026-10-25-vegetation.txt).
FORESTS = {"tempérée": (30.37, 120.53, "20 140"), "boréale": (-49.63, 90.53, "-30 100"), "tropicale": (0.37, 60.53, "10 80"),
           "savane": (10.37, -119.47, "15 -100"), "maquis": (-29.63, 60.53, "-20 80")}


def linear(path):
    c = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def raccord(exe, out, places=None):
    # Where the objects take over from the ground's canopy, both must give the same light: the same views with the plants
    # and without (MYPLANETENGINE_NO_PLANTS, the canopy everywhere), the ratio of their mean luminance, linear, over the
    # screen's middle, where the plants are whole.
    places = places or FORESTS
    shots = [("nadir 200 m", 200.0, 89.9), ("200 m à 45°", 200.0, 45.0)]
    rows = []
    for name, (lat, lon, sun) in places.items():
        jobs = [(os.path.join(out, f"raccord_{name}_{i}_{m}.bmp"), "none", h, lat, lon, p, 0.0) for i, (_, h, p) in enumerate(shots) for m in ("avec", "sans")]
        for mode in ("avec", "sans"):
            run(exe, [j for j in jobs if j[0].endswith(f"_{mode}.bmp")], os.path.join(out, "jobs.txt"), sun,
                {"MYPLANETENGINE_NO_PLANTS": "1"} if mode == "sans" else {})
        row = []
        for i, (label, h, p) in enumerate(shots):
            a, b = (os.path.join(out, f"raccord_{name}_{i}_{m}.bmp") for m in ("avec", "sans"))
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            la, lb = linear(a), linear(b)
            hh, ww = la.shape
            crop = (slice(hh // 4, 3 * hh // 4), slice(ww // 4, 3 * ww // 4)) if p > 80 else (slice(hh // 2, hh), slice(ww // 4, 3 * ww // 4))
            ratio = la[crop].mean() / max(lb[crop].mean(), 1e-6)
            print(f"{name} | {label} | lumière avec / sans les plantes : {ratio:.3f}", flush=True)
            row += [(a, f"{name} {label} : avec, x{ratio:.2f}"), (b, f"{name} {label} : sans")]
        rows.append(row)
    sheet(rows, os.path.join(out, "raccord.png"), 480, 270)


def relais(exe, out, places, sun="20 140"):
    # Where the plants take over from the ground's canopy, seen from the side: the same view with the plants and without
    # (MYPLANETENGINE_NO_PLANTS, the canopy everywhere), the ratio of their mean light, linear, by band of distance (the
    # view distance, without the plants). 1 everywhere: the plants change nothing but the detail.
    edges = [200, 400, 700, 1000, 1400, 1800, 2300, 3000, 4000]
    for i, p in enumerate(places):
        jobs = {m: [(os.path.join(out, f"relais_{i}_{m}_{v}.bmp"), v, *[float(x) for x in p.split()][2:3], *[float(x) for x in p.split()][:2],
                     *[float(x) for x in p.split()][3:5]) for v in ("none", "distance")] for m in ("avec", "sans")}
        run(exe, jobs["avec"], os.path.join(out, "jobs.txt"), sun)
        run(exe, jobs["sans"], os.path.join(out, "jobs.txt"), sun, {"MYPLANETENGINE_NO_PLANTS": "1"})
        a, n = linear(jobs["avec"][0][0]), linear(jobs["sans"][0][0])
        d = 4000.0 * exact(jobs["sans"][1][0])
        cells = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (d >= lo) & (d < hi)
            cells.append(f"{a[m].mean() / max(n[m].mean(), 1e-6):.2f}" if m.sum() > 2000 else "-")
        print(f"| {p} | " + " | ".join(cells) + " |", flush=True)
    print("| vue | " + " | ".join(f"{lo} à {hi} m" for lo, hi in zip(edges[:-1], edges[1:])) + " |")


def climat(exe, out, places, height=2000.0):
    # The climate's mean over the screen's middle, straight down: temperature and growing season (-30 to 40 C), humidity,
    # elevation (0 to 6 km), the canopy's and the trees' shares, from the dithered views.
    views = [("temperature", lambda x: 70 * x - 30, "°C"), ("season", lambda x: 70 * x - 30, "°C"), ("humidity", lambda x: x, ""),
             ("altitude", lambda x: 6000 * x, "m"), ("forest", lambda x: 100 * x, "%"), ("trees", lambda x: 100 * x, "%")]
    jobs = [(os.path.join(out, f"climat_{i}_{v}.bmp"), v, height, *(float(x) for x in p.split()), 89.9, 0.0)
            for i, p in enumerate(places) for v, _, _ in views]
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    for i, p in enumerate(places):
        values = []
        for v, f, unit in views:
            path = os.path.join(out, f"climat_{i}_{v}.bmp")
            w = white(path) if v in ("forest", "trees") else exact(path)
            h, wd = w.shape
            values.append(f"{v} {f(w[h // 4:3 * h // 4, wd // 4:3 * wd // 4].mean()):.2f}{unit}")
            os.remove(path)
        print(p, "|", ", ".join(values), flush=True)


def treeline_formula(latitude):
    # The tree line of the climate's formula alone, its noises at 0 (Materials.hlsli, Temperature; Vegetation.hlsli): the
    # altitude where the growing season's mean is 6.4 C, on flat ground.
    s2 = np.sin(np.radians(latitude)) ** 2
    amplitude = 3.5 + 18.0 * s2
    lo, hi = -10000.0, 10000.0
    for _ in range(60):
        z = 0.5 * (lo + hi)
        t = 28.0 - 52.0 * s2 - 5.0 * max(z, 0.0) / 1000.0
        theta = np.arccos(np.clip((0.9 - t) / amplitude, -1.0, 1.0))
        season = t + amplitude * np.sin(theta) / max(theta, 1e-4)
        lo, hi = (z, hi) if season > 6.4 else (lo, z)
    return z


# The tree line on Earth by latitude (Körner 1998, compiled by the Wikipedia's tree line page; Körner and Paulsen 2004):
# altitude in m, with the latitude of the sites when it differs.
EARTH_TREELINE = {0: "3100 à 3900", 15: "4100 (18° S)", 20: "4000 (19° N)", 30: "4200 (28° N)", 40: "3200 à 3600",
                  45: "2200 (47° N)", 50: "1100 à 2200 (47 à 61° N)", 60: "1100 (61° N)", 68: "650", 70: "0 à 500"}


def box(a, r):
    # The mean over a square of 2r + 1 pixels, by cumulative sums, the edges clamped.
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(np.pad(p, ((1, 0), (1, 0))), 0), 1)
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def cretes(exe, out, places, others=(), height=20000.0):
    # Crests and hollows, straight down from `height`: the ground's height over its mean within 16 km (three box blurs of
    # 5.3 km, about the planet map's mip of Vegetation.hlsli's Exposure), the trees' share by band of it, well under the tree
    # line (growing season over 8 C), for each exe: ridges should lose their trees, hollows keep them.
    mpp = height * 2.0 * np.tan(np.radians(30.0)) / 720.0
    r = int(round(2650.0 / mpp))
    bands = [(-1e9, -150.0, "creux, < -150 m"), (-150.0, 150.0, "entre-deux"), (150.0, 300.0, "haut, 150 à 300 m"), (300.0, 1e9, "crête, > 300 m")]
    print("| lieu | build | " + " | ".join(b[2] for b in bands) + " |")
    print("|---|---|" + "---|" * len(bands))
    for e in [exe] + list(others):
        name = os.path.basename(os.path.dirname(e))
        jobs = [(os.path.join(out, f"cretes_{i}_{v}.bmp"), v, height, *(float(x) for x in p.split()[:2]), 89.9, 0.0)
                for i, p in enumerate(places) for v in ("trees", "altitude", "season")]
        run(e, jobs, os.path.join(out, "jobs.txt"))
        for i, p in enumerate(places):
            t = white(os.path.join(out, f"cretes_{i}_trees.bmp")).astype(np.float32)
            a = 6000.0 * exact(os.path.join(out, f"cretes_{i}_altitude.bmp"))
            s = 70.0 * exact(os.path.join(out, f"cretes_{i}_season.bmp")) - 30.0
            tpi = a - box(box(box(a, r), r), r)
            ok = (s > 8.0) & (a > 1.0)
            cells = []
            for lo, hi, _ in bands:
                m = ok & (tpi >= lo) & (tpi < hi)
                cells.append(f"{100 * t[m].mean():.0f} % ({m.mean() * 100:.0f} %)" if m.sum() > 2000 else "-")
            print(f"| {p} | {name} | " + " | ".join(cells) + " |", flush=True)


def lisiere(exe, out, places, height=20000.0):
    # The tree line on mountains, straight down from `height`: the trees' view dithered, the altitude's and the season's
    # values as they are. The trees' share by band of growing season, against its own near the line, 8 to 11 C: where it
    # falls to half, against 6.4 C. The altitude of the pixels whose season is 6.2 to 6.6 C: the line there, against the
    # formula's alone and the Earth's at that latitude.
    views = ("trees", "altitude", "season")
    jobs = [(os.path.join(out, f"lisiere_{i}_{v}.bmp"), v, height, *(float(x) for x in p.split()[:2]), 89.9, 0.0)
            for i, p in enumerate(places) for v in views]
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    print("| lieu | latitude | saison où les arbres tombent à moitié | altitude de la ligne ici | formule seule | Terre |")
    print("|---|---|---|---|---|---|")
    for i, p in enumerate(places):
        t = white(os.path.join(out, f"lisiere_{i}_trees.bmp")).astype(np.float32)
        e, s = (6000.0 * exact(os.path.join(out, f"lisiere_{i}_altitude.bmp")), 70.0 * exact(os.path.join(out, f"lisiere_{i}_season.bmp")) - 30.0)
        lat = float(p.split()[0])
        near = (s >= 8.0) & (s < 11.0)
        ref = t[near].mean() if near.sum() > 500 else float("nan")
        cross = float("nan")
        previous = None
        for a in np.arange(11.0, 2.0, -0.25):
            m = (s >= a) & (s < a + 0.25)
            if m.sum() < 200:
                continue
            share = t[m].mean() / ref
            if previous is not None and share < 0.5 <= previous[1]:
                cross = a + 0.125 + 0.25 * (0.5 - share) / (previous[1] - share)
                break
            previous = (a, share)
        line = e[(s >= 6.2) & (s < 6.6)]
        earth = EARTH_TREELINE.get(min(EARTH_TREELINE, key=lambda k: abs(k - abs(lat))), "")
        print(f"| {p} | {lat:.1f} | {cross:.1f} °C | {np.median(line) if line.size > 200 else float('nan'):.0f} m | "
              f"{treeline_formula(lat):.0f} m | {earth} m |", flush=True)


# The views judged in flight (tools/tests/2026-10-25-vegetation-v3.txt): label, height above the ground (m), latitude,
# longitude, pitch down, heading, the subsolar point. The palettes of the generated plants, v1 and v2, went with them
# (docs/log/recherche-vegetation-historique.md).
TEST_VIEWS = [
    ("Orbite, 3 000 km : forêts, savanes, déserts sans taches sombres", 3.0e6, 0.0, 60.0, 70.0, 0.0, "10 75"),
    ("F3, forêt tempérée à 150 m : les arbres prennent le relais de la canopée, sans pousser", 150.0, 30.37, 120.53, 20.0, 0.0, "20 140"),
    ("F3 après 500 m de vol vers le nord : la même bande, d'autres arbres", 150.0, 30.37449, 120.53, 20.0, 0.0, "20 140"),
    ("Départ en vol, 150 m, forêt tropicale : avancer vers le nord", 150.0, 0.37, 60.53, 15.0, 0.0, "10 80"),
    ("Départ en vol, 400 m, forêt tempérée : avancer vers le nord", 400.0, 30.37, 120.53, 8.0, 0.0, "20 140"),
    ("Départ en vol, 400 m, forêt boréale : avancer vers l'est", 400.0, -49.63, 90.53, 8.0, 90.0, "-30 100"),
    ("Vue lointaine à 400 m : la forêt garde sa hauteur jusqu'à l'horizon", 400.0, 30.37, 120.53, 6.0, 0.0, "20 140"),
    ("Lisière vue de la clairière, 2 m : son manteau d'arbustes", 2.0, 30.37000, 120.53027, 3.0, 0.0, "20 140"),
    ("Dans la forêt tempérée, 2 m : un sous-bois plus clair", 2.0, 30.36948, 120.52781, 5.0, 0.0, "20 140"),
    ("Clairière de la forêt tropicale, 2 m : moins d'arbustes", 2.0, 0.37288, 60.53092, 3.0, 0.0, "10 80"),
    ("Forêt boréale à 150 m : clairières sur la neige", 150.0, -49.63, 90.53, 20.0, 0.0, "-30 100"),
    ("Montagne à 300 m : vallée boisée, crêtes sans arbres", 300.0, -14.90, 119.95, 8.0, 120.0, "-5 125"),
    ("Savane à 100 m : bosquets et terres nues", 100.0, 10.37, -119.47, 15.0, 0.0, "15 -100"),
    ("Maquis à 2 m : arbustes par taches", 2.0, -29.63, 60.53, 5.0, 180.0, "-20 80"),
    ("Désert à 2 m : arbustes épars, gris-vert", 2.0, -19.63208, 0.52597, 5.0, 0.0, "-15 5"),
    ("Ligne des arbres, 2 m : arbustes au-dessus, krummholz, la forêt en contrebas", 2.0, -14.90437, 119.94946, 5.0, 120.0, "-5 125"),
]
TEST_HEADER = ("# Végétation (docs/recherche-vegetation.md, docs/vegetation-planetaire.md) : les arbres ne poussent pas, chacun entier\n"
               "# dès qu'il est dessiné, au-dessus d'une canopée qui a leur hauteur ; pas de forêt sous 1 000 mm.\n"
               "# Les vues « Départ en vol » sont des points de départ : avancer vers le cap indiqué pour voir les arbres prendre le relais.\n")


def tests(exe, out, path):
    # Every test view, captured hidden in batch mode under its own sun; the tests file written with each view's position
    # as the title gives it, altitude over the sea; and the sheet of all views.
    import re
    by_sun = {}
    for i, v in enumerate(TEST_VIEWS):
        by_sun.setdefault(v[6], []).append(i)
    positions = {}
    for sun, ids in by_sun.items():
        jobs = [(os.path.join(out, f"test_{i:02d}.bmp"), "none", TEST_VIEWS[i][1], *TEST_VIEWS[i][2:6]) for i in ids]
        for i, t in zip(ids, run(exe, jobs, os.path.join(out, "jobs.txt"), sun)):
            m = re.search(r"\| position ([-\d. ]+)", t)
            positions[i] = m.group(1).strip() if m else ""
            n = re.search(r"plantes (\d+ \+ \d+) lointaines, (\d+) flottent, de ([\d.]+) px", t)
            g = re.search(r"objets ([\d.]+) \+ ([\d.]+) ms", t)
            print(f"{i:02d} | {TEST_VIEWS[i][0]} | {positions[i]} | plantes {n.group(1) if n else '?'}, flottent {n.group(2) if n else '?'} "
                  f"({n.group(3) if n else '?'} px) | objets {g.group(1) if g else '?'} + {g.group(2) if g else '?'} ms", flush=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(TEST_HEADER + "# libellé | altitude (m) latitude longitude inclinaison cap | latitude longitude du soleil\n")
        for i, v in enumerate(TEST_VIEWS):
            f.write(f"{v[0]} | {positions.get(i, '')} | {v[6]}\n")
    sheet([[(os.path.join(out, f"test_{i:02d}.bmp"), f"{i:02d} {TEST_VIEWS[i][0]}") for i in range(j, min(j + 2, len(TEST_VIEWS)))]
           for j in range(0, len(TEST_VIEWS), 2)], os.path.join(out, "tests.png"))


def orbite(exe, out, base, height=4000e3):
    # The planet's light seen from orbit by biome, against another build: the colour views of `biomes`' eight sides, the
    # mean linear luminance of each class's pixels, the ratio of this build's to the other's.
    sides = [(0.0, 0.0), (0.0, 90.0), (0.0, 180.0), (0.0, -90.0), (60.0, 45.0), (-60.0, -135.0), (45.0, -120.0), (-45.0, 60.0)]
    lum = {}
    for name, e in (("veg", exe), ("base", base)):
        jobs = [(os.path.join(out, f"orbite_{name}_{i}.bmp"), "none", height, lat, lon, 89.9, 0.0) for i, (lat, lon) in enumerate(sides)]
        if name == "veg":
            jobs += [(os.path.join(out, f"orbite_biome_{i}.bmp"), "biome", height, lat, lon, 89.9, 0.0) for i, (lat, lon) in enumerate(sides)]
        run(e, jobs, os.path.join(out, "jobs.txt"), "0 0")
    sums = np.zeros((2, 8)); count = np.zeros(8)
    for i in range(len(sides)):
        b = os.path.join(out, f"orbite_biome_{i}.bmp")
        if not os.path.exists(b):
            continue
        c = classes(b)
        h, wd = c.shape
        yy, xx = np.mgrid[0:h, 0:wd]
        keep = (yy - h / 2) ** 2 + (xx - wd / 2) ** 2 < (0.3 * h) ** 2
        for j, name in enumerate(("veg", "base")):
            l = linear(os.path.join(out, f"orbite_{name}_{i}.bmp"))
            for k in range(1, 8):
                m = keep & (c == k)
                sums[j, k] += l[m].sum()
                if j == 0:
                    count[k] += m.sum()
    print("| biome | lumière vue d'orbite, avec / sans la végétation |")
    print("|---|---|")
    for k in range(1, 8):
        if count[k] > 0:
            print(f"| {BIOMES[k]} | {sums[0, k] / max(sums[1, k], 1e-6):.3f} |")


def bord(exe, out, places, height=1000.0):
    # For each place, straight down from `height`, the trees' view: the open pixel nearest the screen's middle that has
    # forest within 30 to 100 m to the north; its latitude and longitude, to stand in the clearing and look at the edge.
    from PIL import ImageFilter
    jobs = [(os.path.join(out, f"bord_{i}.bmp"), "trees", height, *(float(x) for x in p.split()[:2]), 89.9, 0.0) for i, p in enumerate(places)]
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    mpp = height * 2.0 * np.tan(np.radians(30.0)) / 720.0
    for (path, _, _, lat0, lon0, _, _) in jobs:
        t = np.asarray(Image.open(path).convert("L").filter(ImageFilter.BoxBlur(6)), np.float32) / 255.0
        best = None
        for y in range(120, 680, 4):
            for x in range(120, 1160, 4):
                if t[y, x] < 0.15:
                    for dd in range(int(30 / mpp), int(100 / mpp), 2):
                        if y - dd > 0 and t[y - dd, x] > 0.75:
                            if best is None or abs(y - 360) + abs(x - 640) < abs(best[0] - 360) + abs(best[1] - 640):
                                best = (y, x, dd)
                            break
        if best:
            y, x, dd = best
            lat = lat0 - (y - 360) * mpp / 6378000.0 * 180.0 / np.pi
            lon = lon0 + (x - 640) * mpp / (6378000.0 * np.cos(np.radians(lat0))) * 180.0 / np.pi
            print(f"{lat0} {lon0} | clairière {lat:.5f} {lon:.5f}, lisière à {dd * mpp:.0f} m au nord", flush=True)
        else:
            print(f"{lat0} {lon0} | pas de clairière près du milieu", flush=True)


def mouvement(exe, out, places, others=(), frames=41, step=25.0, band=(450.0, 2200.0)):
    # The camera flies forward over a forest, `frames` captures `step` m apart, each with the colour, the height of the
    # surface seen over the ground (view height, 0 to 64 m) and its distance (view distance, 0 to 4 km), as is. Each pixel
    # of the screen's middle third is a ground point `forward` m ahead of the camera's start; a fixed band of 20 m of it,
    # seen from frame to frame as it comes closer, should keep its seen height and its light while the trees take over
    # from the canopy, `band` m away: a tree never grows. Prints, for each exe, the seen height against the distance, and
    # per band of ground the change from one frame to the next and over the whole crossing.
    exes = [exe] + list(others)
    for number, place in enumerate(places):
        lat0, lon0, height, pitch, heading = (float(x) for x in place.split())
        curves = {}
        for e in exes:
            name = os.path.basename(os.path.dirname(e))
            jobs = []
            for t in range(frames):
                d = t * step / 6378000.0
                lat = lat0 + np.degrees(d * np.cos(np.radians(heading)))
                lon = lon0 + np.degrees(d * np.sin(np.radians(heading)) / np.cos(np.radians(lat0)))
                for v in ("none", "height", "distance"):
                    jobs.append((os.path.join(out, f"mouv{number}_{name}_{t:02d}_{v}.bmp"), v, height, lat, lon, pitch, heading))
            run(e, jobs, os.path.join(out, "jobs.txt"), "20 140")
            bins = {}
            for t in range(frames):
                c = linear(os.path.join(out, f"mouv{number}_{name}_{t:02d}_none.bmp"))
                hh = 64.0 * exact(os.path.join(out, f"mouv{number}_{name}_{t:02d}_height.bmp"))
                dd = 4000.0 * exact(os.path.join(out, f"mouv{number}_{name}_{t:02d}_distance.bmp"))
                w = c.shape[1]
                sl = (slice(0, c.shape[0]), slice(w // 3, 2 * w // 3))
                c, hh, dd = c[sl], hh[sl], dd[sl]
                ok = (dd > 50.0) & (dd < 3990.0)
                forward = t * step + np.sqrt(np.maximum(dd ** 2 - height ** 2, 0.0))
                key = np.floor(forward / 20.0).astype(int)
                for k in np.unique(key[ok]):
                    m = ok & (key == k)
                    if m.sum() < 30:
                        continue
                    bins.setdefault(k, []).append((t, dd[m].mean(), hh[m].mean(), c[m].mean()))
            # The seen height and light against the distance, all bands and frames together.
            rows = [r for b in bins.values() for r in b]
            dist = np.array([r[1] for r in rows]); hs = np.array([r[2] for r in rows]); ls = np.array([r[3] for r in rows])
            edges = [200, 300, 450, 600, 800, 1000, 1300, 1600, 2000, 2500, 3000]
            curve = []
            for a, b in zip(edges[:-1], edges[1:]):
                m = (dist >= a) & (dist < b)
                curve.append((hs[m].mean(), ls[m].mean()) if m.sum() else (float("nan"), float("nan")))
            curves[name] = (edges, curve)
            # Per band of ground, while it crosses `band`: the change of its seen height and light from one frame to the
            # next, and over the whole crossing.
            dh, dl, rh, rl = [], [], [], []
            for b in bins.values():
                b = [r for r in b if band[0] <= r[1] <= band[1]]
                if len(b) < 4:
                    continue
                h = np.array([r[2] for r in b]); l = np.array([r[3] for r in b])
                dh.append(np.abs(np.diff(h)).mean()); dl.append((np.abs(np.diff(l)) / l.mean()).mean())
                rh.append(h.max() - h.min()); rl.append((l.max() - l.min()) / l.mean())
            print(f"{place} | {name} | de {band[0]:.0f} à {band[1]:.0f} m, par bande de 20 m de sol : hauteur vue, "
                  f"{np.mean(dh):.2f} m d'une image à la suivante, {np.mean(rh):.1f} m sur la traversée ; lumière, "
                  f"{100 * np.mean(dl):.1f} % d'une image à la suivante, {100 * np.mean(rl):.0f} % sur la traversée", flush=True)
        print(f"| distance | " + " | ".join(f"hauteur vue, {n} | lumière, {n}" for n in curves) + " |")
        print("|---|" + "---|---|" * len(curves))
        for i in range(len(edges) - 1):
            cells = []
            for n, (_, curve) in curves.items():
                cells += [f"{curve[i][0]:.1f} m", f"{curve[i][1]:.3f}"]
            print(f"| {edges[i]} à {edges[i + 1]} m | " + " | ".join(cells) + " |", flush=True)
        # A film strip: the frames 0, 10, 20, 30, 40 of each exe, side by side.
        sheet([[(os.path.join(out, f"mouv{number}_{os.path.basename(os.path.dirname(e))}_{t:02d}_none.bmp"),
                 f"{os.path.basename(os.path.dirname(e))}, +{t * step:.0f} m") for e in exes] for t in range(0, frames, 10)],
              os.path.join(out, f"mouvement_{lat0:.2f}_{height:.0f}.png"), 640, 360)


def krummholz(exe, out, places, height=3000.0):
    # For each place, straight down from `height`: the pixel nearest the screen's middle whose growing season is 4.3 to
    # 5.0 C, over the shrubs' cold limit and under the trees', where the canopy view still shows plants: the krummholz.
    jobs = [(os.path.join(out, f"krumm_{i}_{v}.bmp"), v, height, *(float(x) for x in p.split()[:2]), 89.9, 0.0)
            for i, p in enumerate(places) for v in ("season", "forest")]
    run(exe, jobs, os.path.join(out, "jobs.txt"))
    mpp = height * 2.0 * np.tan(np.radians(30.0)) / 720.0
    for i, p in enumerate(places):
        lat0, lon0 = (float(x) for x in p.split()[:2])
        s = 70.0 * exact(os.path.join(out, f"krumm_{i}_season.bmp")) - 30.0
        f = np.asarray(Image.open(os.path.join(out, f"krumm_{i}_forest.bmp")).convert("L"), np.float32)
        ok = (s > 4.3) & (s < 5.0) & (f > 60)
        ys, xs = np.nonzero(ok)
        if len(ys) == 0:
            print(f"{p} | pas de krummholz", flush=True)
            continue
        j = np.argmin(np.abs(ys - 360) + np.abs(xs - 640))
        lat = lat0 - (ys[j] - 360) * mpp / 6378000.0 * 180.0 / np.pi
        lon = lon0 + (xs[j] - 640) * mpp / (6378000.0 * np.cos(np.radians(lat0))) * 180.0 / np.pi
        print(f"{p} | krummholz {lat:.5f} {lon:.5f}, saison {s[ys[j], xs[j]]:.1f} C", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    exe, out, command = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    if command == "vues":
        vues(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()], *(sys.argv[5:6] or [SUN]))
    elif command == "releve":
        releve(exe, out)
    elif command == "biomes":
        biomes(exe, out)
    elif command == "raccord":
        raccord(exe, out)
    elif command == "orbite":
        orbite(exe, out, os.path.abspath(sys.argv[4]))
    elif command == "bord":
        bord(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()])
    elif command == "tests":
        tests(exe, out, sys.argv[4])
    elif command == "cretes":
        cretes(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()], [os.path.abspath(e) for e in sys.argv[5:]])
    elif command == "relais":
        relais(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()], *(sys.argv[5:6] or ["20 140"]))
    elif command == "mouvement":
        mouvement(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()], [os.path.abspath(e) for e in sys.argv[5:]])
    elif command == "krummholz":
        krummholz(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()])
    elif command == "lisiere":
        lisiere(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()])
    elif command == "formule":
        print("| latitude | ligne des arbres de la formule |")
        print("|---|---|")
        for lat in range(0, 75, 5):
            print(f"| {lat}° | {treeline_formula(lat):.0f} m |")
    elif command == "climat":
        climat(exe, out, [p.strip() for p in sys.argv[4].split(";") if p.strip()])
