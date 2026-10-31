# Test bench: every view of a tests file (the format of tools/lance.ps1: "label | altitude latitude longitude pitch
# heading [| sunLatitude sunLongitude]"), captured hidden with each exe, side by side in one sheet, with the GPU times of
# each capture. To compare builds on the views judged in flight.
#
# python tools/banc_tests.py <tests.txt> <out folder> <exe> [exe ...]
import os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

CAPTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture.ps1")


def tests(path):
    for line in open(path, encoding="utf-8-sig"):
        fields = [f.strip() for f in line.split("|")]
        if line.startswith("#") or len(fields) < 2:
            continue
        yield fields[0], fields[1], fields[2] if len(fields) > 2 else ""


def capture(exe, args, sun, png):
    env = dict(os.environ, MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1", **({"MYPLANETENGINE_SUN": sun} if sun else {}))
    out = subprocess.run(["powershell", "-NoProfile", "-File", CAPTURE, "-Out", png, "-AppArgs", args, "-Exe", exe],
                         env=env, capture_output=True, text=True, timeout=180).stdout.strip()
    title = out.splitlines()[-1] if out else ""
    m = re.search(r"calcul ([\d.]+) ms(?: \([^)]*\))?, rendu ([\d.]+) ms", title)
    return (float(m.group(1)), float(m.group(2))) if m else (float("nan"), float("nan"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    path, out, exes = sys.argv[1], os.path.abspath(sys.argv[2]), [os.path.abspath(e) for e in sys.argv[3:]]
    os.makedirs(out, exist_ok=True)
    rows = []
    for k, (label, args, sun) in enumerate(tests(path)):
        row = []
        for exe in exes:
            name = os.path.basename(os.path.dirname(exe))
            png = os.path.join(out, f"{k:02d}_{name}.png")
            compute, draw = capture(exe, args, sun, png)
            print(f"{k:02d} {name:>14} | calcul {compute:5.1f} ms, rendu {draw:5.2f} ms | {label}", flush=True)
            row.append((png, f"{name} : {label}"))
        rows.append(row)
    w, h = 640, 360
    sheet = Image.new("RGB", (w * len(exes), h * len(rows)), "black")
    draw, font = ImageDraw.Draw(sheet), ImageFont.truetype("arial.ttf", 15)
    for j, row in enumerate(rows):
        for i, (png, text) in enumerate(row):
            if os.path.exists(png):
                sheet.paste(Image.open(png).convert("RGB").resize((w, h)), (i * w, j * h))
            draw.text((i * w + 6, j * h + 4), text, fill="white", font=font)
    sheet.save(os.path.join(out, "planche.png"))
