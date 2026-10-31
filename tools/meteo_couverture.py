"""Couverture optique du mip 0, sans moteur. Usage : python tools/meteo_couverture.py 0 (ou chemin.bin)."""
import argparse
from pathlib import Path
import struct
import zlib

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="0", help="Graine ou fichier meteo-<graine>.bin")
    args = parser.parse_args()
    path = (Path(__file__).resolve().parents[1] / "x64" / "Release" / f"meteo-{args.source}.bin"
            if args.source.isdecimal() else Path(args.source))
    try:
        with path.open("rb") as stream:
            header = stream.read(20)
            if len(header) != 20:
                raise ValueError("en-tête tronqué")
            magic, seed, width, height = struct.unpack("<8sIII", header)
            if magic != b"EXOMETEO" or (width, height) != (1024, 512):
                raise ValueError("format attendu : EXOMETEO, RGBA8 1024 × 512")
            pixels = np.frombuffer(stream.read(width * height * 4), dtype=np.uint8)
            if pixels.size != width * height * 4:
                raise ValueError("mip 0 tronqué")
            pixels = pixels.reshape(height, width, 4)
    except (OSError, ValueError) as error:
        parser.error(f"{path} : {error}")

    # Same measured opacity table as CloudControl; above R = .28 the thickness closes the last holes, up to 1 at e = 1.
    controls = [0, .08, .10, .12, .14, .16, .18, .20, .22, .24, .26, .28, .90, 1]
    opacity = [0, .06, .13, .21, .32, .44, .55, .66, .75, .82, .88, .92, 1, 1]
    cover = np.interp(pixels[:, :, 0] / 255.0, controls, opacity)
    organized = pixels[:, :, 0] / 255.0 >= .28
    latitude = 90.0 - (np.arange(height) + .5) * 180.0 / height
    area = np.cos(np.deg2rad(latitude))

    def mean(field, rows):
        return np.sum(field[rows] * area[rows, None]) / (width * np.sum(area[rows]))

    all_rows = np.ones(height, dtype=bool)
    print(f"{path.name} — graine {seed}")
    print(f"Globale : {mean(cover, all_rows):.3f} (cible 0.35–0.45)")
    print("Latitude    Nord : c (écart), opaque     Sud : c (écart), opaque")
    edges = [0, 10, 20, 30, 40, 50, 60, 70, 90]
    north = [.40, .25, .20, .30, .50, .60, .55, .45]
    south = [.40, .25, .20, .35, .55, .65, .60, .35]
    errors = []
    for lo, hi, n, s in zip(edges[:-1], edges[1:], north, south):
        band = (np.abs(latitude) >= lo) & (np.abs(latitude) < hi)
        cn = mean(cover, band & (latitude > 0))
        cs = mean(cover, band & (latitude < 0))
        errors.extend((abs(cn - n), abs(cs - s)))
        on = mean(organized, band & (latitude > 0))
        os = mean(organized, band & (latitude < 0))
        print(f"{lo:2d}–{hi:2d}°     {cn:.3f} ({cn-n:+.3f}), {on:.1%}          {cs:.3f} ({cs-s:+.3f}), {os:.1%}")
    cirrus = mean(pixels[:, :, 2] / 255.0 > .03, all_rows)
    print(f"B > 0.03 : {cirrus:.1%} de l'aire (cible 4–8 %) ; tolérance zonale ±0.10")
    clear = mean(cover < .05, all_rows)
    partial = mean((cover >= .05) & (cover <= .9), all_rows)
    opaque = mean(cover > .9, all_rows)
    print(f"Opacité : < 0.05 = {clear:.1%} ; 0.05–0.9 = {partial:.1%} ; > 0.9 = {opaque:.1%}")
    checks = [.35 <= mean(cover, all_rows) <= .45, max(errors) <= .10, clear >= .40,
              .22 <= opaque <= .35, partial <= .38, .04 <= cirrus <= .08]
    print("Cibles : " + "; ".join(f"{name} {'OK' if ok else 'HORS CIBLE'}" for name, ok in
                                   zip(["globale", "16 bandes", "clairs ≥ 40 %", "opaques 22–35 %",
                                        "intermédiaires ≤ 38 %", "cirrus"], checks)))

    # .28 rounds to 71 in RGBA8: include e = 0, which a literal R/255 >= .28 would incorrectly exclude.
    thick_mask = pixels[:, :, 0] >= round(.28 * 255)
    thickness = np.clip((pixels[:, :, 0] / 255.0 - .28) / .62, 0, 1)
    weights = np.broadcast_to(area[:, None], (height, width))
    thick_area = np.sum(weights[thick_mask])
    histogram, _ = np.histogram(thickness[thick_mask], bins=np.linspace(0, 1, 6), weights=weights[thick_mask])
    print("Épaisseur e, aire opaque (R ≥ 71/255, seuil .28 quantifié) :")
    print(" ; ".join(f"{k/5:.1f}–{(k+1)/5:.1f} : {value/max(thick_area, 1e-12):.1%}"
                     for k, value in enumerate(histogram)))
    family = pixels[:, :, 1] / 255.0
    for name, mask in [("nappe G < .2", family < .2), ("mixte", (family >= .2) & (family <= .8)),
                       ("cumulus G > .8", family > .8)]:
        selected = thick_mask & mask
        total = np.sum(weights[selected])
        value = f"{np.sum(thickness[selected] * weights[selected]) / total:.3f}" if total else "sans texel"
        print(f"e moyen {name} : {value} ({total/max(thick_area, 1e-12):.1%} de l'aire opaque)")

    # A small RGB PNG writer keeps this diagnostic dependent on numpy and the standard library alone.
    pink = np.clip(pixels[:, :, 2] / 255.0, 0, .25) * (1 - .6 * cover)
    rgb = cover[:, :, None] + (1 - cover[:, :, None]) * np.array([20, 40, 90]) / 255.0
    rgb = rgb * (1 - pink[:, :, None]) + pink[:, :, None] * np.array([1, .4, .8])
    rgb = np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)

    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload)))

    def write_png(output, values):
        scanlines = b"".join(b"\0" + row.tobytes() for row in values)
        color = 2 if values.ndim == 3 else 0
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
        output.write_bytes(png)
        print(f"PNG : {output}")

    write_png(path.with_suffix(".png"), rgb)
    write_png(path.with_name(path.stem + "-e.png"), np.rint(thickness * thick_mask * 255).astype(np.uint8))


if __name__ == "__main__":
    main()
