# Tones bench (docs/recherche-tons-exposition.md): what the screen shows of the light, against photographs.
#
# python tools/banc_tons.py vues <out folder> <tests file> <exe> [exe ...]
#   Each view of the tests file, its sun with it, captured in colour and in the sea's diagnostic view, whose grey pixels
#   are the ground and the sea, its coloured ones the sky. Per view: the ground's luminance percentiles, linear, its
#   shadows (stops from the median down to p5), its spread (p5 to p95, stops), the sky's median, the share of clipped
#   pixels. The photos of docs/images/cible-*.jpg go through the same measures, their ground below a hand-set row.
# python tools/banc_tons.py descente <out folder> "<lat> <lon>" "<sun lat> <sun lon>" <exe> [exe ...]
#   Straight down from 1 500 km to 30 m above the same ground, one run (MYPLANETENGINE_BATCH): the mean light of the
#   centre of the image, which looks at the same ground all the way. With several exes, each against the first, in stops
#   per height: the ground's own change cancels out, a smooth line is a stable exposure.
# python tools/banc_tons.py tour <out folder> "<lat> <lon>" "<sun lat> <sun lon>" <exe> [exe ...]
#   From 800 m, the camera turns from the sky to the ground (pitch -20 to 70 degrees), then around (heading). The sky
#   10 degrees above the horizon and the ground 25 degrees below, straight ahead, are the same at every pitch: their light
#   must not change with what else the frame holds, whose mean is what an exposure metered on the image would follow.
# The day views of the summary are those under 20 km with the sun 15 degrees up or more, like the photos.
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import banc_visuel

DOCS = os.path.join(HERE, "..", "docs", "images")
# The photos' ground: the rows below this share of the height (the sky and the far ridges above it).
PHOTO_GROUND = {"badlands": 0.40, "basalte": 0.10, "cote": 0.45, "desert": 0.30, "falaise-alcoves": 0.25,
                "granite": 0.55, "gres-neige": 0.35, "gres-zion": 0.55, "plis": 0.0}
OVERCAST = {"basalte", "gres-zion", "plis"}  # no sun on the ground: shown, not counted in the sunny median
FOV_Y = np.radians(60.0)


def linear(img):
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def luminance(lin):
    return lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def measures(img, ground, sky=None):
    lin = linear(img)
    y = luminance(lin)
    g = y[ground]
    p = np.percentile(g, [1, 5, 25, 50, 75, 95, 99]) if g.size else np.full(7, np.nan)
    clipped = float((np.asarray(img.convert("RGB")).max(axis=2) >= 254).mean())
    s = float(np.median(y[sky])) if sky is not None and sky.any() else float("nan")
    return {"p": p, "shadows": float(np.log2(p[3] / max(p[1], 1e-4))), "spread": float(np.log2(p[5] / max(p[1], 1e-4))),
            "sky": s, "clipped": clipped}


def line(name, m):
    p = m["p"]
    return (f"{name[:44]:44s} | sol p5 {p[1]:.3f} p25 {p[2]:.3f} p50 {p[3]:.3f} p75 {p[4]:.3f} p95 {p[5]:.3f} p99 {p[6]:.3f}"
            f" | ombres {m['shadows']:.1f} IL, étendue {m['spread']:.1f} IL | ciel {m['sky']:.3f} | écrêté {100 * m['clipped']:.1f} %")


def photos():
    out = []
    for f in sorted(os.listdir(DOCS)):
        if not f.startswith("cible-"):
            continue
        name = f[6:-4]
        img = Image.open(os.path.join(DOCS, f)).convert("RGB")
        img = img.resize((1280, round(img.height * 1280 / img.width)), Image.LANCZOS)
        rows = np.arange(img.height)[:, None] >= PHOTO_GROUND.get(name, 0.5) * img.height
        ground = np.broadcast_to(rows, (img.height, img.width))
        out.append((name, measures(img, ground)))
    return out


def tests(path):
    views = []
    for raw in open(path, encoding="utf-8-sig"):
        if raw.startswith("#") or raw.count("|") < 2:
            continue
        label, place, sun = (s.strip() for s in raw.split("|"))
        views.append((label, place, sun))
    return views


def elevation(place, sun):
    # The sun's height above the horizon at the camera's nadir, degrees.
    lat, lon = (np.radians(float(v)) for v in place.split()[1:3])
    slat, slon = (np.radians(float(v)) for v in sun.split())
    return 90.0 - np.degrees(np.arccos(np.sin(lat) * np.sin(slat) + np.cos(lat) * np.cos(slat) * np.cos(slon - lon)))


def vues(out, tests_file, exes):
    views = tests(tests_file)
    sunny = [m for n, m in photos() if n not in OVERCAST]
    for n, m in photos():
        print(line(f"photo {n}{' (couvert)' if n in OVERCAST else ''}", m))
    med = lambda k: float(np.median([m[k] for m in sunny]))
    print(f"{'photos ensoleillées, médiane':44s} | sol " + " ".join(f"p{q} {np.median([m['p'][k] for m in sunny]):.3f}"
          for k, q in ((1, 5), (2, 25), (3, 50), (4, 75), (5, 95))) + " "
          f"| ombres {med('shadows'):.1f} IL, étendue {med('spread'):.1f} IL | écrêté {100 * med('clipped'):.1f} %", flush=True)
    for exe in exes:
        tag = os.path.basename(os.path.dirname(exe))
        folder = os.path.join(out, tag)
        os.makedirs(folder, exist_ok=True)
        sheet = Image.new("RGB", (4 * 320, ((len(views) + 3) // 4) * (180 + 30)), "white")
        d, font = ImageDraw.Draw(sheet), ImageFont.truetype("arial.ttf", 12)
        rows = []
        for i, (label, place, sun) in enumerate(views):
            png, mask = os.path.join(folder, f"v{i:02d}.png"), os.path.join(folder, f"v{i:02d}_masque.png")
            banc_visuel.capture(exe, place, sun, png)
            os.environ["MYPLANETENGINE_VIEW"] = "sea"
            banc_visuel.capture(exe, place, sun, mask)
            del os.environ["MYPLANETENGINE_VIEW"]
            img, msk = Image.open(png), np.asarray(Image.open(mask).convert("RGB")).astype(np.int16)
            ground = (np.abs(msk[..., 0] - msk[..., 1]) < 12) & (np.abs(msk[..., 2] - msk[..., 1]) < 12)
            ground &= (msk.max(axis=2) > 2) | (np.asarray(img.convert("RGB")).max(axis=2) > 1)  # space: black in both
            sky = ~ground & (msk.max(axis=2) - msk.min(axis=2) >= 12)
            m = measures(img, ground, sky)
            rows.append((label, m))
            print(f"{tag} | " + line(label, m), flush=True)
            x, y = (i % 4) * 320, (i // 4) * 210
            sheet.paste(img.convert("RGB").resize((320, 180)), (x, y + 30))
            d.text((x + 4, y + 2), label[:52], fill="black", font=font)
            d.text((x + 4, y + 15), f"sol p50 {m['p'][3]:.2f}, ombres {m['shadows']:.1f} IL, ciel {m['sky']:.2f}", fill="black", font=font)
        sheet.save(os.path.join(out, f"{tag}_vues.jpg"), quality=90)
        def summary(name, group):
            if group:
                print(f"{tag} | {name:44s} | sol p5 {np.median([m['p'][1] for m in group]):.3f} "
                      f"p25 {np.median([m['p'][2] for m in group]):.3f} p50 {np.median([m['p'][3] for m in group]):.3f} "
                      f"p75 {np.median([m['p'][4] for m in group]):.3f} p95 {np.median([m['p'][5] for m in group]):.3f} "
                      f"| ombres {np.median([m['shadows'] for m in group]):.1f} IL, étendue "
                      f"{np.median([m['spread'] for m in group]):.1f} IL | ciel {np.median([m['sky'] for m in group]):.3f}", flush=True)
        # Like the photos: from the ground or low (under 20 km), the sun 15 degrees up or more; then the low suns.
        summary("vues de jour sous 20 km, médiane", [m for (_, p, s), (_, m) in zip(views, rows) if float(p.split()[0]) < 2e4 and elevation(p, s) >= 15])
        summary("soleil bas sous 20 km, de 0 à 15°, médiane", [m for (_, p, s), (_, m) in zip(views, rows) if float(p.split()[0]) < 2e4 and 0 < elevation(p, s) < 15])


def batch(exe, jobs, folder, sun):
    path = os.path.join(folder, "jobs.txt")
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=sun, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE"):
        env.pop(k, None)
    subprocess.run([exe], env=env, timeout=900)


def descente(out, place, sun, exes):
    lat, lon = place.split()
    heights = [1.5e6, 8e5, 4e5, 2e5, 1e5, 5e4, 2.5e4, 1.2e4, 6e3, 3e3, 1.5e3, 800, 400, 200, 100, 50, 30]
    curves = []
    for exe in exes:
        tag = os.path.basename(os.path.dirname(exe))
        folder = os.path.join(out, f"{tag}_descente")
        os.makedirs(folder, exist_ok=True)
        jobs = [(os.path.join(folder, f"d{k:02d}.bmp"), "-", h, lat, lon, 89.9, 0.0) for k, h in enumerate(heights)]
        batch(exe, jobs, folder, sun)
        values = []
        for k, h in enumerate(heights):
            img = Image.open(jobs[k][0])
            w, hgt = img.size
            centre = luminance(linear(img.crop((w // 2 - 40, hgt // 2 - 40, w // 2 + 40, hgt // 2 + 40)))).mean()
            whole = luminance(linear(img)).mean()
            values.append((h, centre, whole))
        steps = [abs(np.log2(b[1] / a[1])) for a, b in zip(values, values[1:])]
        print(f"{tag} | descente " + " ".join(f"{h / 1000:g}km:{c:.3f}" for h, c, _ in values), flush=True)
        print(f"{tag} | plus grand écart d'une hauteur à la suivante, centre : {max(steps):.2f} IL ; de 1 500 km à 30 m : "
              f"{np.log2(values[-1][1] / values[0][1]):+.2f} IL", flush=True)
        curves.append((tag, values))
    # Against the first exe: what the new tones change at each height. The ground's own change cancels out.
    for tag, values in curves[1:]:
        ratio = [np.log2(v[1] / b[1]) for v, b in zip(values, curves[0][1])]
        print(f"{tag} | contre {curves[0][0]}, IL " + " ".join(f"{h / 1000:g}km:{r:+.2f}" for h, r in zip(heights, ratio))
              + f" ; plus grand saut d'une hauteur à la suivante : {max(abs(b - a) for a, b in zip(ratio, ratio[1:])):.2f} IL", flush=True)


def tour(out, place, sun, exes):
    lat, lon = place.split()
    pitches = [-20, -10, 0, 10, 20, 30, 45, 60, 70]
    headings = list(range(0, 360, 30))
    for exe in exes:
        tag = os.path.basename(os.path.dirname(exe))
        folder = os.path.join(out, f"{tag}_tour")
        os.makedirs(folder, exist_ok=True)
        jobs = [(os.path.join(folder, f"p{k:02d}.bmp"), "-", 800, lat, lon, p, 0.0) for k, p in enumerate(pitches)]
        jobs += [(os.path.join(folder, f"c{k:02d}.bmp"), "-", 800, lat, lon, 30, c) for k, c in enumerate(headings)]
        batch(exe, jobs, folder, sun)
        probes, means = {10: [], -25: []}, []  # the sky 10 degrees up, the ground 25 degrees down, straight ahead
        for k, p in enumerate(pitches):
            img = Image.open(jobs[k][0])
            w, h = img.size
            y = luminance(linear(img))
            means.append(float(y.mean()))
            for e, values in probes.items():
                row = round(h / 2 - np.tan(np.radians(e + p)) / np.tan(FOV_Y / 2) * h / 2)
                values.append(float(y[row - 2:row + 3, w // 2 - 20:w // 2 + 20].mean()) if 2 <= row < h - 2 else float("nan"))
        print(f"{tag} | tour, inclinaison " + " ".join(f"{p}°:{a:.3f}/{b:.3f}/{m:.3f}" for p, a, b, m in
              zip(pitches, probes[10], probes[-25], means)) + " (ciel à +10° / sol à -25° / image entière)", flush=True)
        for e, values in probes.items():
            ok = [v for v in values if v == v]
            print(f"{tag} | {'ciel à +10°' if e > 0 else 'sol à -25°'}, {len(ok)} inclinaisons : écart {np.log2(max(ok) / min(ok)):.2f} IL", flush=True)
        print(f"{tag} | image entière : {np.log2(max(means) / min(means)):.2f} IL, ce qu'une mesure sur l'image ferait varier "
              f"l'exposition", flush=True)
        cap = [float(luminance(linear(Image.open(jobs[len(pitches) + k][0]))).mean()) for k in range(len(headings))]
        print(f"{tag} | tour, cap " + " ".join(f"{c}°:{m:.3f}" for c, m in zip(headings, cap))
              + f" : {np.log2(max(cap) / min(cap)):.2f} IL d'une image à l'autre, vers le soleil ou dos à lui", flush=True)


if __name__ == "__main__":
    mode, out = sys.argv[1], os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    if mode == "vues":
        vues(out, sys.argv[3], [os.path.abspath(e) for e in sys.argv[4:]])
    else:
        {"descente": descente, "tour": tour}[mode](out, sys.argv[3], sys.argv[4], [os.path.abspath(e) for e in sys.argv[5:]])
