# Tremble bench: the engine keeps the camera still while the mesh moves as if the camera flew forward
# (MYPLANETENGINE_TREMBLE). The terrain is fixed on the planet, so a perfectly stable renderer gives the same
# image every frame: every difference between consecutive frames is trembling.
#
# python tools/banc_tremblement.py <out folder> <exe> "<altitude latitude longitude pitch [heading]>" [exe ...]
# Prints, for each exe, the mean change between consecutive frames over the terrain, with and without the
# temporal smoothing, and writes a heat map of where it trembles.
import glob, os, subprocess, sys
import numpy as np
from PIL import Image

SKY = np.array([5, 8, 20])  # the clear colour


def run(exe, args, prefix, extra_env):
    for f in glob.glob(prefix + "_*.bmp"):
        os.remove(f)
    env = dict(os.environ, MYPLANETENGINE_TREMBLE=prefix, MYPLANETENGINE_SUN=os.environ.get("MYPLANETENGINE_SUN", "10 70"),
               MYPLANETENGINE_GLARE="1", **extra_env)
    env.pop("MYPLANETENGINE_VIEW", None)
    ps = f"Start-Process '{exe}' -ArgumentList '{args}' -WindowStyle Minimized -Wait"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, timeout=180)
    return sorted(glob.glob(prefix + "_*.bmp"))


def analyse(files, heat_png):
    frames = np.stack([np.asarray(Image.open(f).convert("RGB")).astype(np.int16) for f in files])
    terrain = np.abs(frames[0] - SKY).max(axis=2) > 3
    diffs = np.abs(np.diff(frames, axis=0)).max(axis=3)
    Image.fromarray(np.clip(diffs.mean(axis=0) * 16, 0, 255).astype(np.uint8)).save(heat_png)
    for f in files:
        os.remove(f)
    return float(diffs[:, terrain].mean())


if __name__ == "__main__":
    out, args = os.path.abspath(sys.argv[1]), sys.argv[3]
    exes = [os.path.abspath(sys.argv[2])] + [os.path.abspath(e) for e in sys.argv[4:]]
    os.makedirs(out, exist_ok=True)
    for exe in exes:
        name = os.path.basename(os.path.dirname(exe))
        res = []
        for taa in (True, False):
            tag = f"{name}{'' if taa else '_off'}"
            files = run(exe, args, os.path.join(out, tag), {"MYPLANETENGINE_TAA": "1"} if taa else {})
            res.append(analyse(files, os.path.join(out, tag + "_heat.png")) if len(files) > 1 else float("nan"))
        print(f"{name} | tremblement avec/sans lissage : {res[0]:.2f} / {res[1]:.2f}", flush=True)
