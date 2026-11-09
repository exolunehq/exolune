"""Requested Part C CPU checks. No engine, rendering or bench.

--before-file is the pre-Part-C cp.py snapshot; both versions read the same current engine caches.
Run from the worktree root. The snapshot defaults to x64/Release/cp-avant-pentes.py.
"""
import argparse
import hashlib
import sys
import types
from pathlib import Path

import numpy as np
import cp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cotes"))
import verifie_falaises as cliffs

PLACES = [(34.1611352, -73.72443), (-48.3497, -44.8221), (-38.1080, 166.4916), (44.16, -60.08), (-46.9, -33.8)]
COASTS = [(8.54005, -103.23344), (-23.01696, 158.00809), (-3.34285, 169.01181),
          (-51.89165, -40.94037), (-8.11021, 131.04460), (8.76166, -103.24998)]


def load_before(path):
    source = Path(path).read_bytes()
    old = types.ModuleType("before_slopes")
    old.__file__ = cp.__file__
    exec(compile(source, str(path), "exec"), old.__dict__)
    print(f"before source SHA256 {hashlib.sha256(source).hexdigest()}", flush=True)
    return old


def without_gullies(model, points):
    original = model.detail
    def bare(*args, **kwargs):
        args = list(args)
        if len(args) > 14:
            args[14] = None
        kwargs.pop("gullies", None)
        return original(*args, **kwargs)
    model.detail = bare
    try:
        return model.elevation(model.Ctx(1.0), points)
    finally:
        model.detail = original


def slope_stats(height):
    gy, gx = np.gradient(height.reshape(101, 101), 1.0)
    angle = np.degrees(np.arctan(np.hypot(gx, gy)))
    return np.array([100.0 * np.mean(angle > t) for t in (35.0, 45.0, 60.0)] + [angle.max()])


def windows(old):
    for index, (lat, lon) in enumerate(PLACES):
        # window() takes the cells' total span: 101 centres over 101 m put its endpoints 100 m apart.
        points = cp.window(cliffs.direction(lat, lon)[0], 101.0, 101)
        before = old.elevation(old.Ctx(1.0), points)
        after = cp.elevation(cp.Ctx(1.0), points)
        resolved = cp.elevation(cp.Ctx(0.25), points)
        assert np.array_equal(after, resolved), "the fully resolved gully rule changed with the mesh"
        bare_old, bare_new = without_gullies(old, points), without_gullies(cp, points)
        pre = cp.elevation(cp.Ctx(1.0), points, valleys=False)
        pre_old = old.elevation(old.Ctx(1.0), points, valleys=False)
        # E corrects the valleys' angular distance and active-floor mask. Those legitimately move the bare carved
        # surface; compare the undisturbed noise with valleys=False, where neither carve nor floor mask intervenes.
        assert np.array_equal(pre_old, pre), np.max(abs(pre_old-pre))
        print(f'  bare carved surface change: {np.max(abs(bare_old-bare_new)):.9f} m; undisturbed noise bit-identical', flush=True)
        stats = [slope_stats(z) for z in (before, after, bare_new, pre)]
        for label, values in zip(("before", "after", "without gullies", "valleys=false"), stats):
            print(f"({lat}, {lon}) {label}: >35/>45/>60 {values[0]:.6f}/{values[1]:.6f}/{values[2]:.6f}%; "
                  f"max {values[3]:.6f} deg", flush=True)
        print(f"  gully height effect after: {np.max(abs(after-bare_new)):.9f} m; "
              f"mean before/after change {np.mean(after-before):.6f} m (a local window, not a phase mean)", flush=True)
        if index < 4:
            assert stats[1][1] <= stats[3][1] + 3.0, stats
        else:
            # E judges kilometre rock incisions on 5 km, not on a 100 m rectangle which can lie on one flank.
            wide = cp.window(cliffs.direction(lat, lon)[0], 5025.0, 201)
            z = cp.elevation(cp.Ctx(25.0), wide).reshape(201, 201)
            gy, gx = np.gradient(z, 25.0)
            angles = np.degrees(np.arctan(np.hypot(gx, gy)))
            print(f'  rock-scale window, 5 km at 25 m: >60 {100*np.mean(angles>60):.6f}%', flush=True)
            assert np.any(angles > 60.0), 'the broad rock incision window lost its walls'
        if index < 2:
            p = cliffs.direction(lat, lon)
            north = np.array([0.0, 1.0, 0.0]) - p * p[:, 1:2]
            north /= np.linalg.norm(north)
            transect = cp.move(p, north, np.arange(0.0, 25.0001, 0.25))
            for label, model in (("before", old), ("after", cp)):
                z = model.elevation(model.Ctx(1.0), transect)
                print(f"  north {label}: max {np.degrees(np.arctan(abs(np.diff(z)).max()/0.25)):.6f} deg; "
                      f"rise/0.5m {(z[2:]-z[:-2]).max():.9f} m; abs/0.5m {abs(z[2:]-z[:-2]).max():.9f} m", flush=True)


def analytic():
    rng = np.random.default_rng(7465)
    under, normal, stripe, share = rng.random((4, 20000)) * np.array([[2.0], [2.0], [20.0], [1.0]])
    gain = cp._gully_gain(under, normal, stripe, share)
    left = np.maximum(cp.EROSION_GULLY_CRITICAL - under - normal, 0.0)
    assert ((gain >= 0.0) & (gain <= 1.0)).all()
    assert np.all(gain * share * (normal + stripe) <= left + 1e-12)
    assert np.all(gain[left == 0.0] == 0.0)
    mean_abs = 0.5 * (1.0 + cp.MEAN_BILLOW[True])
    scale = 0.5 * np.pi * mean_abs
    x = scale * np.cos((np.arange(200000) + 0.5) * np.pi / 200000)
    worst = 0.0
    for rounding in (0.0001, 0.03, 0.1, 0.5, 1.0, 2.0):
        e = np.full_like(x, rounding * scale)
        value, _ = cp._rcrease(x, e)
        delta, _ = cp._sharpen_crease(x, e, np.full_like(x, cp.EROSION_GLACIAL_SHARPEN))
        worst = max(worst, abs((cp._stripe_mean(e)-value-delta).mean()))
    assert worst < 1e-8, worst
    print(f"analytic: octave reserve respected; centred stripe mean error <= {worst:.3g}", flush=True)


def coasts(old):
    for lat, lon in COASTS:
        points = cp.window(cliffs.direction(lat, lon)[0], 60000.0, 201)
        values = []
        for model in (old, cp):
            cliffs.cp = model
            values.append(cliffs.evaluate(points, 10.0))
        before, after = values
        # Compare Hc at identical places, independently of the coast's changed active footprint.
        error = np.max(abs(before[2]-after[2]))
        active = (before[0] >= 0.0) & (before[0] <= before[2]) & (before[0]-before[1] > 1.0)
        q = np.percentile(before[2][active], [50, 90, 100]) if active.any() else np.zeros(3)
        active_after = (after[0] >= 0.0) & (after[0] <= after[2]) & (after[0]-after[1] > 1.0)
        q_after = np.percentile(after[2][active_after], [50, 90, 100]) if active_after.any() else np.zeros(3)
        print(f"Hc ({lat}, {lon}): before median/p90/max {q}; after active {q_after}; "
              f"n {active.sum()} -> {active_after.sum()}; max field change {error:.9g} m", flush=True)
        # The main spherical relief now supplies Hc. Bit identity with the former coastal estimator is no longer
        # required; evaluate() above still checks lowering, contour bounds and unchanged high ground.
    cliffs.cp = cp
    rng = np.random.default_rng(917)
    points = rng.normal(size=(288, 3))
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    for seed in (0, 1):
        cp.PLANET_SEED = old.PLANET_SEED = seed
        for cell in (1.0, 1000.0, 30000.0):
            a = old.elevation(old.Ctx(cell), points, valleys=False)
            b = cp.elevation(cp.Ctx(cell), points, valleys=False)
            assert np.array_equal(a, b), np.max(abs(a-b))
        print(f"valleys=false: seed {seed}, 288 points x 3 cell sizes, bit-identical", flush=True)
    cp.PLANET_SEED = old.PLANET_SEED = 0
    points = cp.window(cliffs.direction(16.71, -89.28)[0], 10000.0, 21)
    a, b = old.elevation(old.Ctx(10.0), points), cp.elevation(cp.Ctx(10.0), points)
    print(f"flat coast: max change {np.max(abs(a-b)):.9g} m", flush=True)
    assert np.array_equal(a, b), np.max(abs(a-b))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-file", default="x64/Release/cp-avant-pentes.py")
    parser.add_argument("--only", choices=("analytic", "windows", "coasts"))
    args = parser.parse_args()
    old = load_before(args.before_file)
    if args.only in (None, "analytic"):
        analytic()
    if args.only in (None, "windows"):
        windows(old)
    if args.only in (None, "coasts"):
        coasts(old)
    print("ok", flush=True)
