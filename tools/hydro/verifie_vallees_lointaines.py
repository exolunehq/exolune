"""Clipped valley sections and fixed terrain windows; CPU only."""
import json
import numpy as np
import cp
from verifie_lames import direction
from verifie_filtre_vallees import physical_parameters


def link(d, z, f, c, glacier):
    return dict(d=np.asarray(d), z=np.asarray(z), floor_width=np.asarray(f),
                curvature=np.asarray(c), glacier=np.asarray(glacier))


def raw(x, f, c, walls):
    t = np.abs(x)
    shoulder = cp.EROSION_GLACIER_WALLS/(2.*c)
    return walls*np.maximum(t-f,0.), c*np.minimum(t,shoulder)**2+cp.EROSION_GLACIER_WALLS*np.maximum(t-shoulder,0.)


def clipped(d, h, r, f, c, glacier, walls=.65, z=0.):
    return cp.erosion_clipped_section(link(d,z,f,c,glacier),h,walls,r)


def analytic():
    f, _, c, shoulder = physical_parameters(100.,1e8,.01,.65)
    max_error = max_close = 0.
    count = 0
    for r in (2., 8., 100., 2000., 20000.):
        for depth in (-10., 0., .1, 100., c*shoulder**2*.8, c*shoulder**2*1.2, 5000.):
            for d in (0., f*.5, f+20., shoulder, shoulder+2*r):
                x = np.linspace(d-r,d+r,131073)
                a,b = raw(x,f,c,.65)
                for g in (0.,.4,1.):
                    # The mixed section clipped once, never each shape clipped then mixed.
                    numerical = np.trapezoid(np.minimum(depth,(1.-g)*a+g*b),x)/(2.*r)
                    value = clipped(d,depth,r,f,c,g)
                    max_error = max(max_error,float(abs(value-numerical)))
                    if r == cp.CREASE_MIN_CELL:
                        uncut = np.trapezoid((1.-g)*a+g*b,x)/(2.*r)
                        max_close = max(max_close,float(abs(value-min(depth,uncut))))
                    count += 1
    assert max_error < .003, max_error
    assert max_close < .5, max_close
    return dict(samples=count, max_quadrature_error_m=max_error, max_close_difference_m=max_close)


def conservation():
    f, _, c, _ = physical_parameters(100.,1e8,.01,.65)
    h = 350.
    errors = []
    for r in (2.,8.,100.,2000.,20000.):
        # Trapezoidal integration on a fixed fine grid resolves both the incision and box edges.
        extent = r+f+h/.65+cp.EROSION_GLACIER_WALLS/(2*c)+h/.85+100.
        x = np.linspace(-extent,extent,400001)
        a,b = raw(x,f,c,.65)
        for g in (0.,.4,1.):
            area = np.trapezoid(np.maximum(h-(1-g)*a-g*b,0.),x)
            filtered = np.trapezoid(h-clipped(abs(x),h,r,f,c,g),x)
            errors.append(abs(filtered-area)/area)
    assert max(errors)<2e-5, max(errors)
    return dict(max_relative_area_error=max(errors))


def continuity():
    f, _, c, shoulder = physical_parameters(100.,1e8,.01,.65)
    max_jump = 0.
    for axis in ('d','r','h'):
        for g in (0.,.4,1.):
            for center in (0.,f,shoulder,500.,2000.):
                d,r,h = 500.,200.,300.
                x = np.linspace(max(center, .01) if axis == 'r' else center, (max(center,.01) if axis == 'r' else center)+.01,101)
                value = clipped(x if axis=='d' else d,x if axis=='h' else h,
                                x if axis=='r' else r,f,c,g)
                max_jump=max(max_jump,float(np.max(abs(np.diff(value)))))
    assert max_jump<.001, max_jump
    return dict(max_step_m=max_jump, input_step=.0001)


def terrain():
    cases = [('snowy_approach',-46.85004,-33.85772,4000.),('snowy_trough',-25.6,-26.94,4000.),
             ('tropical_trough',-5.6,127.9,4000.),('junction',-12.486714,52.694265,20000.),
             ('plain_river',7.967792903,-84.518564462,4000.)]
    original=cp.erosion_carve
    def old(h,coarse,v,k):
        detail=h-coarse
        tail=np.maximum(k-abs(detail),0.)
        spurs=np.maximum(detail,0.)+tail*tail/(4.*k)
        return cp.erosion_cut(h,v['surface']+spurs*(1.-v['floor']),k*(1.-v['floor']))
    rows=[]
    try:
        for spacing in (1.,.25,16.):
            changes=[]
            for name,lat,lon,size in cases:
                p=cp.window(direction(lat,lon),size,41)
                cp.erosion_carve=old
                before=cp.elevation(cp.Ctx(spacing),p)
                cp.erosion_carve=original
                after=cp.elevation(cp.Ctx(spacing),p)
                delta=after-before
                changes.append(dict(name=name,max_abs_m=float(abs(delta).max()),mean_m=float(delta.mean())))
            rows.append(dict(spacing_m=spacing,windows=changes))
    finally:
        cp.erosion_carve=original
    return rows


if __name__=='__main__':
    print(json.dumps(dict(analytic=analytic(),conservation=conservation(),continuity=continuity(),terrain=terrain()),indent=2))
