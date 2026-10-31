# Hybrid trial bench (docs/log/spec-hybride-scans.md): the same views from several builds, side by side in one sheet, each
# with its GPU time. The close views first, then the repetition views: sand, and the scree under the ledge view, at 2,
# 10 and 50 m above their ground, where a scan's pattern would show despite the stochastic tiling.
#
# python tools/banc_hybride.py <out.png> <exe> [exe ...]
import os, re, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_visuel

VIEWS = {  # name: "altitude latitude longitude pitch heading", the engine's own arguments
    "constat": "1391.1 -11.04542 50.06777 2.6 55.3",
    "corniche": "2182.0 31.16045 8.58814 1.9 -17.1",
    "roche rouge": "586.6 -25.21899 135.73187 -0.2 92.0",
}
REPEAT = [(2.0, 30), (10.0, 45), (50.0, 60)]  # m above the ground, pitch down (degrees)
REPEAT_SITES = {"sable": (26.0, 45.0, "20 110", 0.0), "eboulis": (31.16045, 8.58814, None, -17.1)}  # lat, lon, sun, heading

if __name__ == "__main__":
    sheet, exes = os.path.abspath(sys.argv[1]), [os.path.abspath(e) for e in sys.argv[2:]]
    scratch = os.path.join(os.path.dirname(sheet), "banc_hybride")
    os.makedirs(scratch, exist_ok=True)
    rows = [(name, args, None) for name, args in VIEWS.items()]
    for site, (lat, lon, sun, heading) in REPEAT_SITES.items():
        g = banc_visuel.ground(exes[0], lat, lon, sun, scratch)  # the first build's ground, the same camera for all
        rows += [(f"{site} {h:g} m", f"{g + h:.1f} {lat} {lon} {pitch} {heading}", sun) for h, pitch in REPEAT]
    w, h, top = 640, 360, 22
    img = Image.new("RGB", (w * len(exes), (h + top) * len(rows)), "white")
    d = ImageDraw.Draw(img)
    for row, (name, args, sun) in enumerate(rows):
        for col, exe in enumerate(exes):
            png = os.path.join(scratch, f"{row}_{col}.png")
            title = banc_visuel.capture(exe, args, sun, png)
            gpu = re.search(r"rendu ([\d.]+) ms", title)
            build = os.path.basename(os.path.dirname(exe))
            d.text((col * w + 6, row * (h + top) + 4), f"{name} | {build} | rendu {gpu.group(1) if gpu else '?'} ms", fill="black")
            img.paste(Image.open(png).convert("RGB").resize((w, h)), (col * w, row * (h + top) + top))
        print(name, flush=True)
    img.save(sheet)
    print(sheet)
