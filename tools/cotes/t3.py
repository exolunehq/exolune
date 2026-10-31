import numpy as np, cp
cp.set_cell(0.5)
P = np.load("shore.npy"); N = len(P)
t1, t2 = cp.tangent_basis(P)
e0, dg = cp.elevation(P, diag=True)
kind = np.where(dg["ba"] > 0.5, "badlands", np.where(dg["ma"] > 0.5, "montagnes", np.where(dg["ha"] > 0.5, "collines", "plaines")))
print("terrain at the shore:", {k: int((kind == k).sum()) for k in np.unique(kind)})
print("continentDef at shore p5/50/95", np.percentile(dg["cd"], [5, 50, 95]).round(4), "plains offset m p5/50/95", np.percentile(dg["plains"], [5, 50, 95]).round(1))
print("river term at shore m p5/50/95", np.percentile(dg["river"], [5, 50, 95]).round(1), "riversAlpha median", np.median(dg["ra"]).round(2))
scales = [1, 3, 10, 30, 100, 300, 1000, 3000]
slope = {}
for D in scales:
    gx = (cp.elevation(cp.move(P, t1, np.full(N, D))) - cp.elevation(cp.move(P, t1, np.full(N, -D)))) / (2 * D)
    gy = (cp.elevation(cp.move(P, t2, np.full(N, D))) - cp.elevation(cp.move(P, t2, np.full(N, -D)))) / (2 * D)
    slope[D] = np.hypot(gx, gy)
    if D == 30: up = (gx[:, None] * t1 + gy[:, None] * t2) / np.hypot(gx, gy)[:, None]
print("\nslope (tan) at the shoreline, by baseline 2*D:  p10 / p50 / p90 / share>0.65 (rock)")
for D in scales:
    v = slope[D]; print(f"  D={D:5d} m  {np.percentile(v,10):.3f} / {np.percentile(v,50):.3f} / {np.percentile(v,90):.3f}   rock {(v>0.65).mean():.3f}")
for k in np.unique(kind):
    m = kind == k
    print(f"  {k:10s} n={m.sum():3d}  D=10: median {np.median(slope[10][m]):.3f}  D=100: {np.median(slope[100][m]):.3f}  D=1000: {np.median(slope[1000][m]):.3f}")
# transect along the steepest ascent at 30 m
d = np.concatenate([np.arange(-2000, 0, 20), np.arange(0, 500, 2), np.arange(500, 3001, 10)]).astype(float)
E = np.stack([cp.elevation(cp.move(P, up, np.full(N, x))) for x in d], 1)
np.save("transect.npy", E); np.save("transect_d.npy", d); np.save("kind.npy", kind)
inland = d >= 0
def first_reach(h):
    out = np.full(N, np.nan)
    for i in range(N):
        k = np.nonzero(E[i, inland] >= h)[0]
        if len(k): out[i] = d[inland][k[0]]
    return out
print("\ndistance inland (m) to first reach h: p10 / p50 / p90 / never within 3 km")
for h in [2, 5, 15, 25, 50, 100]:
    r = first_reach(h); ok = ~np.isnan(r)
    print(f"  h={h:3d} m  {np.nanpercentile(r,10):6.0f} / {np.nanpercentile(r,50):6.0f} / {np.nanpercentile(r,90):6.0f}   never {(~ok).mean():.2f}")
for x in [10, 50, 100, 200, 500, 1000]:
    j = np.argmin(np.abs(d - x)); print(f"  elevation {x:5d} m inland: p10 {np.percentile(E[:,j],10):6.1f}  p50 {np.percentile(E[:,j],50):6.1f}  p90 {np.percentile(E[:,j],90):6.1f}")
for x in [-50, -200, -1000, -2000]:
    j = np.argmin(np.abs(d - x)); print(f"  elevation {x:5d} m offshore: p10 {np.percentile(E[:,j],10):6.1f}  p50 {np.percentile(E[:,j],50):6.1f}  p90 {np.percentile(E[:,j],90):6.1f}")
# cliff test: rise within 100 m inland of 20 m or more, and max local slope within 200 m
j100 = np.argmin(np.abs(d - 100)); j200 = np.argmin(np.abs(d - 200))
rise100 = E[:, j100]
seg = E[:, (d >= 0) & (d <= 200)]; dd = d[(d >= 0) & (d <= 200)]
maxs = np.max(np.diff(seg, axis=1) / np.diff(dd), axis=1)
print(f"\nrise over the first 100 m >= 20 m (cliff-like): {(rise100 >= 20).mean():.3f};  >= 10 m: {(rise100 >= 10).mean():.3f}")
print(f"max slope over 2 m steps within 200 m inland: p50 {np.median(maxs):.3f}  p90 {np.percentile(maxs,90):.3f}  share>0.65 {(maxs>0.65).mean():.3f}  share>1 {(maxs>1).mean():.3f}")
# Young & Carilli: backshore elevation 100 m inland > 4.4 m -> likely cliffed
print(f"elevation 100 m inland > 4.4 m (Young & Carilli 'likely cliffed' rule): {(rise100 > 4.4).mean():.3f}; mean {rise100.mean():.1f} m")
np.save("slopes.npy", np.stack([slope[D] for D in scales]))
