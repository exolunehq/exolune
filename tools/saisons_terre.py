# The seasons of the real Earth, for the tree line (docs/recherche-vegetation.md): the engine knows the annual mean
# temperature only, and trees answer to the growing season's (Körner and Paulsen: the mean of the days over 0.9 C, at
# least 6.4 C over at least 94 days). On TerraClimate's monthly normals (1991-2020, 1 degree, CC0; ../donnees-terre),
# the half amplitude of the annual cycle by latitude over land, and how well a sine of that amplitude around the annual
# mean gives the growing season's mean and length, against the months themselves.
#
# python tools/saisons_terre.py [<donnees-terre folder>]
import os, sys
import numpy as np

FOLDER = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "donnees-terre")
THRESHOLD, SEASON_MEAN, SEASON_DAYS = 0.9, 6.4, 94.0


def grid(name):
    # The OPeNDAP ASCII dump: rows "[month][lat], v, v, ...", int16, -32768 for no data; packed as tenths of a degree above
    # -73 C, as the annual means derived from them, temperature_annuelle_1deg.csv, give exactly (correlation 1.0000).
    out = np.full((12, 180, 360), np.nan, np.float32)
    for line in open(os.path.join(FOLDER, f"terraclimate_{name}_1deg.ascii")):
        if not line.startswith("["):
            continue
        head, _, rest = line.partition("],")
        m, lat = (int(x) for x in head.strip("[").split("]["))
        values = np.array(rest.split(","), np.float32)
        values[values == -32768] = np.nan
        out[m, lat] = values * 0.1 - 73.0
    return out


def sine_season(mean, amplitude):
    # The season of a sine T(t) = mean + amplitude cos(2 pi t): its days over THRESHOLD and their mean. Closed form.
    c = np.clip((THRESHOLD - mean) / np.maximum(amplitude, 1e-3), -1.0, 1.0)
    theta = np.arccos(c)
    days = 365.0 * theta / np.pi
    season = mean + amplitude * np.sin(theta) / np.maximum(theta, 1e-6)
    return days, season


def ok(days, season):
    return (days >= SEASON_DAYS) & (season >= SEASON_MEAN)


if __name__ == "__main__":
    monthly = 0.5 * (grid("tmax") + grid("tmin"))  # monthly mean temperature
    lats = 89.5 - np.arange(180)
    mean = np.nanmean(monthly, axis=0)
    amplitude = 0.5 * (np.nanmax(monthly, axis=0) - np.nanmin(monthly, axis=0))
    land = np.isfinite(mean) & (lats[:, None] > -60)
    # The months' own season: months over the threshold, their mean, 30.4 days each.
    warm = monthly > THRESHOLD
    days = 30.4 * warm.sum(axis=0)
    season = np.where(warm.any(axis=0), np.nansum(np.where(warm, monthly, 0.0), axis=0) / np.maximum(warm.sum(axis=0), 1), np.nan)
    sdays, sseason = sine_season(mean, amplitude)
    print("| latitude | demi-amplitude médiane | 25-75 % | modèle 1 + 17 sin² |")
    print("|---|---|---|---|")
    fit_x, fit_y = [], []
    for band in range(-55, 80, 10):
        rows = (np.abs(lats) >= abs(band)) & (np.abs(lats) < abs(band) + 10) & (np.sign(lats) == np.sign(band if band else 1))
        a = amplitude[rows][land[rows]]
        if a.size < 20:
            continue
        s2 = np.sin(np.radians(band + 5 * np.sign(band if band else 1))) ** 2
        fit_x.append(s2), fit_y.append(np.median(a))
        print(f"| {band:+d} à {band + 10 * np.sign(band if band else 1):+d}° | {np.median(a):.1f} °C | {np.percentile(a, 25):.1f} à {np.percentile(a, 75):.1f} | {1 + 17 * s2:.1f} |")
    # Least squares of A = a + b sin^2(latitude), over every land cell.
    s2 = np.sin(np.radians(lats))[:, None] ** 2 * np.ones((1, 360))
    X = np.stack([np.ones(land.sum()), s2[land]], axis=1)
    coef = np.linalg.lstsq(X, amplitude[land], rcond=None)[0]
    print(f"\nmoindres carrés sur les terres : A = {coef[0]:.2f} + {coef[1]:.2f} sin²(latitude)")
    model = coef[0] + coef[1] * s2
    mdays, mseason = sine_season(mean, model)
    trees, sine_trees, model_trees = ok(days, season), ok(sdays, sseason), ok(mdays, mseason)
    agree = lambda a, b: float((a[land] == b[land]).mean())
    print(f"saison au-dessus de {THRESHOLD} °C, moyenne de la sinusoïde contre les mois : écart médian "
          f"{np.nanmedian(np.abs(sseason - season)[land & warm.any(axis=0)]):.2f} °C ; jours {np.nanmedian(np.abs(sdays - days)[land]):.0f}")
    print(f"arbres possibles (>= {SEASON_MEAN} °C sur >= {SEASON_DAYS:.0f} jours), part des terres : mois {trees[land].mean():.3f}, "
          f"sinusoïde mesurée {sine_trees[land].mean():.3f}, sinusoïde du modèle {model_trees[land].mean():.3f}")
    print(f"accord cellule par cellule avec les mois : sinusoïde mesurée {agree(trees, sine_trees):.3f}, modèle {agree(trees, model_trees):.3f}")
    # The polar limit of trees at sea level-ish cells, by the months and by the model: the highest latitude with trees.
    for name, t in (("mois", trees), ("modèle", model_trees)):
        north = [lats[i] for i in range(180) if (t[i] & land[i]).sum() > 0.5 * max(land[i].sum(), 1) and lats[i] > 0]
        print(f"{name} : la moitié des terres d'une latitude ou plus porte des arbres jusqu'à {max(north) if north else float('nan'):.1f}° N")
