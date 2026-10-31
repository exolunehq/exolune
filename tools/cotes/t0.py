import time, numpy as np, cp
rng = np.random.default_rng(1)
p = rng.normal(size=(20000, 3)); p /= np.linalg.norm(p, axis=1, keepdims=True)
for cell in (1000.0, 1.0):
    cp.set_cell(cell); t = time.time()
    e, d = cp.elevation(p[:5000], diag=True)
    print(cell, "s", round(time.time() - t, 1), "land", (e > 0).mean().round(3), "pct", np.percentile(e, [5, 25, 50, 75, 95]).round(0),
          "hills", (d["ha"] > 0.5).mean().round(3), "mnt", (d["ma"] > 0.5).mean().round(3), "bad", (d["ba"] > 0.5).mean().round(3))
