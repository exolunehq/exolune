"""Self-check of step A's ravines (cp.py, mirror of Relief.hlsli's ReliefDetail; docs/spec-erosion.md, the ravines).

Run from the repository root: python tools/hydro/verifie_ravines.py
- each octave's analytic gradient against finite differences, its steering held fixed, at several points and footprints;
- the steering's Jacobians (the warp's, the map's slopes) against finite differences;
- the whole ravine sum's gradient against finite differences, steering free: the residual is the steering's own turning,
  which the analytic gradient holds fixed; printed, bounded;
- continuity along a line crossing many lattice cells, and across the footprint's octave fades;
- no ravines at sea nor on a flat ground;
- the pre-erosion form (valleys=False) bit-identical whether the switch is on or off.
"""
import math

import numpy as np

import cp
from verifie_lames import direction

SITES = dict(massif=(-7.138614, 122.604860), chaine_enneigee=(-25.6, -26.94), montagnes_humides=(42.693130, -175.950838))


def octave(p, across, k, rounding):
    """Ravine octave k at the points p, `across` fixed: (profile, its gradient per metre), as ReliefDetail draws it."""
    first = cp.RAVINE_PERIODS[0]
    x0 = p * (cp.R / (2.0 * first))
    c0 = np.floor(x0)
    u = (x0 - c0) * 2.0 ** k
    fu = np.floor(u)
    re, m, dre, dm = cp._ravine_blend(c0.astype(np.int64) * 2 ** k + fu.astype(np.int64), u - fu, p, across, first * 0.5 ** k, k)
    v, a, b = cp._ravine_profile(re, m, rounding)
    return v, a[:, None] * dre + b[:, None] * dm


def fd(f, p, t1, t2, step):
    """f's finite-difference gradient along the tangents t1, t2 (metres)."""
    out = 0.0
    for t in (t1, t2):
        out = out + ((f(cp.move(p, t, np.full(len(p), step))) - f(cp.move(p, t, np.full(len(p), -step)))) / (2.0 * step))[:, None] * t
    return out


def main():
    rng = np.random.default_rng(7)
    worst = 0.0
    for site in SITES.values():
        p = cp.window(direction(*site), 20000.0, 12)
        t1, t2 = cp.tangent_basis(p)
        a = rng.random(len(p)) * 2.0 * math.pi
        across = np.cos(a)[:, None] * t1 + np.sin(a)[:, None] * t2
        for k in (0, 3, 6, 10):
            period = cp.RAVINE_PERIODS[0] * 0.5 ** k
            for cell in (0.5, 2.0, 0.3 * period):  # the trough's rounding at three footprints
                r = 2.0 * math.pi * max(cp.RAVINE_ROUNDING[0] * cell / period, cp.RAVINE_ROUNDING[1])
                _, g = octave(p, across, k, r)
                tangential = lambda v: v - p * (v * p).sum(1, keepdims=True)
                e = fd(lambda q: octave(q, across, k, r)[0], p, t1, t2, 1e-4 * period)
                worst = max(worst, np.abs(tangential(g) - e).max() / np.abs(e).max())
    print(f"octave gradient, steering fixed: max error {worst:.1e} of the largest slope")
    assert worst < 1e-4

    # The steering's Jacobians: the detail warp's (RlTurbulenceJacobian) and the map's slope on the sphere (ReliefMapSlope).
    q = rng.normal(size=(300, 3))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    ctx = cp.Ctx(10.0)
    warp = (cp.R_KM / cp.RELIEF_DETAIL_WARP[0], cp.RELIEF_DETAIL_WARP[1] / (cp.SIGMA * cp.R_KM), 3, cp._rseed(4))
    j = cp.turbulence_jacobian(ctx, q, *warp)
    for axis in range(3):
        d = np.zeros(3)
        d[axis] = 1e-7
        e = (cp.turbulence(ctx, q + d, *warp) - cp.turbulence(ctx, q - d, *warp)) / 2e-7
        assert np.abs(e - j[:, :, axis]).max() < 1e-6
    t1, t2 = cp.tangent_basis(q)
    m = cp.tectonic_fields(q)
    e = 0.0
    for t in (t1, t2):
        e = e + ((cp.tectonic_fields(q + 1e-7 * t)[0][:, 0] - cp.tectonic_fields(q - 1e-7 * t)[0][:, 0]) / 2e-7)[:, None] * t
    error = np.linalg.norm(cp._map_slope(m["forms_gradient"], q) - e, axis=1) / np.linalg.norm(e, axis=1).max()
    raw = m["forms_gradient"] - q * (m["forms_gradient"] * q).sum(1, keepdims=True)
    print(f"map slope on the sphere: error {np.percentile(error, 90):.1e} (p90), the map's own gradient "
          f"{np.percentile(np.linalg.norm(raw - e, axis=1) / np.linalg.norm(e, axis=1).max(), 90):.1e}")
    assert np.percentile(error, 90) < 1e-3

    # The whole sum, steering free.
    for cell in (200.0, 20.0, 2.0):
        res, size = [], []
        for site in SITES.values():
            p = cp.window(direction(*site), 300.0 * cell, 16)
            ctx = cp.Ctx(cell)
            t1, t2 = cp.tangent_basis(p)
            g = cp.elevation(ctx, p, extra=True)["ravine_slope"]
            e = fd(lambda q: cp.elevation(ctx, q, extra=True)["ravines"], p, t1, t2, 0.01 * cell)
            res.append(np.linalg.norm(g - e, axis=1))
            size.append(np.linalg.norm(e, axis=1))
        rel = math.sqrt(np.mean(np.concatenate(res) ** 2) / np.mean(np.concatenate(size) ** 2))
        print(f"ravine sum's gradient, steering free, cell {cell:g} m: rms residual {rel:.2f} of the rms slope")
        assert rel < 0.5

    # Continuity: a 2 km line at 2 m cells, its steps halved; then the footprint swept through the octaves' fades.
    c = direction(*SITES["chaine_enneigee"])
    t1, t2 = cp.tangent_basis(c[None])
    ctx = cp.Ctx(2.0)
    jumps = []
    for step in (0.5, 0.25):
        s = np.arange(0.0, 2000.0, step)
        h = cp.elevation(ctx, cp.move(np.repeat(c[None], len(s), 0), np.repeat(t1, len(s), 0), s), extra=True)["ravines"]
        jumps.append(np.abs(np.diff(h)).max())
    print(f"along a line: largest step {jumps[0]:.3f} m at 0.5 m, {jumps[1]:.3f} m at 0.25 m")
    assert jumps[1] < 0.7 * jumps[0]
    p = cp.window(c, 3000.0, 8)
    cells = 0.5 * 1.03 ** np.arange(0, 312)
    h = np.stack([cp.elevation(cp.Ctx(x), p, extra=True)["ravines"] for x in cells])
    change = np.abs(np.diff(h, axis=0)).max()
    print(f"footprint from {cells[0]:g} m to {cells[-1]:.0f} m by 3 %: largest change {change:.2f} m, "
          f"ravines up to {np.abs(h).max():.0f} m")
    assert change < 0.1 * np.abs(h).max()

    # None at sea, none on a flat ground.
    q = rng.normal(size=(4000, 3))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    d = cp.elevation(cp.Ctx(100.0), q, extra=True)
    below = cp.elevation(cp.Ctx(100.0), q, valleys=False)
    sea = (d["large"] + d["volcanoes"] < -1000.0) & (below < -1000.0)
    # The land fade reads each octave's steering ground: under 200 m of sea, finer octaves than it may still dip.
    shallow = (below < -200.0) & ~sea
    print(f"at sea: {sea.sum()} points 1000 m under, ravines {np.abs(d['ravines'][sea]).max():g} m; "
          f"{shallow.sum()} other points under 200 m, ravines up to {np.abs(d['ravines'][shallow]).max():.2f} m")
    assert sea.sum() > 1000 and np.all(d["ravines"][sea] == 0.0)
    n = 64
    p = cp.window(c, 1000.0, 8)
    flat = dict(carved=np.zeros(n), ground=np.full(n, 500.0), surface=np.full(n, 1e9), valley_slope=np.zeros((n, 3)),
                incision=np.zeros(n), slope=np.zeros((n, 3)), share=np.zeros(n), glacial=np.zeros(n), ravines=np.ones(n),
                oriented=np.broadcast_to(np.eye(3), (n, 3, 3)))
    out = []
    cp.detail(cp.Ctx(1.0), p, p, 3, cp.RELIEF_DETAIL_TOP, cp.RELIEF_OCTAVES, np.zeros(n), np.full(n, 0.5), np.zeros(n),
              cp._rseed(1), wide_octaves=1, gullies=flat, ravines=out)
    print(f"on a flat ground: ravines {np.abs(out[0][0]).max():g} m")
    assert np.all(out[0][0] == 0.0) and np.all(out[0][1] == 0.0)

    # The pre-erosion form, the level 0's input, whether step A is on or off.
    q = q[:1000]
    saved = cp.EROSION_RAVINES
    try:
        forms = []
        for on in (True, False):
            cp.EROSION_RAVINES = on
            forms.append(cp.elevation(cp.Ctx(30.0), q, valleys=False))
    finally:
        cp.EROSION_RAVINES = saved
    assert forms[0].tobytes() == forms[1].tobytes()
    print("pre-erosion form: bit-identical with the switch on and off")
    print("ok")


if __name__ == "__main__":
    main()
