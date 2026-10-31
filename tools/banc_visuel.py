# Visual bench: each site captured at several heights above its ground, next to the reference image it aims
# at, in one sheet. For fast iterations on close-up detail (docs/spec-textures-generees.md).
#
# python tools/banc_visuel.py <exe> <out.png> [site ...]
# The ground height of each site is probed first, so that every capture is at its height above the ground.
import os, re, subprocess, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs", "images")
CAPTURE = os.path.join(HERE, "capture.ps1")

# name: (latitude, longitude, sun "latitude longitude", reference image or None)
SITES = {
    "desert": (26.0, 45.0, "20 110", "cible-desert.jpg"),
    "roche": (-14.9635, 119.991, "-5 150", "cible-cote.jpg"),
    "herbe": (-15.0, 50.0, "10 70", None),
}
HEIGHTS = [(1.5, 8), (10.0, 12), (100.0, 15), (1000.0, 20)]  # m above the ground, pitch down (degrees)


def capture(exe, args, sun, png):
    out = subprocess.run(["powershell", "-NoProfile", "-File", CAPTURE, "-Out", png, "-AppArgs", args, "-Exe", exe],
                         env=dict(os.environ, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1", **({"MYPLANETENGINE_SUN": sun} if sun else {})), capture_output=True, text=True, timeout=120).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def clearance(title):
    m = re.search(r"hauteur ([\d.]+) (k?m)", title)
    return float(m.group(1)) * (1000.0 if m.group(2) == "km" else 1.0)


def probe(exe, args, sun, png):
    # The height above the ground in the title; a capture that ends before its title shows is run again.
    for attempt in range(3):
        title = capture(exe, args, sun, png)
        if re.search(r"hauteur ([\d.]+) (k?m)", title):
            return clearance(title)
    raise RuntimeError(f"no height in the title: {title!r}")


def ground(exe, lat, lon, sun, scratch):
    # From high up, the ground to 0.1 km; then from 300 m above that, to the metre.
    png = os.path.join(scratch, "probe.png")
    rough = 20000.0 - probe(exe, f"20000 {lat} {lon} 60", sun, png)
    return rough + 300.0 - probe(exe, f"{rough + 300.0:.1f} {lat} {lon} 60", sun, png)


if __name__ == "__main__":
    exe, sheet = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    names = sys.argv[3:] or list(SITES)
    scratch = os.path.join(os.path.dirname(sheet), "banc_visuel")
    os.makedirs(scratch, exist_ok=True)
    w, h, top = 480, 270, 22
    img = Image.new("RGB", (w * (len(HEIGHTS) + 1), (h + top) * len(names)), "white")
    d = ImageDraw.Draw(img)
    for row, name in enumerate(names):
        lat, lon, sun, reference = SITES[name]
        g = ground(exe, lat, lon, sun, scratch)
        y = row * (h + top)
        d.text((6, y + 4), f"{name}, sol {g:.0f} m : reference", fill="black")
        if reference:
            img.paste(Image.open(os.path.join(DOCS, reference)).convert("RGB").resize((w, h)), (0, y + top))
        for col, (height, pitch) in enumerate(HEIGHTS, start=1):
            png = os.path.join(scratch, f"{name}_{height:g}m.png")
            title = capture(exe, f"{g + height:.1f} {lat} {lon} {pitch}", sun, png)
            gpu = re.search(r"rendu ([\d.]+) ms", title)
            d.text((col * w + 6, y + 4), f"{height:g} m, rendu {gpu.group(1) if gpu else '?'} ms", fill="black")
            img.paste(Image.open(png).convert("RGB").resize((w, h)), (col * w, y + top))
        print(name, f"sol {g:.1f} m", flush=True)
    img.save(sheet)
    print(sheet)
