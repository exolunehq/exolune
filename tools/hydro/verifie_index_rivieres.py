"""Verify the native activity index, not performance.

MYPLANETENGINE_EROSION_ACTIVITY_DUMP=<file> exports its exact eligibility and masks.
The CPU predicate is independent of the GPU's course construction. Search tests
preserve the original candidate multiset, including remapped cube-face edges.
"""
import argparse
from collections import Counter
from pathlib import Path

import numpy as np

import cp


def predicate(words, n):
    cells = np.arange(6 * n * n)
    bits = words[0, :, 1].astype(np.int64)
    graph = (bits >> 16) & 255
    flow = words[3, :, 0].astype(np.int64)
    code, outgoing = flow & 255, (flow >> 8) & 255
    outlet = (bits & (cp._SEA | cp._LAKE)) != 0
    down = cp._eneighbour(cells, bits & 7, n)
    down = np.where(outlet, cells, down)
    twice = 16 * (np.log2(cp.RIVER_Q[0]) + 8)
    active = (outlet | ((bits & cp._HAS_RECEIVER) != 0)) & (2 * (np.maximum(graph, graph[down]) + 1) >= twice)
    inflow = np.zeros(len(cells), dtype=bool)
    top_graph = graph.copy()
    top_outgoing = outgoing.copy()
    connector = np.zeros(len(cells), dtype=bool)
    stopped = (words[2, :, 1] & 65535) < 65535
    for side in range(8):
        present = ((bits >> (side + 4)) & 1) != 0
        upstream = cp._eneighbour(cells, np.full(len(cells), side), n)
        connector |= present & (outgoing[upstream] + np.where(stopped[upstream], outgoing[upstream], code) >= twice)
        largest = present & (~inflow | (graph[upstream] > top_graph))
        top_graph = np.where(largest, graph[upstream], top_graph)
        top_outgoing = np.where(largest, outgoing[upstream], top_outgoing)
        inflow |= present
    active &= ~outlet | inflow
    active &= (code + np.where((flow & 65536) != 0, code, code[down]) >= twice) | (inflow & (2 * top_outgoing >= twice)) | connector
    return active


def select(mask, rank):
    low, high = int(mask[0]), int(mask[1])
    first = low.bit_count()
    word, index, rank = (low, 0, rank) if rank < first else (high, 32, rank - first)
    for half in (16, 8, 4, 2, 1):
        lower = word & ((1 << half) - 1)
        count = lower.bit_count()
        if rank >= count:
            rank -= count
            word >>= half
            index += half
        else:
            word = lower
    return index


def verify(cache, dump):
    raw = np.frombuffer(Path(dump).read_bytes(), dtype='<u4')
    n = int(raw[0])
    cells = 6 * n * n
    assert raw.size == 1 + 4 * cells
    flags = raw[1:1 + 2 * cells].reshape(cells, 2)
    tiles = raw[1 + 2 * cells:].reshape(6, n, n, 2)
    words = np.frombuffer(Path(cache).read_bytes()[24:], dtype='<u4').reshape(4, cells, 2)
    expected = predicate(words, n)
    assert np.array_equal(flags[:, 0], expected), np.flatnonzero(flags[:, 0] != expected)[:20]
    assert tiles[0, -1, -1, 0] in (0x45524932, 0x45524933)
    if tiles[0, -1, -1, 0] == 0x45524932:
        assert not flags[:, 1].any()
    else:
        bounds = flags[:, 1].copy().view('<f4')
        assert np.isfinite(bounds).all() and (bounds[expected] > 0.).all()
    halo = 3 * n // 8
    # Check the entire halo against an independently remapped source chart, in bounded batches.
    side = 7 * n // 8
    bits = np.arange(64)
    halo_count = 0
    for face in range(6):
        for first in range(0, side, 16):
            tx, ty, bit = np.meshgrid(np.arange(side), np.arange(first, min(first + 16, side)), bits, indexing='xy')
            ij = np.column_stack(((tx * 8 + bit % 8 - 3 * n).ravel(), (ty * 8 + bit // 8 - 3 * n).ravel()))
            ids = cp._ecell(np.full(len(ij), face), ij, n)
            words_at = tiles[face, ty, tx, bit // 32]
            observed = ((words_at >> (bit % 32)) & 1).ravel() != 0
            assert np.array_equal(observed, expected[ids]), (face, first, int(np.count_nonzero(observed != expected[ids])))
            halo_count += len(ids)
    print(f'All {halo_count:,} native chart/halo mask bits match independent remapping.', flush=True)
    decoded = np.zeros(cells, dtype=bool)
    for face in range(6):
        for ty in range(n // 8):
            for tx in range(n // 8):
                mask = tiles[face, ty + halo, tx + halo]
                packed = int(mask[0]) | (int(mask[1]) << 32)
                bits = [i for i in range(64) if (packed >> i) & 1]
                actual = [select(mask, i) for i in range(packed.bit_count())]
                assert actual == bits
                for bit in bits:
                    decoded[(face * n + ty * 8 + bit // 8) * n + tx * 8 + bit % 8] = True
    assert np.array_equal(decoded, expected)
    print(f'All {cells:,} native node predicates and mask bits match; {expected.sum():,} active nodes.', flush=True)
    rng = np.random.default_rng(4158)
    seam = 0
    for i in range(1800):
        face = i % 6
        origin = rng.integers(-60, n + 20, size=2)
        count = rng.integers(1, 100, size=2)
        x, y = np.meshgrid(np.arange(origin[0], origin[0] + count[0]), np.arange(origin[1], origin[1] + count[1]))
        ij = np.column_stack((x.ravel(), y.ravel()))
        ids = cp._ecell(np.full(len(ij), face), ij, n)
        original = ids[expected[ids]]
        sparse = count.prod() > 64 and (origin >= -3 * n).all() and (origin + count <= 4 * n).all()
        seam += int((origin < 0).any() or (origin + count > n).any())
        if sparse:
            found = []
            begin, end = origin // 8, (origin + count + 7) // 8
            for ty in range(begin[1], end[1]):
                for tx in range(begin[0], end[0]):
                    mask = tiles[face, ty + halo, tx + halo]
                    for rank in range(int(mask[0]).bit_count() + int(mask[1]).bit_count()):
                        bit = select(mask, rank)
                        xy = np.array([tx * 8 + bit % 8, ty * 8 + bit // 8])
                        if (xy >= origin).all() and (xy < origin + count).all():
                            found.append(xy)
            positions = np.array(found, dtype=np.int64).reshape(-1, 2)
            found = cp._ecell(np.full(len(positions), face), positions, n)
        else:
            found = ids[decoded[ids]]
        assert Counter(original) == Counter(found), (face, origin, count)
    print(f'1,800 searches preserve all active candidates and duplicates, including {seam} face-edge searches.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cache')
    p.add_argument('dump')
    a = p.parse_args()
    verify(a.cache, a.dump)
