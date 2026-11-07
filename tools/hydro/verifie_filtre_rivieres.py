"""Correctness checks for the step-B channel filter; no rendering or performance measurements.

Independent Gauss quadrature of the physical, ground-clipped bank, then conservation of incision and wet area.
Run from the worktree root: python tools/hydro/verifie_filtre_rivieres.py
"""
import numpy as np

import cp
from verifie_lames import direction


NODES, WEIGHTS = np.polynomial.legendre.leggauss(24)


def physical(x, width, bank, above):
    shoulder = min(width, max(cp.RIVER_BANK_SHOULDER[0], cp.RIVER_BANK_SHOULDER[1]*bank))
    t = np.clip((np.abs(x)-width)/shoulder, 0., 1.)
    height = bank*t*t*(3.-2.*t) + cp.RIVER_STEEP_BANK*np.maximum(np.abs(x)-2.*width, 0.)
    return np.maximum(above-height, 0.)


def limits(width, bank, above):
    # Locate the zero by bisection on the actual profile, independent of the production inverse and primitive.
    lo, hi = 0., 2.*width + above/cp.RIVER_STEEP_BANK
    for _ in range(60):
        mid = .5*(lo+hi)
        if physical(mid, width, bank, above) > 0.:
            lo = mid
        else:
            hi = mid
    edge = .5*(lo+hi)
    shoulder = min(width, max(cp.RIVER_BANK_SHOULDER[0], cp.RIVER_BANK_SHOULDER[1]*bank))
    return np.array([-edge, -2.*width, -width-shoulder, -width, 0., width, width+shoulder, 2.*width, edge])


def integrate(f, breaks):
    edges = np.unique(breaks)
    centre = .5*(edges[1:]+edges[:-1])
    half = .5*np.diff(edges)
    x = centre[:, None] + half[:, None]*NODES
    return np.sum(half*np.sum(f(x)*WEIGHTS, axis=1))


def wet_sections():
    rng = np.random.default_rng(1104)
    error = 0.
    for width, depth, radius in zip(10.**rng.uniform(-1, 3, 120), 10.**rng.uniform(-2, 1, 120),
                                     10.**rng.uniform(-1, 4, 120)):
        bank = min(width, max(cp.RIVER_BANK_SHOULDER[0], cp.RIVER_BANK_SHOULDER[1]*depth))
        edges = np.array([-width, -width+bank, 0., width-bank, width])
        def wet(x):
            t = np.clip((width-np.abs(x))/bank, 0., 1.)
            return depth*t*t*(3.-2.*t)
        for x in rng.uniform(-width-radius, width+radius, 20):
            breaks = np.unique(np.clip(np.r_[x-radius, edges, x+radius], x-radius, x+radius))
            expected = integrate(wet, breaks)/(2.*radius)
            actual = cp.river_channel_mean(x, width, depth, radius)
            assert abs(actual-expected) < 1e-8*max(depth, 1.), (width, depth, radius, expected, actual)
            single = cp.river_channel_mean(*(np.float32(v) for v in (x, width, depth, radius)))
            error = max(error, abs(single-expected)/max(depth, 1.))
            assert error < 3e-4, error
        area = integrate(lambda x: cp.river_channel_mean(x, width, depth, radius),
                         np.unique(np.r_[edges-radius, edges+radius]))
        assert abs(area-depth*(2.*width-bank)) < 1e-8*max(depth*width, 1.)
    print(f'120 wet sections: independent quadrature and area pass; float32 relative error <= {error:.2g}.')


def check():
    wet_sections()
    rng = np.random.default_rng(1103)
    largest_relative = 0.
    cases = [(50., 2., 4000., 4000.), (50., 2., 2., 4000.), (50., 2., .2, 4000.)]
    cases += list(zip(10.**rng.uniform(-1., 3., 100), 10.**rng.uniform(-2., 2., 100),
                      10.**rng.uniform(-3., 4., 100), 10.**rng.uniform(.3, 4., 100)))
    for width, bank, above, radius in cases:
        edges = limits(width, bank, above)
        reach = max(abs(edges))+radius
        for d in rng.uniform(0., reach, 12):
            bounds = np.unique(np.clip(np.r_[d-radius, edges, d+radius], d-radius, d+radius))
            expected = integrate(lambda x: physical(x, width, bank, above), bounds)/(2.*radius)
            actual = cp.river_channel_bank_cut(d, width, bank, above, radius)
            assert abs(actual-expected) < 2e-9*max(above, 1.), (width, radius, d, expected, actual)
            floats = [np.float32(x) for x in (d, width, bank, above, radius)]
            single = float(cp.river_channel_bank_cut(*floats))
            relative = abs(single-expected)/max(above, 1.)
            largest_relative = max(largest_relative, relative)
            assert relative < 3e-4, (floats, expected, single)
        original = integrate(lambda x: physical(x, width, bank, above), edges)
        breaks = np.unique(np.r_[edges-radius, edges+radius, -reach, reach])
        filtered = integrate(lambda x: cp.river_channel_bank_cut(np.abs(x), width, bank, above, radius), breaks)
        assert abs(filtered-original) < 2e-8*max(original, 1.), (original, filtered)
        wet_breaks = np.array([-width-radius, -abs(width-radius), abs(width-radius), width+radius])
        wet = integrate(lambda x: cp.river_channel_coverage(np.abs(x), width, radius), wet_breaks)
        assert abs(wet-2.*width) < 2e-8*max(width, 1.), (width, radius, wet)
    print(f'{len(cases)} sections: independent quadrature, incision area and wet area pass; float32 relative error <= {largest_relative:.2g}')
    # A lower neighbouring corridor must still receive the compact wet cut. Otherwise the coverage renderer paints
    # a resolved channel over dry terrain and exact vegetation placement legitimately leaves trees in the water.
    points = cp.window(direction(-7.173005, 125.036219), 2000., 64)
    ground = cp.elevation(cp.Ctx(2.), points, extra=True)
    wet = (ground['water_coverage'] > 1.-1e-6) & (ground['water_depth'] > .02) & (ground['water_level'] > 0.)
    gap = np.maximum(ground['water_level']-ground['elev'], 0.)
    assert wet.sum() > 100, 'The confluence witness must contain resolved wet samples.'
    error = np.max(np.abs(ground['water_depth'][wet]-gap[wet]))
    assert error < 2e-5, f'Resolved water/terrain mismatch: {error:g} m'
    print(f'Resolved confluence: {wet.sum()} wet samples agree with the stage/bed gap.')


if __name__ == '__main__':
    check()
