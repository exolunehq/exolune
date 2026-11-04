"""First-water cache, runoff conservation and physical termination checks. No benchmark."""
import argparse
from pathlib import Path
import numpy as np

import cp


def stop_filter():
    course = dict(xyz=np.array([[1., 0., 0.], [1., 5000./cp.R, 0.], [1., 10000./cp.R, 0.]]),
                  stops=np.array([.4, .4]), split=False)
    for radius in (2., 20., 500., 4000.):
        x = np.linspace(4000.-radius-90., 4000.+radius+170., 101)
        actual = cp.river_stop_share(course, x/10000., np.zeros(len(x)), radius)
        samples = x[:, None]+np.linspace(-radius, radius, 32769)
        physical = 1.-cp._smooth(0., cp.RIVER_CONTACT[2], samples-4000.)
        expected = np.trapezoid(physical, dx=2.*radius/(physical.shape[1]-1), axis=1)/(2.*radius)
        assert np.max(np.abs(actual-expected)) < 2e-6
        assert np.all(np.diff(actual) <= 1e-12), 'A course must not restart after its first contact.'
        assert actual[0] == 1. and actual[-1] == 0.
    print('Termination: four footprints agree with independent quadrature; no downstream restart.')


def runoff():
    words, n = cp.erosion_map()
    assert cp._magic[cp.PLANET_SEED] == b'EXOEROS6', 'Run the current Release engine once to prepare its contact cache.'
    data = cp._flow_words[cp.PLANET_SEED]
    N = len(words)
    has = (words[:, 1]&cp._HAS_RECEIVER) != 0
    cells = np.flatnonzero(has)
    receiver = np.full(N, -1, np.int64)
    receiver[cells] = cp._eneighbour(cells, (words[cells, 1]&7).astype(np.int64), n)
    cut = ((data[:, 0]>>16)&1).astype(bool)
    local = data[:, 1].copy().view(np.float32).astype(float)
    assert np.all(np.isfinite(local)) and np.all(local >= 0.)
    q = local.copy()
    pending = np.bincount(receiver[has], minlength=N)
    queue = list(np.flatnonzero(pending == 0))
    for c in queue:
        r = receiver[c]
        if r >= 0:
            if not cut[c]:
                q[r] += q[c]
            pending[r] -= 1
            if pending[r] == 0:
                queue.append(int(r))
    assert len(queue) == N, 'Drainage must be acyclic.'
    value = 8.*(np.log2(np.maximum(q, 1e-9))+8.)
    code = np.clip(np.floor(value+.5), 0, 255).astype(np.uint32)
    saved = data[:, 0]&255
    assert np.array_equal(code, saved), f'{np.count_nonzero(code != saved)} incorrect effective discharges.'
    expected_mid = np.where(cp._contacts[cp.PLANET_SEED][:, 1] < 1., 0, code)
    assert np.array_equal(expected_mid, data[:, 0]>>8&255)
    received = q[cut | ~has].sum()
    assert abs(received-local.sum()) < 1e-10*max(local.sum(), 1.)
    old = words[:, 1]>>16&255
    assert np.all(saved <= old+1), 'Stopping flow cannot increase downstream discharge.'
    before = Path(cp._REPO)/'x64/erosion-reprise/erosion-before-stops.bin'
    if before.exists():
        original = np.frombuffer(before.read_bytes()[24:], np.uint32).reshape(-1, 2)[:N]
        assert np.array_equal(words, original), 'The original level-0 network must remain unchanged.'
    print(f'Runoff: {N} cached nodes match independent accumulation; {cut.sum()} stopped links; sink balance preserved.')
    return words, n


def coast():
    # The user's coastal crossing. Compare the surviving courses with the same geometry before contact cuts.
    from verifie_lames import direction
    seed = cp.PLANET_SEED
    words, _ = cp.erosion_map()
    p = cp.window(direction(-9.040512300, 127.244378813), 16000., 112)
    ctx = cp.Ctx(10.)
    current = cp.elevation(ctx, p, extra=True)
    saved_flow, saved_contacts = cp._flow_words[seed], cp._contacts[seed]
    raw_code = words[:, 1]>>16&255
    try:
        cp._flow_words[seed] = np.stack((raw_code | raw_code<<8, np.zeros(len(words), np.uint32)), 1)
        cp._contacts[seed] = np.broadcast_to(np.ones(4), (len(words), 4))
        previous = cp.elevation(ctx, p, extra=True)
    finally:
        cp._flow_words[seed], cp._contacts[seed] = saved_flow, saved_contacts
    old_wet = previous['river_coverage'] > .9
    removed = old_wet & (current['river_coverage'] < .1)
    assert removed.sum() > 40, 'The coastal crossing witness must lose its disconnected river continuations.'
    assert np.all(np.isfinite(current['elev']))
    print(f'Coastal crossing: {removed.sum()} of {old_wet.sum()} formerly wet samples lose the disconnected channel.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter-only', action='store_true')
    args = parser.parse_args()
    stop_filter()
    if not args.filter_only:
        runoff()
        coast()
    print('ok')
