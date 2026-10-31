# Glare bench (docs/recherche-halo.md): the halo the engine adds, measured on its own captures, rendered hidden.
#
# python tools/banc_halo.py <exe> <out folder>
#
# 1. The sun from 2 000 km, in front of black space: no air, illuminance E = pi, so the image is the glare alone.
#    Its radial profile, in linear light, against the law it is built on, L = s E / theta^2, and against the young
#    eye's, the CIE general disability glare equation (Vos 2003, CIE 146:2002).
# 2. The sun in the air, low and high: the light added, on (MYPLANETENGINE_GLARE) - (1 - W) off, by angle from the
#    sun, and the net change against the sky and ground without glare.
# 3. A snowfield, the sun behind: the light added next to it, by distance from its edge, against the law convolved
#    with the image without glare.
# Linear light is read back from the captures: sRGB decoded, the tone curve's shoulder undone (ToneMap.hlsl, identity
# below 0.76); pixels near white are left out.
import os, re, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FOV_Y = 60.0  # degrees, D3DApp
# The straylight s, read from the settings (PlanetSettings.hlsli, GLARE_STRAYLIGHT).
S = float(re.search(r"GLARE_STRAYLIGHT\s*=\s*([\d.]+)", open(os.path.join(HERE, "..", "MyPlanetEngine",
                                                                       "PlanetSettings.hlsli")).read()).group(1))
EDGES = np.array([2, 3, 4, 6, 8, 12, 16, 24, 32])  # rings, degrees
MIDS = np.sqrt(EDGES[:-1] * EDGES[1:])
SUN = [  # name, engine arguments, subsolar point
    ("soleil_orbite", "2000000 0 0 0 90", "0 90"),
    ("soleil_bas", "800 26.0 45.0 -2 110", "-15.547 121.329"),
    ("soleil_haut", "1941.7 0.00280 118.14145 -20 156.6", "-50.0 140.0"),
]
SNOW = ("neige", "6561.8 -18.67002 131.64981 9.8 -117.1", "10 70")


def capture(exe, args, sun, png, glare):
    env = dict(os.environ, MYPLANETENGINE_SUN=sun, MYPLANETENGINE_TAA="1")
    env.pop("MYPLANETENGINE_GLARE", None)
    if glare:
        env["MYPLANETENGINE_GLARE"] = "1"
    subprocess.run(["powershell", "-NoProfile", "-File", os.path.join(HERE, "capture.ps1"), "-Out", png,
                    "-AppArgs", args, "-Exe", exe], env=env, capture_output=True, text=True, timeout=180)


def linear(png):
    """The brightest channel in linear light, and whether it can be read back (not near white). The glare is grey:
    it adds to that channel as it is."""
    c = np.asarray(Image.open(png).convert("RGB")).astype(np.float64).max(axis=2) / 255.0
    readable = c < 0.97
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    start, d = 0.76, 0.24  # ToneMap.hlsl, CompressHighlights, its peak undone
    return np.where(c < start, c, d * d / np.maximum(1.0 - c, 1e-4) - d + start), readable


def angles(shape, centre):
    """Angle (degrees) of each pixel from the direction of `centre`, through the perspective projection."""
    h, w = shape
    f = (h / 2) / np.tan(np.radians(FOV_Y / 2))
    y, x = np.mgrid[0:h, 0:w] + 0.5
    v = np.stack([x - w / 2, y - h / 2, np.full(x.shape, f)], axis=-1)
    c = np.array([centre[0] - w / 2, centre[1] - h / 2, f])
    cos = (v @ c) / np.linalg.norm(v, axis=-1) / np.linalg.norm(c)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def cie_eye(theta, age=25.0, p=0.5):
    """CIE 146:2002 general disability glare equation, sr^-1, theta in degrees (0.1 to 100)."""
    return 10 / theta ** 3 + (5 / theta ** 2 + 0.1 * p / theta) * (1 + (age / 62.5) ** 4) + 2.5e-3 * p


def law_image(img, s):
    """The glare the law predicts for an image: each pixel spreads s (pi/180)^2 / r^2 of its light at r pixels,
    the screen-space kernel the pyramid approximates; by FFT on a padded canvas."""
    h, w = img.shape
    y, x = np.mgrid[-h:h, -w:w]
    r2 = (x * x + y * y).astype(np.float64)
    k = np.where(r2 > 0, s * (np.pi / 180) ** 2 / np.maximum(r2, 1.0), 0.0)
    pad = np.zeros((2 * h, 2 * w))
    pad[:h, :w] = img
    return np.real(np.fft.ifft2(np.fft.fft2(pad) * np.fft.fft2(np.fft.ifftshift(k))))[:h, :w]


def distance(mask, steps):
    """Distance in pixels to the mask, by growing it one pixel at a time (city-block and diagonal alternating)."""
    d = np.where(mask, 0.0, np.inf)
    grown = mask.copy()
    for i in range(1, steps + 1):
        g = grown.copy()
        g[1:] |= grown[:-1]; g[:-1] |= grown[1:]; g[:, 1:] |= grown[:, :-1]; g[:, :-1] |= grown[:, 1:]
        if i % 2 == 0:
            g[1:, 1:] |= grown[:-1, :-1]; g[:-1, :-1] |= grown[1:, 1:]; g[1:, :-1] |= grown[:-1, 1:]; g[:-1, 1:] |= grown[1:, :-1]
        d[g & ~grown] = i
        grown = g
    return d


def rings(theta, values, mask):
    out = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        m = mask & (theta >= a) & (theta < b)
        out.append(float(np.median(values[m])) if m.sum() > 20 else float("nan"))
    return np.array(out)


def row(label, values, fmt="{:7.4f}"):
    print(f"{label:24} | " + " ".join(fmt.format(v) for v in values), flush=True)


if __name__ == "__main__":
    exe, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    row("anneaux (degres)", MIDS, "{:7.1f}")
    for name, args, sun in SUN + [SNOW]:
        on, off = os.path.join(out, name + ".png"), os.path.join(out, name + "_sans.png")
        capture(exe, args, sun, on, True)
        capture(exe, args, sun, off, False)
        (a, ra), (b, rb) = linear(on), linear(off)
        W = int(np.log2(min(a.shape))) * 2 * np.pi * np.log(2) * (np.pi / 180) ** 2 * S  # one octave per level
        added, ok = a - (1 - W) * b, ra & rb
        if name == SNOW[0]:
            snow = b > 0.45
            theta = distance(snow, int(EDGES[-1] * a.shape[0] / FOV_Y)) * FOV_Y / a.shape[0]
            near = ok & ~snow
            row(f"neige {snow.mean():.0%}, ajout mesure", rings(theta, added, near))
            row("neige, loi sur l'image", rings(theta, law_image(np.where(rb, b, 1.0), S), near))
            row("neige, ajout / fond", rings(theta, (a - b) / np.maximum(b, 1e-3), near), "{:7.2%}")
            continue
        centre = np.argwhere(a >= np.percentile(a, 99.995)).mean(axis=0)[::-1]
        theta = angles(a.shape, centre)
        meas = rings(theta, added if name != "soleil_orbite" else a, ok)
        row(name + ", mesure", meas)
        if name == "soleil_orbite":
            law = S * np.pi / MIDS ** 2  # no air: E = pi
            row(f"loi, s = {S}", law)
            row("mesure / loi", meas / law, "{:7.2f}")
            row("oeil CIE, 25 ans", cie_eye(MIDS) * np.pi)
        else:
            row("  ajout / fond", rings(theta, (a - b) / np.maximum(b, 1e-3), ok), "{:7.1%}")
