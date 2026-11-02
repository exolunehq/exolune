"""Valley-filter regression checks: independent quadrature and fixed terrain positions.

CPU only. No rendering or performance benchmark.
Run from the repository root: python tools/hydro/verifie_filtre_vallees.py
"""
import json
from pathlib import Path

import numpy as np
import cp
from verifie_lames import direction
from verifie_erosion_roche import reference as historical_reference


def physical_parameters(q, ice, slope, walls):
    floor = min(max(2.*np.sqrt(q)*np.clip(.002/max(slope,1e-6),1.,15.),max(1.,2.4*np.sqrt(q))),4000.)
    glacier = np.clip(np.log2(max(ice,1.))-22.,0.,1.)
    curvature = .3/np.clip(600.*(max(ice,1.)/1e8)**.4,150.,1500.)
    shoulder = .85/(2.*curvature)
    return floor, glacier, curvature, shoulder


def raw_profile(x, q, ice, slope, walls):
    floor, glacier, curvature, shoulder = physical_parameters(q,ice,slope,walls)
    x = np.abs(x)
    v = walls*np.maximum(x-floor,0.)
    u = np.where(x <= shoulder, curvature*x*x, .85*(x-.5*shoulder))
    return v+(u-v)*glacier


def quadrature(d, radius, q, ice, slope, walls):
    """Gauss integration split at every physical kink; each piece has degree at most two."""
    floor, _, _, shoulder = physical_parameters(q,ice,slope,walls)
    bounds = sorted(set([d-radius,d+radius]+[x for x in (-floor,floor,-shoulder,shoulder)
                                           if d-radius < x < d+radius]))
    nodes, weights = np.polynomial.legendre.leggauss(3)
    integral = 0.
    for lo,hi in zip(bounds[:-1],bounds[1:]):
        x = .5*(lo+hi)+.5*(hi-lo)*nodes
        integral += .5*(hi-lo)*np.dot(weights,raw_profile(x,q,ice,slope,walls))
    return integral/(2.*radius)


def profiles():
    count, max_error, max_derivative_error = 0,0.,0.
    for ice in (0.,6e6,1e8):
        for q in (.004,100.):
            floor, glacier, _, shoulder = physical_parameters(q,ice,.01,.65)
            limit = .65+(.85-.65)*glacier
            for radius in (2.,8.,64.,2000.,10000.):
                distances = np.array([0.,floor,abs(floor-.5*radius),floor+.5*radius,
                                      abs(shoulder-.5*radius),shoulder,shoulder+.5*radius,
                                      max(floor,shoulder)+2.*radius])
                z,flat,_,rise = cp._erosion_profile(distances,0.,q,ice,.01,.65,0.,2.*radius,4000.)
                oracle = np.array([quadrature(d,radius,q,ice,.01,.65) for d in distances])
                raw = raw_profile(distances,q,ice,.01,.65)
                max_error = max(max_error,float(abs(z-oracle).max()))
                assert np.all(z >= raw-1e-9), 'Averaging excavates a convex profile'
                assert np.all(z-raw <= limit*radius/2.+1e-9), 'Filter exceeds the physical slope bound'
                assert abs(z[-1]-raw[-1]) < 1e-8, 'A distant planar bank moved'
                assert np.all((rise >= -1e-12)&(rise <= limit+1e-12))
                # Narrow channels put a kernel endpoint exactly on a bank kink. A smaller symmetric step keeps
                # this numerical oracle accurate across the resulting jump of the second derivative.
                derivative_step = 1e-4
                shifted = np.array([(quadrature(d+derivative_step,radius,q,ice,.01,.65)
                                     -quadrature(d-derivative_step,radius,q,ice,.01,.65))/(2.*derivative_step) for d in distances])
                max_derivative_error = max(max_derivative_error,float(abs(rise-shifted).max()))
                for depth in (1e-6,1.,1000.):
                    other = cp._erosion_profile(distances,0.,q,ice,.01,.65,depth,2.*radius,4000.)
                    assert np.array_equal(z,other[0]), 'Coarse reference depth changes filtering'
                    assert np.array_equal(flat,other[1]), 'Coarse reference depth moves the floor mask'
                count += len(distances)
    assert max_error < 1e-8, max_error
    assert max_derivative_error < 1e-5, max_derivative_error
    return dict(samples=count,quadrature_error_m=max_error,derivative_error=max_derivative_error)


def terrain():
    rows=[]
    old_profile = historical_reference('7187c1b')._erosion_profile
    # The snowy pose comes from the running engine while the user reported the mutation.
    # The other two regions guard existing troughs. Coastal-cliff filtering is a separate system.
    for name,lat,lon in [('snowy_approach',-46.85004,-33.85772),
                         ('snowy_trough_witness',-25.6,-26.94),('tropical_trough_witness',-5.6,127.9)]:
        points=cp.window(direction(lat,lon),4000.,61)
        reference=cp.elevation(cp.Ctx(1.),points)
        assert np.array_equal(reference,cp.elevation(cp.Ctx(.25),points))
        row=dict(name=name,lat=lat,lon=lon)
        for cell,bound in ((4.,5.),(16.,25.)):
            z=cp.elevation(cp.Ctx(cell),points)
            change=float(abs(z-reference).max())
            row[f'max_change_at_{cell:g}m']=change
            assert change < bound, (name,cell,change)
        if name == 'snowy_approach':
            # Reproduce the historical defect with its signed-detail composition. The current envelope bound can
            # mask the former dilation, so restoring only its profile is no longer a valid failing control.
            current_profile, current_carve = cp._erosion_profile, cp.erosion_carve
            cp._erosion_profile = old_profile
            cp.erosion_carve = lambda h,coarse,v,k: cp.erosion_cut(h,v['surface']+(h-coarse)*(1.-v['floor']),k)
            try:
                old_resolved = cp.elevation(cp.Ctx(1.),points)
                for cell in (4.,16.):
                    change = float(abs(cp.elevation(cp.Ctx(cell),points)-old_resolved).max())
                    row[f'before_at_{cell:g}m'] = change
                    assert change > 100., 'The old filter no longer reproduces the reported mutation'
            finally:
                cp._erosion_profile, cp.erosion_carve = current_profile, current_carve
        rows.append(row)
    return rows


if __name__=='__main__':
    report=dict(profiles=profiles(),terrain=terrain())
    out=Path('x64/erosion-continuation/filter-checks.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
