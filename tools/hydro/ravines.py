"""The 'ravines' variants of etude_relief.py: gullies added to the no-erosion relief, per point. CPU prototype.

ravines, from published principles only (Grenier et al. 2024; the eroded-noise lineage, Clay John 2018 to runevision
2026, from their descriptions, no code read):
- Octaves of gullies, periods TOP down to BOTTOM, halving, each bent by one warp octave. Each is a stripe pattern running
  down the slope of everything coarser than it: the no-erosion relief keeping wavelengths from 2 periods (STEER_FILTER),
  plus the coarser gully octaves at CASCADE of their slope. A gully on the wall of a coarser one runs into it at an angle:
  branching by cascade.
- Per octave, each corner of a 3D lattice cell of PERIODS periods anchors the stripes at a pivot jittered by its hash;
  the corners blend by the quintic fade. Where their phases cancel, a gully ends or two gullies merge.
- Profile: a V trough, a rounded interfluve, zero mean (2 |cos(u / 2)| - 4 / pi of the blended phase u).
- Amplitude: BETA x period x the steering slope, saturated at SLOPE_CAP. Flats and summits get nothing; the change along
  the flow is bounded by a fraction of the slope the octave rides on (pits are measured, not excluded).
- Then the land (no gullies under the sea), the rock (erodibility), the climate (humidity) and the relief (mountains).
The steering slope is computed here by finite differences of a filtered relief on a grid; the engine would carry it
analytically through its octave loop, as ReliefDetail already does for its own gullies.

ravines_moteur: the engine's own gullies (ReliefDetail's, through cp.py) on the no-erosion relief, every point treated as
a carved valley wall, with no valley carved and no sea cliffs: an adapter around cp.elevation.
"""
import math

import numpy as np

import cp
from arbre import Frame

TOP, BOTTOM = 5000.0, 4.0      # gully periods (m) of the first and last octaves, halving; a 10 km octave drew
                               # parallel stripes over the no-erosion relief's own valleys
PERIODS = 1                    # stripe periods per lattice cell: gully length between blends
JITTER = 0.8                   # pivot jitter, share of a cell
BETA = 0.15                    # amplitude = BETA x period x slope: side slopes up to 2 pi BETA, 0.94, of that slope
STEER_ROUNDING = 1.0           # a coarser gully steers an octave with its trough rounded over the octave's period
CASCADE = 0.5                  # and with half its slope: the steering turns less, so stripes far from their pivot crowd less
SLOPE_CAP = 0.8                # the steering slope saturates there (tanh): no runaway on the cascade's steep walls
LAND = (0.0, 50.0)             # m: gullies fade in over the first 50 m of the filtered relief above the sea
ROCK = (0.5, 2.0)              # erodibility clipped there; amplitude x its square root
WET = (0.6, 1.0)               # amplitude factor from humidity 0 (desert) to 1 (wet)
PLAINS = 0.6                   # amplitude factor on plains, 1 in mountains (relief 300 to 1200 m, as cp's mountains)
ROUNDING = (2.0, 0.1)          # the V trough is rounded over 2 cells or 10 % of the period, whichever is wider
WARP = (0.2, 2.0)              # each octave's point bent by one noise octave: 0.2 period, wavelength 2 periods; sinuous
PAD = 4                        # cells computed around the window for the finite differences
STEER = 8                      # steering grid: samples per period (at least the window's cell)
STEER_FILTER = 1.0             # the steering relief filtered at a cell of 1 period: wavelengths from 2, fully from 4 periods.
                               # Finer, its turns compress the stripes far from their pivots into bundles of scratches
SEED = 20                      # cp._rseed(SEED) + octave: seeds no other relief brick uses


def _resample(g, x):
    """Cubic B-spline matrix (len(x), len(g)) from the regular axis g to the positions x: C2, so the steering varies
    smoothly between grid nodes (linear and Catmull-Rom reads left straight creases along the grid lines)."""
    u = np.clip((x - g[0]) / (g[1] - g[0]), 1.0, len(g) - 2.000001)
    i = np.floor(u).astype(int)
    w, _ = cp._weights(u - i)
    m = np.zeros((len(x), len(g)))
    for j in range(4):
        np.add.at(m, (np.arange(len(x)), i - 1 + j), w[:, j])
    return m


def steering(frame, axis, cell, period):
    """The no-erosion relief filtered for an octave (cell STEER_FILTER periods) and its gradient (x east, y north), on a
    grid of period / STEER, read at the grid axis (columns east, rows north to south): (height (N,), gradient (N, 2),
    relief evaluations)."""
    step = max(period / STEER, cell)
    m = int(np.ceil((axis[-1] - axis[0]) / step)) + 5
    g = (np.arange(m) - 2.0) * step + axis[0]
    x, y = np.meshgrid(g, g)
    z = cp.elevation(cp.Ctx(STEER_FILTER * period), frame.sphere(np.stack((x.ravel(), y.ravel()), 1)), valleys=False)
    z = z.reshape(m, m)
    gy, gx = np.gradient(z, step)
    rx, ry = _resample(g, axis), _resample(g, -axis)
    read = lambda a: (ry @ a @ rx.T).ravel()
    return read(z), np.stack((read(gx), read(gy)), 1), m * m


def octave(p, period, across, seed, o):
    """One gully octave's blend at the unit vectors p, stripes of the given period (m) across the unit tangent `across`:
    (m cos u, m sin u), u the phase (trough at pi), m the blend's strength in [0, 1]. Each lattice corner anchors the
    stripes at a pivot jittered by its hash, so the pattern ignores the sign of `across`."""
    c, q = cp._lattice(p, cp.R / (PERIODS * period), o)
    s = cp._fade(q, True)
    k = cp._seed_term(seed)
    re, im = np.zeros(len(p)), np.zeros(len(p))
    for i, h in enumerate(cp._corner_hashes(c)):
        r = cp._mix(h + k)
        jitter = np.stack((r & 1023, (r >> 10) & 1023, (r >> 20) & 1023), 1) / 1023.0 - 0.5
        corner = np.array([i & 1, (i >> 1) & 1, i >> 2], np.float64)
        phase = 2.0 * math.pi * PERIODS * ((q - corner - JITTER * jitter) * across).sum(1)
        w = np.where(corner > 0.5, s, 1.0 - s).prod(1)
        re += w * np.cos(phase)
        im += w * np.sin(phase)
    m = np.hypot(re, im)
    boost = 2.0 - m  # contrast: the blend's strength m becomes m (2 - m), 1 at full strength
    return re * boost, im * boost


def profile(re, m, rounding):
    """The gully profile of a blend (re = m cos u): 2 |cos(u / 2)| m with the trough rounded over `rounding` radians of
    phase, less its mean: a V trough at u = pi, a rounded interfluve."""
    u = np.linspace(0.0, 2.0 * math.pi, 512, endpoint=False)
    mean = np.sqrt(2.0 * (1.0 + np.cos(u)) + rounding * rounding).mean()
    return np.sqrt(np.maximum(2.0 * m * (m + re), 0.0) + (rounding * m) ** 2) - mean * m


def environment(p, d):
    """Amplitude factor from the rock, the climate and the relief at the points (no-erosion extra fields d)."""
    rock = np.sqrt(np.clip(cp.erodibility(p), *ROCK))
    wet = WET[0] + (WET[1] - WET[0]) * cp.humidity(cp.climate(p)["precipitation"])
    relief = PLAINS + (1.0 - PLAINS) * cp._smooth(300.0, 1200.0, d["relief"])
    return rock * wet * relief


def counted(f, *args, **kw):
    """f(*args) and the lattice cells it hashed (8 corners each: one gradient-noise octave per point)."""
    calls, original = [0], cp._corner_hashes

    def counting(c):
        calls[0] += len(c)
        return original(c)
    cp._corner_hashes = counting
    try:
        return f(*args, **kw), calls[0]
    finally:
        cp._corner_hashes = original


def relief(points, cell, fine_period=0.0):
    """The ravines relief on a cp.window grid: (height, sea depth, metrics, no-erosion extra fields and 'gullies_fine',
    the octaves of period below fine_period), all at the points. Computed on the grid grown by PAD cells, so the finite
    differences of the cascade have no edge."""
    n = int(round(math.sqrt(len(points))))
    frame, ctx, N = Frame(points.sum(0)), cp.Ctx(cell), n + 2 * PAD
    axis = (np.arange(N) + 0.5 - PAD) * cell - 0.5 * n * cell
    x, y = np.meshgrid(axis, -axis)
    p = frame.sphere(np.stack((x.ravel(), y.ravel()), 1))
    d, cells = counted(cp.elevation, ctx, p, extra=True, valleys=False)
    env = environment(p, d)
    total, parts, fine = np.zeros(len(p)), [], np.zeros(len(p))
    octaves, steer_evaluations, period, k = 0, 0, TOP, 0
    grad = lambda a: np.stack([g.ravel() for g in np.gradient(a, cell)[::-1]], 1) * [1.0, -1.0]  # (east, north)
    while period >= BOTTOM and cp._weight(ctx, cp.R / period) > 0.0:
        hc, G, evaluations = steering(frame, axis, cell, period)
        steer_evaluations += evaluations
        # The coarser gullies steer too, their troughs rounded at this octave's scale: on their walls this octave runs
        # into them; along their axis, only within half a period of it.
        if parts:
            coarser = sum(A * profile(re, m, 2.0 * math.pi * STEER_ROUNDING * period / P) for A, re, m, P in parts)
            G = G + CASCADE * grad(coarser.reshape(N, N))
        S = np.hypot(G[:, 0], G[:, 1])
        a2 = np.stack((-G[:, 1], G[:, 0]), 1) / np.maximum(S, 1e-12)[:, None]
        across = a2[:, :1] * frame.e + a2[:, 1:] * frame.n
        across -= p * (across * p).sum(1, keepdims=True)
        amp = BETA * period * SLOPE_CAP * np.tanh(S / SLOPE_CAP) * env * cp._smooth(*LAND, hc) * cp._weight(ctx, cp.R / period)
        rounding = 2.0 * math.pi * max(ROUNDING[0] * cell / period, ROUNDING[1])
        bent = cp.turbulence(ctx, p, cp.R / (WARP[1] * period), WARP[0] * period / (cp.SIGMA * cp.R), 1,
                             cp._rseed(SEED) + 32 + k)
        re, im = octave(bent, period, across, cp._rseed(SEED) + k, k)
        m = np.hypot(re, im)
        total += amp * profile(re, m, rounding)
        if period < fine_period:
            fine += amp * profile(re, m, rounding)
        parts.append((amp, re, m, period))
        octaves += 1
        period *= 0.5
        k += 1
    crop = lambda a: a.reshape((N, N) + a.shape[1:])[PAD:-PAD, PAD:-PAD].reshape((n * n,) + a.shape[1:])
    d = {key: crop(a) for key, a in dict(d, gullies_fine=fine).items() if isinstance(a, np.ndarray) and len(a) == len(p)}
    total = crop(total)
    h = d["elev"] + total
    extra = dict(gully_octaves=octaves, noise_cells_sans=cells / len(p), noise_cells_added=2.0 * octaves,
                 steering_relief_evaluations_per_sample=steer_evaluations / len(p),
                 gully_rms_m=float(np.sqrt(np.mean(total ** 2))),
                 new_sea_share=float(np.mean((h < 0.0) & (d["elev"] >= 0.0))))
    return h, np.maximum(-h, 0.0), extra, d


def moteur(points, cell):
    """The engine's gullies on the no-erosion relief: cp.elevation with a valley map that carves nothing but marks every
    land point as a valley wall (carved = 1) steered by the large forms' slope; no carve, no sea cliffs."""
    ctx, N = cp.Ctx(cell), len(points)
    warped = cp.turbulence(ctx, points, cp.R_KM / cp.RELIEF_WARP_TOP, cp.RELIEF_WARP / (cp.SIGMA * cp.R_KM),
                           cp.RELIEF_WARP_OCTAVES, cp._rseed(0))
    slope = cp.tectonic_fields(warped)["forms_gradient"] / (1000.0 * cp.R_KM)

    def valleys(p, cell_km, walls, seed=None):
        zero, low, high = np.zeros(N), np.full(N, -1e9), np.full(N, 1e9)
        return dict(surface=low, gradient=slope.copy(), floor=zero, level=zero, glacier=zero, incision=zero, deposit=low,
                    channel_bed=high, channel_surface=high, lake_level=zero, flow=np.zeros((N, 3)), walls=walls,
                    links=[dict(z=high.copy()) for _ in range(2)], box_radius=max(1000.0 * cell_km, cp.CREASE_MIN_CELL))
    saved = cp.erosion_valleys, cp.erosion_carve, cp.erosion_coast
    cp.erosion_valleys, cp.erosion_carve, cp.erosion_coast = valleys, lambda h, *_: h, lambda p, h, *_: h
    try:
        d, cells = counted(cp.elevation, ctx, points, extra=True, valleys=True)
    finally:
        cp.erosion_valleys, cp.erosion_carve, cp.erosion_coast = saved
    return d["elev"], d["water_depth"], dict(noise_cells_per_sample=cells / N)


if __name__ == "__main__":
    # The trough is the minimum, the profile has zero mean over a phase turn, and the octave is bounded.
    u = np.linspace(0.0, 2.0 * math.pi, 100001)[:-1]
    m, re = 1.0, np.cos(u)
    v = np.sqrt(2.0 * m * (m + re)) - 4.0 / math.pi
    assert abs(v.mean()) < 1e-6 and abs(u[v.argmin()] - math.pi) < 1e-3
    from verifie_lames import direction
    p = cp.window(direction(-7.138614, 122.604860), 2000.0, 64)
    a = np.tile(np.cross(p[:1], [0.0, 1.0, 0.0]), (len(p), 1))
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    re, im = octave(p, 100.0, a, 7, 3)
    x = profile(re, np.hypot(re, im), 0.0)
    assert x.min() >= -4.0 / math.pi - 1e-9 and x.max() <= 2.0 - 4.0 / math.pi + 1e-9
    print("ok")
