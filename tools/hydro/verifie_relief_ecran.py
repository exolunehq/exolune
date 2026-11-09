"""Compare native screen-relief field captures; correctness only, no timing benchmark.

Set MYPLANETENGINE_SCREEN_DUMP=1 with a native capture to write <image>.screen.
The file contains uint32 width/height/stride, then 16 float32 fields per texel.
"""
import argparse
from pathlib import Path

import numpy as np


def read(path):
    with Path(path).open('rb') as stream:
        shape = np.fromfile(stream, dtype='<u4', count=3)
        values = np.fromfile(stream, dtype='<f4')
    assert len(shape) == 3 and shape[2] == 16, (path, shape)
    assert values.size == int(np.prod(shape)), (path, shape, values.size)
    return values.reshape(int(shape[1]), int(shape[0]), 16)


def compare(reference, actual):
    expected, observed = read(reference), read(actual)
    assert expected.shape == observed.shape
    assert np.array_equal(np.isnan(expected), np.isnan(observed)), 'Ray-hit masks or NaN fields differ.'
    assert not np.isinf(expected).any() and not np.isinf(observed).any()
    valid = np.isfinite(expected[..., 3])
    assert valid.any(), 'No terrain rays exercised.'
    a, b = expected[valid].astype(float), observed[valid].astype(float)
    # Float reconstruction tolerances; position is camera-relative in metres.
    # Wet coverage, premultiplied water moments and flow have their own tight bounds.
    names = ('position', 'elevation', 'coverage', 'stage moment', 'depth moment', 'distance', 'flow', 'ground')
    groups = ((slice(0, 3), 0.02, 2e-6), (3, 0.02, 2e-6), (4, 2e-5, 2e-6),
              (5, 0.02, 2e-6), (6, 0.002, 2e-6), (7, 0.05, 2e-6),
              (slice(8, 12), 2e-5, 2e-6), (slice(12, 16), 2e-5, 2e-6))
    failures = []
    for name, (field, absolute, relative) in zip(names, groups):
        delta = np.abs(a[:, field] - b[:, field])
        limit = absolute + relative * np.abs(a[:, field])
        outside = int(np.count_nonzero(delta > limit))
        print(f'{name}: max difference {delta.max():.9g}, outside tolerance {outside}')
        if outside:
            failures.append(name)
    assert not failures, ', '.join(failures)
    print(f'PASS: {valid.sum()} terrain rays, {expected.shape[0]*expected.shape[1]} screen texels.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    parser.add_argument('actual')
    args = parser.parse_args()
    compare(args.reference, args.actual)
