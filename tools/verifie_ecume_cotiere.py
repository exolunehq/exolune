"""Correctness of the water-conditioned coastal foam mean. No renderer or benchmark."""
import math
import numpy as np


def cdf(x):
    return .5*np.vectorize(math.erfc)(-np.asarray(x)/math.sqrt(2.))


NODES, WEIGHTS = np.polynomial.legendre.leggauss(12)
REF_NODES, REF_WEIGHTS = np.polynomial.legendre.leggauss(256)


def probability(depth, spread, height, sigma):
    """Sea.hlsli's CoastalFoam probability, before its energy gate and coverage coefficient."""
    total = float(cdf((height-.39*depth)/math.sqrt(sigma*sigma+.1521*spread*spread)))
    if depth > 5.*spread:
        return total
    wet = float(cdf(depth/spread))
    if height > 5.*sigma:
        return np.clip((total-cdf(-depth/spread))/wet, 0., 1.)
    if height < -5.*sigma:
        return 0.
    lo = max(0., depth-5.*spread)
    hi = min(max(depth, 0.)+5.*spread, max(height+5.*sigma, 0.)/.39)
    if hi <= lo:
        return 0.
    half, centre = .5*(hi-lo), .5*(hi+lo)
    z = centre+half*NODES
    density = np.exp(-.5*((z-depth)/spread)**2)/(math.sqrt(2.*math.pi)*spread)
    return np.clip(half*np.sum(WEIGHTS*density*cdf((height-.39*z)/sigma))/wet, 0., 1.)


def reference(depth, spread, height, sigma):
    # Independent 256-point quadrature over an eight-sigma domain. It explicitly excludes dry columns.
    lo = max(0., depth-8.*spread)
    hi = min(max(depth, 0.)+8.*spread, max(height+8.*sigma, 0.)/.39)
    if hi <= lo:
        return 0.
    half, centre = .5*(hi-lo), .5*(hi+lo)
    z = centre+half*REF_NODES
    density = np.exp(-.5*((z-depth)/spread)**2)/(math.sqrt(2.*math.pi)*spread)
    return half*np.sum(REF_WEIGHTS*density*cdf((height-.39*z)/sigma))/cdf(depth/spread)


def check():
    rng = np.random.default_rng(1104)
    error = 0.
    cases = zip(10.**rng.uniform(-2, 3, 10000), 10.**rng.uniform(-1.7, .3, 10000),
                rng.uniform(-3., 3., 10000), rng.uniform(-4., 8., 10000))
    for spread, sigma, height, ratio in cases:
        depth = ratio*spread
        value = probability(depth, spread, height, sigma)
        assert np.isfinite(value) and 0. <= value <= 1.
        error = max(error, abs(value-reference(depth, spread, height, sigma)))
    assert error < .0002, error
    # A coarse mixed coast must not turn its dry fraction into a bright foam band.
    coarse = [probability(0., spread, 0., .5) for spread in (1., 10., 100., 1000.)]
    assert np.all(np.diff(coarse) < 0.) and coarse[-1] < .001, coarse
    # A resolved incident crest generates foam near shore; a trough and deep water do not.
    assert probability(.5, .02, 1., .02) > .99
    assert probability(.5, .02, -1., .02) < 1e-6
    assert probability(100., 1., 0., 1.) < 1e-6
    print(f'10,000 conditional wave/depth cases: maximum coverage error {error:.6g}; finite and bounded.')
    print(f'Mixed-coast probability decreases with footprint depth spread: {coarse}.')
    print('Resolved crest, trough and deep-water limits pass; no dry-area foam contribution.')


if __name__ == '__main__':
    check()
