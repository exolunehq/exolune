# Planet map bench (docs/recherche-rivieres.md, step 1): the engine computes its planet map at startup (PlanetMap.hlsl,
# PlanetMap.cpp) and saves it (MYPLANETENGINE_MAP); this bench checks it and measures what it holds.
# - Checks: its elevation against the numpy port of the relief (tools/hydro/cp.py) at cells drawn at random; its
#   filled surface against a flood of our own, by the plain Priority-Flood, which must give the same one; every cell
#   drains to the sea, downhill or level, to a neighbour; the sea receives every land cell's area.
# - Measures: lakes once every pit is filled (share of land, count, sizes, N(>A) against HydroLAKES), the land draining
#   into a pit, drainage density by drained area and its exponent, Hack's law; the haze's regional ground (its highest,
#   for the atmosphere tables' GROUND_MAX_KM) and the highest plateaus, for the test views. Startup times and memory.
#
# python tools/banc_carte.py <exe> <out folder>      (or <map.bin> instead of <exe>: an existing dump)
import os, subprocess, sys
import warnings
import numpy as np
from numba import njit

warnings.simplefilter("ignore", np.exceptions.RankWarning)  # the fits over repeated sizes

HERE = os.path.dirname(os.path.abspath(__file__))
N, R = 1024, 6378.0  # PlanetMap::Size, km
CELLS = 6 * N * N


@njit(cache=True)
def face_direction(f, s, t):
    if f == 0: return 1.0, -t, -s
    if f == 1: return -1.0, -t, s
    if f == 2: return s, 1.0, t
    if f == 3: return s, -1.0, -t
    if f == 4: return s, -t, 1.0
    return -s, -t, -1.0


@njit(cache=True)
def cell_of(x, y, z):
    ax, ay, az = abs(x), abs(y), abs(z)
    if ax >= ay and ax >= az:
        f, ma, sc, tc = (0 if x > 0 else 1), ax, (-z if x > 0 else z), -y
    elif ay >= az:
        f, ma, sc, tc = (2 if y > 0 else 3), ay, x, (z if y > 0 else -z)
    else:
        f, ma, sc, tc = (4 if z > 0 else 5), az, (x if z > 0 else -x), -y
    i = min(max(int(np.floor((sc / ma + 1.0) * 0.5 * N)), 0), N - 1)
    j = min(max(int(np.floor((tc / ma + 1.0) * 0.5 * N)), 0), N - 1)
    return (f * N + j) * N + i


@njit(cache=True)
def neighbours(c, out, diagonals=True):
    f, j, i = c // (N * N), c // N % N, c % N
    k = 0
    for dj in range(-1, 2):
        for di in range(-1, 2):
            if (di == 0 and dj == 0) or (not diagonals and di != 0 and dj != 0):
                continue
            ii, jj = i + di, j + dj
            if 0 <= ii < N and 0 <= jj < N:
                out[k] = c + dj * N + di
            else:
                x, y, z = face_direction(f, (ii + 0.5) * 2.0 / N - 1.0, (jj + 0.5) * 2.0 / N - 1.0)
                out[k] = cell_of(x, y, z)
            k += 1
    return k


def directions():
    c = np.arange(CELLS)
    f, j, i = c // (N * N), c // N % N, c % N
    s, t = (i + 0.5) * 2.0 / N - 1.0, (j + 0.5) * 2.0 / N - 1.0
    one = np.ones_like(s)
    table = [(one, -t, -s), (-one, -t, s), (s, one, t), (s, -one, -t), (s, -t, one), (-s, -t, -one)]
    d = np.zeros((CELLS, 3))
    for k in range(6):
        m = f == k
        d[m] = np.stack([a[m] for a in table[k]], axis=1)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    area = 4.0 / N ** 2 / (1.0 + s * s + t * t) ** 1.5 * R * R
    return d, area


@njit(cache=True)
def plain_flood(e):
    # Priority-Flood, algorithm 1: every cell through the heap. The filled surface is unique: it must be the engine's.
    filled = np.zeros(e.size, np.float32)
    done = np.zeros(e.size, np.bool_)
    level = np.empty(e.size, np.float32)
    cell = np.empty(e.size, np.int64)
    n = 0
    nb = np.empty(8, np.int64)
    for c in range(e.size):
        if e[c] < 0:
            done[c] = True
            level[n] = 0.0; cell[n] = c  # all at 0: a valid heap
            n += 1
    while n > 0:
        c, lc = cell[0], level[0]
        n -= 1
        lv, cv = level[n], cell[n]
        i = 0
        while True:
            ch = 2 * i + 1
            if ch >= n: break
            if ch + 1 < n and level[ch + 1] < level[ch]: ch += 1
            if level[ch] >= lv: break
            level[i] = level[ch]; cell[i] = cell[ch]; i = ch
        level[i] = lv; cell[i] = cv
        for k in range(neighbours(c, nb)):
            m = nb[k]
            if done[m]: continue
            done[m] = True
            filled[m] = max(e[m], lc)
            i = n; n += 1
            while i > 0 and level[(i - 1) // 2] > filled[m]:
                level[i] = level[(i - 1) // 2]; cell[i] = cell[(i - 1) // 2]; i = (i - 1) // 2
            level[i] = filled[m]; cell[i] = m
    return filled


@njit(cache=True)
def receivers_ok(e, filled, receiver, area):
    # Each land cell's receiver: a neighbour, no higher on the filled surface; every chain ends at the sea.
    nb = np.empty(8, np.int64)
    bad_neighbour = bad_slope = 0
    for c in range(e.size):
        r = receiver[c]
        if e[c] < 0:
            if r != 0xffffffff: bad_neighbour += 1
            continue
        k = neighbours(c, nb)
        if not (nb[:k] == r).any(): bad_neighbour += 1
        if filled[r] > filled[c]: bad_slope += 1
    return bad_neighbour, bad_slope


@njit(cache=True)
def components(mask, label):
    # 4-connected components of mask across the cube's faces; returns the cell count of each.
    stack = np.empty(mask.size, np.int64)
    nb = np.empty(8, np.int64)
    sizes = []
    for c0 in range(mask.size):
        if not mask[c0] or label[c0] >= 0: continue
        k0 = len(sizes); label[c0] = k0; top = 0; stack[0] = c0; top = 1; s = 0
        while top > 0:
            top -= 1; c = stack[top]; s += 1
            for q in range(neighbours(c, nb, False)):
                m = nb[q]
                if mask[m] and label[m] < 0:
                    label[m] = k0; stack[top] = m; top += 1
        sizes.append(s)
    return sizes


@njit(cache=True)
def downstream(order, receiver, lake, step):
    # order: land cells from the sea up (decreasing drained area). Whether the way to the sea crosses a lake.
    into_pit = np.zeros(receiver.size, np.bool_)
    for c in order:
        r = receiver[c]
        into_pit[c] = lake[c] or (r != 0xffffffff and into_pit[r])
    return into_pit


@njit(cache=True)
def main_length(order_up, receiver, step):
    # order_up: land cells from the heights down (increasing area). The longest way upstream of each cell (km).
    length = np.zeros(receiver.size, np.float32)
    for c in order_up:
        r = receiver[c]
        if r != 0xffffffff:
            length[r] = max(length[r], length[c] + step[c])
    return length


def run(exe, out):
    dump = os.path.join(out, "map.bin")
    env = dict(os.environ, MYPLANETENGINE_MAP=dump, MYPLANETENGINE_CAPTURE=os.path.join(out, "map_capture.bmp"), MYPLANETENGINE_TAA="1", MYPLANETENGINE_GLARE="1")
    env.setdefault("MYPLANETENGINE_SCANS", os.path.join(HERE, "..", "..", "scans"))
    for k in ("MYPLANETENGINE_VIEW", "MYPLANETENGINE_BATCH", "MYPLANETENGINE_TREMBLE", "MYPLANETENGINE_TESTS"):
        env.pop(k, None)
    subprocess.run(["powershell", "-NoProfile", "-Command", f"Start-Process '{exe}' -WindowStyle Minimized -Wait"], env=env,
                   timeout=300)
    for f in ("map_capture.bmp", "map_capture.bmp.txt"):
        if os.path.exists(os.path.join(out, f)): os.remove(os.path.join(out, f))
    return dump


def latlon(d):
    return np.degrees(np.arcsin(d[..., 1])), np.degrees(np.arctan2(d[..., 2], d[..., 0]))


def fit(x, y):
    return np.polyfit(np.log(x), np.log(y), 1)[0]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    dump = src if src.endswith(".bin") else run(src, out)
    raw = np.fromfile(dump, np.float32).reshape(4, CELLS)
    e, filled, area = raw[0], raw[1], raw[2]
    receiver = raw[3].view(np.uint32)
    if os.path.exists(dump + ".txt"):
        print("Démarrage : " + ", ".join(open(dump + ".txt").read().split("\n")).strip(", "))
    d, own = directions()
    land, sea = e >= 0, e < 0
    land_km2 = own[land].sum()
    print(f"Terres : {100 * land_km2 / own.sum():.1f} % de la planète ; mailles de {np.sqrt(own.min()):.1f} à {np.sqrt(own.max()):.1f} km")

    # 1. The elevation against the numpy port, near the faces' centres, where a texel's tangential size is 2 R / N.
    sys.path.insert(0, os.path.join(HERE, "hydro"))
    import cp
    rng = np.random.default_rng(1)
    c = np.arange(CELLS)
    centre = (np.abs(c % N - N / 2) < N / 16) & (np.abs(c // N % N - N / 2) < N / 16)
    pick = rng.choice(np.nonzero(centre)[0], 600, replace=False)
    ref = cp.elevation(cp.Ctx(R * 1000.0 * 2.0 / N), d[pick])
    err = np.abs(ref - e[pick])
    print(f"Altitude contre cp.py, 600 mailles : écart médian {np.median(err):.3f} m, max {err.max():.3f} m"
          f" (altitudes de {e[pick].min():.0f} à {e[pick].max():.0f} m)")

    # 2. The flood against our own, and the receivers.
    mine = plain_flood(e)
    diff = np.abs(mine - filled)
    print(f"Surface remplie contre le Priority-Flood simple : {int((diff > 0).sum())} mailles différentes, écart max {diff.max():.3g} m")
    bad_n, bad_s = receivers_ok(e, filled, receiver, area)
    sea_in = area[sea].sum()
    print(f"Exutoires : {bad_n} receveurs non voisins, {bad_s} qui montent ; la mer reçoit {100 * sea_in / land_km2:.3f} % des terres")

    # 3. Lakes, every pit filled.
    depth = filled - np.maximum(e, 0.0)
    lake = land & (depth > 1.0)
    label = -np.ones(CELLS, np.int64)
    sizes = np.array(components(lake, label))
    lake_km2 = np.bincount(label[lake], weights=own[lake])
    print(f"Lacs (plus de 1 m) : {100 * own[lake].sum() / land_km2:.1f} % des terres ; {len(sizes)} lacs ; profondeur médiane "
          f"{np.median(depth[lake]):.0f} m, p90 {np.percentile(depth[lake], 90):.0f} m")
    big = np.sort(lake_km2)[::-1]
    print("Les plus grands (km²) : " + ", ".join(f"{a:,.0f}".replace(",", " ") for a in big[:5])
          + f" ; part des lacs de plus de 100 000 km² dans leur surface : {100 * big[big > 1e5].sum() / big.sum():.0f} %")
    for a in (1e3, 1e4, 1e5, 1e6):
        print(f"  N(> {a:,.0f} km²) = {(lake_km2 > a).sum()}".replace(",", " "))
    tail = np.sort(lake_km2[lake_km2 >= 1e3])[::-1]
    slope = fit(tail, np.arange(1, tail.size + 1))
    print(f"  N(>A) ∝ A^{slope:.2f} au-dessus de 1 000 km² ; HydroLAKES, A^-1,14 au-dessus de 0,46 km² (Cael et Seekell 2016)")

    # 4. Drainage: the land draining into a pit, density by drained area, Hack.
    p = d[np.where(receiver == 0xffffffff, 0, receiver)]
    step = np.where(land, R * np.arccos(np.clip((d * p).sum(axis=1), -1.0, 1.0)), 0.0).astype(np.float32)
    order_down = np.nonzero(land)[0][np.argsort(-area[land], kind="stable")]
    into_pit = downstream(order_down, receiver, lake, step)
    print(f"Terres qui se jettent dans une cuvette : {100 * own[into_pit & land].sum() / land_km2:.0f} %"
          f" (Terre, bassins sans issue : 20 %, Wang 2018)")
    for a in (1e2, 1e3, 1e4, 1e5):
        channel = land & (area >= a)
        print(f"  densité de drainage, aire drainée > {a:.0f} km² : {step[channel].sum() / land_km2:.4f} km/km²")
    a_s = np.array([3e2, 1e3, 1e4, 1e5])
    share = np.array([own[land & (area >= a)].sum() / land_km2 for a in a_s])
    print(f"  P(A > a) ∝ a^{fit(a_s, share):.2f} de 300 à 100 000 km² ; Terre, a^-0,43 (Rodriguez-Iturbe et Rinaldo 1997) ;"
          f" HydroRIVERS, 0,27 km/km² au-dessus de 10 km², soit 0,037 au-dessus de 1 000 km² à cet exposant")
    length = main_length(order_down[::-1], receiver, step)
    hk = land & (area >= 1e3) & (area <= 1e6)
    print(f"  loi de Hack : L ∝ A^{fit(area[hk], length[hk]):.2f} de 1 000 à 10⁶ km² (Terre, 0,5 à 0,6)")
    outlets = sea & (area > 0)
    basins = np.sort(area[outlets])[::-1]
    print("  plus grands bassins (km²) : " + ", ".join(f"{a:,.0f}".replace(",", " ") for a in basins[:5]))

    # 5. The haze's ground: the mip pyramid of max(e, 0), as the engine samples it, and the highest plateaus.
    g = np.maximum(e, 0.0).reshape(6, N, N).astype(np.float64)
    for level in range(1, 5):
        g = 0.25 * (g[:, 0::2, 0::2] + g[:, 1::2, 0::2] + g[:, 0::2, 1::2] + g[:, 1::2, 1::2])
        print(f"  sol régional, mip {level} ({2 ** level * 2 * np.pi * R / 4 / N:.0f} km au centre d'une face) : max {g.max():.0f} m,"
              f" p99,9 des terres {np.percentile(g[g > 0], 99.9):.0f} m")
        if level == 3:
            n3 = N >> 3
            top = np.argsort(-g.ravel())
            seen = []
            for k in top:
                f, j, i = k // (n3 * n3), k // n3 % n3, k % n3
                x, y, z = face_direction(f, (i + 0.5) * 2.0 / n3 - 1.0, (j + 0.5) * 2.0 / n3 - 1.0)
                v = np.array([x, y, z]) / np.linalg.norm([x, y, z])
                if all(np.dot(v, w) < np.cos(np.radians(5)) for w in seen):
                    seen.append(v)
                    la, lo = latlon(v)
                    print(f"    plateau : {la:.3f} {lo:.3f}, sol régional {g.ravel()[k]:.0f} m")
                if len(seen) == 4: break
