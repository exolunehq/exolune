# Shadow descent bench (docs/recherche-ombres-relief.md): the same ground, straight down, from high to low, at a low
# sun. Each height sees the ground the next one, lower, sees whole: the sunlight on it must keep its mean and its
# shapes. A mean that jumps, or shapes that do not match, is a popping shadow.
#
# python tools/banc_ombres.py <exe> <out.png> <latitude> <longitude> <sun elevation> <sun azimuth> [heights in km ...]
# Heights count from the ground under the camera. The engine runs its colour view, then its "sun" view
# (MYPLANETENGINE_VIEW): each pixel white with the probability of the direct sunlight's factor, N.L times the share the
# relief leaves. The mean light on rough ground is the macro surface's, however fine the relief drawn (Smith): it must
# not change with the height. Per pair of heights, on the lower view's ground: the mean of that factor in each, and
# the correlation of their maps of it, both brought to the higher view's pixels.
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_visuel

FOV_Y, HEIGHT_PX, WIDTH_PX = math.radians(60.0), 720, 1280


def subsolar(lat, lon, elevation, azimuth):
    # The point under the sun when it stands `elevation` degrees high toward `azimuth` (degrees east of north).
    d, p1, l1, b = math.radians(90.0 - elevation), math.radians(lat), math.radians(lon), math.radians(azimuth)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0


def light(png):
    return np.asarray(Image.open(png).convert("L"), np.float32) / 255.0


if __name__ == "__main__":
    exe, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    lat, lon, elevation, azimuth = (float(x) for x in sys.argv[3:7])
    heights = [float(h) * 1000.0 for h in sys.argv[7:]] or [50e3, 20e3, 8e3, 3e3, 1.2e3, 500.0, 200.0]
    sun = "%.4f %.4f" % subsolar(lat, lon, elevation, azimuth)
    scratch = os.path.join(os.path.dirname(out), "banc_ombres")
    os.makedirs(scratch, exist_ok=True)
    os.environ.pop("MYPLANETENGINE_VIEW", None)
    ground = max(banc_visuel.ground(exe, lat, lon, sun, scratch), 0.0)
    colour, shadow = [], []
    for h in heights:
        args = f"{ground + h:.1f} {lat} {lon} 89.9 0"
        for view, images in (("", colour), ("sun", shadow)):
            png = os.path.join(scratch, f"{view or 'colour'}_{h:g}m.png")
            if view:
                os.environ["MYPLANETENGINE_VIEW"] = view
            title = banc_visuel.capture(exe, args, sun, png)
            os.environ.pop("MYPLANETENGINE_VIEW", None)
            images.append(png)
        print(f"{h:g} m | {title[title.find('GPU'):][:34]}", flush=True)

    tile, top = 320, 36
    sheet = Image.new("RGB", (tile * len(heights), 2 * tile + top), "white")
    d = ImageDraw.Draw(sheet)
    report = []
    for i, h in enumerate(heights):
        img = Image.open(colour[i]).convert("RGB").crop(((WIDTH_PX - HEIGHT_PX) // 2, 0, (WIDTH_PX + HEIGHT_PX) // 2, HEIGHT_PX))
        sheet.paste(img.resize((tile, tile)), (i * tile, top))
        sheet.paste(Image.open(shadow[i]).convert("RGB").crop(((WIDTH_PX - HEIGHT_PX) // 2, 0, (WIDTH_PX + HEIGHT_PX) // 2, HEIGHT_PX))
                    .resize((tile, tile)), (i * tile, top + tile))
        line = f"{h / 1000:g} km"
        if i + 1 < len(heights):
            # The lower view's ground in this one: the same angles, shrunk by the ratio of heights.
            f = heights[i + 1] / h
            ch, cw = HEIGHT_PX * f, WIDTH_PX * f
            box = (int(round((WIDTH_PX - cw) / 2)), int(round((HEIGHT_PX - ch) / 2)), int(round((WIDTH_PX + cw) / 2)), int(round((HEIGHT_PX + ch) / 2)))
            hi = light(shadow[i])[box[1]:box[3], box[0]:box[2]]
            lo = light(shadow[i + 1])
            # Both on one grid, cells of 4 pixels of the higher view: the dithered view's share, averaged.
            grid = (max(hi.shape[1] // 4, 1), max(hi.shape[0] // 4, 1))
            a, b = (np.asarray(Image.fromarray(x).resize(grid, Image.BOX)) for x in (hi, lo))
            corr = float(np.corrcoef(a.ravel(), b.ravel())[0, 1]) if a.std() > 0 and b.std() > 0 else float("nan")
            report.append((h, heights[i + 1], float(hi.mean()), float(lo.mean()), corr))
            s = (tile / HEIGHT_PX)
            x0 = i * tile + (box[0] - (WIDTH_PX - HEIGHT_PX) / 2) * s
            d.rectangle((x0, top + box[1] * s, x0 + (box[2] - box[0]) * s, top + box[3] * s), outline="yellow")
            line += f" | soleil {100 * hi.mean():.1f} -> {100 * lo.mean():.1f} %, corr {corr:.2f}"
        d.text((i * tile + 4, 4), line, fill="black")
    for h, h2, a, b, c in report:
        print(f"{h / 1000:g} -> {h2 / 1000:g} km | lumière directe {100 * a:.2f} -> {100 * b:.2f} % | correlation {c:.2f}")
    sheet.save(out)
    print(out)
