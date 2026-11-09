"""Check course bounds against the original projected curve/triangle gates.

Native bounds are optional: pass an ERI3 activity dump. No rendering or timing.
"""
import argparse
from pathlib import Path
import numpy as np
import cp


def bound(v):
    centre = v['r']['at']
    def course(k):
        a, b, c = k['xyz'] - centre
        return (max(np.linalg.norm(a), np.linalg.norm(c))
                + .5*np.linalg.norm(b-.5*(a+c)))*cp.R + cp._course_reach(k)
    result = course(v['main'])
    if v['head']:
        result = max(result, course(cp._head_course(v)))
    if v['outlet']:
        result = max(result, course(cp._outlet_course(v)))
    for side in range(8):
        if not (v['connectors'] & (1 << side)): continue
        _, n = cp.erosion_map()
        node = int(cp._eneighbour(np.array([v['r']['c']]), np.array([side]), n)[0])
        start = .5*(cp._river_node(node)['at']-centre)
        extent = max(np.linalg.norm(start), np.linalg.norm(v['main']['xyz']-centre, axis=1).max())
        result = max(result, extent*cp.R+2.*cp._course_reach(v['main']))
    return result


def verify(dump):
    rng = np.random.default_rng(51105)
    words, n = cp.erosion_map()
    from verifie_index_rivieres import predicate
    words = np.frombuffer(Path(cp.EROSION_CACHE.format(seed=cp.PLANET_SEED)).read_bytes()[24:], dtype='<u4').reshape(4, -1, 2)
    ids = np.flatnonzero(predicate(words, n))
    selected = rng.choice(ids, min(1200, len(ids)), replace=False)
    native = None
    if dump:
        raw = np.frombuffer(Path(dump).read_bytes(), dtype='<u4')
        assert raw[0] == n
        native = raw[1:1+12*n*n].reshape(-1, 2)[:, 1].copy().view('<f4')
    checked = 0
    for node in selected:
        v = cp._node_courses(int(node))
        exact = bound(v)
        radius = exact + 64.*cp.R*np.finfo(np.float32).eps
        if native is not None:
            assert np.isfinite(native[node]) and native[node] >= exact, (node, native[node], exact)
            radius = native[node]
        centre = v['r']['at']
        points = cp.window(centre, 120000., 12)
        d = centre-points
        projected = d - (d*points).sum(1)[:, None]*points
        dist = np.linalg.norm(projected, axis=1)*cp.R
        courses = [v['main']]
        if v['head']: courses.append(cp._head_course(v))
        if v['outlet']: courses.append(cp._outlet_course(v))
        for footprint in (2., 1000., 20000., 200000.):
            rejected = dist > radius+footprint
            for k in courses:
                q = k['xyz'][None]-points[:, None]
                q -= (q*points[:, None]).sum(2)[..., None]*points[:, None]
                a,b,c = q[:, 0],q[:, 1],q[:, 2]
                e = c-a
                t = np.clip(-(a*e).sum(1)/np.maximum((e*e).sum(1), 1e-30), 0., 1.)
                gate = (np.linalg.norm(a+t[:, None]*e, axis=1)-.5*np.linalg.norm(b-.5*(a+c), axis=1))*cp.R
                assert not (rejected & (gate <= cp._course_reach(k)+footprint)).any(), (node, footprint)
                checked += len(points)
            for side in range(8):
                if not (v['connectors'] & (1 << side)): continue
                upstream = int(cp._eneighbour(np.array([node]), np.array([side]), n)[0])
                u = cp._river_node(upstream)
                start = .5*(u['at']+centre)
                t = cp._junction(v['main'], .5*(u['stage']+v['r']['stage']))
                controls = v['main']['xyz']
                junction = (1.-t)**2*controls[0]+2.*t*(1.-t)*controls[1]+t*t*controls[2]
                triangle = np.stack([start, centre, junction])[None]-points[:, None]
                triangle -= (triangle*points[:, None]).sum(2)[..., None]*points[:, None]
                gate = cp._triangle_distance(triangle[:, 0],triangle[:, 1],triangle[:, 2],points)*cp.R
                assert not (rejected & (gate <= 2.*cp._course_reach(v['main'])+footprint)).any(), (node,side,footprint)
                checked += len(points)
    print(f'{len(selected)} planetary nodes, {checked:,} projected course gates retain every original candidate.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', nargs='?')
    verify(p.parse_args().dump)
