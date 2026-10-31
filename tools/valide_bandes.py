# The validator of the materials' scale bands (docs/spec-texturage-universel.md, step 2). Two checks:
# - declared: tools/bandes_materiaux.json, the bands each material is drawn with, read from the code; every octave from
#   1 mm to 2 km must hold a source of colour, at a strength that shows;
# - measured: the engine looks straight down from 1.5 m to 6 km over places picked by material (banc_qualite.py's
#   picking); rock and scree, which keep to slopes, are looked at 45 degrees down towards where they show most, a
#   pixel's size on the ground then taken as its distance along the flat ground's ray, row by row (walls facing the
#   camera foreshorten little); each height shows five octaves, 2 to 64 pixels, of a known size; the contrast of each octave
#   (the deviation of the log of the light, in dB) is gathered by material and octave of the world, next to the same
#   measure on the photo scans of ../scans, whose real widths are known (their albedo only: no sun on them).
#
# python tools/valide_bandes.py <exe> <out folder> [--sites 15] [--seed 2]
# python tools/valide_bandes.py --declared       the declared check alone
import argparse, json, math, os, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import banc_qualite as bq

HEIGHTS = [1.5, 6.0, 24.0, 96.0, 384.0, 1536.0, 6144.0]  # m above the ground, straight down
FOOTPRINT = 2.0 * math.tan(math.radians(30.0)) / 720.0   # m per pixel per m of height, at the centre
BANDS = ((2, 4), (4, 8), (8, 16), (16, 32), (32, 64))    # pixels
OCTAVES = range(-9, 12)                                  # log2 of the wavelength (m): 2 mm, two 1 mm texels, to 2 km
VIEW = {"sable": "sand", "herbe": "grass", "sol nu": "soil", "eboulis": "scree", "roche": "rock", "neige": "snow"}  # rock: with its ledges
SCANS = {"sand": [("sandy_gravel_02", 2.53), ("aerial_sand", 15.0), ("aerial_beach_01", 30.0)], "soil": [("sandy_gravel_02", 2.53)],
         "rock": [("dark_rock_02", 2.0), ("cliff_side", 1.83), ("marble_cliff_04", 12.7), ("marble_cliff_05", 20.0)],
         "scree": [("gray_rocks", 1.8)], "snow": [("snow_02", 2.0), ("snow_field_aerial", 80.0)]}
WEAK = 0.1  # a band whose gain leaves it under this share of its widest octave's strength does not show


def octave_variance(tile):
    # The variance of each pixel octave of a tile of the log of the light, Hann window.
    n = tile.shape[0]
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    x = (tile - tile.mean()) * w
    spectrum = np.abs(np.fft.fft2(x)) ** 2 / (n * n * (w * w).sum())
    f = np.hypot(*np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n)))
    return [float(spectrum[(f > 1.0 / hi) & (f <= 1.0 / lo)].sum()) for lo, hi in BANDS]


def log_light(img):
    return np.log(bq.luminance(img) + 0.01)


def world_octave(lo, hi, metres_per_pixel):
    return int(round(math.log2(math.sqrt(lo * hi) * metres_per_pixel)))


def declared(data):
    # Per material, per octave: the sources of colour that show, and those of light.
    out = {}
    for name, bands in data["materiaux"].items():
        rows = {}
        for k in OCTAVES:
            lam = 2.0 ** (k + 0.5)
            colour, light = [], []
            for b in bands + [c for c in data["communes"] if name not in c.get("sauf", [])]:
                lo, hi = b["lambda"]
                if not lo <= lam <= hi:
                    continue
                strength = b.get("gain", 1.0) ** math.log2(hi / lam) if "gain" in b else 1.0
                if strength < WEAK:
                    continue
                (colour if "couleur" in b["porte"] else light).append(b["nom"])
            rows[k] = {"couleur": colour, "lumiere": light}
        out[name] = rows
    return out


def declared_report(dec):
    lines = ["## Couverture déclarée", "", "Octave par octave, de 1 mm à 2 km : `C` une source de couleur, `l` de la lumière seule, `·` rien.", ""]
    head = "| matériau | " + " | ".join(f"{fmt(2.0 ** k)}" for k in OCTAVES) + " |"
    lines += [head, "|" + "---|" * (len(OCTAVES) + 1)]
    for name, rows in dec.items():
        cells = ["C" if rows[k]["couleur"] else ("l" if rows[k]["lumiere"] else "·") for k in OCTAVES]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    for name, rows in dec.items():
        holes = [k for k in OCTAVES if not rows[k]["couleur"]]
        if holes:
            lines.append(f"- **{name} :** sans couleur de {fmt(2.0 ** spans(holes)[0][0])} à {fmt(2.0 ** (spans(holes)[0][1] + 1))}"
                         + "".join(f", de {fmt(2.0 ** a)} à {fmt(2.0 ** (b + 1))}" for a, b in spans(holes)[1:]) + ".")
    return lines


def spans(ks):
    out = []
    for k in ks:
        if out and k == out[-1][1] + 1:
            out[-1][1] = k
        else:
            out.append([k, k])
    return out


def fmt(m):
    return f"{m * 1000:.0f} mm" if m < 0.01 else (f"{m * 100:.0f} cm" if m < 1.0 else (f"{m:.0f} m" if m < 1000.0 else f"{m / 1000:.0f} km"))


def measure(exe, out, n, seed, only=None):
    work = os.path.join(out, "travail")
    os.makedirs(work, exist_ok=True)
    land = [site for site in bq.pick_sites(exe, work, n, seed) if only is None or site[3] == only]
    found = {}  # (view material, octave) -> [dB]
    for s, (lat, lon, heading, target) in enumerate(land):
        best = []
        sun = f"{max(min(lat - 20.0, 60.0), -60.0):.2f} {lon + 35.0:.2f}"
        jobs = []
        pitch = 45.0 if target in ("rock", "scree") else 89.9
        for h in HEIGHTS:
            jobs.append((os.path.join(work, f"c{h:g}.bmp"), "-", h, lat, lon, pitch, heading))
            jobs += [(os.path.join(work, f"{m}{h:g}.bmp"), m, h, lat, lon, pitch, heading) for m in bq.VIEWS + ["sea", "rockall"]]
        bq.run(exe, jobs, os.path.join(work, "jobs.txt"), sun)
        for h in HEIGHTS:
            colour = cv2.imread(os.path.join(work, f"c{h:g}.bmp"))
            masks = {m: cv2.imread(os.path.join(work, f"{m}{h:g}.bmp")) for m in bq.VIEWS + ["sea", "rockall"]}
            if colour is None or any(v is None for v in masks.values()):
                continue
            weights = bq.visible({m: bq.weight(v) for m, v in masks.items()})
            # A wall as it is seen: its rock with the ledges that break it, scree and soil on them (the rock view leaves
            # them out, and the rock seldom covers 70 % of a crop without them).
            weights["rock"] = weights["rockall"] * (1.0 - weights["snow"])
            best.append(f"{h:g} m {float(weights[target][256:].max()):.2f}")
            light = log_light(colour)
            # Straight down, the centre's crops, where a pixel's size on the ground is about FOOTPRINT * h; at 45
            # degrees, the lower rows, each at its distance along its ray.
            rows = range(168, 552 - bq.TILE + 1, bq.TILE) if pitch > 80.0 else range(256, 720 - bq.TILE + 1, bq.TILE)
            cols = range(320, 960 - bq.TILE + 1, bq.TILE) if pitch > 80.0 else range(0, 1280 - bq.TILE + 1, bq.TILE)
            for y in rows:
                below = math.radians(pitch + (y + bq.TILE / 2 - 360) * 60.0 / 720.0)
                mpp = FOOTPRINT * h / math.sin(min(below, math.pi / 2))
                for x in cols:
                    if weights["sea"][y:y + bq.TILE, x:x + bq.TILE].mean() > 0.05:
                        continue
                    shares = {m: float(weights[m][y:y + bq.TILE, x:x + bq.TILE].mean()) for m in bq.MATERIALS}
                    m = max(shares, key=shares.get)
                    if shares[m] < bq.CROP_SHARE:
                        continue
                    for (lo, hi), v in zip(BANDS, octave_variance(light[y:y + bq.TILE, x:x + bq.TILE])):
                        found.setdefault((m, world_octave(lo, hi, mpp)), []).append(10 * math.log10(v + 1e-12))
        for f in os.listdir(work):
            if f.endswith(".bmp"):
                os.remove(os.path.join(work, f))
        print(f"site {s + 1}/{len(land)} ({target}) {lat:.3f} {lon:.3f} cap {heading:g} ; part visible maximale : "
              + ", ".join(best), flush=True)
    return {f"{m}|{k}": v for (m, k), v in found.items()}


def scans():
    folder = os.path.join(HERE, "..", "..", "scans")
    found = {}
    rng = np.random.default_rng(0)
    for m, items in SCANS.items():
        for name, width in items:
            path = os.path.join(folder, name, f"{name}_diff_2k.jpg")
            if not os.path.exists(path):
                continue
            img = cv2.imread(path)
            for k in range(6):
                scaled = cv2.resize(img, (img.shape[1] >> k, img.shape[0] >> k), interpolation=cv2.INTER_AREA) if k else img
                light = log_light(scaled)
                mpp = width / scaled.shape[1]
                for _ in range(8 if scaled.shape[0] > 2 * bq.TILE else 2):
                    if scaled.shape[0] < bq.TILE:
                        break
                    y, x = (int(v) for v in rng.integers(0, scaled.shape[0] - bq.TILE + 1, 2))
                    for (lo, hi), v in zip(BANDS, octave_variance(light[y:y + bq.TILE, x:x + bq.TILE])):
                        found.setdefault(f"{m}|{world_octave(lo, hi, mpp)}", []).append(10 * math.log10(v + 1e-12))
    return found


def chart(dec, measured, reference, data, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(data["materiaux"])
    fig, axes = plt.subplots(len(names), 1, figsize=(11, 2.6 * len(names)), sharex=True)
    for ax, name in zip(axes, names):
        m = VIEW[name]
        xs = [k for k in OCTAVES if f"{m}|{k}" in measured and len(measured[f"{m}|{k}"]) >= 3]
        ax.plot([2.0 ** (k + 0.5) for k in xs], [np.median(measured[f"{m}|{k}"]) for k in xs], "o-", color="C0", label="rendu, médiane")
        ax.fill_between([2.0 ** (k + 0.5) for k in xs], [np.percentile(measured[f"{m}|{k}"], 25) for k in xs],
                        [np.percentile(measured[f"{m}|{k}"], 75) for k in xs], color="C0", alpha=0.2)
        rs = [k for k in OCTAVES if f"{m}|{k}" in reference]
        if rs:
            ax.plot([2.0 ** (k + 0.5) for k in rs], [np.median(reference[f"{m}|{k}"]) for k in rs], "s--", color="C3", label="scans réels (albédo)")
        lo, hi = ax.get_ylim() if xs or rs else (-60, -10)
        for k in OCTAVES:
            if not dec[name][k]["couleur"]:
                ax.axvspan(2.0 ** k, 2.0 ** (k + 1), color="0.85", zorder=0)
        ax.set_xscale("log")
        ax.set_ylabel("contraste (dB)")
        ax.set_title(f"{name} : déclaré en gris là où aucune couleur ne montre ; mesuré par la vue « {m} »", fontsize=9, loc="left")
        ax.legend(fontsize=7, loc="lower right")
        ax.grid(True, which="both", alpha=0.3)
    axes[-1].set_xlabel("longueur d'onde au sol (m)")
    axes[-1].set_xlim(1e-3, 2e3)
    fig.tight_layout()
    fig.savefig(path, dpi=90)


def measured_report(measured, reference, data):
    lines = ["## Contraste mesuré, médiane en dB par octave", "",
             "Rendu ; entre parenthèses, les scans réels du même matériau quand il y en a.", ""]
    head = "| vue | " + " | ".join(fmt(2.0 ** k) for k in OCTAVES) + " |"
    lines += [head, "|" + "---|" * (len(OCTAVES) + 1)]
    for m in bq.MATERIALS:
        cells = []
        for k in OCTAVES:
            v = measured.get(f"{m}|{k}", [])
            r = reference.get(f"{m}|{k}", [])
            cell = f"{np.median(v):.0f}" if len(v) >= 3 else "·"
            if r:
                cell += f" ({np.median(r):.0f})"
            cells.append(cell)
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    return lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--sites", type=int, default=15); ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--declared", action="store_true")
    ap.add_argument("--only", help="the places picked for this view's material only (rock, sand, grass, snow, scree)")
    a = ap.parse_args()
    data = json.load(open(os.path.join(HERE, "bandes_materiaux.json"), encoding="utf-8"))
    dec = declared(data)
    lines = declared_report(dec)
    if not a.declared:
        out = os.path.abspath(a.out)
        os.makedirs(out, exist_ok=True)
        measured = measure(os.path.abspath(a.exe), out, a.sites, a.seed, a.only)
        reference = scans()
        json.dump({"rendu": measured, "scans": reference}, open(os.path.join(out, "spectre.json"), "w"))
        lines += [""] + measured_report(measured, reference, data)
        chart(dec, measured, reference, data, os.path.join(out, "spectre.png"))
        open(os.path.join(out, "bandes.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
