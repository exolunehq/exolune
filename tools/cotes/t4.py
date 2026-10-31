# Which noise sets the slope at the shore: finite differences of each component of the elevation.
import numpy as np, cp
cp.set_cell(0.5)
P = np.load("shore.npy"); N = len(P); kind = np.load("kind.npy")
t1, t2 = cp.tangent_basis(P)
def comp_grad(D):
    out = {}
    for sgn, tt in ((1, t1), (2, t2)):
        ep, dp = cp.elevation(cp.move(P, tt, np.full(N, D)), diag=True)
        em, dm = cp.elevation(cp.move(P, tt, np.full(N, -D)), diag=True)
        for k in ("bce", "plains", "river"):
            out.setdefault(k, []).append((dp[k] - dm[k]) / (2 * D))
        out.setdefault("total", []).append((ep - em) / (2 * D))
    return {k: np.hypot(*v) for k, v in out.items()}
pl = kind == "plaines"
for D in (10, 100, 1000):
    g = comp_grad(D)
    print(f"D={D:4d} m, plains coasts, median slope: total {np.median(g['total'][pl]):.4f}  continent {np.median(g['bce'][pl]):.4f}  plains noise {np.median(g['plains'][pl]):.4f}  rivers {np.median(g['river'][pl]):.4f}")
# continent octaves: slope of base continent alone per octave count (no plains)
