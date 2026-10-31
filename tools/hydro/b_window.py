# B. One window at a given cell size: river valley widths, spacing, depth, and what water would do in them.
# usage: python b_window.py name lat lon size_km n
import sys, time, heapq, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cp import *

name, lat, lon, size_km, n = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
cell = size_km * 1000 / n
la, lo = np.radians(lat), np.radians(lon)
c = [np.cos(la) * np.cos(lo), np.sin(la), np.cos(la) * np.sin(lo)]
p = window(c, size_km * 1000, n)
t0 = time.time()
ctx = Ctx(cell)
d = elevation(ctx, p, extra=True)
rp, cu0, cu1, n0, n1 = river_positions(ctx, p, parts=True)
print(name, "time %.0f s, cell %.0f m" % (time.time() - t0, cell))
E = d["elev"].reshape(n, n); B = d["norivers"].reshape(n, n)
carve = (d["riv_a"] * (rp - 1) * RIVER_DEPTH / 2 * MAX_ELEV).reshape(n, n)
cu0, cu1, n0, n1 = (a.reshape(n, n) for a in (cu0, cu1, n0, n1))
land = B > 0
res = dict(name=name, lat=lat, lon=lon, cell=cell, land=float(land.mean()),
           mount=float(d["mount_a"].mean()), hills=float(d["hills_a"].mean()),
           elev_p50=float(np.median(B[land])) if land.any() else None)

# Centreline length per area (stereology: L_A = pi/2 * crossings per unit test-line length), on land.
def length_density(f, mask):
    cx = (np.sign(f[:, 1:]) != np.sign(f[:, :-1])) & mask[:, 1:] & mask[:, :-1]
    cy = (np.sign(f[1:, :]) != np.sign(f[:-1, :])) & mask[1:, :] & mask[:-1, :]
    nl = (cx.sum() + cy.sum()) / ((mask[:, 1:] & mask[:, :-1]).sum() + (mask[1:, :] & mask[:-1, :]).sum()) / cell
    return np.pi / 2 * nl  # per m
big_floor = (cu0 < -0.9) & land
small_floor = (cu1 < 0.6) & (cu1 < cu0) & land
LA0 = length_density(n0, land); LA1 = length_density(n1, land)
res["big_km_per_1000km2"] = LA0 * 1e9 / 1e3 if land.any() else None
res["small_km_per_1000km2"] = LA1 * 1e9 / 1e3 if land.any() else None
if land.any():
    res["big_floor_width_km"] = float(big_floor.mean() / land.mean() / LA0 / 1000)
    res["big_valley_width_km"] = float(((cu0 < 0.5) & land).mean() / land.mean() / LA0 / 1000)
    res["small_floor_width_km"] = float(small_floor.mean() / land.mean() / LA1 / 1000)
    res["carve_p50_in_big_floor"] = float(np.median(carve[big_floor])) if big_floor.any() else None
    res["carve_p50_in_small_floor"] = float(np.median(carve[small_floor])) if small_floor.any() else None
    # bank steepness: max slope of the carving itself (m/m)
    gy, gx = np.gradient(carve, cell)
    res["carve_slope_p99"] = float(np.percentile(np.hypot(gx, gy)[land], 99))

# Priority flood: sea cells and the window border drain; filled depth = water a lake would hold.
def priority_flood(z, outlet):
    nn = z.shape[0]
    filled = np.full(z.shape, np.inf); done = np.zeros(z.shape, bool); h = []
    for i, j in zip(*np.nonzero(outlet)):
        filled[i, j] = z[i, j]; done[i, j] = True; heapq.heappush(h, (z[i, j], i, j))
    while h:
        zz, i, j = heapq.heappop(h)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nn and 0 <= b < nn and not done[a, b]:
                done[a, b] = True
                filled[a, b] = max(z[a, b], zz)
                heapq.heappush(h, (filled[a, b], a, b))
    return filled
outlet = ~land.copy(); outlet[0, :] = outlet[-1, :] = outlet[:, 0] = outlet[:, -1] = True
F = priority_flood(E, outlet); depth = F - E
lake = (depth > 1.0) & land
res["lake_share_of_land"] = float(lake.sum() / max(land.sum(), 1))
res["lake_share_in_big_floor"] = float((lake & big_floor).sum() / max(big_floor.sum(), 1))
res["lake_share_outside_valleys"] = float((lake & land & (cu0 > 0.5) & (cu1 > 1.0)).sum() / max((land & (cu0 > 0.5) & (cu1 > 1.0)).sum(), 1))
res["lake_depth_p50_p90"] = [float(np.percentile(depth[lake], 50)), float(np.percentile(depth[lake], 90))] if lake.any() else None
# lake count and sizes (4-connected components)
lab = -np.ones(E.shape, int); sizes = []
for i, j in zip(*np.nonzero(lake)):
    if lab[i, j] >= 0: continue
    k = len(sizes); stack = [(i, j)]; lab[i, j] = k; s = 0
    while stack:
        a, b = stack.pop(); s += 1
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = a + da, b + db
            if 0 <= x < n and 0 <= y < n and lake[x, y] and lab[x, y] < 0:
                lab[x, y] = k; stack.append((x, y))
    sizes.append(s)
sizes = np.array(sizes) * cell * cell / 1e6  # km2
res["lakes_count"] = int(len(sizes))
res["lakes_per_1000km2"] = float(len(sizes) / max(land.sum() * cell * cell / 1e9, 1e-9))
if len(sizes):
    res["lake_km2_p50_p90_max"] = [float(np.percentile(sizes, 50)), float(np.percentile(sizes, 90)), float(sizes.max())]

# Longitudinal profiles along the big rivers' centrelines (contour n0 = 0), inside land.
cs = plt.contour(n0, levels=[0.0])
prof = []
for seg in cs.allsegs[0]:
    if len(seg) < 30: continue
    jj, ii = seg[:, 0], seg[:, 1]
    seglen = np.hypot(np.diff(jj), np.diff(ii)).sum() * cell
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(jj), np.diff(ii)))]) * cell
    t = np.arange(0, s[-1], cell)
    ji, ii2 = np.interp(t, s, jj), np.interp(t, s, ii)
    zi = E[np.clip(np.round(ii2).astype(int), 0, n - 1), np.clip(np.round(ji).astype(int), 0, n - 1)]
    di = depth[np.clip(np.round(ii2).astype(int), 0, n - 1), np.clip(np.round(ji).astype(int), 0, n - 1)]
    if (zi > 0).mean() < 0.9 or len(zi) < 50: continue
    k = max(1, int(5000 / cell))
    zs = np.convolve(zi, np.ones(k) / k, mode="valid")
    dz = np.diff(zs)
    up, down = dz[dz > 0].sum(), -dz[dz < 0].sum()
    mins = ((zs[1:-1] < zs[:-2]) & (zs[1:-1] < zs[2:])).sum()
    closed = np.hypot(jj[0] - jj[-1], ii[0] - ii[-1]) < 2
    prof.append(dict(len_km=len(zi) * cell / 1000, rise_m=float(up), fall_m=float(down), net_m=float(zs[-1] - zs[0]),
                     minima_per_100km=float(mins / (len(zi) * cell / 1e5)), share_in_pits=float((di > 1).mean()),
                     z_min=float(zi.min()), z_max=float(zi.max()), closed=bool(closed), reaches_sea=bool((zi <= 0).any())))
    if len(prof) == 1: prof0 = (t, zi)
plt.close("all")
if prof:
    L = np.array([q["len_km"] for q in prof])
    res["profiles"] = dict(count=len(prof), total_km=float(L.sum()),
                           rise_over_fall=float(sum(q["rise_m"] for q in prof) / max(sum(q["fall_m"] for q in prof), 1)),
                           minima_per_100km=float(np.average([q["minima_per_100km"] for q in prof], weights=L)),
                           share_in_pits=float(np.average([q["share_in_pits"] for q in prof], weights=L)),
                           reaches_sea=float(np.mean([q["reaches_sea"] for q in prof])),
                           relief_along_p50=float(np.median([q["z_max"] - q["z_min"] for q in prof])))
print(json.dumps(res, indent=1))
json.dump(res, open(f"{name}.json", "w"), indent=1)
np.savez(f"{name}.npz", E=E, B=B, carve=carve, depth=depth, cu0=cu0, cu1=cu1)

fig, ax = plt.subplots(1, 3, figsize=(21, 7))
ext = (-size_km / 2, size_km / 2, -size_km / 2, size_km / 2)
ax[0].imshow(np.where(land, E, np.nan), cmap="terrain", origin="lower", extent=ext, vmin=0, vmax=max(500, np.percentile(E, 99)))
ax[0].imshow(np.where(~land, 1, np.nan), cmap="Blues", origin="lower", extent=ext, vmin=0, vmax=2)
ax[0].set_title(f"{name}: elevation, sea blue ({lat}, {lon}), cell {cell:.0f} m")
ax[1].imshow(carve, cmap="magma", origin="lower", extent=ext, vmin=-200, vmax=0); ax[1].set_title("river carving (m)")
ax[2].imshow(np.where(land, E, np.nan), cmap="gray", origin="lower", extent=ext)
ax[2].imshow(np.where(lake, depth, np.nan), cmap="cool", origin="lower", extent=ext, vmin=0, vmax=100)
ax[2].imshow(np.where(~land, 1, np.nan), cmap="Blues", origin="lower", extent=ext, vmin=0, vmax=2)
ax[2].set_title("water if every pit filled (priority flood), depth 0-100 m")
plt.savefig(f"{name}.png", dpi=70, bbox_inches="tight")
