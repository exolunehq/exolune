"""Check the optimized section partition against a general sort; no GPU or timing.

The independent oracle sorts the original fourteen physical transitions and both
footprint ends. Compare positive intervals exactly, including inverted outer
walls, coincident transitions and footprints much wider than the whole valley.
"""
import numpy as np


def check():
    rng = np.random.default_rng(1105)
    count = 100_000
    floor = (10. ** rng.uniform(-2, 4.5, count)).astype('f4')
    outer = np.minimum(floor + 10. ** rng.uniform(-2, 4, count), 8500.).astype('f4')
    rounding = rng.uniform(.15, .5, count).astype('f4')
    along = rng.uniform(-1, 1, count).astype('f4') * outer
    bank = (10. ** rng.uniform(-2, 4, count)).astype('f4')
    keep = np.maximum(4 * bank, rng.uniform(0, 2, count) * floor).astype('f4')
    ratio = rng.uniform(2 ** -.5, 2 ** .5, count).astype('f4')
    radius = (10. ** rng.uniform(-3, 7, count)).astype('f4')
    lateral = rng.uniform(-1, 1, count).astype('f4') * (radius + outer)
    channel = lateral + rng.uniform(-3000, 3000, count).astype('f4')
    # Coincident transitions exercise zero intervals and both clipped ends.
    rounding[::9] = .5
    along[::11] = 0
    keep[::7] = 4 * bank[::7]
    wall = outer - floor
    boundaries = np.stack((floor, floor + rounding * wall, outer - rounding * wall, outer), axis=1)
    reach = np.sqrt(np.maximum(boundaries ** 2 - along[:, None] ** 2, 0))
    bank_reach = np.sqrt(np.maximum(np.stack((2 * bank, 4 * bank, keep), axis=1) ** 2 - along[:, None] ** 2, 0))
    unsorted = np.concatenate((-lateral[:, None] - reach, -lateral[:, None] + reach,
                              (-channel[:, None] - bank_reach) / ratio[:, None],
                              (-channel[:, None] + bank_reach) / ratio[:, None]), axis=1)
    oracle = np.sort(np.clip(np.column_stack((-radius, radius, unsorted)), -radius[:, None], radius[:, None]), axis=1)

    # Fixed four/three-element sorting networks used before the four-list merge.
    for a, b in ((0, 1), (2, 3), (0, 2), (1, 3), (1, 2)):
        reach[:, a], reach[:, b] = np.minimum(reach[:, a], reach[:, b]), np.maximum(reach[:, a], reach[:, b])
    for a, b in ((0, 1), (1, 2), (0, 1)):
        bank_reach[:, a], bank_reach[:, b] = np.minimum(bank_reach[:, a], bank_reach[:, b]), np.maximum(bank_reach[:, a], bank_reach[:, b])
    lists = [-lateral[:, None] - reach[:, ::-1], -lateral[:, None] + reach,
             (-channel[:, None] - bank_reach[:, ::-1]) / ratio[:, None],
             (-channel[:, None] + bank_reach) / ratio[:, None]]
    lists = [np.clip(values, -radius[:, None], radius[:, None]) for values in lists]
    positions = np.zeros((count, 4), dtype=int)
    rows = np.arange(count)
    lo = -radius
    visited = np.zeros(count, dtype=int)
    expected = np.sum(np.diff(oracle, axis=1) > 0, axis=1)
    for _ in range(15):
        heads = np.stack([values[rows, np.minimum(positions[:, k], values.shape[1]-1)]
                          for k, values in enumerate(lists)], axis=1)
        for k, values in enumerate(lists):
            heads[positions[:, k] >= values.shape[1], k] = radius[positions[:, k] >= values.shape[1]]
        hi = np.min(heads, axis=1)
        assert (hi >= lo).all()
        positive = hi > lo
        # Each positive interval must be adjacent in the general sixteen-boundary oracle.
        adjacent = ((oracle[:, :-1] == lo[:, None]) & (oracle[:, 1:] == hi[:, None])).any(axis=1)
        assert adjacent[positive].all()
        visited += positive
        positions += heads == hi[:, None]
        lo = hi
    assert np.array_equal(lo, radius)
    assert np.array_equal(visited, expected)
    print(f'{count:,} sections preserve every positive quadrature interval exactly; '
          f'{np.count_nonzero(floor > outer):,} include an inverted capped wall.')


if __name__ == '__main__':
    check()
