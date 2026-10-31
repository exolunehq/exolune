# Performance bench (docs/optimisation.md): the game, the exe's default (its clouds, FFT sea, detailed vegetation),
# 1920 x 1080, VSync off, without a window. Each view's GPU time per pass, the mean over the 120 frames the vegetation
# samples (MYPLANETENGINE_BATCH, <capture>.perf).
#
# python tools/banc_perf.py [--exe <exe>] [--out <folder>] [--before previous.json] [--res "1920 1080"]
#                           [--full] [--weather <s>] [--views <a,b>]
#                           [--motion "<heading deg> <latitude deg> <weather s> [<height factor> [<still frames>
#                                     [<speed>]]]"]
#
# --full: the clouds' single full-resolution pass instead of the temporal one. --weather: the weather's time. --motion,
# per frame: the camera reaches each view by turning, flying north and descending (its height divided by the factor at
# each frame), the weather runs up to its time; then it holds still for the given frames before the capture. Compared
# with the same motion under --full, it shows what the temporal pass loses in motion (docs/optimisation.md). <speed>: a
# further share of the height flown north per frame, the app's own speed rule; x6 at 140 fps is 0.04.
#
# Build the exe first: powershell -File tools/lance.ps1 -Build -NoLaunch. One run at a time: the GPU is the thing
# measured.
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, r"x64\Release\MyPlanetEngine.exe")
SCANS = os.environ.get("MYPLANETENGINE_SCANS", os.path.join(os.path.expanduser("~"), r"Documents\repos\MyPlanetEngine\scans"))

# name: height above the ground (m), latitude, longitude, pitch down, heading, sun latitude, sun longitude
VIEWS = {
    "foret_sol": (2, 30.38761, 120.52330, 5, -115, 20, 120),
    "lisiere":   (3, 30.37000, 120.53027, 3, 0, 20, 140),
    "montagne":  (30, -14.90437, 119.94946, 5, 120, -5, 125),
    "mer":       (3, -20.47, -75.45, 5, 200, -50.47, -75.45),
    "survol":    (1300, 30.68685, 120.10788, 32, -64.7, 20, 120),
    "cumulus":   (10000, 38.1445, 103.5352, 35, 90, 38.1445, 128.5352),
    "orbite":    (300000, -41.6602, 87.7148, 80, 0, -41.6602, 112.7148),
    "globe":     (10000000, 0.5, 161.775, 90, 0, -15, 175),
    # Toward the horizon from high orbit, over the northern sheet and cumulus: where the temporal pass showed plates.
    "haut160":   (160000, 76.0, 38.8477, 20, 0, 70.0, 63.8477),
    "haut440":   (440000, 30.0, 103.5352, 25, 0, 38.1445, 128.5352),
    # 150 m above a forest, looking up at cumulus in a blue sky: flying fast between the ground and the clouds.
    "cumulus_sol": (150, -41.0, 88.5, -12, 60, -41.66, 112.71),
}
# In the order of D3DApp::ReadGpuTimes, GPU ms. Then the CPU's frame, ms: preparation, recording, submission and present,
# the wait for the GPU; the cadence, from one present to the next, what the eye gets; the GPU idle between two frames.
PASSES = ["mer_fft", "terrain_calc", "objets_place", "plantes_place", "copies", "feuillage_tri", "terrain_dessin",
          "objets_dessin", "feuillage_dessin", "nuages_aux", "nuages_trace", "atmosphere", "post", "total",
          "cpu_prep", "cpu_liste", "cpu_present", "cpu_attente", "cadence", "gpu_inactif"]


def run(exe, out, res, full=False, weather=None, motion=None, views=None):
    os.makedirs(out, exist_ok=True)
    if views:
        for name in [v for v in VIEWS if v not in views]:
            del VIEWS[name]
    jobs = os.path.join(out, "jobs.txt")
    with open(jobs, "w") as f:
        for name, (h, lat, lon, pitch, head, slat, slon) in VIEWS.items():
            time = "" if weather is None else f" {weather}"
            f.write(f"{os.path.join(out, name + '.bmp')} rendu {h} {lat} {lon} {pitch} {head} 2{time} {slat} {slon}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MYPLANETENGINE_")}
    env.update(MYPLANETENGINE_BATCH=jobs, MYPLANETENGINE_RESOLUTION=res, MYPLANETENGINE_VSYNC="0",
               MYPLANETENGINE_FULLSCREEN="0", MYPLANETENGINE_SCANS=SCANS)
    if full:
        env["MYPLANETENGINE_CLOUD_FULL"] = "1"
    if motion:
        env["MYPLANETENGINE_BATCH_MOTION"] = motion
    # The ini beside the exe must not override the bench: the environment wins over it (Settings.cpp).
    subprocess.run([exe], env=env, cwd=os.path.dirname(exe), timeout=900, check=True)
    result = {}
    for name in VIEWS:
        with open(os.path.join(out, name + ".bmp.perf")) as f:
            values = f.read().split()
        assert int(values[-1]) > 0, f"{name}: no sample"
        result[name] = dict(zip(PASSES, map(float, values[:-1])))
    return result


def image_change(out, before_dir, name):
    # The quality guard: the mean change of the view's pixels against the previous run's, in 8-bit levels, and the
    # share of pixels changed by more than 8 levels, a step the eye sees on a flat area; then the share changed by more
    # than 2 levels on average over 9 x 9 pixels: plates, flat offsets with sharp edges that neither of the others sees.
    import cv2, numpy as np
    a, b = (cv2.imread(os.path.join(d, name + ".bmp")).astype(np.float32) for d in (out, before_dir))
    d = np.abs(a - b).max(axis=2)
    plates = np.abs(cv2.blur(a - b, (9, 9))).max(axis=2)
    return float(d.mean()), float((d > 8).mean() * 100), float((plates > 2).mean() * 100)


def table(result, before=None, out=None, before_dir=None):
    shown = [p for p in PASSES if any(r[p] >= 0.05 for r in result.values())]
    print("vue        " + " ".join(f"{p[:9]:>9}" for p in shown) + "   fps  réel" + ("  écart >8 plaques" if before else ""))
    for name, r in result.items():
        cells = []
        for p in shown:
            c = f"{r[p]:9.2f}"
            if before and name in before and p in ("total", "cadence") and before[name].get(p):
                c = f"{r[p]:5.2f}{(r[p] - before[name][p]) / before[name][p] * 100:+4.0f}%"
            cells.append(c)
        change = ""
        if before and name in before:
            mean, share, plates = image_change(out, before_dir, name)
            change = f" {mean:5.2f} {share:5.2f}% {plates:5.2f}%"
        real = f" {1000 / r['cadence']:5.0f}" if r.get("cadence") else "     -"
        print(f"{name:10} " + " ".join(cells) + f" {1000 / r['total']:5.0f}" + real + change)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--exe", default=EXE)
    a.add_argument("--out", default=os.path.join(ROOT, r"x64\banc_perf"))
    a.add_argument("--before")
    a.add_argument("--res", default="1920 1080")
    a.add_argument("--full", action="store_true")
    a.add_argument("--weather", type=float)
    a.add_argument("--motion")
    a.add_argument("--views", help="comma-separated subset of the views")
    args = a.parse_args()
    args.out = os.path.abspath(args.out)
    result = run(args.exe, args.out, args.res, args.full, args.weather, args.motion,
                 args.views.split(",") if args.views else None)
    with open(os.path.join(args.out, "perf.json"), "w") as f:
        json.dump(result, f, indent=1)
    before = json.load(open(args.before)) if args.before else None
    table(result, before, args.out, os.path.dirname(os.path.abspath(args.before)) if args.before else None)
    print("json:", os.path.join(args.out, "perf.json"))
