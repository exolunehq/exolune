"""Composed confluence/fan sections and bank bandwidth regressions; no benchmark."""
import numpy as np

import cp


def fixture_courses(node):
    """Isolate section morphology from the separately tested first-water routing."""
    words, _ = cp.erosion_map()
    seed = cp.PLANET_SEED
    flow, stops = cp._flow_words[seed], cp._contacts[seed]
    code = words[:, 1]>>16&255
    try:
        cp._flow_words[seed] = np.stack((code | code<<8, np.zeros(len(words), np.uint32)), 1)
        cp._contacts[seed] = np.broadcast_to(np.ones(4), (len(words), 4))
        return cp.river_courses(cp.Ctx(2.), node)
    finally:
        cp._flow_words[seed], cp._contacts[seed] = flow, stops


def section(k, t, span=3000., step=2., height=100., lake=0.):
    ctx = cp.Ctx(2.)
    T = cp._course_tangent(k, np.array([t]))
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    m, p = cp._meander(ctx, k, np.array([t]), T)
    if k['taper']:
        m *= 1.-cp._smooth(.6, 1., t)
    N = np.cross(T, p)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    x = np.arange(-span, span+step, step)
    P = p+((m[0, 0]+m[2, 0]+x)/cp.R)[:, None]*N
    P /= np.linalg.norm(P, axis=1, keepdims=True)
    n = len(P)
    out = dict(fill=np.zeros(n), carve=np.zeros(n), bed=np.full(n, 1e9), stage=np.zeros(n),
               cut=np.zeros(n), weight=np.zeros(n), edge=np.full(n, -1e9), distance=np.full(n, 1e9),
               flow=np.zeros((n, 3)), coverage=np.zeros(n), bank=np.zeros(n), lake_level=np.full(n, lake))
    cost = {key: np.zeros(n) for key in ('corridors','meanders','octaves')}
    # The full corridor, its physical banks and channel cuts on a level support.
    h = np.full(n, height)
    cp._corridor(ctx, k, P, h, h, np.zeros(n), 2., cp._smooth(0., 50., h-lake), out, np.arange(n), cost)
    wet = out['coverage'] > .99
    assert np.all(np.isfinite(out['bed']))
    assert np.all((out['coverage'] >= 0.) & (out['coverage'] <= 1.))
    return x, wet, out


def openings():
    # Test the composed physical wet section, not a mandatory width gain: equal-sized arrivals must not make a bulb.
    k = dict(fixture_courses(1197130)[0])[1]
    saved = cp.RIVER_WIDTH_NOISE, cp.RIVER_BANK_EDGE
    width = float(cp.erosion_river_size(2000.)[0])
    end = k['xyz'][2]/np.linalg.norm(k['xyz'][2])
    t1, t2 = (v[0] for v in cp.tangent_basis(end[None]))
    count = 0
    try:
        cp.RIVER_WIDTH_NOISE, cp.RIVER_BANK_EDGE = (saved[0][0], 0.), (0., 0.)
        for angle in (12., 35., 55., 85.):
            tangent = np.cos(np.radians(angle))*t1+np.sin(np.radians(angle))*t2
            xyz = np.stack([end-15000.*tangent/cp.R, end-7500.*tangent/cp.R, end])
            plain = dict(k, xyz=xyz, lq=np.full(3, np.log2(2000.)), sinuous=np.zeros(3),
                         stage=np.full(3, 20.), flare=np.zeros(3), mouth=False, fan=np.zeros(3))
            for ratio in (.5, 1., 2., 5.):
                target = ratio*width
                for side in (-1., -.25, 0., .25, 1.):
                    course = dict(plain, flare=np.array([target, target, side]))
                    for t in (.1, .98, 1.):
                        x, wet, out = section(course, t, span=max(width, target)+20., step=.5)
                        banks = np.array([x[wet].min()-2., x[wet].max()+2.])
                        # All bank extents, including the shifted endpoint cap, fit the wider receiving/own section.
                        assert np.max(np.abs(banks)) <= max(width, target)+1., (angle, ratio, side, t, banks)
                        assert wet[np.argmin(np.abs(x))], 'The immutable drainage spine must remain inside water.'
                        if t == .1 or ratio == 1. or (side == 0. and ratio > 1.):
                            assert np.max(np.abs(banks-np.array([-width, width]))) < 1., banks
                        elif ratio > 1.:
                            upstream = 0 if side > 0. else 1
                            assert abs(abs(banks[upstream])-width) < 1., 'Opening must preserve the upstream land tongue.'
                            assert abs(banks[1-upstream]) > width+1., 'Only the downstream-facing bank should open.'
                        elif t == 1.:
                            assert np.max(np.abs(banks-np.array([-target, target]))) < 1., banks
                        stage = out['stage']/np.maximum(out['weight'], 1e-9)
                        assert np.all(out['bed'][wet] < stage[wet]), 'The shifted wet support must excavate the same bed.'
                        count += 1
        # Even a very short connector must meet the unchanged upstream cross-section at its first point.
        short_xyz = np.stack([end-500.*t1/cp.R, end-250.*t1/cp.R, end])
        short = dict(plain, xyz=short_xyz, flare=np.array([5.*width, 5.*width, 1.]))
        _, before, a = section(dict(short, flare=np.zeros(3)), 0., span=6.*width)
        _, after, b = section(short, 0., span=6.*width)
        assert np.array_equal(before, after)
        assert np.allclose(a['bed'], b['bed'], rtol=0., atol=1e-9), 'A short opening cannot jump at the upstream join.'
    finally:
        cp.RIVER_WIDTH_NOISE, cp.RIVER_BANK_EDGE = saved
    print(f'Confluences: {count} physical sections, both banks, four angles and width ratios; no equal-width bulb, upstream tongue and short-course join retained.')


def bank_orientation():
    words, _ = cp.erosion_map()
    bits = words[:, 1]
    code = cp._flow_words[cp.PLANET_SEED][:, 0] & 255
    counts = np.array([i.bit_count() for i in range(256)])
    nodes = np.flatnonzero((counts[bits>>4&255] >= 2) & (code >= 135) & ((bits & (cp._SEA | cp._LAKE)) == 0))
    tested = parallel = corrected = 0
    for node in np.random.default_rng(4871).permutation(nodes)[:512]:
        courses, v = cp.river_courses(cp.Ctx(2.), int(node))
        for kind, k in courses:
            if isinstance(kind, str) or k['flare'][0] == 0.:
                continue
            t = np.array([k['junction']])
            tangent = cp._course_tangent(v['main'], t)
            tangent /= np.linalg.norm(tangent, axis=1)[:, None]
            m, q = cp._meander(cp.Ctx(2.), v['main'], t, tangent)
            up = q[0]
            along = tangent[0] - np.dot(tangent[0], up)*up
            along /= np.linalg.norm(along)
            flow = along+np.clip(m[1, 0]+m[3, 0], -1., 1.)*np.cross(along, up)
            arrival = k['xyz'][2]-k['xyz'][1]
            arrival /= np.linalg.norm(arrival)
            normal = np.cross(arrival, up)
            turn = np.dot(flow, normal)/np.linalg.norm(flow)
            assert k['flare'][2]*turn >= 0., 'The opening must face actual downstream flow, including its meanders.'
            assert abs(k['flare'][2]) <= 1.
            if abs(turn) < np.sin(np.radians(cp.RIVER_JUNCTION[0])):
                assert abs(k['flare'][2]) < 1., 'Nearly parallel courses cannot switch between two full bank openings.'
                parallel += 1
            corrected += np.dot(along, normal)*turn < 0.
            tested += 1
    assert tested > 100
    print(f'Local flow orientation: {tested} planetary connectors; {parallel} near-parallel openings fade, {corrected} sides differ from the coarse heading.')


def fans():
    k = dict(fixture_courses(1205821)[0])['outlet']
    plain = dict(k, fan=np.zeros(3))
    spans = []
    for course in (plain, k):
        x, wet, out = section(course, .9)
        spans.append(float(x[wet].max()-x[wet].min()))
    runs = np.count_nonzero(wet & ~np.r_[False, wet[:-1]])
    assert runs == 3, runs
    assert spans[1] > 4.*spans[0], spans
    near_x, near_wet, _ = section(k, .1)
    near_span = float(near_x[near_wet].max()-near_x[near_wet].min())
    assert spans[1] > 1.6*near_span, 'The terminal channels must continue diverging, not become parallel canals.'
    # Each distributary must still excavate below its common surface, with dry intervening ground.
    stage = out['stage']/np.maximum(out['weight'], 1e-9)
    assert np.all(out['bed'][wet] < stage[wet])
    assert np.any((out['bed'] > 0.) & ~wet & (np.abs(x) < .4*spans[1]))
    mountain = dict(fixture_courses(1205818)[0])['main']
    assert np.all(mountain['fan'] == 0.), 'A steep coastal massif must not acquire a broad depositional fan.'
    print(f'Low-coast fan: three separated wet channels, aperture {spans[0]:.0f} -> {spans[1]:.0f} m; mountain outlet excluded.')


def bank_bandwidth():
    from verifie_lames import direction
    p = cp.window(direction(-6.2504, 125.3465), 1000., 40)
    close = cp._bank_factor(cp.Ctx(2.), p)
    coarse = cp._bank_factor(cp.Ctx(200.), p)
    assert np.all((close >= 1.-cp.RIVER_BANK_DETAIL[1]) & (close <= 1.+cp.RIVER_BANK_DETAIL[1]))
    assert np.std(close) > .04
    assert np.all(coarse == 1.), 'Unresolved bank octaves must tend to their mean, without changing bank height.'
    print(f'World-fixed bank relief: resolved variation {np.std(close):.3f}, unresolved mean exactly 1.')


def junction_current():
    ctx = cp.Ctx(2.)
    k = dict(cp.river_courses(ctx, 1197130)[0])[1]
    centre = k['xyz'][2]/np.linalg.norm(k['xyz'][2])
    t1, t2 = cp.tangent_basis(centre[None])
    changes = []
    for spacing in (.25, .0625):
        x = np.arange(-200., 200.+spacing/2., spacing)
        P = centre+x[:, None]/cp.R*(t1+.4*t2)
        P /= np.linalg.norm(P, axis=1, keepdims=True)
        d = cp.elevation(ctx, P, extra=True)
        speed = np.linalg.norm(d['flow'], axis=1)
        assert np.all(speed <= 4.+1e-8)
        wet = d['water_coverage'] > .99
        interior = wet[:-1] & wet[1:]
        changes.append(np.linalg.norm(np.diff(d['flow'], axis=0), axis=1)[interior].max())
    assert changes[1] < .35*changes[0]+1e-6, changes
    print(f'Confluence current: a four-times finer step reduces the largest wet velocity change by {changes[1]/changes[0]:.3f}; speed bounded at 4 m/s.')


def mouths():
    # The same physical inlet, with its shore above the receiving lake or sea. No shoreline is allowed to
    # close across the channel, and drowned support cannot be raised into a pair of artificial levees.
    k = dict(dict(fixture_courses(1205821)[0])['outlet'], fan=np.zeros(3))
    spans = []
    for level in (0., 100.):
        course = dict(k, stage=np.full(3, level))
        widths = []
        for ground in (level+200., level+1., level-5.):
            x, wet, out = section(course, .3, height=ground, lake=level)
            widths.append(float(x[wet].max()-x[wet].min()))
            if ground < level:
                assert np.all(out['fill'] == 0.), 'Drowned river banks must never rebuild a dike across receiving water.'
        assert widths[1] > 2.*widths[0], widths
        spans.append(widths)
    assert spans[0] == spans[1], 'A marine inlet and an elevated lake inlet use the same mouth geometry.'
    print(f'Receiving water: inlet opens {spans[0][0]:.0f} -> {spans[0][1]:.0f} m; drowned fill is zero at sea and lake level.')


def head_tips():
    _, v = fixture_courses(1197130)
    k = cp._head_course(v)
    widths, cuts = [], []
    for t in (.05, .2, .5, .95):
        height = float(cp._bez(k['stage'], np.array([t]))[0])+500.
        x, _, out = section(k, t, span=12000., step=4., height=height)
        cut = out['carve'].max()
        active = out['carve'] > max(.1*cut, .01)
        widths.append(float(np.ptp(x[active])))
        cuts.append(float(cut))
        assert not np.any(out['coverage']), 'The head continuation is a dry valley, not a new water channel.'
    assert np.all(np.diff(widths) > 0.), widths
    assert cuts[0] < .03*cuts[-1] and cuts[1] < .2*cuts[-1], cuts
    assert widths[0] < .15*widths[-1], widths
    print(f'Dry head: width {widths[0]:.0f} -> {widths[-1]:.0f} m and incision {cuts[0]:.1f} -> {cuts[-1]:.1f} m towards the trunk.')


def shore_microgeometry():
    k = dict(fixture_courses(1197130)[0])['main']
    offsets = []
    saved = cp.RIVER_BANK_EDGE
    try:
        for t in np.linspace(.2, .8, 13):
            edges = []
            for setting in ((0., 0.), saved):
                cp.RIVER_BANK_EDGE = setting
                x, wet, _ = section(k, t, span=500., step=.25)
                edges.append(np.array([x[wet].min(), x[wet].max()]))
            offsets.append(edges[1]-edges[0])
    finally:
        cp.RIVER_BANK_EDGE = saved
    offsets = np.array(offsets)
    assert np.max(np.abs(offsets)) <= saved[0]+.5, offsets
    assert np.ptp(offsets) > 1., 'Fine bank octaves must move the physical wet boundary.'
    assert np.max(np.abs(offsets.sum(1))) > 1., 'Opposing banks must not repeat a mirrored width sequence.'
    print(f'Fine shore geometry: independent bank offsets up to {np.max(np.abs(offsets)):.2f} m, inside the {saved[0]:.0f} m bound.')


if __name__ == '__main__':
    openings()
    bank_orientation()
    fans()
    bank_bandwidth()
    junction_current()
    mouths()
    head_tips()
    shore_microgeometry()
    print('ok')
