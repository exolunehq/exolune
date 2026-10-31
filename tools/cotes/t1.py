import numpy as np, cp
def d(lat, lon):
    a, b = np.radians(lat), np.radians(lon)
    return np.array([np.cos(a)*np.cos(b), np.sin(a), np.cos(a)*np.sin(b)])
sites = [(4.72962, -146.52288, 1272.7), (-37.40219, 14.81078, 1861.1), (-5.05673, -166.69451, 4353.7), (17.9226, -115.98272, 1644.7)]
cp.set_cell(0.5)
p = np.array([d(a, b) for a, b, _ in sites])
e = cp.elevation(p)
for (a, b, g), x in zip(sites, e): print(a, b, "engine", g, "cpu", round(x, 1))
