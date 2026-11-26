"""Hidden native Exolune spaceport review captures for Milestone 1 characters.

Generates viewpoints directly from the spaceport pad frame in the city bank's
layout.json, runs MyPlanetEngine.exe headlessly via MYPLANETENGINE_BATCH with
TAA enabled, converts captures to PNG and emits a user flight/walk review route.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geographical(lat: float, lon: float, x: float, y: float):
    a, b = map(math.radians, [lat, lon])
    up = np.array([math.cos(a) * math.cos(b), math.sin(a), math.cos(a) * math.sin(b)])
    east = np.array([-math.sin(b), 0.0, math.cos(b)])
    north = np.array([-math.sin(a) * math.cos(b), math.cos(a), -math.sin(a) * math.sin(b)])
    p = up * 6378000.0 + east * x + north * y
    p /= np.linalg.norm(p)
    return math.degrees(math.asin(p[1])), math.degrees(math.atan2(p[2], p[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--city-bank", type=Path, default=Path("E:/ExoluneAssets/city-tripo-2026-11-11/delivery-07/bank"))
    ap.add_argument("--char-bank", type=Path, default=Path("E:/ExoluneAssets/characters-m1-2026-11-21/bank"))
    ap.add_argument("--out", type=Path, default=Path("E:/ExoluneAssets/characters-m1-2026-11-21/native-review"))
    ap.add_argument("--exe", type=Path, default=ROOT / "x64/Release/MyPlanetEngine.exe")
    ap.add_argument("--size", default="1280 720")
    ap.add_argument("--route-out", type=Path, default=ROOT / "tools/tests/2026-11-21-personnages-spatioport.txt")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    layout = json.loads((args.city_bank / "layout.json").read_text(encoding="utf-8"))
    lat, lon = float(layout["anchor"][0]), float(layout["anchor"][1])
    terminal = next(x for x in layout["instances"] if x["id"] == "space_terminal")
    pad = layout["earthworks"]["pads"][int(terminal["pad"])]
    pad_cx, pad_cy, cos_a, sin_a, _hu, _hv, _r, _pz = pad
    deck_z = float(terminal["position"][2])

    def uv_to_city(u: float, v: float):
        return pad_cx + u * cos_a - v * sin_a, pad_cy + u * sin_a + v * cos_a

    def aim(cam_uv, tgt_uv, cam_h: float, tgt_h: float):
        cx, cy = uv_to_city(*cam_uv)
        tx, ty = uv_to_city(*tgt_uv)
        dist = math.hypot(tx - cx, ty - cy)
        heading = math.degrees(math.atan2(tx - cx, ty - cy))
        pitch = math.degrees(math.atan2(cam_h - tgt_h, max(dist, 1e-3)))
        return cx, cy, cam_h, pitch, heading

    # Sun angles relative to city anchor: noon, golden dusk, warm low-sun sunset.
    sun_noon = (lat + 16.0, lon - 20.0)
    sun_dusk = (lat - 6.0, lon - 84.0)
    sun_twilight = (lat - 8.0, lon - 89.0)

    specs = [
        ("01_terminal_closeup_noon", "Gros plan terminal (midi)", aim((-26.2, -4.6), (-30.0, -2.0), 1.55, 1.25), sun_noon),
        ("02_concourse_walk_noon", "Parvis et allee pietonne (midi)", aim((-18.5, 12.5), (-7.0, -4.0), 1.85, 1.10), sun_noon),
        ("03_shuttle_crew_noon", "Equipage au pied de la navette (midi)", aim((10.5, -19.5), (17.5, -10.0), 1.75, 1.45), sun_noon),
        ("04_canopy_lounge_noon", "Ombriere et terrasse pavee (midi)", aim((-12.0, -21.0), (-0.5, -13.5), 1.75, 1.10), sun_noon),
        ("05_concourse_dusk", "Parvis au couchant", aim((-25.5, -5.0), (-12.0, 4.0), 1.75, 1.15), sun_dusk),
        ("06_spaceport_wide", "Spatioport vue ensemble", aim((-32.0, -22.0), (-2.0, -2.0), 14.0, 1.0), sun_noon),
        ("07_concourse_twilight", "Parvis au crepuscule", aim((-26.0, -4.5), (-30.0, -2.0), 1.60, 1.20), sun_twilight),
        ("08_portrait_closeup_sun", "Portrait visage et peau (soleil rasant)", aim((-29.9, -3.2), (-31.0, -2.5), 1.64, 1.58), sun_twilight),
        ("09_pilot_portrait_noon", "Portrait pilote Style B (midi)", aim((-30.4, -2.4), (-29.0, -1.6), 1.50, 1.36), sun_noon),
        ("10_traveler_portrait_noon", "Portrait citoyenne Style B (midi)", aim((-4.3, -12.2), (-5.0, -14.0), 1.48, 1.32), sun_noon),
    ]

    job_lines = []
    route_lines = [
        "# Milestone 1 rigged MPFB2 characters around the extended city spaceport (Pad 43).",
        f"# Launch with: powershell -NoProfile -ExecutionPolicy Bypass -File tools\\lance.ps1 -Ville {args.city_bank.as_posix()} -Personnages {args.char_bank.as_posix()} -Parcours tools\\tests\\2026-11-21-personnages-spatioport.txt",
    ]
    for name, label, (cx, cy, ch, pitch, heading), (slat, slon) in specs:
        la, lo = geographical(lat, lon, cx, cy)
        job_lines.append(f"{args.out / name}.bmp natural {ch:.3f} {la:.10f} {lo:.10f} {pitch:.3f} {heading:.3f} 2 0 {slat:.6f} {slon:.6f}")
        route_lines.append(f"{label} | {deck_z + ch:.3f} {la:.10f} {lo:.10f} {pitch:.3f} {heading:.3f} | {slat:.6f} {slon:.6f}")

    # Add a grounded FPS walking start right on the spaceport plaza for interactive inspection!
    wcx, wcy = uv_to_city(-23.0, 1.0)
    wtx, wty = uv_to_city(-30.0, -2.0)
    wla, wlo = geographical(lat, lon, wcx, wcy)
    whead = math.degrees(math.atan2(wtx - wcx, wty - wcy))
    route_lines.append(f"Marcher sur le spatioport | {deck_z + 1.68:.3f} {wla:.10f} {wlo:.10f} 0.000 {whead:.3f} marche | {sun_noon[0]:.6f} {sun_noon[1]:.6f}")

    jobs_path = args.out / "views.txt"
    jobs_path.write_text("\n".join(job_lines) + "\n", encoding="utf-8")

    env = {k: v for k, v in os.environ.items() if not k.startswith("MYPLANETENGINE_")}
    env.update(
        MYPLANETENGINE_BATCH=str(jobs_path),
        MYPLANETENGINE_CITY_ASSETS=str(args.city_bank),
        MYPLANETENGINE_CHARACTER_ASSETS=str(args.char_bank),
        MYPLANETENGINE_RESOLUTION=args.size,
        MYPLANETENGINE_FULLSCREEN="0",
        MYPLANETENGINE_VSYNC="0",
        MYPLANETENGINE_SCANS=str(ROOT.parent / "scans"),
        MYPLANETENGINE_TIME="0 0",
        MYPLANETENGINE_TAA="1",
        MYPLANETENGINE_FOLIAGE_WARMUP="48",
        MYPLANETENGINE_FOLIAGE_SAMPLES="1",
    )

    with (args.out / "engine.log").open("w", encoding="utf-8") as log:
        res = subprocess.run(
            [str(args.exe)],
            cwd=args.exe.parent,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=600,
        )
    if res.returncode != 0:
        raise RuntimeError(f"Character native capture failed ({res.returncode}); inspect {args.out / 'engine.log'}")

    captured = []
    for name, _label, *_ in specs:
        bmp = args.out / f"{name}.bmp"
        im = Image.open(bmp).convert("RGB")
        arr = np.asarray(im)
        if arr.std() < 1.0:
            raise ValueError(f"Blank native capture: {name}")
        png = bmp.with_suffix(".png")
        im.save(png)
        captured.append({"name": name, "png": str(png), "sha256": sha(png)})
        print(f"[review_native] captured {png} (std={arr.std():.1f})")

    args.route_out.write_text("\n".join(route_lines) + "\n", encoding="utf-8")
    (args.out / "report.json").write_text(
        json.dumps({"exe_sha256": sha(args.exe), "captures": captured, "route": str(args.route_out)}, indent=2),
        encoding="utf-8",
    )
    print(f"[review_native] wrote user review route -> {args.route_out}")


if __name__ == "__main__":
    main()
