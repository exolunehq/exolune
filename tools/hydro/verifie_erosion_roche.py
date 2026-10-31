"""Requested Part E CPU measurements, same caches for integration, Part D and the current port.

No engine or rendering. References: git show fe22cfe:tools/hydro/cp.py and git show 1ca9743:tools/hydro/cp.py.
"""
import argparse
import inspect
import subprocess
import types
from pathlib import Path

import numpy as np
import cp
from verifie_fonds_vallees import flood, sample
from verifie_pentes_ravines import cliffs, PLACES, coasts


def reference(revision):
    code = subprocess.check_output(['git','show',f'{revision}:tools/hydro/cp.py'])
    m = types.ModuleType(revision)
    m.__file__ = cp.__file__
    exec(compile(code,revision,'exec'),m.__dict__)
    return m


def stats(z,n,step):
    dy,dx = np.gradient(z.reshape(n,n),step)
    angle = np.degrees(np.arctan(np.hypot(dx,dy)))
    return [100*np.mean(angle>t) for t in (35,45,60)]+[angle.max()]


def windows(old,integration):
    for lat,lon in PLACES[:4]+[(-25.60,-26.94),(-46.9,-33.8)]:
        n,step = (101,1.) if (lat,lon) in PLACES[:4] else (201,25.)
        p = cp.window(cliffs.direction(lat,lon)[0],n*step,n)
        results = []
        for label,m in [('integration',integration),('D',old),('E',cp)]:
            z=m.elevation(m.Ctx(step),p)
            values=stats(z,n,step)
            results.append(values)
            print(f'{lat},{lon} {n-1:g}x{step:g}m {label}: >35/>45/>60 {values[:3]}; max {values[3]:.6f}',flush=True)
        if step==1:
            assert abs(results[2][1]-results[1][1]) <= 1.0, 'the accepted soil window lost its protection'
        else:
            # "Close" at this scale: 15% of the reference share, with a two-point allowance for rare steep walls.
            assert np.all(abs(np.array(results[2][:3])-results[0][:3]) <= np.maximum(2.,.15*np.array(results[0][:3]))), 'the broad gullies remain unlike integration'
    assert cp._gully_rock(.3,3000.,1.,1.) == 0.
    assert cp._gully_rock(10.,3000.,0.,1.) == 0.
    assert cp._gully_rock(10.,3000.,1.,0.) > .5


def oval_center(index):
    p=cliffs.direction(*[(-25.566,-26.916),(-25.486,-27.075)][index])[0]
    if index==0:
        north=np.array([0.,1.,0.])-p*p[1]
        north/=np.linalg.norm(north)
        delta=2325.*north+1475.*np.cross(p,north)
        p=cp.move(p[None,:],delta[None,:]/np.linalg.norm(delta),[np.linalg.norm(delta)])[0]
    return p


def warp(p):
    w=cp.turbulence(cp.Ctx(5.),p,cp.R_KM/cp.EROSION_WARP[0],cp.EROSION_WARP[1]/(cp.SIGMA*cp.R_KM),2,cp._rseed(9))
    return w/np.linalg.norm(w,axis=1,keepdims=True)


def axis_at(p):
    """Expose the nearest curve only for diagnostics, without changing the port's computation."""
    original=cp.erosion_valleys
    code=inspect.getsource(original)
    code=code.replace('nearest = np.full(N, 1e30)', '''nearest = np.full(N, 1e30)
    v['_node'],v['_t'] = np.zeros(N,dtype=np.int64),np.zeros(N)
    v['_sphere'] = p.copy()
    for key in ('_a','_b','_c'):
        v[key] = np.zeros((N,3))''')
    code=code.replace('nearest = np.where(closer, d, nearest)', '''v['_node'] = np.where(closer,r,v['_node'])
            v['_t'] = np.where(closer,t,v['_t'])
            for key,value in (('_a',a),('_b',b),('_c',end)):
                v[key] = np.where(closer[:,None],value,v[key])
            nearest = np.where(closer, d, nearest)''')
    exec(compile(code,'diagnostic axis','exec'),cp.__dict__)
    try:
        _,v=sample(cp,p[None,:],5.)
    finally:
        cp.erosion_valleys=original
    return v


def thalweg(start):
    v=axis_at(start)
    r=int(v['_node'][0]); t=float(v['_t'][0])
    sphere=v['_sphere'][0]
    a,b,c=(v[key][0]+sphere for key in ('_a','_b','_c'))
    words,n=cp.erosion_map()
    path=[]
    length=0.
    while length<12000.:
        times=np.unique(np.r_[t,np.arange(.25,1.0001,.25)])
        times=times[times>=t]
        knots=np.array([(1-x)**2*a+2*x*(1-x)*b+x*x*c for x in np.arange(0.,1.0001,.25)])
        for x,y in zip(times[:-1],times[1:]):
            left=np.minimum(int(x*4),3)
            q0=knots[left]+(x*4-left)*(knots[left+1]-knots[left])
            q1=knots[left]+(y*4-left)*(knots[left+1]-knots[left])
            span=np.linalg.norm(q1-q0)*cp.R
            count=max(int(np.ceil(span/25)),1)
            points=q0+(q1-q0)*np.linspace(0.,1.,count+1)[:,None]
            path.extend(points[:-1])
            length+=span
        bits=cp._eread(words,np.array([r]))[4][0]
        if not bits & cp._HAS_RECEIVER or bits & (cp._LAKE|cp._SEA):
            break
        rr=int(cp._eneighbour(np.array([r]),np.array([bits & 7]),n)[0])
        r=rr; a=c; b=cp._enode(np.array([r]),n)[0].astype(float)
        bits=cp._eread(words,np.array([r]))[4][0]
        rr=int(cp._eneighbour(np.array([r]),np.array([bits & 7]),n)[0])
        c=.5*(b+cp._enode(np.array([rr]),n)[0].astype(float))
        t=0.
    targets=np.array(path)
    targets/=np.linalg.norm(targets,axis=1,keepdims=True)
    # Invert the angular warp using metre finite differences only in this offline diagnostic.
    x=start+(targets-targets[0])
    x/=np.linalg.norm(x,axis=1,keepdims=True)
    for _ in range(16):
        w=warp(x)
        east=np.cross(x,[0.,1.,0.]); east/=np.linalg.norm(east,axis=1,keepdims=True)
        north=np.cross(east,x)
        te=np.cross(targets,[0.,1.,0.]); te/=np.linalg.norm(te,axis=1,keepdims=True)
        tn=np.cross(te,targets)
        we=warp(cp.move(x,east,np.ones(len(x))))-w
        wn=warp(cp.move(x,north,np.ones(len(x))))-w
        delta=targets-w
        j11=(we*te).sum(1); j12=(wn*te).sum(1)
        j21=(we*tn).sum(1); j22=(wn*tn).sum(1)
        d1=(delta*te).sum(1); d2=(delta*tn).sum(1)
        determinant=j11*j22-j12*j21
        de=(d1*j22-d2*j12)/determinant
        dn=(d2*j11-d1*j21)/determinant
        scale=np.minimum(1.,2000./np.maximum(np.hypot(de,dn),1e-20))
        x+=((de*scale)[:,None]*east+(dn*scale)[:,None]*north)/cp.R
        x/=np.linalg.norm(x,axis=1,keepdims=True)
    error=np.linalg.norm(warp(x)-targets,axis=1)*cp.R
    assert error.max()<.01, f'angular warp inversion residual {error.max()} m'
    distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(x,axis=0),axis=1)*cp.R)]
    assert distance[-1]>=5000., 'the traced link reached its lake/outlet before 5 km'
    # Keep the original on-axis points: no interpolation off a curved thalweg.
    ids=np.unique(np.searchsorted(distance,np.arange(0.,5000.01,25.)))
    return x[ids],distance[ids],error.max()


def troughs(old):
    for index in (0,1):
        center=oval_center(index)
        p=cp.window(center,4025.,161)
        start=center
        for label,m in [('D',old),('E',cp)]:
            z,v=sample(m,p,5.)
            total=flood(z.reshape(161,161)).ravel()-z
            coarse=flood(v['cut'].reshape(161,161)).ravel()-v['cut']
            wet=(v['coarse']-v['cut']>60.) & (abs(v['cut']-v['level'])<1e-8)
            print(f'oval {index} {label}: square closed max {total.max():.9f}m; coarse {coarse.max():.9f}m; '
                  f'water-clamped floor closed max {total[wet].max():.9f}m',flush=True)
            np.savez(f'x64/Release/erosion-e-oval-{index}-{label}.npz',points=p,height=z,closed=total,**v)
            if label=='D' and index==1:
                start=p[np.argmax(coarse)]
            if label=='E':
                assert coarse.max()<.1, 'the coarse carve still closes its trough'
                assert total[wet].max()<.1, 'the water-clamped floor is still closed'
        points,distance,error=thalweg(start)
        print(f'oval {index}: thalweg {len(points)} samples down {distance[-1]:.3f}m, inverse warp error {error:.9g}m',flush=True)
        for cell in (5.,200.):
            for label,m in [('D',old),('E',cp)]:
                z,v=sample(m,points,cell)
                delta=z-v['level']; coarse=v['cut']-v['level']
                print(f'  {label} mesh {cell:g}m: thalweg ground-water [{delta.min():.9f},{delta.max():.9f}]m; '
                      f'coarse-water [{coarse.min():.9f},{coarse.max():.9f}]m',flush=True)
                np.savetxt(f'x64/Release/erosion-e-thalweg-{index}-{label}-{cell:g}.csv',np.column_stack((distance,z,v['cut'],v['level'])),
                           delimiter=',',header='distance_m,ground_m,coarse_carve_m,water_m',comments='')
                if label=='E':
                    assert max(abs(delta).max(),abs(coarse).max())<.1
                    assert np.diff(v['level']).max()<=.01, 'the traced water goes uphill'
    words,n=cp.erosion_map()
    # Query actual lake outlets with an incoming link; isolated lake cells have no level-1 curve to read.
    lakes=np.flatnonzero(((words[:,1] & cp._LAKE)!=0) & (((words[:,1]>>4)&255)!=0))
    ids=lakes[np.linspace(0,len(lakes)-1,min(len(lakes),16)).astype(int)]
    nodes=cp._enode(ids,n).astype(float)
    nodes/=np.linalg.norm(nodes,axis=1,keepdims=True)
    levels=cp._eread(words,ids)[0]
    actual=cp.erosion_valleys(nodes,.005,.6)['level']
    assert abs(actual-levels).max()<.1, 'a level-0 lake lost its own level'
    print(f'level-0 lake outlets: {len(ids)} nodes with inflow, max water-level error {abs(actual-levels).max():.9g}m',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only',choices=('windows','troughs','coasts'))
    args=parser.parse_args()
    old=reference('1ca9743')
    if args.only in (None,'windows'):
        windows(old,reference('fe22cfe'))
    if args.only in (None,'troughs'):
        troughs(old)
    if args.only in (None,'coasts'):
        coasts(old)
    print('ok',flush=True)
