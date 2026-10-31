"""Requested CPU checks for rounded glacial crests and the computed climate. No engine or bench.

Run from the worktree root; --before selects the baseline git revision (HEAD by default).
Both versions read the same existing level 0: this isolates local geometry, not a rebuilt drainage network.
"""
import argparse
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

import cp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cotes"))
import verifie_falaises as cliffs


def baseline(revision):
    source = subprocess.check_output(["git", "show", f"{revision}:tools/hydro/cp.py"], encoding="utf-8")
    module = types.ModuleType("crest_baseline")
    module.__file__ = cp.__file__
    exec(compile(source, f"{revision}:tools/hydro/cp.py", "exec"), module.__dict__)
    return module


def rounded_profile():
    """Check the whole analytic profile, including super-amplitude rounding and intermediate glacial shares."""
    scale = 0.5 * np.pi * 0.5 * (1.0 + cp.MEAN_BILLOW[True])
    x = scale * np.cos((np.arange(200000) + 0.5) * np.pi / 200000)
    worst_mean, worst_derivative = 0.0, 0.0
    for r in (0.0001, 0.01, 0.0999, 0.1001, 0.3, 0.9999, 1.0, 1.0001, 2.0, 10.0):
        for bend in (0.0, 0.15, 0.3, cp.EROSION_GLACIAL_SHARPEN):
            e, b = np.full_like(x, scale * r), np.full_like(x, bend)
            change, derivative = cp._sharpen_crease(x, e, b)
            worst_mean = max(worst_mean, abs(change.mean()))
            assert np.isfinite(change).all() and np.isfinite(derivative).all()
            assert abs(change.mean()) < 1e-8, (r, bend, change.mean())
            if bend == 0.0:
                assert np.array_equal(change, np.zeros_like(x))
            # Sample away from the piecewise joins; include the exact crest.
            probes = scale * np.array([-1.5, -0.8, -0.1, -1e-5, 0.0, 1e-5, 0.1, 0.8, 1.5])
            ep, bp = np.full_like(probes, scale * r), np.full_like(probes, bend)
            _, d = cp._sharpen_crease(probes, ep, bp)
            step = 1e-9
            fd = (cp._sharpen_crease(probes + step, ep, bp)[0]
                  - cp._sharpen_crease(probes - step, ep, bp)[0]) / (2.0 * step)
            worst_derivative = max(worst_derivative, np.max(np.abs(fd-d)))
            assert np.max(np.abs(fd-d)) < 2e-6, (r, bend, fd, d)
            assert d[4] == 0.0
            _, base_derivative = cp._rcrease(x, e)
            assert np.min((base_derivative+derivative)*np.sign(x)) >= -1e-10
    print(f"profile: mean change <= {worst_mean:.3g} noise units; derivative error <= {worst_derivative:.3g}; "
          "finite, monotone, zero slope at crest", flush=True)


def crests(old):
    for lat, lon in ((34.1611352, -73.72443), (-48.3497, -44.8221), (-46.9, -33.8)):
        p = cliffs.direction(lat, lon)
        north = np.array([0.0, 1.0, 0.0]) - p * p[:, 1:2]
        north /= np.linalg.norm(north)
        transect = cp.move(p, north, np.arange(0.0, 25.0001, 0.25))
        window = cp.window(p[0], 200.0, 201)
        for name, model in (("before", old), ("after", cp)):
            z = model.elevation(model.Ctx(1.0), transect)
            steepest = np.degrees(np.arctan(np.max(np.abs(np.diff(z))) / 0.25))
            rise = np.max(z[2:]-z[:-2])
            w = model.elevation(model.Ctx(1.0), window).reshape(201, 201)
            gy, gx = np.gradient(w, 1.0)
            angles = np.degrees(np.arctan(np.hypot(gx, gy)))
            # Use interior points, where the difference spans one metre on either side.
            share = 100.0 * np.mean(angles[1:-1, 1:-1] > 60.0)
            print(f"crest ({lat}, {lon}) {name}: north max {steepest:.3f} deg; rise/0.5m {rise:.6f} m; "
                  f"window >60deg {share:.6f}%; max {angles[1:-1, 1:-1].max():.3f} deg", flush=True)
        fields = cp.climate(p)
        print(f"  climate: P {fields['precipitation'][0]:.3f} mm/yr; T {fields['temperature'][0]:.3f} C; "
              f"ELA {old.erosion_equilibrium_line(p)[0]:.3f} -> {cp.erosion_equilibrium_line(p)[0]:.3f} m", flush=True)
        # The glacial chain must still respond to sharpening, at identical climate and level 0.
        if lat == -46.9:
            setting = cp.EROSION_GLACIAL_SHARPEN
            try:
                cp.EROSION_GLACIAL_SHARPEN = 0.0
                smooth = cp.elevation(cp.Ctx(1.0), window).reshape(201, 201)
            finally:
                cp.EROSION_GLACIAL_SHARPEN = setting
            gy, gx = np.gradient(smooth, 1.0)
            print(f"  sharpening under the soil budget: max height effect {np.max(np.abs(w-smooth)):.6f} m; "
                  f"unsharpened window max {np.degrees(np.arctan(np.hypot(gx, gy))).max():.3f} deg", flush=True)
            # The soil budget may remove the gully replacement entirely; the bedrock crests must remain sharp.
            wy, wx = np.gradient(w, 1.0)
            assert np.degrees(np.arctan(np.hypot(wx, wy))).max() >= 45.0


def coasts(old):
    places = [(8.54005, -103.23344), (-23.01696, 158.00809), (-3.34285, 169.01181),
              (-51.89165, -40.94037), (-8.11021, 131.04460), (8.76166, -103.24998)]
    for lat, lon in places:
        p = cliffs.direction(lat, lon)
        for name, model in (("before", old), ("after", cp)):
            cliffs.cp = model
            print(name, end=" ", flush=True)
            cliffs.distribution(lat, lon)
            wind = model.erosion_wave_wind(p)
            print(f"  wind force {np.linalg.norm(wind):.6f}", flush=True)
        fields = cp.climate(p)
        print(f"  wind E/N {fields['wind_east'][0]:.6f} / {fields['wind_north'][0]:.6f} m/s", flush=True)
    cliffs.cp = cp
    cliffs.unchanged()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", default="HEAD")
    parser.add_argument("--only", choices=("crests", "coasts", "profile"))
    args = parser.parse_args()
    old = baseline(args.before)
    print("Existing level 0 retained; no new global drainage/ice-share measurement.", flush=True)
    if args.only in (None, "profile"):
        rounded_profile()
    if args.only in (None, "crests"):
        crests(old)
    if args.only in (None, "coasts"):
        coasts(old)
    print("ok", flush=True)
