"""Cook Tripo H3.1 Mixamo characters and painterly brush atlas into a native CHR1 bank.

Supports:
  - Legacy 2-hero mode (default): cooks pilot_explorer + crew_lead into bank-tripo-painterly.
  - --cast-json mode: cooks up to 20+ unique archetypes, 6 animation slots (idle, walk, talk,
    sit_idle, sit_talk, interact), and data-driven furniture-anchored Pad 43 placements
    (planted_bench, planted_bench_wild, sorting_station, service_cabinet, solar_canopy, etc.).
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cook  # noqa: E402


DEFAULT_TRIPO_DIR = Path("E:/ExoluneAssets/characters-m1-2026-11-21/tripo-poc")
DEFAULT_BANK_DIR = Path("E:/ExoluneAssets/characters-m1-2026-11-21/bank-tripo-painterly")
DEFAULT_CITY_BANK = Path("E:/ExoluneAssets/city-tripo-2026-11-11/delivery-07/bank")
DEFAULT_GLTF2OZZ = Path("E:/ExoluneAssets/characters-m1-2026-11-21/ozz-build/src/animation/offline/gltf/gltf2ozz.exe")

ARCHETYPES = [
    {
        "id": "pilot_explorer",
        "glb": DEFAULT_TRIPO_DIR / "pilot_h31_v2_aaa_120k.glb",
        "clips": {"idle": "idle_standing", "walk": "walk_female", "talk": "talk_general"},
        "stride_m": 1.36,
        "hs": 1.000,
        "eye_y": 1.5507,
        "nose_z": 0.1268,
        "tex_color": 2048,
        "tex_norm": 2048,
        "tex_mr": 1024,
    },
    {
        "id": "crew_lead",
        "glb": DEFAULT_TRIPO_DIR / "crew_lead_h31_v2_aaa_120k.glb",
        "clips": {"idle": "idle_weight_shift", "walk": "walk_confident", "talk": "talk_asking"},
        "stride_m": 1.62,
        "hs": 1.060,
        "eye_y": 1.6536,
        "nose_z": 0.1263,
        "tex_color": 2048,
        "tex_norm": 2048,
        "tex_mr": 1024,
    },
]

SPACEPORT_PLACEMENTS = [
    {"name": "terminal_talk_a", "archetype": "crew_lead", "clip": "talk", "pad_uv": [-31.0, -2.5], "yaw_deg": 23.0, "phase": 0.10},
    {"name": "terminal_talk_b", "archetype": "pilot_explorer", "clip": "talk", "pad_uv": [-29.0, -1.6], "yaw_deg": 203.0, "phase": 0.55},
    {"name": "shuttle_inspect_a", "archetype": "pilot_explorer", "clip": "talk", "pad_uv": [13.2, -14.6], "yaw_deg": 25.0, "phase": 0.25},
    {"name": "shuttle_inspect_b", "archetype": "crew_lead", "clip": "idle", "pad_uv": [15.8, -14.8], "yaw_deg": 175.0, "phase": 0.62},
    {"name": "canopy_wait_a", "archetype": "crew_lead", "clip": "idle", "pad_uv": [-5.0, -14.0], "yaw_deg": 75.0, "phase": 0.40},
    {"name": "canopy_wait_b", "archetype": "pilot_explorer", "clip": "idle", "pad_uv": [-2.2, -18.8], "yaw_deg": 65.0, "phase": 0.82},
    {
        "name": "concourse_walk_1", "archetype": "pilot_explorer", "clip": "walk", "speed": 1.18, "phase": 0.12,
        "loop_pad_uv": [[-27.5, 2.0], [-13.0, 2.5], [4.5, 2.5], [4.5, -1.5], [-13.0, -1.5], [-27.5, -2.0]],
    },
    {
        "name": "concourse_walk_2", "archetype": "crew_lead", "clip": "walk", "speed": 1.13, "phase": 0.18,
        "loop_pad_uv": [[-28.0, -15.0], [-19.5, -15.0], [-19.5, -4.0], [-28.0, -4.0]],
    },
]

# Local furniture attachment anchors (measured & visually verified in Blender EEVEE):
# (local_x, local_y, local_dz, local_facing_yaw_deg)
FURNITURE_SLOTS = {
    "planted_bench": [
        (0.18, -0.48, 0.0, -90.0),
        (0.85, -0.48, 0.0, -90.0),
    ],
    "planted_bench_wild": [
        (-0.68, 0.46, 0.0, 90.0),
        (0.05, 0.46, 0.0, 90.0),
    ],
    "sorting_station": [
        (-0.15, -0.84, 0.0, 90.0),
    ],
    "service_cabinet": [
        (0.32, -0.94, 0.0, 90.0),
    ],
}


def run_gltf2ozz_mapped(gltf2ozz_exe: Path, glb_path: Path, bank_dir: Path, model_index: int, clip_map: dict[str, str]):
    """Extract skeleton and named Mixamo animations into anim_<idx>_{idle,walk,talk,...}.ozz."""
    cfg = {
        "skeleton": {
            "filename": str(bank_dir / f"skel_{model_index}.ozz"),
            "import": {
                "enable": True,
                "raw": False,
                "types": {
                    "skeleton": True,
                    "marker": False,
                    "camera": False,
                    "geometry": False,
                    "light": False,
                    "null": False,
                    "any": False,
                },
            },
        },
        "animations": [
            {
                "clip": src_clip,
                "filename": str(bank_dir / f"anim_{model_index}_{slot}.ozz"),
                "raw": False,
                "additive": False,
                "sampling_rate": 30.0,
                "iframe_interval": 0.0,
                "optimize": True,
                "optimization_settings": {"tolerance": 0.0005, "distance": 0.08},
            }
            for slot, src_clip in clip_map.items()
        ],
    }
    cfg_path = bank_dir / f"_gltf2ozz_tripo_{model_index}.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    cmd = [str(gltf2ozz_exe), f"--file={glb_path}", f"--config_file={cfg_path}", "--log_level=standard"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    cfg_path.unlink(missing_ok=True)
    if res.returncode != 0:
        raise RuntimeError(f"gltf2ozz failed for {glb_path}:\n{res.stdout}\n{res.stderr}")
    outputs = [bank_dir / f"skel_{model_index}.ozz"] + [bank_dir / f"anim_{model_index}_{slot}.ozz" for slot in clip_map]
    for p in outputs:
        if not p.exists() or p.stat().st_size < 32:
            raise RuntimeError(f"Expected ozz output missing or empty: {p}")
    return outputs


def load_pow2_rgba(path: Path, max_size: int = 1024) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    target = 1
    while target * 2 <= min(max(w, h), max_size):
        target *= 2
    target = max(target, 64)
    if (w, h) != (target, target):
        im = im.resize((target, target), Image.Resampling.LANCZOS)
    return np.asarray(im, dtype=np.uint8)


def load_archetypes_from_cast(cast_json_path: Path) -> tuple[list[dict], list[dict]]:
    """Build ready archetype list and furniture-adapted placements covering all ready cast models."""
    cast = json.loads(cast_json_path.read_text(encoding="utf-8"))
    glbs_dir = Path(cast["glbs_dir"])
    archs = []
    for entry in cast["characters"]:
        cid = entry["id"]
        glb_path = glbs_dir / f"{cid}_aaa.glb"
        if not glb_path.exists():
            continue
        lm_path = glbs_dir / f"{cid}_landmarks.json"
        lm = json.loads(lm_path.read_text(encoding="utf-8")) if lm_path.exists() else {}
        is_hero = cid in ("pilot_explorer", "crew_lead")
        archs.append({
            "id": cid,
            "glb": glb_path,
            "clips": entry["clips"],
            "stride_m": float(entry.get("stride_m", 1.46)),
            "hs": float(lm.get("hs", entry.get("target_height", 1.68) / 1.68)),
            "eye_y": float(lm.get("eye_y", 1.55 * entry.get("target_height", 1.68) / 1.68)),
            "nose_z": float(lm.get("nose_z", 0.126 * entry.get("target_height", 1.68) / 1.68)),
            "tex_color": 2048 if is_hero else 1024,
            "tex_norm": 2048 if is_hero else 1024,
            "tex_mr": 1024 if is_hero else 512,
        })
    return archs, cast


def build_furniture_placements(city_bank: Path, bank_dir: Path, arch_list: list[dict], model_strides: list[float]):
    """Generate CHRPLC1 v2 combining Pad 43 furniture anchors, standing conversations, and walks."""
    layout = json.loads((city_bank / "layout.json").read_text(encoding="utf-8"))
    library = json.loads((city_bank / "library.json").read_text(encoding="utf-8"))["models"]
    anchor_lat, anchor_lon = float(layout["anchor"][0]), float(layout["anchor"][1])

    terminal = next(x for x in layout["instances"] if x["id"] == "space_terminal")
    pad = layout["earthworks"]["pads"][int(terminal["pad"])]
    pad_cx, pad_cy, cos_a, sin_a, half_u, half_v, _rad, _pad_z = pad
    surface_z = float(terminal["position"][2])
    pad_yaw = math.atan2(sin_a, cos_a)

    def uv_to_city(u: float, v: float):
        return pad_cx + u * cos_a - v * sin_a, pad_cy + u * sin_a + v * cos_a, surface_z

    # Collect obstacle OBBs (only non-furniture obstacles used to check walk loops)
    obstacles = []
    pad43_furniture = {"planted_bench": [], "planted_bench_wild": [], "sorting_station": [], "service_cabinet": []}
    for inst in layout["instances"]:
        px, py, pz = inst["position"]
        if math.hypot(px - pad_cx, py - pad_cy) > 95.0:
            continue
        mname = library[inst["model"]].get("id") or inst.get("id")
        if mname in pad43_furniture:
            pad43_furniture[mname].append(inst)
        if inst["id"] != "runway_beacon":
            lo, hi = library[inst["model"]]["bounds_z_up"]
            obstacles.append((inst["id"], px, py, float(inst.get("yaw", 0.0)), lo[0], hi[0], lo[1], hi[1]))

    def is_clear(x: float, y: float, margin: float = 0.50) -> bool:
        du = (x - pad_cx) * cos_a + (y - pad_cy) * sin_a
        dv = -(x - pad_cx) * sin_a + (y - pad_cy) * cos_a
        if abs(du) > half_u - 2.5 or abs(dv) > half_v - 2.5:
            return False
        for oid, ox, oy, oyaw, lx, hx, ly, hy in obstacles:
            c, s = math.cos(-oyaw), math.sin(-oyaw)
            rx = (x - ox) * c - (y - oy) * s
            ry = (x - ox) * s + (y - oy) * c
            if lx - margin <= rx <= hx + margin and ly - margin <= ry <= hy + margin:
                return False
        return True

    clip_map = {"idle": 0, "walk": 1, "talk": 2, "sit_idle": 3, "sit_talk": 4, "interact": 5}
    aids = [a["id"] for a in arch_list]
    arch_idx = {aid: i for i, aid in enumerate(aids)}
    non_hero = [a for a in aids if a not in ("pilot_explorer", "crew_lead")]
    pool = non_hero + ["pilot_explorer", "crew_lead"]
    cursor = [0]

    def next_aid() -> str:
        aid = pool[cursor[0] % len(pool)]
        cursor[0] += 1
        return aid

    actors = []

    # 1. Fixed hero showcase spots + standing groups covering Pad 43 landmarks
    standing_spots = [
        ("terminal_talk_a", "crew_lead" if "crew_lead" in arch_idx else aids[0], "talk", [-31.0, -2.5], 23.0, 0.10),
        ("terminal_talk_b", "pilot_explorer" if "pilot_explorer" in arch_idx else aids[0], "talk", [-29.0, -1.6], 203.0, 0.55),
        ("terminal_talk_c", next_aid(), "idle", [-30.1, -0.5], 195.0, 0.30),
        ("shuttle_inspect_a", next_aid(), "talk", [13.2, -14.6], 25.0, 0.25),
        ("shuttle_inspect_b", next_aid(), "idle", [15.8, -14.8], 175.0, 0.62),
        ("canopy_wait_a", next_aid(), "talk", [-4.6, -15.4], 150.0, 0.40),
        ("canopy_wait_b", next_aid(), "idle", [-2.2, -16.8], 330.0, 0.82),
    ]
    for name, aid, clip, puv, ydeg, phase in standing_spots:
        if aid not in arch_idx:
            continue
        wx, wy, wz = uv_to_city(puv[0], puv[1])
        actors.append({
            "name": name, "model": arch_idx[aid], "clip": clip_map[clip], "speed": 0.0, "phase": phase,
            "tint": [1.0, 1.0, 1.0, 1.0], "yaw": pad_yaw + math.radians(ydeg), "waypoints": [(wx, wy, wz)],
        })

    # Pool for seated bench slots (exclude long trench coats like pilot_explorer whose skirt spans legs)
    sit_candidates = [a for a in aids if a != "pilot_explorer"] or aids
    sit_cursor = [0]

    def next_sit_aid() -> str:
        aid = sit_candidates[sit_cursor[0] % len(sit_candidates)]
        sit_cursor[0] += 1
        return aid

    # 2. Seated actors directly anchored to all Pad 43 planted_bench (3) & planted_bench_wild (1)
    furniture_anchors = []
    for ftype in ("planted_bench", "planted_bench_wild"):
        for b_idx, inst in enumerate(pad43_furniture[ftype]):
            fx, fy, fz = inst["position"]
            fyaw = float(inst.get("yaw", 0.0))
            cf, sf = math.cos(fyaw), math.sin(fyaw)
            slots = FURNITURE_SLOTS[ftype]
            for s_idx, (lx, ly, ldz, lyaw) in enumerate(slots):
                aid = next_sit_aid()
                wx = fx + lx * cf - ly * sf
                wy = fy + lx * sf + ly * cf
                wz = surface_z + ldz
                clip = "sit_talk" if (len(slots) >= 2 and s_idx % 2 == 0) else "sit_idle"
                # Slight natural inward angle between seatmates
                yaw_adj = math.radians(10.0 if s_idx == 0 else -10.0)
                actors.append({
                    "name": f"{ftype}_{b_idx}_seat_{s_idx}",
                    "model": arch_idx[aid],
                    "clip": clip_map[clip],
                    "speed": 0.0,
                    "phase": (0.17 * (b_idx * 2 + s_idx)) % 1.0,
                    "tint": [1.0, 1.0, 1.0, 1.0],
                    "yaw": fyaw + math.radians(lyaw) + yaw_adj,
                    "waypoints": [(wx, wy, wz)],
                })
                furniture_anchors.append({"actor": actors[-1]["name"], "archetype": aid, "clip": clip, "furniture": ftype, "world": [wx, wy, wz]})

    # 3. Standing interaction actors at sorting_station and service_cabinet
    for ftype in ("sorting_station", "service_cabinet"):
        for f_idx, inst in enumerate(pad43_furniture[ftype]):
            fx, fy, _ = inst["position"]
            fyaw = float(inst.get("yaw", 0.0))
            cf, sf = math.cos(fyaw), math.sin(fyaw)
            for s_idx, (lx, ly, ldz, lyaw) in enumerate(FURNITURE_SLOTS[ftype]):
                aid = next_aid()
                wx = fx + lx * cf - ly * sf
                wy = fy + lx * sf + ly * cf
                actors.append({
                    "name": f"{ftype}_{f_idx}_use_{s_idx}",
                    "model": arch_idx[aid],
                    "clip": clip_map["interact"],
                    "speed": 0.0,
                    "phase": (0.29 * f_idx + 0.13) % 1.0,
                    "tint": [1.0, 1.0, 1.0, 1.0],
                    "yaw": fyaw + math.radians(lyaw),
                    "waypoints": [(wx, wy, surface_z + ldz)],
                })
                furniture_anchors.append({"actor": actors[-1]["name"], "archetype": aid, "clip": "interact", "furniture": ftype, "world": [wx, wy, surface_z + ldz]})

    # 4. Walk patrol loops ensuring every remaining cast archetype also appears active
    walk_loops = [
        ("concourse_walk_1", 1.18, 0.12, [[-27.5, 2.0], [-13.0, 2.5], [4.5, 2.5], [4.5, -1.5], [-13.0, -1.5], [-27.5, -2.0]]),
        ("concourse_walk_2", 1.13, 0.35, [[-28.0, -15.0], [-19.5, -15.0], [-19.5, -4.0], [-28.0, -4.0]]),
        ("concourse_walk_3", 1.24, 0.58, [[-21.2, 18.2], [-13.8, 7.0], [-10.4, 1.8], [-7.2, -3.2], [-8.0, -3.6], [-11.2, 1.2], [-14.6, 6.4], [-22.0, 17.6]]),
        ("apron_walk_4", 1.20, 0.72, [[-26.0, 17.0], [10.0, 18.0], [38.0, 19.0], [38.0, 24.0], [10.0, 23.0], [-26.0, 22.0]]),
        ("apron_walk_5", 1.22, 0.24, [[40.0, -18.0], [14.0, -18.0], [14.0, -24.0], [40.0, -24.0]]),
    ]
    used_models = {a["model"] for a in actors}
    missing = [a for a in aids if arch_idx[a] not in used_models]
    for w_idx, (wname, spd, ph, luv) in enumerate(walk_loops):
        aid = missing.pop(0) if missing else next_aid()
        wps = [uv_to_city(u, v) for u, v in luv]
        # Verify loop segments clear static obstacles
        ok = all(is_clear(wx, wy, 0.35) for wx, wy, _ in wps)
        if not ok:
            print(f"[cook][WARN] walk loop {wname} skirts obstacle bounds slightly", flush=True)
        yaw = math.atan2(wps[1][1] - wps[0][1], wps[1][0] - wps[0][0])
        actors.append({
            "name": wname, "model": arch_idx[aid], "clip": clip_map["walk"], "speed": spd, "phase": ph,
            "tint": [1.0, 1.0, 1.0, 1.0], "yaw": yaw, "waypoints": wps,
        })
        used_models.add(arch_idx[aid])

    # Any still-unplaced archetypes join promenade stands along the central apron axis
    extra_u = -24.0
    while missing:
        aid = missing.pop(0)
        while not is_clear(*uv_to_city(extra_u, 11.0)[:2], margin=0.6) and extra_u < 28.0:
            extra_u += 2.2
        wx, wy, wz = uv_to_city(extra_u, 11.0)
        extra_u += 2.6
        actors.append({
            "name": f"promenade_{aid}", "model": arch_idx[aid], "clip": clip_map["idle"], "speed": 0.0, "phase": 0.4,
            "tint": [1.0, 1.0, 1.0, 1.0], "yaw": pad_yaw - math.pi * 0.5, "waypoints": [(wx, wy, wz)],
        })

    # Write CHRPLC1 v2 binary
    buf = bytearray()
    buf += b"CHRPLC1\x00"
    buf += cook.struct.pack("<IddfII", 2, anchor_lat, anchor_lon, 1.46, len(actors), len(model_strides))
    for s in model_strides:
        buf += cook.struct.pack("<f", float(s))
    for a in actors:
        buf += cook.struct.pack(
            "<IIff4fIf",
            a["model"], a["clip"], a["speed"], a["phase"],
            a["tint"][0], a["tint"][1], a["tint"][2], a["tint"][3],
            len(a["waypoints"]), a["yaw"],
        )
        for wx, wy, wz in a["waypoints"]:
            buf += cook.struct.pack("<3f", wx, wy, wz)

    out_path = bank_dir / "placements.bin"
    out_path.write_bytes(bytes(buf))
    print(f"[tripo-cook] wrote {len(actors)} actors ({len(furniture_anchors)} furniture-anchored) -> {out_path}")
    return out_path, actors, furniture_anchors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cast-json", default="")
    ap.add_argument("--bank-dir", default=str(DEFAULT_BANK_DIR))
    ap.add_argument("--city-bank", default=str(DEFAULT_CITY_BANK))
    ap.add_argument("--gltf2ozz", default=str(DEFAULT_GLTF2OZZ))
    ap.add_argument("--oil-brush", default=str(DEFAULT_TRIPO_DIR / "mobile-viewer" / "oil_brush_detail.png"))
    args = ap.parse_args()

    bank_dir = Path(args.bank_dir)
    bank_dir.mkdir(parents=True, exist_ok=True)
    gltf2ozz = Path(args.gltf2ozz)
    oil_path = Path(args.oil_brush)
    if not gltf2ozz.exists():
        raise FileNotFoundError(f"gltf2ozz.exe not found: {gltf2ozz}")
    if not oil_path.exists():
        raise FileNotFoundError(f"oil_brush_detail.png not found: {oil_path}")

    if args.cast_json:
        arch_list, _ = load_archetypes_from_cast(Path(args.cast_json))
    else:
        arch_list = ARCHETYPES

    textures = []
    tex_dedup = {}

    def register_texture(fmt: int, rgba: np.ndarray) -> int:
        if fmt == 1:
            w, h, mips, data = cook.encode_bc5_normal_mips(rgba)
        else:
            w, h, mips, data = cook.encode_rgba_mips(rgba)
        key = (fmt, cook.sha256_bytes(data))
        if key in tex_dedup:
            return tex_dedup[key]
        idx = len(textures)
        tex_dedup[key] = idx
        textures.append({"w": w, "h": h, "mips": mips, "fmt": fmt, "data": data})
        return idx

    oil_tex_idx = register_texture(2, load_pow2_rgba(oil_path, max_size=1024))

    canonical_joints = None
    materials = []
    all_vertices = []
    all_indices = []
    models = []
    model_strides = []
    manifest_entries = []
    arch_index = {}

    v_dtype = np.dtype([
        ("pos", "<3f4"), ("nrm", "<3f4"), ("tan", "<4f4"), ("uv", "<2f4"),
        ("joints", "<4u2"), ("weights", "<4f4"), ("material", "<u4"), ("pad", "<u4"),
    ])
    assert v_dtype.itemsize == 80

    for m_idx, arch in enumerate(arch_list):
        aid = arch["id"]
        arch_index[aid] = m_idx
        glb_path = Path(arch["glb"])
        if not glb_path.exists():
            raise FileNotFoundError(f"Missing Tripo GLB: {glb_path}")

        ozz_files = run_gltf2ozz_mapped(gltf2ozz, glb_path, bank_dir, m_idx, arch["clips"])
        gltf, bin_chunk = cook.read_glb(glb_path)

        skin = gltf["skins"][0]
        skin_joint_names = [gltf["nodes"][ni]["name"] for ni in skin["joints"]]
        ibms = cook.read_accessor(gltf, bin_chunk, skin["inverseBindMatrices"]).astype(np.float32)
        if canonical_joints is None:
            canonical_joints = list(skin_joint_names)
        if set(skin_joint_names) != set(canonical_joints):
            raise ValueError(f"Archetype {aid} skeleton does not match Mixamo canonical joints.")

        canon_pos = {name: i for i, name in enumerate(canonical_joints)}
        skin_to_canon = np.array([canon_pos[name] for name in skin_joint_names], dtype=np.uint32)
        ordered_ibms = np.zeros((len(canonical_joints), 16), dtype=np.float32)
        for s_i, c_i in enumerate(skin_to_canon):
            ordered_ibms[c_i] = ibms[s_i]

        mat_remap = {}
        for gm_idx, gm in enumerate(gltf.get("materials", [])):
            pbr = gm.get("pbrMetallicRoughness", {})
            bc_factor = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
            rough = float(pbr.get("roughnessFactor", 1.0))
            metal = float(pbr.get("metallicFactor", 1.0))

            color_tex = -1
            if "baseColorTexture" in pbr:
                src = gltf["textures"][pbr["baseColorTexture"]["index"]]["source"]
                color_tex = register_texture(0, cook.read_image_rgba(gltf, bin_chunk, src, max_size=arch.get("tex_color", 1024)))

            norm_tex = -1
            norm_scale = 1.0
            if "normalTexture" in gm:
                src = gltf["textures"][gm["normalTexture"]["index"]]["source"]
                norm_scale = float(gm["normalTexture"].get("scale", 1.0))
                norm_tex = register_texture(1, cook.read_image_rgba(gltf, bin_chunk, src, max_size=arch.get("tex_norm", 1024)))

            orm_tex = -1
            if "metallicRoughnessTexture" in pbr:
                src = gltf["textures"][pbr["metallicRoughnessTexture"]["index"]]["source"]
                orm_tex = register_texture(2, cook.read_image_rgba(gltf, bin_chunk, src, max_size=arch.get("tex_mr", 512)))

            mat_remap[gm_idx] = len(materials)
            materials.append({
                "baseColor": [float(c) for c in bc_factor],
                "pbr": [rough, metal, norm_scale, 5.0],
                "textures": [color_tex, norm_tex, orm_tex, 0],
                "extra": [arch["hs"], arch["eye_y"], arch["nose_z"], float(oil_tex_idx + 1)],
            })

        first_vertex = sum(len(v) for v in all_vertices)
        first_index = sum(len(ix) for ix in all_indices)
        model_verts = []
        model_indices = []
        model_vcount = 0

        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                attrs = prim["attributes"]
                pos = cook.read_accessor(gltf, bin_chunk, attrs["POSITION"]).astype(np.float32)
                nrm = cook.read_accessor(gltf, bin_chunk, attrs["NORMAL"]).astype(np.float32)
                uv = (
                    cook.read_accessor(gltf, bin_chunk, attrs["TEXCOORD_0"]).astype(np.float32)
                    if "TEXCOORD_0" in attrs
                    else np.zeros((len(pos), 2), dtype=np.float32)
                )
                idx = cook.read_accessor(gltf, bin_chunk, prim["indices"]).astype(np.uint32)
                raw_tan = cook.read_accessor(gltf, bin_chunk, attrs["TANGENT"]) if "TANGENT" in attrs else None
                tan = cook.compute_safe_tangents(pos, nrm, uv, idx, existing=raw_tan)

                jnt = skin_to_canon[cook.read_accessor(gltf, bin_chunk, attrs["JOINTS_0"]).astype(np.uint32)]
                wgt = cook.read_accessor(gltf, bin_chunk, attrs["WEIGHTS_0"]).astype(np.float32)
                wsum = np.sum(wgt, axis=1, keepdims=True)
                zero_w = wsum[:, 0] < 1e-5
                if np.any(zero_w):
                    wgt[zero_w] = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
                    jnt[zero_w] = 0
                    wsum = np.sum(wgt, axis=1, keepdims=True)
                wgt = wgt / wsum

                if not (np.all(np.isfinite(pos)) and np.all(np.isfinite(nrm)) and np.all(np.isfinite(tan)) and np.all(np.isfinite(wgt))):
                    raise ValueError(f"Non-finite vertex data in {aid}")

                vbuf = np.zeros(len(pos), dtype=v_dtype)
                vbuf["pos"] = pos
                vbuf["nrm"] = nrm
                vbuf["tan"] = tan
                vbuf["uv"] = uv
                vbuf["joints"] = jnt.astype(np.uint16)
                vbuf["weights"] = wgt
                vbuf["material"] = mat_remap[prim["material"]]

                model_indices.append(idx + np.uint32(first_vertex + model_vcount))
                model_verts.append(vbuf)
                model_vcount += len(pos)

        m_verts = np.concatenate(model_verts)
        m_inds = np.concatenate(model_indices)
        lo = m_verts["pos"].min(axis=0).tolist()
        hi = m_verts["pos"].max(axis=0).tolist()
        if abs(lo[1]) > 0.03:
            raise ValueError(f"Archetype {aid} ground datum out of tolerance: minY={lo[1]:.4f}m")

        model_strides.append(float(arch["stride_m"]))
        all_vertices.append(m_verts)
        all_indices.append(m_inds)
        models.append({
            "name": aid, "lo": lo, "hi": hi,
            "firstVertex": first_vertex, "vertexCount": len(m_verts),
            "firstIndex": first_index, "indexCount": len(m_inds),
            "ibms": ordered_ibms,
        })
        manifest_entries.append({
            "id": aid, "glb": str(glb_path), "glb_sha256": cook.sha256_file(glb_path),
            "vertices": len(m_verts), "triangles": len(m_inds) // 3,
            "height_m": round(hi[1] - lo[1], 4), "min_y_m": round(lo[1], 5),
            "walk_stride_m": arch["stride_m"], "clips": arch["clips"],
            "ozz_files": {p.name: cook.sha256_file(p) for p in ozz_files},
        })
        print(f"[tripo-cook] {aid}: {len(m_verts)} verts, {len(m_inds)//3} tris, h={hi[1]-lo[1]:.3f}m, minY={lo[1]:.4f}m")

    if len(textures) > 96:
        raise ValueError(f"Texture budget exceeded: {len(textures)} > 96")

    verts_cat = np.concatenate(all_vertices)
    inds_cat = np.concatenate(all_indices)
    out = bytearray()
    out += b"CHR1\x00\x00\x00\x00"
    out += cook.struct.pack("<7I", 1, len(models), len(materials), len(textures), len(verts_cat), len(inds_cat), len(canonical_joints))
    for jname in canonical_joints:
        raw_name = jname.encode("ascii")[:63]
        out += raw_name + b"\x00" * (64 - len(raw_name))
    for tex in textures:
        out += cook.struct.pack("<5I", tex["w"], tex["h"], tex["mips"], tex["fmt"], len(tex["data"]))
        out += tex["data"]
    for mat in materials:
        out += cook.struct.pack("<4f", *mat["baseColor"])
        out += cook.struct.pack("<4f", *mat["pbr"])
        out += cook.struct.pack("<4i", *mat["textures"])
        out += cook.struct.pack("<4f", *mat["extra"])
    for m in models:
        raw_name = m["name"].encode("ascii")[:63]
        out += raw_name + b"\x00" * (64 - len(raw_name))
        out += cook.struct.pack("<3f3f4I", *m["lo"], *m["hi"], m["firstVertex"], m["vertexCount"], m["firstIndex"], m["indexCount"])
        out += m["ibms"].astype("<f4").tobytes()
    out += verts_cat.tobytes()
    out += inds_cat.astype("<u4").tobytes()

    chr_path = bank_dir / "characters.bin"
    chr_path.write_bytes(bytes(out))

    furniture_anchors = []
    if args.cast_json:
        plc_path, actors, furniture_anchors = build_furniture_placements(Path(args.city_bank), bank_dir, arch_list, model_strides)
    else:
        placement_recipe = {"city_bank": str(args.city_bank), "stride_m": 1.46, "spaceport_placements": SPACEPORT_PLACEMENTS}
        plc_path, actors, _ = cook.cook_placements(placement_recipe, bank_dir, arch_index, model_strides)

    manifest = {
        "schema": "exolune.characters.tripo.painterly.v2",
        "oil_brush_png": str(oil_path),
        "oil_brush_sha256": cook.sha256_file(oil_path),
        "oil_brush_tex_index": oil_tex_idx,
        "canonical_joints": canonical_joints,
        "textures": len(textures),
        "materials": len(materials),
        "total_vertices": int(len(verts_cat)),
        "total_triangles": int(len(inds_cat) // 3),
        "characters_bin_bytes": chr_path.stat().st_size,
        "characters_bin_sha256": cook.sha256_file(chr_path),
        "placements_bin_sha256": cook.sha256_file(plc_path),
        "actor_count": len(actors),
        "furniture_anchors": furniture_anchors,
        "archetypes": manifest_entries,
    }
    (bank_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[tripo-cook] DONE: {chr_path} ({chr_path.stat().st_size/1e6:.2f} MB), {len(textures)} textures, {len(actors)} actors")


if __name__ == "__main__":
    main()
