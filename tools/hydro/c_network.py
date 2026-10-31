# C. A coarse drainage network computed on complexplanet itself (4.8 km), against the 1.2 km terrain of the same
# window: does it follow complexplanet's valleys, and how far does finer terrain rise above its water level?
# usage: python c_network.py name   (needs name.npz/json from b_window.py)
import sys, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cp import *
from hydro import *

name = sys.argv[1]
info = json.load(open(f"{name}.json")); fine = np.load(f"{name}.npz")
E1, cu0, cu1 = fine["E"], fine["cu0"], fine["cu1"]
n1 = E1.shape[0]; k = 4; nc = n1 // k; cellc = info["cell"] * k
la, lo = np.radians(info["lat"]), np.radians(info["lon"])
c = [np.cos(la) * np.cos(lo), np.sin(la), np.cos(la) * np.sin(lo)]
size = info["cell"] * n1
p = window(c, nc * cellc, nc)
Ec = elevation(Ctx(cellc), p).reshape(nc, nc)
land = Ec > 0
out = ~land; out[0, :] = out[-1, :] = out[:, 0] = out[:, -1] = True
F0 = priority_flood(Ec, out)              # lake levels
Fe = priority_flood(Ec, out, eps=0.01)    # drains everywhere
acc, rec = d8_accumulation(Fe, out)
A = acc * (cellc / 1000) ** 2             # km2
res = dict(name=name, coarse_cell=cellc)
res["coarse_lake_share"] = float(((F0 - Ec > 1) & land).sum() / land.sum())
# valley masks on the coarse grid: a coarse cell is "in a valley" if most of its fine cells are
blk = lambda a: a[:nc * k, :nc * k].reshape(nc, k, nc, k).mean((1, 3))
inbig = blk((cu0 < -0.9).astype(float)) > 0.5
insmall = blk(((cu1 < 0.6) & (cu1 < cu0)).astype(float)) > 0.5
for thr in (200, 2000, 20000):
    net = (A > thr) & land
    if net.sum() == 0: continue
    res[f"net_A>{thr}km2"] = dict(cells=int(net.sum()),
                                  share_in_big_valley=float((net & inbig).sum() / net.sum()),
                                  share_in_any_valley=float((net & (inbig | insmall)).sum() / net.sum()),
                                  share_in_lakes=float((net & (F0 - Ec > 1)).sum() / net.sum()))
res["land_share_big_valley"] = float((inbig & land).sum() / land.sum())
res["land_share_any_valley"] = float(((inbig | insmall) & land).sum() / land.sum())
# finer terrain against the coarse water level, along the network outside lakes
net = (A > 200) & land & ~(F0 - Ec > 1)
E1b = E1[:nc * k, :nc * k].reshape(nc, k, nc, k)
ex_min = E1b.min((1, 3)) - Fe     # the lowest 1.2 km cell of the block, above the coarse level
ex_mean = E1b.mean((1, 3)) - Fe
res["fine_min_above_level_m_p50_p90_p99"] = [float(np.percentile(ex_min[net], q)) for q in (50, 90, 99)]
res["fine_mean_above_level_m_p50_p90"] = [float(np.percentile(ex_mean[net], q)) for q in (50, 90)]
res["share_net_where_fine_min_above_level_by_5m"] = float((ex_min[net] > 5).mean())
# along-river slope of the coarse level
sl = []
for i, j in zip(*np.nonzero(net)):
    r = rec[i * nc + j]
    if r >= 0: sl.append((Fe[i, j] - Fe.flat[r]) / cellc)
res["network_slope_p10_p50_p90"] = [float(np.percentile(sl, q)) for q in (10, 50, 90)]
print(json.dumps(res, indent=1)); json.dump(res, open(f"{name}_net.json", "w"), indent=1)
np.savez(f"{name}_net.npz", Ec=Ec, F0=F0, Fe=Fe, A=A, rec=rec)
ext = (-size / 2000, size / 2000, -size / 2000, size / 2000)
fig, ax = plt.subplots(1, 2, figsize=(14, 7))
ax[0].imshow(fine["carve"], cmap="magma", origin="lower", extent=ext, vmin=-200, vmax=0)
yy, xx = np.nonzero((A > 200) & land)
ax[0].scatter((xx + 0.5) / nc * size / 1000 - size / 2000, (yy + 0.5) / nc * size / 1000 - size / 2000,
              s=np.clip(np.log10(A[yy, xx]) - 1.5, 0.2, 4) ** 2, c="cyan")
ax[0].set_title(f"{name}: valleys (carving) and the 4.8 km drainage network (A > 200 km2)")
ax[1].imshow(np.where(land, Ec, np.nan), cmap="gray", origin="lower", extent=ext)
ax[1].imshow(np.where((F0 - Ec > 1) & land, F0 - Ec, np.nan), cmap="cool", origin="lower", extent=ext, vmin=0, vmax=100)
ax[1].set_title("coarse lakes (filled depth)")
plt.savefig(f"{name}_net.png", dpi=70, bbox_inches="tight")
