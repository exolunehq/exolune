# Sea bench (docs/recherche-mer.md, section 7): the sun's glint against Cox and Munk, the whitecaps' share and the
# glint's mean on the way down, the wind map. The engine renders hidden, in batch (MYPLANETENGINE_BATCH), in its views
# `glint` (on the sea: the glint's reflectance pi L / (E mu_s) over 4, without the air, the wind's speed over 32 m/s, its direction
# modulo pi) and `foam` (the root of the whitecaps' share, in red). Every pixel's view and sun are rebuilt here as D3DApp places
# the camera, and Cox and Munk's reflectance computed for the pixel's own wind, independently of the shader.
#
# python tools/banc_mer.py <exe> <out folder> carte
#     the sea and its wind from 15 000 km, both hemispheres: the zonal mean of the wind, and sites by wind speed
# python tools/banc_mer.py <exe> <out folder> reflet <lat> <lon> [<lat> <lon> ...]
#     the glint from 400 km over each site, the sun 20 degrees from its zenith: measured over predicted, by band of the
#     prediction, and the profile along the sun's plane
# python tools/banc_mer.py <exe> <out folder> descente <lat> <lon> [heights in m ...]
#     the same sea from 1 500 km down to 10 m, straight down, the sun 20 degrees from the zenith: the glint's mean over the
#     view against Cox and Munk's, the whitecaps' share against Monahan's
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

R = 6378000.0
W_PX, H_PX, TAN_Y = 1280, 720, np.tan(np.radians(30.0))
NORTH = np.array([0.0, 1.0, 0.0])


def lat_lon_to_dir(lat, lon):
    a, b = np.radians(lat), np.radians(lon)
    return np.array([np.cos(a) * np.cos(b), np.sin(a), np.cos(a) * np.sin(b)])


def camera(lat, lon, pitch_down, heading, altitude):
    # D3DApp::PlaceCamera, then the axes XMMatrixLookToLH builds: position, forward, right, up.
    up = lat_lon_to_dir(lat, lon)
    north = NORTH - up * up.dot(NORTH)
    north = north / np.linalg.norm(north) if np.linalg.norm(north) > 1e-6 else np.array([1.0, 0.0, 0.0])
    b = np.radians(lon)
    east = np.array([-np.sin(b), 0.0, np.cos(b)])
    p, h = np.radians(pitch_down), np.radians(heading)
    forward = (north * np.cos(h) + east * np.sin(h)) * np.cos(p) - up * np.sin(p)
    forward /= np.linalg.norm(forward)
    right = np.cross(up, forward)
    right /= np.linalg.norm(right)
    return up * (R + altitude), forward, right, np.cross(forward, right)


def pixels(position, forward, right, cam_up):
    # Each pixel's ray, where it meets the sea-level sphere (NaN where it misses), the normal there, east and north.
    x = (2.0 * (np.arange(W_PX) + 0.5) / W_PX - 1.0) * TAN_Y * W_PX / H_PX
    y = (1.0 - 2.0 * (np.arange(H_PX) + 0.5) / H_PX) * TAN_Y
    rays = forward + x[None, :, None] * right + y[:, None, None] * cam_up
    rays /= np.linalg.norm(rays, axis=2, keepdims=True)
    b = rays @ position
    disc = b * b - (position @ position - R * R)
    t = -b - np.sqrt(np.where(disc > 0.0, disc, np.nan))
    point = position + t[..., None] * rays
    n = point / R
    east = np.cross(n, NORTH)
    east /= np.linalg.norm(east, axis=2, keepdims=True)
    north = NORTH - n * (n @ NORTH)[..., None]
    north /= np.linalg.norm(north, axis=2, keepdims=True)
    return -rays, n, east, north


def fresnel(c, m=1.333):
    g = np.sqrt(m * m - 1.0 + c * c)
    return 0.5 * ((g - c) / (g + c)) ** 2 * (1.0 + ((c * (g + c) - 1.0) / (c * (g - c) + 1.0)) ** 2)


def cox_munk(view, sun, n, east, north, speed, angle):
    # Cox and Munk 1954's glint reflectance, pi F p / (4 mu_s mu_v mu_h^4), the slopes normal along and across the wind,
    # with Smith's masking for Beckmann's law (Walter 2007), the exact Fresnel of water.
    su, sc = 3.16e-3 * speed, 0.003 + 1.92e-3 * speed
    along = np.cos(angle)[..., None] * east + np.sin(angle)[..., None] * north
    across = np.cross(n, along)
    h = view + sun
    h /= np.linalg.norm(h, axis=-1, keepdims=True)
    mu_h, mu_v, mu_s = (h * n).sum(-1), (view * n).sum(-1), (sun * n).sum(-1)
    zu, zc = -(h * along).sum(-1) / mu_h, -(h * across).sum(-1) / mu_h
    p = np.exp(-0.5 * (zu * zu / su + zc * zc / sc)) / (2.0 * np.pi * np.sqrt(su * sc))
    lam = 0.0
    for d, mu in ((view, mu_v), (sun, mu_s)):
        flat = d - mu[..., None] * n
        c2 = (flat * along).sum(-1) ** 2 / np.maximum((flat * flat).sum(-1), 1e-12)
        m = mu / np.sqrt(np.maximum(2.0 * (su * c2 + sc * (1.0 - c2)) * (1.0 - mu * mu), 1e-12))
        lam = lam + np.where(m < 1.6, (1.0 - 1.259 * m + 0.396 * m * m) / (3.535 * m + 2.181 * m * m), 0.0)
    rho = np.pi * fresnel((view * h).sum(-1)) * p / (4.0 * mu_s * mu_v * mu_h ** 4) / (1.0 + lam)
    return np.where(mu_s > 0.0, rho, 0.0), mu_v, mu_s


def linear(img):
    c = np.asarray(img.convert("RGB"), np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def run(exe, jobs, folder, sun):
    path = os.path.join(folder, "jobs.txt")
    with open(path, "w") as f:
        for j in jobs:
            f.write(" ".join(str(x) for x in j) + "\n")
    env = dict(os.environ, MYPLANETENGINE_BATCH=path, MYPLANETENGINE_SUN=f"{sun[0]} {sun[1]}", MYPLANETENGINE_TAA="1",
               MYPLANETENGINE_TIME=os.environ.get("MYPLANETENGINE_TIME", "0 20"))  # jobs seconds apart: other waves
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_CAPTURE", "MYPLANETENGINE_TREMBLE"):
        env.pop(k, None)
    subprocess.run([exe], env=env, timeout=1800)


def glint_view(path):
    # The view `glint`: the measured reflectance, the wind, and the sea's pixels (blue from 0.02).
    c = linear(Image.open(path))
    sea = np.asarray(Image.open(path).convert("RGB"))[..., 2] >= 4
    angle = np.pi * (c[..., 2] - 0.02) / 0.96
    return 4.0 * c[..., 0], 32.0 * c[..., 1], angle, sea


def site_sun(lat, lon, tilt=20.0):
    # The sun `tilt` degrees from the site's zenith, towards the south (or north beyond 60 degrees south).
    return (lat - tilt if lat > -60.0 else lat + tilt, lon)


def carte(exe, out):
    jobs, sites = [], [(0.0, 0.0), (0.0, 180.0), (60.0, 90.0), (-60.0, -90.0)]
    for k, (lat, lon) in enumerate(sites):
        jobs.append((os.path.join(out, f"carte_{k}.bmp"), "glint", 15.0e6, lat, lon, 89.9, 0.0))
    run(exe, jobs, out, (0.0, 0.0))
    lats, speeds, rows = [], [], []
    for k, (lat, lon) in enumerate(sites):
        _, speed, _, sea = glint_view(jobs[k][0])
        view, n, _, _ = pixels(*camera(lat, lon, 89.9, 0.0, 15.0e6))
        ok = sea & np.isfinite(n[..., 0])
        la = np.degrees(np.arcsin(np.clip(n[..., 1], -1, 1)))
        lo = np.degrees(np.arctan2(n[..., 2], n[..., 0]))
        lats.append(la[ok]), speeds.append(speed[ok])
        rows.append(np.stack([la[ok], lo[ok], speed[ok]], 1)[::97])
    lats, speeds, rows = np.concatenate(lats), np.concatenate(speeds), np.concatenate(rows)
    print("| latitude | vent moyen (m/s) | pixels de mer |")
    print("|---|---|---|")
    for a in range(-80, 80, 10):
        m = (lats >= a) & (lats < a + 10)
        if m.sum() > 50:
            print(f"| {a} à {a + 10}° | {speeds[m].mean():.1f} | {m.sum()} |")
    for lo, hi in ((0, 4), (5, 8), (9, 12), (14, 30)):
        m = (rows[:, 2] >= lo) & (rows[:, 2] < hi) & (np.abs(rows[:, 0]) < 70)
        print(f"vent {lo} à {hi} m/s :", "; ".join(f"{r[0]:.2f} {r[1]:.2f} ({r[2]:.1f})" for r in rows[m][:: max(1, m.sum() // 4)][:4]))


def reflet(exe, out, sites):
    jobs = [(os.path.join(out, f"reflet_{k}.bmp"), "glint", 400e3, lat, lon, 89.9, 0.0) for k, (lat, lon) in enumerate(sites)]
    for k, (lat, lon) in enumerate(sites):
        run(exe, [jobs[k]], out, site_sun(lat, lon))
    sheet = Image.new("RGB", (640, 220 * len(sites)), "white")
    draw = ImageDraw.Draw(sheet)
    print("| site | vent (m/s) | mesuré / Cox-Munk, par part du maximum prédit : > 0,5 | 0,2 à 0,5 | 0,05 à 0,2 | 0,01 à 0,05 | écart moyen |")
    print("|---|---|---|---|---|---|---|")
    for k, (lat, lon) in enumerate(sites):
        rho, speed, angle, sea = glint_view(jobs[k][0])
        view, n, east, north = pixels(*camera(lat, lon, 89.9, 0.0, 400e3))
        sun = lat_lon_to_dir(*site_sun(lat, lon))
        predicted, mu_v, mu_s = cox_munk(view, sun, n, east, north, speed, angle)
        ok = sea & np.isfinite(predicted) & (mu_v > 0.5) & (mu_s > 0.5)
        top = predicted[ok].max()
        cells = []
        for lo, hi in ((0.5, 2.0), (0.2, 0.5), (0.05, 0.2), (0.01, 0.05)):
            m = ok & (predicted >= lo * top) & (predicted < hi * top)
            cells.append(f"{rho[m].mean() / predicted[m].mean():.3f}" if m.sum() > 100 else "-")
        m = ok & (predicted > 0.05 * top)
        gap = np.abs(rho[m] - predicted[m]).mean() / predicted[m].mean()
        print(f"| {lat:.2f} {lon:.2f} | {np.median(speed[ok]):.1f} | " + " | ".join(cells) + f" | {100 * gap:.1f} % |", flush=True)
        # The profile along the image's middle column, the sun's plane: measured and predicted, rows averaged by 8.
        col = slice(W_PX // 2 - 4, W_PX // 2 + 4)
        meas, pred = rho[:, col].mean(1), predicted[:, col].mean(1)
        y0 = 220 * k + 210
        scale = 190.0 / max(pred.max(), 1e-6)
        for i in range(H_PX - 1):
            xa, xb = 20 + i * 600 / H_PX, 20 + (i + 1) * 600 / H_PX
            draw.line((xa, y0 - scale * pred[i], xb, y0 - scale * pred[i + 1]), fill="black", width=2)
            draw.line((xa, y0 - scale * meas[i], xb, y0 - scale * meas[i + 1]), fill="red", width=1)
        draw.text((24, 220 * k + 4), f"{lat:.2f} {lon:.2f}, vent {np.median(speed[ok]):.1f} m/s : rouge mesuré, noir Cox-Munk",
                  fill="black")
    sheet.save(os.path.join(out, "reflet_profils.png"))


def descente(exe, out, lat, lon, heights):
    sun = site_sun(lat, lon)
    jobs = []
    for h in heights:
        for r in range(1 if h > 2000 else 6 if h > 100 else 16):  # near the sea, several times: the groups outsize the view
            jobs.append((os.path.join(out, f"glint_{h:g}_{r}.bmp"), "glint", h, lat, lon, 89.9, 0.0))
            jobs.append((os.path.join(out, f"foam_{h:g}_{r}.bmp"), "foam", h, lat, lon, 89.9, 0.0))
    run(exe, jobs, out, sun)
    print("| hauteur | reflet mesuré / Cox-Munk | vent (m/s) | moutons vus | Monahan au vent du pixel |")
    print("|---|---|---|---|---|")
    for h in heights:
        position, forward, right, cam_up = camera(lat, lon, 89.9, 0.0, h)
        view, n, east, north = pixels(position, forward, right, cam_up)
        measured, predicted, foam, monahan, speeds = [], [], [], [], []
        r = 0
        while os.path.exists(os.path.join(out, f"glint_{h:g}_{r}.bmp")):
            rho, speed, angle, sea = glint_view(os.path.join(out, f"glint_{h:g}_{r}.bmp"))
            p, _, _ = cox_munk(view, lat_lon_to_dir(*sun), n, east, north, speed, angle)
            ok = sea & np.isfinite(p)
            measured.append(rho[ok].mean()), predicted.append(p[ok].mean()), speeds.append(np.median(speed[ok]))
            share = linear(Image.open(os.path.join(out, f"foam_{h:g}_{r}.bmp")))[..., 0] ** 2
            foam.append(share[ok].mean()), monahan.append(np.minimum(3.84e-6 * speed[ok] ** 3.41, 0.5).mean())
            r += 1
        print(f"| {h:g} m | {np.mean(measured) / np.mean(predicted):.3f} | {np.mean(speeds):.1f} | {100 * np.mean(foam):.2f} % "
              f"| {100 * np.mean(monahan):.2f} % |", flush=True)


if __name__ == "__main__":
    exe, out, mode = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    args = [float(a) for a in sys.argv[4:]]
    if mode == "carte":
        carte(exe, out)
    elif mode == "reflet":
        reflet(exe, out, list(zip(args[0::2], args[1::2])))
    else:
        descente(exe, out, args[0], args[1],
                 args[2:] or [1.5e6, 4.0e5, 1.0e5, 3.0e4, 1.0e4, 3000.0, 1000.0, 500.0, 200.0, 80.0, 30.0, 10.0])
