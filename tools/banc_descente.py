# Descent bench (docs/spec-rendu-lointain.md): the same patch of ground, straight down, from high to low. The
# share of each material within it should not change with the height: a flat curve is a stable rendering, a wave is a
# mutation. The engine runs in its diagnostic views (MYPLANETENGINE_VIEW): each pixel white with the probability
# of the material's weight, so the share of white pixels is the material's mean share. One batch run renders every
# height and every view (MYPLANETENGINE_BATCH).
#
# python tools/banc_descente.py <exe> <out.png> <latitude> <longitude> <patch width in km> [heights in km ...]
# Heights count from the ground under the patch's centre. BANC_MATERIAU picks the views, comma-separated: snow (default),
# rock, elevation (over 6 km), spread (the slope spread), scree, grass, sand, beach, wet (the green of humid lands), sea
# or rockall (the rock, its covered ledges included). The views give each material's weight before the layers cover each
# other; with snow, rock, scree, grass and sand all measured, the shares seen are added, as banc_qualite.py lays them.
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_qualite

FOV_Y, HEIGHT_PX, WIDTH_PX = np.radians(60.0), 720, 1280
MATERIALS = os.environ.get("BANC_MATERIAU", "snow").split(",")


def run(exe, jobs, path, sun="10 70"):
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=sun, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE"):
        env.pop(k, None)
    subprocess.run([exe], env=env, timeout=1800)


def weights(img):
    # The view's weight per pixel: its white, averaged over 9 pixels, so that two views' weights can be multiplied.
    return np.asarray(img.convert("L").filter(ImageFilter.BoxBlur(4)), np.float32) / 255.0


def descent(exe, scratch, lat, lon, width, heights):
    # Shares per height: {height: {material: share}}, and the crops, for the sheet.
    os.makedirs(scratch, exist_ok=True)
    jobs = [(os.path.join(scratch, f"{m}_{h:.0f}.bmp"), m, h, lat, lon, 89.9, 0.0) for h in heights for m in MATERIALS]
    run(exe, jobs, os.path.join(scratch, "jobs.txt"))
    shares, crops = {}, {}
    for h in heights:
        metres_per_px = h * 2.0 * np.tan(FOV_Y / 2.0) / HEIGHT_PX  # at the nadir
        half = min(int(0.5 * width / metres_per_px), HEIGHT_PX // 2)
        box = (WIDTH_PX // 2 - half, HEIGHT_PX // 2 - half, WIDTH_PX // 2 + half, HEIGHT_PX // 2 + half)
        row, w = {}, {}
        for m in MATERIALS:
            path = os.path.join(scratch, f"{m}_{h:.0f}.bmp")
            if not os.path.exists(path):
                continue
            crop = Image.open(path).crop(box)
            row[m] = float((np.asarray(crop.convert("L"), np.float32) > 127.0).mean())
            w[m] = weights(crop)
            crops.setdefault(h, []).append(crop)
            os.remove(path)
        if all(m in w for m in ("snow", "rock", "scree", "grass", "sand")):
            row.update({f"{m} vu": float(v.mean()) for m, v in banc_qualite.visible(w).items() if m != "sea"})
        shares[h] = row
    return shares, crops


if __name__ == "__main__":
    exe, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    lat, lon, width = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]) * 1000.0
    heights = [float(h) * 1000.0 for h in sys.argv[6:]] or [1500e3, 800e3, 400e3, 200e3, 130e3, 90e3, 60e3]
    shares, crops = descent(exe, os.path.join(os.path.dirname(out), "banc_descente"), lat, lon, width, heights)
    names = list(next(iter(shares.values())).keys())
    print("| hauteur | " + " | ".join(names) + " |")
    print("|---|" + "---|" * len(names))
    for h in heights:
        print(f"| {h / 1000:g} km | " + " | ".join(f"{100 * shares[h].get(m, float('nan')):.1f} %" for m in names) + " |", flush=True)
    tile = 192
    sheet = Image.new("RGB", (tile * len(heights), tile * len(MATERIALS) + 20), "white")
    d = ImageDraw.Draw(sheet)
    for i, h in enumerate(heights):
        d.text((i * tile + 4, 4), f"{h / 1000:g} km", fill="black")
        for k, crop in enumerate(crops.get(h, [])):
            sheet.paste(crop.convert("RGB").resize((tile, tile)), (i * tile, 20 + k * tile))
    sheet.save(out)
    print(out)
