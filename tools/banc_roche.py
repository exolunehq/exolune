# Rock bench (docs/spec-roche-organique.md): the view of the finding, at its exact position, then mountain sites
# at 100 m, 500 m and 2 km above their ground, each next to the reference photo of the rock it should evoke.
#
# python tools/banc_roche.py <exe> <out.png> [site ...]
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_visuel

FINDING = "1391.1 -11.04542 50.06777 2.6 55.3"  # the wall seen from 150 m, default sun
# name: (latitude, longitude, heading, sun, reference image)
SITES = {
    "constat": None,
    "canyon": (-11.045, 50.068, 55, "10 70", "cible-falaise-alcoves.jpg"),  # bedded
    "sec": (-20.0, 125.0, 0, "10 70", "cible-plis.jpg"),  # bedded, dry
    "basalte": (-14.9635, 119.991, 0, "-5 150", "cible-basalte.jpg"),  # flows
    "granite": (-19.7, 124.6, 0, "10 70", "cible-granite.jpg"),  # massive
    "badlands": (-20.3, 125.4, 0, "10 70", "cible-badlands.jpg"),  # soft
}
HEIGHTS = [(100.0, 10), (500.0, 15), (2000.0, 20)]  # m above the ground, pitch down (degrees)

if __name__ == "__main__":
    exe, sheet = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    names = sys.argv[3:] or list(SITES)
    scratch = os.path.join(os.path.dirname(sheet), "banc_roche")
    os.makedirs(scratch, exist_ok=True)
    w, h, top = 480, 270, 22
    img = Image.new("RGB", (w * (len(HEIGHTS) + 1), (h + top) * len(names)), "white")
    d = ImageDraw.Draw(img)
    for row, name in enumerate(names):
        y = row * (h + top)
        if SITES[name] is None:
            reference, shots = "cible-plis.jpg", [("constat", FINDING, None)]
        else:
            lat, lon, heading, sun, reference = SITES[name]
            g = banc_visuel.ground(exe, lat, lon, sun, scratch)
            shots = [(f"{height:g} m", f"{g + height:.1f} {lat} {lon} {pitch} {heading}", sun) for height, pitch in HEIGHTS]
        d.text((6, y + 4), f"{name} : {reference}", fill="black")
        img.paste(Image.open(os.path.join(banc_visuel.DOCS, reference)).convert("RGB").resize((w, h)), (0, y + top))
        for col, (label, args, sun) in enumerate(shots, start=1):
            png = os.path.join(scratch, f"{name}_{col}.png")
            title = banc_visuel.capture(exe, args, sun, png)
            gpu = banc_visuel.re.search(r"rendu ([\d.]+) ms", title)
            d.text((col * w + 6, y + 4), f"{label}, rendu {gpu.group(1) if gpu else '?'} ms", fill="black")
            if os.path.exists(png):
                img.paste(Image.open(png).convert("RGB").resize((w, h)), (col * w, y + top))
        print(name, flush=True)
    img.save(sheet)
    print(sheet)
