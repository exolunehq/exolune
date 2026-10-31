# The relief of Exolune on the CPU, in float64: the numpy port of MyPlanetEngine/Noise.hlsli, Tectonics.hlsli and
# Relief.hlsli, with the same hash, the same gradients, the same octave filtering and crease rounding. The engine's planet
# map is checked against it (tools/banc_carte.py); the erosion research (tools/hydro, level 0) and the coast survey
# (tools/cotes, through its cp.py) use it. Always the exact lattice: the GPU's float and pair splits only differ by
# float32 rounding.
#
# The large forms come from the tectonic map, which the engine computes at startup (Tectonics.cpp) and writes beside its
# executable, x64/Release/tectonique-<seed>.bin: run the engine once for a seed, then this port reads it
# (docs/spec-relief-tectonique.md, the CPU port). EXOLUNE_TECTONIQUE overrides the path, with {seed} for the seed. The
# volcanoes likewise, volcans-<seed>.bin, EXOLUNE_VOLCANS (docs/spec-volcanisme.md).
#
# Interface: the constants of PlanetSettings.hlsli, PLANET_SEED, Ctx(cell), elevation(ctx, p, extra, valleys),
# tectonic_fields(q), window(center, size_m, n), latlon(nlat, nlon), tangent_basis(p), move(p, t, metres). The level 0's
# inputs: elevation(ctx, p, valleys=False), the form before erosion; uplift(p), the rock uplift (mm/yr); erodibility(p),
# the rock's, relative (docs/spec-relief-tectonique.md, the level 0); climate(p), the climate map's fields, the year's
# precipitation (mm) among them, and humidity(precipitation), the materials' (docs/spec-climat.md).
import math
import os
import numpy as np

R = 6378000.0  # m
R_KM = R / 1000.0

# The relief's settings (PlanetSettings.hlsli, first section). PLANET_SEED is read at every call.
PLANET_SEED = 0
RELIEF_WARP_TOP, RELIEF_WARP_OCTAVES, RELIEF_WARP = 800.0, 6, 30.0
RELIEF_SEGMENTS = (120.0, 0.25, 1.0)
RELIEF_TRENCH = (22.0, 6.0)
RELIEF_RIDGE_AXIS = 10.0
RELIEF_GRABEN = (25.0, 5.0)
RELIEF_TRANSFORM = (8.0, 4.0)
RELIEF_COAST = (12.0, 8.0, 40.0, 300.0)
RELIEF_COAST_SLOPE = (0.3, 2.0, 8.0)
RELIEF_COAST_NOISE = (60.0, 5.0, 0.62, 0.7)
RELIEF_RIAS = (0.6, 0.35)
RELIEF_BARRIER = (2.5, 0.6, 3.0, 0.5)
RELIEF_BARRIER_GAPS = (400.0, 15.0)
RELIEF_BARRIER_FORM = (0.6, 0.15, 4.0, 3)
RELIEF_COAST_QUIET = (0.1, 12.0)
RELIEF_DETAIL_TOP, RELIEF_OCTAVES, RELIEF_LACUNARITY = 50.0, 12, 2.11
RELIEF_DETAIL_WARP = (60.0, 5.0)
RELIEF_ORIENTED_OCTAVES, RELIEF_ORIENTATION = 3, (2.5, 450.0)
RELIEF_FOLD, RELIEF_FOLD_SETS = (26.0, 0.35, 150.0, 1.0), (2.0, 120.0)
RELIEF_FOLD_SADDLES, RELIEF_FOLD_REACH = (0.8, 50.0), (500.0, 800.0, 0.5, 0.7)
RELIEF_EROSION, RELIEF_RIDGE_EROSION = 1.5, 0.5
RELIEF_OLD_CREASE = 0.3
RELIEF_MESAS = (350.0, 12.0, 7.0)
RELIEF_MESA_STEP, RELIEF_RISER = 120.0, (0.1, 0.6)
RELIEF_BADLANDS = (45.0, 0.6, 6.0)
RELIEF_HIGHEST = (8000.0, 1000.0)
VOLCANO_FLOWS = (1.5, 0.25, 40.0, 15.0)
VOLCANO_CONES = 2.5
VOLCANO_REEF = (4.5, -12.0, 1.5)
VOLCANO_LOBES = (0.12, 0.1, 0.35)
MAX_TERRAIN_HEIGHT = 10000.0
NO_LIMIT = 3.4e38
CREASE_ROUNDING = 2.0
CREASE_MIN_CELL = 2.0
MESH_BAND_LIMIT = 2.0

# The noise's own constants (Noise.hlsli): its deviation, its scale per quality, the means of the filtered signals.
SIGMA = 0.4
SCALE = {False: 2.1935, True: 2.0961}  # standard, best
MEAN_BILLOW = {False: -0.3503, True: -0.3448}  # 2 E|n| - 1
MEAN_RIDGED = {False: 0.5103, True: 0.5048}  # E[(1 - |n|)^2]
MEAN_VORONOI = -0.0550


class Ctx:
    """The filtering state of a window: its cell in metres; None, no filtering."""

    def __init__(self, cell=None):
        self.maxf = NO_LIMIT if cell is None else R / (MESH_BAND_LIMIT * cell)
        self.creasef = NO_LIMIT if cell is None else R / (MESH_BAND_LIMIT * max(cell, CREASE_MIN_CELL))

    def capped(self, f):
        c = Ctx()
        c.maxf, c.creasef = min(self.maxf, f), self.creasef
        return c


# --- The hash: xxHash32's rounds, nested axis by axis, then its avalanche; 32-bit integers that wrap. ---
_P1, _P2, _P3, _P4, _P5 = (np.uint32(x) for x in (0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D, 0x27D4EB2F, 0x165667B1))
_ONE = np.uint32(1)


def _round(h, v):
    h = h + v * _P2
    h = (h << np.uint32(13)) | (h >> np.uint32(19))
    return h * _P1


def _mix(h):
    h = h ^ (h >> np.uint32(15))
    h = h * _P2
    h = h ^ (h >> np.uint32(13))
    h = h * _P3
    return h ^ (h >> np.uint32(16))


def _seed_term(seed):
    return np.uint32((int(seed) * 0x27D4EB2F) & 0xFFFFFFFF)


def _u32(c):
    return (c & 0xFFFFFFFF).astype(np.uint32)


def _corner_hashes(c):
    """The 8 corners of the cells c (n, 3) int64, bit 0 for x + 1, bit 1 for y + 1, bit 2 for z + 1."""
    x, y, z = _u32(c[:, 0]), _u32(c[:, 1]), _u32(c[:, 2])
    a0, a1 = _round(_P5, x), _round(_P5, x + _ONE)
    b = (_round(a0, y), _round(a1, y), _round(a0, y + _ONE), _round(a1, y + _ONE))
    return [_round(h, z) for h in b] + [_round(h, z + _ONE) for h in b]


def _gradient_table():
    # 256 unit vectors on a Fibonacci spiral, rounded to float32 as in Noise.hlsli.
    i = np.arange(256, dtype=np.float64)
    z = 1.0 - (2.0 * i + 1.0) / 256.0
    r = np.sqrt(1.0 - z * z)
    a = i * (math.pi * (3.0 - math.sqrt(5.0)))
    return np.stack([r * np.cos(a), r * np.sin(a), z], 1).astype(np.float32)


GRADIENTS = _gradient_table()
_G = GRADIENTS.astype(np.float64)
_SHIFT_STEP = np.array([0.7548776662, 0.5698402910, 0.4142135624], np.float32)


def _shift(o):
    # Each octave's lattice shifted by a fraction of a cell (docs/principes.md), computed in float32 as on the GPU.
    s = np.float32(o) * _SHIFT_STEP
    return (s - np.floor(s)).astype(np.float64)


def _lattice(p, f, o):
    x = p * f
    c = np.floor(x)
    q = x - c + _shift(o)
    fl = np.floor(q)
    return (c + fl).astype(np.int64), q - fl


def _fade(q, best):
    return q * q * q * (q * (q * 6.0 - 15.0) + 10.0) if best else q * q * (3.0 - 2.0 * q)


def _gradient(hashes, q, seed, best, s=None):
    k = _seed_term(seed)
    r = q - 1.0
    v = []
    for i, h in enumerate(hashes):
        g = _G[_mix(h + k) >> np.uint32(24)]
        v.append(g[:, 0] * (r[:, 0] if i & 1 else q[:, 0]) + g[:, 1] * (r[:, 1] if i & 2 else q[:, 1])
                 + g[:, 2] * (r[:, 2] if i & 4 else q[:, 2]))
    s = _fade(q, best) if s is None else s
    x0 = [v[j] + s[:, 0] * (v[j + 1] - v[j]) for j in (0, 2, 4, 6)]
    y0 = [x0[j] + s[:, 1] * (x0[j + 1] - x0[j]) for j in (0, 2)]
    return (y0[0] + s[:, 2] * (y0[1] - y0[0])) * SCALE[best]


def gradient_noise(p, seed, best=False, o=0):
    """One octave at the lattice point p (n, 3), unscaled frequency."""
    c, q = _lattice(np.asarray(p, np.float64), 1.0, o)
    return _gradient(_corner_hashes(c), q, seed, best)


def _value(h, seed):
    return (_mix(h + _seed_term(seed)) >> np.uint32(8)).astype(np.float64) * (2.0 / 16777216.0) - 1.0


# --- The bricks. ---
def _weight(ctx, f):
    return min(max(2.0 - 2.0 * f / ctx.maxf, 0.0), 1.0)


_PHI0 = 1.0 / math.sqrt(2.0 * math.pi)


def _excess(e):
    """The mean excess of the rounded |x| over |x|, for a normal noise of deviation SIGMA."""
    if e <= 0.0:
        return 0.0
    s, s2 = SIGMA, SIGMA * SIGMA
    if e < s:
        e2 = e * e
        return _PHI0 / s * e2 * (1.0 / 3.0 - e2 / (60.0 * s2) + e2 * e2 / (840.0 * s2 * s2) - e2 ** 3 / (12096.0 * s2 ** 3))
    u = e / s
    er, ph = math.erf(u / math.sqrt(2.0)), _PHI0 * math.exp(-0.5 * u * u)
    return s2 / (2.0 * e) * (er - 2.0 * u * ph) + 0.5 * e * er - 2.0 * s * (_PHI0 - ph)


def _crease(ctx, x, f):
    e = CREASE_ROUNDING * f / ctx.creasef
    a = np.abs(x)
    if e <= 0.0:
        return a
    return np.where(a >= e, a, 0.5 * (x * x / e + e)) - _excess(e)


def fbm(ctx, p, f, lac, n, seed, best):
    out, amp = np.zeros(len(p)), 1.0
    for o in range(n):
        w = _weight(ctx, f)
        if w <= 0.0:
            break
        c, q = _lattice(p, f, o)
        out += amp * w * _gradient(_corner_hashes(c), q, seed + o, best)
        f *= lac
        amp *= 0.5
    return out


def billow(ctx, p, f, lac, n, seed, best):
    out, amp = np.full(len(p), 0.5), 1.0
    for o in range(n):
        w = _weight(ctx, f)
        if w > 0.0:
            c, q = _lattice(p, f, o)
            b = 2.0 * _crease(ctx, _gradient(_corner_hashes(c), q, seed + o, best), f) - 1.0
            out += amp * (MEAN_BILLOW[best] + w * (b - MEAN_BILLOW[best]))
        else:
            out += amp * MEAN_BILLOW[best]
        f *= lac
        amp *= 0.5
    return out


def ridged(ctx, p, f, lac, n, seed, best, raw=None):
    out, chain, spectral = np.zeros(len(p)), np.ones(len(p)), 1.0
    for o in range(n):
        w = _weight(ctx, f)
        if w > 0.0:
            c, q = _lattice(p, f, o)
            g = _gradient(_corner_hashes(c), q, seed + o, best)
            if raw is not None and o == 0:
                raw.append(g)
            r = (1.0 - _crease(ctx, g, f)) ** 2
            r = MEAN_RIDGED[best] + w * (r - MEAN_RIDGED[best])
        else:
            r = np.full(len(p), MEAN_RIDGED[best])
            if raw is not None and o == 0:
                raw.append(np.full(len(p), np.nan))
        r = r * chain
        chain = np.clip(2.0 * r, 0.0, 1.0)
        out += r * spectral
        f *= lac
        spectral /= lac
    return 1.25 * out - 1.0


def voronoi(ctx, p, f, seed):
    w = _weight(ctx, f)
    if w <= 0.0:
        return np.full(len(p), MEAN_VORONOI)
    c, q = _lattice(p, f, 0)
    x, y, z = _u32(c[:, 0]), _u32(c[:, 1]), _u32(c[:, 2])
    best = np.full(len(p), np.inf)
    for dz in range(-2, 3):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                h = _round(_round(_round(_P5, x + np.uint32(dx & 0xFFFFFFFF)), y + np.uint32(dy & 0xFFFFFFFF)),
                           z + np.uint32(dz & 0xFFFFFFFF))
                d0 = dx + _value(h, seed) - q[:, 0]
                d1 = dy + _value(h, seed + 1) - q[:, 1]
                d2 = dz + _value(h, seed + 2) - q[:, 2]
                best = np.minimum(best, d0 * d0 + d1 * d1 + d2 * d2)
    v = math.sqrt(3.0) * np.sqrt(best) - 1.0
    return MEAN_VORONOI + w * (v - MEAN_VORONOI)


def turbulence(ctx, p, f, power, n, seed):
    """The point displaced by three fBm of lacunarity 2, one per axis, sharing the lattice and the blend."""
    if _weight(ctx, f) <= 0.0:
        return p
    d, amp = np.zeros_like(p), 1.0
    for o in range(n):
        w = _weight(ctx, f)
        if w <= 0.0:
            break
        c, q = _lattice(p, f, o)
        h, s = _corner_hashes(c), _fade(q, False)
        for a in range(3):
            d[:, a] += amp * w * _gradient(h, q, seed + 16 * a + o, False, s)
        f *= 2.0
        amp *= 0.5
    return p + power * d


def gradient_noise_d(cell, q, seed):
    """One octave and its gradient against the lattice coordinates, best quality, as RlGradientNoiseD (Noise.hlsli):
    (value, gradient (n, 3)), the cell (n, 3) int64 and the remainder q (n, 3)."""
    fl = np.floor(q)
    cell, q = cell + fl.astype(np.int64), q - fl
    h = _corner_hashes(cell)
    k = _seed_term(seed)
    g = [_G[_mix(x + k) >> np.uint32(24)] for x in h]  # bit 0 x + 1, bit 1 y + 1, bit 2 z + 1
    r = q - 1.0
    n = []
    for i in range(8):
        d = np.stack([r[:, 0] if i & 1 else q[:, 0], r[:, 1] if i & 2 else q[:, 1], r[:, 2] if i & 4 else q[:, 2]], 1)
        n.append((g[i] * d).sum(1))
    s = _fade(q, True)
    ds = 30.0 * q * q * r * r
    n000, n100, n010, n110, n001, n101, n011, n111 = n
    g000, g100, g010, g110, g001, g101, g011, g111 = g
    k1, k2, k3 = n100 - n000, n010 - n000, n001 - n000
    k4, k5, k6 = n000 - n100 - n010 + n110, n000 - n010 - n001 + n011, n000 - n100 - n001 + n101
    k7 = n100 + n010 + n001 + n111 - n000 - n110 - n101 - n011
    a1, a2, a3 = g100 - g000, g010 - g000, g001 - g000
    a4, a5, a6 = g000 - g100 - g010 + g110, g000 - g010 - g001 + g011, g000 - g100 - g001 + g101
    a7 = g100 + g010 + g001 + g111 - g000 - g110 - g101 - g011
    sx, sy, sz = s[:, 0:1], s[:, 1:2], s[:, 2:3]
    value = (n000 + k1 * s[:, 0] + k2 * s[:, 1] + k3 * s[:, 2] + k4 * s[:, 0] * s[:, 1] + k5 * s[:, 1] * s[:, 2]
             + k6 * s[:, 2] * s[:, 0] + k7 * s[:, 0] * s[:, 1] * s[:, 2])
    grad = (g000 + a1 * sx + a2 * sy + a3 * sz + a4 * sx * sy + a5 * sy * sz + a6 * sz * sx + a7 * sx * sy * sz
            + ds * np.stack([k1 + k4 * s[:, 1] + k6 * s[:, 2] + k7 * s[:, 1] * s[:, 2],
                             k2 + k5 * s[:, 2] + k4 * s[:, 0] + k7 * s[:, 2] * s[:, 0],
                             k3 + k6 * s[:, 0] + k5 * s[:, 1] + k7 * s[:, 0] * s[:, 1]], 1))
    return value * SCALE[True], grad * SCALE[True]


# --- The tectonic map (MyPlanetEngine/Tectonics.h, Tectonics.hlsli), read from the engine's cache. ---
# The engine computes it at startup and writes it beside its executable, tectonique-<seed>.bin: a header, then RGBA half
# floats, per face 5 slices of (size + 2 pad)^2 texels, each face padded with the fields beyond its edges: the relief's
# three, then slice 3, the views' (age, margin, uplift, suture), slice 4 the erodibility, at full resolution.
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TECTONIC_CACHE = os.environ.get("EXOLUNE_TECTONIQUE", os.path.join(_REPO, "x64", "Release", "tectonique-{seed}.bin"))
_maps = {}

# Each face's normal and texel axes, D3D's cube map layout.
_FN = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], np.float64)
_FS = np.array([[0, 0, -1], [0, 0, 1], [1, 0, 0], [1, 0, 0], [1, 0, 0], [-1, 0, 0]], np.float64)
_FT = np.array([[0, -1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], [0, -1, 0], [0, -1, 0]], np.float64)
TECTONIC_BLEND = 1.5  # texels


def tectonic_map(seed=None):
    """The map of the seed (PLANET_SEED by default): (texels (6, 5, w, w, 4) float32, size, pad)."""
    seed = PLANET_SEED if seed is None else seed
    if seed not in _maps:
        path = TECTONIC_CACHE.format(seed=seed)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path}: run the engine once with this seed, it writes its tectonic map there")
        raw = open(path, "rb").read()
        assert raw[:8] == b"EXOTECT2", f"{path}: an older map, run the engine again"
        s, n, pad, slices, faces = (int(x) for x in np.frombuffer(raw[8:28], np.uint32))
        w = n + 2 * pad
        tex = np.frombuffer(raw[28:], np.float16).astype(np.float32).reshape(faces, slices, w, w, 4)
        _maps[seed] = (tex, n, pad)
    return _maps[seed]


def _weights(f):
    g, f2 = 1.0 - f, f * f
    w = np.stack([g * g * g, 3.0 * f2 * f - 6.0 * f2 + 4.0, -3.0 * f2 * f + 3.0 * f2 + 3.0 * f + 1.0, f2 * f], 1) / 6.0
    dw = np.stack([-g * g, 3.0 * f2 - 4.0 * f, -3.0 * f2 + 2.0 * f + 1.0, f2], 1) * 0.5
    return w, dw


def _face_read(tex, n, pad, q, face, slices):
    """The cubic B-spline of the slices at q on its face `face` (n,), its own texels; in 3D, the gradients of slice 0's x,
    slice 2's x and slice 2's y, as TectonicFace."""
    m = (q * _FN[face]).sum(1)
    x = ((q * _FS[face]).sum(1) / m + 1.0) * 0.5 * n - 0.5 + pad
    y = ((q * _FT[face]).sum(1) / m + 1.0) * 0.5 * n - 0.5 + pad
    cx, cy = np.floor(x), np.floor(y)
    wx, dx = _weights(x - cx)
    wy, dy = _weights(y - cy)
    ix, iy = cx.astype(np.int64) - 1, cy.astype(np.int64) - 1
    w = tex.shape[2]
    out = {s: np.zeros((len(q), 4)) for s in slices}
    g = {k: np.zeros((len(q), 2)) for k in ("forms", "side", "orientation")}
    for j in range(4):
        yy = np.clip(iy + j, 0, w - 1)
        for i in range(4):
            xx = np.clip(ix + i, 0, w - 1)
            k = (wx[:, i] * wy[:, j])[:, None]
            for s in slices:
                v = tex[face, s, yy, xx]
                out[s] += k * v
                for name, sl, ch in (("forms", 0, 0), ("side", 2, 0), ("orientation", 2, 1)):
                    if s == sl:
                        g[name][:, 0] += dx[:, i] * wy[:, j] * v[:, ch]
                        g[name][:, 1] += wx[:, i] * dy[:, j] * v[:, ch]
    grads = {k: (v[:, 0:1] * _FS[face] + v[:, 1:2] * _FT[face]) * (0.5 * n) for k, v in g.items()}
    return out, grads


def tectonic_fields(q, slices=(0, 1, 2), seed=None):
    """The map's fields at the directions q (n, 3), as TectonicFields (Tectonics.hlsli): a dictionary slice -> (n, 4),
    and the gradients (n, 3) of slice 0's x, 'forms_gradient', of slice 2's x, 'gradient', and y, 'orientation_gradient';
    the faces blended near their edges."""
    tex, n, pad = tectonic_map(seed)
    q = np.asarray(q, np.float64)
    a = np.abs(q)
    axis = np.argmax(a, 1)  # ties: x, then y, as the shader
    rows = np.arange(len(q))
    largest = a[rows, axis]
    start = 1.0 - 2.0 * TECTONIC_BLEND / n
    face = 2 * axis + (q[rows, axis] < 0.0)
    total = np.ones(len(q))
    sums, grads = _face_read(tex, n, pad, q, face, slices)
    for k in (1, 2):
        other = (axis + k) % 3
        t = np.clip((a[rows, other] / largest - start) / (1.0 - start), 0.0, 1.0)
        w = t * t * (3.0 - 2.0 * t)
        sel = w > 0.0
        if not sel.any():
            continue
        f2 = 2 * other[sel] + (q[sel, other[sel]] < 0.0)
        o, g = _face_read(tex, n, pad, q[sel], f2, slices)
        for s in slices:
            sums[s][sel] += w[sel, None] * o[s]
        for name in grads:
            grads[name][sel] += w[sel, None] * g[name]
        total[sel] += w[sel]
    out = {s: sums[s] / total[:, None] for s in slices}
    out["forms_gradient"] = grads["forms"] / total[:, None]
    out["gradient"] = grads["side"] / total[:, None]
    out["orientation_gradient"] = grads["orientation"] / total[:, None]
    return out


def uplift(p, seed=None):
    """The rock uplift (mm/yr) at the unit vectors p (n, 3), the level 0's: the large forms' own, a share of their
    convergence where they rise, < 0 in the forelands and the grabens (Tectonics.cpp)."""
    return tectonic_fields(p, (3,), seed)[3][:, 2]


def erodibility(p, seed=None):
    """The rock's erodibility at the unit vectors p (n, 3), relative to the young chains', 0.25 on the shields to 3 in the
    soft sediments (Tectonics.cpp, kErodibility)."""
    return tectonic_fields(p, (4,), seed)[4][:, 0]


# --- The climate map (MyPlanetEngine/Climate.h, Climate.hlsli), read from the engine's cache. ---
# The engine computes it at startup from the tectonic map and writes it beside its executable, climat-<seed>.bin: a header,
# then per texel the fields of CLIMATE_FIELDS as float32, face by face, row by row. EXOLUNE_CLIMAT overrides the path.
CLIMATE_CACHE = os.environ.get("EXOLUNE_CLIMAT", os.path.join(_REPO, "x64", "Release", "climat-{seed}.bin"))
CLIMATE_FIELDS = ("precipitation", "temperature", "amplitude", "summer", "wind_east", "wind_north", "continentality",
                  "upwelling")
_climates = {}


def climate_map(seed=None):
    """The climate map of the seed (PLANET_SEED by default): (fields (6, n, n, channels) float32, n)."""
    seed = PLANET_SEED if seed is None else seed
    if seed not in _climates:
        path = CLIMATE_CACHE.format(seed=seed)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path}: run the engine once with this seed, it writes its climate map there")
        raw = open(path, "rb").read()
        assert raw[:8] == b"EXOCLIM1", f"{path}: an older map, run the engine again"
        s, n, channels, faces = (int(x) for x in np.frombuffer(raw[8:24], np.uint32))
        _climates[seed] = (np.frombuffer(raw[24:], np.float32).reshape(faces, n, n, channels), n)
    return _climates[seed]


def _cube_cell(q, n):
    """The face holding each direction q (n, 3), D3D's choice, and q's texel coordinates on it, texel i's centre at i."""
    axis = np.argmax(np.abs(q), 1)
    rows = np.arange(len(q))
    face = 2 * axis + (q[rows, axis] < 0.0)
    m = (q * _FN[face]).sum(1)
    return face, ((q * _FS[face]).sum(1) / m + 1.0) * 0.5 * n - 0.5, ((q * _FT[face]).sum(1) / m + 1.0) * 0.5 * n - 0.5


def climate(p, seed=None):
    """The climate map's fields at the directions p (n, 3), as Climate::At: bilinear on the face holding p, the texels past
    its edge taken on the next face. A dictionary CLIMATE_FIELDS -> (n,): precipitation (mm/yr), temperature (C, the
    year's mean at sea level, the ground's 5 C colder per km), amplitude (C, the seasons' half), summer (the rain's share
    in the warm half-year), wind_east and wind_north (m/s), continentality (0 to 1), upwelling (C, <= 0)."""
    cells, n = climate_map(seed)
    q = np.asarray(p, np.float64)
    face, x, y = _cube_cell(q, n)
    fx, fy = np.floor(x), np.floor(y)
    u, v = x - fx, y - fy
    out = np.zeros((len(q), cells.shape[3]))
    for k in range(4):
        ii, jj = fx.astype(np.int64) + (k & 1), fy.astype(np.int64) + (k >> 1)
        f, i, j = face.copy(), ii.copy(), jj.copy()
        past = (ii < 0) | (jj < 0) | (ii >= n) | (jj >= n)
        if past.any():
            s_ = (ii[past] + 0.5) * 2.0 / n - 1.0
            t_ = (jj[past] + 0.5) * 2.0 / n - 1.0
            d = _FN[face[past]] + s_[:, None] * _FS[face[past]] + t_[:, None] * _FT[face[past]]
            f2, x2, y2 = _cube_cell(d, n)
            f[past] = f2
            i[past] = np.clip(np.floor(x2 + 0.5), 0, n - 1).astype(np.int64)
            j[past] = np.clip(np.floor(y2 + 0.5), 0, n - 1).astype(np.int64)
        w = ((u if k & 1 else 1.0 - u) * (v if k >> 1 else 1.0 - v))[:, None]
        out += w * cells[f, j, i]
    return {name: out[:, k] for k, name in enumerate(CLIMATE_FIELDS)}


def humidity(precipitation):
    """The humidity the materials and the plants read (Climate.hlsli): the log of the year's precipitation from 100 to
    3 000 mm, 0 to 1."""
    return np.clip(np.log(np.maximum(precipitation, 1.0) / 100.0) / np.log(30.0), 0.0, 1.0)


# --- The volcanoes (MyPlanetEngine/Volcanoes.hlsli), read from the engine's file, volcans-<seed>.bin: a header, the
# volcanoes (Tectonics::Volcano, 52 bytes), their index. The port evaluates every volcano within its reach of each point,
# which is what the index lists. ---
VOLCANO_CACHE = os.environ.get("EXOLUNE_VOLCANS", os.path.join(_REPO, "x64", "Release", "volcans-{seed}.bin"))
VOLCANO_DTYPE = np.dtype([("at", "<f4", 3), ("radius", "<f4"), ("height", "<f4"), ("shape", "<f4"), ("crater", "<f4"),
                          ("depth", "<f4"), ("top", "<f4"), ("reef", "<f4"), ("cones", "<f4"), ("fresh", "<f4"),
                          ("seed", "<u4")])
VOLCANO_NO_TOP, VOLCANO_REACH = 1e8, (1.7, 80.0)
_volcanoes = {}


def volcanoes(seed=None):
    """The volcanoes of the seed (PLANET_SEED by default), a structured array (VOLCANO_DTYPE)."""
    seed = PLANET_SEED if seed is None else seed
    if seed not in _volcanoes:
        path = VOLCANO_CACHE.format(seed=seed)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path}: run the engine once with this seed, it writes its volcanoes there")
        raw = open(path, "rb").read()
        assert raw[:8] == b"EXOVOLC1", f"{path}: an older file, run the engine again"
        count = int(np.frombuffer(raw[12:16], np.uint32)[0])
        _volcanoes[seed] = np.frombuffer(raw[28:28 + count * 52], VOLCANO_DTYPE)
    return _volcanoes[seed]


def _profile(x, shape):
    strato = np.exp(-3.0 * x) * (1.0 - _smooth(0.7, 1.3, x))
    shield = (1.0 - np.clip(x, 0.0, 1.0) ** 1.3) * (1.0 - _smooth(0.6, 1.0, x))
    return strato + (shield - strato) * shape


def _over(t):
    """1 - Phi(t)."""
    return 0.5 * np.vectorize(math.erfc)(np.asarray(t, np.float64) / math.sqrt(2.0))


def _vseed(v, k=0):
    return (int(v["seed"]) + k) & 0xFFFFFFFF


def _flows(ctx, xy, r, v, radius, cell_km):
    """VolcanoFlows: (thickness (n,), share (n,))."""
    x = r / radius
    env = _smooth(np.maximum(0.25 * radius, v["crater"]), np.maximum(0.4 * radius, v["crater"] + 0.1 * radius), r) * (1.0 - _smooth(1.0, 1.15, x))
    n = len(r)
    if v["fresh"] <= 0.0 or not (env > 0.0).any():
        return np.zeros(n), np.zeros(n)
    across = VOLCANO_FLOWS[0] * (1.0 + v["shape"])
    k = 0.5 * radius / across
    wide = np.maximum(r, 0.05 * radius) / k
    w = np.clip(2.0 - 2.0 * (R_KM / wide) / ctx.maxf, 0.0, 1.0)
    threshold = -0.6 + 1.9 * x
    e = np.maximum(0.6, 5.0 * cell_km / wide)
    lobe = _over(threshold + 0.5 * e)
    sel = w > 0.0
    if sel.any():
        c = xy[sel] / np.maximum(r[sel], 1e-4)[:, None]
        q = np.stack([k[sel] * c[:, 0], k[sel] * c[:, 1], r[sel] / np.maximum(VOLCANO_FLOWS[1] * radius[sel], 3.0)], 1) + [0.5, 0.25, 0.125]
        coarse = q * [0.4, 0.4, 1.5]
        q[:, 0] += 0.5 * gradient_noise(coarse, _vseed(v, 1), False) / SIGMA
        q[:, 1] += 0.5 * gradient_noise(coarse, _vseed(v, 2), False) / SIGMA
        nz = gradient_noise(q, _vseed(v), True) / SIGMA
        t = np.clip((nz - threshold[sel]) / e[sel], 0.0, 1.0)
        lobe[sel] = lobe[sel] + (t * t * (3.0 - 2.0 * t) - lobe[sel]) * w[sel]
    share = lobe * env
    thick = v["fresh"] * (VOLCANO_FLOWS[2] + (VOLCANO_FLOWS[3] - VOLCANO_FLOWS[2]) * v["shape"])
    return thick * env * (lobe - _over(threshold + 0.5 * e)), share


def _cones(ctx, xy, r, v, radius, cell_km):
    """VolcanoCones: (height (n,), presence (n,))."""
    n = len(r)
    spacing = VOLCANO_CONES
    density = v["cones"] * (1.0 - _smooth(0.6, 1.2, r / radius))
    if not (density > 0.0).any():
        return np.zeros(n), np.zeros(n)
    w = min(max(2.0 - 2.0 * (R_KM / spacing) / ctx.maxf, 0.0), 1.0)
    h, presence = np.zeros(n), np.zeros(n)
    if w > 0.0:
        g = np.floor(xy / spacing)
        start = np.full(n, np.uint32(_vseed(v) ^ 0x165667B1), np.uint32)
        for k in range(9):
            cell = g + [k % 3 - 1, k // 3 - 1]
            ci = cell.astype(np.int64)
            hsh = _round(_round(start, _u32(ci[:, 0])), _u32(ci[:, 1]))
            u = np.stack([(_mix(hsh + np.uint32(i)) >> np.uint32(8)).astype(np.float64) / 16777216.0 for i in range(4)], 1)
            centre = (cell + 0.15 + 0.7 * u[:, 1:3]) * spacing
            keep = u[:, 0] < v["cones"] * (1.0 - _smooth(0.6, 1.2, np.linalg.norm(centre, axis=1) / radius))
            size = 0.25 + 0.5 * u[:, 3]
            wide = np.maximum(size, 2.0 * cell_km)
            height = 250.0 * size * (size / wide) ** 2
            dist = np.linalg.norm(xy - centre, axis=1)
            t = np.clip((1.0 - dist / wide) / 0.6, 0.0, 1.0)
            cone = height * t * t * (3.0 - 2.0 * t)
            rim = 0.4 * size
            rim_wide = np.maximum(rim, 2.0 * cell_km)
            u2 = dist / rim_wide
            cone = cone - np.where(u2 < 1.0, 0.35 * height * (rim / rim_wide) ** 2 * (1.0 - u2 * u2) ** 2, 0.0)
            h = np.where(keep, np.maximum(h, cone), h)
            presence = np.where(keep, np.maximum(presence, w * np.clip(2.0 * t, 0.0, 1.0)), presence)
    mean = density * math.pi * 0.3 * 250.0 * 0.156 / (spacing * spacing)
    return w * h + (1.0 - w) * mean, presence


def _around(c, around, km, seed):
    """VolcanoAround: a noise on the circle around a volcano at the directions c (n, 2), in deviations."""
    q = np.stack([c[:, 0] * (around / km), c[:, 1] * (around / km), np.full(len(c), 0.5)], 1)
    return gradient_noise(q, seed, True) / SIGMA


def _drawn(v, k):
    """A volcano's uniform draw k, as (RlMix1(v.seed + k) >> 8) / 2^24."""
    return float((_mix(np.array([_vseed(v, k)], np.uint32)) >> np.uint32(8))[0]) / 16777216.0


def _reef(ctx, v, xy, r, lobes, cell_km):
    """VolcanoReef (Volcanoes.hlsli): (reef, crest, lagoon, lagoonLevel), each (n,)."""
    n = len(r)
    reef, crest, lagoon, level = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    if v["reef"] <= 0.0:
        return reef, crest, lagoon, level
    c = xy / np.maximum(r, 1e-4)[:, None]
    rim = VOLCANO_REEF[2]
    w = min(max(2.0 - 2.0 * (R_KM / rim) / ctx.maxf, 0.0), 1.0)
    windward = 0.5 + 0.5 * c[:, 0]
    line = v["reef"] * lobes + 0.35 * rim * w * _around(c, v["reef"], 2.0 * rim, _vseed(v, 10))
    flat0 = (0.25 + 0.55 * windward) * (1.0 + 0.5 * w * _around(c, v["reef"], 3.0 * rim, _vseed(v, 11)))
    wp = min(max(2.0 - 2.0 * (R_KM * 2.5 / rim) / ctx.maxf, 0.0), 1.0)
    qp = xy * (2.5 / rim)
    ragged = wp * gradient_noise(np.stack([qp[:, 0], qp[:, 1], np.full(n, 4.3)], 1), _vseed(v, 15), True) / SIGMA
    cut = wp * gradient_noise(np.stack([qp[:, 0], qp[:, 1], np.full(n, 7.9)], 1), _vseed(v, 16), True) / SIGMA
    flat = np.maximum(flat0, 2.0 * cell_km)
    u = (r - line) / flat + 0.25 * ragged
    inside = u <= 1.0
    reef = np.where(inside, 1.0 - _smooth(0.6, 1.0, np.abs(u)), 0.0)
    lagoon = np.where(inside, 1.0 - _smooth(-1.0, -0.5, u), 0.0)
    pass_limit, motu_limit = -0.6 - 0.9 * windward, 1.2 - 0.9 * windward
    open_, motu = _over(pass_limit + 0.15), _over(motu_limit + 0.15)
    if w > 0.0:
        a = _smooth(pass_limit, pass_limit + 0.3, _around(c, v["reef"], rim, _vseed(v, 12)))
        b = _smooth(motu_limit, motu_limit + 0.3, 0.8 * _around(c, v["reef"], rim, _vseed(v, 13)) + 0.6 * cut)
        open_, motu = open_ + (a - open_) * w, motu + (b - motu) * w
    crest = ((-8.0 + 6.5 * open_) + VOLCANO_REEF[0] * motu * open_ * (1.0 - _smooth(0.15, 0.45, np.abs(u + 0.15 * cut)))) * flat0 / flat
    wl = min(max(2.0 - 2.0 * (R_KM / (2.0 * rim)) / ctx.maxf, 0.0), 1.0)
    q = np.stack([xy[:, 0] / (2.0 * rim), xy[:, 1] / (2.0 * rim), np.full(n, 9.1)], 1)
    level = VOLCANO_REEF[1] * (1.0 + 0.3 * wl * np.tanh(gradient_noise(q, _vseed(v, 14), True) / SIGMA))
    return reef, crest, lagoon, level


def volcano_edifices(ctx, p, seed=None):
    """VolcanoEdifices (Volcanoes.hlsli) at the unit vectors p (n, 3): (the edifices (m), quiet, volcanic, finish), finish
    a dictionary of the dominant volcano's top, topWeight, reef, crest, lagoon and lagoonLevel."""
    p = np.asarray(p, np.float64)
    n = len(p)
    cell_km = _cell_km(ctx)
    rise, sink, cones = np.zeros(n), np.zeros(n), np.zeros(n)
    quiet, volcanic, presence, dominant = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    fin = dict(top=np.full(n, VOLCANO_NO_TOP), topWeight=np.zeros(n), reef=np.zeros(n), crest=np.zeros(n),
               lagoon=np.zeros(n), lagoonLevel=np.zeros(n))
    for v in volcanoes(seed):
        at = v["at"].astype(np.float64)
        reach = max(VOLCANO_REACH[0] * v["radius"], VOLCANO_REACH[1])
        off = (p - at) * R_KM
        r = np.linalg.norm(off, axis=1)
        sel = np.nonzero(r < reach)[0]
        if not len(sel):
            continue
        off, r = off[sel], r[sel]
        a = np.asarray(v["at"], np.float32)
        up = np.array([0.0, 1.0, 0.0], np.float32) if abs(a[1]) < 0.99 else np.array([1.0, 0.0, 0.0], np.float32)
        east = np.cross(a, up).astype(np.float64)
        east /= np.linalg.norm(east)
        north = np.cross(east, at)
        xy = np.stack([off @ east, off @ north], 1)
        base = min(max(float(v["radius"]), 2.0 * cell_km), reach / VOLCANO_REACH[0])
        height = v["height"] * (v["radius"] / base) ** 2
        c = xy / np.maximum(r, 1e-4)[:, None]
        angle = 6.2831853 * _drawn(v, 6)
        stretch = (VOLCANO_LOBES[1] + (VOLCANO_LOBES[2] - VOLCANO_LOBES[1]) * v["shape"]) * _drawn(v, 7)
        lobes = np.clip(1.0 + VOLCANO_LOBES[0] * (_around(c, 1.0, 1.0, _vseed(v, 4)) + 0.35 * _around(c, 2.5, 1.0, _vseed(v, 5))) / 1.06
                        + stretch * ((c[:, 0] ** 2 - c[:, 1] ** 2) * math.cos(2.0 * angle) + 2.0 * c[:, 0] * c[:, 1] * math.sin(2.0 * angle)),
                        0.7, 1.3)
        radius = base * lobes
        x = r / radius
        e = height * _profile(x, v["shape"])
        if v["crater"] > 0.0:
            wide = max(float(v["crater"]), 2.0 * cell_km)
            u = r / wide
            caldera = _smooth(0.8, 2.5, v["crater"])
            b = 1.0 - np.minimum(u, 1.0) ** (2.0 + 6.0 * caldera)
            bowl = (b * b + (b - b * b) * caldera) * (v["crater"] / wide) ** 2
            floor = height * _profile(v["crater"] / base, v["shape"]) - v["depth"]
            e = np.where(u < 1.0, e + (floor - e) * bowl, e)
        fl, flowing = _flows(ctx, xy, r, v, radius, cell_km)
        e = e + fl
        cn, pr = _cones(ctx, xy, r, v, base, cell_km)
        cones[sel] = np.maximum(cones[sel], cn)
        presence[sel] = np.maximum(presence[sel], pr)
        rise[sel] += np.where(e > 0.0, e, 0.0) ** 4
        sink[sel] = np.minimum(sink[sel], e)
        core = 1.0 - _smooth(0.2, 1.3, x)
        summit = 1.0 - _smooth(0.4 + (0.15 - 0.4) * v["shape"], 0.8 + (0.35 - 0.8) * v["shape"], x)
        quiet[sel] = np.maximum(quiet[sel], (0.3 + 0.5 * v["fresh"]) * core)
        volcanic[sel] = np.maximum(volcanic[sel], v["fresh"] * np.maximum(0.8 * summit, flowing))
        dom = e > dominant[sel]
        if dom.any():
            i = sel[dom]
            dominant[i] = e[dom]
            fin["top"][i] = v["top"]
            fin["topWeight"][i] = (1.0 - _smooth(0.9, 1.05, x[dom])) if v["top"] < VOLCANO_NO_TOP else 0.0
            fin["reef"][i], fin["crest"][i], fin["lagoon"][i], fin["lagoonLevel"][i] = _reef(ctx, v, xy[dom], r[dom], lobes[dom], cell_km)
    return np.sqrt(np.sqrt(rise)) + sink + cones, quiet, np.maximum(volcanic, presence), fin


def volcano_finish(ctx, p, h, fin):
    """VolcanoFinish (Volcanoes.hlsli): the planed tops, the reefs and their lagoons, after the detail."""
    h = h.copy()
    t, tw = fin["top"], fin["topWeight"]
    k = np.clip(t, 20.0, 400.0)
    gap = np.maximum(k - np.abs(h - t), 0.0)
    low = np.minimum(h, t) - gap * gap / (4.0 * k)
    h = np.where(tw > 0.0, h + (low - h) * tw, h)
    h = h + (np.maximum(h, fin["lagoonLevel"]) - h) * fin["lagoon"]
    return np.maximum(h, h + (fin["crest"] - h) * fin["reef"])

# --- The relief (MyPlanetEngine/Relief.hlsli): the large forms from the map, the detail from the noise. ---
def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _rseed(k):
    return (PLANET_SEED * 4096 + 64 * k) & 0xFFFFFFFF


def _cell_km(ctx):
    return R_KM / (MESH_BAND_LIMIT * ctx.maxf)


def _width(w, cell_km, depth):
    wide = np.maximum(w, 2.0 * cell_km)
    return wide, depth * w / wide


def _rcrease(x, e):
    a = np.abs(x)
    e = np.broadcast_to(e, a.shape)
    ex = np.vectorize(_excess)(e) if np.ndim(e) else _excess(float(e))
    inside = a < e
    safe = np.where(inside, e, 1.0)
    c = np.where(inside, 0.5 * (x * x / safe + e), a) - ex
    dc = np.where(inside, x / safe, np.sign(x))
    return c, dc


def detail(ctx, oriented, plain, oriented_octaves, top_km, octaves, relief, sharp, crease, seed, fold=None, fold_share=0.0,
           fold_weight=0.0, wide_octaves=0):
    """ReliefDetail (Relief.hlsli): (value, slope vector (n, 3)), and with wide_octaves the value of these widest octaves
    alone; fold, (value (n,), gradient per radian (n, 3))."""
    up = plain / np.linalg.norm(plain, axis=1, keepdims=True)
    n = len(plain)
    rnd, rid, chain, amp = np.zeros(n), np.zeros(n), np.ones(n), 1.0
    rs, ds = np.zeros((n, 3)), np.zeros((n, 3))
    wide = np.zeros(n)
    f = R_KM / top_km
    metres = relief / (1000.0 * R_KM)
    sharp = np.broadcast_to(sharp, (n,))
    crease = np.broadcast_to(crease, (n,))
    for o in range(octaves):
        w = _weight(ctx, f)
        if w <= 0.0:
            break
        pt = oriented if o < oriented_octaves else plain
        c, q = _lattice(pt, f, o)
        v, g = gradient_noise_d(c, q, seed + o)
        g = g * f * metres[:, None]
        g = g - up * (g * up).sum(1, keepdims=True)
        a = amp * w / (1.0 + RELIEF_EROSION * (rs * rs).sum(1))
        rnd += a * v
        rs += a[:, None] * g
        x, gr, wr = v, g, np.full(n, w)
        if o == 0 and fold is not None:
            share = np.broadcast_to(fold_share, (n,))
            gf = fold[1] * metres[:, None]
            gf = gf - up * (gf * up).sum(1, keepdims=True)
            x = v + (fold[0] - v) * share
            gr = g + (gf - g) * share[:, None]
            wr = w + (fold_weight - w) * share
        e = np.maximum(crease, CREASE_ROUNDING * f / ctx.creasef)
        cr, dc = _rcrease(x, e)
        r = 1.0 - cr
        folded = 1.0 - 0.5 * np.broadcast_to(fold_share, (n,)) * np.clip(fold_weight, 0.0, 1.0) if o in (1, 2) else 1.0
        a = 1.7 * amp * wr * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * (ds * ds).sum(1))
        rid += a * (r - 0.5 * (1.0 - MEAN_BILLOW[True]))
        ds += (a * -dc)[:, None] * gr
        chain = np.clip(0.3 + 1.2 * r, 0.0, 1.0)
        if o < wide_octaves:
            wide = rnd + (rid - rnd) * sharp
        f *= RELIEF_LACUNARITY
        amp *= 0.5
    slope = rs + (ds - rs) * sharp[:, None]
    if wide_octaves:
        return rnd + (rid - rnd) * sharp, slope, wide
    return rnd + (rid - rnd) * sharp, slope


def _noise_d(ctx, p, km, seed):
    """ReliefNoiseD (Relief.hlsli): one octave in deviations, (value, gradient per radian (n, 3))."""
    f = R_KM / km
    w = _weight(ctx, f)
    if w <= 0.0:
        return np.zeros(len(p)), np.zeros((len(p), 3))
    c, q = _lattice(p, f, 0)
    v, g = gradient_noise_d(c, q, seed)
    return w * v / SIGMA, w * g * f / SIGMA


def _fold(ctx, p, along, along_gradient):
    """ReliefFold (Relief.hlsli): (value, gradient per radian (n, 3)), weight (n,)."""
    pi = math.pi
    w1, g1 = _noise_d(ctx, p, RELIEF_FOLD[2], _rseed(8))
    w2, g2 = _noise_d(ctx, p, RELIEF_FOLD[2] / 3.0, _rseed(8) + 2)
    scale = RELIEF_FOLD[1] * RELIEF_FOLD[0] / 1.118
    shift, shift_g = (w1 + 0.5 * w2) * scale, (g1 + 0.5 * g2) * scale
    z, zg = _noise_d(ctx, p, RELIEF_FOLD_SETS[1], _rseed(8) + 3)
    u = np.clip(0.5 + 0.6 * z, 0.0, 1.0)
    st = u * u * (3.0 - 2.0 * u)
    st_g = np.where((u > 0.0) & (u < 1.0), 3.6 * u * (1.0 - u), 0.0)[:, None] * zg
    k1 = pi / RELIEF_FOLD[0]
    k2 = k1 / RELIEF_FOLD_SETS[0]
    x = along + shift
    dx = along_gradient + shift_g
    s1, c1 = np.sin(k1 * x), np.cos(k1 * x)
    s2, c2 = np.sin(k2 * x), np.cos(k2 * x)
    n = (1.0 - st) * s1 + st * s2
    m = np.sqrt((1.0 - st) ** 2 + st ** 2)
    dn = ((1.0 - st) * c1 * k1 + st * c2 * k2)[:, None] * dx + (s2 - s1)[:, None] * st_g
    dm = ((2.0 * st - 1.0) / m)[:, None] * st_g
    zs, _ = _noise_d(ctx, p, RELIEF_FOLD_SADDLES[1], _rseed(8) + 1)
    w_short, w_long = _weight(ctx, R_KM / RELIEF_FOLD[0]), _weight(ctx, R_KM / (RELIEF_FOLD[0] * RELIEF_FOLD_SETS[0]))
    weight = (w_short + (w_long - w_short) * st) * (1.0 + RELIEF_FOLD_SADDLES[0] * np.tanh(1.5 * zs))
    a = 0.5 * (1.0 + MEAN_BILLOW[True]) * 0.5 * pi
    return (a * n / m, a * (dn / m[:, None] - (n / (m * m))[:, None] * dm)), weight


def _coast_noise(ctx, p, gain, rias, seed):
    """ReliefCoastNoise (Relief.hlsli): unit deviation; and its RELIEF_BARRIER_FORM.w widest octaves, their rias rounded."""
    mean_abs = 0.5 * (1.0 + MEAN_BILLOW[True])
    dev_abs = math.sqrt(SIGMA * SIGMA - mean_abs * mean_abs)
    f, total, amp = R_KM / RELIEF_COAST_NOISE[0], np.zeros(len(p)), np.ones(len(p))
    smooth = np.zeros(len(p))
    for o in range(int(RELIEF_COAST_NOISE[1])):
        w = _weight(ctx, f)
        if w <= 0.0:
            break
        c, q = _lattice(p, f, o)
        v = _gradient(_corner_hashes(c), q, seed + o, True)
        valley = (_crease(ctx, v, f) - mean_abs) * (SIGMA / dev_abs)
        share = rias if o > 0 else 0.0
        total += amp * w * (v + (valley - v) * share)
        if o < RELIEF_BARRIER_FORM[3]:
            wide = (_rcrease(v, 0.5 * SIGMA)[0] - mean_abs) * (SIGMA / dev_abs)
            smooth += amp * w * (v + (wide - v) * share)
        f *= 2.2
        amp = amp * gain
    norm = SIGMA * np.sqrt((1.0 - (gain * gain) ** RELIEF_COAST_NOISE[1]) / (1.0 - gain * gain))
    return total / norm, smooth / norm


def _sea_profile(x, w, cell_km, ground, amplitude, fan):
    """ReliefSeaProfile: two dry cells or submerged; flat core, Gaussian flanks, the whole profile's area kept."""
    sqrt_pi = 1.7724538509
    head = np.log(np.maximum(amplitude / np.maximum(-ground, 1e-20), 1.0))
    kept = w * np.minimum(np.sqrt(head), 0.5 * sqrt_pi * (1.0 + fan) * head)
    core = np.where((ground < 0.0) & (amplitude > 0.0), np.maximum(2.0 * cell_km - kept, 0.0), 0.0)
    amplitude = amplitude / (1.0 + 2.0 * core / (sqrt_pi * w * (1.0 + fan)))
    u = np.maximum(np.abs(x) - core, 0.0) / w
    g = np.exp(-u * u)
    g = g + np.where(x > 0.0, fan * (np.exp(-u * u / 9.0) - g), 0.0)
    return amplitude * g


def _terraces(h, step, slope, cell_km):
    x = h / step
    k = np.floor(x)
    drawn = (_mix((k.astype(np.int64) & 0xFFFFFFFF).astype(np.uint32) + np.uint32((PLANET_SEED * 0x9E3779B1) & 0xFFFFFFFF))
             >> np.uint32(8)).astype(np.float64) / 16777216.0
    mesh = 2000.0 * cell_km * slope / step
    riser = np.clip(np.maximum(RELIEF_RISER[0] + (RELIEF_RISER[1] - RELIEF_RISER[0]) * drawn, mesh), 0.0, 1.0)
    shift = np.clip(np.maximum(0.5 * (RELIEF_RISER[0] + RELIEF_RISER[1]), mesh), 0.0, 1.0)
    t = np.clip((x - k - (1.0 - riser)) / np.maximum(riser, 1e-9), 0.0, 1.0)
    return (k + t * t * (3.0 - 2.0 * t) + 0.5 * (1.0 - shift)) * step


def _relief(ctx, p, valleys=True):
    p = np.asarray(p, np.float64)
    cell_km = _cell_km(ctx)
    warped = turbulence(ctx, p, R_KM / RELIEF_WARP_TOP, RELIEF_WARP / (SIGMA * R_KM), RELIEF_WARP_OCTAVES, _rseed(0))
    m = tectonic_fields(warped)
    forms, sharp, side = m[0], m[1], m[2]
    h = forms[:, 0].copy()
    axis_km = np.abs(side[:, 0]) + (sharp[:, 0] - np.abs(side[:, 0])) * _smooth(25.0, 60.0, sharp[:, 0])
    rift = _smooth(-2500.0, -1000.0, h)
    segment = np.zeros(len(p))
    f = R_KM / RELIEF_SEGMENTS[0]
    wf = _weight(ctx, f)
    sel = (sharp[:, 1] > 1.0) | (np.abs(sharp[:, 2]) > 1.0)
    if wf > 0.0 and sel.any():
        c, q = _lattice(p[sel], f, 0)
        segment[sel] = wf * _gradient(_corner_hashes(c), q, _rseed(6), True)
    tr = sharp[:, 1] > 1.0
    w, depth = _width(RELIEF_TRENCH[0], cell_km, sharp[:, 1] * (1.0 + RELIEF_SEGMENTS[1] * segment))
    fl = RELIEF_TRENCH[1]
    h -= np.where(tr, depth * np.exp((fl - np.sqrt(axis_km ** 2 + fl * fl)) / w), 0.0)
    dv = np.abs(sharp[:, 2]) > 1.0
    w, valley = _width(RELIEF_RIDGE_AXIS, cell_km, sharp[:, 2] * (1.0 + RELIEF_SEGMENTS[2] * segment))
    wall, graben = _width(RELIEF_GRABEN[1], cell_km, sharp[:, 2] * (1.0 + RELIEF_SEGMENTS[1] * segment))
    v1 = valley * np.exp(-axis_km ** 2 / (w * w))
    v2 = graben * (1.0 - _smooth(RELIEF_GRABEN[0] - wall, RELIEF_GRABEN[0] + wall, axis_km))
    h += np.where(dv, v1 + (v2 - v1) * rift, 0.0)
    sh = sharp[:, 3] > 1.0
    w, depth = _width(RELIEF_TRANSFORM[0] + (RELIEF_TRANSFORM[1] - RELIEF_TRANSFORM[0]) * rift, cell_km, sharp[:, 3])
    h -= np.where(sh, depth * np.exp(-axis_km ** 2 / (w * w)), 0.0)

    # The coasts: the level moved near the shore; on the flat coasts, barriers.
    coast_slope = np.maximum(np.linalg.norm(m["forms_gradient"], axis=1) / R_KM, RELIEF_COAST_SLOPE[0])
    rocky = _smooth(RELIEF_COAST_SLOPE[1], RELIEF_COAST_SLOPE[2], coast_slope)
    shore = h / coast_slope
    smooth = shore  # the smooth shore, the barriers': without the coast's and the detail's finer octaves
    near = np.exp(-shore * shore / RELIEF_COAST[2] ** 2 - h * h / RELIEF_COAST[3] ** 2)
    sel = near > 1e-3
    if sel.any():
        ps, rk, hs, ss = p[sel], rocky[sel], h[sel], coast_slope[sel]
        gain = RELIEF_COAST_NOISE[2] + (RELIEF_COAST_NOISE[3] - RELIEF_COAST_NOISE[2]) * rk
        rias = RELIEF_RIAS[1] + (RELIEF_RIAS[0] - RELIEF_RIAS[1]) * rk
        n, n0 = _coast_noise(ctx, ps, gain, rias, _rseed(7))
        moved = near[sel] * ss * (RELIEF_COAST[1] + (RELIEF_COAST[0] - RELIEF_COAST[1]) * rk)
        smooth = shore.copy()
        smooth[sel] = (hs + moved * n0) / ss
        hs = hs + moved * n
        sh_km = hs / ss
        h = h.copy()
        h[sel] = hs
        shore = shore.copy()
        shore[sel] = sh_km
    large = h.copy()
    # The volcanoes' edifices, on the large forms; their young flanks quiet the detail.
    volc, quiet_v, volcanic, fin = volcano_edifices(ctx, p)
    h = h + volc

    relief, youth, strata = forms[:, 1] * (1.0 - quiet_v), np.clip(forms[:, 2], 0.0, 1.0), forms[:, 3]
    plain = p
    bent = turbulence(ctx, plain, R_KM / RELIEF_DETAIL_WARP[0], RELIEF_DETAIL_WARP[1] / (SIGMA * R_KM), 3, _rseed(4))
    reach = RELIEF_ORIENTATION[1]
    t = np.clip(side[:, 1] * (8.0 / (15.0 * reach)), -1.0, 1.0)  # the engine's quintic, levelling off at 15/8 reach
    lift = RELIEF_ORIENTATION[0] * reach * t * (1.875 + t * t * (-1.25 + 0.375 * t * t)) / R_KM
    oriented = bent * (1.0 + lift)[:, None]
    mountains = _smooth(300.0, 1200.0, relief)
    crease = RELIEF_OLD_CREASE * (1.0 - youth)
    fold_share = (RELIEF_FOLD[3] * (1.0 - _smooth(RELIEF_FOLD_REACH[0], RELIEF_FOLD_REACH[1], side[:, 1])) * mountains
                  * _smooth(RELIEF_FOLD_REACH[2], RELIEF_FOLD_REACH[3], np.linalg.norm(m["orientation_gradient"], axis=1) / R_KM))
    fold, fold_weight = None, 0.0
    if (fold_share > 0.0).any():
        fold, fold_weight = _fold(ctx, plain, side[:, 1], m["orientation_gradient"])
    quiet = 1.0 + (RELIEF_COAST_QUIET[0] - 1.0) * (1.0 - rocky) * np.exp(-shore * shore / RELIEF_COAST_QUIET[1] ** 2)
    d, slope, wide = detail(ctx, oriented, plain, RELIEF_ORIENTED_OCTAVES, RELIEF_DETAIL_TOP, RELIEF_OCTAVES, relief * quiet,
                            mountains, crease, _rseed(1), fold, np.where(fold_share > 0.0, fold_share, 0.0), fold_weight,
                            int(RELIEF_BARRIER_FORM[3]))
    h = h + relief * quiet * d
    smooth = smooth + relief * quiet * wide / coast_slope
    s = np.linalg.norm(slope, axis=1)
    land = _smooth(-20.0, 60.0, h)
    mesas = np.clip(2.0 * strata, 0.0, 1.0) * land
    badlands = np.clip(-2.0 * strata, 0.0, 1.0) * land * quiet
    if (mesas > 0.0).any():
        sel = mesas > 0.0
        tb, ts = detail(ctx, plain[sel], plain[sel], 0, RELIEF_MESAS[1], int(RELIEF_MESAS[2]),
                        np.full(sel.sum(), RELIEF_MESAS[0]), 0.0, 0.0, _rseed(5))
        hm = h[sel] + mesas[sel] * RELIEF_MESAS[0] * tb
        sm = np.linalg.norm(slope[sel] + mesas[sel, None] * ts, axis=1)
        h[sel] = hm + (_terraces(hm, RELIEF_MESA_STEP, sm, cell_km) - hm) * mesas[sel]
    if (badlands > 0.0).any():
        sel = badlands > 0.0
        b, _ = detail(ctx, plain[sel], plain[sel], 0, RELIEF_BADLANDS[1], int(RELIEF_BADLANDS[2]),
                      np.full(sel.sum(), RELIEF_BADLANDS[0]), 1.0, 0.0, _rseed(2))
        h[sel] += badlands[sel] * RELIEF_BADLANDS[0] * b
    # The flat coasts' barriers, along the smooth shore: arcs offshore between inlets, recurved toward them, a smooth beach,
    # low dunes and washover fans behind. Raised from the relief beneath them, their crests whole:
    # from the smooth level, fine coast noise cut them to the sea. Faded over the first half metre of dry land.
    bar = (near > 1e-3) & (rocky < 1.0) & (h < 0.5) & (np.abs(smooth + RELIEF_BARRIER[0]) < 10.0 * max(RELIEF_BARRIER[1], 2.0 * cell_km))
    if bar.any():
        pb, hb = p[bar], h[bar]
        fp, fi, fd = R_KM / RELIEF_BARRIER_GAPS[0], R_KM / RELIEF_BARRIER_GAPS[1], R_KM / RELIEF_BARRIER_FORM[2]
        c, q = _lattice(pb, fp, 0)
        patch = _weight(ctx, fp) * _gradient(_corner_hashes(c), q, _rseed(7) + 16, True) / SIGMA
        c, q = _lattice(pb, fi, 0)
        a = np.abs(_weight(ctx, fi) * _gradient(_corner_hashes(c), q, _rseed(7) + 17, True) / SIGMA)
        c, q = _lattice(pb, fd, 0)
        dunes = np.clip(_weight(ctx, fd) * _gradient(_corner_hashes(c), q, _rseed(7) + 18, True) / SIGMA, -1.0, 1.0)
        t = np.clip(a / 0.8, 0.0, 1.0)
        arch = t * (2.0 - t)
        over = 2.5 * (0.5 - RELIEF_BARRIER[3])
        presence = ((1.0 - rocky[bar]) * _smooth(over - 0.1, over + 0.1, patch)
                    * _smooth(RELIEF_BARRIER_FORM[1], 2.0 * RELIEF_BARRIER_FORM[1], a) * (1.0 - _smooth(0.0, 0.5, hb)))
        wb, lift = _width(RELIEF_BARRIER[1] * (0.6 + 0.4 * arch), cell_km,
                          np.maximum(RELIEF_BARRIER[2] * (0.75 + 0.25 * arch) * (1.0 + 0.4 * dunes) - hb, 0.0))
        x = smooth[bar] + RELIEF_BARRIER[0] * (1.0 - RELIEF_BARRIER_FORM[0] * (1.0 - arch))
        h[bar] = hb + _sea_profile(x, wb, cell_km, hb, presence * lift, np.clip(-dunes, 0.0, 1.0) / 3.0)
    h = volcano_finish(ctx, p, h, fin)
    norivers = h.copy()  # no valley is carved: the rivers will be the level 0's
    rough = 0.1 + 0.25 * _smooth(50.0, 400.0, relief) + 0.15 * _smooth(400.0, 1500.0, relief)
    rough = rough + (1.0 - rough) * youth * _smooth(500.0, 1500.0, relief)
    rough = rough + (0.6 - rough) * np.maximum(mesas, badlands)

    def cap(x):
        return np.where(x > RELIEF_HIGHEST[0], RELIEF_HIGHEST[0] + RELIEF_HIGHEST[1] * np.tanh((x - RELIEF_HIGHEST[0]) / RELIEF_HIGHEST[1]), x)
    return dict(elev=cap(h), norivers=cap(norivers), large=large, volcanoes=volc, volcanic=volcanic, relief=relief,
                youth=youth, strata=strata,
                axis=sharp[:, 0], trench=sharp[:, 1], divergent=sharp[:, 2], shear=sharp[:, 3], roughness=rough)


def elevation(ctx, p, extra=False, valleys=True):
    """Elevation (m) of the unit vectors p (n, 3); with extra, the dictionary of the parts: elev, norivers (without the
    valleys), large (the large forms, sharp profiles included), volcanoes (their edifices) and volcanic (the fresh
    volcanic ground), relief, youth, strata, the boundary's fields, roughness."""
    d = _relief(ctx, p, valleys)
    return d if extra else d["elev"]


# --- Utilities, unrelated to the noise. ---
def window(center, size_m, n):
    """n x n points on the sphere, a square of size_m around center, rows north to south, columns west to east."""
    c = np.asarray(center, np.float64)
    c = c / np.linalg.norm(c)
    east = np.cross(c, [0.0, 1.0, 0.0])
    east = east / np.linalg.norm(east) if np.linalg.norm(east) > 1e-9 else np.array([1.0, 0.0, 0.0])
    north = np.cross(east, c)
    s = ((np.arange(n) + 0.5) / n - 0.5) * size_m / R
    u, v = np.meshgrid(s, -s)
    p = c + u.reshape(-1, 1) * east + v.reshape(-1, 1) * north
    return p / np.linalg.norm(p, axis=1, keepdims=True)


def latlon(nlat, nlon):
    """Cell centres of a latitude-longitude grid, rows from north to south, longitudes from -180 to 180."""
    lat = np.radians(np.linspace(90.0 - 90.0 / nlat, -90.0 + 90.0 / nlat, nlat))
    lon = np.radians(np.linspace(-180.0 + 180.0 / nlon, 180.0 - 180.0 / nlon, nlon))
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    la, lo = la.reshape(-1), lo.reshape(-1)
    return np.stack([np.cos(la) * np.cos(lo), np.sin(la), np.cos(la) * np.sin(lo)], 1)


def tangent_basis(p):
    """Two unit tangents (n, 3) at each unit vector p, orthogonal to each other."""
    p = np.asarray(p, np.float64)
    a = np.where(np.abs(p[:, 1:2]) < 0.9, [[0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0]])
    t1 = np.cross(p, a)
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    return t1, np.cross(p, t1)


def move(p, t, metres):
    """p moved along its tangent t by metres on the sphere."""
    a = np.asarray(metres, np.float64)[:, None] / R
    return p * np.cos(a) + t * np.sin(a)

if __name__ == "__main__":
    # The crease excess is continuous; the derivative noise's gradient is its value's, by finite differences; its value
    # is the plain noise's.
    assert abs(_excess(SIGMA * (1 - 1e-9)) - _excess(SIGMA)) < 1e-6
    rng = np.random.default_rng(1)
    c = rng.integers(-50, 50, (200, 3))
    q = rng.random((200, 3))
    v, g = gradient_noise_d(c, q, 7)
    assert np.allclose(v, _gradient(_corner_hashes(c), q, 7, True), atol=1e-9)
    for a in range(3):
        e = np.zeros(3)
        e[a] = 1e-6
        assert np.allclose((gradient_noise_d(c, q + e, 7)[0] - gradient_noise_d(c, q - e, 7)[0]) / 2e-6, g[:, a], atol=1e-5)
    # The terraces are continuous and keep the mean over many steps.
    h = np.linspace(0.0, 14000.0, 2000001)
    tr = _terraces(h, 140.0, 0.0, 0.0)
    assert np.abs(np.diff(tr)).max() < 1.0 and abs(tr.mean() - h.mean()) < 5.0, (np.abs(np.diff(tr)).max(), tr.mean() - h.mean())
    # The climate map, when the engine has written it: its texels read back at their centres; continuous across a face's
    # edge, a step of 1 km there moving the precipitation by a fraction of its change over a texel.
    if os.path.exists(CLIMATE_CACHE.format(seed=PLANET_SEED)):
        cells, n = climate_map()
        f, j, i = rng.integers(0, 6, 50), rng.integers(0, n, 50), rng.integers(0, n, 50)
        d = _FN[f] + ((i + 0.5) * 2.0 / n - 1.0)[:, None] * _FS[f] + ((j + 0.5) * 2.0 / n - 1.0)[:, None] * _FT[f]
        assert np.allclose(climate(d / np.linalg.norm(d, axis=1, keepdims=True))["precipitation"], cells[f, j, i, 0], rtol=1e-4)
        t = np.linspace(-0.9, 0.9, 200)
        edge = np.stack([np.ones_like(t), t, np.full_like(t, 1.0 - 1e-7)], 1)  # the edge of faces 0 and 4
        def across(metres):
            a, b = edge.copy(), edge.copy()
            a[:, 2] -= 0.5 * metres / R
            b[:, 2] += 0.5 * metres / R
            return np.abs(climate(a)["precipitation"] - climate(b)["precipitation"])
        jump, change = across(1e3), across(50e3)
        assert (jump <= 0.1 * change + 1.0).all(), (jump - 0.1 * change).max()
    print("ok")
