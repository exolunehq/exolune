import numpy as np
E = np.load("transect.npy"); d = np.load("transect_d.npy"); kind = np.load("kind.npy"); sl = np.load("slopes.npy")
inl = d >= 0
def reach(h):
    out = np.full(len(E), np.nan)
    for i in range(len(E)):
        k = np.nonzero(E[i, inl] >= h)[0]
        if len(k): out[i] = d[inl][k[0]]
    return out
for h in [0.5, 1, 2, 3, 4, 15]:
    r = reach(h)
    print(f"h={h:4} m: width p10 {np.nanpercentile(r,10):5.0f}  p25 {np.nanpercentile(r,25):5.0f}  p50 {np.nanpercentile(r,50):5.0f}  p75 {np.nanpercentile(r,75):5.0f}  p90 {np.nanpercentile(r,90):5.0f}  >200 m {(np.nan_to_num(r, nan=1e9)>200).mean():.2f}")
# mean slope over the first 3 m of rise (the beach face) vs the slope 10 m scale
r3 = reach(3.0)
print("mean slope from 0 to 3 m: p10/p50/p90", np.nanpercentile(3.0 / r3, [10, 50, 90]).round(3), " share > 0.18 (steeper than any beach face)", np.nanmean(3.0 / r3 > 0.18).round(2), " share < 0.01 (tidal flat)", np.nanmean(3.0 / r3 < 0.01).round(2))
