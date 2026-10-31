"""Requested valley-floor checks against the pre-Part-D cp.py snapshot; no engine or rendering.

The 4 km flood uses eight neighbours and open boundaries, at fixed 25 m sample spacing.
Both versions read the same current seed-0 engine caches. Run from the worktree root.
"""
import argparse
import heapq

import numpy as np
import cp
from verifie_pentes_ravines import load_before, cliffs


def flood(z):
    """Lowest escape level to the square's boundary (D8 minimax paths)."""
    n = z.shape[0]
    seen = np.zeros_like(z, dtype=bool)
    filled = z.copy()
    heap = []
    for j in range(n):
        for i in range(n):
            if i in (0, n-1) or j in (0, n-1):
                seen[j, i] = True
                heapq.heappush(heap, (z[j, i], j, i))
    while heap:
        level, j, i = heapq.heappop(heap)
        for dj, di in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            y, x = j+dj, i+di
            if 0 <= x < n and 0 <= y < n and not seen[y, x]:
                seen[y, x] = True
                filled[y, x] = max(level, z[y, x])
                heapq.heappush(heap, (filled[y, x], y, x))
    return filled


def sample(model, points, cell):
    state = {}
    original = model.erosion_carve
    def capture(h, coarse, v, k):
        state.update(h=h, coarse=coarse, **v)
        result = original(h, coarse, v, k)
        e = np.maximum(k-abs(coarse-v['surface']), 0.0)/k
        state['cut'] = np.maximum(np.minimum(coarse,v['surface'])-.25*k*e*e, np.minimum(coarse,v['level']))
        return result
    model.erosion_carve = capture
    try:
        z = model.elevation(model.Ctx(cell), points)
    finally:
        model.erosion_carve = original
    return z, state


def analytic(old):
    # At a carved thalweg, either sign of detail goes to the water level. A level-0 lake keeps its own level.
    coarse = np.full(101, 2000.)
    detail = np.linspace(-100.,100.,101)
    for level in (1500.,1700.):
        for floor_share in (0.,.5,1.):
            v = dict(surface=np.full(101,level-200.), level=np.full(101,level), floor=np.full(101,floor_share))
            actual = cp.erosion_carve(coarse+detail, coarse, v,60.)
            assert np.max(abs(actual-level)) < 1e-10
            v['surface'][:] = 3000.
            assert np.array_equal(cp.erosion_carve(coarse+detail,coarse,v,60.), old.erosion_carve(coarse+detail,coarse,v,60.))
    print('analytic: either sign removed on the carved thalweg; lake level retained; no carve unchanged', flush=True)


def floors(old):
    for index,(lat,lon) in enumerate(((-25.566,-26.916),(-25.486,-27.075))):
        base = cliffs.direction(lat,lon)[0]
        center = base.copy()
        if index == 0:
            north = np.array([0.,1.,0.])-base*base[1]
            north /= np.linalg.norm(north)
            east = np.cross(base,north)
            delta = 2325.*north+1475.*east
            center = cp.move(base[None,:],delta[None,:]/np.linalg.norm(delta),[np.linalg.norm(delta)])[0]
            assert np.arcsin(center[1]) > np.radians(lat)
            assert np.arctan2(center[2],center[0]) > np.radians(lon)
        print(f'4km center: {np.degrees(np.arcsin(center[1])):.9f}, '
              f'{np.degrees(np.arctan2(center[2],center[0])):.9f}',flush=True)
        # window() gives cell centres: endpoints are exactly 4 km apart, 25 m apart.
        points = cp.window(center,4025.,161)
        results = [sample(m,points,5.) for m in (old,cp)]
        depths = []
        for label,(z,v) in zip(('before','after'),results):
            filled = flood(z.reshape(161,161)).ravel()
            depth = filled-z
            depths.append(depth)
            middle = len(z)//2
            print(f'  square center {label}: closed depth {depth[middle]:.9f} m; '
                  f'ground {z[middle]:.9f} m; water {v["level"][middle]:.9f} m',flush=True)
            water = (v['coarse']-v['cut']>60.) & (abs(v['cut']-v['level'])<1e-8)
            axis = water & (v['floor']>1.-1e-8)
            residual = (z-v['level'])[axis]
            plateau = (z-v['level'])[water]
            print(f'{lat},{lon} 4km {label}: closed max {depth.max():.6f} m; area(depth>1m) {np.mean(depth>1)*16:.6f} km2; '
                  f'thalweg n={axis.sum()}, h-level [{residual.min() if len(residual) else np.nan:.9f}, '
                  f'{residual.max() if len(residual) else np.nan:.9f}] m',flush=True)
            print(f'  whole water-clamped floor n={water.sum()}, h-level '
                  f'[{plateau.min():.9f}, {plateau.max():.9f}] m; closed max on this floor {depth[water].max():.6f} m',flush=True)
            # Trace each cross-section's deepest coarse profile, independently of the fine height being tested.
            cross = np.where(water,v['surface']-v['level'],np.inf).reshape(161,161)
            rows = np.flatnonzero(np.isfinite(cross).any(axis=1))
            ids = rows*161+np.argmin(cross[rows],axis=1)
            profile = z[ids]-v['level'][ids]
            print(f'  thalweg cross-section trace n={len(ids)}, h-level '
                  f'[{profile.min():.9f}, {profile.max():.9f}] m',flush=True)
            np.savetxt(f'x64/Release/thalweg-{index}-{label}.csv',
                       np.column_stack((rows,ids%161,z[ids],v['level'][ids],profile)),delimiter=',',
                       header='row,column,ground_m,water_level_m,ground_minus_water_m',comments='')
            if label == 'after':
                assert abs(plateau).max() < 1e-8, 'the carved water-clamped floor retains fine detail'
                coarse_depth = flood(v['cut'].reshape(161,161)).ravel()-v['cut']
                print(f'  coarse carve alone: closed max {coarse_depth.max():.6f} m; '
                      f'on the water-clamped floor {coarse_depth[water].max():.6f} m',flush=True)
            np.savez(f'x64/Release/fonds-{index}-{label}.npz',points=points,height=z,filled=filled,**v)
        low = np.argmax(depths[0])
        print(f'  deepest before point: depth {depths[0][low]:.6f} -> {depths[1][low]:.6f} m; '
              f'ground {results[0][0][low]:.6f} -> {results[1][0][low]:.6f} m; level {results[1][1]["level"][low]:.6f} m',flush=True)
        # The 10 km comparison stays centred on each reported oval, at fixed 100 m sample spacing.
        points = cp.window(base,10100.,101)
        for label,model in (('before',old),('after',cp)):
            z,v = sample(model,points,5.)
            below = z<v['level']-5.
            print(f'  10km {label}: below water by >5m {100*np.mean(below):.6f}%; '
                  f'floor-supported {100*np.mean(below & (v["floor"]>0)):.6f}%; max deficit {np.max(v["level"]-z):.6f} m',flush=True)
        # Isolate the floor rule from the simultaneous rock-bound change.
        rock = cp.EROSION_GULLY_ROCK
        cp.EROSION_GULLY_ROCK = cp.EROSION_GULLY_CRITICAL
        try:
            baseline,state = sample(old,points,5.)
            changed,_ = sample(cp,points,5.)
            untouched = state['cut']==state['coarse']
            assert np.array_equal(baseline[untouched],changed[untouched])
            print(f'  no carve: {untouched.sum()} points bit-identical with the floor rule isolated',flush=True)
        finally:
            cp.EROSION_GULLY_ROCK = rock


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-file',default='x64/Release/cp-avant-fonds.py')
    args=parser.parse_args()
    old=load_before(args.before_file)
    analytic(old)
    floors(old)
    print('ok',flush=True)
