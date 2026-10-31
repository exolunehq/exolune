"""Contrôle des formules de CloudLowDensity, sans moteur ni banc de rendu."""

import math
from pathlib import Path

import numpy as np


# Mean sigma of mip 1's 2x2x2 blocks: 0.0124 for shape, 0.0323 for erosion.
# The finer octaves' geometric variance sum is carried at every mip, as in Clouds.hlsli.
SHAPE_UNRESOLVED_SIGMA = 0.0124
DETAIL_UNRESOLVED_SIGMA = 0.033


def phi(x):
    return 0.39894228040 * math.exp(-0.5 * x * x)


def cdf(x):
    """Même approximation de erf que CloudNormalCdf."""
    z = abs(x) * 0.70710678118
    t = 1.0 / (1.0 + 0.3275911 * z)
    tail = 0.5 * t * (
        0.254829592 + t * (-0.284496736 + t * (
            1.421413741 + t * (-1.453152027 + t * 1.061405429)))
    ) * math.exp(-z * z)
    return 1.0 - tail if x >= 0.0 else tail


def statistics(mu, sigma, coverage):
    """Part couverte et moments E, E2 du seuil clampé, avant profil et érosion."""
    m = mu - (1.0 - coverage)
    if sigma == 0.0:
        base = min(max(m, 0.0), coverage)
        return float(m > 0.0), base, base * base
    alpha, beta = -m / sigma, (coverage - m) / sigma
    fraction = cdf(m / sigma)
    interval, upper_tail = cdf(beta) - cdf(alpha), cdf(-beta)
    pdf_alpha, pdf_beta = phi(alpha), phi(beta)
    expected = min(max(m * interval + sigma * (pdf_alpha - pdf_beta)
                       + coverage * upper_tail, 0.0), coverage)
    expected_square = (m * m * interval + 2.0 * m * sigma * (pdf_alpha - pdf_beta)
                       + sigma * sigma * (interval - (beta * pdf_beta - alpha * pdf_alpha))
                       + coverage * coverage * upper_tail)
    expected_square = min(max(expected_square, expected * expected), coverage * expected)
    return fraction, expected, expected_square


def margin_moments(mu, sigma, coverage, p, g, detail_mean, detail_sigma):
    """Moyenne et écart type de U = b - g D, forme et détail indépendants."""
    sigma = math.hypot(sigma, SHAPE_UNRESOLVED_SIGMA)
    detail_sigma = math.hypot(detail_sigma, DETAIL_UNRESOLVED_SIGMA)
    _, expected, expected_square = statistics(mu, sigma, coverage)
    # Factor p^2 before subtracting moments to avoid cancellation after the profile.
    return (p * expected - g * detail_mean,
            math.sqrt(p * p * max(expected_square - expected * expected, 0.0)
                      + (g * detail_sigma) ** 2))


def density_statistics(mu, sigma, coverage, p, g, detail_mean, detail_sigma):
    """Loi jointe de CloudLowDensity : part couverte et densité dans le nuage."""
    margin_mean, margin_sigma = margin_moments(mu, sigma, coverage, p, g, detail_mean, detail_sigma)
    if margin_sigma < 1.0e-4:
        fraction, positive_mean = float(margin_mean > 0.0), max(margin_mean, 0.0)
    else:
        z = margin_mean / margin_sigma
        fraction = cdf(z)
        positive_mean = max(margin_mean * fraction + margin_sigma * phi(z), 0.0)
    density = (positive_mean / fraction / max(1.0 - g * detail_mean, 1.0e-6) / coverage
               if fraction > 0.0 else 0.0)
    return fraction, density


def assert_sample(expected, samples, label):
    # Six erreurs types, plus la précision de la CDF et les arrondis.
    tolerance = 6.0 * float(samples.std()) / math.sqrt(samples.size) + 2.0e-6
    assert abs(expected - float(samples.mean())) < tolerance, (label, expected, samples.mean(), tolerance)


def mip1_sigma(values, side):
    """Measure the mean standard deviation inside mip 1's 2x2x2 blocks of mip 0."""
    blocks = values.reshape(side // 2, 2, side // 2, 2, side // 2, 2)
    return float(np.sqrt(blocks.var(axis=(1, 3, 5))).mean())


def check_textures(rng):
    """Les deux contrôles mesurés, contre le champ fin tiré dans nos textures."""
    assets = Path(__file__).resolve().parents[1] / "assets" / "clouds"
    shape = np.fromfile(assets / "shape128.rgba8mips", dtype=np.uint8)
    detail = np.fromfile(assets / "detail32.rgba8mips", dtype=np.uint8)
    fine_shape = shape[:4 * 128 ** 3:4].astype(float) / 255.0
    fine_detail = detail[:4 * 32 ** 3:4].astype(float) / 255.0
    shape_fine_sigma = mip1_sigma(fine_shape, 128)
    detail_fine_sigma = mip1_sigma(fine_detail, 32)
    for measured, expected in ((shape_fine_sigma, SHAPE_UNRESOLVED_SIGMA),
                               (detail_fine_sigma, DETAIL_UNRESOLVED_SIGMA)):
        assert abs(measured - expected) <= 0.10 * expected, (measured, expected)
    print(f"Écarts types des blocs du mip 1 : forme {shape_fine_sigma:.6f}, érosion {detail_fine_sigma:.6f}")
    # Comme à l'upload : R du dernier mip, B = round(255 * min(2 sigma, 1)).
    mu, detail_mean = float(shape[-4]) / 255.0, float(detail[-4]) / 255.0
    sigma = math.floor(255.0 * min(2.0 * float(fine_shape.std()), 1.0) + 0.5) / 510.0
    detail_sigma = math.floor(255.0 * min(2.0 * float(fine_detail.std()), 1.0) + 0.5) / 510.0
    x = rng.choice(fine_shape, 2_000_000)
    d = rng.choice(fine_detail, x.size)
    # Extend the texture samples by the same independent subtexel populations as the shader.
    x += SHAPE_UNRESOLVED_SIGMA * rng.standard_normal(x.size)
    d += DETAIL_UNRESOLVED_SIGMA * rng.standard_normal(d.size)
    for coverage, p, g in ((0.2, 1.0, 0.09), (0.3, 0.6, 0.19)):
        fraction, density = density_statistics(mu, sigma, coverage, p, g, detail_mean, detail_sigma)
        margin = p * np.clip(x - (1.0 - coverage), 0.0, coverage) - g * d
        true_fraction = float((margin > 0.0).mean())
        true_mean = float((np.maximum(margin, 0.0) / (1.0 - g * d) / coverage).mean())
        # La fermeture normale est une approximation ; ses erreurs restent celles des contrôles mesurés.
        assert abs(fraction - true_fraction) < 0.012, (coverage, fraction, true_fraction)
        assert abs(fraction * density - true_mean) < 0.010, (coverage, fraction * density, true_mean)
        print(f"Textures c={coverage:.1f}, p={p:g}, g={g:g} : f {fraction:.3f} / {true_fraction:.3f},"
              f" densité moyenne {fraction * density:.3f} / {true_mean:.3f} (moments RGBA8)")


def main():
    for x in np.linspace(-10.0, 10.0, 2001):
        assert abs(cdf(x) - 0.5 * math.erfc(-x / math.sqrt(2.0))) < 1.0e-4

    # Une population fixe de normales, partagée entre les cas pour rendre le contrôle reproductible.
    rng = np.random.default_rng(20261031)
    normal = rng.standard_normal(2_000_000)
    cases = [
        (0.50, 0.10, 0.50),  # moyenne sur le seuil
        (0.70, 0.15, 0.40),
        (0.90, 0.20, 0.60),  # saturation supérieure fréquente
        (0.25, 0.18, 0.35),  # faible part couverte
        (0.40, 0.30, 0.90),  # les deux bornes coupent la population
        (0.92, 0.04, 0.10),
        (0.65, 0.001, 0.35), # faible variance, moyenne au seuil
        (0.10, 0.001, 0.20),
        (0.95, 0.001, 0.40),
        (0.45, 0.20, 1.00),
        (0.65, 0.0002, 0.35),
    ]
    for mu, sigma, coverage in cases:
        x = mu + sigma * normal
        covered = x > 1.0 - coverage
        clamped = np.clip(x - (1.0 - coverage), 0.0, coverage)
        fraction, expected, expected_square = statistics(mu, sigma, coverage)
        assert_sample(fraction, covered, (mu, sigma, coverage, "f"))
        assert_sample(expected, clamped, (mu, sigma, coverage, "E"))
        assert_sample(expected_square, clamped * clamped, (mu, sigma, coverage, "E2"))
        assert 0.0 <= expected <= coverage
        assert expected * expected <= expected_square <= coverage * expected

    joint_cases = [
        (0.50, 0.10, 0.50, 1.0, 0.15, 0.70, 0.10),
        (0.70, 0.15, 0.40, 0.6, 0.19, 0.70, 0.12),
        (0.90, 0.20, 0.60, 0.8, 0.30, 0.70, 0.10),
        (0.89, 0.05, 0.20, 1.0, 0.09, 0.70, 0.15),
        (0.89, 0.05, 0.30, 0.6, 0.19, 0.70, 0.15),
        (0.89, 0.00, 0.20, 1.0, 0.09, 0.70, 0.15), # variance du détail seul
        (0.89, 0.05, 0.20, 1.0, 0.09, 0.70, 0.00), # variance de la forme seule
    ]
    for case in joint_cases:
        coverage, g, detail_mean = case[2], case[4], case[5]
        fraction, density = density_statistics(*case)
        margin_mean, margin_sigma = margin_moments(*case)
        u = margin_mean + margin_sigma * normal
        assert_sample(fraction, u > 0.0, (*case, "f joint"))
        mean_density = np.maximum(u, 0.0) / (1.0 - g * detail_mean) / coverage
        assert_sample(fraction * density, mean_density, (*case, "densité moyenne"))

    # The threshold's mathematical zero-variance limit, before adding the subtexel population.
    for coverage in (0.04, 0.10, 0.40, 1.0):
        for mu in (*np.linspace(0.0, 1.0, 101), 1.0 - coverage):
            fraction, expected, expected_square = statistics(mu, 0.0, coverage)
            fine = np.clip((mu - (1.0 - coverage)) / coverage, 0.0, 1.0) * coverage
            assert fraction == float(mu > 1.0 - coverage)
            assert abs(expected / max(fraction, 1.0e-4) - fine) < 1.0e-15
            assert expected_square == expected * expected

    # At mip 0 either noise alone still creates partial coverage across its turbulent edge.
    for p, g, detail_mean in ((1.0, 0.0, 0.7), (0.0, 0.3, 0.0)):
        fraction, density = density_statistics(0.8, 0.0, 0.2, p, g, detail_mean, 0.0)
        assert 0.0 < fraction < 1.0
        assert density > 0.0

    # The exact branch remains valid when the profile propagates a negligible total variance.
    for sigma in (0.0, 1.0e-5):
        for mu in (0.84, 0.88):
            p, g = 0.001, 0.0001
            fraction, density = density_statistics(mu, sigma, 0.2, p, g, 0.7, sigma)
            margin_mean, margin_sigma = margin_moments(mu, sigma, 0.2, p, g, 0.7, sigma)
            assert margin_sigma < 1.0e-4
            assert fraction == float(margin_mean > 0.0)
            assert abs(density - max(margin_mean, 0.0) / (1.0 - g * 0.7) / 0.2) < 1.0e-13

    check_textures(rng)
    print(f"OK : f, E, E2 ({len(cases)} populations), loi jointe ({len(joint_cases)} populations),"
          " textures et variance sous les texels au mip 0.")


if __name__ == "__main__":
    main()
