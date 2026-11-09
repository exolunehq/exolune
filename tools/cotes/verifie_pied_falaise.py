"""Cliff-toe regression: monotone talus contact and fixed coastal witnesses.

CPU checks only; no performance or image-quality benchmark.
Run from the repository root: python tools/cotes/verifie_pied_falaise.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hydro'))
import cp
from verifie_falaises import direction, evaluate


def old_scree(h, hc, delta, talus, gradient):
    return np.maximum(talus-cp.EROSION_CLIFF_SCREE[0]*abs(h-hc)/gradient,0.)


def contact_oracle(hc, delta, talus):
    """Independent bisection of the physical face, not the production Newton iteration."""
    lo, hi = hc, hc+delta
    target = cp.EROSION_CLIFF_PLATFORM[0]+talus
    for _ in range(60):
        mid = (lo+hi)*.5
        t = (mid-hc)/delta
        surface = mid-(hc-cp.EROSION_CLIFF_PLATFORM[0])*(1.-3.*t*t+2.*t*t*t)
        if surface < target:
            lo = mid
        else:
            hi = mid
    return (lo+hi)*.5


def section(model, h, hc, delta, depth, talus, gradient):
    bare = cp.erosion_cliff_profile(h,hc,delta,depth)
    platform = cp.EROSION_CLIFF_PLATFORM[0]-depth*(1.-np.minimum(h/hc,1.))
    return np.minimum(h,np.maximum(bare,platform+model(h,hc,delta,talus,gradient)))


def profiles():
    count, error, rejected = 0, 0., 0
    for hc in (8.,30.,100.,400.):
        for delta in (.1*hc,hc,10.*hc):
            for depth in (0.,4.):
                for gradient in (.002,.05,.2,2.):
                    for fraction in (0.,.01,.11,.22):
                        talus = fraction*hc
                        contact = contact_oracle(hc,delta,talus)
                        h = np.unique(np.r_[np.linspace(-hc,hc,257),hc+delta*np.linspace(0.,1.,1025),
                                             contact-1e-5,contact,contact+1e-5,hc+delta+1.])
                        expected = np.maximum(talus-cp.EROSION_CLIFF_SCREE[0]*np.maximum(contact-h,0.)/gradient,0.)
                        actual = cp.erosion_cliff_scree(h,hc,delta,talus,gradient)
                        error = max(error,float(abs(actual-expected).max()))
                        z = section(cp.erosion_cliff_scree,h,hc,delta,depth,talus,gradient)
                        assert np.isfinite(z).all()
                        assert np.all(np.diff(z)>=-1e-8), 'The talus falls again towards the wall'
                        assert np.all(z<=h+1e-9), 'The talus rises above original terrain'
                        assert np.all(z>=cp.erosion_cliff_profile(h,hc,delta,depth)-1e-9)
                        if talus == 0.:
                            assert np.array_equal(z,section(old_scree,h,hc,delta,depth,talus,gradient))
                        previous = section(old_scree,h,hc,delta,depth,talus,gradient)
                        rejected += bool(np.any(np.diff(previous)<-1e-6))
                        count += 1
    assert error<1e-7, error
    assert rejected>0, 'The old profile no longer reproduces a back slope'
    # Parameters recovered at the reported pose. Only the test contains this location's values.
    hc, gradient = 99.22333923686524, .20560170127804567
    h = np.linspace(hc-20.,hc*1.1+5.,10001)
    drops = {}
    for name,model in [('before',old_scree),('after',cp.erosion_cliff_scree)]:
        z = section(model,h,hc,.1*hc,4.,.22*hc,gradient)
        drops[name] = float((np.maximum.accumulate(z)-z).max())
    assert drops['before']>5. and drops['after']<1e-8
    return dict(sections=count,old_sections_with_moat=rejected,oracle_error_m=error,
                reported_section_landward_drop_m=drops)


def terrain():
    rows=[]
    for name,lat,lon,size,n in [
        ('reported_cold_cliff',-47.008952,-32.993928,128.,129),
        ('tropical_coast',8.48997,-103.55646,400.,65),
        ('southern_coast',-23.18981,157.86949,1000.,65),
        ('flat_coast',16.71,-89.28,400.,65),
    ]:
        points=cp.window(direction(lat,lon)[0],size,n)
        source,after,_,_=evaluate(points,1.)
        current=cp.erosion_cliff_scree
        cp.erosion_cliff_scree=old_scree
        try:
            _,before,_,_=evaluate(points,1.)
        finally:
            cp.erosion_cliff_scree=current
        assert np.isfinite(after).all() and np.all(after<=source+1e-6)
        if name=='flat_coast':
            assert np.array_equal(before,after), 'The flat coast changed'
        rows.append(dict(name=name,lat=lat,lon=lon,samples=len(points),
                         max_change_m=float(abs(after-before).max()),
                         before_ground_m=float(before[len(points)//2]),
                         after_ground_m=float(after[len(points)//2])))
    # The physical coast metric can reject the former reported cut altogether. The profile oracle above still
    # reproduces that talus failure; at least one valid present-day cliff must exercise the full terrain path.
    assert any(row['max_change_m']>1. for row in rows), 'No current cliff exercises the talus'
    return rows


if __name__=='__main__':
    report=dict(profiles=profiles(),terrain=terrain())
    out=Path('x64/erosion-cliff-toe/checks.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
