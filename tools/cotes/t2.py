# Coast survey: shoreline points found along random arcs (weighted by coastline length), then slopes at several
# scales, a transect inland and offshore, and the terrain type there.
import numpy as np, cp, time
rng = np.random.default_rng(7)
cp.set_cell(0.5)  # full detail: what the mesh carries near the ground
M, S, STEP = 1500, 150, 1000.0
p0 = rng.normal(size=(M, 3)); p0 /= np.linalg.norm(p0, axis=1, keepdims=True)
t1, t2 = cp.tangent_basis(p0)
ang = rng.uniform(0, 2*np.pi, M)
dirs = np.cos(ang)[:, None] * t1 + np.sin(ang)[:, None] * t2
t = time.time()
s = np.arange(S) * STEP
P = np.concatenate([cp.move(np.repeat(p0[i:i+1], S, 0), np.repeat(dirs[i:i+1], S, 0), s) for i in range(M)])
E = cp.elevation(P).reshape(M, S)
print("arcs", round(time.time() - t, 1), "s, land share", (E > 0).mean().round(3))
ii, jj = np.nonzero(np.sign(E[:, :-1]) != np.sign(E[:, 1:]))
print("crossings", len(ii))
a = s[jj].astype(float); b = a + STEP
pa = p0[ii]; da = dirs[ii]; ea = E[ii, jj]
for _ in range(18):
    m = 0.5 * (a + b)
    em = cp.elevation(cp.move(pa, da, m))
    same = np.sign(em) == np.sign(ea)
    a = np.where(same, m, a); b = np.where(same, b, m)
shore = cp.move(pa, da, 0.5 * (a + b))
np.save("shore.npy", shore)
print("shore points", len(shore), "residual |e| p95", np.percentile(np.abs(cp.elevation(shore)), 95).round(3))
