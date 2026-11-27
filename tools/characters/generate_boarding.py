"""Generate V9 transport shuttle boarding choreography (sequences/shuttle_boarding.txt) and Pad 43 multi-view test file."""
import argparse
import json
import math
from pathlib import Path

PLANET_RADIUS_M = 6378000.0
PAD_DEPTH_M = 2.6388
GROUND_Z = -PAD_DEPTH_M

NOON_SUN = "5.003003 43.681051"
DUSK_SUN = "-18.996997 -25.318949"


def city_bend(x: float, y: float, z: float) -> tuple[float, float, float]:
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


def make_actor_path(wait_xy, row_y: float, side_x: float, is_pilot: bool) -> list[tuple[float, float, float]]:
    """Build exact 3D ship-local boarding path: apron wait -> airstair -> airlock -> aisle -> seat."""
    wx, wy = wait_xy
    # Shared centerline climb up the 8-riser open airstair (y=6.15 ground -> y=4.07 sill -> y=2.45 cabin floor)
    common = [
        (wx, wy, GROUND_Z),
        (wx * 0.25, 6.75, GROUND_Z),
        (0.0, 6.08, GROUND_Z),
        (0.0, 5.73, -2.453),
        (0.0, 4.90, -1.795),
        (0.0, 4.07, -1.149),
        (0.0, 3.38, -1.149),
        (0.0, 2.45, -1.240),
        (0.0, -0.30, -1.240),
    ]
    if is_pilot:
        # Pilot walks down full aisle right to the front edge of the pilot sled, turns -90 deg, sits cleanly.
        return common + [
            (0.0, -3.78, -1.240),
            (0.0, -3.96, -1.240),
            (0.0, -4.23, -1.335),
        ]
    # Passenger steps down center aisle, sidesteps into row entry in front of their seat, turns -90 deg, sits.
    stand_x = 0.28 if side_x > 0 else -0.28
    seat_x = 0.66 if side_x > 0 else -0.66
    return common + [
        (0.0, row_y + 0.14, -1.240),
        (stand_x, row_y + 0.08, -1.240),
        (seat_x, row_y + 0.04, -1.240),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city-bank", default=r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-07\bank")
    parser.add_argument("--char-bank", default=r"E:\ExoluneAssets\characters-m1-2026-11-21\bank-cast-20-painterly")
    args = parser.parse_args()

    city_bank = Path(args.city_bank)
    char_bank = Path(args.char_bank)
    repo_root = Path(__file__).resolve().parents[2]
    seq_dir = char_bank / "sequences"
    seq_dir.mkdir(parents=True, exist_ok=True)
    out_board = seq_dir / "shuttle_boarding.txt"
    out_tests = repo_root / "tools" / "tests" / "2026-11-26-embarquement-navette.txt"

    layout = json.loads((city_bank / "layout.json").read_text(encoding="utf-8"))
    manifest = json.loads((char_bank / "manifest.json").read_text(encoding="utf-8"))
    arch_idx = {a["id"]: i for i, a in enumerate(manifest["archetypes"])}

    anchor_lat, anchor_lon = float(layout["anchor"][0]), float(layout["anchor"][1])
    terminal = next(x for x in layout["instances"] if x["id"] == "space_terminal")
    pad = layout["earthworks"]["pads"][int(terminal["pad"])]
    pad_cx, pad_cy, cos_a, sin_a = pad[0], pad[1], pad[2], pad[3]
    surface_z = float(terminal["position"][2])
    pad_yaw = math.atan2(sin_a, cos_a)

    # Clear Pad 43 spot: pad_uv = (+10.0, +22.0), nose facing +u (rear ramp opens toward terminal apron -u).
    u0, v0 = 10.0, 22.0
    park_x = pad_cx + u0 * cos_a - v0 * sin_a
    park_y = pad_cy + u0 * sin_a + v0 * cos_a

    # Board front-to-back so later passengers never brush past an already-seated passenger in the aisle!
    manifest_cast = [
        # (archetype, wait_clip(0=idle,2=talk), seat_clip(3=sit_idle,4=sit_talk), delay_s, speed_mps, is_pilot, row_y, side_x, wait_xy)
        ("pilot_explorer",    0, 3,  0.0, 1.38, True,  -4.25,  0.00, ( 0.05,  7.45)),
        ("crew_lead",         2, 4,  2.3, 1.32, False, -3.15,  0.66, (-0.70,  8.05)),
        ("botanist_f",        2, 3,  4.6, 1.28, False, -3.15, -0.66, ( 0.80,  8.35)),
        ("engineer_m",        0, 3,  6.9, 1.30, False, -2.38,  0.66, (-1.20,  9.05)),
        ("architect_f",       2, 4,  9.2, 1.26, False, -2.38, -0.66, ( 1.15,  9.35)),
        ("hydrologist_m",     2, 4, 11.5, 1.29, False, -1.61,  0.66, (-0.45,  9.95)),
        ("navigator_f",       0, 3, 13.8, 1.25, False, -1.61, -0.66, ( 0.55, 10.35)),
        ("medic_m",           0, 3, 16.1, 1.27, False, -0.90,  0.66, (-1.45, 10.85)),
        ("tech_specialist_f", 2, 4, 18.4, 1.24, False, -0.90, -0.66, ( 1.35, 11.20)),
    ]

    lines = [
        "# V9 Transport Shuttle group boarding choreography (Pad 43)",
        f"PARK {park_x:.4f} {park_y:.4f} {surface_z:.4f} {math.degrees(pad_yaw):.4f}",
    ]
    for aid, wc, sc, delay, spd, is_pilot, ry, sx, wait_xy in manifest_cast:
        mdl = arch_idx[aid]
        wps = make_actor_path(wait_xy, ry, sx, is_pilot)
        wp_str = " ; ".join(f"{x:.3f} {y:.3f} {z:.3f}" for x, y, z in wps)
        lines.append(
            f"ACTOR {mdl} {wc} {sc} {delay:.2f} {spd:.2f} -90.0 {1 if is_pilot else 0} | {wp_str} # {aid}"
        )

    out_board.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Convert ship-local (sx, sy, sz) -> city (cx, cy, cz): du = -sy, dv = +sx, dz = sz + PAD_DEPTH_M
    def ship_to_city(sx: float, sy: float, sz: float):
        du, dv = -sy, sx
        cx = park_x + du * cos_a - dv * sin_a
        cy = park_y + du * sin_a + dv * cos_a
        cz = surface_z + (sz + PAD_DEPTH_M)
        return (cx, cy, cz)

    def ship_cam(label: str, eye_s, tgt_s, sun: str, extra: str):
        cam_str = world_to_camera_line(anchor_lat, anchor_lon, ship_to_city(*eye_s), ship_to_city(*tgt_s), sun, extra)
        return f"{label} | {cam_str}"

    tests = [
        "# Embarquement groupe (pilote + 8 passagers) par la trappe arriere de la navette V9 sur le spatioport Pad 43.",
        "# Launch: powershell -NoProfile -ExecutionPolicy Bypass -File tools\\lance.ps1 -DepartTest 1 -ModeleVaisseau navette -Ville E:/ExoluneAssets/city-tripo-2026-11-11/delivery-07/bank -Personnages E:/ExoluneAssets/characters-m1-2026-11-21/bank-cast-20-painterly -Parcours tools\\tests\\2026-11-26-embarquement-navette.txt",
        ship_cam("Embarquement trappe arriere (midi)",          ( 5.8, 12.2, -0.35), ( 0.0,  4.2, -1.65), NOON_SUN, "sequence=shuttle_boarding"),
        ship_cam("Cabine et sieges passagers (verriere)",      ( 5.4, -2.1,  0.55), ( 0.0, -2.1, -0.80), NOON_SUN, "navette-fixe"),
        ship_cam("Poste de pilotage (pilote assis)",          ( 2.8, -6.2, -0.25), ( 0.0, -4.1, -0.70), NOON_SUN, "navette-fixe"),
        ship_cam("Interieur cabine vers la trappe",            ( 0.0, -3.55, -0.10), ( 0.0, 2.8, -0.95), NOON_SUN, "navette-fixe"),
        ship_cam("Embarquement au crepuscule",                 ( 6.4, 11.4, -0.10), ( 0.0,  3.5, -1.45), DUSK_SUN, "navette-fixe"),
        ship_cam("Spatioport vue ensemble (navette et parvis)",(18.0, 22.0, 10.50), (-6.0, 2.0, -1.20), NOON_SUN, "navette-fixe"),
        ship_cam("Marche libre autour de la navette",          ( 4.6,  9.2, -0.95), ( 0.0,  4.0, -1.50), NOON_SUN, "navette-fixe marche"),
        ship_cam("Cockpit pret au decollage (L pour partir)",  ( 0.0, -4.4, -0.35), ( 0.0, -14.0, -0.50), NOON_SUN, "navette-fixe cockpit"),
    ]
    out_tests.write_text("\n".join(tests) + "\n", encoding="utf-8")
    print(f"Wrote {out_board} ({len(manifest_cast)} actors)")
    print(f"Wrote {out_tests} ({len(tests)-2} views)")


if __name__ == "__main__":
    main()
