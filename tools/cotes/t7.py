# Large scale: offshore distance to -130 m (a real shelf break) and to -700 m (complexplanet's shelf select), inland to 100 m.
import numpy as np, cp
cp.set_cell(100.0)
P = np.load("shore.npy")[:150]; N = len(P)
t1, t2 = cp.tangent_basis(P)
D = 1000.0
gx = (cp.elevation(cp.move(P, t1, np.full(N, D))) - cp.elevation(cp.move(P, t1, np.full(N, -D)))) / (2 * D)
gy = (cp.elevation(cp.move(P, t2, np.full(N, D))) - cp.elevation(cp.move(P, t2, np.full(N, -D)))) / (2 * D)
up = (gx[:, None] * t1 + gy[:, None] * t2) / np.hypot(gx, gy)[:, None]
d = np.arange(0, 300001, 1000.0)
off = np.stack([cp.elevation(cp.move(P, -up, np.full(N, x))) for x in d], 1)
on = np.stack([cp.elevation(cp.move(P, up, np.full(N, x))) for x in d[:101]], 1)
def first(A, cond, dd):
    return np.array([dd[np.nonzero(cond(a))[0][0]] if cond(a).any() else np.nan for a in A])
for h in (-130, -700, -2000):
    r = first(off, lambda a: a <= h, d) / 1000
    print(f"offshore to {h} m: p10 {np.nanpercentile(r,10):.0f} km  p50 {np.nanpercentile(r,50):.0f} km  p90 {np.nanpercentile(r,90):.0f} km  never in 300 km {np.isnan(r).mean():.2f}")
for h in (50, 100, 300):
    r = first(on, lambda a: a >= h, d[:101]) / 1000
    print(f"inland to {h} m: p10 {np.nanpercentile(r,10):.1f} km  p50 {np.nanpercentile(r,50):.1f} km  p90 {np.nanpercentile(r,90):.1f} km  never in 100 km {np.isnan(r).mean():.2f}")
