# A. Global map: land, terrain types, river carving; picks windows for the next steps.
import time, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cp import *

t0 = time.time()
NLAT, NLON = 360, 720  # 0.5 deg
p = latlon(NLAT, NLON)
ctx = Ctx(R * np.radians(0.5))      # terrain filtered like a 55 km mesh cell
d = elevation(ctx, p, extra=True)
ctxr = Ctx(1000.0)                  # rivers unfiltered
rp, cu0, cu1, n0, n1 = river_positions(ctxr, p, parts=True)
carve = d["riv_a"] * (rp - 1) * RIVER_DEPTH / 2 * MAX_ELEV   # m, <= 0
print("time", time.time() - t0)
e = d["elev"].reshape(NLAT, NLON); land = d["norivers"] > 0
lat = np.repeat(np.linspace(90 - 0.25, -90 + 0.25, NLAT), NLON)
w = np.cos(np.radians(lat))
def share(m, base=None):
    base = np.ones_like(m, bool) if base is None else base
    return (w * (m & base)).sum() / (w * base).sum()
print("land share %.3f" % share(land))
print("mountain share of land %.3f, hills %.3f" % (share(d["mount_a"] > 0.5, land), share((d["hills_a"] > 0.5) & (d["mount_a"] <= 0.5), land)))
nb = d["norivers"][land] * 1  # m
for q in (10, 25, 50, 75, 90, 99): print("land elev p%d %.0f m" % (q, np.percentile(nb, q)))
print("land: riv_a mean %.2f; share riv_a>0.9 %.2f; share riv_a<0.1 %.2f" % (
    (w * d["riv_a"] * land).sum() / (w * land).sum(), share(d["riv_a"] > 0.9, land), share(d["riv_a"] < 0.1, land)))
for thr in (-10, -50, -100, -150):
    print("land share carved deeper than %d m: %.3f" % (-thr, share(carve < thr, land)))
print("share of land in big-river floor (cu0<-0.9): %.3f; small-river floor (cu1<0.6 & cu1<cu0): %.3f" % (
    share(cu0 < -0.9, land), share((cu1 < 0.6) & (cu1 < cu0), land)))
np.savez("global.npz", e=e, carve=carve.reshape(NLAT, NLON), rp=rp.reshape(NLAT, NLON), nb=d["norivers"].reshape(NLAT, NLON),
         mount=d["mount_a"].reshape(NLAT, NLON), riv_a=d["riv_a"].reshape(NLAT, NLON))
fig, ax = plt.subplots(2, 1, figsize=(14, 14))
ax[0].imshow(np.where(e > 0, e, np.nan), cmap="terrain", extent=(-180, 180, -90, 90), vmin=0, vmax=4000)
ax[0].imshow(np.where(e <= 0, 1, np.nan), cmap="Blues", extent=(-180, 180, -90, 90), vmin=0, vmax=2)
ax[0].set_title("elevation (land), sea in blue")
ax[1].imshow(np.where(d["norivers"].reshape(NLAT, NLON) > 0, carve.reshape(NLAT, NLON), np.nan), cmap="magma",
             extent=(-180, 180, -90, 90), vmin=-200, vmax=0)
ax[1].set_title("river carving on land (m)")
for a in ax: a.grid(True, alpha=0.3)
plt.savefig("global.png", dpi=80, bbox_inches="tight")
