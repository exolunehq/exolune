# Distance to the shore estimated as h / |grad h_L|, h_L the elevation without octaves under L, by forward differences
# at a fixed step on the planet: against the distance along the transect.
import numpy as np, cp
P = np.load("shore.npy"); N = len(P)
t1, t2 = cp.tangent_basis(P)
cp.set_cell(0.5)
gx = (cp.elevation(cp.move(P, t1, np.full(N, 30.0))) - cp.elevation(cp.move(P, t1, np.full(N, -30.0)))) / 60
gy = (cp.elevation(cp.move(P, t2, np.full(N, 30.0))) - cp.elevation(cp.move(P, t2, np.full(N, -30.0)))) / 60
up = (gx[:, None] * t1 + gy[:, None] * t2) / np.hypot(gx, gy)[:, None]
for L in (50.0, 200.0, 1000.0):
    print(f"--- low-pass: octaves under ~{L:.0f} m removed, step {L/4:.0f} m")
    for D in (10.0, 25.0, 50.0, 100.0, 200.0, 400.0):
        Q = cp.move(P, up, np.full(N, D))
        cp.set_cell(0.5); h = cp.elevation(Q)
        cp.set_cell(L / 4); st = L / 4
        b1, b2 = cp.tangent_basis(Q)
        h0 = cp.elevation(Q)
        sL = np.hypot(cp.elevation(cp.move(Q, b1, np.full(N, st))) - h0, cp.elevation(cp.move(Q, b2, np.full(N, st))) - h0) / st
        ok = h > 0
        est = h[ok] / np.maximum(sL[ok], 1e-4)
        ratio = est / D
        print(f"  true {D:4.0f} m: estimate p10 {np.percentile(est,10):6.0f}  p50 {np.percentile(est,50):6.0f}  p90 {np.percentile(est,90):6.0f}   within x2: {np.mean((ratio>0.5)&(ratio<2)):.2f}  (land {ok.mean():.2f})")
