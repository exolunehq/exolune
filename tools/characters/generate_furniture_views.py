"""Compute exact Exolune test camera views framing all cooked Pad 43 furniture & hero zones."""
import json
import math
from pathlib import Path

PLANET_RADIUS_M = 6378000.0
NOON_SUN = "5.003003 43.681051"
GRAZING_SUN = "-18.996997 -25.318949"
COUCHANT_SUN = "-16.996997 -20.318949"


def city_bend(x: float, y: float, z: float) -> tuple[float, float, float]:
    # CityBendDouble(cx, cy, cz): matches Characters.cpp / City.hlsli spherical bend
    scale = (PLANET_RADIUS_M + z) / PLANET_RADIUS_M
    r2 = (x * x + y * y) / (2.0 * PLANET_RADIUS_M)
    return x * scale, y * scale, z - r2


def city_to_world(anchor_lat_deg: float, anchor_lon_deg: float, x: float, y: float, z: float):
    lat = math.radians(anchor_lat_deg)
    lon = math.radians(anchor_lon_deg)
    up = (math.cos(lat) * math.cos(lon), math.sin(lat), math.cos(lat) * math.sin(lon))
    east = (-math.sin(lon), 0.0, math.cos(lon))
    north = (-math.sin(lat) * math.cos(lon), math.cos(lat), -math.sin(lat) * math.sin(lon))
    bx, by, bz = city_bend(x, y, z)
    return (
        up[0] * (PLANET_RADIUS_M + bz) + east[0] * bx + north[0] * by,
        up[1] * (PLANET_RADIUS_M + bz) + east[1] * bx + north[1] * by,
        up[2] * (PLANET_RADIUS_M + bz) + east[2] * bx + north[2] * by,
    )


def world_to_camera_line(anchor_lat_deg: float, anchor_lon_deg: float, eye_xyz, tgt_xyz, sun: str, extra: str = "") -> str:
    we = city_to_world(anchor_lat_deg, anchor_lon_deg, *eye_xyz)
    wt = city_to_world(anchor_lat_deg, anchor_lon_deg, *tgt_xyz)
    re = math.sqrt(we[0] ** 2 + we[1] ** 2 + we[2] ** 2)
    alt = re - PLANET_RADIUS_M
    lat_r = math.asin(max(-1.0, min(1.0, we[1] / re)))
    lon_r = math.atan2(we[2], we[0])
    lat_deg = math.degrees(lat_r)
    lon_deg = math.degrees(lon_r)

    up = (we[0] / re, we[1] / re, we[2] / re)
    east = (-math.sin(lon_r), 0.0, math.cos(lon_r))
    north = (-math.sin(lat_r) * math.cos(lon_r), math.cos(lat_r), -math.sin(lat_r) * math.sin(lon_r))
    dx, dy, dz = wt[0] - we[0], wt[1] - we[1], wt[2] - we[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    fwd = (dx / dist, dy / dist, dz / dist)

    f_up = fwd[0] * up[0] + fwd[1] * up[1] + fwd[2] * up[2]
    f_e = fwd[0] * east[0] + fwd[1] * east[1] + fwd[2] * east[2]
    f_n = fwd[0] * north[0] + fwd[1] * north[1] + fwd[2] * north[2]
    pitch_down = math.degrees(math.asin(max(-1.0, min(1.0, -f_up))))
    heading = math.degrees(math.atan2(f_e, f_n))
    suffix = f" {extra}" if extra else ""
    return f"{alt:.3f} {lat_deg:.10f} {lon_deg:.10f} {pitch_down:.3f} {heading:.3f}{suffix} | {sun}"


def make_front_view(anchor_lat: float, anchor_lon: float, fx: float, fy: float, surface_z: float,
                    fyaw: float, local_cam, local_tgt, sun: str) -> str:
    cf, sf = math.cos(fyaw), math.sin(fyaw)
    ex = fx + local_cam[0] * cf - local_cam[1] * sf
    ey = fy + local_cam[0] * sf + local_cam[1] * cf
    ez = surface_z + local_cam[2]
    tx = fx + local_tgt[0] * cf - local_tgt[1] * sf
    ty = fy + local_tgt[0] * sf + local_tgt[1] * cf
    tz = surface_z + local_tgt[2]
    return world_to_camera_line(anchor_lat, anchor_lon, (ex, ey, ez), (tx, ty, tz), sun)


def main():
    city_bank = Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-07\bank")
    char_manifest = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\bank-cast-20-painterly\manifest.json")
    out_txt = Path(r"c:\Users\etien\Documents\repos\Exolune\tools\tests\2026-11-26-cast20-mobilier.txt")

    layout = json.loads((city_bank / "layout.json").read_text(encoding="utf-8"))
    library = json.loads((city_bank / "library.json").read_text(encoding="utf-8"))["models"]
    anchor_lat, anchor_lon = float(layout["anchor"][0]), float(layout["anchor"][1])
    terminal = next(x for x in layout["instances"] if x["id"] == "space_terminal")
    pad = layout["earthworks"]["pads"][int(terminal["pad"])]
    pad_cx, pad_cy, cos_a, sin_a = pad[0], pad[1], pad[2], pad[3]
    surface_z = float(terminal["position"][2])

    benches = []
    wild_benches = []
    sorting = []
    cabinets = []
    for inst in layout["instances"]:
        px, py, _ = inst["position"]
        if math.hypot(px - pad_cx, py - pad_cy) > 95.0:
            continue
        mname = library[inst["model"]].get("id") or inst.get("id")
        if mname == "planted_bench":
            benches.append(inst)
        elif mname == "planted_bench_wild":
            wild_benches.append(inst)
        elif mname == "sorting_station":
            sorting.append(inst)
        elif mname == "service_cabinet":
            cabinets.append(inst)

    lines = [
        "# Cast painterly Tripo H3.1 + animations adaptees au mobilier (Pad 43).",
        "# Launch: powershell -NoProfile -ExecutionPolicy Bypass -File tools\\lance.ps1 -Ville E:/ExoluneAssets/city-tripo-2026-11-11/delivery-07/bank -Personnages E:/ExoluneAssets/characters-m1-2026-11-21/bank-cast-20-painterly -Parcours tools\\tests\\2026-11-26-cast20-mobilier.txt",
        f"Duo terminal Pilot et Crew Lead (midi) | 562.573 -11.0037662578 63.6790345499 3.728 -100.620 | {NOON_SUN}",
        f"Portrait Pilot peau 0.54 (soleil rasant) | 562.663 -11.0037808676 63.6790015468 2.635 -102.529 | {GRAZING_SUN}",
    ]

    if benches:
        b0 = benches[0]
        lines.append("Banc plante assis duo (midi) | " + make_front_view(
            anchor_lat, anchor_lon, b0["position"][0], b0["position"][1], surface_z, float(b0.get("yaw", 0.0)),
            (0.95, -4.10, 1.45), (0.45, -0.35, 0.85), NOON_SUN))
        b_term = benches[-1]
        lines.append("Banc terminal assis (soleil rasant) | " + make_front_view(
            anchor_lat, anchor_lon, b_term["position"][0], b_term["position"][1], surface_z, float(b_term.get("yaw", 0.0)),
            (0.95, -4.10, 1.45), (0.45, -0.35, 0.85), GRAZING_SUN))

    if wild_benches:
        bw = wild_benches[0]
        lines.append("Banc sauvage assis duo (midi) | " + make_front_view(
            anchor_lat, anchor_lon, bw["position"][0], bw["position"][1], surface_z, float(bw.get("yaw", 0.0)),
            (-0.75, 4.10, 1.45), (-0.30, 0.35, 0.85), NOON_SUN))

    if sorting:
        ss = sorting[0]
        lines.append("Station de tri interaction (midi) | " + make_front_view(
            anchor_lat, anchor_lon, ss["position"][0], ss["position"][1], surface_z, float(ss.get("yaw", 0.0)),
            (-1.90, -3.50, 1.55), (-0.15, -0.45, 1.00), NOON_SUN))

    if cabinets:
        sc = cabinets[0]
        lines.append("Borne technique interaction (midi) | " + make_front_view(
            anchor_lat, anchor_lon, sc["position"][0], sc["position"][1], surface_z, float(sc.get("yaw", 0.0)),
            (1.90, -3.60, 1.55), (0.30, -0.50, 1.05), NOON_SUN))

    lines.extend([
        f"Equipage au pied de la navette (midi) | 562.773 -11.0036277822 63.6793684625 1.456 -8.616 | {NOON_SUN}",
        f"Parvis et marcheurs au couchant | 562.873 -11.0036087232 63.6789737221 2.136 100.125 | {COUCHANT_SUN}",
        f"Parvis au crepuscule | 562.623 -11.0037643521 63.6790351970 4.847 -102.995 | {GRAZING_SUN}",
        f"Spatioport vue ensemble (cast complet) | 575.023 -11.0039136290 63.6791096143 19.827 11.310 | {NOON_SUN}",
        f"Marcher sur le spatioport | 562.703 -11.0037103585 63.6790190195 0.000 -158.199 marche | {NOON_SUN}",
    ])

    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    m = json.loads(char_manifest.read_text(encoding="utf-8")) if char_manifest.exists() else {}
    print(f"[views] wrote {len(lines)-2} test views -> {out_txt} (actors in bank: {m.get('actor_count', '?')})")


if __name__ == "__main__":
    main()
