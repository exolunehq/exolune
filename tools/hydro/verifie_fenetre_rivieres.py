"""Verify spherical-cap chart pruning against the original remapped-node gate.

The CPU reference keeps the original search and tests actual jittered nodes.
The new window must contain every node that the former distance gate accepts.
This is correctness validation, not a performance benchmark.
"""
import numpy as np

import cp


def clipped(p, x, n, radius, origin, count):
    f = np.float32
    normal = f(np.abs(p.astype(f)).max())
    chord = f((1.15*(2*cp.R/n)+cp.RIVER_EXTEND[0]+16000+radius)/cp.R)
    chord += f(2*np.sqrt(2)*(.5+cp.EROSION_JITTER)/n+64*np.finfo(f).eps)
    if chord >= f(np.sqrt(2)):
        return origin, count
    sine2 = f(chord*chord*(f(1)-f(.25)*chord*chord))
    divisor = f(normal*normal-sine2)
    if divisor <= f(1e-5):
        return origin, count
    axis = ((x.astype(f)+f(.5))*f(2/n)-f(1))*normal
    spread = np.sqrt(np.maximum(sine2*(normal*normal+axis*axis-sine2), f(0)))
    low = ((axis*normal-spread)/divisor+f(1))*f(.5*n)-f(.5)
    high = ((axis*normal+spread)/divisor+f(1))*f(.5*n)-f(.5)
    end = np.minimum(origin+count, np.ceil(np.minimum(high+1, origin+count)).astype(int)+1)
    begin = np.maximum(origin, np.floor(np.maximum(low-1, origin)).astype(int)-1)
    return begin, np.maximum(end-begin, 0)


def verify():
    n = 512
    nodes = cp._enode(np.arange(6*n*n), n).astype(np.float64)
    samples = []
    for face in range(6):
        for st in ((0., 0.), (.97, .91), (.6, -.9), (1., 1.)):
            raw = cp._edirection(np.array([face]), np.array([st[0]]), np.array([st[1]]))[0].astype(float)
            samples.append(raw/np.linalg.norm(raw))
    checked = removed = kept = 0
    for p in samples:
        faces, xx = cp._elocate(p[None], n)
        face, x = faces[0], xx[0]
        for radius in (2., 20000., 200000., 2000000., 4000000.):
            reach = cp._river_footprint_reach(p[None], xx, n, radius)[0]
            origin = np.floor(x-reach).astype(int)-1
            count = np.floor(x+reach).astype(int)+3-origin
            begin, size = clipped(p, x, n, radius, origin, count)
            assert (begin >= origin).all() and (begin+size <= origin+count).all()
            old_gate = 1.15*(2*cp.R/n)+cp.RIVER_EXTEND[0]+16000+radius
            for start in range(0, int(count.prod()), 131072):
                k = np.arange(start, min(start+131072, int(count.prod())))
                ij = origin+np.column_stack((k % count[0], k//count[0]))
                outside = ((ij < begin) | (ij >= begin+size)).any(axis=1)
                candidates = ij[outside]
                ids = cp._ecell(np.full(len(candidates), face), candidates, n)
                distance = np.linalg.norm(nodes[ids]-p, axis=1)*cp.R
                assert not (distance <= old_gate).any(), (p, radius, candidates[distance <= old_gate][:4])
                checked += len(ij)
                removed += len(candidates)
                kept += len(ij)-len(candidates)
    print(f'{len(samples)*5} face/interior/seam/corner/footprint cases: {checked:,} chart candidates checked.')
    print(f'{removed:,} rejected candidates fail the original node gate; {kept:,} retained. No contributing node lost.')


if __name__ == '__main__':
    verify()
