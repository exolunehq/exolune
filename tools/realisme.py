# Realism measure: how close the engine's ground looks to a real material scan, at the same scale. The engine
# is captured straight down from a height where one pixel covers what one texel of the scan covers; both are
# reduced to their local structure (luminance, less its local mean, over its local spread), so that lighting
# and colour count less than the shapes. Two scores, lower is better:
# - patches: the sliced Wasserstein distance between their 7 x 7 patches, at three scales, as a multiple of
#   the distance between two areas of the scan itself (1: as close as the scan to itself);
# - spectrum: the mean gap between their power spectra, in dB, for wavelengths of 3 cm to 1 m, within
#   what the view holds.
# Follows the AI proof of concept of branch poc-ia-textures (docs/spec-textures-generees.md).
#
# python tools/realisme.py <exe> <scan.png|jpg> <scan width in m> <site> <out.png>
# Sites as in banc_visuel.py. Scans stay out of the repository, for instance CC0 ones from Poly Haven.
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_visuel

FOV_Y, HEIGHT_PX = np.radians(60.0), 720


def blur(a, sigma=8.0):
    """Separable Gaussian blur, edges repeated."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    a = np.pad(a, r, mode="edge")
    a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, a)


def structure(img):
    """Luminance less its local mean, over its local spread (Gaussian, 8 pixels)."""
    lum = np.asarray(img.convert("L"), np.float32)
    mean = blur(lum)
    spread = np.sqrt(np.maximum(blur((lum - mean) ** 2), 1.0))
    return (lum - mean) / spread


def patches(a, count, rng):
    ys = rng.integers(0, a.shape[0] - 7, count)
    xs = rng.integers(0, a.shape[1] - 7, count)
    return np.stack([a[y:y + 7, x:x + 7].ravel() for y, x in zip(ys, xs)])


def sliced_wasserstein(a, b, rng, projections=64, count=20000):
    pa, pb = patches(a, count, rng), patches(b, count, rng)
    directions = rng.normal(size=(pa.shape[1], projections))
    directions /= np.linalg.norm(directions, axis=0)
    return float(np.mean(np.abs(np.sort(pa @ directions, axis=0) - np.sort(pb @ directions, axis=0))))


def half(a):
    """Half the resolution, by 2 x 2 averages."""
    a = a[:a.shape[0] // 2 * 2, :a.shape[1] // 2 * 2]
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def multiscale(a, b, rng):
    total = 0.0
    for k in range(3):
        total += sliced_wasserstein(a, b, rng)
        a, b = half(a), half(b)
    return total / 3.0


def spectrum(a, metres_per_px):
    a = a * np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    power = np.abs(np.fft.fftshift(np.fft.fft2(a))) ** 2
    fy, fx = np.indices(a.shape)
    radius = np.hypot(fy - a.shape[0] / 2, fx - a.shape[1] / 2) / a.shape[0]  # cycles per pixel
    # From 3 cm, or 3 pixels, to 1 m, or half the view: the bands the view holds.
    wavelengths = np.geomspace(max(0.03, 3.0 * metres_per_px), min(1.0, 0.5 * a.shape[0] * metres_per_px), 10)
    bands = [power[(radius > metres_per_px / (w * 1.15)) & (radius <= metres_per_px / (w / 1.15))].mean()
             for w in wavelengths]
    bands = np.log10(np.array(bands) / np.sum(bands)) * 10.0
    return bands


if __name__ == "__main__":
    exe, scan_path, scan_width, site, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
    rng = np.random.default_rng(1)
    scan = Image.open(scan_path).convert("RGB")
    metres_per_px = scan_width / scan.size[0]
    # The camera's height for the same scale, one pixel of the screen per texel of the scan. The camera stays
    # 1.5 m above the ground at least: below, the scan is reduced to the camera's scale instead.
    height = metres_per_px * HEIGHT_PX / (2.0 * np.tan(FOV_Y / 2.0))
    if height < 1.5:
        height = 1.5
        metres_per_px = height * 2.0 * np.tan(FOV_Y / 2.0) / HEIGHT_PX
        size = int(round(scan_width / metres_per_px))
        scan = scan.resize((size, size), Image.LANCZOS)
    crop = min(600, (scan.size[0] - 32) // 2) # two areas of the scan, side by side
    if crop < 256:
        raise SystemExit(f"scan too small at this scale: {scan.size[0]} px")
    lat, lon, sun, _ = banc_visuel.SITES[site]
    scratch = os.path.join(os.path.dirname(os.path.abspath(out)), "realisme")
    os.makedirs(scratch, exist_ok=True)
    ground = banc_visuel.ground(exe, lat, lon, sun, scratch)
    render_png = os.path.join(scratch, f"{site}_vertical.png")
    banc_visuel.capture(exe, f"{ground + height:.2f} {lat} {lon} 89.9", sun, render_png)
    render = Image.open(render_png).convert("RGB").crop((640 - crop // 2, 360 - crop // 2, 640 + crop - crop // 2,
                                                          360 + crop - crop // 2))  # the centre, least slanted
    s = scan.size[0]
    scan_a = scan.crop((16, 16, 16 + crop, 16 + crop))
    scan_b = scan.crop((s - 16 - crop, s - 16 - crop, s - 16, s - 16))
    sa, sb, sr = structure(scan_a), structure(scan_b), structure(render)
    floor = multiscale(sa, sb, rng)
    patch_score = multiscale(sr, sa, rng) / floor
    spectrum_gap = float(np.mean(np.abs(spectrum(sr, metres_per_px) - spectrum(sa, metres_per_px))))
    spectrum_floor = float(np.mean(np.abs(spectrum(sb, metres_per_px) - spectrum(sa, metres_per_px))))
    sheet = Image.new("RGB", (2 * crop, crop))
    sheet.paste(render, (0, 0))
    sheet.paste(scan_a, (crop, 0))
    sheet.save(out)
    print(f"{site}: hauteur {height:.2f} m | motifs x{patch_score:.2f} (1 = le scan contre lui-meme) | "
          f"spectre {spectrum_gap:.1f} dB (scan contre lui-meme {spectrum_floor:.1f} dB)")
