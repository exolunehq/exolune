"""Coastal metric regression: ria cusps must not set cliff heights at mesh scale.

CPU checks only; no performance or image-quality benchmark.
Run from the repository root: python tools/cotes/verifie_metrique_cotiere.py
"""
import ast
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hydro'))
import cp
from verifie_falaises import direction, evaluate


def previous_gradient():
    """Isolate the old metric; keep all other current erosion rules and the same caches."""
    root = Path(__file__).resolve().parents[2]
    source = subprocess.check_output(['git', 'show', '7187c1b:tools/hydro/cp.py'], cwd=root, text=True)
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_coast_gradient')
    namespace = dict(vars(cp))
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<previous-coast-gradient>', 'exec'), namespace)
    return namespace['_coast_gradient']


@contextmanager
def metric(model):
    current = cp._coast_gradient
    cp._coast_gradient = model
    try:
        yield
    finally:
        cp._coast_gradient = current


def derivative():
    """Compare the analytic gradient with finite differences of the independently evaluated noise value."""
    rng = np.random.default_rng(739)
    points = rng.normal(size=(96, 3))
    points /= np.linalg.norm(points, axis=1, keepdims=True)
    gain = np.linspace(.62, .7, len(points))
    rias = np.tile([0., .35, .6], len(points)//3)
    physical = cp.Ctx(1000.*cp.EROSION_CLIFF_SLOPE_KM/cp.MESH_BAND_LIMIT)
    error = 0.
    for seed in (647, 4743, 8839):
        gradient = cp._coast_gradient(cp.Ctx(.25), points, gain, rias, seed)
        for cell in (1., 4., 16., 256., 4500.):
            assert np.array_equal(gradient, cp._coast_gradient(cp.Ctx(cell), points, gain, rias, seed)), cell
        for tangent in cp.tangent_basis(points):
            plus = cp._coast_noise(physical, cp.move(points, tangent, np.full(len(points),.5)), gain, rias, seed)[0]
            minus = cp._coast_noise(physical, cp.move(points, tangent, np.full(len(points),-.5)), gain, rias, seed)[0]
            numeric = (plus-minus)*cp.R
            error = max(error, float(abs(numeric-(gradient*tangent).sum(1)).max()))
    assert error < 1e-3, error
    return dict(points=96, seeds=3, tangent_derivatives=576,
                max_derivative_error_per_radian=error, mesh_invariant_through_m=4500.)


def terrain():
    previous = previous_gradient()
    rows = []
    for name,lat,lon,size,n in [
        ('reported_ria_cusp',34.979160269604336,88.50935723258769,128.,129),
        ('reported_surroundings',34.983719,88.511430,2000.,101),
        ('cold_cliff_toe',-47.008952,-32.993928,256.,65),
        ('tropical_coast',8.48997,-103.55646,400.,65),
        ('southern_coast',-23.18981,157.86949,1000.,65),
        ('flat_coast',16.71,-89.28,400.,65),
    ]:
        points = cp.window(direction(lat,lon)[0],size,n)
        source,after,hc,delta = evaluate(points,1.)
        parent = cp.elevation(cp.Ctx(1.),points,valleys=False)
        with metric(previous):
            before = cp.elevation(cp.Ctx(1.),points)
            assert np.array_equal(parent,cp.elevation(cp.Ctx(1.),points,valleys=False))
        resolved = cp.elevation(cp.Ctx(.25),points)
        assert np.array_equal(after,resolved), 'Resolved terrain changes with mesh spacing'
        assert np.isfinite(after).all()
        if name == 'flat_coast':
            assert np.array_equal(before,after), 'The flat coast changed'
        def step(height):
            return float(max(abs(np.diff(height.reshape(n,n),axis=k)).max() for k in (0,1)))
        row = dict(name=name,lat=lat,lon=lon,samples=n*n,spacing_m=size/(n-1),
                   before_step_m=step(before),after_step_m=step(after),
                   max_cut_m=float((source-after).max()),max_height_parameter_m=float(hc.max()),
                   center_height_m=float(after[len(points)//2]))
        if name == 'reported_ria_cusp':
            assert row['before_step_m'] > 10., 'The historical wall is not reproduced'
            assert row['after_step_m'] < 1., 'The ria cusp still makes a wall'
            approach = cp.elevation(cp.Ctx(4.),points)
            row['approach_1_to_4_m'] = float(abs(approach-after).max())
            assert row['approach_1_to_4_m'] < 1.
        print(json.dumps(row),flush=True)
        rows.append(row)
    assert sum(row['max_cut_m']>10. for row in rows)>=3, 'The fix suppressed coastal erosion altogether'
    return rows


if __name__ == '__main__':
    report = dict(derivative=derivative(),terrain=terrain())
    out = Path('x64/erosion-walls/checks.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['derivative']))
