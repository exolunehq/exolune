"""Correctness of surviving midpoint flow and physical lake/sea mouths. No benchmark."""
import numpy as np

import cp
from verifie_raccords import section


def midpoints():
    words, n = cp.erosion_map()
    data = cp._flow_words[cp.PLANET_SEED][:, 0]
    candidates = np.flatnonzero(((data >> 16) & 1) != 0)
    full = int(np.ceil(8.*(np.log2(cp.RIVER_Q[2])+8.)))
    candidates = candidates[((data[candidates] >> 8) & 255) >= full]
    total, rerouted = 0, 0
    for c in candidates:
        v = cp._node_courses(int(c))
        if v is None:
            continue
        r = int(cp._eneighbour(np.array([c]), np.array([int(words[c, 1]) & 7]), n)[0])
        receiver = cp._node_courses(r)
        if receiver is None:
            continue
        # The source still supplies this midpoint; the receiving node no longer receives this edge's flow.
        expected = (data[c] & 255)/8.-8.
        assert v['main']['lq'][2] == expected, (c, 'source', v['main']['lq'], expected)
        incoming = int(cp._eneighbour(np.array([r]), np.array([receiver['main_inflow']]), n)[0])
        if incoming == c:
            k = receiver['main']
        else:
            k = cp._connector(cp.Ctx(2.), receiver, v['r'])
            rerouted += 1
        assert k['lq'][0] == expected, (c, 'receiver', k['lq'], expected)
        total += 1
    assert total > 100 and rerouted > 0, 'Exercise both main halves and rerouted tributaries across the planet.'
    print(f'Broken-edge discharge: both sides agree at {total} surviving midpoints, including {rerouted} connectors.')


def mouth():
    # Regression witness from the reported coastal gap. The production rule has no geographical condition.
    k = dict(cp._node_courses(1205820)['main'], fan=np.zeros(3))
    end = .5*k['stops'][0]
    widths = []
    for t in np.linspace(max(0., end-.08), end-1e-5, 4):
        x, wet, _ = section(k, t, span=1000., step=1., height=100.)
        widths.append(float(np.ptp(x[wet])))
    assert widths[-1] > 2.*widths[0] and np.all(np.diff(widths) > 0), widths
    print(f'Contact mouth opens on high pre-erosion support, before the shore: {widths} m.')
    for level in (0., 100.):
        lifted = dict(k, stage=k['stage']+level)
        _, wet, out = section(lifted, end, span=1000., height=level+100., lake=level)
        stage = out['stage']/np.maximum(out['weight'], 1e-9)
        assert np.max(np.abs(stage[wet]-level)) < 1e-5
        assert np.any(wet)
        if level == 0.:
            baseline = wet
        else:
            assert np.array_equal(wet, baseline)
    # For contacts close to either end of either half, the aperture starts at zero and grows monotonically.
    for split in (False, True):
        for limit in (.001, .05, .4, .99):
            course = dict(k, stops=np.array([limit, limit]), split=split)
            for start, span in ((0., .5), (.5, .5)) if split else ((0., 1.),):
                t = start+span*np.linspace(0., limit, 65)
                a = cp.river_mouth_share(course, t, np.zeros_like(t), np.full_like(t, 200.))
                assert a[0] == 0. and abs(a[-1]-1.) < 1e-12 and np.all(np.diff(a) >= -1e-12)
    print('Same receiving aperture and level for sea and lake; short-contact approaches remain continuous.')


def coastal_gap():
    k = cp._node_courses(1205308)['main']
    t = np.linspace(.4, 1., 257)
    tangent = cp._course_tangent(k, t)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    m, p = cp._meander(cp.Ctx(2.), k, t, tangent)
    normal = np.cross(tangent, p)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    p += ((m[0]+m[2])/cp.R)[:, None]*normal
    p /= np.linalg.norm(p, axis=1, keepdims=True)
    g = cp.elevation(cp.Ctx(2.), p, extra=True)
    wet = (g['water_coverage'] > .99) | (g['elev'] < 0.)
    assert np.all(wet), f'{np.count_nonzero(~wet)} dry gaps before the receiving course.'
    print(f'Reported coastal reach: {len(t)} successive samples stay wet up to the shared midpoint.')


def interval_union():
    rng = np.random.default_rng(1105)
    # Independent endpoint partition, including contained intervals and branches outside the footprint.
    cases = [([-2., -.1, .2], [2., .1, .3]), ([1., -1., 0.], [1., 1., 0.])]
    for _ in range(3000):
        centres = rng.uniform(-3., 3., 3)
        widths = 10.**rng.uniform(-3., 1., 3)
        cases.append((np.clip(centres-widths, -1., 1.), np.clip(centres+widths, -1., 1.)))
    for lower, upper in cases:
        lo, hi = np.clip(lower, -1., 1.), np.clip(upper, -1., 1.)
        knots = np.unique(np.r_[lo, hi])
        mid = .5*(knots[1:]+knots[:-1])
        covered = np.any((mid[:, None] > lo) & (mid[:, None] < hi), axis=1)
        expected = np.sum(np.diff(knots)[covered])*.5
        actual = cp.river_interval_coverage(lo, hi, 1.)
        assert abs(actual-expected) < 2e-15, (lo, hi, actual, expected)
        single = cp.river_interval_coverage(lo.astype(np.float32), hi.astype(np.float32), np.float32(1.))
        assert abs(single-expected) < 4e-7
    from verifie_raccords import fixture_courses
    k = dict(fixture_courses(1205821)[0])['outlet']
    for amount in (.001, .01, .03, .1, .4, 1.):
        course = dict(k, fan=np.full(3, amount))
        _, _, out = section(course, .3, span=3000.)
        assert not np.any((out['cut'] > 1e-5) & (out['coverage'] < 1e-8)), amount
    print(f'Wet union: {len(cases)} interval partitions and six nascent fans have no false dry strip.')


def coastal_composition():
    from verifie_lames import direction
    # Every location uses the same two independent envelopes, also where one process is absent.
    for lat, lon in ((-9.0403, 127.415), (-9.0405123, 127.2443788), (-13.2600946, 136.819891),
                     (8.73276, -103.30263), (-3.21606, 169.25336)):
        p = cp.window(direction(lat, lon), 6000., 64)
        ctx = cp.Ctx(2.)
        g = cp._relief_ground(ctx, p, True)
        substrate = cp._relief_ground(ctx, p, True, False)
        assert np.array_equal(g['_wave'][1], substrate['_wave'][1]), 'Wave erosion must not read a lowered river floor.'
        finished = cp.elevation(ctx, p, extra=True)
        assert np.all(np.isfinite(finished['elev']))
    # This former rectangular pool lay on dry land and arose only after the second coastal cut.
    p = cp.window(direction(-9.0403, 127.415), 6000., 160)
    base = cp._relief(cp.Ctx(2.), p, True, False)['elev']
    current = cp.elevation(cp.Ctx(2.), p, extra=True)
    unwanted = (base > 30.) & (current['elev'] < 0.) & (current['river_coverage'] < .1)
    assert np.count_nonzero(unwanted) == 0, np.count_nonzero(unwanted)
    print('Five coastal substrates agree; the reported dry-land window has no spurious marine pool.')


if __name__ == '__main__':
    midpoints()
    mouth()
    coastal_gap()
    interval_union()
    coastal_composition()
    print('ok')
