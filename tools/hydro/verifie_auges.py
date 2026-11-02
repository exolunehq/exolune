"""Contrôle des auges et raccords, sans fenêtre ; depuis la racine du worktree.

python tools/hydro/verifie_auges.py --out x64/erosion-2026-11-01/geometrie.json
The reference is the public-history replay, 7c9f475; both versions use the same caches.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import cp
from verifie_erosion_roche import reference, oval_center, stats
from verifie_pentes_ravines import cliffs, PLACES
from verifie_fonds_vallees import flood


def sample(model, p, cell):
    state = {}
    original = model.erosion_carve
    def capture(h, coarse, v, k):
        state.update(coarse=coarse, **v)
        return original(h, coarse, v, k)
    model.erosion_carve = capture
    try:
        z = model.elevation(model.Ctx(cell), p)
    finally:
        model.erosion_carve = original
    return z, state


def warp(p):
    w = cp.turbulence(cp.Ctx(5.), p, cp.R_KM/cp.EROSION_WARP[0],
                      cp.EROSION_WARP[1]/(cp.SIGMA*cp.R_KM), 2, cp._rseed(9))
    return w/np.linalg.norm(w,axis=1,keepdims=True)


def unwarp(target):
    """Inverse de la direction, uniquement pour placer les sondes du contrôle."""
    target = target/np.linalg.norm(target,axis=1,keepdims=True)
    p = target.copy()
    for _ in range(18):
        w = warp(p)
        east = np.cross(p,[0.,1.,0.]); east /= np.linalg.norm(east,axis=1,keepdims=True)
        north = np.cross(east,p)
        te = np.cross(target,[0.,1.,0.]); te /= np.linalg.norm(te,axis=1,keepdims=True)
        tn = np.cross(te,target)
        we = warp(cp.move(p,east,np.ones(len(p))))-w
        wn = warp(cp.move(p,north,np.ones(len(p))))-w
        error = target-w
        j11,j12 = (we*te).sum(1),(wn*te).sum(1)
        j21,j22 = (we*tn).sum(1),(wn*tn).sum(1)
        e1,e2 = (error*te).sum(1),(error*tn).sum(1)
        determinant = j11*j22-j12*j21
        de,dn = (e1*j22-e2*j12)/determinant,(e2*j11-e1*j21)/determinant
        scale = np.minimum(1.,2000./np.maximum(np.hypot(de,dn),1e-20))
        p += ((de*scale)[:,None]*east+(dn*scale)[:,None]*north)/cp.R
        p /= np.linalg.norm(p,axis=1,keepdims=True)
    residual = np.linalg.norm(warp(p)-target,axis=1)*cp.R
    assert residual.max() < .01, f'inversion du gauchissement : {residual.max()} m'
    return p


def profiles(old):
    rows = []
    for ice in (1e7,1e8,1e9):
        row = dict(ice=ice)
        d = np.arange(0.,5000.25,.25)
        for name,m in (('avant',old),('apres',cp)):
            s,f,g,r = m._erosion_profile(d,1500.,100.,ice,.02,.65,10000.,2.,4000.)
            z = m.erosion_carve(np.full_like(d,11500.),np.full_like(d,11500.),
                                dict(surface=s,level=np.full_like(d,1500.),floor=f),60.)
            row[name+'_largeur_plate_m'] = float(.5*np.sum(abs(z-1500.)<.1))
            if name == 'apres':
                assert np.all(np.diff(z)>=-1e-8), 'le U remonte puis redescend transversalement'
                assert z.min()>=1500., 'le profil passe sous son fond drainé'
                curvature = cp.EROSION_GLACIER[2]/np.clip(cp.EROSION_GLACIER[0]*(ice/1e8)**cp.EROSION_GLACIER[1],150.,1500.)
                assert abs(z[0]-1500.-curvature*cp.CREASE_MIN_CELL**2/3.)<1e-8
                assert np.max(abs(np.gradient(s,.25)[2:-2]-r[2:-2]))<1e-4
                assert row[name+'_largeur_plate_m']<50., 'le fond est encore un large aplat'
        rows.append(row)
    # Le raccord au sol ne doit ni creuser sous le profil ni modifier le sol hors creusement.
    ground = np.linspace(-100.,100.,10001)
    cut = cp.erosion_cut(ground,np.zeros_like(ground),60.)
    assert np.all(cut>=np.minimum(ground,0.)) and np.all(cut<=ground)
    assert np.array_equal(cut[ground<=0.],ground[ground<=0.])
    # Quieting a hollow's detail must never fill it or create an artificial rim.
    rng = np.random.default_rng(93)
    coarse = rng.uniform(0.,5000.,10000)
    h = coarse+rng.uniform(-1000.,1000.,len(coarse))
    v = dict(surface=coarse+rng.uniform(-1500.,1000.,len(coarse)),floor=rng.random(len(coarse)))
    cut = cp.erosion_carve(h,coarse,v,60.)
    target = v['surface']+(h-coarse)*(1.-v['floor'])
    assert np.all(cut<=h+1e-9) and np.all(cut>=np.minimum(h,target)-1e-9), 'le creusement relève un creux'
    return rows


def curves():
    # Oracle indépendant : toutes les racines du polynôme de stationnarité de la distance.
    rng = np.random.default_rng(41)
    b = rng.uniform(-1.,1.,(500,3)); b[:,2] = 0.
    a,c = b+rng.uniform(-1.,1.,b.shape),b+rng.uniform(-1.,1.,b.shape)
    a[:,2] = c[:,2] = 0.
    distances,_,_ = cp._curve(a,b,c)
    error = []
    for i in range(len(a)):
        d,e = b[i]-a[i],a[i]-2.*b[i]+c[i]
        roots = np.roots([2.*np.dot(e,e),6.*np.dot(d,e),
                         4.*np.dot(d,d)+2.*np.dot(a[i],e),2.*np.dot(a[i],d)])
        ts = [0.,1.]+[x.real for x in roots if abs(x.imag)<1e-8 and 0.<x.real<1.]
        exact = min(np.linalg.norm(a[i]+2.*d*t+e*t*t) for t in ts)
        error.append(abs(distances[i]-exact))
    assert max(error)<1e-8
    # Distance alone misses a wrong parameter beside a head: it moves the interpolated ice and height by metres.
    u = np.r_[np.linspace(-.01,.01,201),np.linspace(.99,1.01,201)]
    a = np.column_stack([-u,np.full(len(u),.5),np.zeros(len(u))])
    c = a+[1.,0.,0.]
    parameter_error = 0.
    for b,expected in ((a,np.sqrt(np.clip(u,0.,1.))),(c,1.-np.sqrt(1.-np.clip(u,0.,1.)))):
        distance,t,point = cp._curve(a,b,c)
        parameter_error = max(parameter_error,float(np.max(abs(t-expected))))
    assert parameter_error<1e-12, 'le paramètre saute près des sources ou exutoires'
    return dict(courbes=500,erreur_max=max(error),extremites=2*len(u),erreur_parametre_max=parameter_error)


def filtering():
    """Check the local mean against independent quadrature, including zero reference depth.

    The former area-preserving dilation passed positive-depth sections but moved the
    unbounded banks by hundreds of metres when reference depth approached zero.
    """
    from verifie_filtre_vallees import profiles as averaged_profiles
    return averaged_profiles()


def parent_independence():
    """Le réseau ne modifie pas le relief qu'il est chargé de creuser, plis et octaves grossières compris."""
    rows = []
    original, original_cut, saved_seed = cp.detail, cp.erosion_carve, cp.PLANET_SEED
    captured = {}
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        if len(args)>15 and args[4]==cp.RELIEF_DETAIL_TOP and args[9]==cp._rseed(1):
            captured['detail'] = args[6]*args[15][0]
        return result
    cp.detail = capture
    def capture_cut(h,coarse,v,k):
        captured.update(before_cut=h.copy(),uncut=coarse<=v['surface'])
        return original_cut(h,coarse,v,k)
    cp.erosion_carve = capture_cut
    try:
        for seed in (0,1):
            cp.PLANET_SEED = seed
            p = np.random.default_rng(541+seed).normal(size=(2000,3))
            p /= np.linalg.norm(p,axis=1,keepdims=True)
            p = np.vstack([p,*[cliffs.direction(lat,lon) for lat,lon in PLACES]])
            parents = []
            for enabled in (False,True):
                ground = cp._relief_ground(cp.Ctx(1.),p,enabled)
                parents.append(ground['large']+captured['detail'])
                if not enabled:
                    plain = ground['elev'].copy()
            error = float(np.max(abs(parents[0]-parents[1])))
            assert np.array_equal(*parents), f'le réseau modifie encore son support : {error} m'
            uncut = captured['uncut']
            detail_error = float(np.max(abs(plain[uncut]-captured['before_cut'][uncut])))
            assert detail_error<1e-9, f'détail modifié hors incision : {detail_error} m'
            rows.append(dict(graine=seed,sondes=len(p),ecart_max_m=error,hors_incision=int(uncut.sum()),
                             ecart_detail_hors_incision_m=detail_error))
    finally:
        cp.detail,cp.erosion_carve,cp.PLANET_SEED = original,original_cut,saved_seed
    print('support indépendant',rows,flush=True)
    return rows


def soils(old):
    rows = []
    for lat,lon in PLACES[:4]:
        p = cp.window(cliffs.direction(lat,lon)[0],101.,101)
        before = old.elevation(old.Ctx(1.),p)
        after = cp.elevation(cp.Ctx(1.),p)
        a,b = stats(before,101,1.),stats(after,101,1.)
        # Le déplacement du réseau peut changer la pente locale ; le sol mobile garde son seuil physique.
        assert b[3]<=np.degrees(np.arctan(cp.EROSION_GULLY_CRITICAL)), f'paroi dans le manteau : {(lat,lon)}, {b}'
        assert np.array_equal(after,cp.elevation(cp.Ctx(.25),p)), 'le sol résolu dépend de la maille'
        assert np.array_equal(cp.elevation(cp.Ctx(1.),p,valleys=False),
                              old.elevation(old.Ctx(1.),p,valleys=False))
        rows.append(dict(lat=lat,lon=lon,avant=a,apres=b))
        print('sol',rows[-1],flush=True)
    return rows


def trough_windows(old):
    rows = []
    for i in (0,1):
        p = cp.window(oval_center(i),4025.,161)
        row = dict(fenetre=i)
        for name,m in (('avant',old),('apres',cp)):
            z,v = sample(m,p,5.)
            closed = flood(z.reshape(161,161)).ravel()-z
            flat = (v['coarse']-z>60.) & (abs(z-v['level'])<.1)
            row[name] = dict(plat_pct=100.*flat.mean(),cuvette_p99=float(np.percentile(closed,99)),
                             cuvette_max=float(closed.max()))
        assert row['apres']['plat_pct']<.1*row['avant']['plat_pct']
        rows.append(row)
        print('auge',row,flush=True)
    return rows


def joins(seed):
    cp.PLANET_SEED = seed
    words,n = cp.erosion_map()
    ids = np.arange(len(words)); level,ground,flow,ice,bits = cp._eread(words,ids)
    candidates = ids[((bits & cp._HAS_RECEIVER)!=0) & ((bits & (cp._SEA|cp._LAKE))==0)
                     & (ground-level>200.) & (ice>1e7)]
    rng = np.random.default_rng(17+seed)
    ids = rng.choice(candidates,min(100,len(candidates)),replace=False)
    receiver = cp._eneighbour(ids,bits[ids]&7,n)
    a,b = cp._enode(ids,n).astype(float),cp._enode(receiver,n).astype(float)
    mid = .5*(a+b); mid /= np.linalg.norm(mid,axis=1,keepdims=True)
    tangent = b-a; tangent -= mid*(tangent*mid).sum(1)[:,None]
    tangent /= np.linalg.norm(tangent,axis=1,keepdims=True)
    changes = []
    for epsilon in (.01,.1):
        minus = cp.move(mid,tangent,np.full(len(mid),-epsilon))
        plus = cp.move(mid,tangent,np.full(len(mid),epsilon))
        vl,vr = [cp.erosion_valleys(p,.001,.65) for p in (minus,plus)]
        changes.append(abs(vl['surface']-vr['surface']))
    excess = changes[0]-.2*changes[1]
    assert excess.max()<.01, f'saut de profil aux raccords de la graine {seed}: {excess.max()} m'
    # Des traces de 5 km dans trois régions indépendantes, sur les vraies courbes sphériques.
    traces = []
    chosen = []
    for r in ids:
        if any(np.linalg.norm(cp._enode(np.array([r]),n)[0]-x)<.1 for x in chosen):
            continue
        inflows = int(bits[r]>>4)&255
        if not inflows:
            continue
        k = (inflows & -inflows).bit_length()-1
        u = int(cp._eneighbour(np.array([r]),np.array([k]),n)[0])
        down = int(cp._eneighbour(np.array([r]),np.array([bits[r]&7]),n)[0])
        node = cp._enode(np.array([r]),n)[0].astype(float)
        a = .5*(cp._enode(np.array([u]),n)[0]+node)
        c = .5*(cp._enode(np.array([down]),n)[0]+node)
        t = np.linspace(0.,1.,257)[:,None]
        targets = (1.-t)**2*a+2.*t*(1.-t)*node+t*t*c
        p = unwarp(targets)
        length = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1)*cp.R)]
        z,v = sample(cp,p,5.)
        active = (v['coarse']-v['surface']>60.) & (v['floor']>.999)
        if active.sum()<20:
            continue
        error = abs(z[active]-v['surface'][active])
        # At an overlap the lower valley can win off its own axis: its profile, not an unrelated water level, applies.
        assert error.max()<.1, f'détail sur le fond creusé : graine {seed}, {r}, {error.max()} m'
        traces.append(dict(noeud=int(r),longueur_m=float(length[-1]),sondes=int(active.sum()),
                           ecart_profil_max_m=float(error.max()),
                           ecart_eau_max_m=float(abs(z[active]-v['level'][active]).max())))
        chosen.append(node)
        if len(traces)==3:
            break
    assert len(traces)==3, 'moins de trois régions glaciaires vérifiées'
    row = dict(graine=seed,raccords=len(ids),saut_residuel_max_m=float(excess.max()),thalwegs=traces)
    print('réseau',row,flush=True)
    return row


def jacobians():
    """La déformation doit conserver l'orientation locale, sur deux échantillons planétaires fixes."""
    rows = []
    saved_seed,saved_warp = cp.PLANET_SEED,cp.EROSION_WARP
    try:
        for seed in (0,1):
            cp.PLANET_SEED = seed
            p = np.random.default_rng(300+seed).normal(size=(100000,3))
            p /= np.linalg.norm(p,axis=1,keepdims=True)
            east = np.cross(p,[0.,1.,0.]); east /= np.linalg.norm(east,axis=1,keepdims=True)
            north = np.cross(east,p)
            for amplitude in (7.,saved_warp[1]):
                cp.EROSION_WARP = (saved_warp[0],amplitude)
                w = warp(p)
                we = (warp(cp.move(p,east,np.ones(len(p))))-w)*cp.R
                wn = (warp(cp.move(p,north,np.ones(len(p))))-w)*cp.R
                te = np.cross(w,[0.,1.,0.]); te /= np.linalg.norm(te,axis=1,keepdims=True)
                tn = np.cross(te,w)
                det = (we*te).sum(1)*(wn*tn).sum(1)-(we*tn).sum(1)*(wn*te).sum(1)
                rows.append(dict(graine=seed,amplitude_km=amplitude,sondes=len(p),
                                 determinant_min=float(det.min()),replis_pct=float(100.*np.mean(det<0.))))
                if amplitude == saved_warp[1]:
                    assert det.min()>0., 'le gauchissement replie encore le réseau'
    finally:
        cp.PLANET_SEED,cp.EROSION_WARP = saved_seed,saved_warp
    return rows


def boundaries(seed):
    """Traverser les changements de face et de fenêtre de lecture, au-delà de leur quantification float32."""
    cp.PLANET_SEED = seed
    points,directions = [],[]
    for i,j in ((0,1),(0,2),(1,2)):
        k = 3-i-j
        for si in (-1.,1.):
            for sj in (-1.,1.):
                for value in np.linspace(-.95,.95,15):
                    p = np.zeros(3);p[i],p[j],p[k] = si,sj,value
                    p /= np.linalg.norm(p)
                    e = np.zeros(3);e[i],e[j] = si,-sj;e /= np.linalg.norm(e)
                    points.append(p);directions.append(e)
    _,n = cp.erosion_map()
    rng = np.random.default_rng(80+seed)
    f = rng.integers(0,6,240)
    x = (rng.integers(8,n-8,240)+.5)*2./n-1.
    y = rng.uniform(-.95,.95,240)
    p = cp._edirection(f,x,y).astype(float);p /= np.linalg.norm(p,axis=1,keepdims=True)
    e = cp._edirection(f,x+.001,y).astype(float)
    e -= p*(e*p).sum(1)[:,None];e /= np.linalg.norm(e,axis=1,keepdims=True)
    p = np.vstack([points,p]);e = np.vstack([directions,e])
    changes=[]
    for epsilon in (.5,5.):
        a,b=[cp.erosion_valleys(cp.move(p,e,np.full(len(p),sign*epsilon)),.001,.65) for sign in (-1.,1.)]
        active = np.minimum(a['surface'],b['surface'])<12000.
        changes.append({key:(np.linalg.norm(a[key]-b[key],axis=1) if key=='gradient' else abs(a[key]-b[key]))
                        for key in ('surface','gradient','floor','incision')})
    row=dict(graine=seed,frontieres=len(p),actives=int(active.sum()))
    for key,tolerance in (('surface',.05),('gradient',.001),('floor',.001),('incision',.05)):
        excess = np.maximum(changes[0][key]-.2*changes[1][key],0.)[active]
        row[key+'_saut_residuel_max'] = float(excess.max(initial=0.))
        assert row[key+'_saut_residuel_max']<tolerance, f'frontière : {row}'
    print('frontières',row,flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='x64/erosion-2026-11-01/geometrie.json')
    args = parser.parse_args()
    old = reference('7c9f475')
    report = dict(reference='7c9f475',profils=profiles(old),courbes=curves(),gauchissement=jacobians(),filtrage=filtering(),
                  support=parent_independence())
    report['sols'] = soils(old)
    report['auges'] = trough_windows(old)
    report['reseaux'] = [joins(seed) for seed in (0,1)]
    report['frontieres'] = [boundaries(seed) for seed in (0,1)]
    cp.PLANET_SEED = 0
    path = Path(args.out); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ok',path,flush=True)


if __name__ == '__main__':
    main()
