"""Correctness of retained spurs beside narrow upstream channels; no benchmark.

Run after the Release build: python tools/hydro/verifie_amont.py
The reported course is a regression fixture, never a terrain-generation exception.
"""
import numpy as np

import cp


def bank_envelope():
    lift = np.geomspace(.001, 10000., 201)[:, None]
    run = np.concatenate(([-10., 0.], np.geomspace(.001, 20000., 301)))[None, :]
    kept = cp.river_spur_bank_lift(lift, run)
    assert np.all((kept >= 0.) & (kept <= lift))
    assert np.all(kept <= cp.RIVER_SPURS[2]*np.maximum(run, 0.)), 'Tall spurs need horizontal room.'
    assert np.all(np.diff(kept, axis=0) >= -1e-12), 'A higher mountain must not recover less height.'
    assert np.all(np.diff(kept, axis=1) >= -1e-12)
    assert np.all(kept[:, :2] == 0.), 'The physical bank must stay clear.'
    # Ample room keeps the old terrain exactly, rather than flattening every broad valley.
    ample = 4.*(lift+cp.RIVER_SPURS[1])/cp.RIVER_SPURS[2]
    assert np.array_equal(cp.river_spur_bank_lift(lift, ample), lift)
    # Finite-difference slopes on both sides of the bank and the soft-cap join.
    eps = 1e-4
    y = cp.river_spur_bank_lift(500., np.array([-eps, 0., eps]))
    assert abs((y[2]-2.*y[1]+y[0])/eps) < 1e-5
    run0 = 250.
    cap = cp.river_spur_bank_lift(1e15, run0)
    y = cp.river_spur_bank_lift(.5*cap+np.array([-eps, 0., eps]), run0)
    assert abs((y[2]-2.*y[1]+y[0])/eps) < 1e-5
    print('Bank recovery: bounded, monotone, C1 onsets; ample-room spurs unchanged.')


def upstream_sections():
    ctx = cp.Ctx(2.)
    k = dict(cp.river_courses(ctx, 1193549)[0])['main']
    t = np.linspace(.25, .95, 29)
    tangent = cp._course_tangent(k, t)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    m, q = cp._meander(ctx, k, t, tangent)
    normal = np.cross(tangent, q)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    distance = np.arange(-600., 601., 5.)
    p = q[:, None] + (((m[0]+m[2])[:, None]+distance[None])/cp.R)[:, :, None]*normal[:, None]
    p = p.reshape(-1, 3)
    p /= np.linalg.norm(p, axis=1, keepdims=True)
    after = cp.elevation(ctx, p, extra=True)
    saved = cp.river_spur_bank_lift
    try:
        cp.river_spur_bank_lift = lambda lift, run: lift
        before = cp.elevation(ctx, p, extra=True)
    finally:
        cp.river_spur_bank_lift = saved
    a, b = (v['elev'].reshape(len(t), len(distance)) for v in (after, before))
    centre = len(distance)//2
    inner = np.abs(distance) <= 300.
    rise_a = (a[:, inner]-a[:, centre, None]).max(1)
    rise_b = (b[:, inner]-b[:, centre, None]).max(1)
    assert np.count_nonzero(rise_b > 350.) >= 20, 'The fixture must expose the old prolonged narrow trench.'
    assert np.max(rise_a) < 200., 'Recovered relief still leaves a deep slot beside the small channel.'
    assert np.max(np.abs(np.diff(a[:, inner], axis=1))/5.) < 2., 'Check the composed banks, not only the lift.'
    assert np.all(after['elev'] <= before['elev']+1e-8), 'Recovery cannot fill the existing channel.'
    assert np.array_equal(after['water_coverage'], before['water_coverage']), 'The correction must not resize water.'
    wet = after['water_coverage'] > .999
    assert np.any(wet)
    assert np.allclose(after['water_level'][wet]-after['elev'][wet], after['water_depth'][wet], atol=2e-5)
    length = np.linalg.norm(np.diff(q, axis=0), axis=1).sum()*cp.R
    print(f'{len(t)} sections over {length/1000.:.1f} km: maximum rise within 300 m '
          f'{rise_b.max():.1f} -> {rise_a.max():.1f} m; water footprint unchanged.')


if __name__ == '__main__':
    bank_envelope()
    upstream_sections()
    print('ok')
