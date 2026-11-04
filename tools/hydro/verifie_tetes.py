"""Dry head growth and real-terrain continuity at several scales. No benchmark."""
from pathlib import Path
import re

import numpy as np

import cp
from verifie_lames import direction
from verifie_raccords import section


def growth():
    source = (Path(cp._REPO)/'MyPlanetEngine/PlanetSettings.hlsli').read_text()
    values = re.search(r'RIVER_Q\s*=\s*float3\(([^)]+)\)', source).group(1)
    assert tuple(float(x) for x in values.split(',')) == cp.RIVER_Q, 'CPU/GPU onset settings differ.'
    q = np.geomspace(1., 100000., 8193)
    share = cp._course_share(np.log2(q))
    assert np.all(np.isfinite(share)) and np.all((share >= 0.) & (share <= 1.))
    assert np.all(np.diff(share) >= -1e-12)
    assert np.all(share[q <= cp.RIVER_Q[0]] == 0.)
    assert np.all(share[q >= cp.RIVER_Q[1]] == 1.), 'Mature corridors must retain their whole profile.'
    assert cp._course_share(np.log2(150.)) < .16
    assert cp._course_share(np.log2(200.)) <= .50, 'New dry tributaries must not acquire full-size valleys.'
    for threshold in cp.RIVER_Q[:2]:
        eps = .001
        s = cp._course_share(np.log2(threshold + np.array([-eps, 0., eps])))
        assert np.max(np.abs(np.diff(s)))/eps < 1e-6, 'An onset must not introduce a slope step.'
    print('Onset: CPU/GPU thresholds agree; bounded monotone growth, smooth ends, mature valleys unchanged.')


def dry_sections():
    # Real upstream course in the reported massif, rather than a fabricated high-discharge dry extension.
    k = cp._node_courses(1197637)['main']
    spans, depths = [], []
    for t in (.45, .6, .75, .95):
        x, wet, out = section(k, t, span=6000., step=2., height=float(cp._bez(k['stage'], t))+2000.)
        assert not np.any(wet) and np.all(out['coverage'] == 0.), 'A dry head cannot create liquid water.'
        cut = out['carve']
        active = cut > 1.
        spans.append(float(np.ptp(x[active])) if np.any(active) else 0.)
        depths.append(float(cut.max()))
    assert np.all(np.diff(spans) > 0.) and np.all(np.diff(depths) > 0.), (spans, depths)
    assert spans[0] < .3*spans[-1] and depths[0] < .2*depths[-1], 'Width and depth must taper together.'
    print(f'Real dry head: section widths {spans} m; depths {np.round(depths, 1).tolist()} m; no water.')


def extension():
    # Compare against the former onset on identical cached drainage and physical terrain.
    p = cp.window(direction(-6.05, 125.95), 100000., 80)
    saved_q, saved_share = cp.RIVER_Q, cp._course_share
    for radius in (40., 500., 2000.):
        after = cp._relief_ground(cp.Ctx(radius), p)
        try:
            cp.RIVER_Q = (200., *saved_q[1:])
            cp._course_share = lambda lq: cp._smooth(np.log2(200.), np.log2(300.), lq)
            before = cp._relief_ground(cp.Ctx(radius), p)
        finally:
            cp.RIVER_Q, cp._course_share = saved_q, saved_share
        old, new = before['rivers'], after['rivers']
        extended = (old['carve'] < 1.) & (new['carve'] > 10.)
        assert np.count_nonzero(extended) >= 5, (radius, np.count_nonzero(extended))
        assert np.all(new['coverage'][extended] == 0.), 'An extended point remains dry at every bandwidth.'
        assert np.all(after['elev'] <= before['_wave'][1]+1e-6), 'A dry extension cannot raise mountains.'
        print(f'Reported head, {radius:g} m footprint: {extended.sum()} extended dry samples, without a camera-dependent shape.')


def dry_joins():
    words, n = cp.erosion_map()
    data = cp._flow_words[cp.PLANET_SEED][:, 0]
    q = np.exp2((data & 255)/8.-8.)
    eligible = np.flatnonzero((q > 100.) & (q < 200.) &
                             ((words[:, 1] & (cp._SEA | cp._LAKE)) == 0) &
                             ((words[:, 1] & cp._HAS_RECEIVER) != 0) & ((data & (1 << 16)) == 0))
    nodes = eligible[np.linspace(0, len(eligible)-1, 12).astype(int)]
    worst = 0.
    for node in nodes:
        k = cp._node_courses(int(node))['main']
        at = k['xyz'][2]/np.linalg.norm(k['xyz'][2])
        east, north = cp.tangent_basis(at[None])
        changes = []
        for step in (2., .5):
            x = np.arange(-16., 16.+step/2., step)
            p = at+(x/cp.R)[:, None]*(east+.4*north)
            p /= np.linalg.norm(p, axis=1, keepdims=True)
            g = cp._relief_ground(cp.Ctx(2.), p)
            assert np.all(np.isfinite(g['elev']))
            changes.append(float(np.max(np.abs(np.diff(g['rivers']['carve'])))))
        if changes[0] > .01:
            ratio = changes[1]/changes[0]
            worst = max(worst, ratio)
            assert ratio < .6, (node, changes)
    print(f'Twelve dry joins distributed across the planet: maximum refinement ratio {worst:.3f}; no fixed jump.')


def pruning():
    words, n = cp.erosion_map()
    raw = (words[:, 1] >> 16) & 255
    flow = cp._flow_words[cp.PLANET_SEED][:, 0]
    has = (words[:, 1] & cp._HAS_RECEIVER) != 0
    c = np.flatnonzero(has)
    r = cp._eneighbour(c, (words[c, 1] & 7).astype(np.int64), n)
    # Independent proof of the early bound for every cached link, including stopped and rerouted inflows.
    assert np.all(raw[c] <= raw[r]), 'Raw receiver flow must bound every inflow.'
    assert np.all((flow & 255) <= raw+1) and np.all((flow >> 8 & 255) <= raw+1)
    print(f'Inactive-course bound: raw accumulation and surviving-flow upper bounds hold on {len(c)} links.')
    # The tightened spatial bound must only remove work; compare it with the former larger bound on composed terrain.
    def former(k):
        lq = max(k['lq'].max(), k['part_lq'].max() if k.get('split', False) else -1e9)
        trace = k.get('trace_lq', k['lq'])
        bend = max(cp._meander_bounds(cp._finest(trace.max()), 1.)[0],
                   cp._meander_bounds(cp._finest(min(trace[0], trace[2])), 1.)[0])
        nominal = float(cp.erosion_river_size(2.**lq)[0])
        w = (1.+cp.RIVER_WIDTH_NOISE[1])*nominal+k['flare'][0]+cp.RIVER_BANK_EDGE[0]
        w += max(min(cp.RIVER_MOUTH[0]*nominal, cp.RIVER_MOUTH[2]) if k.get('mouth', False) else 0.,
                 cp._smooth(0., 1., k['fan'].max())*cp.RIVER_DELTA[3])
        floor = min(float(cp._valley_floor(2.**lq, k['floor'].max()))*2.**cp.RIVER_VALLEY_NOISE[1], cp.RIVER_FLOOR[2])
        outer = min(floor+2.*np.sqrt(2.)*w+max(k['wall'].max()*2.**cp.RIVER_VALLEY_NOISE[2], 1.), cp.RIVER_REACH)
        return max(outer, 2.*w+bend)+bend+cp.RIVER_OFFSET_MAX
    saved = cp._course_reach
    for centre in ((-6.05, 125.95), (-26.2884, -36.5200), (-6.7166, 122.4399)):
        p = cp.window(direction(*centre), 60000., 28)
        after = cp._relief_ground(cp.Ctx(100.), p)
        try:
            cp._course_reach = former
            before = cp._relief_ground(cp.Ctx(100.), p)
        finally:
            cp._course_reach = saved
        for key in ('carve', 'fill', 'coverage', 'bed', 'stage'):
            assert np.array_equal(after['rivers'][key], before['rivers'][key]), (centre, key)
    print('Tighter spatial bound: identical terrain and water fields across three massifs.')


if __name__ == '__main__':
    growth()
    dry_sections()
    extension()
    dry_joins()
    pruning()
    print('ok')
