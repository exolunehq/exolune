"""Correctness of terrain-residual preservation and physical river widths; no benchmark.

Run after the Release build: python tools/hydro/verifie_morphologie.py
The full joined terrain/water regression remains in verifie_couloirs.py.
"""
import numpy as np

import cp
from verifie_lames import direction


def spurs():
    rng = np.random.default_rng(110303)
    ground = rng.uniform(-100., 8000., 4096)
    parent = ground + rng.uniform(-2500., 2500., len(ground))
    fine = rng.uniform(-40., 40., len(ground))
    bank = ground + rng.uniform(-5000., 100., len(ground))
    profile, keep = rng.random((2, len(ground)))
    lift = cp.river_spur_lift(ground, parent, fine, bank, keep)
    before = bank + (ground-bank)*profile
    after = before + (1.-profile)*lift
    assert np.all(lift >= 0.)
    assert np.all(after >= before-1e-10), 'Retaining a spur must not deepen a trench.'
    assert np.all(after <= np.maximum(ground, before)+1e-10), 'A spur cannot raise the original terrain.'
    assert np.all(lift[ground <= parent+fine] == 0.), 'Negative residuals cannot dig a second valley.'
    assert np.all(cp.river_spur_lift(ground, parent, fine, bank, 0.) == 0.), 'The channel must stay unobstructed.'
    # Bank and residual onsets are physical boundaries. Check their slopes from both sides independently.
    for offset in (0., cp.RIVER_SPURS[1]):
        eps = .0001
        x = offset + np.array([-eps, 0., eps])
        y = cp.river_spur_lift(3000.+x, 3000., 0., 1000., 1.)
        assert abs((y[2]-y[1])-(y[1]-y[0]))/eps < 1e-4
    eps = .0001
    x = np.array([-eps, 0., eps])
    y = cp.river_spur_lift(1000.+x, 0., 0., 1000., 1.)
    assert abs((y[2]-y[1])-(y[1]-y[0]))/eps < 1e-4, 'Bank onset must not introduce a slope step.'
    print('4096 terrain compositions: no new excavation, no raised mountain, clear wet bank; onset slopes continuous.')


def widths():
    p = cp.window(direction(-7.173005, 125.036219), 60000., 48)
    a = cp._width_factor(cp.Ctx(.25), p, cp._course_noise(cp.Ctx(.25), p, cp.RIVER_VALLEY_NOISE[0], 17))
    b = cp._width_factor(cp.Ctx(2.), p, cp._course_noise(cp.Ctx(2.), p, cp.RIVER_VALLEY_NOISE[0], 17))
    assert np.array_equal(a, b), 'Resolved physical widths cannot change with the mesh.'
    amplitude = cp.RIVER_WIDTH_NOISE[1]
    assert np.all((a >= 1.-amplitude) & (a <= 1.+amplitude)), 'The culling bound must enclose every width.'
    far = cp._width_factor(cp.Ctx(100000.), p, cp._course_noise(cp.Ctx(100000.), p, cp.RIVER_VALLEY_NOISE[0], 17))
    assert np.array_equal(far, np.ones(len(p))), 'Unresolved centred width octaves must return the nominal width.'
    assert np.ptp(a) > .4, 'The course must retain spatial width variation at a fixed discharge.'
    print('Physical width: bounded, spatially varying, identical at resolved scales, nominal when fully filtered.')


def confinement():
    rng = np.random.default_rng(110304)
    ground = rng.uniform(-100., 8000., 4096)
    parent = ground + rng.uniform(-3000., 3000., len(ground))
    bank = ground + rng.uniform(-6000., 100., len(ground))
    factor = cp.river_confinement(ground, parent, 0., bank)
    assert np.all((factor >= cp.RIVER_CONFINEMENT[0]) & (factor <= 1.))
    assert np.all(factor[ground <= parent] == 1.)
    width = rng.uniform(20., 400., len(ground))
    offset = rng.uniform(-2000., 2000., len(ground))
    valley_slope, channel_slope = rng.uniform(-1., 1., (2, len(ground)))
    metric = 1./np.sqrt(1.+valley_slope**2)
    belt = np.abs(offset)*metric + 2.*width*np.maximum(1., np.sqrt(1.+channel_slope**2)*metric)
    base_floor = rng.uniform(100., 4000., len(ground))
    floor = np.maximum(belt, base_floor)
    wall = rng.uniform(300., 6000., len(ground))
    distance = rng.uniform(0., cp.RIVER_REACH, len(ground))
    lq = rng.uniform(np.log2(450.), 16., len(ground))
    outer = np.minimum(floor+wall, cp.RIVER_REACH)
    original = cp._wall_profile((distance-floor)/(outer-floor), lq)
    narrowed = np.maximum(belt, base_floor*factor)
    outer_narrowed = np.minimum(narrowed+wall*factor, cp.RIVER_REACH)
    profile = cp._wall_profile((distance-narrowed)/(outer_narrowed-narrowed), lq)
    # Independent points on the displaced channel's outer bank, then measured in the valley's own metric.
    angle = rng.uniform(-np.pi, np.pi, len(ground))
    along = 2.*width*np.cos(angle)
    across = offset + 2.*width*np.sin(angle)*np.sqrt(1.+channel_slope**2)
    bank_distance = np.hypot(along, across*metric)
    assert np.all(narrowed >= bank_distance), 'Confinement must contain the displaced wet banks, not only the axis.'
    assert np.all(outer_narrowed <= outer), 'Terrain confinement must stay inside the original search bound.'
    assert np.all(profile >= original-1e-12), 'Contracting a valley cannot create deeper dry incision.'
    print('4096 confined profiles: bounded reach, no deeper incision, actual displaced banks inside the floor.')


def reach():
    # The fixed 4x4 node search must contain the widest channel plus all meander offsets, including at cube corners.
    # Bound the full discharge range of the current planet, not only the displayed valley's courses.
    words, size = cp.erosion_map()
    max_lq = float(((words[:, 1] >> 16) & 255).max())/8.-8.
    lq = np.linspace(np.log2(cp.RIVER_Q[0]), max_lq, 2048)
    finest = cp._finest(lq)
    fine, _ = cp._meander_bounds(finest, 1.)
    max_fine = float(np.max(fine))
    nominal = float(cp.erosion_river_size(2.**max_lq)[0])
    # Matching a receiving width adds no envelope beyond the wider channel, including its one-sided shift.
    assert 0. <= cp.RIVER_CONFLUENCE[0] <= .5, 'The shifted endpoint must fit the receiving half-width.'
    width = (1.+cp.RIVER_WIDTH_NOISE[1])*nominal + cp.RIVER_BANK_EDGE[0]
    width += max(min(cp.RIVER_MOUTH[0]*nominal, cp.RIVER_MOUTH[2]), cp.RIVER_DELTA[3])
    assert max(cp.RIVER_FLOOR[2], 2.*np.sqrt(2.)*width) < cp.RIVER_REACH, 'The displaced bank needs room inside the corridor.'
    bound = max(cp.RIVER_REACH, 2.*width+max_fine)+max_fine+cp.RIVER_OFFSET_MAX
    available = 1.2*(2.*cp.R/size)*np.sqrt(2.)/3.
    assert bound < available, (bound, available, 'Meanders escape the fixed node search.')
    _, valley = cp._meander_octave(2.*cp.RIVER_CHANNEL_WAVE, finest, 1.)
    assert np.all(valley == 1.), 'Large bends belong to the bounded valley offset.'
    print(f'Current planet: corridor reach bound {bound:.1f} m stays inside the {available:.1f} m node-search contract.')


if __name__ == '__main__':
    spurs()
    widths()
    confinement()
    reach()
    print('ok')
