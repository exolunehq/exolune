# The relief for the coast survey (t0.py to t7.py): tools/hydro/cp.py, the numpy port of Relief.hlsli, behind a global
# filtering state. set_cell(cell) filters like a mesh of that cell (m); without it, no filtering.
# t0, t3 and t4 read the parts of the relief before the tectonic one, by name (docs/recherche-cotes.md, its audit): they
# are its record, and no longer run.
import importlib.util
import os

_spec = importlib.util.spec_from_file_location("relief_cp", os.path.join(os.path.dirname(__file__), "..", "hydro", "cp.py"))
relief = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(relief)

R = relief.R
tangent_basis, move = relief.tangent_basis, relief.move
_ctx = relief.Ctx()


def set_cell(cell):
    global _ctx
    _ctx = relief.Ctx(cell)


def elevation(p, diag=False):
    """Elevations (m) of the unit vectors p (n, 3); with diag, (e, parts): large the large forms (m), relief the noise's
    amplitude (m), youth, strata, axis the distance to the plate's boundary (km), roughness."""
    d = relief.elevation(_ctx, p, extra=True)
    if not diag:
        return d["elev"]
    return d["elev"], {k: d[k] for k in ("large", "relief", "youth", "strata", "axis", "roughness")}
