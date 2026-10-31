# Ridge bench: crests at eye level, 1.3 m above the ground, looking level, for several builds side by side.
# Spikes and saw teeth of the material relief show on the skyline (docs/spec-rendu-lointain.md).
#
# python tools/banc_cretes.py <out.png> <exe> [exe ...]
import os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_visuel

# latitude, longitude, pitch down (degrees): rocky crests, snowy and dry
POINTS = [(-14.9655, 119.994, -2), (-14.9600, 119.990, 0), (-24.3, 129.75, -3), (-24.31, 129.76, 0)]

if __name__ == "__main__":
    sheet, exes = os.path.abspath(sys.argv[1]), [os.path.abspath(e) for e in sys.argv[2:]]
    scratch = os.path.join(os.path.dirname(sheet), "banc_cretes")
    os.makedirs(scratch, exist_ok=True)
    w, h = 480, 270
    img = Image.new("RGB", (w * len(exes), (h + 20) * len(POINTS)), "white")
    d = ImageDraw.Draw(img)
    for r, (lat, lon, pitch) in enumerate(POINTS):
        g = banc_visuel.ground(exes[0], lat, lon, "10 70", scratch)
        for c, exe in enumerate(exes):
            png = os.path.join(scratch, f"{r}_{c}.png")
            for attempt in range(2):
                if os.path.exists(png):
                    os.remove(png)
                banc_visuel.capture(exe, f"{g + 1.3:.1f} {lat} {lon} {pitch}", "10 70", png)
                if os.path.exists(png):
                    break
            name = os.path.basename(os.path.dirname(exe))
            d.text((c * w + 6, r * (h + 20) + 4), f"{name} {lat} {lon}", fill="black")
            if os.path.exists(png):
                img.paste(Image.open(png).convert("RGB").resize((w, h)), (c * w, r * (h + 20) + 20))
        print(lat, lon, f"sol {g:.0f} m", flush=True)
    img.save(sheet)
    print(sheet)
