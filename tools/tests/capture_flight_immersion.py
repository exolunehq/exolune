"""Functional in-engine stills for canopy coverage, atmospheric entry and the suit."""
import argparse
import math
import os
from pathlib import Path
import re
import subprocess

from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[2]
ROUTE = ROOT / "tools/tests/2026-11-20-vol-immersion.txt"
PROFILES = ("classique", "chasseur", "navigateur")
FPS = 20
LAST = 60
ENTRY_HISTORY_SECONDS = 20
ENTRY_PATH_PITCH = -20  # flight-path angle, with the nose eight degrees above the trajectory
# A freshly installed display driver may compile the planet's pipelines before the first frame.
NATIVE_TIMEOUT = 900


def entry_travel(speed, seconds, level=False):
    if level:
        # Same final pose after a real hot approach, followed by three seconds
        # of level high-speed flight. The elapsed descent starts above 100 km.
        descending = min(seconds + 3, 0)
        pitch = math.radians(-24)
        return (speed * (descending * math.cos(pitch) + max(seconds, -3)),
                speed * descending * math.sin(pitch))
    pitch = math.radians(ENTRY_PATH_PITCH)
    return speed * seconds * math.cos(pitch), speed * seconds * math.sin(pitch)


def cinematic_environment(folder, profile, rain=False, entry_speed=None, level=False):
    # Paired runs end at exactly the same pose, sun, clock and sea state.
    entering = entry_speed is not None
    lat, lon, altitude, heading, pitch = (
        (30.68685, 120.10788, 57000, 76, -12) if entering
        else (-20.47, -75.45, 1300, 160, -1)
    )
    last = ENTRY_HISTORY_SECONDS * FPS if entering else LAST
    lines = [f"fps {FPS}"]
    for frame in range(last + 1):
        horizontal, vertical = entry_travel(entry_speed, (frame - last) / FPS, level) if entering else (0.0, 0.0)
        arc = math.degrees(horizontal / (6378000 + altitude))
        ship = (lat + arc * math.cos(math.radians(heading)),
                lon + arc * math.sin(math.radians(heading)) / math.cos(math.radians(lat)),
                altitude + vertical, heading, pitch, 0)
        # Cockpit mode takes its eye directly from the selected ship profile.
        values = " ".join(f"{v:.9f}" for v in (*ship, *ship, 63, 0))
        lines.append(f"{frame} cockpit {values}")
    path = folder / "pose.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    options = dict(MYPLANETENGINE_MODELE_VAISSEAU=profile, MYPLANETENGINE_CINE=str(path),
                   MYPLANETENGINE_CINE_RANGE=f"{last} 1 {LAST}", MYPLANETENGINE_CINE_OUT=str(folder),
                   MYPLANETENGINE_SUN="12 -161" if entering else "-50.47 -75.45")
    if rain:
        options["MYPLANETENGINE_VERRIERE"] = "pluie"
    return options, folder / f"frame_{last:05d}.bmp"


def route_environment(folder, row, chase=False):
    path = folder / "capture.bmp"
    route = ROUTE.with_name("2026-11-20-propulsion-verriere.txt") if chase else ROUTE
    return dict(MYPLANETENGINE_CAPTURE=str(path), MYPLANETENGINE_CAPTURE_FRAME="14" if chase else "40",
                MYPLANETENGINE_TESTS=str(route), MYPLANETENGINE_FIRST_TEST=str(row),
                MYPLANETENGINE_VAISSEAU="poursuite" if chase else "cockpit"), path


def changed_fraction(a, b, box, threshold):
    red, green, blue = ImageChops.difference(a.crop(box), b.crop(box)).split()
    difference = ImageChops.lighter(red, ImageChops.lighter(green, blue))
    return sum(difference.histogram()[threshold:]) / (difference.width * difference.height)


def check_entry(observed, cold, luminous=True):
    def horizon_contrast(image):
        grey = image.convert("L")
        sky = ImageStat.Stat(grey.crop((400, 78, 560, 126))).mean[0]
        earth = ImageStat.Stat(grey.crop((400, 206, 560, 254))).mean[0]
        return earth - sky

    # The gas may cross the line of sight. The pilot still needs the horizon
    # and the three physical instruments when the passage reaches full brightness.
    window = (20, 55, 940, 285)
    if luminous:
        contrast = horizon_contrast(observed) / max(1, horizon_contrast(cold))
        if contrast < .5:
            raise ValueError(f"The cockpit retained only {contrast:.0%} of the horizon contrast")
        if changed_fraction(observed, cold, window, 20) < .04:
            raise ValueError("The entry was invisible from the cockpit")
        if changed_fraction(observed, cold, (255, 386, 705, 521), 24) > .08:
            raise ValueError("The luminous gas reached the opaque instrument cluster")
        print(f"Cockpit retained {contrast:.0%} of cold horizon contrast", flush=True)
    elif changed_fraction(observed, cold, window, 12) > .035:
        raise ValueError("Fast level flight still lights the forward view")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=ROOT / "x64/Release/MyPlanetEngine.exe")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/vol-immersion-2026-11-20")
    cases = [(f"{p}-{w}", p, w == "pluie", None, 0) for p in PROFILES for w in ("sec", "pluie")]
    cases.extend([("rentree", "chasseur", False, 7100, 0), ("approche-lente", "chasseur", False, 250, 0),
                  ("palier-rapide", "chasseur", False, 7100, 0),
                  ("casque-foret", "", False, None, 8), ("survol-lune", "", False, None, 10),
                  ("casque-lune", "", False, None, 11), ("poursuite-jour", "chasseur", False, None, 9)])
    parser.add_argument("--case", choices=[c[0] for c in cases], nargs="+")
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    out = args.out.resolve()
    base = {k: v for k, v in os.environ.items() if not k.startswith("MYPLANETENGINE_")}
    base.update(MYPLANETENGINE_RESOLUTION="960 540", MYPLANETENGINE_FULLSCREEN="0",
                MYPLANETENGINE_SCANS=str(ROOT.parent / "scans"), MYPLANETENGINE_COORDINATES="0")
    images = {}
    for name, profile, rain, speed, row in cases:
        if args.case and name not in args.case:
            continue
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        chase = name == "poursuite-jour"
        options, bitmap = (route_environment(folder, row, chase) if row else
                           cinematic_environment(folder, profile, rain, speed, level=name == "palier-rapide"))
        bitmap.unlink(missing_ok=True)
        if row:
            Path(f"{bitmap}.txt").unlink(missing_ok=True)
        subprocess.run([exe], cwd=exe.parent, env={**base, **options},
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=NATIVE_TIMEOUT, check=True)
        with Image.open(bitmap) as frame:
            rgb = frame.convert("RGB")
            if rgb.size != (960, 540) or rgb.getextrema()[0][1] < 35:
                raise ValueError(f"{name} produced an empty or incorrectly sized frame")
            images[name] = rgb
            rgb.save(out / f"{name}.png")
        if row:
            title = Path(f"{bitmap}.txt").read_text(encoding="utf-8")
            expected = "poursuite" if chase else "marche" if row in (8, 11) else "chauffe 0 %"
            if expected not in title:
                raise ValueError(f"{name}: '{expected}' missing from capture title")
            if chase:
                heat = re.search(r"chauffe (\d+(?:[.,]\d+)?) %", title)
                if not heat or float(heat[1].replace(",", ".")) < 20:
                    raise ValueError("The playable chase camera did not witness a hot entry")
        print(f"{name} complete", flush=True)
    for profile in PROFILES:
        dry, wet = (images.get(f"{profile}-{w}") for w in ("sec", "pluie"))
        if dry is None or wet is None:
            continue
        # The same sky patch includes drops on every model. The lower central patch is inside the cabin.
        if changed_fraction(dry, wet, (0, 0, 960, 205), 3) < 0.0002:
            raise ValueError(f"{profile} rain did not reach the visible pane")
        if changed_fraction(dry, wet, (365, 487, 595, 540), 3) > 0.002:
            raise ValueError(f"{profile} rain reached the opaque cabin")
    hot, cold = images.get("rentree"), images.get("approche-lente")
    if hot is not None and cold is not None:
        check_entry(hot, cold)
    level = images.get("palier-rapide")
    if level is not None and cold is not None:
        check_entry(level, cold, luminous=False)


if __name__ == "__main__":
    main()
