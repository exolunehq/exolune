"""Conservation of a river valley across footprints and sampling phases; no benchmark."""
import numpy as np

import cp


def quadrature():
    rng = np.random.default_rng(1193549)
    errors = []
    for i in range(256):
        bank = rng.uniform(2., 100.)
        floor = rng.uniform(2.*bank, 2000.)
        outer = floor+rng.uniform(300., 5000.)
        lv = rng.uniform(-outer, outer)
        s = dict(along=0. if i % 3 else rng.uniform(0., 1200.), lv=lv, lc=lv+rng.uniform(-.6*floor, .6*floor),
                 ratio=rng.uniform(.71, 1.41), F=floor, D=outer, lq=rng.uniform(8., 13.), bank=bank,
                 keep=max(4.*bank, .6*floor), rough=rng.uniform(-.3, 10.), height=rng.uniform(-20., 5000.),
                 spur=rng.uniform(0., 2000.), fill=1., share=1.)
        radius = np.exp(rng.uniform(np.log(2.), np.log(20000.)))
        x = np.linspace(-radius, radius, 32769)
        reference = np.trapezoid(cp.river_corridor_profile(x, s), x)/(2.*radius)
        result = cp.river_corridor_mean({k: np.array([v]) for k, v in s.items()}, radius)[0]
        errors.append(abs(result-reference)/max(abs(s['height']), 1.))
    assert max(errors) < 4e-4, max(errors)
    print(f'256 composed sections: independent dense quadrature, maximum normalized error {max(errors):.3g}.')


def sliding_cells():
    s = dict(along=0., lv=0., lc=-75., ratio=1., F=200., D=3000., lq=9., bank=35., keep=150.,
             rough=1., height=3000., spur=1100., fill=1., share=1.)
    dense = np.linspace(-s['D'], s['D'], 65537)
    reference = np.trapezoid(cp.river_corridor_profile(dense, s), dense)
    errors, point_errors = [], []
    for radius in (2., 32., 128., 512., 2048., 8192.):
        spacing = 2.*radius
        for phase in np.linspace(0., 1., 9)[:-1]:
            centres = (np.arange(-int(s['D']/spacing)-3, int(s['D']/spacing)+4)+phase)*spacing
            a = {k: np.full(len(centres), v) for k, v in s.items()}
            a['lv'] += centres
            a['lc'] += centres
            area = cp.river_corridor_mean(a, radius).sum()*spacing
            errors.append(abs(area/reference-1.))
            point_area = cp.river_corridor_profile(centres, s).sum()*spacing
            point_errors.append(abs(point_area/reference-1.))
    assert max(point_errors) > 1., 'The witness must expose missed/oversampled valleys.'
    assert max(errors) < .002, max(errors)
    print(f'48 footprint/phase combinations: incision area conserved within {max(errors):.2%}; '
          f'point sampling error reaches {max(point_errors):.0%}.')


def water_moments():
    rng = np.random.default_rng(7)
    coverage = rng.random((512, 16))
    coverage[:, :8] = 0.
    weights = rng.random((512, 16))
    weights /= weights.sum(1)[:, None]
    stage, depth, speed = 1732., 2.7, 1.3
    moments = coverage[..., None]*np.array([1., stage, depth, speed])
    filtered = np.sum(weights[..., None]*moments, axis=1)
    # Two different resolutions can cover different fractions of a pixel without changing conditional water.
    other = np.linspace(0., 1., len(filtered))[:, None]*np.array([1., stage, depth, speed])
    for blend in np.linspace(0., 1., 17):
        mixed = filtered*(1.-blend)+other*blend
        wet = mixed[:, 0] > 0.
        assert np.allclose(mixed[wet, 1:]/mixed[wet, :1], [stage, depth, speed], atol=1e-10)
    print('Wet moments: constant stage, depth and flow survive dry samples and resolution crossfades.')


def float_spur_cap():
    # A resolved lift below a millimetre can coexist with kilometres of bank allowance.
    # The former vector lerp subtracts nearly equal huge numbers and creates visible terrain walls.
    lift = np.geomspace(1e-9, 1e4, 151)[:, None]
    run = np.geomspace(.001, 20000., 173)[None, :]
    reference = cp.river_spur_bank_lift(lift, run)
    L, x = lift.astype(np.float32), run.astype(np.float32)
    B = np.float32(cp.RIVER_SPURS[2])*x*x/(x+np.float32(cp.RIVER_SPURS[1]/cp.RIVER_SPURS[2]))
    stable = np.minimum(L, B*(1.-.25*B/np.maximum(L, np.maximum(.5*B, 1e-9))))
    error = np.max(np.abs(stable-reference)/np.maximum(reference, 1e-9))
    assert error < 4e-7, error
    assert np.all(stable >= 0.)
    print(f'26123 float32 spur caps: maximum relative error {error:.2g}; tiny retained lifts preserved.')


def footprint_search():
    from verifie_lames import direction
    words, n = cp.erosion_map()
    cell = 2.*cp.R/n
    checked = 0
    # Include almost-corner directions, where the chart stretches most, and sliding node boundaries.
    for p in (np.array([1., .98, .98]), np.array([1., .02, -.99]), direction(-6.25, 125.34)):
        p = p/np.linalg.norm(p)
        face, x = cp._elocate(p[None], n)
        t1, t2 = cp.tangent_basis(p[None])
        for radius in (2., 128., 2048., 8192., 20000.):
            reach = cp._river_footprint_reach(p[None], x, n, radius)[0]
            lo, hi = np.floor(x[0]-reach).astype(int)-1, np.floor(x[0]+reach).astype(int)+2
            candidates = {int(cp._ecell(face, np.array([[a,b]]), n)[0])
                          for a in range(lo[0],hi[0]+1) for b in range(lo[1],hi[1]+1)}
            for angle in np.linspace(0., 2.*np.pi, 32, endpoint=False):
                q = cp.move(p[None], np.cos(angle)*t1+np.sin(angle)*t2, np.array([radius]))
                f, y = cp._elocate(q, n)
                assert f[0] == face[0], 'This chart-bound fixture must remain on the same face.'
                origin = np.floor(y).astype(int)-1
                local = {int(cp._ecell(f, origin+np.array([a,b]), n)[0]) for a in range(4) for b in range(4)}
                assert local <= candidates, 'The footprint misses a neighbouring physical search.'
                checked += 1
    print(f'{checked} footprint-edge searches: all neighbouring physical course candidates retained.')


if __name__ == '__main__':
    quadrature()
    sliding_cells()
    water_moments()
    float_spur_cap()
    footprint_search()
    print('ok')
