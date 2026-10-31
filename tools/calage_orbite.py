# The references behind the orbit view's constants (docs/spec-rendu-orbite.md), by Monte Carlo, on the CPU:
#   python tools/calage_orbite.py air      the air seen from orbit over a black ground: single and multiple scattering,
#                                          Rayleigh alone and with the haze (PlanetSettings.hlsli), for the similarity
#                                          scaling of the haze's multiple scattering (Atmosphere.hlsli)
#   python tools/calage_orbite.py nuages   a cloud slab, Henyey-Greenstein g 0.85: its radiance factors seen from above
#                                          and below, then the fit of the clouds' multiple scattering (Clouds.hlsli,
#                                          CLOUD_MULTI_*); a few minutes
# Radiance factor: pi L / (mu0 E), E the sun's irradiance normal to it.
import sys
import numpy as np

PI = np.pi
rng = np.random.default_rng(3)


def hg(c, g):
    return (1 - g * g) / (4 * PI * (1 + g * g - 2 * g * c) ** 1.5)


def sample_hg(g, n):
    s = (1 - g * g) / (1 - g + 2 * g * rng.random(n))
    return (1 + g * g - s * s) / (2 * g)


def sample_rayleigh(n):
    out, k = np.empty(n), 0
    while k < n:
        c = rng.uniform(-1, 1, 2 * n)
        keep = c[rng.random(2 * n) < (1 + c * c) / 2][:n - k]
        out[k:k + keep.size] = keep
        k += keep.size
    return out


def turn(d, ct):
    """Directions d turned by the cosines ct, at a random azimuth."""
    st, ph = np.sqrt(np.maximum(0, 1 - ct * ct)), 2 * PI * rng.random(ct.size)
    a = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
    u1 = np.cross(d, a)
    u1 /= np.linalg.norm(u1, axis=1, keepdims=True)
    u2 = np.cross(d, u1)
    return ct[:, None] * d + (st * np.cos(ph))[:, None] * u1 + (st * np.sin(ph))[:, None] * u2


def air(tau_rayleigh, tau_haze, sun_zenith_deg, n=400000):
    """The air over a black ground, seen at nadir from above: (single, total). Rayleigh in 8 km of scale height, the
    haze uniform under 2 km, scattering 0.9 of its extinction, HG 0.7 (PlanetSettings.hlsli)."""
    z = np.linspace(0, 100, 20001)
    d_r, d_a = tau_rayleigh / 8 * np.exp(-z / 8), np.where(z < 2, tau_haze / 2, 0.0)
    ext = d_r + d_a
    above = np.concatenate([[0], np.cumsum(((ext[1:] + ext[:-1]) / 2 * np.diff(z))[::-1])])[::-1]
    mu0 = np.cos(np.radians(sun_zenith_deg))
    d = np.tile([np.sin(np.radians(sun_zenith_deg)), 0.0, -mu0], (n, 1))  # z up
    tau, w = np.zeros(n), np.ones(n)
    alive, first = np.ones(n, bool), np.ones(n, bool)
    single = total = 0.0
    for _ in range(200):
        i = np.nonzero(alive)[0]
        if i.size == 0:
            break
        tau[i] -= np.log(rng.random(i.size)) * -d[i, 2]
        out = (tau[i] < 0) | (tau[i] > above[0])
        alive[i[out]] = False
        i = i[~out]
        h = np.interp(-tau[i], -above, z)
        haze = rng.random(i.size) < np.interp(h, z, d_a) / (np.interp(h, z, d_r) + np.interp(h, z, d_a))
        w[i[haze]] *= 0.9
        c = d[i, 2]  # toward the viewer, straight up
        seen = w[i] * np.where(haze, hg(c, 0.7), 3 / (16 * PI) * (1 + c * c)) * np.exp(-tau[i])
        total += seen.sum()
        single += seen[first[i]].sum()
        first[i] = False
        d[i] = turn(d[i], np.where(haze, sample_hg(0.7, i.size), sample_rayleigh(i.size)))
    return PI * single / n, PI * total / n


def slab(tau, mu0, g=0.85, n=150000):
    """A conservative cloud slab over a black ground: (R seen at nadir from above, diffuse T seen at the zenith from
    below)."""
    d = np.tile([np.sqrt(1 - mu0 * mu0), 0.0, mu0], (n, 1))  # z down, into the cloud
    z, alive = np.zeros(n), np.ones(n, bool)
    r = t = 0.0
    for _ in range(4000):
        i = np.nonzero(alive)[0]
        if i.size == 0:
            break
        z[i] -= np.log(rng.random(i.size)) * d[i, 2]
        out = (z[i] < 0) | (z[i] > tau)
        alive[i[out]] = False
        i = i[~out]
        r += np.sum(hg(-d[i, 2], g) * np.exp(-z[i]))
        t += np.sum(hg(d[i, 2], g) * np.exp(-(tau - z[i])))
        d[i] = turn(d[i], sample_hg(g, i.size))
    return PI * r / n, PI * t / n


# The clouds' light on a slab as Clouds.hlsli computes it, fine steps: single scattering HG 0.85, the multiple's
# isotropic source sigma S W mu / (1 + b tau_s) / 4 pi, a slab's diffuse transmission toward the sun, summed along the
# view and scaled by F = 1 - e^(-k tau_view / mu);
# tau_s from the six sun samples, 7.875 km at most; sigma 40 /km.
SIGMA, SUN_REACH = 40.0, 7.875


def model(p, mu0, tau, view):
    W, b, k = p
    h = tau / SIGMA
    ds = min(0.002, h / 200)
    s = np.arange(ds / 2, h, ds)
    depth = s if view == "R" else h - s
    tau_s = SIGMA * np.minimum(depth / mu0, SUN_REACH)
    seen = np.exp(-SIGMA * s)
    single = np.sum(seen * SIGMA * np.exp(-tau_s) * hg(-mu0 if view == "R" else mu0, 0.85))
    multiple = np.sum(seen * SIGMA * W * mu0 * / (1 + b * tau_s) / (4 * PI)) * (1 - np.exp(-k * tau / mu0))
    return (single + multiple) * ds * PI / mu0


def fit_clouds():
    targets = []
    for mu0 in (1.0, 0.5):
        for tau in (2, 5, 10, 20, 50, 100):
            r, t = slab(tau, mu0)
            targets.append((mu0, tau, "R", r))
            if mu0 < 1 or tau >= 20:  # straight under the sun, a thin cloud's T is its aureole
                targets.append((mu0, tau, "T", t))
            print(f"Monte Carlo  mu0 {mu0}  tau {tau:3d}  R {r:.3f}  T {t:.3f}", flush=True)

    def cost(p):
        return sum(np.log(max(model(p, m, tau, v), 1e-5) / val) ** 2 for m, tau, v, val in targets)

    x, step = np.array([3.40, 0.040, 0.061]), np.array([0.9, 0.012, 0.018])
    for _ in range(100):
        for i in range(3):
            for sign in (1, -1):
                y = x.copy()
                y[i] = max(y[i] + sign * step[i], 1e-5)
                if cost(y) < cost(x):
                    x = y
        step *= 0.9
    print(f"W {x[0]:.3f}  b {x[1]:.4f}  k {x[2]:.4f}  rms log error {np.sqrt(cost(x) / len(targets)):.2f}")
    for m, tau, v, val in targets:
        print(f"  mu0 {m}  tau {tau:3d}  {v}  Monte Carlo {val:.3f}  model {model(x, m, tau, v):.3f}")


if __name__ == "__main__":
    if sys.argv[1:] == ["air"]:
        haze = 3.912 / 40.0 - 13.558e-3  # the haze's extinction per km at 550 nm (VISIBILITY_KM), over its 2 km
        for name, tr, ta in (("680 nm", 0.046, 2 * haze * 0.759), ("550 nm", 0.108, 2 * haze),
                             ("440 nm", 0.265, 2 * haze * 1.337)):
            s, t = air(tr, ta, 17)
            s0, t0 = air(tr, 0.0, 17)
            print(f"{name}: haze  single {s:.4f} total {t:.4f} multiple/single {t / s - 1:.2f};"
                  f"  Rayleigh alone  single {s0:.4f} total {t0:.4f} multiple/single {t0 / s0 - 1:.2f}")
    elif sys.argv[1:] == ["nuages"]:
        fit_clouds()
    else:
        print(__doc__ or "usage: python tools/calage_orbite.py air | nuages")
