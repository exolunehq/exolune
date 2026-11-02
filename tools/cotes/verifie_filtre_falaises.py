"""Coastal-filter regression: composed physical profile, independent quadrature and fixed terrain witnesses.

CPU only; no engine, rendering or performance/quality benchmark.
Run from the repository root: python tools/cotes/verifie_filtre_falaises.py [--profiles-only]
"""
import argparse
import inspect
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hydro'))
import cp


def contact(hc, delta, talus):
    """Independent bisection, not the production Newton iteration or factored quadratic."""
    lo, hi = 0., 1.
    for _ in range(60):
        t = .5*(lo+hi)
        if delta*t+(hc-cp.EROSION_CLIFF_PLATFORM[0])*t*t*(3.-2.*t) < talus:
            lo = t
        else:
            hi = t
    return hc+delta*.5*(lo+hi)


def physical(h, hc, delta, depth, talus, gradient):
    """Definition of the physical profile; no production mean, join partition or quadrature is reused."""
    foot = cp.EROSION_CLIFF_PLATFORM[0]
    platform = foot-depth+depth*np.minimum(h/hc,1.)
    t = np.clip((h-hc)/delta,0.,1.)
    bare = h-np.minimum(np.maximum(h-platform,0.),(hc-foot)*(1.-3.*t*t+2.*t*t*t))
    apron = platform+np.maximum(talus-cp.EROSION_CLIFF_SCREE[0]*np.maximum(contact(hc,delta,talus)-h,0.)/gradient,0.)
    return np.minimum(h,np.maximum(bare,apron))


G8, G16 = np.polynomial.legendre.leggauss(8), np.polynomial.legendre.leggauss(16)


def integrate(fn, lo, hi, tolerance=2e-10, depth=0):
    if hi<=lo:
        return 0.
    mid, half = .5*(lo+hi), .5*(hi-lo)
    a = half*np.dot(G8[1],fn(mid+half*G8[0]))
    b = half*np.dot(G16[1],fn(mid+half*G16[0]))
    if abs(a-b)<tolerance or depth>=22:
        return float(b)
    return integrate(fn,lo,mid,tolerance*.5,depth+1)+integrate(fn,mid,hi,tolerance*.5,depth+1)


def oracle(h, radius, hc, delta, depth, talus, gradient):
    if radius==0.:
        return float(physical(np.array(h),hc,delta,depth,talus,gradient))
    bottom = (cp.EROSION_CLIFF_PLATFORM[0]-depth)/(1.-depth/hc)
    meet = contact(hc,delta,talus)
    toe = meet-talus*gradient/cp.EROSION_CLIFF_SCREE[0]
    # Normalize the independent quadrature as well: h +/- tiny radius must not lose the integration width.
    landmarks = [(x-h)/radius for x in (bottom,hc,hc+delta,meet,toe)]
    bounds = sorted(set([-1.,1.]+[x for x in landmarks if -1.<x<1.]))
    fn = lambda u: (h+radius*u)-physical(h+radius*u,hc,delta,depth,talus,gradient)
    return h-.5*sum(integrate(fn,a,b) for a,b in zip(bounds[:-1],bounds[1:]))


def profiles():
    count, error, float_error, limit_error = 0,0.,0.,0.
    for hc in (8.,100.,400.):
        for g in (.002,.05,.2,.7,2.,10.):
            for depth in (0.,4.):
                for share in (0.,.22):
                    delta, talus = .1*hc, share*hc
                    for cell in (.001,2.,64.,512.):
                        radius = g*cell
                        h = hc+radius*np.array([-1.1,-.25,0.,.6,1.1])+.4*delta
                        actual = cp.erosion_cliff_mean(h,hc,delta,depth,talus,g,radius)
                        expected = np.array([oracle(v,radius,hc,delta,depth,talus,g) for v in h])
                        error = max(error,float(abs(actual-expected).max()))
                        assert np.isfinite(actual).all() and np.all(actual<=h+1e-9)
                        assert np.all(actual>=h-(hc-cp.EROSION_CLIFF_PLATFORM[0])-1e-9)
                        f32 = [np.asarray(x,np.float32) for x in (h,hc,delta,depth,talus,g,radius)]
                        low = cp.erosion_cliff_mean(*f32)
                        precise = cp.erosion_cliff_mean(*(x.astype(np.float64) for x in f32))
                        float_error = max(float_error,float(abs(low-precise).max()))
                        count += len(h)
                    h = np.linspace(-20.,hc+delta+2.,1001)
                    raw = physical(h,hc,delta,depth,talus,g)
                    point = cp.erosion_cliff_mean(h,hc,delta,depth,talus,g,0.)
                    limit_error = max(limit_error,float(abs(raw-point).max()))
                    for radius in (.2,4.,64.):
                        z = cp.erosion_cliff_mean(h,hc,delta,depth,talus,g,radius)
                        assert np.min(np.diff(z))>=-1e-8,'The filtered supported profile reverses slope'
                        bottom = (cp.EROSION_CLIFF_PLATFORM[0]-depth)/(1.-depth/hc)
                        outside = (h+radius<=bottom)|(h-radius>=hc+delta)
                        assert np.array_equal(z[outside],h[outside]),'Filtering exceeds its physical support'
    assert error<1e-7,error
    assert float_error<.002,float_error
    assert limit_error<1e-8,limit_error
    return dict(oracle_samples=count,quadrature_error_m=error,float32_error_m=float_error,zero_radius_error_m=limit_error)


def area():
    rows=[]
    hc,g,delta,depth=100.,.2,10.,4.
    bottom=(cp.EROSION_CLIFF_PLATFORM[0]-depth)/(1.-depth/hc)
    for talus in (0.,22.):
        x=np.linspace(bottom/g,(hc+delta)/g,50001)
        incision=x*g-physical(x*g,hc,delta,depth,talus,g)
        initial=float(np.trapezoid(incision,x))
        centre=float(np.trapezoid(x*incision,x)/initial)
        for cell in (16.,64.,256.):
            x=np.linspace(bottom/g-cell,(hc+max(delta,2.*cell*g))/g+cell,50001)
            cut=x*g-cp.erosion_cliff_mean(x*g,hc,delta,depth,talus,g,cell*g)
            old=x*g-physical(x*g,hc,max(delta,2.*cell*g),depth,talus,g)
            filtered=float(np.trapezoid(cut,x))
            drift=float(np.trapezoid(x*cut,x)/filtered-centre)
            area_error=abs(filtered/initial-1.)
            assert area_error<1e-7 and abs(drift)<1e-5,(area_error,drift)
            rows.append(dict(talus_m=talus,cell_m=cell,relative_area_error=area_error,centroid_shift_m=drift,
                             old_area_change_percent=float(100.*(np.trapezoid(old,x)/initial-1.)),
                             old_crest_shift_m=(max(delta,2.*cell*g)-delta)/g))
    return rows


def joins():
    """Both apron/face branch transitions, including the partial cubic/linear overlap."""
    maximum, discontinuity, samples = 0.,0.,0
    for hc in (8.,100.,400.):
        delta,talus=.1*hc,.22*hc
        meet=contact(hc,delta,talus)
        t=(meet-hc)/delta
        foot_slope=talus/(meet-hc)
        contact_slope=1.+6.*(hc-cp.EROSION_CLIFF_PLATFORM[0])*t*(1.-t)/delta
        for slope in (foot_slope,.5*(foot_slope+contact_slope),contact_slope):
            g=cp.EROSION_CLIFF_SCREE[0]/slope
            h=np.array([hc-.2*delta,hc,hc+.5*(meet-hc),meet,hc+delta])
            radius=16.*g
            actual=cp.erosion_cliff_mean(h,hc,delta,4.,talus,g,radius)
            expected=np.array([oracle(v,radius,hc,delta,4.,talus,g) for v in h])
            maximum=max(maximum,float(abs(actual-expected).max()))
            below=cp.erosion_cliff_mean(h,hc,delta,4.,talus,g*(1.-1e-7),radius)
            above=cp.erosion_cliff_mean(h,hc,delta,4.,talus,g*(1.+1e-7),radius)
            discontinuity=max(discontinuity,float(abs(above-below).max()))
            samples+=len(h)
    assert maximum<1e-7 and discontinuity<1e-4,(maximum,discontinuity)
    return dict(samples=samples,oracle_error_m=maximum,parameter_step_change_m=discontinuity)


def terrain():
    # Reconstruct only the replaced dilation, holding the current source terrain and all other composition fixed.
    source=inspect.getsource(cp.erosion_coast)
    current_line='delta, footprint = EROSION_CLIFF_FACE * hc, 1000.0 * cell_km * g'
    assert source.count(current_line)==1
    source=source.replace(current_line,'delta, footprint = np.maximum(EROSION_CLIFF_FACE * hc, 2000.0 * cell_km * g), 0.0')
    namespace=dict(cp.__dict__)
    exec(source,namespace)
    previous,current=namespace['erosion_coast'],cp.erosion_coast
    rows=[]
    for name,lat,lon,size in [('tropical_coast',8.48997,-103.55646,800.),
                             ('southern_coast',-23.18981,157.86949,1000.),
                             ('cold_coast',-47.008952,-32.993928,800.),
                             ('flat_coast',16.71,-89.28,800.)]:
        la,lo=np.radians([lat,lon])
        centre=np.array([np.cos(la)*np.cos(lo),np.sin(la),np.cos(la)*np.sin(lo)])
        points=cp.window(centre,size,17)
        row=dict(name=name,samples=len(points))
        for cell in (1.,64.):
            after=cp.elevation(cp.Ctx(cell),points)
            cp.erosion_coast=previous
            try:
                before=cp.elevation(cp.Ctx(cell),points)
            finally:
                cp.erosion_coast=current
            assert np.isfinite(after).all()
            change=float(abs(after-before).max())
            if name=='flat_coast':
                assert np.array_equal(before,after),'Flat coast changed'
            row[f'max_change_at_{cell:g}m']=change
        print(json.dumps(row),flush=True)
        rows.append(row)
    assert any(x['max_change_at_64m']>1. for x in rows),'No coastal witness exercises the filter'
    return rows


if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('--profiles-only',action='store_true')
    options=args.parse_args()
    report=dict(profiles=profiles(),joins=joins(),area=area())
    if not options.profiles_only:
        report['terrain']=terrain()
    out=Path('x64/coast-filter/production-checks.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
