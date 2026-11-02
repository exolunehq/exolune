"""Functional checks for inland water. No render or performance benchmark.

Run the engine once to create the EXOEROS3 cache, then run this script from the repository root.
"""
import json
from pathlib import Path
import numpy as np
import cp


def profiles():
    nodes, weights = np.polynomial.legendre.leggauss(3)
    error = 0.
    count = 0
    for q in (.06, .5, 10., 1000., 100000.):
        width, depth = cp.erosion_river_size(q)
        for radius in (2., 16., 128., 2048.):
            for d in (0., width*.5, width, width+radius*.5, width+radius*2.):
                bounds = sorted(set([d-radius,d+radius]+[v for v in (-width,width) if d-radius<v<d+radius]))
                integral = 0.
                for lo,hi in zip(bounds[:-1],bounds[1:]):
                    x = .5*(lo+hi)+.5*(hi-lo)*nodes
                    cut = depth*np.maximum(1.-(x/width)**2,0.)**2
                    bank = .65*np.maximum(abs(x)-width,0.)
                    integral += .5*(hi-lo)*np.dot(weights,bank-cut)
                measured = cp.erosion_river_profile(d,0.,q,.65,radius)
                error = max(error,abs(measured-integral/(2.*radius)))
                count += 1
            x = np.linspace(0.,width+2*radius,400)
            h = cp.erosion_river_profile(x,0.,q,.65,radius)
            assert np.all(np.diff(h)>=-1e-8), 'A bank folds back into the river'
            assert np.all(h>=-depth-1e-8), 'Filtering digs deeper than the physical bed'
    assert error<1e-8, error
    return dict(sections=count,max_quadrature_error_m=float(error))


def network():
    words,n = cp.erosion_map()
    basins = cp.erosion_basins()
    assert np.any(basins[:,1]), 'No terminal basins: run the updated engine first'
    ids = np.arange(len(words))
    level,_,_,_,bits = cp._eread(words,ids)
    linked = (bits&cp._HAS_RECEIVER)!=0
    receiver = cp._eneighbour(ids[linked],bits[linked]&7,n)
    assert np.all(level[linked]>=level[receiver]), 'A river runs uphill'
    assert np.array_equal(basins[linked],basins[receiver]), 'Terminal stage changes along a catchment'
    wet = basins[:,1]!=0
    unique = np.unique(basins[wet],axis=0)
    assert len(unique)==len(np.unique(unique[:,1])), 'A lake has several surface levels'
    old = Path(cp._REPO)/'x64/inland-water/erosion-before-0.bin'
    if old.exists():
        before = np.frombuffer(old.read_bytes()[24:],np.uint32).reshape(-1,2)[:len(words)]
        assert np.array_equal(before,words), 'Adding water changed the existing drainage solve'
    return dict(links=int(linked.sum()),terminal_basins=len(unique),lake_catchment_cells=int(wet.sum()))


def envelopes():
    # Two overlapping tributaries at different stages. Taking a winning link's stage would jump at the switch.
    x = np.linspace(-500.,500.,10001)
    beds,tops = [],[]
    for centre,stage,q in ((-100.,30.,3000.),(110.,12.,800.)):
        d = abs(x-centre)
        bed = cp.erosion_river_profile(d,stage,q,.65,2.)
        beds.append(bed);tops.append(bed+cp.erosion_river_cut(d,q,2.))
    for terrain in (np.full_like(x,100.),20.+.1*x,15.+30.*np.sin(x/120.)):
        bed = np.minimum(terrain,np.minimum.reduce(beds))
        top = np.minimum(terrain,np.minimum.reduce(tops))
        assert np.all(top>=bed-1e-9)
        assert np.all(top-bed<=max(cp.erosion_river_size(3000.)[1],cp.erosion_river_size(800.)[1])+1e-8)
        assert np.max(abs(np.diff(top)))<.066, 'A tributary switch creates a water wall'
    return dict(overlap_sections=3,points_per_section=len(x))


def basin_connections():
    words,n=cp.erosion_map();basins=cp.erosion_basins();ids=np.arange(len(words))
    right=np.minimum(ids+1,len(words)-1)
    border=(ids%n<n-1)&(basins[:,1]!=basins[right,1])&((basins[:,1]!=0)|(basins[right,1]!=0))
    lake=((words[:,1]&cp._LAKE)!=0)|((words[right,1]&cp._LAKE)!=0)
    ids=ids[border&lake];ids=ids[np.linspace(0,len(ids)-1,min(512,len(ids))).astype(int)]
    face=ids//(n*n);s=(ids%n+1)*2./n-1.;t=(ids//n%n+.5)*2./n-1.
    centre=cp._edirection(face,s,t).astype(float);centre/=np.linalg.norm(centre,axis=1,keepdims=True)
    across=cp._edirection(face,s+.01,t).astype(float)
    across-=centre*(across*centre).sum(1)[:,None];across/=np.linalg.norm(across,axis=1,keepdims=True)
    differences=[]
    for half_step in (5.,.5):
        p=np.concatenate((centre-across*half_step/cp.R,centre+across*half_step/cp.R))
        p/=np.linalg.norm(p,axis=1,keepdims=True)
        stage=cp.erosion_valleys(p,.002,.65)['lake_level']
        differences.append(abs(stage[:len(ids)]-stage[len(ids):]))
    # A true step retains its height as the interval shrinks. Allow the float32 cube locator's rounding.
    assert np.all(differences[1] <= .3*differences[0]+.5), 'Terminal stage has a discontinuous cell boundary'
    return dict(borders=len(ids),max_step_10m=float(differences[0].max()),max_step_1m=float(differences[1].max()))


def terrain():
    # Reproduction points only. The generator contains no location-specific rules.
    cases = [('river',-1.828016777,69.643755616),('river',7.967792903,-84.518564462),
             ('river',3.163467160,71.926289340),('river',-12.420076761,62.004321796),
             ('lake',42.485748699,-24.571964994),('lake',41.279216597,-28.287525936),
             ('mouth',10.400192245,112.399488633),('mouth',-13.070692636,51.726377504),
             ('mouth',46.525721619,-71.580659240),('mouth',-11.761219936,172.297308544)]
    result=[]
    for kind,lat,lon in cases:
        la,lo=np.radians([lat,lon])
        centre=np.array([np.cos(la)*np.cos(lo),np.sin(la),np.cos(la)*np.sin(lo)])
        points=cp.window(centre,2048.,48)
        a,b=[cp.elevation(cp.Ctx(cell),points,extra=True) for cell in (2.,16.)]
        assert np.isfinite(a['surface']).all() and np.all(a['surface']>=a['elev'])
        wet=a['water_depth'].reshape(48,48)>.1
        assert wet.sum()>50, (kind,lat,lon,'water missing')
        s=a['surface'].reshape(48,48)
        jumps=np.concatenate((abs(np.diff(s,axis=0))[wet[:-1]&wet[1:]],
                              abs(np.diff(s,axis=1))[wet[:,:-1]&wet[:,1:]]))
        jump=float(jumps.max(initial=0.))
        change=float(abs(a['surface']-b['surface']).max())
        assert jump<1., (kind,lat,lon,'water seam',jump)
        assert change<3., (kind,lat,lon,'approach change',change)
        result.append(dict(kind=kind,lat=lat,lon=lon,max_wet_step_m=jump,max_lod_change_m=change))
    return result


if __name__=='__main__':
    print(json.dumps(dict(profiles=profiles(),network=network(),envelopes=envelopes(),
                         basin_connections=basin_connections(),terrain=terrain()),indent=2))
