# The report's figure: complexplanet's river valleys and what water would do in them.
import heapq, json, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cp import *

g = np.load("global.npz"); E = g["e"]; n, m = E.shape
land = E > 0
# global closed basins, longitude wrapped
F = np.full(E.shape, np.inf); done = ~land; F[done] = E[done]
h = [(E[i, j], i, j) for i, j in zip(*np.nonzero(done))]; heapq.heapify(h)
while h:
    z, i, j = heapq.heappop(h)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            a, b = i + di, (j + dj) % m
            if 0 <= a < n and not done[a, b]:
                done[a, b] = True; F[a, b] = max(E[a, b], z); heapq.heappush(h, (F[a, b], a, b))

# longitudinal profile along the plain window's longest big-valley centreline
info = json.load(open("plain.json")); pl = np.load("plain.npz"); Ep = pl["E"]; npx = Ep.shape[0]
la, lo = np.radians(info["lat"]), np.radians(info["lon"])
p = window([np.cos(la) * np.cos(lo), np.sin(la), np.cos(la) * np.sin(lo)], info["cell"] * npx, npx)
_, _, _, n0, _ = river_positions(Ctx(info["cell"]), p, parts=True); n0 = n0.reshape(npx, npx)
cs = plt.contour(n0, levels=[0.0]); segs = sorted(cs.allsegs[0], key=len)[::-1]; plt.close("all")
seg = segs[0]
d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(seg, axis=0).T))]) * info["cell"] / 1000
zz = Ep[np.clip(np.round(seg[:, 1]).astype(int), 0, npx - 1), np.clip(np.round(seg[:, 0]).astype(int), 0, npx - 1)]

net = np.load("plain_net.npz"); A = net["A"]; Ec = net["Ec"]; nc = Ec.shape[0]
tar = np.load("tarns2.npz")
fig, ax = plt.subplots(2, 3, figsize=(21, 12))
a = ax[0, 0]; a.set_title("a. Vallées de rivières de complexplanet (creusement, m), terres seules", fontsize=11)
a.imshow(np.where(g["nb"] > 0, g["carve"], np.nan), cmap="magma", extent=(-180, 180, -90, 90), vmin=-200, vmax=0)
a.set_facecolor("#9ec6e8")
a = ax[0, 1]; a.set_title("b. Cuvettes fermées à l'échelle des continents (mailles de 55 km) : 41 % des terres", fontsize=11)
a.imshow(np.where(land, E, np.nan), cmap="gray", extent=(-180, 180, -90, 90), vmin=0, vmax=3000)
a.imshow(np.where(land & (F - E > 1), F - E, np.nan), cmap="cool", extent=(-180, 180, -90, 90), vmin=0, vmax=600)
a.set_facecolor("#9ec6e8")
a = ax[0, 2]; s = info["cell"] * npx / 2000; ext = (-s, s, -s, s)
a.set_title("c. Plaine 600 km : vallées (sombre) et réseau de drainage calculé à 4,8 km", fontsize=11)
a.imshow(pl["carve"], cmap="magma", origin="lower", extent=ext, vmin=-200, vmax=0)
yy, xx = np.nonzero((A > 200) & (Ec > 0))
a.scatter((xx + 0.5) / nc * 2 * s - s, (yy + 0.5) / nc * 2 * s - s, s=np.clip(np.log10(A[yy, xx]) - 1.5, 0.2, 4) ** 2, c="cyan")
a.plot((seg[:, 0] + 0.5) / npx * 2 * s - s, (seg[:, 1] + 0.5) / npx * 2 * s - s, c="lime", lw=1)
a.set_xlabel("km")
a = ax[1, 0]; a.set_title("d. Profil en long du fond de la vallée verte (c) : il monte et descend", fontsize=11)
a.plot(d, zz, c="k"); a.set_xlabel("distance le long de la vallée (km)"); a.set_ylabel("altitude du fond (m)"); a.grid(alpha=0.3)
a = ax[1, 1]; a.set_title("e. Plaine 600 km : eau si chaque cuvette est remplie (19 % des terres)", fontsize=11)
dep = pl["depth"]
a.imshow(Ep, cmap="gray", origin="lower", extent=ext)
a.imshow(np.where((dep > 1) & (Ep > 0), dep, np.nan), cmap="cool", origin="lower", extent=ext, vmin=0, vmax=100)
a.set_xlabel("km")
a = ax[1, 2]; a.set_title("f. Montagne 12 km, mailles de 30 m : cuvettes remplies (11 %)", fontsize=11)
Et = tar["E"]; s2 = 6
a.imshow(Et, cmap="gray", origin="lower", extent=(-s2, s2, -s2, s2))
a.imshow(np.where(tar["depth"] > 1, tar["depth"], np.nan), cmap="cool", origin="lower", extent=(-s2, s2, -s2, s2), vmin=0, vmax=60)
a.set_xlabel("km")
plt.tight_layout()
plt.savefig("rivieres-complexplanet.jpg", dpi=60, pil_kwargs={"quality": 82})
print("profile length km %.0f, z range %.0f..%.0f" % (d[-1], zz.min(), zz.max()))
