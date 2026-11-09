"""Exact pruning of zero-contribution river work; correctness only, no timing benchmark."""
import numpy as np

import cp
from verifie_lames import direction


def unpruned_noise(ctx, q, wave, salt):
    f = cp.R / wave
    c, qq = cp._lattice(q, f, 0)
    n = cp._weight(ctx, f) * cp._gradient(cp._corner_hashes(c), qq, cp._rseed(cp.RIVER_SEED)+salt, True)
    return np.clip(n / (2.*cp.SIGMA), -1., 1.)


def bandwidth():
    rng = np.random.default_rng(1914)
    p = rng.normal(size=(1024, 3))
    p /= np.linalg.norm(p, axis=1)[:, None]
    saved = cp._lattice, cp.PLANET_SEED
    zeros = 0
    def forbidden(*args, **kwargs):
        raise AssertionError('A zero-weight octave must return before building or hashing its lattice.')
    try:
        for seed in (0, 1):
            cp.PLANET_SEED = seed
            for wave in (12000., 3000., 2400., 750., 180., 45., 11.25):
                boundary = wave/cp.MESH_BAND_LIMIT
                for scale in (.01, .49, .5, .75, .999999, 1., 1.000001, 2., 100.):
                    ctx = cp.Ctx(scale*boundary)
                    expected = unpruned_noise(ctx, p, wave, 19)
                    if cp._weight(ctx, cp.R/wave) == 0.:
                        cp._lattice = forbidden
                        zeros += 1
                    try:
                        actual = cp._course_noise(ctx, p, wave, 19)
                    finally:
                        cp._lattice = saved[0]
                    assert np.array_equal(actual, expected), (seed, wave, scale)
    finally:
        cp._lattice, cp.PLANET_SEED = saved
    print(f'126 octave/footprint/seed combinations are bit-identical; {zeros} fully filtered cases perform no lattice work.')


def unpruned_connector(optimized):
    def former(ctx, v, u):
        k = optimized(ctx, v, u)
        # Reconstruct the former, unused wet opening on a dry connector; everything else is unchanged.
        if u['stops'][2] >= 1. and 2.**k['lq'][0] <= cp.RIVER_Q[1]:
            t = np.array([k['junction']])
            tangent = cp._course_tangent(v['main'], t)[0]
            m, q, valley = cp._meander(ctx, v['main'], t, (tangent/np.linalg.norm(tangent))[None], valley=True)
            q = q[0]
            along = tangent-(tangent@q)*q
            along /= np.linalg.norm(along)
            left = np.cross(along, q)
            flow = along+np.clip(m[1, 0]+m[3, 0], -1., 1.)*left
            flow /= np.linalg.norm(flow)
            arrival = k['xyz'][2]-k['xyz'][1]
            turn = float(flow@np.cross(arrival/np.linalg.norm(arrival), q))
            side = np.sign(turn)*cp._smooth(0., np.sin(np.radians(cp.RIVER_JUNCTION[0])), abs(turn))
            width = float(cp.erosion_river_size(2.**cp._bez(v['main']['lq'], t)[0])[0])
            k['flare'] = np.array([width*float(cp._width_factor(ctx, q[None], valley[1])[0]), width, side])
        return k
    return former


def composed():
    # These sites cover both hemispheres, large rivers, dry heads and a near-parallel confluence.
    centres = ((-6.05, 125.95), (-32.328588383, 85.6696902), (42.69313, -175.950838))
    saved = cp._course_noise, cp._connector
    count = 0
    for centre in centres:
        p = cp.window(direction(*centre), 80000., 20)
        for footprint in (2., 40., 375., 1500., 6000., 20000.):
            ctx = cp.Ctx(footprint)
            after = cp._relief_ground(ctx, p)
            try:
                cp._course_noise, cp._connector = unpruned_noise, unpruned_connector(saved[1])
                before = cp._relief_ground(ctx, p)
            finally:
                cp._course_noise, cp._connector = saved
            for key in ('carve', 'fill', 'coverage', 'bed', 'stage', 'flow', 'bank'):
                assert np.array_equal(after['rivers'][key], before['rivers'][key]), (centre, footprint, key)
            assert np.array_equal(after['elev'], before['elev']), (centre, footprint, 'terrain')
            count += len(p)
    print(f'{count} composed samples across three regions and six footprints retain identical terrain, water, banks and current.')


def footprint_bound():
    words, n = cp.erosion_map()
    cell = 2.*cp.R/n
    rng = np.random.default_rng(28)
    points = np.vstack((rng.normal(size=(64, 3)), np.eye(3), [[1., 1., 1.], [1., .9999, -.9999]]))
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    checked = seam = tighter = 0
    for p in points:
        face, x = cp._elocate(p[None], n)
        t1, t2 = cp.tangent_basis(p[None])
        for radius in (2., 4000., 20000., 100000.):
            corner = 3.*radius/(cell*max(1.-2.*radius/cp.R, .5))
            reach = cp._river_footprint_reach(p[None], x, n, radius)[0]
            if np.any(x-corner < 1.) or np.any(x+corner > n-3.):
                assert np.array_equal(reach, [corner, corner])
                seam += 1
                continue
            tighter += int(np.any(reach < corner))
            lo = np.floor(x[0]-reach).astype(int)-1
            hi = np.floor(x[0]+reach).astype(int)+2
            for angle in np.linspace(0., 2.*np.pi, 32, endpoint=False):
                q = cp.move(p[None], np.cos(angle)*t1+np.sin(angle)*t2, np.array([radius]))
                f, y = cp._elocate(q, n)
                assert f[0] == face[0]
                origin = np.floor(y[0]).astype(int)-1
                assert np.all(origin >= lo) and np.all(origin+3 <= hi), (p, radius, angle)
                checked += 1
    print(f'{checked} interior footprint-edge searches covered; {tighter} tighter bounds; {seam} face-edge halos unchanged.')


def footprint_composed():
    saved = cp._river_footprint_reach
    def former(p, x, n, radius):
        return np.full_like(x, 3.*radius/(2.*cp.R/n*max(1.-2.*radius/cp.R, .5)))
    count = 0
    centres = ((-6.05, 125.95), (-32.328588, 85.66969), (42.69313, -175.950838), (35.26438, 45.))
    for centre in centres:
        p = cp.window(direction(*centre), 80000., 12)
        for footprint in (2., 1000., 6000., 20000., 100000.):
            ctx = cp.Ctx(footprint)
            after = cp._relief_ground(ctx, p)
            try:
                cp._river_footprint_reach = former
                before = cp._relief_ground(ctx, p)
            finally:
                cp._river_footprint_reach = saved
            for key in ('carve', 'fill', 'coverage', 'bed', 'stage', 'flow', 'bank'):
                assert np.array_equal(after['rivers'][key], before['rivers'][key]), (centre, footprint, key)
            assert np.array_equal(after['elev'], before['elev']), (centre, footprint, 'terrain')
            count += len(p)
    print(f'{count} composed samples retain identical fields with the tighter interior footprint search.')


if __name__ == '__main__':
    bandwidth()
    composed()
    footprint_bound()
    footprint_composed()
    print('ok')
