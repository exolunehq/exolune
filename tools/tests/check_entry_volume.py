"""Check the hot gas outside the rendered hull at the same ship and camera pose."""
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

from capture_flight_immersion import PROFILES, ROOT


def measure(hot, cold, background):
    # The cold ship and the bare camera see the same level flight. Their difference
    # locates the visible hull, including each model's particular nose and wings.
    height, width = cold.shape[:2]
    y, x = np.ogrid[:height, :width]
    difference = np.max(np.abs(cold - background), axis=2)
    silhouette = Image.fromarray((difference > 36).astype(np.uint8) * 255).filter(ImageFilter.MedianFilter(3))
    hull = np.asarray(silhouette) > 0
    near_ship = (x > .37 * width) & (x < .85 * width) & (y > .26 * height) & (y < .74 * height)
    rows, columns = np.where(hull & near_ship)
    if columns.size < 100:
        raise ValueError("The cold exterior and bare view did not resolve the hull")
    nose = columns.max()
    nose_y = np.median(rows[columns > nose - 5])
    # Exclude antialiasing along the cold silhouette. Test both the detached
    # front and the space just outside the shoulder, away from the engine plume.
    clear = np.asarray(silhouette.filter(ImageFilter.MaxFilter(9))) == 0
    ahead = clear & (x >= nose + 3) & (x <= nose + .05 * width) & (abs(y - nose_y) < .045 * height)
    near_flank = np.asarray(silhouette.filter(ImageFilter.MaxFilter(35))) > 0
    sides = near_flank & clear & (x > .39 * width) & (x < nose - .055 * width)
    delta = hot - cold
    warm = (delta[:, :, 0] > 20) & (delta[:, :, 0] - delta[:, :, 2] > 16)
    if not ahead.any() or not sides.any():
        raise ValueError("No background area available to inspect in front of the nose or beside the hull")
    return warm[ahead].mean(), warm[sides].mean(), warm[:height // 9].mean()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="chasseur")
    parser.add_argument("--exe", type=Path, default=ROOT / "x64/Release/MyPlanetEngine.exe")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/vol-assiste-2026-11-20")
    parser.add_argument("--use-existing", action="store_true", help="Inspect frames already rendered into --out")
    args = parser.parse_args()
    images = []
    for shot, view in (("rentree", "exterieur"), ("palier", "exterieur"), ("palier", "decor")):
        if not args.use_existing:
            subprocess.run([sys.executable, Path(__file__).with_name("capture_reentry_motion.py"),
                            "--profile", args.profile, "--shot", shot, "--view", view, "--still-at", "10",
                            "--exe", args.exe, "--out", args.out], check=True)
        with Image.open(args.out / f"{args.profile}-{shot}-{view}-300.png") as frame:
            images.append(np.asarray(frame.convert("RGB").resize((640, 360), Image.Resampling.BOX), dtype=np.int16))
    bow, flank, sky = measure(*images)
    print(f"{args.profile}: changed warm pixels ahead of the nose {bow:.1%}, beside the hull {flank:.1%}, far sky {sky:.1%}")
    if bow < .07 or flank < .07:
        raise SystemExit("Entry light must occupy visible air ahead of the bow and around the flanks")
    if sky > .01:
        raise SystemExit("Entry light reached the distant sky away from the ship")


if __name__ == "__main__":
    main()
