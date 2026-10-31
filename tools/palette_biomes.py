# Biome palette from the real Earth (docs/spec-photos-par-echelle.md, step 1): the colour of the ground, by
# temperature and humidity, measured on NASA's Blue Marble and on NASA climate grids, all public domain.
# Writes MyPlanetEngine/BiomePalette.hlsli, a table the pixel shader reads: no image enters the engine.
#
# python tools/palette_biomes.py <blue marble january,july> <temperature grid> <precipitation grid> [<out .hlsli>]
#   blue marble: equirectangular true-colour land mosaics, without relief shading (sRGB), of January and July: each
#   hemisphere is taken in its summer, its least snowy month, since the engine draws its snow apart;
#   grids: equirectangular CSV, rows from the north, mean temperature in C and annual precipitation in mm,
#   99999 or empty for no data; any size, they are resampled to the image's grid.
# Prints the table's coverage and a few control points (Sahara, Amazon, Siberia).
import os, sys
import numpy as np
from PIL import Image

T_MIN, T_MAX, T_BINS = -20.0, 35.0, 23     # C, every 2.5 C
H_BINS = 11                                # humidity 0 to 1, every 0.1
P_DRY, P_WET = 100.0, 3000.0               # mm per year for humidity 0 and 1, logarithmic between
# Blue Marble's colours are enhanced, not reflectances: per channel, albedo = a * value^g, fitted on two anchors, the
# Libyan Sahara and the Amazon, whose surface albedos (red, green, blue) are about (0.45, 0.35, 0.22) and
# (0.03, 0.06, 0.025) from satellite measurements. Their Blue Marble values: (0.745, 0.622, 0.462), (0.091, 0.145, 0.039).
ANCHOR_VALUES = np.array([[0.745, 0.622, 0.462], [0.0905, 0.1453, 0.0393]])
ANCHOR_ALBEDOS = np.array([[0.45, 0.35, 0.22], [0.03, 0.06, 0.025]])
GAMMA = np.log(ANCHOR_ALBEDOS[0] / ANCHOR_ALBEDOS[1]) / np.log(ANCHOR_VALUES[0] / ANCHOR_VALUES[1])
SCALE = ANCHOR_ALBEDOS[0] / ANCHOR_VALUES[0] ** GAMMA


def read_grid(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        cells = [c.strip() for c in line.replace(";", ",").split(",") if c.strip() != ""]
        try:
            rows.append([float(c) for c in cells])
        except ValueError:
            continue  # a header
    width = max(len(r) for r in rows)
    grid = np.full((len(rows), width), np.nan, np.float32)
    for i, r in enumerate(rows):
        grid[i, :len(r)] = r
    grid[np.abs(grid) >= 9999.0] = np.nan
    return grid


def resample(grid, shape):
    """Nearest cell of `grid` for every pixel of an image of `shape` (rows, columns), both equirectangular."""
    rows = (np.arange(shape[0]) * grid.shape[0] // shape[0])[:, None]
    cols = (np.arange(shape[1]) * grid.shape[1] // shape[1])[None, :]
    return grid[rows, cols]


def albedo_of(value):
    return SCALE * np.maximum(value, 1e-4) ** GAMMA


def humidity_of(precipitation):
    return np.clip(np.log(np.maximum(precipitation, 1.0) / P_DRY) / np.log(P_WET / P_DRY), 0.0, 1.0)


if __name__ == "__main__":
    image_path, t_path, p_path = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(__file__), "..", "MyPlanetEngine", "BiomePalette.hlsli")
    Image.MAX_IMAGE_PIXELS = None
    images = []
    for path in image_path.split(","):
        image = Image.open(path).convert("RGB")
        if image.size[0] > 2160:  # 1/6 degree is plenty for climate bins
            image = image.resize((2160, 1080), Image.BOX)
        images.append(np.asarray(image, np.float32) / 255.0)
    january, july = images
    raw = july.copy()
    raw[raw.shape[0] // 2:] = january[raw.shape[0] // 2:]  # the north in July, the south in January
    rgb = albedo_of(raw)
    shape = rgb.shape[:2]
    temperature = np.nan_to_num(resample(read_grid(t_path), shape), nan=-999.0)
    humidity = humidity_of(resample(read_grid(p_path), shape))
    # Land with both climate values; no permanent ice (it is the snow's, decided apart) and no water.
    land = np.isfinite(humidity) & (temperature > T_MIN - 5.0)
    humidity = np.nan_to_num(humidity)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    land &= ~((raw.min(axis=2) > 0.5) & (raw.max(axis=2) - raw.min(axis=2) < 0.15))  # ice and snow, white in Blue Marble
    ti = np.clip(np.round((temperature - T_MIN) / (T_MAX - T_MIN) * (T_BINS - 1)), 0, T_BINS - 1).astype(int)
    hi = np.clip(np.round(humidity * (H_BINS - 1)), 0, H_BINS - 1).astype(int)
    # Pixels weigh their area: cos(latitude).
    weight = np.repeat(np.cos(np.radians(90.0 - (np.arange(shape[0]) + 0.5) * 180.0 / shape[0]))[:, None], shape[1], 1)
    total = np.zeros((T_BINS, H_BINS)); colour = np.zeros((T_BINS, H_BINS, 3)); lum2 = np.zeros((T_BINS, H_BINS))
    sel = land
    np.add.at(total, (ti[sel], hi[sel]), weight[sel])
    for c in range(3):
        np.add.at(colour[..., c], (ti[sel], hi[sel]), weight[sel] * rgb[..., c][sel])
    np.add.at(lum2, (ti[sel], hi[sel]), weight[sel] * lum[sel] ** 2)
    filled = total > 1e-3 * total.sum() / (T_BINS * H_BINS)
    mean = np.where(filled[..., None], colour / np.maximum(total, 1e-9)[..., None], np.nan)
    meanLum = mean @ np.array([0.2126, 0.7152, 0.0722])
    spread = np.where(filled, np.sqrt(np.maximum(lum2 / np.maximum(total, 1e-9) - meanLum ** 2, 0.0)) / np.maximum(meanLum, 1e-4), np.nan)
    # Empty bins (climates the Earth lacks): the nearest filled bins' mean, by diffusion, so the table is smooth.
    table = np.concatenate([mean, spread[..., None]], axis=2)
    known = filled.copy()
    while not known.all():
        add = np.zeros_like(table); count = np.zeros(known.shape)
        for axis in (0, 1):
            for step in (1, -1):
                src = np.roll(table, step, axis); ok = np.roll(known, step, axis)
                edge = [slice(None)] * 2
                edge[axis] = 0 if step == 1 else -1
                ok[tuple(edge)] = False  # no wrapping around the table
                add += np.where(ok[..., None], np.nan_to_num(src), 0.0); count += ok
        newly = ~known & (count > 0)
        table[newly] = add[newly] / count[newly][:, None]
        known |= newly
    print(f"cases remplies par la Terre : {filled.sum()} sur {filled.size}")
    def at(t, h):
        v = table[int(round((t - T_MIN) / (T_MAX - T_MIN) * (T_BINS - 1))), int(round(h * (H_BINS - 1)))]
        return " ".join(f"{x:.3f}" for x in v)
    for name, t, p in (("Sahara", 27, 50), ("Sahel", 28, 400), ("steppe", 8, 300), ("Europe", 10, 800),
                       ("Amazonie", 27, 2500), ("taïga", -3, 450), ("toundra", -12, 250)):
        print(f"{name:9s} T {t:3d} C, P {p:4d} mm -> r g b dispersion : {at(t, float(humidity_of(np.array(p))))}")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("// Generated by tools/palette_biomes.py from NASA's Blue Marble and NASA climate grids (public domain):\n")
        f.write("// the ground's mean colour (linear albedo, rgb) and its relative spread of brightness (w), by mean temperature\n")
        f.write(f"// ({T_MIN:g} to {T_MAX:g} C, {T_BINS} rows) and humidity (0 to 1, {H_BINS} columns: log of the annual\n")
        f.write(f"// precipitation from {P_DRY:g} to {P_WET:g} mm). docs/spec-photos-par-echelle.md. Do not edit by hand.\n")
        f.write("#ifndef BIOME_PALETTE_HLSLI\n#define BIOME_PALETTE_HLSLI\n")
        f.write(f"static const float BIOME_T_MIN = {T_MIN:g}, BIOME_T_MAX = {T_MAX:g};\n")
        f.write(f"static const int BIOME_T_BINS = {T_BINS}, BIOME_H_BINS = {H_BINS};\n")
        f.write(f"static const float4 BIOME_PALETTE[{T_BINS * H_BINS}] = {{\n")
        for i in range(T_BINS):
            f.write("    " + ", ".join(f"float4({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}, {v[3]:.3f})" for v in table[i]) + ",\n")
        f.write("};\n#endif\n")
    print(os.path.abspath(out))
