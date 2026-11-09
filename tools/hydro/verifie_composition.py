"""Functional checks for bounded valley and channel composition.

No performance or image-quality benchmark. Run from the repository root.
"""
import json
from pathlib import Path

import numpy as np
import cp
from verifie_lames import direction


def flat_valley(surface, floor):
    surface = np.asarray(surface)
    link = dict(d=np.zeros_like(surface), z=surface, floor_width=np.full_like(surface,1e6),
                curvature=np.full_like(surface,.001), glacier=np.zeros_like(surface))
    empty = dict(link, z=np.full_like(surface,1e9))
    return dict(surface=surface, floor=floor, links=[link,empty], walls=.65, box_radius=2.)


def analytic():
    rng = np.random.default_rng(714)
    n = 20000
    coarse = rng.uniform(-500.,7000.,n)
    parent = coarse+rng.uniform(-2500.,2500.,n)
    profile = coarse+rng.uniform(-4000.,3000.,n)
    v = flat_valley(profile,rng.random(n))
    out = cp.erosion_carve(parent,coarse,v,60.)
    assert np.all(out<=parent+1e-9), 'Erosion raised existing terrain'
    assert np.all(out>=np.minimum(parent,profile)-1e-9), 'Detail excavated below the valley envelope'
    assert np.all(parent-out<=np.maximum(parent-profile,0.)+1e-9), 'Detail deepened the physical valley profile'
    hollow = parent<=profile
    assert np.array_equal(out[hollow],parent[hollow]), 'A pre-existing hollow was filled or deepened'
    # A height datum must not alter an erosion process. No implicit sea-level clamp belongs to this composition.
    shift = 2000.
    shifted = cp.erosion_carve(parent+shift,coarse+shift,flat_valley(profile+shift,v["floor"]),60.)
    assert np.max(abs(shifted-out-shift))<1e-8

    # A shallow incision must reach the draining floor. The shoulder join formerly left a dam here.
    parent = np.array([20.,31.,31.001,39.,60.,120.])
    v = flat_valley(np.full_like(parent,31.),np.ones_like(parent))
    floor = cp.erosion_carve(parent,np.full_like(parent,80.),v,60.)
    assert np.allclose(floor,np.minimum(parent,31.),rtol=0.,atol=1e-12)
    assert np.isfinite(cp.erosion_cut(31.,31.,0.))
    # The same join still rounds the shoulders and stays bounded while its width tends to zero.
    share = np.linspace(0.,1.,10001)
    joined = cp.erosion_carve(39.,80.,flat_valley(np.full_like(share,31.),share),60.)
    assert np.isfinite(joined).all() and np.all((joined>=31.)&(joined<=39.))
    assert np.all(np.diff(joined)<=1e-10)
    assert np.max(abs(np.diff(joined)))<.01

    # A constant hillside residual formerly became two deeper side channels beside an intact floor.
    x = np.linspace(-1000.,1000.,4001)
    profile = 30.+.25*np.maximum(abs(x)-100.,0.)
    floor = 1.-cp._smooth(100.,300.,abs(x))
    parent = np.full_like(x,220.)
    v = flat_valley(profile,floor)
    section = cp.erosion_carve(parent,np.full_like(x,400.),v,60.)
    assert section.min()>=30.-1e-9
    assert np.all(np.diff(section[len(x)//2:])>=-1e-9), 'A constant residual made a reverse bank'

    # Different tributaries may win the envelopes. Their stage metadata must not become an independent clamp.
    s = np.minimum(20.+.3*abs(x+200.),140.+.5*abs(x-200.))
    v = flat_valley(s,np.zeros_like(x))
    out = cp.erosion_carve(np.full_like(x,500.),np.full_like(x,600.),v,60.)
    assert np.max(abs(np.diff(out)))<.26, 'A tributary switch introduced a height jump'
    return dict(random_sections=n,transverse_samples=len(x))


def channels():
    heights = np.linspace(-500.,5000.,2001)
    count = 0
    for stage in (0.,50.,2000.):
        for q in (.06,1.,100.,10000.):
            width,depth = cp.erosion_river_size(q)
            for d in (0.,width,.5*width,width+400.):
                bed = cp.erosion_river_profile(d,stage,q,.65,2.)
                top = bed+cp.erosion_river_cut(d,q,2.)
                cut = cp.erosion_channel_cut(heights,bed,top)
                assert np.all((cut>=0.)&(cut<=depth+1e-8)), 'Channel cutting excavated another valley'
                assert np.all(heights-cut>=np.minimum(heights,bed)-1e-8)
                assert np.all(cut[heights<=bed]==0.), 'A pre-existing hollow was cut again'
                assert np.max(cut)<=top-bed+1e-8
                count += len(heights)
    return dict(channel_samples=count)


def terrain():
    cases = [('perched_river',-12.406891,52.928246,12000.),
             ('junction',-12.486714,52.694265,20000.),
             ('snowy_range',-25.6,-26.94,20000.),
             ('collision_range',-7.5,117.,40000.),
             ('cold_range',-46.9,-33.8,30000.),
             ('plain_river',7.967792903,-84.518564462,4000.)]
    rows = []
    original = cp.erosion_carve
    state = {}
    def record(h,coarse,v,k):
        out = original(h,coarse,v,k)
        state.update(parent=h.copy(),coarse=coarse.copy(),carved=out.copy(),**v)
        return out
    cp.erosion_carve = record
    try:
        for name,lat,lon,size in cases:
            p = cp.window(direction(lat,lon),size,65)
            ground = cp.elevation(cp.Ctx(8.),p,extra=True)
            delta = state['parent']-state['carved']
            assert np.all(delta>=-1e-8)
            detail = state['parent']-state['coarse']
            tail = np.maximum(60.-abs(detail),0.)
            lift = (np.maximum(detail,0.)+tail*tail/240.)*(1.-state['floor'])
            local_ground = state['parent']-lift
            clipped = [cp.erosion_clipped_section(link,local_ground,state['walls'],state['box_radius'])
                       for link in state['links']]
            bound = np.minimum(*clipped)
            assert np.all(state['carved']>=bound-1e-8), name
            for link, value in zip(state['links'],clipped):
                assert np.all(value>=np.minimum(local_ground,link['z'])-1e-8), name
            assert np.isfinite(ground['surface']).all()
            rows.append(dict(name=name,samples=len(p),incised=int(np.sum(delta>1.)),
                             max_incision_m=float(delta.max()),
                             wet_samples=int(np.sum((ground['water_depth']>.1)&(ground['water_level']>1.)))))
    finally:
        cp.erosion_carve = original

    centre = direction(-12.4068909864,52.9309713794)
    flow = cp.elevation(cp.Ctx(2.),centre[None,:],extra=True)['flow'][0]
    across = np.cross(centre,flow)
    across /= np.linalg.norm(across)
    x = np.linspace(-2500.,2500.,1001)
    p = centre[None,:]+across[None,:]*x[:,None]/cp.R
    p /= np.linalg.norm(p,axis=1,keepdims=True)
    ground = cp.elevation(cp.Ctx(2.),p,extra=True)
    banks = (abs(x)>=125.)&(abs(x)<=500.)
    assert ground['elev'][banks].min()>30., 'The reported river remains perched above artificial side pools'
    assert ground['water_depth'][500]>.1, 'Fixing the banks erased the reported river'
    return dict(windows=rows,reported_bank_min_m=float(ground['elev'][banks].min()),
                reported_centre_depth_m=float(ground['water_depth'][500]))


if __name__=='__main__':
    report = dict(analytic=analytic(),channels=channels(),terrain=terrain())
    path = Path('x64/water-approach/composition-checks.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
