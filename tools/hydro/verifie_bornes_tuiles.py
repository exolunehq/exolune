"""Check the queue's conservative chart-tile sphere against every remapped node.

Normalization on a cube-chart plane is 1/min(length) Lipschitz. Adding the
physical-cell rounding and bounded jitter covers the actual ErosionNode. The
triangle inequality then retains every node accepted by the original chord gate,
for any query position and footprint. This is correctness, not a timing benchmark.
"""
import numpy as np

import cp


def verify(n):
    width, halo = 7*n//8, 3*n//8
    nodes = cp._enode(np.arange(6*n*n), n)
    bits = np.arange(64)
    offset = np.column_stack((bits % 8, bits // 8))
    tested, largest_ratio = 0, 0.
    for start in range(0, 6*width*width, 2048):
        index = np.arange(start, min(start+2048, 6*width*width))
        face = index//(width*width)
        tile = np.column_stack((index % width, index//width % width))-halo
        st = (tile.astype(np.float32)*8+4)*(np.float32(2.)/n)-1
        raw = cp._edirection(face, st[:, 0], st[:, 1])
        length = np.linalg.norm(raw, axis=1)
        centre = raw/length[:, None]
        raw_radius = np.float32(7*np.sqrt(2.)/n)
        span = raw_radius/np.maximum(1., length-raw_radius)
        span += np.float32(2*np.sqrt(2.)*(.5+cp.EROSION_JITTER)/n)
        span += np.float32(64*np.finfo(np.float32).eps)
        ij = (tile[:, None]*8+offset[None]).reshape(-1, 2)
        ids = cp._ecell(np.repeat(face, 64), ij, n)
        actual = nodes[ids].reshape(-1, 64, 3)
        distances = np.linalg.norm(actual-centre[:, None], axis=2)
        ratio = distances.max(axis=1)/span
        assert (ratio <= 1.).all(), (n, tile[np.argmax(ratio)], ratio.max())
        largest_ratio = max(largest_ratio, float(ratio.max()))
        tested += len(ids)
    print(f'n={n}: {tested:,} chart nodes enclosed, maximum bound utilization {largest_ratio:.6f}.', flush=True)


if __name__ == '__main__':
    for n in (8, 64, 512):
        verify(n)
