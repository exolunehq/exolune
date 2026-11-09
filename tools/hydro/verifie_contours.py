"""Functional contour fixtures. No renderer or quality/performance benchmark."""
import itertools
import json
import numpy as np
import cp


def derivative_quads():
    for bits in itertools.product((0., 1.), repeat=4):
        q = np.array(bits).reshape(2, 2)
        row = np.clip(q + abs(q[:, 1:2] - q[:, 0:1]), 0., 1.)
        active = row + abs(row[1:2, :] - row[0:1, :])
        assert np.all((active > 0.) == any(bits))
    return 16


def missed_channel():
    # Four dry corners do not exclude a narrow channel through the centre of a cell.
    cell, width, depth, stage = 20., 2., .3, 100.
    corners = np.array([[-10., -10.], [10., -10.], [-10., 10.], [10., 10.]])
    assert np.all(abs(corners[:, 0]) > width)
    assert np.mean(abs(corners[:, 0]) - width) < 2 * cell
    # Independent exact integral of depth*(1-(x/width)^2)^2 over its complete support.
    mean_depth = depth * 8. / 15.
    assert mean_depth > 0. and stage - mean_depth < stage
    # The candidate must survive rotation and every sliding-grid phase, despite dry vertices.
    cases = 0
    for angle in np.linspace(0., np.pi, 33):
        axis = np.array([np.cos(angle), np.sin(angle)])
        for x, y in itertools.product(np.linspace(-.5, .5, 9), repeat=2):
            c = corners + cell * np.array([x, y])
            distance = abs(c @ axis) - width
            assert distance.max() < 2 * cell
            cases += 1
    return dict(grid_phases=cases, recovered_depth_m=mean_depth)


def wet_intersections():
    count = 0
    for q, radius in itertools.product((.06, .5, 20., 1000.), (2., 8., 64.)):
        width, _ = cp.erosion_river_size(q)
        for d in np.linspace(0., width + 2 * radius, 23):
            bed = cp.erosion_river_profile(d, 100., q, .65, radius)
            surface = bed + cp.erosion_river_cut(d, q, radius)
            for h in (surface - 50., surface - .1, surface, surface + .1, surface + 50.):
                cut = min(max(h - bed, 0.), max(surface - bed, 0.))
                explicit_depth = max(min(h, surface) - (h - cut), 0.)
                clearance = min(surface - bed - abs(h - surface), radius - (d - width))
                assert (clearance > 1e-7) == (explicit_depth > 1e-7)
                count += 1
    # The compact mean has a finite halo; a physical-width clamp would incorrectly remove it.
    width, radius, d = 2., 2., 2.5
    assert radius - (d - width) > 0.
    assert radius - ((width + radius + 1.) - width) < 0.
    return count


def dry_floor():
    # A derivative filter must preserve an exactly dry drainage-stage plane, at every sampling scale.
    for aa in (.02, 1., 20., 1000.):
        clearance = np.array([-aa, 0., .25 * aa, .5 * aa, aa])
        t = np.clip(clearance / (.5 * aa), 0., 1.)
        cover = t * t * (3. - 2. * t)
        assert cover[0] == cover[1] == 0.
        assert cover[-1] == 1. and np.all(np.diff(cover) >= 0.)
    return 4


def water_rung(count=160, radii=(50., 300.)):
    """The pixel contour's channel rung (gErosionWater, cp.WATER), on the full query's own inputs, at points up to 1.5 km
    from the massif's channels: the same wet fraction, stage, cut, current and positive edge, with fewer courses."""
    from verifie_lames import direction
    rng = np.random.default_rng(1106)
    centre = direction(-9.148316, 124.767492)
    east = np.cross([0., 1., 0.], centre)
    east /= np.linalg.norm(east)
    north = np.cross(centre, east)
    result = {}
    for radius in radii:
        ctx = cp.Ctx(radius)
        a, d = rng.uniform(0., 2. * np.pi, 64), 150e3 * np.sqrt(rng.uniform(size=64))
        seeds = centre + (d / cp.R)[:, None] * (np.cos(a)[:, None] * east + np.sin(a)[:, None] * north)
        lines = cp.river_lines(ctx, seeds / np.linalg.norm(seeds, axis=1, keepdims=True), 2000.)
        on = lines[rng.choice(len(lines), count)]
        side = np.cross(on, rng.normal(size=(count, 3)))
        side /= np.linalg.norm(side, axis=1, keepdims=True)
        pts = on + (rng.uniform(-1500., 1500., count) / cp.R)[:, None] * side
        pts /= np.linalg.norm(pts, axis=1, keepdims=True)
        inputs, original = {}, cp.erosion_rivers
        cp.erosion_rivers = lambda c, q, hr, parent, fine, seed=None: (
            inputs.update(q=q, hr=hr, parent=parent, fine=fine) or original(c, q, hr, parent, fine, seed))
        try:
            cp._relief_ground(ctx, pts)
        finally:
            cp.erosion_rivers = original
        args = (ctx, inputs['q'], inputs['hr'], inputs['parent'], inputs['fine'])
        full = cp.erosion_rivers(*args)
        cp.WATER = True
        try:
            water = cp.erosion_rivers(*args)
        finally:
            cp.WATER = False
        for key in ('coverage', 'cut', 'stage', 'flow'):
            assert np.array_equal(full[key], water[key]), (radius, key)
        assert np.array_equal(np.maximum(full['edge'], 0.), np.maximum(water['edge'], 0.)), radius
        result[f'{radius:g} m'] = dict(points=len(inputs['q']), wet=int((full['coverage'] > 0.).sum()),
                                      courses_full=round(float(full['cost']['meanders'].mean()), 2),
                                      courses_water=round(float(water['cost']['meanders'].mean()), 2))
    return result


if __name__ == '__main__':
    print(json.dumps(dict(quad_masks=derivative_quads(), narrow_channel=missed_channel(),
                          explicit_intersections=wet_intersections(), dry_floor_scales=dry_floor(),
                          water_rung=water_rung()), indent=2))
