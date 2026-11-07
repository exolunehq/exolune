# Flicker of an animated sea (docs/recherche-mer.md): banc_tremblement.py's frames, the camera still while the mesh moves
# as if it flew (MYPLANETENGINE_TREMBLE), the sea's time running at 60 frames a second. The sea's pixels come from its
# diagnostic view; the rest, land and sky, must not flicker more than with the sea frozen (MYPLANETENGINE_TIME="0 0").
# On the sea, with and without the temporal smoothing: the change from one frame to the next, which is its motion, and the
# contrast of its detail, which a smoothing that smears the motion would lower.
#
# python tools/banc_tremblement_mer.py <out folder> <exe> "<altitude latitude longitude pitch [heading]>"
import glob, os, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter


def run(exe, args, prefix, extra):
    for f in glob.glob(prefix + "_*.bmp"):
        os.remove(f)
    env = dict(os.environ, MYPLANETENGINE_TREMBLE=prefix, MYPLANETENGINE_SUN=os.environ.get("MYPLANETENGINE_SUN", "10 70"),
               MYPLANETENGINE_GLARE="1", **extra)
    env.pop("MYPLANETENGINE_VIEW", None)
    if "MYPLANETENGINE_VIEW" in extra:
        env["MYPLANETENGINE_VIEW"] = extra["MYPLANETENGINE_VIEW"]
    ps = f"Start-Process '{exe}' -ArgumentList '{args}' -WindowStyle Minimized -Wait"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, timeout=300)
    files = sorted(glob.glob(prefix + "_*.bmp"))
    frames = np.stack([np.asarray(Image.open(f).convert("RGB")).astype(np.float32) for f in files])
    for f in files:
        os.remove(f)
    return frames


def detail(frame):
    # The luminance less its 9-pixel blur: the waves' detail.
    lum = Image.fromarray(np.clip(frame.mean(axis=2), 0, 255).astype(np.uint8))
    return np.asarray(lum, np.float32) - np.asarray(lum.filter(ImageFilter.BoxBlur(4)), np.float32)


if __name__ == "__main__":
    out, exe, args = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
    os.makedirs(out, exist_ok=True)
    tag = os.path.join(out, "t")
    view = run(exe, args, tag, {"MYPLANETENGINE_VIEW": "sea", "MYPLANETENGINE_TREMBLE_FRAMES": "2"})[0]
    sea, ground = view.min(axis=2) > 250, view.max(axis=2) < 5  # the view: the sea white, the ground black, the sky its own
    rows = []
    for name, extra in (("mer figée, lissage", {"MYPLANETENGINE_TIME": "0 0", "MYPLANETENGINE_TAA": "1"}), ("mer figée, sans lissage", {"MYPLANETENGINE_TIME": "0 0", "MYPLANETENGINE_TAA": "0"}),
                        ("mer animée, lissage", {"MYPLANETENGINE_TAA": "1"}), ("mer animée, sans lissage", {"MYPLANETENGINE_TAA": "0"})):
        frames = run(exe, args, tag, extra)
        diffs = np.abs(np.diff(frames, axis=0)).max(axis=3)
        land = ground
        contrast = np.mean([detail(f)[sea].std() for f in frames]) if sea.any() else float("nan")
        rows.append((name, diffs[:, land].mean() if land.any() else float("nan"), diffs[:, sea].mean() if sea.any() else float("nan"), contrast))
    print(f"mer {100 * sea.mean():.0f} % de l'image")
    print("| cas | sol hors mer : écart d'une image à l'autre | mer : écart | mer : contraste du détail |")
    print("|---|---|---|---|")
    for name, land, water, contrast in rows:
        print(f"| {name} | {land:.2f} | {water:.2f} | {contrast:.2f} |")
