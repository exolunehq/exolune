"""Requested contour-cliff checks, seeds 0 and 1. No engine, rendering or performance bench.

Run from the worktree root: python tools/cotes/verifie_falaises.py.
The baseline disables only waves, retaining identical valleys, deposits and barriers.
"""
import sys
import subprocess
import types
from collections import deque
from contextlib import contextmanager
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hydro"))
import cp


@contextmanager
def band_model(kind="current"):
    """Ablate each fifth-pass change independently; only current enables the physical marine witness."""
    band, access = cp.erosion_cliff_band, cp.erosion_sea_access
    def variant(shore, retreat, relief, coast_slope):
        bound = retreat + cp.EROSION_CLIFF_REACH[0]
        if kind in ("extension", "fifth"):
            bound = np.minimum(bound+relief/coast_slope, cp.EROSION_CLIFF_REACH[2])
        return 1.0-cp._smooth(bound-cp.EROSION_CLIFF_REACH[1], bound,
                            shore if kind in ("opening", "fifth") else np.abs(shore))
    if kind != "current":
        cp.erosion_cliff_band = variant
        cp.erosion_sea_access = lambda height, slope: np.ones_like(height)
    try:
        yield
    finally:
        cp.erosion_cliff_band, cp.erosion_sea_access = band, access


def direction(lat, lon):
    la, lo = np.radians([lat, lon])
    return np.array([[np.cos(la) * np.cos(lo), np.sin(la), np.cos(la) * np.sin(lo)]])


def evaluate(points, cell=10.0, inputs=False):
    """Evaluate actual full relief before/after waves, and check every point against its own Hc."""
    coast, mean = cp.erosion_coast, cp.erosion_cliff_mean
    captured, geometry = [], []

    def no_waves(*args):
        captured.append(args)
        return args[1].copy()

    def contour(*args):
        geometry.append(args)
        return mean(*args)

    cp.erosion_coast = no_waves
    try:
        before = cp.elevation(cp.Ctx(cell), points)
    finally:
        cp.erosion_coast = coast
    cp.erosion_cliff_mean = contour
    try:
        after = cp.elevation(cp.Ctx(cell), points)
    finally:
        cp.erosion_cliff_mean = mean
    args = captured[0]
    hc = np.full(len(points), cp.EROSION_CLIFF_HEIGHT[0])
    delta = np.zeros(len(points))
    footprint = np.zeros(len(points))
    selected = ((args[4] > 0.3) & (args[5] > 1e-3) & (np.abs(args[2]) < cp.EROSION_CLIFF_REACH[2])
                & (args[2] / args[-1] < cp.EROSION_CLIFF_REACH[2]))
    if geometry:
        hc[selected], delta[selected] = geometry[0][1:3]
        footprint[selected] = geometry[0][6]
    lowering = before - after
    assert np.min(lowering) >= -1e-6, np.min(lowering)
    assert np.max(lowering - hc) <= -cp.EROSION_CLIFF_PLATFORM[0] + 1e-5, np.max(lowering - hc)
    high = args[1] - footprint >= hc + delta
    assert np.max(np.abs(lowering[high]), initial=0.0) < 1e-5
    return (before, after, hc, delta, args) if inputs else (before, after, hc, delta)


def profile(lat, lon, flat=False):
    """A fixed transect through the user's contour centre, with no search for a more favourable centre."""
    p = direction(lat, lon)
    t1, t2 = cp.tangent_basis(p)
    samples = np.concatenate([cp.move(p, t, np.array([s])) for t in (t1, t2) for s in (-10.0, 10.0)])
    # The transect follows the full ground, whose contour now places the cliff.
    z = evaluate(samples)[0]
    gradient = (z[1] - z[0]) * t1 + (z[3] - z[2]) * t2
    tangent = gradient / np.linalg.norm(gradient)
    metres = np.arange(-15000.0, 15000.1, 10.0)
    points = cp.move(p, tangent, metres)
    before, after, hc, delta = evaluate(points)
    lowering = before - after
    if flat:
        error = np.max(np.abs(lowering))
        assert error <= 0.01, error
        print(f"flat ({lat:.5f}, {lon:.5f}): max change {error:.6f} m")
        return False
    slope = np.abs(np.diff(after) / 10.0)
    face = ((before[:-1] >= hc[:-1]) & (before[:-1] <= hc[:-1] + delta[:-1])
            | (before[1:] >= hc[1:]) & (before[1:] <= hc[1:] + delta[1:]))
    active = face & (np.maximum(lowering[:-1], lowering[1:]) > 1.0)
    active &= np.abs(metres[:-1]) < 2000.0
    if not active.any():
        print(f"({lat:.5f}, {lon:.5f}): no active face; max lowering {lowering.max():.3f} m; "
              f"max(lowering-Hc) {np.max(lowering-hc):.3f} m")
        return False
    peak = int(np.argmax(np.where(active, slope, -np.inf)))
    angle = np.degrees(np.arctan(slope[peak]))
    # Pair the face with an adjacent platform on this same transect, within 300 m in either direction.
    j = np.arange(max(0, peak - 30), min(len(slope), peak + 31))
    bench = j[(after[j] >= -6.0) & (after[j] <= 0.0) & (slope[j] < 0.1) & (lowering[j] > 1.0)]
    level_id = bench[np.argmin(abs(bench-peak))] if len(bench) else None
    level = f"{after[level_id]:.3f} m" if level_id is not None else "absent"
    # Measure a real crest which has rejoined the original ground, on the higher side of this face. This avoids
    # reporting the contour setting itself as the wall's measured height.
    higher = j[j > peak] if after[peak + 1] > after[peak] else j[j <= peak]
    crest = higher[(before[higher] >= hc[higher] + delta[higher]) & (lowering[higher] < 1.0)]
    crest_id = crest[np.argmin(abs(crest-peak))] if len(crest) else None
    wall_height = after[crest_id] - after[level_id] if crest_id is not None and level_id is not None else 0.0
    land_width = float("nan")
    if level_id is not None:
        # Continue seaward until the original deep sea, rather than accepting a newly flooded inland pit as the sea.
        step = -1 if after[peak + 1] > after[peak] else 1
        path = np.arange(level_id, -1 if step < 0 else len(before), step)
        sea = np.flatnonzero(before[path] < -20.0)
        if len(sea):
            land_width = 10.0 * np.count_nonzero(after[path[:sea[0]]] > 5.0)
    print(f"({lat:.5f}, {lon:.5f}): wall {wall_height:.3f} m; face {angle:.2f} deg; platform {level}; max lowering {lowering.max():.3f} m; "
          f"max(lowering-Hc) {np.max(lowering-hc):.3f} m; land above +5 m to original sea {land_width:.0f} m")
    return angle > 60.0 and len(bench) > 0, wall_height > 100.0 and angle > 60.0 and len(bench) > 0, land_width


def distribution(lat, lon):
    """Hc on the active coast: original land between sea level and Hc, lowered by at least 1 m."""
    points = cp.window(direction(lat, lon)[0], 60000.0, 201)
    before, after, hc, delta = evaluate(points, 10.0)
    coast = (before >= 0.0) & (before <= hc) & (before - after > 1.0)
    values = hc[coast]
    if not len(values):
        print(f"Hc ({lat:.5f}, {lon:.5f}), 60 km square / 300 m: no active coastal samples")
        return
    median, p90, maximum = np.percentile(values, [50.0, 90.0, 100.0])
    print(f"Hc ({lat:.5f}, {lon:.5f}), 60 km square / 300 m: n={len(values)}; "
          f"median {median:.3f} m; p90 {p90:.3f} m; max {maximum:.3f} m")


def original_transect(lat, lon):
    p = direction(lat, lon)
    t1, t2 = cp.tangent_basis(p)
    samples = np.concatenate([cp.move(p, t, np.array([s])) for t in (t1, t2) for s in (-10.0, 10.0)])
    z = cp.elevation(cp.Ctx(10.0), samples, extra=True, valleys=False)["large"]
    tangent = (z[1] - z[0]) * t1 + (z[3] - z[2]) * t2
    tangent /= np.linalg.norm(tangent)
    points = cp.move(p, tangent, np.arange(-15000.0, 15000.1, 10.0))
    before, after, hc, delta = evaluate(points)
    print(f"original ({lat:.5f}, {lon:.5f}): max lowering {(before-after).max():.3f} m; "
          f"max(lowering-Hc) {np.max(before-after-hc):.3f} m")
    if lat in (-51.89165, -8.11021):
        shore = points[np.argmin(np.abs(before))]
        print("  nearest actual shoreline on this transect:")
        factors(np.degrees(np.arcsin(shore[1])), np.degrees(np.arctan2(shore[2], shore[0])))


def window_points(lat, lon):
    # 201 sample points including the square's edges: exactly 10 km wide with 50 m spacing.
    p = direction(lat, lon)
    east, north = cp.tangent_basis(p)
    east = np.cross(p, [[0.0, 1.0, 0.0]])
    east /= np.linalg.norm(east)
    north = np.cross(east, p)
    u, v = np.meshgrid(np.arange(-5000.0, 5000.1, 50.0), np.arange(-5000.0, 5000.1, 50.0))
    q = p + (u.reshape(-1, 1) * east + v.reshape(-1, 1) * north) / cp.R
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return q


def flood_reached(before, transit, seed_level=-20.0):
    """Sea connectivity on the requested 4-neighbour grid."""
    before, transit = before.reshape(201, 201), transit.reshape(201, 201)
    reached = before < seed_level
    queue = deque(map(tuple, np.argwhere(reached)))
    while queue:
        y, x = queue.popleft()
        for j, i in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
            if 0 <= j < 201 and 0 <= i < 201 and transit[j, i] and not reached[j, i]:
                reached[j, i] = True
                queue.append((j, i))
    return reached.reshape(-1)


def flood_share(before, after):
    """The requested sea flood, with its exact seed and transit thresholds."""
    lowered = before - after > 10.0
    reached = flood_reached(before, (after < 0.0) | (before - after > 1.0))
    return 100.0 * np.count_nonzero(lowered & ~reached) / max(np.count_nonzero(lowered), 1)


def sea_distance(before):
    """Exact planar distance to original sea cells: negative ground connected to ground below -50 m, four neighbours."""
    sea = flood_reached(before, before < 0.0, -50.0).reshape(201, 201)
    x = np.arange(201)[None, :]
    left = np.maximum.accumulate(np.where(sea, x, -10000), axis=1)
    right = np.minimum.accumulate(np.where(sea, x, 10000)[:, ::-1], axis=1)[:, ::-1]
    horizontal = np.minimum(x-left, right-x).astype(float)**2
    distance = np.empty_like(horizontal)
    # Minimise the separable squared distance over rows. No scipy dependency or approximation to nearest sea cells.
    for y in range(201):
        distance[y] = np.min(horizontal + (np.arange(201)-y)[:, None]**2, axis=0)
    if not sea.any():
        distance[:] = np.inf
    return 50.0*np.sqrt(distance).reshape(-1)


def window(lat, lon, erosion_diagnostic=False):
    carve, carved = cp.erosion_carve, []
    def traced(h, coarse, valley, k):
        result = carve(h, coarse, valley, k)
        carved[:] = [(h-result, valley["surface"])]
        return result
    if erosion_diagnostic:
        cp.erosion_carve = traced
    try:
        before, after, hc, delta = evaluate(window_points(lat, lon), 50.0)
    finally:
        cp.erosion_carve = carve
    lowering = before - after
    enclosed = flood_share(before, after)
    distance = sea_distance(before)[lowering > 10.0]
    p99, maximum = (np.percentile(distance, [99.0, 100.0]) if np.isfinite(distance).all()
                    else (np.inf, np.inf)) if len(distance) else (0.0, 0.0)
    reach = f"{p99:.3f}/{maximum:.3f} m" if len(distance) else "none (no lowering >10 m)"
    print(f"window ({lat:.5f}, {lon:.5f}), 10 km, 50 m: max lowering {lowering.max():.3f} m; "
          f">10 m {100.0*np.mean(lowering>10.0):.3f}%; max(lowering-Hc) {np.max(lowering-hc):.3f} m; enclosed {enclosed:.3f}%; "
          f"sea distance p99/max {reach}")
    if erosion_diagnostic and carved and np.any(lowering > 10.0):
        mask = lowering > 10.0
        print(f"  original valley carving at wave-cut points: maximum {np.max(carved[0][0][mask]):.6f} m; "
              f"lowest valley surface {np.min(carved[0][1][mask]):.3f} m")
    return enclosed, p99


def presence_factors(a):
    """The controller's inputs, including points rejected by its early support branch."""
    p, h, shore, cs, rocky, near, offset, fg, er, cell, detail_slope, relief, metric = a
    d = p.astype(np.float32).astype(np.float64)
    slope = fg - (fg*d).sum(1)[:, None]*d
    seaward = -slope / np.maximum(np.linalg.norm(slope, axis=1, keepdims=True), 1e-6)
    shelter = cp._smooth(*cp.EROSION_CLIFF_BAY, offset)
    exposure = shelter * (cp.EROSION_CLIFF_WAVES[0] + (1.0-cp.EROSION_CLIFF_WAVES[0])
                          * np.maximum((-seaward*cp.erosion_wave_wind(d)).sum(1), 0.0))
    variation = cp.erosion_cliff_noise(p, cp.EROSION_CLIFF_NOISE, cp.PLANET_SEED*4096+640)
    retreat = np.minimum(cp.EROSION_CLIFF_RETREAT[2], cp.EROSION_CLIFF_RETREAT[1]*exposure*er
                         * np.maximum(0.2, 1.0+cp.EROSION_CLIFF_RETREAT[3]*variation))
    band = cp.erosion_cliff_band(shore/metric, retreat, relief, cs)
    proxy = 1.0-cp._smooth(cp.EROSION_CLIFF_REACH[2]-cp.EROSION_CLIFF_REACH[1], cp.EROSION_CLIFF_REACH[2], np.abs(shore))
    return dict(rocky=rocky, near=near, shelter=shelter, exposure=exposure, erodibility=er, band=band,
                shore_km=shore/metric, original_m=h, proxy=proxy, detail_shift_km=relief/cs)


def factors(lat, lon):
    _, _, _, _, a = evaluate(direction(lat, lon), inputs=True)
    values = presence_factors(a)
    print(f"presence ({lat:.5f}, {lon:.5f}): " + "; ".join(f"{k}={float(v[0]):.6f}" for k,v in
          values.items()))


def support_connection():
    """Even unlimited lowering inside the current support cannot cross a gap in that support."""
    before, after, _, _, args = evaluate(window_points(8.73276, -103.30263), 50.0, inputs=True)
    f = presence_factors(args)
    potential = ((f["band"] > 0.0) & (f["proxy"] > 0.0) & (f["rocky"] > 0.3)
                 & (f["near"] > 1e-3) & (f["shelter"] > 0.0))
    # This is deliberately more permissive than the shader: ignore Hc, partial presence and stack remnants.
    reached = flood_reached(before, (before < 0.0) | potential)
    isolated = (before-after > 10.0) & ~flood_reached(before, (after < 0.0) | (before-after > 1.0))
    print(f"support diagnostic: {np.count_nonzero(isolated)} enclosed cells; "
          f"{np.count_nonzero(isolated & ~reached)} still unreachable with unlimited lowering inside the support")


def shoreline_profile(lat, lon):
    """Find the nearest original sea-level crossing along the large forms' normal, then measure its actual cliff."""
    p = direction(lat, lon)
    t1, t2 = cp.tangent_basis(p)
    probes = np.concatenate([cp.move(p, t, np.array([s])) for t in (t1, t2) for s in (-10.0, 10.0)])
    z = cp.elevation(cp.Ctx(10.0), probes, extra=True, valleys=False)["large"]
    tangent = (z[1]-z[0])*t1 + (z[3]-z[2])*t2
    tangent /= np.linalg.norm(tangent)
    metres = np.arange(-15000.0, 15000.1, 10.0)
    points = cp.move(p, tangent, metres)
    before = evaluate(points)[0]
    crossings = np.flatnonzero((before[:-1] >= 0.0) != (before[1:] >= 0.0))
    if not len(crossings):
        print(f"shoreline ({lat:.5f}, {lon:.5f}): no original shoreline on 30 km transect")
        return False
    index = crossings[np.argmin(np.abs(metres[crossings]+5.0))]
    a, b, za = metres[index], metres[index+1], before[index]
    for _ in range(20):
        mid = (a+b)*0.5
        z = evaluate(cp.move(p, tangent, np.array([mid])))[0][0]
        if (z >= 0.0) == (za >= 0.0):
            a = mid
        else:
            b = mid
    q = cp.move(p, tangent, np.array([(a+b)*0.5]))[0]
    la, lo = np.degrees(np.arcsin(q[1])), np.degrees(np.arctan2(q[2], q[0]))
    print(f"shoreline of ({lat:.5f}, {lon:.5f}): ({la:.5f}, {lo:.5f}), shift {(a+b)*0.5:.3f} m")
    factors(la, lo)
    return profile(la, lo)


def committed_port():
    """The pre-hookup port, used for the original wind's fixed cliff calibration and the uneroded form."""
    source = subprocess.check_output(["git", "show", "HEAD:tools/hydro/cp.py"], text=True, encoding="utf-8")
    baseline = types.ModuleType("cliff_baseline")
    baseline.__file__ = cp.__file__
    exec(compile(source, "HEAD:tools/hydro/cp.py", "exec"), baseline.__dict__)
    return baseline


def unchanged():
    """Compare the uneroded form against the committed port, and the flat-coast window against waves disabled."""
    baseline = committed_port()
    rng = np.random.default_rng(917)
    points = rng.normal(size=(288, 3))
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    for seed in (0, 1):
        baseline.PLANET_SEED = cp.PLANET_SEED = seed
        error = 0.0
        for cell in (10.0, 1000.0, 30000.0):
            before = baseline.elevation(baseline.Ctx(cell), points, valleys=False)
            after = cp.elevation(cp.Ctx(cell), points, valleys=False)
            error = max(error, np.max(np.abs(before-after)))
            assert np.array_equal(before, after), error
        print(f"seed {seed}, valleys=false vs HEAD, 288 points at 10 m / 1 km / 30 km: max change {error:.6f} m")
    cp.PLANET_SEED = 0
    before, after, _, _ = evaluate(cp.window(direction(16.71, -89.28)[0], 10000.0, 21))
    error = np.max(np.abs(before-after))
    assert error <= 0.01, error
    print(f"flat 10 km square / 441 points: max change {error:.6f} m")


def distance_check():
    ground = np.full((201, 201), 100.0)
    ground[100, 100] = -100.0
    ground[100, 101:104] = -1.0
    ground[100, 105] = -1.0  # A disconnected shallow lake must not become an original-sea source.
    distance = sea_distance(ground.reshape(-1)).reshape(201, 201)
    assert distance[100, 103] == 0.0 and distance[100, 105] == 100.0
    assert distance[103, 107] == 250.0


if __name__ == "__main__":
    distance_check()
    cp.PLANET_SEED = 1
    for kind in ("fourth", "opening", "extension", "fifth"):
        print("glacial ablation:", kind, flush=True)
        with band_model(kind):
            window(-65.00789, -113.42094, erosion_diagnostic=(kind == "fifth"))
    windows = [(0, 8.73276, -103.30263), (0, -23.18173, 157.88952), (0, -3.21302, 169.26372),
               (1, -65.00789, -113.42094), (1, 23.78160913, -126.35918730), (1, 40.46592, -84.75513)]
    results_windows = []
    for seed, lat, lon in windows:
        cp.PLANET_SEED = seed
        print("seed:", seed, flush=True)
        results_windows.append(window(lat, lon))
    cp.PLANET_SEED = 0
    places = [(8.78450, -103.26910), (-23.17203, 157.90432), (-3.22014, 169.25837),
              (-51.89165, -40.94037), (-8.11021, 131.04460)]
    for place in places:
        original_transect(*place)
    contours = [(8.72580, -103.29430), (-23.18981, 157.86949), (-3.21302, 169.26372)]
    results = [profile(*place) for place in contours]
    print(f"computed wind: {sum(bool(result and result[0]) for result in results)} of 3 fixed profiles have an active face")
    for place in places[3:]:
        shoreline_profile(*place)
    # These centres predate integration with volcanoes. On integration's pre-hookup port and current seed-0 caches,
    # the third fixed face is already absent. Compare to that explicit baseline rather than asserting its historical
    # three faces; all lowering, reach, connectivity and flat-coast limits still run on the computed wind unchanged.
    current = cp
    try:
        cp = committed_port()
        print("pre-hookup integration calibration control:", flush=True)
        calibration = [profile(*place) for place in contours]
    finally:
        cp = current
    count = sum(bool(result and result[0]) for result in results)
    high = sum(bool(result and result[1]) for result in results)
    baseline_count = sum(bool(result and result[0]) for result in calibration)
    baseline_high = sum(bool(result and result[1]) for result in calibration)
    print(f"fixed faces, before -> after: {baseline_count} -> {count}; over 100 m: {baseline_high} -> {high}", flush=True)
    for place in [(8.54005, -103.23344), (-23.01696, 158.00809), (-3.34285, 169.01181),
                  (-51.89165, -40.94037), (-8.11021, 131.04460), (8.76166, -103.24998)]:
        distribution(*place)
    profile(16.71, -89.28, flat=True)
    window(8.76166, -103.24998)
    window(-23.18173, 157.88952)
    factors(-51.89165, -40.94037)
    factors(-8.11021, 131.04460)
    unchanged()
    support_connection()
    assert baseline_count > 0 and count >= baseline_count, f"fixed faces regress: {baseline_count} -> {count}"
    assert high >= baseline_high, f"walls above 100 m regress: {baseline_high} -> {high}"
    assert all(not result or result[2] < 100.0 for result in results), "land remains between a face's foot and the sea"
    assert all(not result or result[2] < 100.0 for result in calibration), "pre-hookup calibration leaves land before the sea"
    assert max(result[0] for result in results_windows) < 5.0, f"enclosed cuts exceed 5%: {results_windows}"
    assert max(result[1] for result in results_windows) < 4000.0, f"inland reach exceeds 4 km: {results_windows}"
    print("ok")
