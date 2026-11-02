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
# the rock's, relative (docs/spec-relief-tectonique.md, the level 0). The erosion (docs/spec-erosion.md): the level 0 read
# from the engine's cache, x64/Release/erosion-<seed>.bin (EXOLUNE_EROSION overrides it), erosion_map, erosion_valleys;
# elevation(ctx, p, valleys=True) carves its valleys and gullies.
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
EROSION_JITTER, EROSION_REACH = 0.3, 0.6
EROSION_FLOOR = (2.0, 0.002, 15.0)
EROSION_WALLS = (0.25, 0.65)
EROSION_GLACIER, EROSION_GLACIER_WALLS = (600.0, 0.4, 0.3, 22.0), 0.85
EROSION_SMOOTH, EROSION_COARSE = 60.0, 20.0
EROSION_GULLY_FIRST, EROSION_GULLY_SHARE, EROSION_GULLY, EROSION_GULLY_PERIODS = 2, 0.85, (0.02, 0.15, 0.1), 2
EROSION_GULLY_FORK = 0.3
EROSION_GULLY_CRITICAL = 1.25
EROSION_GULLY_ROCK = 2.74747742
EROSION_GULLY_MANTLE = (0.3, 1.0)
EROSION_GULLY_ROCK_RELIEF = (600.0, 1400.0)
EROSION_GLACIAL_SHARPEN = 0.2
EROSION_GLACIAL_BAND = 600.0
EROSION_WARP, EROSION_WALL_RELIEF = (40.0, 2.0), 0.35
EROSION_DELTA, EROSION_DELTA_DISCHARGE, EROSION_DELTA_FRONT = (60.0, 0.3, 1.6, 3.0), 300.0, 0.05
EROSION_FAN = (120.0, 0.2, 0.03)
EROSION_CLIFF_RETREAT = (1.0, 1.2, 3.0, 0.45)
EROSION_CLIFF_NOISE = 2.4
EROSION_CLIFF_BAY = (-12.0, -6.0)
EROSION_CLIFF_REACH = (1.0, 0.5, 8.0)
EROSION_CLIFF_SEA = (50.0, 0.25)
EROSION_CLIFF_HEIGHT = (8.0, 400.0)
EROSION_CLIFF_SLOPE_KM = 9.0
EROSION_CLIFF_FACE = 0.1
EROSION_CLIFF_SCREE = (0.7002, 0.22)
EROSION_CLIFF_PLATFORM = (-1.0, 0.02, 4.0)
EROSION_CLIFF_STACK = (0.065, 0.8, 1.4)
EROSION_CLIFF_WAVES = (0.28, 1.6)
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
    # Convert the rock per texel, before interpolation, as TectonicFace. The GPU has no erodibility slice.
    out["erodibility"] = np.zeros(len(q))
    if 0 in slices and 2 in slices:
        resistance = np.array([1.0, 0.6, 1.0, 1.6, 0.45, 0.25])
        for j in range(4):
            yy = np.clip(iy + j, 0, w - 1)
            for i in range(4):
                xx = np.clip(ix + i, 0, w - 1)
                rock = np.minimum((tex[face, 2, yy, xx, 2] + 0.5).astype(int) % 8, 5)
                out["erodibility"] += wy[:, j] * wx[:, i] * resistance[rock] * (1.0 + np.clip(-tex[face, 0, yy, xx, 3], 0.0, 1.0))
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
        sums["erodibility"][sel] += w[sel] * o["erodibility"]
        for name in grads:
            grads[name][sel] += w[sel, None] * g[name]
        total[sel] += w[sel]
    out = {s: sums[s] / total[:, None] for s in slices}
    out["erodibility"] = sums["erodibility"] / total
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

# --- The erosion (MyPlanetEngine/Erosion.hlsli, Erosion.h), the level 0 read from the engine's cache. ---
# The engine computes its level 0 at startup (Erosion.cpp) and writes it beside its executable, erosion-<seed>.bin: a
# header, then two 32-bit words per cell of the tectonic map's cube, face by face, row by row (Erosion.h). The positions
# the shader computes in floats are computed here in float32: a node moved by 1e-7 radian moves a valley by 0.6 m.
EROSION_CACHE = os.environ.get("EXOLUNE_EROSION", os.path.join(_REPO, "x64", "Release", "erosion-{seed}.bin"))
_erosion = {}
_basins = {}
EROSION_WATER = 1.0
EROSION_RIVER_SHAPE = (2.4, 0.35, 0.3, 20.0)
EROSION_LAKE_TRANSITION = 2000.0
_HAS_RECEIVER, _LAKE, _SEA, _FAN_APEX, _MOUTH = 8, 1 << 12, 1 << 13, 1 << 14, 1 << 15
_F32 = np.float32


def erosion_map(seed=None):
    """The level 0 of the seed: (words (6 n^2, 2) uint32, n)."""
    seed = PLANET_SEED if seed is None else seed
    if seed not in _erosion:
        path = EROSION_CACHE.format(seed=seed)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path}: run the engine once with this seed, it writes its level 0 there")
        raw = open(path, "rb").read()
        assert raw[:8] in (b"EXOEROS2", b"EXOEROS3"), f"{path}: an older level 0, run the engine again"
        s, n = (int(x) for x in np.frombuffer(raw[8:16], np.uint32))
        data = np.frombuffer(raw[24:], np.uint32).reshape(-1, 2)
        _erosion[seed] = (data[:6*n*n], n)
        _basins[seed] = data[6*n*n:] if raw[:8] == b"EXOEROS3" else np.zeros_like(data)
    return _erosion[seed]


def erosion_basins(seed=None):
    seed = PLANET_SEED if seed is None else seed
    erosion_map(seed)
    return _basins[seed]


def erosion_river_size(q):
    a,b,c,d = EROSION_RIVER_SHAPE
    return np.maximum(1.,a*np.sqrt(q)), np.clip(b*np.power(q,c),.15,d)*_smooth(.05,.5,q)


def erosion_river_cut(d,q,radius):
    width,depth = erosion_river_size(q)
    lo,hi = np.clip((d-radius)/width,-1.,1.),np.clip((d+radius)/width,-1.,1.)
    primitive = lambda x: x*(1.+x*x*(-2./3.+x*x*.2))
    return EROSION_WATER*depth*width*(primitive(hi)-primitive(lo))/(2.*radius)


def erosion_river_profile(d,z,q,walls,radius):
    width,_ = erosion_river_size(q)
    tail0,tail1 = np.maximum(radius-abs(d-width),0.),np.maximum(radius-abs(-d-width),0.)
    rise = walls*(np.maximum(d-width,0.)+(tail0*tail0+tail1*tail1)/(4.*radius))
    return z+rise-erosion_river_cut(d,q,radius)


def _edirection(f, s, t):
    """ErosionDirection: face f's point (s, t), float32."""
    one = np.ones_like(s)
    table = [(one, -t, -s), (-one, -t, s), (s, one, t), (s, -one, -t), (s, -t, one), (-s, -t, -one)]
    d = np.empty(s.shape + (3,), _F32)
    for k, (x, y, z) in enumerate(table):
        m = f == k
        d[m, 0], d[m, 1], d[m, 2] = x[m], y[m], z[m]
    return d


def _elocate(d, n):
    """ErosionLocate in float32: the face and the texel coordinates."""
    d = d.astype(_F32)
    a = np.abs(d)
    fx = (a[:, 0] >= a[:, 1]) & (a[:, 0] >= a[:, 2])
    fy = ~fx & (a[:, 1] >= a[:, 2])
    face = np.where(fx, np.where(d[:, 0] > 0, 0, 1), np.where(fy, np.where(d[:, 1] > 0, 2, 3), np.where(d[:, 2] > 0, 4, 5)))
    ma = np.where(fx, a[:, 0], np.where(fy, a[:, 1], a[:, 2]))
    sc = np.where(fx, np.where(d[:, 0] > 0, -d[:, 2], d[:, 2]), np.where(fy, d[:, 0], np.where(d[:, 2] > 0, d[:, 0], -d[:, 0])))
    tc = np.where(fx, -d[:, 1], np.where(fy, np.where(d[:, 1] > 0, d[:, 2], -d[:, 2]), -d[:, 1]))
    x = np.stack([sc / ma, tc / ma], 1).astype(_F32)
    return face, ((x + _F32(1.0)) * _F32(0.5) * _F32(n) - _F32(0.5)).astype(_F32)


def _ecell(face, ij, n):
    """ErosionCell: the cell (face, i, j), beyond the face's edge the cell holding that point."""
    inside = (ij >= 0).all(1) & (ij < n).all(1)
    cell = (face * n + np.clip(ij[:, 1], 0, n - 1)) * n + np.clip(ij[:, 0], 0, n - 1)
    if not inside.all():
        o = ~inside
        st = ((ij[o].astype(_F32) + _F32(0.5)) * _F32(2.0) / _F32(n) - _F32(1.0)).astype(_F32)
        f2, x = _elocate(_edirection(face[o], st[:, 0], st[:, 1]), n)
        k = np.clip(np.floor(x + _F32(0.5)), 0, n - 1).astype(np.int64)
        cell[o] = (f2 * n + k[:, 1]) * n + k[:, 0]
    return cell


def _eneighbour(c, k, n):
    """ErosionNeighbour: neighbour k, row by row, the centre left out."""
    m = np.where(k < 4, k, k + 1)
    ij = np.stack([c % n + m % 3 - 1, c // n % n + m // 3 - 1], 1)
    return _ecell(c // (n * n), ij, n)


def _enode(c, n):
    """ErosionNode in float32: the cell's centre moved by its hash."""
    h = _mix((c.astype(np.int64) * 0x9E3779B1 + 0x632BE5AB & 0xFFFFFFFF).astype(np.uint32))
    jitter = (np.stack([h & 0xFFFF, h >> 16], 1).astype(_F32) / _F32(65535.0) - _F32(0.5)) * _F32(2.0 * EROSION_JITTER)
    st = ((np.stack([c % n, c // n % n], 1).astype(_F32) + _F32(0.5) + jitter) * _F32(2.0) / _F32(n) - _F32(1.0)).astype(_F32)
    d = _edirection(c // (n * n), st[:, 0], st[:, 1])
    return (d / np.sqrt((d * d).sum(1, keepdims=True))).astype(_F32)


def _eread(words, c):
    t = words[c]
    lv = (t[:, 0] & 0xFFFF).astype(np.float64) * 0.25 - 8192.0
    gr = (t[:, 0] >> 16).astype(np.float64) * 0.25 - 8192.0
    q = 2.0 ** (((t[:, 1] >> 16) & 255).astype(np.float64) / 8.0 - 8.0)
    i8 = (t[:, 1] >> 24).astype(np.float64)
    ice = np.where(i8 > 0, 2.0 ** ((i8 - 1.0) / 6.0 + 10.0), 0.0)
    return lv, gr, q, ice, t[:, 1].astype(np.int64)


def erosion_climate(d):
    """ErosionClimate: computed year's precipitation (m/yr), sea-level temperature (C)."""
    fields = climate(d)
    return 0.001 * fields["precipitation"], fields["temperature"]


def erosion_equilibrium_line(d):
    p, t = erosion_climate(d)
    summer = (-296.0 + np.sqrt(296.0 * 296.0 - 36.0 * (645.0 - 1000.0 * p))) / 18.0
    return (t - (summer - 8.0)) / 6.5e-3 - 900.0


def _gullies(p, f, across, seed):
    """ErosionGullies: the stripes (n,) and their gradient per cell of the octave (n, 3)."""
    c, q = _lattice(p, f / EROSION_GULLY_PERIODS, 0)
    hs = _corner_hashes(c)
    s = _fade(q, True)
    k = _seed_term(seed)
    re, im = np.zeros(len(p)), np.zeros(len(p))
    for i, h in enumerate(hs):
        corner = np.array([i & 1, (i >> 1) & 1, i >> 2], np.float64)
        phase = 2.0 * math.pi * (EROSION_GULLY_PERIODS * ((q - corner) * across).sum(1)
                                 + (_mix(h + k) >> np.uint32(8)).astype(np.float64) / 16777216.0)
        t = np.where(corner > 0.5, s, 1.0 - s)
        w = t[:, 0] * t[:, 1] * t[:, 2]
        re += w * np.cos(phase)
        im += w * np.sin(phase)
    m = np.maximum(np.hypot(re, im), EROSION_GULLY_FORK)
    amp = 0.5 * math.pi * 0.5 * (1.0 + MEAN_BILLOW[True])
    return amp * re / m, (-amp * im / m * 2.0 * math.pi)[:, None] * across


def _curve(a, b, c):
    """ErosionCurveDistance: (distance, parameter, nearest point) to the quadratic Bezier a, b, c relative to the point."""
    best, at, near = np.full(len(a), 1e30), np.zeros(len(a)), a.copy()
    prev = a
    for k in range(1, 5):
        t = k * 0.25
        s = 1.0 - t
        nxt = s * s * a + 2.0 * s * t * b + t * t * c
        e = nxt - prev
        u = np.clip(-(prev * e).sum(1) / np.maximum((e * e).sum(1), 1e-30), 0.0, 1.0)
        qq = prev + u[:, None] * e
        d = (qq * qq).sum(1)
        better = d < best
        best, at = np.where(better, d, best), np.where(better, (k - 1 + u) * 0.25, at)
        near = np.where(better[:, None], qq, near)
        prev = nxt
    bend = a - 2.0 * b + c
    for _ in range(4):
        q = (1.0-at)[:,None]**2*a + (2.0*(1.0-at)*at)[:,None]*b + (at*at)[:,None]*c
        tangent = 2.0*((1.0-at)[:,None]*(b-a)+at[:,None]*(c-b))
        denom = (tangent*tangent).sum(1)+2.0*(q*bend).sum(1)
        at = np.clip(at-np.clip((q*tangent).sum(1)/np.maximum(denom,1e-20),-.25,.25),0.,1.)
    near = (1.0-at)[:,None]**2*a + (2.0*(1.0-at)*at)[:,None]*b + (at*at)[:,None]*c
    best = (near*near).sum(1)
    for endpoint,t in ((a,0.),(c,1.)):
        distance = (endpoint*endpoint).sum(1)
        better = distance < best
        near = np.where(better[:,None],endpoint,near)
        at, best = np.where(better,t,at),np.minimum(best,distance)
    # Heads and outlets are straight runs with a repeated control; solve their parameter as well as their distance.
    head, outlet = (a == b).all(1), (b == c).all(1)
    straight = head | outlet
    e = c-a
    u = np.clip(-(a*e).sum(1)/np.maximum((e*e).sum(1),1e-30),0.,1.)
    point = a+u[:,None]*e
    at = np.where(straight,np.where(head,np.sqrt(u),1.-np.sqrt(1.-u)),at)
    near = np.where(straight[:,None],point,near)
    best = np.where(straight,(point*point).sum(1),best)
    return np.sqrt(best), at, near


def _erosion_box_square_excess(x, radius):
    tail = np.maximum(radius - np.abs(x), 0.)
    cap = tail**3 / (6. * radius)
    return np.where(x >= 0., radius*radius/3. - cap, cap), tail*tail/(2. * radius)


def _erosion_profile(d, z, q, ice, slope, walls, depth, wide, widest, section=None):
    """ErosionProfile: (surface, floor share, glacier, rise).

    depth is unused, retained only for comparison with historical CPU references.
    """
    floor = np.minimum(EROSION_FLOOR[0] * np.sqrt(q) * np.clip(EROSION_FLOOR[1] / np.maximum(slope, 1e-6), 1.0, EROSION_FLOOR[2]), widest)
    floor = np.minimum(np.maximum(floor,erosion_river_size(q)[0]),widest)
    glacier = np.clip(np.log2(np.maximum(ice, 1.0)) - EROSION_GLACIER[3], 0.0, 1.0)
    trough = np.clip(EROSION_GLACIER[0] * (np.maximum(ice, 1.0) / 1e8) ** EROSION_GLACIER[1], 150.0, 1500.0)
    curvature = EROSION_GLACIER[2] / trough
    shoulder = EROSION_GLACIER_WALLS / (2.0 * curvature)
    if section is not None:
        section.update(floor_width=floor, curvature=curvature)
    # Exact local mean; network depth never scales the profile or the physical floor mask.
    radius = np.maximum(0.5 * wide, CREASE_MIN_CELL)
    right_bank, left_bank = d-floor, -d-floor
    right_tail, left_tail = np.maximum(radius-abs(right_bank),0.), np.maximum(radius-abs(left_bank),0.)
    fluvial = walls * (np.maximum(d-floor,0.)+(right_tail**2+left_tail**2)/(4.*radius))
    r_f = walls*(np.clip(.5+.5*right_bank/radius,0.,1.)-np.clip(.5+.5*left_bank/radius,0.,1.))
    u = np.minimum(d, shoulder)
    right, right_derivative = _erosion_box_square_excess(d-shoulder,radius)
    left, left_derivative = _erosion_box_square_excess(-d-shoulder,radius)
    glacial = (curvature*u*u+EROSION_GLACIER_WALLS*np.maximum(d-shoulder,0.)
               +curvature*np.maximum(radius*radius/3.-right-left,0.))
    r_g = 2.*curvature*u-curvature*(right_derivative-left_derivative)
    surface = z+fluvial+(glacial-fluvial)*glacier
    rise = r_f+(r_g-r_f)*glacier
    flat_river = 1.0-_smooth(floor,floor+np.maximum(floor,200.),d)
    flat = flat_river+(1.0-_smooth(.25*trough,.7*trough,d)-flat_river)*glacier
    return surface, flat, glacier, rise


def erosion_valleys(p, cell_km, walls, seed=None):
    """ErosionValleys: project the warped directions onto the sphere.
    Returns surface, gradient, floor, level, glacier, incision, deposit."""
    squared = (p * p).sum(1)
    inverse = (np.float32(1.0) / np.sqrt(squared.astype(np.float32))).astype(np.float64)
    inverse *= 1.5 - 0.5 * squared * inverse * inverse
    p = p * inverse[:, None]
    words, n = erosion_map(seed)
    N = len(p)
    radius, cell_m = R, 2.0 * R / n
    face, x = _elocate(p, n)
    origin = np.floor(x).astype(np.int64) - 1
    lake_level = np.zeros(N)
    band = min(EROSION_LAKE_TRANSITION/cell_m,.5)
    blend = _smooth(.5-band,.5+band,x-np.floor(x))
    for tap in range(4):
        offset = np.array([tap&1,tap>>1])
        c = _ecell(face,np.floor(x).astype(np.int64)+offset,n)
        basin = erosion_basins(seed)[c]
        weight = np.where(offset,blend,1.-blend).prod(axis=1)
        lake_level += weight*np.where((basin[:,1]!=0)&(EROSION_WATER>0),np.maximum(0.,(basin[:,0]&65535)*.25-8192.),0.)
    v = dict(surface=np.full(N, 1e9), gradient=np.zeros((N, 3)), floor=np.zeros(N), level=np.zeros(N), glacier=np.zeros(N),
             incision=np.zeros(N), deposit=np.full(N, -1e9), channel_bed=np.full(N,1e9),channel_surface=np.full(N,1e9),
             lake_level=lake_level,
             flow=np.zeros((N,3)))
    v["links"] = [dict(d=np.zeros(N), z=np.full(N,1e9), floor_width=np.zeros(N),
                       curvature=np.zeros(N), glacier=np.zeros(N)) for _ in range(2)]
    v["walls"] = np.broadcast_to(walls, (N,))
    v["box_radius"] = max(1000.0 * cell_km, CREASE_MIN_CELL)
    second_candidate = np.full(N, 1e9)
    guide_surface = np.full(N, 1e9)
    wide = 2000.0 * cell_km
    walls = np.broadcast_to(walls, (N,))
    pf = p.astype(_F32)
    rest = (p - pf.astype(np.float64)).astype(_F32)

    def rel(x):  # a float32 position less the point, as the shader: (x - pf) - rest
        return ((x.astype(_F32) - pf) - rest).astype(np.float64)
    for k in range(16):
        r = _ecell(face, origin + np.array([k & 3, k >> 2]), n)
        lv, gr, q, ice, bits = _eread(words, r)
        pr32 = _enode(r, n)
        outlet = (bits & (_SEA | _LAKE)) != 0
        has = (bits & _HAS_RECEIVER) != 0
        rr = _eneighbour(r, bits & 7, n)
        lv2, gr2, q2, ice2, _ = _eread(words, rr)
        b = rel(pr32)
        mid = (_F32(0.5) * ((pr32 - pf) + (_enode(rr, n) - pf)) - rest).astype(np.float64)
        c = np.where(has[:, None], mid, b)
        z_down = np.where(has, 0.5 * (lv + lv2), lv)
        q_down = np.where(has, np.sqrt(q * q2), q)
        ice_down = np.where(has, 0.5 * (ice + ice2), ice)
        ground_down = np.where(has, 0.5 * (gr + gr2), gr)
        near_node = np.linalg.norm(b, axis=1) * radius <= (EROSION_REACH + 1.15) * cell_m
        # The deposits: deltas at the mouths, fans at the mountain front.
        dep = near_node & ((bits & (_MOUTH | _FAN_APEX)) != 0) & (ice <= 0.0)
        if dep.any():
            delta = (bits & _MOUTH) != 0
            apex = np.where(delta[:, None], c, b)
            ahead = c - b
            ahead = ahead / np.maximum(np.linalg.norm(ahead, axis=1, keepdims=True), 1e-30)
            along = -(apex * ahead).sum(1) * radius
            across = np.linalg.norm(-apex + (apex * ahead).sum(1, keepdims=True) * ahead, axis=1) * radius
            size = np.minimum(np.where(delta, EROSION_DELTA[0], EROSION_FAN[0]) * np.sqrt(q), 0.25 * cell_m)
            back = np.where(delta, EROSION_DELTA[1], EROSION_FAN[1])
            e = np.hypot(along / np.where(along > 0.0, size, back * size), across / (EROSION_DELTA[2] * size))
            fade = 1.0 - _smooth(0.2, 0.3, np.linalg.norm(apex, axis=1) * radius / cell_m)
            surface = np.where(delta, EROSION_DELTA[3] * (1.0 - e) - np.where(e > 1.0, EROSION_DELTA_FRONT * (e - 1.0) * size, 0.0),
                               lv - EROSION_FAN[2] * e * size - np.where(e > 1.0, (e - 1.0) * size, 0.0))
            ok = dep & (size > 10.0) & np.where(delta, q > EROSION_DELTA_DISCHARGE, True)
            v["deposit"] = np.where(ok, np.maximum(v["deposit"], -1e4 + (surface + 1e4) * fade), v["deposit"])
        inflows = (bits >> 4) & 255
        head = (inflows == 0) & ~outlet
        end = np.where(outlet[:, None], b, c)
        for kq in range(9):
            if kq < 8:
                sel = ((inflows >> kq) & 1) == 1
                if not sel.any():
                    continue
                qc = _eneighbour(r, np.full(N, kq), n)
                lq, gq, qq, iq, _ = _eread(words, qc)
                a = (_F32(0.5) * ((_enode(qc, n) - pf) + (pr32 - pf)) - rest).astype(np.float64)
                z_up, q_up, ice_up = 0.5 * (lq + lv), np.sqrt(qq * q), 0.5 * (iq + ice)
                ground_up = 0.5 * (gq + gr)
            else:
                sel = head
                a, z_up, q_up, ice_up = b, lv, q, ice
                ground_up = gr
            projected = [value-(value*pf).sum(1)[:,None]*pf for value in (a,b,end)]
            dist, t, near = _curve(*projected)
            d = dist * radius
            m = sel & near_node & (d < EROSION_REACH * cell_m)
            if not m.any():
                continue
            s0, z_end = 1.0 - t, np.where(outlet, lv, z_down)
            z = s0 * s0 * z_up + 2.0 * s0 * t * lv + t * t * z_end
            qt = 2.0 ** (s0*s0*np.log2(q_up)+2.*s0*t*np.log2(q)+t*t*np.log2(np.where(outlet,q,q_down)))
            it = s0*s0*ice_up+2.*s0*t*ice+t*t*np.where(outlet,ice,ice_down)
            tangent = 2.0 * (s0[:, None] * (b - a) + t[:, None] * (end - b))
            span = np.maximum(np.linalg.norm(tangent, axis=1), 1e-9) * radius
            water_slope = np.abs(2.0 * (s0 * (lv - z_up) + t * (z_end - lv))) / span
            water_slope = np.where(head,np.abs(z_end-lv)/np.maximum(np.linalg.norm(end-b,axis=1)*radius,1e-6),
                                   np.where(outlet,np.abs(lv-z_up)/np.maximum(np.linalg.norm(b-a,axis=1)*radius,1e-6),water_slope))
            ground = s0 * s0 * ground_up + 2.0 * s0 * t * gr + t * t * np.where(outlet, gr, ground_down)
            depth = np.maximum(ground - z, 0.0)
            section = {}
            surface, flat, glacier, rise = _erosion_profile(d, z, qt, it, water_slope, walls, depth, wide, 0.15 * cell_m, section)
            beyond = _smooth(0.35, 0.5, d / cell_m)
            s = surface + 1e4 * beyond
            guide = np.where(m,np.clip(0.5+0.5*(guide_surface-s)/EROSION_SMOOTH,0.,1.),0.)
            gradient = -rise[:,None]*near/np.maximum(np.linalg.norm(near,axis=1,keepdims=True),1e-12)
            v['gradient'] += guide[:,None]*(gradient-v['gradient'])
            guide_surface += guide*(s-guide_surface)-EROSION_SMOOTH*guide*(1.0-guide)
            low = m & (s < v["surface"])
            second = m & ~low & (s < second_candidate)
            for key, value in dict(d=d, z=z+1e4*beyond, glacier=glacier, **section).items():
                v["links"][1][key] = np.where(low, v["links"][0][key], np.where(second, value, v["links"][1][key]))
                v["links"][0][key] = np.where(low, value, v["links"][0][key])
            second_candidate = np.where(low, v["surface"], np.where(second, s, second_candidate))
            v["surface"] = np.where(low, s, v["surface"])
            v['level'] = np.where(low,z,v['level'])
            channel = erosion_river_profile(d,z,qt,walls,max(.5*wide,CREASE_MIN_CELL))+1e4*beyond
            wet = m & (EROSION_WATER>0) & (qt>.05)
            top = channel+erosion_river_cut(d,qt,max(.5*wide,CREASE_MIN_CELL))
            v['channel_surface'] = np.where(wet,np.minimum(v['channel_surface'],top),v['channel_surface'])
            wet_low = m & (EROSION_WATER>0) & (qt>.05) & (channel<v['channel_bed'])
            v['channel_bed'] = np.where(wet_low,channel,v['channel_bed'])
            width,water_depth = erosion_river_size(qt)
            speed = np.minimum(qt/np.maximum((16./15.)*width*water_depth,1e-3),4.)
            flow = tangent/np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-12)*speed[:,None]
            v['flow'] = np.where(wet_low[:,None],flow,v['flow'])
            near_axis = np.where(m, 1.0 - _smooth(0.1, 0.35, d / cell_m), 0.0)
            v["incision"] = np.maximum(v["incision"], depth * near_axis)
            v["glacier"] = np.maximum(v["glacier"], glacier * near_axis)
            v["floor"] = np.where(m, np.maximum(v["floor"], flat * (1.0 - beyond)), v["floor"])
    return v


def erosion_cut(coarse, surface, k):
    """ErosionCut: a bounded shoulder transition; k=0 reaches the profile without a degenerate smoothstep."""
    depth = np.maximum(coarse-surface,0.)
    t = depth/np.maximum(np.maximum(k,depth),1e-20)
    return coarse-depth*t*t*(3.-2.*t)


def _erosion_box_ramp(x, radius):
    tail = np.maximum(radius-np.abs(x),0.)
    return np.maximum(x,0.)+tail*tail/(4.*radius)


def _erosion_box_positive_square(x, radius):
    return np.maximum(x,0.)**2+_erosion_box_square_excess(x,radius)[0]


def _erosion_section_crossing(depth, f, s, c, walls, glacier):
    """ErosionSectionCrossing: where the mixed section rises `depth` above its level."""
    lo, hi = np.minimum(f,s), np.maximum(f,s)
    def rise(t):
        return (1.-glacier)*walls*np.maximum(t-f,0.)+glacier*(c*np.minimum(t,s)**2+EROSION_GLACIER_WALLS*np.maximum(t-s,0.))
    at = np.where(depth<=rise(lo),.5*lo,np.where(depth<=rise(hi),.5*(lo+hi),hi+1.))
    floor, trough = at<f, at<s
    a = np.where(trough,glacier*c,0.)
    b = np.where(trough,0.,glacier*EROSION_GLACIER_WALLS)+np.where(floor,0.,(1.-glacier)*walls)
    g = np.where(trough,0.,glacier*(c*s*s-EROSION_GLACIER_WALLS*s))-np.where(floor,0.,(1.-glacier)*walls*f)
    rest = np.maximum(depth-g,0.)
    return 2.*rest/np.maximum(b+np.sqrt(b*b+4.*a*rest),1e-20)


def erosion_clipped_section(link, ground, walls, radius):
    """Box mean of a physical section clipped to constant ground."""
    d, z, f = link['d'], link['z'], link['floor_width']
    c, glacier = link['curvature'], link['glacier']
    depth = np.maximum(ground-z,0.)
    c = np.maximum(c,1e-30)
    shoulder = EROSION_GLACIER_WALLS/(2.*c)
    u = np.minimum(d,shoulder)
    glacial = (c*u*u+EROSION_GLACIER_WALLS*np.maximum(d-shoulder,0.)
               +c*np.maximum(radius*radius/3.-_erosion_box_square_excess(d-shoulder,radius)[0]
                             -_erosion_box_square_excess(-d-shoulder,radius)[0],0.))
    fluvial = walls*(_erosion_box_ramp(d-f,radius)+_erosion_box_ramp(-d-f,radius))
    xg = _erosion_section_crossing(depth,f,shoulder,c,walls,glacier)
    xf = np.maximum(f,xg)
    excess_f = walls*(_erosion_box_ramp(d-xf,radius)+_erosion_box_ramp(-d-xf,radius))
    excess_g = 0.
    for x in (d,-d):
        ramp = _erosion_box_ramp(x-xg,radius)
        excess_g += np.where(xg>=shoulder,EROSION_GLACIER_WALLS*ramp,
                             c*(_erosion_box_positive_square(x-xg,radius)+2.*xg*ramp
                                -_erosion_box_positive_square(x-shoulder,radius)))
    mean = z+(fluvial-excess_f)+(glacial-excess_g-fluvial+excess_f)*glacier
    return np.where((ground<=z)|(link['curvature']<=0.),ground,np.minimum(np.maximum(mean,z),ground))


def erosion_carve(h, coarse, v, k):
    """Clip each link at the actual ground before applying the bounded cut."""
    detail = h-coarse
    tail = np.maximum(k-abs(detail),0.)
    spurs = np.maximum(detail,0.)+tail*tail/(4.*k)
    lift = spurs*(1.-v['floor'])
    ground = h-lift
    surface = np.minimum(*(erosion_clipped_section(link,ground,v['walls'],v['box_radius'])
                           for link in v['links']))+lift
    return erosion_cut(h,surface,k*(1.-v['floor']))


def erosion_channel_cut(h, bed, surface):
    """ErosionChannelCut: a compact channel cannot excavate its unbounded bank envelope."""
    return np.minimum(np.maximum(h-bed,0.),np.maximum(surface-bed,0.))


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


def _sharpen_crease(x, e, b):
    """ReliefSharpenCrease: change to the crease and its derivative; exact rounded |cos| mean, finite slope."""
    mean = 2.0 / math.pi
    scale = 0.5 * math.pi * 0.5 * (1.0 + MEAN_BILLOW[True])
    u, r = np.abs(x) / scale, np.broadcast_to(e / scale, x.shape)
    base = np.where(u < r, 0.5 * (u * u / r + r), u)
    derivative = np.where(u < r, x / e, np.sign(x))
    k = mean / ((1.0 + b) * mean - 0.5 * b)
    # As the shader's branches: the closed form is not evaluated for small or super-amplitude rounding.
    rr = r * r
    excess = rr / math.pi * (1.0 / 3.0 + rr * (1.0 / 60.0 + rr / 280.0))
    sel = (r >= 0.1) & (r < 1.0)
    root, angle = np.sqrt(1.0 - rr[sel]), np.arcsin(r[sel])
    excess[sel] = (rr[sel] * angle - 2.0 * r[sel] * (1.0 - root)
                   + 0.5 * (angle - r[sel] * root)) / (math.pi * r[sel])
    square = np.where(u < 1.0, u * u, 2.0 * u - 1.0)
    change = k * (1.0 + b) - 1.0
    slope = change * derivative - k * b * 2.0 * np.minimum(u, 1.0) * np.sign(x)
    value = scale * (change * (base - mean - excess) - k * b * (square - 0.5))
    large = r >= 1.0
    change = k * (1.0 - b) - 1.0
    return (np.where(large, scale * change * (base - (0.5 * r + 0.25 / r)), value),
            np.where(large, change * derivative, slope))


def _stripe_mean(e):
    """ReliefStripeMean: exact rounded sinusoid mean, less the ordinary noise's crease excess."""
    mean = 2.0 / math.pi
    scale = 0.5 * math.pi * 0.5 * (1.0 + MEAN_BILLOW[True])
    r = np.asarray(e) / scale
    rr = r * r
    excess = rr / math.pi * (1.0 / 3.0 + rr * (1.0 / 60.0 + rr / 280.0))
    sel = (r >= 0.1) & (r < 1.0)
    root, angle = np.sqrt(1.0 - rr[sel]), np.arcsin(r[sel])
    excess[sel] = (rr[sel] * angle - 2.0 * r[sel] * (1.0 - root)
                   + 0.5 * (angle - r[sel] * root)) / (math.pi * r[sel])
    value = np.where(r >= 1.0, scale * (0.5 * r + 0.25 / r), scale * (mean + excess))
    return value - np.vectorize(_excess)(e)


def _gully_gain(under, normal, stripe, share, critical=EROSION_GULLY_CRITICAL):
    """ReliefGullyGain: C1 headroom after reserving the ordinary octave; a phase-independent saturation."""
    left = np.maximum(critical - under - normal, 0.0)
    budget, own = left * left / critical, share * (normal + stripe)
    return budget / np.sqrt(budget * budget + own * own + 1e-30)


def _gully_rock(wavelength, relief, mountains, glacial):
    """ReliefGullyRock: the mantle-to-rock transition at the octave's own scale."""
    return mountains * _smooth(*EROSION_GULLY_ROCK_RELIEF, relief) * _smooth(*EROSION_GULLY_MANTLE, wavelength) * (0.8 + 0.2 * glacial)


def detail(ctx, oriented, plain, oriented_octaves, top_km, octaves, relief, sharp, crease, seed, fold=None, fold_share=0.0,
           fold_weight=0.0, wide_octaves=0, gullies=None, coarse=None, cliff_slope=None):
    """ReliefDetail (Relief.hlsli): (value, slope vector (n, 3)); fold, (value (n,), gradient per radian (n, 3)); gullies,
    a dictionary slope (n, 3), carved, share, glacial (n,); coarse, a list given the sum of the octaves over EROSION_COARSE."""
    up = plain / np.linalg.norm(plain, axis=1, keepdims=True)
    n = len(plain)
    rnd, rid, chain, amp = np.zeros(n), np.zeros(n), np.ones(n), 1.0
    crest, top = np.zeros(n), np.zeros(n)
    rs, ds, cs = np.zeros((n, 3)), np.zeros((n, 3)), np.zeros((n, 3))
    coarse_value = np.zeros(n)
    cliff_value = np.zeros((n, 3))
    wide = np.zeros(n)
    f = R_KM / top_km
    metres = relief / (1000.0 * R_KM)
    sharp = np.broadcast_to(sharp, (n,))
    crease = np.broadcast_to(crease, (n,))
    bend = EROSION_GLACIAL_SHARPEN * gullies["glacial"] if gullies is not None else np.zeros(n)
    mean_abs, mean = 0.5 * (1.0 + MEAN_BILLOW[True]), 2.0 / math.pi
    stripe_scale = 0.5 * math.pi * mean_abs
    sharpen_slope = mean * (1.0 + bend) / ((1.0 + bend) * mean - 0.5 * bend)
    noise_gradient, noise_curvature = 26.0, 512.0
    curvature = np.zeros(n)
    for o in range(octaves):
        w = _weight(ctx, f)
        if w <= 0.0:
            break
        if gullies is not None and o == EROSION_GULLY_FIRST:
            gullies = dict(gullies)
            cut_depth = np.maximum(gullies['ground']+relief*coarse_value-gullies['surface'],0.)
            carved = _smooth(0.,800.,cut_depth)
            gullies['carved'] = carved
            gullies['slope'] = gullies['slope']+(gullies['valley_slope']-gullies['slope'])*carved[:,None]
            gullies['share'] = gullies['share']*carved*(1.-4.*carved*(1.-carved))
            amp = amp*np.maximum(1.,EROSION_WALL_RELIEF*np.minimum(gullies['incision'],cut_depth)/np.maximum(relief,1e-6))
        pt = oriented if o < oriented_octaves else plain
        c, q = _lattice(pt, f, o)
        v, g = gradient_noise_d(c, q, seed + o)
        round_before, ridged_before = rs.copy(), ds.copy()
        g = g * f * metres[:, None]
        g = g - up * (g * up).sum(1, keepdims=True)
        share, limited_share = np.zeros(n), np.zeros(n)
        stripe_value, stripe_gradient = np.zeros(n), np.zeros((n, 3))
        round_a = amp * w / (1.0 + RELIEF_EROSION * (rs * rs).sum(1))
        folded = 1.0 - 0.5 * np.broadcast_to(fold_share, (n,)) * np.clip(fold_weight, 0.0, 1.0) if o in (1, 2) else 1.0
        ridge_a = 1.7 * amp * w * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * (ds * ds).sum(1))
        if gullies is not None and o >= EROSION_GULLY_FIRST and R_KM / f > EROSION_GULLY[2]:
            under = gullies["slope"] + rs + (ds - rs) * sharp[:, None] - gullies["carved"][:, None] * cs
            steep = np.linalg.norm(under, axis=1)
            share = gullies["share"] * _smooth(EROSION_GULLY[0], EROSION_GULLY[1], steep) * (1.0 - _smooth(0.85, 1.0, crest * sharp)) * (1.0 - _smooth(0.9, 1.0, top * sharp))
            coefficient = (round_a + (ridge_a - round_a) * sharp) / max(w, 1e-20)
            stripe_coefficient = (round_a + (ridge_a * sharpen_slope - round_a) * sharp) / max(w, 1e-20)
            frequency = f / (1000.0 * R_KM)
            normal_bound = noise_gradient * relief * frequency * coefficient
            stripe_bound = stripe_scale * relief * stripe_coefficient * (2.0 / EROSION_GULLY_FORK) * (2.0 * math.pi * (frequency + 4.0 * curvature / np.maximum(steep, EROSION_GULLY[0])) + 5.625 * frequency)
            # A rock wall allows a larger slope, never an unbudgeted turn of the stripe's direction.
            rock = _gully_rock(R_KM / f, relief, sharp, gullies["glacial"])
            critical = EROSION_GULLY_CRITICAL + (EROSION_GULLY_ROCK - EROSION_GULLY_CRITICAL) * rock
            limited_share = share * _gully_gain(steep, normal_bound, stripe_bound, share, critical)
            sel = (limited_share > 0.0) | ((share > 0.0) & (R_KM / f > EROSION_CLIFF_SLOPE_KM))
            if sel.any():
                across = np.cross(up[sel], under[sel]) / steep[sel, None]
                sv, sg = _gullies(plain[sel], f, across, seed + 32 + o)
                stripe_value[sel] = sv
                stripe_gradient[sel] = sg * f * metres[sel, None]
        a = round_a
        rnd += a * v
        rs += a[:, None] * g
        if (limited_share > 0.0).any():
            rnd += round_a * limited_share * (stripe_value - v)
            rs += (round_a * limited_share)[:, None] * (stripe_gradient - g)
        x, gr, wr = v, g, np.full(n, w)
        if o == 0 and fold is not None:
            fs = np.broadcast_to(fold_share, (n,))
            gf = fold[1] * metres[:, None]
            gf = gf - up * (gf * up).sum(1, keepdims=True)
            x = v + (fold[0] - v) * fs
            gr = g + (gf - g) * fs[:, None]
            wr = w + (fold_weight - w) * fs
        e = np.maximum(crease, CREASE_ROUNDING * f / ctx.creasef)
        cr, dc = _rcrease(x, e)
        normal_c, normal_dc = cr.copy(), dc.copy()
        a = 1.7 * amp * wr * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * (ds * ds).sum(1))
        if (limited_share > 0.0).any():
            stripe_c, stripe_dc = _rcrease(stripe_value, e)
            change, derivative = _sharpen_crease(stripe_value, e, bend)
            stripe_c += change
            stripe_dc += derivative
            normal_value, stripe_value_ridged = mean_abs - normal_c, _stripe_mean(e) - stripe_c
            rid += ridge_a * limited_share * (stripe_value_ridged - normal_value)
            ds += (ridge_a * limited_share)[:, None] * (-stripe_dc[:, None] * stripe_gradient + normal_dc[:, None] * gr)
            cr -= limited_share * (stripe_value_ridged - normal_value)
        r = 1.0 - cr
        rid += a * (1.0 - normal_c - 0.5 * (1.0 - MEAN_BILLOW[True]))
        ds += (a * -normal_dc)[:, None] * gr
        if R_KM / f > EROSION_CLIFF_SLOPE_KM and (share > 0.0).any():
            mixed = v + (stripe_value - v) * share
            mixed_gradient = g + (stripe_gradient - g) * share[:, None]
            _, old_dc = _rcrease(mixed, e)
            _, derivative = _sharpen_crease(mixed, e, bend)
            old_dc += share * (bend > 0.0) * derivative
            old_round = round_before + round_a[:, None] * mixed_gradient
            old_ridged = ridged_before + (a * -old_dc)[:, None] * mixed_gradient
            cliff_value = old_round + (old_ridged - old_round) * sharp[:, None]
        frequency = f / (1000.0 * R_KM)
        intrinsic = np.maximum(crease, CREASE_ROUNDING * MESH_BAND_LIMIT * CREASE_MIN_CELL * frequency)
        curvature += amp * relief * frequency * frequency * (noise_curvature + 1.7 * sharp * sharpen_slope * noise_gradient * noise_gradient / np.maximum(intrinsic, 1e-20))
        chain = np.clip(0.3 + 1.2 * r, 0.0, 1.0)
        if o < wide_octaves:
            wide = rnd + (rid - rnd) * sharp
        crest = r
        if o == 0:
            top = r
        if f < R_KM / EROSION_COARSE:
            coarse_value = rnd + (rid - rnd) * sharp
            cs = rs + (ds - rs) * sharp[:, None]
        if f < R_KM / EROSION_CLIFF_SLOPE_KM and not (share > 0.0).any():
            cliff_value = rs + (ds - rs) * sharp[:, None]
        f *= RELIEF_LACUNARITY
        amp *= 0.5
    if coarse is not None:
        coarse.append(coarse_value)
    if cliff_slope is not None:
        cliff_slope.append(cliff_value)
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


def _coast_gradient(ctx, p, gain, rias, seed):
    """ReliefCoastGradient: filter both octaves and ria cusps at the physical wave-erosion scale."""
    mean_abs = 0.5 * (1.0 + MEAN_BILLOW[True])
    dev_abs = math.sqrt(SIGMA * SIGMA - mean_abs * mean_abs)
    physical_frequency = R_KM / EROSION_CLIFF_SLOPE_KM
    max_frequency = min(ctx.maxf, physical_frequency)
    crease_frequency = min(ctx.creasef, physical_frequency)
    f, total, amp = R_KM / RELIEF_COAST_NOISE[0], np.zeros_like(p), np.ones(len(p))
    for o in range(int(RELIEF_COAST_NOISE[1])):
        w = np.clip(2.0 - 2.0 * f / max_frequency, 0.0, 1.0)
        if w <= 0.0:
            break
        c, q = _lattice(p, f, o)
        n, g = gradient_noise_d(c, q, seed + o)
        e = CREASE_ROUNDING * f / crease_frequency
        dc = np.clip(n / max(e, 1e-30), -1.0, 1.0)
        share = rias if o > 0 else 0.0
        total += (amp * w * f * (1.0 + (dc * SIGMA / dev_abs - 1.0) * share))[:, None] * g
        f *= 2.2
        amp = amp * gain
    return total / SIGMA / np.sqrt((1.0 - (gain * gain) ** RELIEF_COAST_NOISE[1]) / (1.0 - gain * gain))[:, None]


def erosion_wave_wind(d):
    """ErosionWaveWind: climate mean wind's travel times force; 5 m/s -> 1, 8 m/s -> 1.6, calms fade below 1 m/s."""
    fields = climate(d)
    we, wn = fields["wind_east"], fields["wind_north"]
    speed = np.hypot(we, wn)
    strength = _smooth(0.0, 1.0, speed) * (1.0 + (EROSION_CLIFF_WAVES[1] - 1.0) * np.clip((speed - 5.0) / 3.0, 0.0, 1.0))
    east = np.stack([-d[:, 2], np.zeros(len(d)), d[:, 0]], 1) / np.maximum(np.linalg.norm(d[:, [0, 2]], axis=1, keepdims=True), 1e-6)
    north = np.cross(east, d)
    return (we[:, None] * east + wn[:, None] * north) * (strength / np.maximum(speed, 1e-6))[:, None]


def erosion_cliff_profile(h, hc, delta, depth):
    """ErosionCliffProfile: remap full height through a bounded contour, preserving the deeper sea floor."""
    platform = EROSION_CLIFF_PLATFORM[0] - depth * (1.0 - np.minimum(h / hc, 1.0))
    face = 1.0 - _smooth(hc, hc + delta, h)
    cut = np.minimum(np.maximum(h - platform, 0.0), (hc - EROSION_CLIFF_PLATFORM[0]) * face)
    return h - cut


def erosion_cliff_contact(hc, delta, talus):
    """ErosionCliffContact: physical face parameter at the talus contact."""
    height = hc - EROSION_CLIFF_PLATFORM[0]
    t = 2.0 * talus / (delta + np.sqrt(delta*delta + 4.0*height*talus))
    for _ in range(4):
        t -= (delta*t + height*t*t*(3.0-2.0*t)-talus)/(delta+6.0*height*t*(1.0-t))
    return t


def erosion_cliff_scree(h, hc, delta, talus, gradient):
    """ErosionCliffScree: a monotone talus attached to the face, without a landward moat."""
    contact = hc + delta*erosion_cliff_contact(hc,delta,talus)
    return np.maximum(talus-EROSION_CLIFF_SCREE[0]*np.maximum(contact-h,0.0)/gradient,0.0)


def erosion_cliff_linear_mean(lo, hi, centre, change):
    """Contribution of a positive-part line on a subinterval of the normalized [-1,1] footprint."""
    lo, hi = np.clip(lo,-1.,1.), np.clip(hi,-1.,1.)
    a, b = centre+change*lo, centre+change*hi
    pa, pb = np.maximum(a,0.), np.maximum(b,0.)
    share = np.where(np.minimum(a,b)<0.,np.maximum(pa,pb)/np.maximum(abs(b-a),1e-20),1.)
    return .25*np.maximum(hi-lo,0.)*(pa+pb)*np.clip(share,0.,1.)


def erosion_cliff_face_mean(lo, hi, t, radius, height):
    """Two Gauss nodes integrate one already-bounded cubic piece exactly."""
    lo, hi = np.clip(lo,-1.,1.), np.clip(hi,-1.,1.)
    middle, half = .5*(lo+hi), .5*np.maximum(hi-lo,0.)
    a = np.clip(t+radius*(middle-half*.57735026919),0.,1.)
    b = np.clip(t+radius*(middle+half*.57735026919),0.,1.)
    return .5*half*height*(2.-a*a*(3.-2.*a)-b*b*(3.-2.*b))


def erosion_cliff_mean(h, hc, delta, depth, talus, gradient, radius):
    """Box mean of the composed physical incision; fixed parameters, no one-sided mesh dilation."""
    h,hc,delta,depth,talus,gradient,radius = np.broadcast_arrays(h,hc,delta,depth,talus,gradient,radius)
    foot = EROSION_CLIFF_PLATFORM[0]
    height, platform_slope = hc-foot, 1.-depth/hc
    bottom = (foot-depth)/platform_slope
    safe_radius = np.where(radius>0.,radius,1.)
    contact_t = erosion_cliff_contact(hc,delta,talus)
    contact, slope = hc+delta*contact_t, EROSION_CLIFF_SCREE[0]/gradient
    toe = contact-talus/slope
    cut = erosion_cliff_linear_mean((bottom-h)/safe_radius,(np.minimum(toe,hc)-h)/safe_radius,
                                     platform_slope*(h-bottom),platform_slope*safe_radius)
    cut += erosion_cliff_linear_mean((np.maximum(bottom,toe)-h)/safe_radius,(hc-h)/safe_radius,
                                     height-talus+slope*delta*contact_t+(platform_slope-slope)*(h-hc),
                                     (platform_slope-slope)*safe_radius)
    t, r = (h-hc)/delta, safe_radius/delta
    q = delta*(1.-slope)+height*contact_t*(3.-2.*contact_t)
    b = height*(3.-2.*contact_t)
    start = np.where(q>=0.,0.,np.clip(-2.*q/(b+np.sqrt(np.maximum(b*b+8.*height*q,0.))),0.,contact_t))
    start = np.where(slope<1.+6.*height*contact_t*(1.-contact_t)/delta,start,contact_t)
    cut += erosion_cliff_face_mean(-t/r,(start-t)/r,t,r,height)
    cut += erosion_cliff_linear_mean((start-t)/r,(contact_t-t)/r,
                                     height+delta*contact_t-talus+(1.-slope)*(h-contact),(1.-slope)*safe_radius)
    cut += erosion_cliff_face_mean((contact_t-t)/r,(1.-t)/r,t,r,height)
    surface = h-np.clip(cut,0.,height)
    if np.any(radius<=0.):
        platform = foot-depth*(1.-np.minimum(h/hc,1.))
        raw = np.minimum(h,np.maximum(erosion_cliff_profile(h,hc,delta,depth),
                                      platform+erosion_cliff_scree(h,hc,delta,talus,gradient)))
        surface = np.where(radius<=0.,raw,surface)
    return np.where((h+radius<=bottom)|(h-radius>=hc+delta),h,surface)


def erosion_cliff_noise(p, km, seed):
    """ErosionCliffNoise: a precise lattice, with the same seeds and order as the shader."""
    c, q = _lattice(p, R_KM / km, 0)
    return _gradient(_corner_hashes(c), q, seed, True) / SIGMA


def erosion_coast_slope(forms_gradient, d, detail_slope):
    """ErosionCoastSlope: the same tangent projection, with only detail broader than the maximum platform."""
    ground = forms_gradient / (1000.0 * R_KM) + detail_slope
    return np.linalg.norm(ground - (ground * d).sum(1)[:, None] * d, axis=1)


def erosion_cliff_band(shore, retreat, relief, coast_slope):
    """ErosionCliffBand: cover the detail's possible shore displacement, with only an inland distance fade."""
    bound = np.minimum(retreat + EROSION_CLIFF_REACH[0] + relief / coast_slope, EROSION_CLIFF_REACH[2])
    return 1.0 - _smooth(bound - EROSION_CLIFF_REACH[1], bound, shore)


def erosion_sea_point(position, forms_gradient):
    """ErosionSeaPoint: one fixed marine witness; the small-angle rotation remains in doubles."""
    d = position.astype(np.float32).astype(np.float64)
    slope = forms_gradient - (forms_gradient*d).sum(1)[:, None]*d
    seaward = -slope / np.maximum(np.linalg.norm(slope, axis=1, keepdims=True), 1e-6)
    a = EROSION_CLIFF_RETREAT[2] / R_KM
    a2 = a*a
    sn = a*(1.0-a2/6.0+a2*a2/120.0)
    cs = 1.0-a2/2.0+a2*a2/24.0
    return position*cs + seaward*sn


def erosion_sea_access(height, coast_slope):
    """ErosionSeaAccess: conservative marine clearance, with its fade expressed as a coastal distance."""
    return 1.0-_smooth(-EROSION_CLIFF_SEA[0]-coast_slope*EROSION_CLIFF_SEA[1], -EROSION_CLIFF_SEA[0], height)


def erosion_coast(p, h, shore, coast_slope, rocky, near, coast_offset, forms_gradient, erodibility, cell_km, detail_slope, relief, shore_metric):
    """ErosionCoast: full-ground contour erosion; the approximate shore distance only bounds its support."""
    proxy_band = 1.0 - _smooth(EROSION_CLIFF_REACH[2] - EROSION_CLIFF_REACH[1], EROSION_CLIFF_REACH[2], np.abs(shore))
    shore = shore / shore_metric
    sel = (EROSION_CLIFF_RETREAT[0] != 0.0) & (proxy_band != 0.0) & (rocky > 0.3) & (near > 1e-3) & (shore < EROSION_CLIFF_REACH[2])
    out = h.copy()
    if not sel.any():
        return out
    ids = np.flatnonzero(sel)
    ps, hs, sh, cs, rk, nr, off, fg, er, metric = (x[sel] for x in (p, h, shore, coast_slope, rocky, near, coast_offset, forms_gradient, erodibility, shore_metric))
    shelter = _smooth(EROSION_CLIFF_BAY[0], EROSION_CLIFF_BAY[1], off)
    d = ps.astype(np.float32).astype(np.float64)
    slope = fg - (fg * d).sum(1)[:, None] * d
    seaward = -slope / np.maximum(np.linalg.norm(slope, axis=1, keepdims=True), 1e-6)
    exposure = shelter * (EROSION_CLIFF_WAVES[0] + (1.0 - EROSION_CLIFF_WAVES[0])
                          * np.maximum((-seaward * erosion_wave_wind(d)).sum(1), 0.0))
    hard = 1.0 - _smooth(0.45, 1.6, er)
    presence = (EROSION_CLIFF_RETREAT[0] * _smooth(0.3, 0.9, rk) * _smooth(1e-3, 0.05, nr)
                * shelter * np.maximum(hard, _smooth(0.1, EROSION_CLIFF_WAVES[0], exposure)))
    seed = PLANET_SEED * 4096 + 640
    variation = erosion_cliff_noise(ps, EROSION_CLIFF_NOISE, seed)
    retreat = np.minimum(EROSION_CLIFF_RETREAT[2], EROSION_CLIFF_RETREAT[1] * exposure * er
                          * np.maximum(0.2, 1.0 + EROSION_CLIFF_RETREAT[3] * variation))
    band = erosion_cliff_band(sh, retreat, relief[sel], cs)
    g = np.maximum(erosion_coast_slope(fg, d, detail_slope[sel]), np.maximum(cs * metric * 0.001, 1e-6))
    hc = np.clip(1000.0 * retreat * g, EROSION_CLIFF_HEIGHT[0], EROSION_CLIFF_HEIGHT[1])
    delta, footprint = EROSION_CLIFF_FACE * hc, 1000.0 * cell_km * g
    depth = np.minimum(1000.0 * retreat * EROSION_CLIFF_PLATFORM[1], EROSION_CLIFF_PLATFORM[2])
    bottom = (EROSION_CLIFF_PLATFORM[0]-depth)/(1.-depth/hc)
    if np.all((hs+footprint<=bottom)|(hs-footprint>=hc+delta)):
        return out
    patch = _smooth(-0.2, 0.6, erosion_cliff_noise(ps, 0.9, seed + 1))
    talus = hc * EROSION_CLIFF_SCREE[1] * patch
    surface = erosion_cliff_mean(hs,hc,delta,depth,talus,g,footprint)
    radius = EROSION_CLIFF_STACK[0]
    wide = max(radius, 2.0 * cell_km)
    x = erosion_cliff_noise(ps, EROSION_CLIFF_STACK[1], seed + 2) * EROSION_CLIFF_STACK[1]
    y = erosion_cliff_noise(ps, EROSION_CLIFF_STACK[1], seed + 3) * EROSION_CLIFF_STACK[1]
    remnants = _smooth(EROSION_CLIFF_STACK[2], EROSION_CLIFF_STACK[2] + 0.4, variation)
    edge = max(EROSION_CLIFF_FACE * radius, 2.0 * cell_km)
    stack = (remnants * (radius * radius / (wide * wide))
             * (1.0 - _smooth(max(0.0, wide - edge), wide, np.abs(x)))
             * (1.0 - _smooth(max(0.0, wide - edge), wide, np.abs(y))))
    out[ids] = hs + (surface - hs) * (presence * proxy_band[sel] * band * (1.0 - stack))
    return out


def _relief_ground(ctx, p, valleys=True):
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
    original_shore = shore.copy()
    shore_metric = np.ones(len(p))
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
        cliff = sel & (rocky > 0.3) & valleys & (EROSION_CLIFF_RETREAT[0] != 0.0) & (np.abs(shore) < EROSION_CLIFF_REACH[2])
        if cliff.any():
            d = p[cliff].astype(np.float32).astype(np.float64)
            cg = m["forms_gradient"][cliff]
            base_gradient = cg - (cg * d).sum(1)[:, None] * d
            nr, os_, cs_, rk_ = near[cliff], original_shore[cliff], coast_slope[cliff], rocky[cliff]
            near_gradient = (-2.0 * nr * (os_ / (RELIEF_COAST[2] ** 2 * cs_) + os_ * cs_ / RELIEF_COAST[3] ** 2))[:, None] * base_gradient
            gain_ = RELIEF_COAST_NOISE[2] + (RELIEF_COAST_NOISE[3] - RELIEF_COAST_NOISE[2]) * rk_
            rias_ = RELIEF_RIAS[1] + (RELIEF_RIAS[0] - RELIEF_RIAS[1]) * rk_
            noise_gradient = _coast_gradient(ctx, p[cliff], gain_, rias_, _rseed(7))
            distance = RELIEF_COAST[1] + (RELIEF_COAST[0] - RELIEF_COAST[1]) * rk_
            noise = (shore[cliff] - os_) / (nr * distance)
            coast_gradient = base_gradient + (cs_ * distance)[:, None] * (nr[:, None] * noise_gradient + noise[:, None] * near_gradient)
            coast_gradient -= (coast_gradient * d).sum(1)[:, None] * d
            shore_metric[cliff] = np.maximum(np.linalg.norm(coast_gradient, axis=1) / (R_KM * cs_), 0.25)
    large = h.copy()
    # The volcanoes' edifices, on the large forms; their young flanks quiet the detail.
    volc, quiet_v, volcanic, fin = volcano_edifices(ctx, p)
    h = h + volc

    relief, youth, strata = forms[:, 1] * (1.0 - quiet_v), np.clip(forms[:, 2], 0.0, 1.0), forms[:, 3]
    mountains = _smooth(300.0, 1200.0, relief)
    # The level 0's valleys, read at a point warped by a few km; the gullies' inputs.
    v = dict(surface=np.full(len(p), 1e9), floor=np.zeros(len(p)), incision=np.zeros(len(p)), deposit=np.full(len(p), -1e9),
             channel_bed=np.full(len(p),1e9),channel_surface=np.full(len(p),1e9),lake_level=np.zeros(len(p)),flow=np.zeros((len(p),3)))
    gullies = None
    if valleys:
        wander = turbulence(ctx, p, R_KM / EROSION_WARP[0], EROSION_WARP[1] / (SIGMA * R_KM), 2, _rseed(9))
        v = erosion_valleys(wander, cell_km, EROSION_WALLS[0] + (EROSION_WALLS[1] - EROSION_WALLS[0]) * mountains)
        deep = h <= -500.0  # deeper, no valley nor deposit reaches
        for key, none in (("surface", 1e9), ("floor", 0.0), ("level", 0.0), ("glacier", 0.0), ("incision", 0.0), ("deposit", -1e9),
                          ("channel_bed",1e9),("channel_surface",1e9),("lake_level",0.)):
            v[key] = np.where(deep, none, v[key])
        for link in v["links"]:
            link["z"] = np.where(deep, 1e9, link["z"])
        v["gradient"] = np.where(deep[:, None], 0.0, v["gradient"])
        v['flow'] = np.where(deep[:,None],0.,v['flow'])
        gullies = dict(carved=np.zeros_like(h),ground=h.copy(),surface=v['surface'],valley_slope=v['gradient'],incision=v['incision'],
                       slope=m["forms_gradient"] / (1000.0 * R_KM),
                       share=EROSION_GULLY_SHARE * _smooth(-20.0, 60.0, h),
                       glacial=_smooth(-0.5, 0.5, (h - erosion_equilibrium_line(p)) / EROSION_GLACIAL_BAND))
    plain = p
    bent = turbulence(ctx, plain, R_KM / RELIEF_DETAIL_WARP[0], RELIEF_DETAIL_WARP[1] / (SIGMA * R_KM), 3, _rseed(4))
    reach = RELIEF_ORIENTATION[1]
    t = np.clip(side[:, 1] * (8.0 / (15.0 * reach)), -1.0, 1.0)  # the engine's quintic, levelling off at 15/8 reach
    lift = RELIEF_ORIENTATION[0] * reach * t * (1.875 + t * t * (-1.25 + 0.375 * t * t)) / R_KM
    oriented = bent * (1.0 + lift)[:, None]
    crease = RELIEF_OLD_CREASE * (1.0 - youth)
    fold_share = (RELIEF_FOLD[3] * (1.0 - _smooth(RELIEF_FOLD_REACH[0], RELIEF_FOLD_REACH[1], side[:, 1])) * mountains
                  * _smooth(RELIEF_FOLD_REACH[2], RELIEF_FOLD_REACH[3], np.linalg.norm(m["orientation_gradient"], axis=1) / R_KM))
    fold, fold_weight = None, 0.0
    if (fold_share > 0.0).any():
        fold, fold_weight = _fold(ctx, plain, side[:, 1], m["orientation_gradient"])
    quiet = (1.0 + (RELIEF_COAST_QUIET[0] - 1.0) * (1.0 - rocky) * np.exp(-shore * shore / RELIEF_COAST_QUIET[1] ** 2))
    amplitude = relief * quiet
    coarse = []
    cliff_slope = []
    d, slope, wide = detail(ctx, oriented, plain, RELIEF_ORIENTED_OCTAVES, RELIEF_DETAIL_TOP, RELIEF_OCTAVES, amplitude,
                      mountains, crease, _rseed(1), fold, np.where(fold_share > 0.0, fold_share, 0.0), fold_weight, int(RELIEF_BARRIER_FORM[3]), gullies, coarse, cliff_slope)
    coarse = h + amplitude * coarse[0]
    h = h + amplitude * d
    smooth = smooth + amplitude * wide / coast_slope
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
    # The valleys carved into the coarse ground, the finer detail on their walls; the deposits.
    if valleys:
        h = erosion_carve(h, coarse, v, EROSION_SMOOTH)
    h = np.maximum(h, v["deposit"])
    rough = 0.1 + 0.25 * _smooth(50.0, 400.0, relief) + 0.15 * _smooth(400.0, 1500.0, relief)
    rough = rough + (1.0 - rough) * youth * _smooth(500.0, 1500.0, relief)
    rough = rough + (0.6 - rough) * np.maximum(mesas, badlands)

    return dict(elev=h, large=large, relief=relief, youth=youth, strata=strata,
                channel_bed=v['channel_bed'],channel_surface=v['channel_surface'],lake_level=v['lake_level'],flow=v['flow'],
                volcanoes=volc, volcanic=volcanic, _fin=fin, _smooth=smooth,
                axis=sharp[:, 0], trench=sharp[:, 1], divergent=sharp[:, 2], shear=sharp[:, 3], roughness=rough,
                _wave=(p, h, shore, coast_slope, rocky, near, shore-original_shore, m["forms_gradient"],
                       m["erodibility"], cell_km, cliff_slope[0], relief, shore_metric))


def _relief_finish(ctx, p, h, near, rocky, smooth, cell_km, fin):
    """ReliefFinish: smooth barriers, volcanic finish and summit limiting, also for the sea witness."""
    h = h.copy()
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
    def cap(x):
        return np.where(x > RELIEF_HIGHEST[0], RELIEF_HIGHEST[0] + RELIEF_HIGHEST[1] * np.tanh((x - RELIEF_HIGHEST[0]) / RELIEF_HIGHEST[1]), x)
    return cap(h)


def _relief(ctx, p, valleys=True):
    p = np.asarray(p, np.float64)
    ground = _relief_ground(ctx, p, valleys)
    args = ground.pop("_wave")
    h = ground["elev"]
    if valleys:
        candidate = erosion_coast(*args)
        ids = np.flatnonzero(candidate < h)
        if len(ids):
            witness = erosion_sea_point(p[ids], args[7][ids])
            sea = _relief_ground(ctx, witness, False)
            a = sea["_wave"]
            level = _relief_finish(ctx, witness, sea["elev"], a[5], a[4], sea["_smooth"], a[9], sea["_fin"])
            h = h.copy()
            h[ids] += (candidate[ids]-h[ids]) * erosion_sea_access(level, a[3])
    h = _relief_finish(ctx, p, h, args[5], args[4], ground.pop("_smooth"), args[9], ground.pop("_fin"))
    channel_surface,channel_bed = ground.pop('channel_surface'),ground.pop('channel_bed')
    river_surface = np.minimum(h,channel_surface)
    h -= erosion_channel_cut(h,channel_bed,channel_surface)
    ground["elev"], ground["norivers"] = h, h.copy()
    lake = ground['lake_level']>np.maximum(h,river_surface)
    ground['water_level'] = np.maximum(0.,np.maximum(ground['lake_level'],river_surface))
    ground['flow'] = np.where((lake|(ground['water_level']<=0.))[:,None],0.,ground['flow'])
    ground['water_depth'] = np.maximum(ground['water_level']-h,0.)
    ground['surface'] = np.maximum(ground['water_level'],h)
    return ground


def elevation(ctx, p, extra=False, valleys=True):
    """Elevation (m) of the unit vectors p (n, 3); with extra, the dictionary of the parts: elev, norivers (without the
    legacy alias of elev; use valleys=False for the pre-erosion form), large (large forms and sharp profiles), volcanoes (their edifices) and volcanic (the fresh
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
    # The real-ground remap is continuous through the old shoreline and both ends of the face. Its lowering never
    # exceeds Hc minus the platform foot, even with cells of 30 km, and all higher mountains remain exactly unchanged.
    d = np.array([[1.0, 0.0, 0.0]])
    assert erosion_coast_slope(np.array([[1000.0, R * 0.5, 0.0]]), d, np.zeros((1, 3)))[0] == 0.5
    witness = erosion_sea_point(d, np.array([[0.0, 0.0, 1.0]]))
    angle = np.arctan2(np.linalg.norm(np.cross(d, witness)), (d*witness).sum())
    assert abs(angle*R-1000.0*EROSION_CLIFF_RETREAT[2]) < 1e-6
    knots = np.array([-EROSION_CLIFF_SEA[0]-100.0*EROSION_CLIFF_SEA[1], -EROSION_CLIFF_SEA[0]])
    assert np.array_equal(erosion_sea_access(knots, 100.0), np.array([1.0, 0.0]))
    assert np.max(np.abs(erosion_sea_access(knots+1e-7, 100.0)-erosion_sea_access(knots-1e-7, 100.0))) < 1e-6
    # The band stays fully open seaward, includes the detail's displacement, and fades over a distance inland.
    assert erosion_cliff_band(np.array([-100.0, 0.0, 2.0]), 0.5, 200.0, 100.0).min() == 1.0
    for bound in (3.5, 8.0):
        shore = np.array([bound-EROSION_CLIFF_REACH[1], bound])
        relief = 200.0 if bound == 3.5 else 2000.0
        assert np.array_equal(erosion_cliff_band(shore, 0.5, relief, 100.0), np.array([1.0, 0.0]))
        assert np.max(np.abs(erosion_cliff_band(shore+1e-8, 0.5, relief, 100.0)
                             - erosion_cliff_band(shore-1e-8, 0.5, relief, 100.0))) < 1e-6
    for cell_km in (0.01, 0.1, 30.0):
        hc, slope, depth = 200.0, 0.1, 4.0
        delta = max(EROSION_CLIFF_FACE * hc, 2000.0 * cell_km * slope)
        knots = np.array([0.0, hc, hc + delta])
        assert np.max(np.abs(erosion_cliff_profile(knots + 1e-8, hc, delta, depth)
                             - erosion_cliff_profile(knots - 1e-8, hc, delta, depth))) < 1e-5
        h = np.linspace(-100.0, hc + delta + 1000.0, 20001)
        remapped = erosion_cliff_profile(h, hc, delta, depth)
        assert np.all(remapped <= h) and np.max(h - remapped) <= hc - EROSION_CLIFF_PLATFORM[0] + 1e-9
        assert np.array_equal(remapped[h >= hc + delta], h[h >= hc + delta])
        assert erosion_cliff_profile(np.array([-100.0]), hc, delta, depth)[0] == -100.0
    # The combined relief, when the engine has written its caches: volcanoes and the primary point's material survive
    # the valley and sea-witness queries. These places cover an atoll, a barrier coast, two cliffs, a chain and a forest.
    if all(os.path.exists(cache.format(seed=PLANET_SEED)) for cache in (TECTONIC_CACHE, VOLCANO_CACHE, EROSION_CACHE)):
        a = np.radians([[5.593, -115.057], [-27.18082, -152.21264], [8.73276, -103.30263],
                        [-3.21606, 169.25336], [-7.5, 117.0], [34.1611352, -73.72443]])
        p = np.stack([np.cos(a[:, 0]) * np.cos(a[:, 1]), np.sin(a[:, 0]), np.cos(a[:, 0]) * np.sin(a[:, 1])], 1)
        before = elevation(Ctx(1.0), p, extra=True, valleys=False)
        after = elevation(Ctx(1.0), p, extra=True, valleys=True)
        assert np.isfinite(after["elev"]).all()
        assert np.array_equal(after["volcanoes"], before["volcanoes"])
        assert np.array_equal(after["volcanic"], before["volcanic"])
        assert np.max(np.abs(after["elev"] - before["elev"])) > 1.0
    print("ok")
