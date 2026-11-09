"""Regression checks for rock-gully blades. CPU only; no rendering or performance benchmark.

Run from the repository root: python tools/hydro/verifie_lames.py
Both implementations read the same caches. The reference belongs to the public history.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import types

import numpy as np
import cp


# Found by probing the regions used for the flight review, not inferred from truncated screenshot titles.
CASES = [
    (-25.568989230304577, -27.097705237890775),
    (-25.432998443062598, -26.946848975366226),
    (-7.376294929631997, 116.98752629219113),
    (-7.469073555496892, 117.01247636681902),
]


def direction(lat, lon):
    lat, lon = np.radians([lat, lon])
    return np.array([np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)])


def angles(z):
    north, east = np.gradient(z.reshape(81, 81), 1.)
    angle = np.degrees(np.arctan(np.hypot(north, east)))
    return dict(max_degrees=float(angle.max()), above_80=int(np.sum(angle > 80.)),
                max_step_m=float(max(abs(np.diff(z.reshape(81, 81), axis=a)).max() for a in (0, 1))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-ref', default='7187c1b')
    parser.add_argument('--out', default='x64/erosion-continuation/blades.json')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = subprocess.check_output(['git', 'show', args.before_ref + ':tools/hydro/cp.py'], cwd=root)
    old = types.ModuleType('before_blades')
    old.__file__ = cp.__file__
    exec(compile(source, '<before-blades>', 'exec'), old.__dict__)
    # EXOEROS3 adds terminal-water slices; the original six drainage slices are unchanged. Give the historical
    # evaluator those same decoded words instead of asking its EXOEROS2-only reader to parse the new container.
    old.erosion_map = cp.erosion_map
    report = dict(reference=args.before_ref, reference_sha256=hashlib.sha256(source).hexdigest(), cases=[])
    for lat, lon in CASES:
        p = cp.window(direction(lat, lon), 81., 81)
        before = old.elevation(old.Ctx(1.), p)
        after = cp.elevation(cp.Ctx(1.), p)
        resolved = cp.elevation(cp.Ctx(.25), p)
        assert np.isfinite(after).all()
        assert np.array_equal(after, resolved), 'Resolved terrain depends on mesh spacing'
        assert np.array_equal(old.elevation(old.Ctx(1.), p, valleys=False),
                              cp.elevation(cp.Ctx(1.), p, valleys=False)), 'The uncut parent changed'
        share = cp.EROSION_GULLY_SHARE
        try:
            cp.EROSION_GULLY_SHARE = 0.
            carrier = cp.elevation(cp.Ctx(1.), p)
        finally:
            cp.EROSION_GULLY_SHARE = share
        row = dict(lat=lat, lon=lon, before=angles(before), after=angles(after),
                   carrier=angles(carrier), max_gully_effect_m=float(abs(after-carrier).max()),
                   height_m=float(after[len(after)//2]))
        report['cases'].append(row)
        print(json.dumps(row), flush=True)
        assert row['before']['above_80'] > 0, 'The reference no longer reproduces a blade'
        assert row['after']['above_80'] == 0, 'A near-vertical blade remains in the regression window'
        assert row['after']['max_step_m'] < 5., 'A metre-wide height spike remains'
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
