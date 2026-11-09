# Quality bench (docs/spec-texturage-universel.md): many random places, several heights, every material's crops
# measured for the defect families a human eye kept finding one view at a time. The engine renders each place in one
# run (MYPLANETENGINE_BATCH): the colour view, the diagnostic views of the materials, and the colour view again with
# the mesh's cells twice finer. Without the clouds (MYPLANETENGINE_NO_CLOUDS), with the temporal smoothing and the glare,
# as the reference was measured.
#
# python tools/banc_qualite.py <exe> <out folder> [--sites 24] [--seed 1] [--before previous.json] [--from-sites qualite.json]
#
# Per crop of 128 x 128 pixels lying in one material:
# - hf: the energy of its finest octave (wavelengths of 2 to 4 pixels) against its octave of 16 to 32 pixels, dB. A
#   natural image has about the same energy in every octave (a power spectrum in 1/f^2); a blurry one loses its fine
#   octaves: a missing band of detail.
# - gap: how far its weakest middle octave falls below its neighbours, dB: a hole in its ladder of scales.
# - repeat: the highest local peak of the normalised autocorrelation of its detail (its light less a blur of 6 pixels)
#   apart from the central lobe, all that stays above 0.3 around the centre: a pattern that repeats. A long stripe
#   keeps its central lobe long and is not counted as a repeat.
# Per view: lines, the straight segments longer than 60 pixels on the ground (OpenCV's LSD, which breaks a wavy band
# into pieces of under 120 pixels): bands drawn at one stroke, seams.
# Per view and material with 3 crops or more: the spread (std, dB) across its crops of their mean light, of their detail
#   (the energy of the light less a blur of 6 pixels) and of their relative detail (detail over light squared): a tiled
#   texture keeps all three nearly constant, a wallpaper. Real landscapes vary from one crop to the next.
# Per view: mutation, the mean change of the ground's light, relative, when the mesh's cells are twice finer for the
# same camera: what the mesh decides of the look, which changes as the camera comes closer and the cells shrink. The
# pixels' own fading of what they cannot show does not count: the camera is the same.
# The report puts the photos of docs/images/cible-*.jpg through the same crops: what a real landscape scores.
import argparse, atexit, json, math, os, shutil, subprocess, sys, time
import cv2
import numpy as np

HEIGHTS = [12.0, 50.0, 200.0, 800.0, 3000.0]  # m above the ground
PITCH = 35.0                                   # degrees below the horizon
FACE_FACTOR = 2.0                              # the engine's default; the finer mesh takes half
VIEWS = ["rock", "sand", "grass", "snow", "scree"]  # the engine's diagnostic views of the materials
MATERIALS = VIEWS + ["soil"]  # bare soil has no view of its own: the rest of the soils (it went unmeasured, untextured)
TILE = 128
CROP_SHARE = 0.7  # a crop counts for a material that covers this much of it
TOP = 256         # crops below this row only: more than 25 degrees under the horizon, not the far haze
R = 6378e3
ENGINE = dict(MYPLANETENGINE_NO_CLOUDS="1", MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")


def sites(n, seed):
    rng = np.random.default_rng(seed)
    u, v, h = rng.random(n), rng.random(n), rng.random(n)
    return [(math.degrees(math.asin(2 * a - 1)), 360 * b - 180, 360 * c) for a, b, c in zip(u, v, h)]


def run(exe, jobs, path, sun, per_view=4):
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=sun, **ENGINE)
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE"):
        env.pop(k, None)
    # A run's time grows with its views: about 1.3 s each with the erosion's rivers, 1,440 to pick 30 places.
    subprocess.run([exe], env=env, timeout=max(600, per_view * len(jobs)))


def luminance(img):
    rgb = img[..., ::-1].astype(np.float32) / 255.0
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])


def octaves(tile):
    # Energy per octave of wavelength, 2-4, 4-8, 8-16, 16-32, 32-64 pixels, in dB, Hann window.
    n = tile.shape[0]
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    spectrum = np.abs(np.fft.fft2((tile - tile.mean()) * w)) ** 2
    f = np.hypot(*np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n)))
    energy = []
    for lo, hi in ((2, 4), (4, 8), (8, 16), (16, 32), (32, 64)):
        band = (f > 1.0 / hi) & (f <= 1.0 / lo)
        energy.append(10 * np.log10(spectrum[band].sum() + 1e-12))
    return np.array(energy)


def repeat(tile):
    t = tile - cv2.GaussianBlur(tile, (0, 0), 6)
    spectrum = np.abs(np.fft.fft2(t)) ** 2
    ac = np.real(np.fft.ifft2(spectrum))
    ac = np.fft.fftshift(ac / max(ac.flat[0], 1e-12))
    n = tile.shape[0]
    peaks = ac >= cv2.dilate(ac, np.ones((3, 3), np.uint8))  # local maxima only, not a lobe's flank
    _, labels = cv2.connectedComponents((ac > 0.3).astype(np.uint8))
    peaks &= labels != labels[n // 2, n // 2]  # the central lobe, however long
    y, x = np.mgrid[:n, :n] - n // 2
    peaks &= np.hypot(x, y) <= n // 2 - 8  # the edges, where little overlaps
    return float(ac[peaks].max()) if peaks.any() else 0.0


def ground_mask(mask_img):
    # The diagnostic views draw the ground in black and white, the sky in colour.
    b, g, r = [mask_img[..., i].astype(np.int16) for i in range(3)]
    return (np.abs(b - r) < 12) & (np.abs(g - r) < 12)


def weight(mask_img):
    grey = mask_img[..., 1].astype(np.float32) / 255.0
    return cv2.blur(grey, (9, 9))


def visible(weights):
    # What is seen: the materials' weights are decided before the layers cover each other, as the pixels lay them:
    # soil, then scree, then rock, then snow on top.
    weights = dict(weights)
    cover = 1.0 - weights["snow"]
    for m in ("rock", "scree"):
        weights[m] = weights[m] * cover
        cover = cover * (1.0 - weights[m] / np.maximum(cover, 1e-3))
    weights["soil"] = cover * np.clip(1.0 - weights["sand"] - weights["grass"], 0.0, 1.0)
    for m in ("sand", "grass"):
        weights[m] = weights[m] * cover
    return weights


def lines(lum, ground):
    lsd = cv2.createLineSegmentDetector()
    segs = lsd.detect((lum * 255).astype(np.uint8))[0]
    if segs is None:
        return 0
    long = 60.0
    count = 0
    for x1, y1, x2, y2 in segs.reshape(-1, 4):
        mx, my = int((x1 + x2) / 2), int((y1 + y2) / 2)
        if math.hypot(x2 - x1, y2 - y1) > long and ground[min(my, ground.shape[0] - 1), min(mx, ground.shape[1] - 1)]:
            count += 1
    return count


def levels(tile):
    # Mean light and detail of a crop, dB: what the wallpaper's spreads compare from one crop to the next.
    hp = tile - cv2.GaussianBlur(tile, (0, 0), 6)
    return 10 * math.log10(tile.mean() + 1e-6), 10 * math.log10(hp.var() + 1e-9)


def spreads(levels_list):
    # Spread across crops of the mean light, the detail and the relative detail, dB.
    a = np.array(levels_list)
    return float(a[:, 0].std()), float(a[:, 1].std()), float((a[:, 1] - 2 * a[:, 0]).std())


def mutation(coarse, fine, ground):
    # The same camera, the mesh's cells twice finer: the mean change of the ground's light, relative to it.
    if ground.sum() < 1000:
        return None
    return float(np.abs(fine - coarse)[ground].mean() / max(coarse[ground].mean(), 1e-3))


def pick_sites(exe, work, n, seed):
    # Places for every material: eight times as many candidates, each seen from 3 km straight down in the sea's view and
    # in each material's; land only (sea under a fifth of the view), then, material by material, the candidates where it
    # shows most, under what covers it (visible), an equal share of the n places each.
    candidates = sites(8 * n, seed)
    shares = {m: [] for m in ["sea"] + MATERIALS}
    jobs = [(os.path.join(work, f"{m}{i}.bmp"), m, 3000.0, lat, lon, 89.0, 0.0)
            for i, (lat, lon, _) in enumerate(candidates) for m in ["sea"] + VIEWS]
    run(exe, jobs, os.path.join(work, "jobs.txt"), "10 70")
    for i in range(len(candidates)):
        masks = {m: cv2.imread(os.path.join(work, f"{m}{i}.bmp")) for m in ["sea"] + VIEWS}
        if any(v is None for v in masks.values()):
            for m in shares:
                shares[m].append(1.0 if m == "sea" else 0.0)
            continue
        seen = visible({m: weight(v) for m, v in masks.items()})
        for m in shares:
            shares[m].append(float(seen[m].mean()))
    for job in jobs:
        if os.path.exists(job[0]):
            os.remove(job[0])
    land, taken = [], set()
    per = max(n // len(MATERIALS), 1)
    for m in MATERIALS:
        order = sorted((i for i in range(len(candidates)) if shares["sea"][i] < 0.2 and i not in taken),
                       key=lambda i: -shares[m][i])
        for i in order[:per]:
            taken.add(i)
            land.append((candidates[i][0], candidates[i][1], m))
    # Each place looks where its material shows most, among eight headings, from 200 m: rock keeps to slopes.
    jobs = [(os.path.join(work, f"h{s}_{k}.bmp"), m, 200.0, lat, lon, PITCH, 45.0 * k)
            for s, (lat, lon, m) in enumerate(land) for k in range(8) if m in VIEWS]  # bare soil: north
    run(exe, jobs, os.path.join(work, "jobs.txt"), "10 70")
    best = {}
    for job in jobs:
        img = cv2.imread(job[0])
        part = float((img[..., 1] > 127).mean()) if img is not None else 0.0
        s_, k = (int(t) for t in os.path.basename(job[0])[1:-4].split("_"))
        if part >= best.get(s_, (-1.0, 0.0))[0]:
            best[s_] = (part, job[6])
        if os.path.exists(job[0]):
            os.remove(job[0])
    land = [(lat, lon, best.get(s_, (0.0, 0.0))[1], m) for s_, (lat, lon, m) in enumerate(land)]
    return land


def load_sites(path):
    # Les rapports complets conservent les coordonnées ; une référence condensée
    # qui ne contient qu'un nombre de sites ne permet pas de retrouver ces lieux.
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = data.get("sites") if isinstance(data, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("sites doit être une liste non vide de lieux (pas un simple nombre)")
    result = []
    for i, row in enumerate(records, 1):
        if not isinstance(row, dict) or not all(k in row for k in ("lat", "lon", "heading", "target")):
            raise ValueError(f"site {i} : clés lat, lon, heading et target requises")
        lat, lon, heading = (row[k] for k in ("lat", "lon", "heading"))
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (lat, lon, heading)):
            raise ValueError(f"site {i} : coordonnées et cap doivent être des nombres finis")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError(f"site {i} : latitude ou longitude hors limites")
        if not isinstance(row["target"], str) or row["target"] not in MATERIALS:
            raise ValueError(f"site {i} : matériau cible inconnu")
        result.append((lat, lon, heading, row["target"]))
    return result


def survey(exe, out, n, seed, site_list=None, batch_suns=False):
    work = os.path.join(out, "travail")
    crops_dir = os.path.join(out, "crops")
    os.makedirs(work, exist_ok=True)
    os.makedirs(crops_dir, exist_ok=True)
    land = pick_sites(exe, work, n, seed) if site_list is None else site_list
    process = None
    if batch_suns:
        # Un seul processus moteur : soleils explicites par ligne et un sous-dossier
        # par site pour analyser et libérer les images au fur et à mesure.
        if site_list is None:
            raise ValueError("--batch-suns exige --from-sites")
        all_jobs = []
        for i, (lat, lon, heading, target) in enumerate(land):
            site_dir = os.path.join(work, f"site_{i:03}")
            os.makedirs(site_dir, exist_ok=False)
            sun_lat, sun_lon = max(min(lat - 20.0, 60.0), -60.0), lon + 35.0
            for h in HEIGHTS:
                common = (h, lat, lon, PITCH, heading)
                all_jobs.append((os.path.join(site_dir, f"c{h:g}.bmp"), "-", *common, FACE_FACTOR, f"{sun_lat:.2f}", f"{sun_lon:.2f}"))
                all_jobs += [(os.path.join(site_dir, f"{m}{h:g}.bmp"), m, *common, FACE_FACTOR, f"{sun_lat:.2f}", f"{sun_lon:.2f}") for m in VIEWS + ["sea", "rockall"]]
                all_jobs.append((os.path.join(site_dir, f"f{h:g}.bmp"), "-", *common, 0.5 * FACE_FACTOR, f"{sun_lat:.2f}", f"{sun_lon:.2f}"))
        job_path = os.path.join(work, "jobs_batch_suns.txt")
        with open(job_path, "w", encoding="utf-8") as f:
            for job in all_jobs:
                f.write(" ".join(str(x) for x in job) + "\n")
        env = dict(os.environ, MYPLANETENGINE_BATCH=job_path, MYPLANETENGINE_SUN="10 70", **ENGINE)
        for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE"):
            env.pop(k, None)
        engine_log = open(os.path.join(work, "moteur.log"), "w", encoding="utf-8")
        process = subprocess.Popen([exe], env=env, stdout=engine_log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        def stop_process():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
        atexit.register(stop_process)
        deadline = time.monotonic() + 7200
    records = []
    for s, (lat, lon, heading, target) in enumerate(land):
        site_work = os.path.join(work, f"site_{s:03}") if batch_suns else work
        sun = f"{max(min(lat - 20.0, 60.0), -60.0):.2f} {lon + 35.0:.2f}"  # the sun some 50 degrees up
        jobs = []
        for h in HEIGHTS:
            jobs.append((os.path.join(site_work, f"c{h:g}.bmp"), "-", h, lat, lon, PITCH, heading))
            jobs += [(os.path.join(site_work, f"{m}{h:g}.bmp"), m, h, lat, lon, PITCH, heading) for m in VIEWS + ["sea", "rockall"]]
            jobs.append((os.path.join(site_work, f"f{h:g}.bmp"), "-", h, lat, lon, PITCH, heading, 0.5 * FACE_FACTOR))
        t0 = time.time()
        if batch_suns:
            # Le sidecar texte est écrit après la capture, et marque sa fin.
            while not all(os.path.isfile(str(job[0]) + ".txt") for job in jobs):
                if shutil.disk_usage(out).free < 768 * 1024 * 1024:
                    raise RuntimeError("espace disque insuffisant pour poursuivre le banc qualité")
                if process.poll() is not None:
                    raise RuntimeError(f"capture incomplète au site {s + 1} ; code moteur {process.returncode} ; journal {engine_log.name}")
                if time.monotonic() > deadline:
                    process.terminate()
                    raise TimeoutError("banc qualité : délai du processus moteur dépassé")
                time.sleep(0.25)
        else:
            run(exe, jobs, os.path.join(work, "jobs.txt"), sun)
        site = {"lat": lat, "lon": lon, "heading": heading, "target": target, "views": []}
        for h in HEIGHTS:
            if batch_suns and shutil.disk_usage(out).free < 768 * 1024 * 1024:
                raise RuntimeError("espace disque insuffisant pour poursuivre le banc qualité")
            colour = cv2.imread(os.path.join(site_work, f"c{h:g}.bmp"))
            masks = {m: cv2.imread(os.path.join(site_work, f"{m}{h:g}.bmp")) for m in VIEWS + ["sea", "rockall"]}
            if colour is None or any(v is None for v in masks.values()):
                continue
            lum = luminance(colour)
            ground = ground_mask(masks["rock"])
            weights = visible({m: weight(v) for m, v in masks.items()})
            # A wall as it is seen: its rock with the ledges that break it, scree and soil on them (the rock view leaves
            # them out, and the rock seldom covers 70 % of a crop without them).
            weights["rock"] = weights["rockall"] * (1.0 - weights["snow"])
            fine = cv2.imread(os.path.join(site_work, f"f{h:g}.bmp"))
            view = {"height": h, "lines": lines(lum, ground), "tiles": [],
                    "mutation": mutation(lum, luminance(fine), ground) if fine is not None else None}
            for y in range(TOP, lum.shape[0] - TILE + 1, TILE):
                for x in range(0, lum.shape[1] - TILE + 1, TILE):
                    if ground[y:y + TILE, x:x + TILE].mean() < 0.98:
                        continue
                    if weights["sea"][y:y + TILE, x:x + TILE].mean() > 0.05:  # water is no material of the ground
                        continue
                    shares = {m: float(weights[m][y:y + TILE, x:x + TILE].mean()) for m in MATERIALS}
                    material = max(shares, key=shares.get)
                    if shares[material] < CROP_SHARE:
                        continue
                    tile = lum[y:y + TILE, x:x + TILE]
                    e = octaves(tile)
                    gap = float(max(0.5 * (e[i - 1] + e[i + 1]) - e[i] for i in range(1, 4)))
                    light, detail = levels(tile)
                    rec = {"material": material, "x": x, "y": y, "hf": float(e[0] - e[3]), "gap": gap,
                           "repeat": repeat(tile), "contrast": float(tile.std() / max(tile.mean(), 1e-3)),
                           "light": light, "detail": detail}
                    name = f"s{s}_h{h:g}_{x}_{y}.png"
                    cv2.imwrite(os.path.join(crops_dir, name), colour[y:y + TILE, x:x + TILE])
                    rec["crop"] = name
                    view["tiles"].append(rec)
            site["views"].append(view)
        for f in os.listdir(site_work):
            if f.endswith(".bmp"):
                os.remove(os.path.join(site_work, f))
        records.append(site)
        print(f"site {s + 1}/{len(land)} {lat:.2f} {lon:.2f}: {sum(len(v['tiles']) for v in site['views'])} crops, "
              f"{time.time() - t0:.0f} s", flush=True)
    if process is not None:
        code = process.wait(timeout=60)
        engine_log.close()
        if code != 0:
            raise RuntimeError(f"banc qualité : code moteur {code}")
    return records


def summary(records):
    table = {}
    for site in records:
        for view in site["views"]:
            for t in view["tiles"]:
                key = (t["material"], view["height"])
                table.setdefault(key, []).append(t)
    walls = {}  # the wallpaper's spreads, per view and material
    for site in records:
        for view in site["views"]:
            groups = {}
            for t in view["tiles"]:
                if "light" in t:
                    groups.setdefault(t["material"], []).append((t["light"], t["detail"]))
            for m, lv in groups.items():
                if len(lv) >= 3:
                    walls.setdefault((m, view["height"]), []).append(spreads(lv))
    rows = []
    for (m, h), tiles in sorted(table.items()):
        hf = np.array([t["hf"] for t in tiles]); gap = np.array([t["gap"] for t in tiles])
        rep = np.array([t["repeat"] for t in tiles])
        row = {"material": m, "height": h, "n": len(tiles), "hf_median": float(np.median(hf)), "hf_p5": float(np.percentile(hf, 5)),
               "gap_p95": float(np.percentile(gap, 95)), "repeat_p95": float(np.percentile(rep, 95))}
        if (m, h) in walls:
            w = np.median(np.array(walls[(m, h)]), axis=0)
            row.update({"light_spread": float(w[0]), "detail_spread": float(w[1]), "relative_spread": float(w[2])})
        rows.append(row)
    lines_by_height = {}
    mut = {}
    for site in records:
        for view in site["views"]:
            lines_by_height.setdefault(view["height"], []).append(view["lines"])
            if view["mutation"] is not None:
                mut.setdefault(f"{view['height']:g}", []).append(view["mutation"])
    return {"tiles": rows,
            "lines": {f"{h:g}": float(np.mean(v)) for h, v in sorted(lines_by_height.items())},
            "mutation": {h: {"median": float(np.median(v)), "p95": float(np.percentile(v, 95)), "n": len(v)} for h, v in mut.items()}}


def report(summ, before=None):
    out = ["| matériau | hauteur | crops | hf médiane (dB) | hf p5 | trou p95 (dB) | répétition p95 | étalement clarté (dB) | contraste | contraste relatif |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    old = {(r["material"], r["height"]): r for r in before["tiles"]} if before else {}
    for r in summ["tiles"]:
        o = old.get((r["material"], r["height"]))
        d = (lambda k: f" ({r[k] - o[k]:+.1f})" if o and k in o else "")
        w = (lambda k: f"{r[k]:.2f}{d(k)}" if k in r else "-")
        out.append(f"| {r['material']} | {r['height']:g} m | {r['n']} | {r['hf_median']:.1f}{d('hf_median')} | {r['hf_p5']:.1f}{d('hf_p5')} | "
                   f"{r['gap_p95']:.1f}{d('gap_p95')} | {r['repeat_p95']:.2f}{d('repeat_p95')} | "
                   f"{w('light_spread')} | {w('detail_spread')} | {w('relative_spread')} |")
    out.append("")
    out.append("Segments droits par vue : " + ", ".join(f"{h} m {v:.1f}" for h, v in summ["lines"].items()))
    out.append("Mutation (changement relatif de la lumière, maillage deux fois plus fin), médiane et p95 : "
               + ", ".join(f"{h} m {v['median']:.3f} / {v['p95']:.3f}" for h, v in summ["mutation"].items()))
    if "photos" in summ:
        p = summ["photos"]
        out.append(f"Photos réelles (cible-*.jpg, {p['n']} crops) : hf médiane {p['hf_median']:.1f} dB, p5 {p['hf_p5']:.1f} ; "
                   f"trou p95 {p['gap_p95']:.1f} dB ; répétition p95 {p['repeat_p95']:.2f}")
        if "light_spread" in p:
            out.append(f"Étalement d'un crop à l'autre, médiane des photos (de la moins à la plus variée) : clarté {p['light_spread']:.2f} dB "
                       f"({p['light_range'][0]:.2f} à {p['light_range'][1]:.2f}), contraste {p['detail_spread']:.2f} "
                       f"({p['detail_range'][0]:.2f} à {p['detail_range'][1]:.2f}), contraste relatif {p['relative_spread']:.2f} "
                       f"({p['relative_range'][0]:.2f} à {p['relative_range'][1]:.2f})")
    return "\n".join(out)


def photos():
    # The reference: real landscapes, at the renders' width, through the same crops, their lower two thirds.
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "images")
    hf, gap, rep, walls = [], [], [], []
    for name in sorted(os.listdir(folder)):
        if not name.startswith("cible-"):
            continue
        img = cv2.imread(os.path.join(folder, name))
        img = cv2.resize(img, (1280, int(img.shape[0] * 1280 / img.shape[1])), interpolation=cv2.INTER_AREA)
        lum = luminance(img)
        lv = []
        for y in range(lum.shape[0] // 3, lum.shape[0] - TILE + 1, TILE):
            for x in range(0, lum.shape[1] - TILE + 1, TILE):
                tile = lum[y:y + TILE, x:x + TILE]
                e = octaves(tile)
                hf.append(e[0] - e[3]); gap.append(max(0.5 * (e[i - 1] + e[i + 1]) - e[i] for i in range(1, 4)))
                rep.append(repeat(tile))
                lv.append(levels(tile))
        walls.append(spreads(lv))
    w = np.array(walls)
    return {"n": len(hf), "hf_median": float(np.median(hf)), "hf_p5": float(np.percentile(hf, 5)),
            "gap_p95": float(np.percentile(gap, 95)), "repeat_p95": float(np.percentile(rep, 95)),
            "light_spread": float(np.median(w[:, 0])), "detail_spread": float(np.median(w[:, 1])), "relative_spread": float(np.median(w[:, 2])),
            "light_range": [float(w[:, 0].min()), float(w[:, 0].max())], "detail_range": [float(w[:, 1].min()), float(w[:, 1].max())],
            "relative_range": [float(w[:, 2].min()), float(w[:, 2].max())]}


def sheets(records, out):
    # The twelve blurriest and the twelve most repetitive crops of each material.
    tiles = [t for s in records for v in s["views"] for t in v["tiles"]]
    for m in MATERIALS:
        mine = [t for t in tiles if t["material"] == m]
        for key, worst in (("hf", lambda t: t["hf"]), ("repeat", lambda t: -t["repeat"])):
            chosen = sorted(mine, key=worst)[:12]
            if not chosen:
                continue
            sheet = np.full((TILE, TILE * len(chosen), 3), 255, np.uint8)
            for i, t in enumerate(chosen):
                img = cv2.imread(os.path.join(out, "crops", t["crop"]))
                if img is not None:
                    sheet[:, i * TILE:(i + 1) * TILE] = img
            cv2.imwrite(os.path.join(out, f"pires_{m}_{key}.png"), sheet)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("exe"); ap.add_argument("out")
    ap.add_argument("--sites", type=int, default=24); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--before")
    ap.add_argument("--reuse-sites", help="reprendre exactement --sites lieux d’un rapport antérieur")
    ap.add_argument("--from-sites", help="reprendre tous les lieux d'un rapport qualite.json, sans recherche initiale")
    ap.add_argument("--batch-suns", action="store_true", help="une initialisation, soleil par ligne ; nécessite un moteur compatible et --from-sites")
    a = ap.parse_args()
    if a.sites <= 0:
        ap.error("--sites doit être strictement positif")
    if a.from_sites and a.reuse_sites:
        ap.error("choisir --from-sites ou --reuse-sites")
    source_sites = a.from_sites or a.reuse_sites
    if a.batch_suns and not source_sites:
        ap.error("--batch-suns exige --from-sites")
    site_list = None
    if source_sites:
        try:
            site_list = load_sites(source_sites)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            ap.error(f"--from-sites : {error}")
    if a.reuse_sites and len(site_list) != a.sites:
        ap.error("--reuse-sites doit contenir exactement --sites lieux")
    out = os.path.abspath(a.out)
    records = survey(os.path.abspath(a.exe), out, a.sites, a.seed, site_list, a.batch_suns)

    summ = summary(records)
    summ["photos"] = photos()
    json.dump({"sites": records, "summary": summ}, open(os.path.join(out, "qualite.json"), "w"), indent=1)
    sheets(records, out)
    before = json.load(open(a.before))["summary"] if a.before else None
    text = report(summ, before)
    open(os.path.join(out, "rapport.md"), "w", encoding="utf-8").write(text + "\n")
    print(text)
