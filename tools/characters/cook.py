"""Cook MPFB2 glTF 2.0 character sources into Exolune's native CHR1 runtime bank.

Produces:
  - characters.bin       (CHR1: models, rest vertices, indices, IBMs, materials, mipmapped textures)
  - placements.bin       (CHRPLC1: data-driven spaceport placements & patrol loops validated against layout.json)
  - skel_<i >.ozz        (ozz-animation runtime skeleton per archetype)
  - anim_<i>_<clip>.ozz  (ozz-animation runtime clips: idle, walk, talk)
  - manifest.json        (SHA-256 provenance of sources and cooked binaries)
"""
import argparse
import hashlib
import io
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "city"))
import bc  # noqa: E402


COMPONENT_DTYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
TYPE_COUNTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"Not a glTF 2.0 binary: {path}")
    pos = 12
    gltf = None
    bin_chunk = b""
    while pos < length:
        chunk_len, chunk_type = struct.unpack_from("<I4s", raw, pos)
        pos += 8
        chunk = raw[pos : pos + chunk_len]
        pos += chunk_len
        if chunk_type == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif chunk_type == b"BIN\x00":
            bin_chunk = chunk
    if gltf is None:
        raise ValueError(f"Missing JSON chunk in {path}")
    return gltf, bin_chunk


def read_accessor(gltf, bin_chunk: bytes, acc_idx: int) -> np.ndarray:
    acc = gltf["accessors"][acc_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(COMPONENT_DTYPES[acc["componentType"]])
    num_comp = TYPE_COUNTS[acc["type"]]
    count = acc["count"]
    offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    elem_size = dtype.itemsize * num_comp
    stride = bv.get("byteStride", elem_size)
    if stride == elem_size:
        arr = np.frombuffer(bin_chunk, dtype=dtype, count=count * num_comp, offset=offset)
        arr = arr.reshape((count, num_comp) if num_comp > 1 else (count,))
    else:
        out = np.empty((count, num_comp), dtype=dtype)
        for i in range(count):
            row_off = offset + i * stride
            out[i] = np.frombuffer(bin_chunk, dtype=dtype, count=num_comp, offset=row_off)
        arr = out if num_comp > 1 else out[:, 0]
    if acc.get("normalized", False):
        if dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif dtype == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
    return arr.copy()


def read_image_rgba(gltf, bin_chunk: bytes, img_idx: int, max_size: int = 1024) -> np.ndarray:
    img_desc = gltf["images"][img_idx]
    bv = gltf["bufferViews"][img_desc["bufferView"]]
    offset = bv.get("byteOffset", 0)
    raw = bin_chunk[offset : offset + bv["byteLength"]]
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    w, h = im.size
    # Resize to nearest power of two <= max_size (square textures keep mip chains uniform).
    target = 1
    while target * 2 <= min(max(w, h), max_size):
        target *= 2
    target = max(target, 64)
    if (w, h) != (target, target):
        im = im.resize((target, target), Image.Resampling.LANCZOS)
    return np.asarray(im, dtype=np.uint8)


def encode_rgba_mips(rgba: np.ndarray) -> tuple[int, int, int, bytes]:
    h, w, _ = rgba.shape
    assert w == h and (w & (w - 1)) == 0
    mips = int(round(math.log2(w))) + 1
    chunks = []
    cur = Image.fromarray(rgba, mode="RGBA")
    for level in range(mips):
        s = max(w >> level, 1)
        im = cur if level == 0 else cur.resize((s, s), Image.Resampling.LANCZOS)
        chunks.append(np.asarray(im, dtype=np.uint8).tobytes())
    return w, h, mips, b"".join(chunks)


def encode_bc5_normal_mips(rgba: np.ndarray) -> tuple[int, int, int, bytes]:
    h, w, _ = rgba.shape
    assert w == h and (w & (w - 1)) == 0
    mips = int(round(math.log2(w))) + 1
    chunks = []
    cur = Image.fromarray(rgba[..., :3], mode="RGB")
    for level in range(mips):
        s = max(w >> level, 1)
        im = cur if level == 0 else cur.resize((s, s), Image.Resampling.LANCZOS)
        arr = np.asarray(im, dtype=np.uint8)
        # Re-normalize downsampled tangent-space normals.
        if level > 0:
            n = arr.astype(np.float32) / 127.5 - 1.0
            ln = np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-5)
            n = n / ln
            arr = np.clip(np.rint((n * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
        chunks.append(bc.bc5(arr[..., :2]))
    return w, h, mips, b"".join(chunks)


def compute_safe_tangents(pos: np.ndarray, nrm: np.ndarray, uv: np.ndarray, idx: np.ndarray, existing=None) -> np.ndarray:
    """Guarantee finite orthogonal tangent frames everywhere, including UV poles."""
    n = len(pos)
    if existing is not None and len(existing) == n:
        t = existing.astype(np.float32).copy()
        xyz = t[:, :3]
        dot_nt = np.sum(xyz * nrm, axis=1, keepdims=True)
        xyz = xyz - nrm * dot_nt
        ln = np.linalg.norm(xyz, axis=1, keepdims=True)
        bad = (ln[:, 0] < 1e-4) | ~np.all(np.isfinite(t), axis=1)
        xyz = np.where(ln > 1e-4, xyz / np.maximum(ln, 1e-6), 0.0)
        if np.any(bad):
            nb = nrm[bad]
            up = np.where(np.abs(nb[:, 1:2]) < 0.9, np.array([[0.0, 1.0, 0.0]], np.float32), np.array([[1.0, 0.0, 0.0]], np.float32))
            tb = np.cross(up, nb)
            tb /= np.maximum(np.linalg.norm(tb, axis=1, keepdims=True), 1e-6)
            xyz[bad] = tb
            t[bad, 3] = 1.0
        t[:, :3] = xyz
        t[:, 3] = np.where(t[:, 3] < 0.0, -1.0, 1.0)
        return t

    tan = np.zeros((n, 3), dtype=np.float32)
    bitan = np.zeros((n, 3), dtype=np.float32)
    tris = idx.reshape(-1, 3)
    p0, p1, p2 = pos[tris[:, 0]], pos[tris[:, 1]], pos[tris[:, 2]]
    u0, u1, u2 = uv[tris[:, 0]], uv[tris[:, 1]], uv[tris[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = u1 - u0, u2 - u0
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    inv = np.where(np.abs(det) > 1e-10, 1.0 / np.where(np.abs(det) > 1e-10, det, 1.0), 0.0)
    t_tri = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * inv[:, None]
    b_tri = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) * inv[:, None]
    for k in range(3):
        np.add.at(tan, tris[:, k], t_tri)
        np.add.at(bitan, tris[:, k], b_tri)
    tan = tan - nrm * np.sum(tan * nrm, axis=1, keepdims=True)
    ln = np.linalg.norm(tan, axis=1, keepdims=True)
    bad = ln[:, 0] < 1e-4
    tan = np.where(ln > 1e-4, tan / np.maximum(ln, 1e-6), 0.0)
    if np.any(bad):
        nb = nrm[bad]
        up = np.where(np.abs(nb[:, 1:2]) < 0.9, np.array([[0.0, 1.0, 0.0]], np.float32), np.array([[1.0, 0.0, 0.0]], np.float32))
        tb = np.cross(up, nb)
        tb /= np.maximum(np.linalg.norm(tb, axis=1, keepdims=True), 1e-6)
        tan[bad] = tb
    handed = np.where(np.sum(np.cross(nrm, tan) * bitan, axis=1) < 0.0, -1.0, 1.0).astype(np.float32)
    return np.concatenate([tan, handed[:, None]], axis=1)


def run_gltf2ozz(gltf2ozz_exe: Path, glb_path: Path, bank_dir: Path, model_index: int, clips: list[str]):
    cfg = {
        "skeleton": {
            "filename": str(bank_dir / f"skel_{model_index}.ozz"),
            "import": {
                "enable": True,
                "raw": False,
                "types": {"skeleton": True, "marker": False, "camera": False, "geometry": False, "light": False, "null": False, "any": False},
            },
        },
        "animations": [
            {
                "clip": clip,
                "filename": str(bank_dir / f"anim_{model_index}_{clip}.ozz"),
                "raw": False,
                "additive": False,
                "sampling_rate": 30.0,
                "iframe_interval": 0.0,
                "optimize": True,
                "optimization_settings": {"tolerance": 0.0005, "distance": 0.08},
            }
            for clip in clips
        ],
    }
    cfg_path = bank_dir / f"_gltf2ozz_{model_index}.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    cmd = [str(gltf2ozz_exe), f"--file={glb_path}", f"--config_file={cfg_path}", "--log_level=standard"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    cfg_path.unlink(missing_ok=True)
    if res.returncode != 0:
        raise RuntimeError(f"gltf2ozz failed for {glb_path}:\n{res.stdout}\n{res.stderr}")
    outputs = [bank_dir / f"skel_{model_index}.ozz"] + [bank_dir / f"anim_{model_index}_{c}.ozz" for c in clips]
    for p in outputs:
        if not p.exists() or p.stat().st_size < 32:
            raise RuntimeError(f"Expected ozz output missing or empty: {p}")
    return outputs


def role_from_material_name(name: str):
    """Return (role, alpha_mode, sss, sheen, tint_mask, default_rough)."""
    if name.startswith("EX_SKIN"):
        return 1, 0, 0.86, 0.03, 0.0, 0.44
    if name.startswith("EX_HAIR"):
        # Multi-layer hair cards (alpha_mode=1) or matte dark scalp under-cap (alpha_mode=0).
        is_cap = name.endswith("_cap")
        return 2, (0 if is_cap else 1), 0.0, 0.28, 0.0, (0.88 if is_cap else 0.44)
    if name.startswith("EX_EYE"):
        return 3, 0, 0.0, 0.0, 0.0, 0.05
    if name.startswith("EX_METAL"):
        return 4, 0, 0.0, 0.0, 0.0, 0.30
    if name.startswith("EX_RUBBER"):
        return 4, 0, 0.0, 0.0, 0.0, 0.72
    if name.startswith("EX_LEATHER"):
        return 4, 0, 0.0, 0.10, 0.12, 0.45
    if name.startswith("EX_CLOTH_MAIN"):
        return 0, 0, 0.0, 0.62, 0.85, 0.82
    if name.startswith(("EX_CLOTH_ACCENT", "EX_CLOTH_TRIM", "EX_CLOTH_PANTS", "EX_CLOTH_BAG")):
        return 0, 0, 0.0, 0.52, 0.22, 0.82
    return 0, 0, 0.0, 0.55, 0.85, 0.82


def _tileable_value_noise(size: int, freq: int, seed: int) -> np.ndarray:
    """Deterministic periodic value noise in [0, 1] for pore/weave/grain synthesis."""
    rng = np.random.default_rng(seed)
    grid = rng.random((freq, freq), dtype=np.float32)
    coords = np.linspace(0.0, float(freq), size, endpoint=False, dtype=np.float32)
    i0 = np.floor(coords).astype(np.int32) % freq
    i1 = (i0 + 1) % freq
    f = coords - np.floor(coords)
    u = f * f * (3.0 - 2.0 * f)
    top = grid[i0[:, None], i0[None, :]] * (1.0 - u[None, :]) + grid[i0[:, None], i1[None, :]] * u[None, :]
    bot = grid[i1[:, None], i0[None, :]] * (1.0 - u[None, :]) + grid[i1[:, None], i1[None, :]] * u[None, :]
    return top * (1.0 - u[:, None]) + bot * u[:, None]


def _height_to_normal(height: np.ndarray, strength: float) -> np.ndarray:
    """Convert periodic scalar height field into tangent-space RGB normal uint8."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
    nx = -dx
    ny = -dy
    nz = np.ones_like(height, dtype=np.float32)
    inv = 1.0 / np.maximum(np.sqrt(nx * nx + ny * ny + nz * nz), 1e-5)
    rgb = np.stack([nx * inv * 0.5 + 0.5, ny * inv * 0.5 + 0.5, nz * inv * 0.5 + 0.5], axis=-1)
    return np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)


def _blend_normals(base_rgba: np.ndarray, detail_rgb: np.ndarray, weight: float) -> np.ndarray:
    """Reoriented detail normal blend (RNM approximation) preserving macro fold normals."""
    b = base_rgba[..., :3].astype(np.float32) / 127.5 - 1.0
    d = detail_rgb.astype(np.float32) / 127.5 - 1.0
    nx = b[..., 0] + d[..., 0] * weight
    ny = b[..., 1] + d[..., 1] * weight
    nz = np.maximum(b[..., 2], 0.15)
    inv = 1.0 / np.maximum(np.sqrt(nx * nx + ny * ny + nz * nz), 1e-5)
    out = np.empty_like(base_rgba)
    out[..., 0] = np.clip(np.rint((nx * inv * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(np.rint((ny * inv * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(np.rint((nz * inv * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out


def clean_makehuman_logo(rgba: np.ndarray, mat_name: str) -> np.ndarray:
    """Cleanly replace the stock MakeHuman chest emblem on female_casualsuit01/02 with matching jersey fabric."""
    lname = mat_name.lower()
    if "female_casualsuit01" not in lname and "female_casualsuit02" not in lname:
        return rgba
    out = rgba.copy()
    h, w, _ = out.shape
    # Chest emblem sits in the upper-right shirt front panel: x in [0.69, 0.89], y in [0.13, 0.34].
    # Copy matching cotton fabric from the clean upper-left back panel at x in [0.18, 0.38], y in [0.13, 0.34].
    y0, y1 = int(h * 0.13), int(h * 0.34)
    x0, x1 = int(w * 0.69), int(w * 0.89)
    sx0 = int(w * 0.18)
    patch = out[y0:y1, sx0 : sx0 + (x1 - x0)].astype(np.float32)
    dst = out[y0:y1, x0:x1].astype(np.float32)
    # Match local luminance of the front panel border so there is zero tonal seam.
    border_dst = np.concatenate([dst[:6, :, :3].reshape(-1, 3), dst[-6:, :, :3].reshape(-1, 3)], axis=0).mean(axis=0)
    border_src = np.concatenate([patch[:6, :, :3].reshape(-1, 3), patch[-6:, :, :3].reshape(-1, 3)], axis=0).mean(axis=0)
    patch[..., :3] = np.clip(patch[..., :3] * (border_dst / np.maximum(border_src, 1.0)), 0.0, 255.0)
    yy = np.linspace(-1.0, 1.0, y1 - y0, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, x1 - x0, dtype=np.float32)[None, :]
    r = np.sqrt(xx * xx + yy * yy)
    mask = np.clip((0.96 - r) / 0.22, 0.0, 1.0)[..., None]
    out[y0:y1, x0:x1] = np.clip(np.rint(dst * (1.0 - mask) + patch * mask), 0, 255).astype(np.uint8)
    return out


def refine_styleb_skin_albedo(color_rgba: np.ndarray) -> np.ndarray:
    """Style B refined skin: strip muddy 2012 MakeHuman photographic noise while keeping crisp facial features.

    Uses edge-preserving detail smoothing (strong smoothing where local contrast is low/blotchy, zero
    blurring across lip, eyelid, brow, and nostril edges) plus subtle warm luminosity balance.
    """
    rgb = color_rgba[..., :3].astype(np.float32) / 255.0
    img = Image.fromarray(color_rgba[..., :3], mode="RGB")
    soft = np.asarray(img.filter(ImageFilter.GaussianBlur(radius=4.5)), dtype=np.float32) / 255.0
    diff = np.linalg.norm(rgb - soft, axis=-1, keepdims=True)
    # Preserve sharp anatomical edges (lips, eyes, brows, nostrils), smooth low-contrast blotches by 68%.
    edge_keep = np.clip((diff - 0.035) / 0.075, 0.0, 1.0)
    clean = soft * (1.0 - edge_keep) + rgb * edge_keep
    clean = rgb * 0.28 + clean * 0.72
    # Gentle warm Style B lift (keeps authentic dark/medium/light skin tones while removing grey cast).
    clean[..., 0] = np.clip(clean[..., 0] * 1.03, 0.0, 1.0)
    clean[..., 1] = np.clip(clean[..., 1] * 1.01, 0.0, 1.0)
    out = color_rgba.copy()
    out[..., :3] = np.clip(np.rint(clean * 255.0), 0, 255).astype(np.uint8)
    return out


def synthesize_skin_pbr(color_rgba: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Generate Style B refined velvet dermal micro-normal + linear ORM (AO, Roughness, warm SSS mask)."""
    h, w, _ = color_rgba.shape
    rgb = color_rgba[..., :3].astype(np.float32) / 255.0
    lin = np.power(np.clip(rgb, 0.0, 1.0), 2.2)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]

    lum_img = Image.fromarray(np.clip(lum * 255.0, 0, 255).astype(np.uint8), mode="L")
    blur_fine = np.asarray(lum_img.filter(ImageFilter.GaussianBlur(radius=5)), dtype=np.float32) / 255.0
    blur_wide = np.asarray(lum_img.filter(ImageFilter.GaussianBlur(radius=20)), dtype=np.float32) / 255.0

    # Delicate silky skin micro-grain (no harsh 2012 blotchy pores, matching Style B / FF7 Rebirth look).
    pore_hi = _tileable_value_noise(w, 256, 101)
    pore_mid = _tileable_value_noise(w, 96, 202)
    velvet = 1.0 - np.power(pore_hi, 1.6) * 0.35 - pore_mid * 0.25
    detail = np.clip((lum - blur_fine) * 1.15, -0.20, 0.20)
    height = velvet * 0.55 + detail * 0.45
    n_rgb = _height_to_normal(height, strength=0.62)
    norm_rgba = np.concatenate([n_rgb, np.full((h, w, 1), 255, dtype=np.uint8)], axis=-1)

    cavity = np.clip(0.92 + (lum - blur_wide) * 0.95, 0.68, 1.0)
    warmth = np.clip((lin[..., 0] - lin[..., 2]) / np.maximum(lin[..., 0] + 0.08, 0.08), 0.0, 1.0)
    rough = np.clip(0.47 - 0.07 * warmth - 0.04 * np.clip(lum - blur_wide, -0.2, 0.2) + (pore_hi - 0.5) * 0.04, 0.36, 0.54)
    sss_mask = np.clip(0.74 + 0.24 * warmth + 0.05 * (1.0 - cavity), 0.64, 1.0)

    orm = np.stack([
        np.clip(np.rint(cavity * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(rough * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(sss_mask * 255.0), 0, 255).astype(np.uint8),
        np.full((h, w), 255, dtype=np.uint8),
    ], axis=-1)
    return norm_rgba, orm


def synthesize_tactile_class_pbr(kind: str, size: int = 512) -> tuple[np.ndarray, np.ndarray]:
    """Shared tileable tactile PBR normal + linear ORM for clean solid-class garments, leather, rubber & brass."""
    y_idx = np.arange(size, dtype=np.float32)[:, None]
    x_idx = np.arange(size, dtype=np.float32)[None, :]
    if kind == "linen":
        # Crisp solarpunk woven linen warp/weft basket weave + organic thread slub.
        warp = 0.5 + 0.5 * np.sin(x_idx * (2.0 * math.pi / 4.0))
        weft = 0.5 + 0.5 * np.sin(y_idx * (2.0 * math.pi / 4.0))
        checker = ((np.floor(x_idx / 2.0) + np.floor(y_idx / 2.0)) % 2.0)
        weave = np.where(checker > 0.5, warp * 0.72 + weft * 0.28, weft * 0.72 + warp * 0.28)
        slub = _tileable_value_noise(size, 64, 901) * 0.6 + _tileable_value_noise(size, 192, 902) * 0.4
        h = weave * 0.68 + slub * 0.32
        n_rgb = _height_to_normal(h, strength=1.35)
        ao = np.clip(0.86 + (h - 0.5) * 0.26, 0.72, 1.0)
        rough = np.clip(0.82 + (0.5 - h) * 0.14, 0.70, 0.94)
        extra = np.clip(0.65 + 0.35 * h, 0.45, 1.0)
    elif kind == "leather":
        g1 = _tileable_value_noise(size, 192, 911)
        g2 = _tileable_value_noise(size, 64, 912)
        h = g1 * 0.62 + g2 * 0.38
        n_rgb = _height_to_normal(h, strength=1.25)
        ao = np.clip(0.90 + (h - 0.5) * 0.18, 0.78, 1.0)
        rough = np.clip(0.44 + (0.5 - h) * 0.14, 0.34, 0.58)
        extra = np.full((size, size), 0.25, dtype=np.float32)
    elif kind == "rubber":
        h = _tileable_value_noise(size, 256, 921) * 0.7 + _tileable_value_noise(size, 64, 922) * 0.3
        n_rgb = _height_to_normal(h, strength=0.95)
        ao = np.clip(0.88 + (h - 0.5) * 0.16, 0.76, 1.0)
        rough = np.clip(0.72 + (0.5 - h) * 0.12, 0.62, 0.84)
        extra = np.full((size, size), 0.05, dtype=np.float32)
    else:  # brushed brass metal
        streak = _tileable_value_noise(size, 32, 931) * 0.4 + _tileable_value_noise(size, 192, 932) * 0.6
        # Anisotropic horizontal brush lines.
        brush = 0.5 + 0.5 * np.sin(y_idx * (2.0 * math.pi / 3.0) + streak * 1.4)
        h = brush * 0.55 + streak * 0.45
        n_rgb = _height_to_normal(h, strength=0.45)
        ao = np.full((size, size), 0.96, dtype=np.float32)
        rough = np.clip(0.30 + (0.5 - h) * 0.10, 0.22, 0.40)
        extra = np.full((size, size), 0.0, dtype=np.float32)

    norm_rgba = np.concatenate([n_rgb, np.full((size, size, 1), 255, dtype=np.uint8)], axis=-1)
    orm = np.stack([
        np.clip(np.rint(ao * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(rough * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(extra * 255.0), 0, 255).astype(np.uint8),
        np.full((size, size), 255, dtype=np.uint8),
    ], axis=-1)
    return norm_rgba, orm


def synthesize_eye_orm(size: int = 512) -> np.ndarray:
    """Calibrated linear Eye ORM: R = eyelid socket AO, G = wet cornea/sclera roughness, B = iris mask."""
    yy = np.linspace(-1.0, 1.0, size, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, size, dtype=np.float32)[None, :]
    r = np.sqrt(xx * xx + yy * yy)
    iris_mask = np.clip((0.42 - r) / 0.12, 0.0, 1.0)
    ao = np.clip(1.0 - 0.30 * np.clip((r - 0.55) / 0.45, 0.0, 1.0) ** 1.5, 0.68, 1.0)
    rough = 0.045 * iris_mask + 0.11 * (1.0 - iris_mask)
    return np.stack([
        np.clip(np.rint(ao * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(rough * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(iris_mask * 255.0), 0, 255).astype(np.uint8),
        np.full((size, size), 255, dtype=np.uint8),
    ], axis=-1)


def synthesize_cloth_leather_pbr(color_rgba: np.ndarray, norm_rgba, ao_rgba, is_leather: bool) -> tuple[np.ndarray, np.ndarray]:
    """Blend crisp fabric weave / leather grain micro-normal and pack calibrated linear ORM (AO, Roughness, Sheen)."""
    h, w, _ = color_rgba.shape
    if is_leather:
        grain = _tileable_value_noise(w, 192, 404) * 0.65 + _tileable_value_noise(w, 64, 505) * 0.35
        micro_rgb = _height_to_normal(grain, strength=1.45)
        micro_weight = 0.32
    else:
        # Fine woven diagonal twill textile micro-pattern.
        y_idx = np.arange(h, dtype=np.float32)[:, None]
        x_idx = np.arange(w, dtype=np.float32)[None, :]
        twill = 0.5 + 0.25 * np.sin((x_idx + y_idx) * (2.0 * math.pi / 4.0)) + 0.25 * np.sin((x_idx - y_idx) * (2.0 * math.pi / 4.0))
        slub = _tileable_value_noise(w, 128, 606)
        weave = twill * 0.65 + slub * 0.35
        micro_rgb = _height_to_normal(weave, strength=1.25)
        micro_weight = 0.26

    if norm_rgba is not None:
        if norm_rgba.shape[:2] != (h, w):
            norm_rgba = np.asarray(Image.fromarray(norm_rgba, mode="RGBA").resize((w, h), Image.Resampling.LANCZOS), dtype=np.uint8)
        out_norm = _blend_normals(norm_rgba, micro_rgb, micro_weight)
    else:
        out_norm = np.concatenate([micro_rgb, np.full((h, w, 1), 255, dtype=np.uint8)], axis=-1)

    if ao_rgba is not None:
        if ao_rgba.shape[:2] != (h, w):
            ao_rgba = np.asarray(Image.fromarray(ao_rgba, mode="RGBA").resize((w, h), Image.Resampling.LANCZOS), dtype=np.uint8)
        ao = ao_rgba[..., 0].astype(np.float32) / 255.0
        ao = np.clip(0.30 + 0.70 * ao, 0.30, 1.0)
    else:
        rgb = color_rgba[..., :3].astype(np.float32) / 255.0
        lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        blur = np.asarray(Image.fromarray(np.clip(lum * 255.0, 0, 255).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=14)), dtype=np.float32) / 255.0
        ao = np.clip(0.86 + (lum - blur) * 0.85, 0.58, 1.0)

    n_var = _tileable_value_noise(w, 128, 707 if is_leather else 808)
    if is_leather:
        rough = np.clip(0.38 + (1.0 - ao) * 0.18 + (n_var - 0.5) * 0.10, 0.28, 0.62)
        sheen = np.clip(0.35 * ao, 0.1, 0.5)
    else:
        rough = np.clip(0.82 + (1.0 - ao) * 0.12 + (n_var - 0.5) * 0.09, 0.68, 0.94)
        sheen = np.clip(0.55 + 0.45 * ao, 0.35, 1.0)

    orm = np.stack([
        np.clip(np.rint(ao * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(rough * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.rint(sheen * 255.0), 0, 255).astype(np.uint8),
        np.full((h, w), 255, dtype=np.uint8),
    ], axis=-1)
    return out_norm, orm


def cook_placements(recipe: dict, bank_dir: Path, arch_index: dict[str, int], model_strides: list[float]):
    city_bank = Path(recipe["city_bank"])
    layout = json.loads((city_bank / "layout.json").read_text(encoding="utf-8"))
    library = json.loads((city_bank / "library.json").read_text(encoding="utf-8"))["models"]
    anchor_lat, anchor_lon = float(layout["anchor"][0]), float(layout["anchor"][1])

    # Pad 43 (spaceport platform) frame from layout.json.
    terminal = next(x for x in layout["instances"] if x["id"] == "space_terminal")
    pad_idx = int(terminal["pad"])
    pad = layout["earthworks"]["pads"][pad_idx]
    pad_cx, pad_cy, cos_a, sin_a, half_u, half_v, _rad, pad_z = pad
    surface_z = float(terminal["position"][2])  # exact spaceport deck datum

    def uv_to_city(u: float, v: float):
        x = pad_cx + u * cos_a - v * sin_a
        y = pad_cy + u * sin_a + v * cos_a
        return x, y, surface_z

    # Collect obstacle circles/boxes on the spaceport pad to validate clearance.
    obstacles = []
    for inst in layout["instances"]:
        px, py, pz = inst["position"]
        if math.hypot(px - pad_cx, py - pad_cy) > 100.0:
            continue
        if inst["id"] in ("runway_beacon",):
            continue
        m = library[inst["model"]]
        lo, hi = m["bounds_z_up"]
        # Use conservative rotated 2D OBB check in obstacle local frame.
        obstacles.append((inst["id"], px, py, float(inst.get("yaw", 0.0)), lo[0], hi[0], lo[1], hi[1]))

    def check_clear(label: str, x: float, y: float, margin: float = 0.55):
        # Must remain comfortably inside Pad 43 level apron.
        du = (x - pad_cx) * cos_a + (y - pad_cy) * sin_a
        dv = -(x - pad_cx) * sin_a + (y - pad_cy) * cos_a
        if abs(du) > half_u - 3.0 or abs(dv) > half_v - 3.0:
            raise ValueError(f"Placement {label} ({x:.1f}, {y:.1f}) leaves Pad 43 level deck (u={du:.1f}, v={dv:.1f}).")
        for oid, ox, oy, oyaw, lx, hx, ly, hy in obstacles:
            c, s = math.cos(-oyaw), math.sin(-oyaw)
            dx, dy = x - ox, y - oy
            rx = dx * c - dy * s
            ry = dx * s + dy * c
            if lx - margin <= rx <= hx + margin and ly - margin <= ry <= hy + margin:
                raise ValueError(f"Placement {label} at ({x:.2f},{y:.2f}) collides with {oid} at ({ox:.2f},{oy:.2f}) (local {rx:.2f},{ry:.2f}).")

    clip_map = {"idle": 0, "walk": 1, "talk": 2}
    actors = []
    pad_yaw = math.atan2(sin_a, cos_a)
    for item in recipe["spaceport_placements"]:
        m_idx = arch_index[item["archetype"]]
        c_idx = clip_map[item["clip"]]
        speed = float(item.get("speed", 0.0))
        phase = float(item.get("phase", 0.0))
        tint = item.get("tint", [1.0, 1.0, 1.0])
        scale = float(item.get("scale", 1.0))
        if "loop_pad_uv" in item:
            wps = [uv_to_city(u, v) for u, v in item["loop_pad_uv"]]
            for i, (wx, wy, _wz) in enumerate(wps):
                check_clear(f"{item['name']}[{i}]", wx, wy)
                # Also sample segment midpoints against obstacles.
                nx, ny, _ = wps[(i + 1) % len(wps)]
                for s in (0.25, 0.5, 0.75):
                    check_clear(f"{item['name']}[{i}->{s}]", wx + (nx - wx) * s, wy + (ny - wy) * s)
            yaw = math.atan2(wps[1][1] - wps[0][1], wps[1][0] - wps[0][0])
        else:
            u, v = item["pad_uv"]
            wx, wy, wz = uv_to_city(u, v)
            check_clear(item["name"], wx, wy)
            wps = [(wx, wy, wz)]
            yaw = pad_yaw + math.radians(float(item.get("yaw_deg", 0.0)))
        actors.append({
            "name": item["name"],
            "model": m_idx,
            "clip": c_idx,
            "speed": speed,
            "phase": phase,
            "tint": [float(tint[0]), float(tint[1]), float(tint[2]), scale],
            "yaw": yaw,
            "waypoints": wps,
        })

    # Write CHRPLC1 v2 binary (includes per-archetype measured MoCap stride table for 0% foot sliding).
    buf = bytearray()
    buf += b"CHRPLC1\x00"
    buf += struct.pack("<IddfII", 2, anchor_lat, anchor_lon, float(recipe["stride_m"]), len(actors), len(model_strides))
    for s in model_strides:
        buf += struct.pack("<f", float(s))
    for a in actors:
        buf += struct.pack(
            "<IIff4fIf",
            a["model"],
            a["clip"],
            a["speed"],
            a["phase"],
            a["tint"][0],
            a["tint"][1],
            a["tint"][2],
            a["tint"][3],
            len(a["waypoints"]),
            a["yaw"],
        )
        for wx, wy, wz in a["waypoints"]:
            buf += struct.pack("<3f", wx, wy, wz)

    out_path = bank_dir / "placements.bin"
    out_path.write_bytes(bytes(buf))
    print(f"[cook] wrote {len(actors)} spaceport actors (all obstacle-clear on Pad 43) -> {out_path}")
    return out_path, actors, (anchor_lat, anchor_lon, pad_cx, pad_cy, surface_z, cos_a, sin_a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe", default="assets/characters/spaceport_m1.json")
    ap.add_argument("--gltf2ozz", default="E:/ExoluneAssets/characters-m1-2026-11-21/ozz-build/src/animation/offline/gltf/gltf2ozz.exe")
    args = ap.parse_args()

    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    out_root = Path(recipe["output_root"])
    bank_dir = out_root / "bank"
    bank_dir.mkdir(parents=True, exist_ok=True)
    gltf2ozz = Path(args.gltf2ozz)
    if not gltf2ozz.exists():
        raise FileNotFoundError(f"gltf2ozz.exe not found at {gltf2ozz}")

    clips = ["idle", "walk", "talk"]
    canonical_joints = None
    textures = []  # list of dict(w, h, mips, fmt, data)
    tex_dedup = {}  # (fmt, sha256) -> index
    materials = []  # list of dict
    all_vertices = []
    all_indices = []
    models = []
    model_strides = []
    manifest_entries = []
    arch_index = {}

    def register_texture(fmt: int, rgba: np.ndarray) -> int:
        if fmt == 1:
            w, h, mips, data = encode_bc5_normal_mips(rgba)
        else:
            w, h, mips, data = encode_rgba_mips(rgba)
        key = (fmt, sha256_bytes(data))
        if key in tex_dedup:
            return tex_dedup[key]
        idx = len(textures)
        tex_dedup[key] = idx
        textures.append({"w": w, "h": h, "mips": mips, "fmt": fmt, "data": data})
        return idx

    for m_idx, arch in enumerate(recipe["archetypes"]):
        aid = arch["id"]
        arch_index[aid] = m_idx
        glb_path = out_root / "sources" / aid / f"{aid}.glb"
        if not glb_path.exists():
            raise FileNotFoundError(f"Missing authored GLB: {glb_path}")

        # 1. Cook ozz skeleton & clips directly from the GLB.
        ozz_files = run_gltf2ozz(gltf2ozz, glb_path, bank_dir, m_idx, clips)

        # 2. Parse GLB skin, geometry, materials and textures.
        gltf, bin_chunk = read_glb(glb_path)
        skin = gltf["skins"][0]
        skin_joint_nodes = skin["joints"]
        skin_joint_names = [gltf["nodes"][ni]["name"] for ni in skin_joint_nodes]
        ibms = read_accessor(gltf, bin_chunk, skin["inverseBindMatrices"]).astype(np.float32)
        if canonical_joints is None:
            canonical_joints = list(skin_joint_names)
        if set(skin_joint_names) != set(canonical_joints):
            raise ValueError(f"Archetype {aid} skeleton does not match canonical joints!")

        # Reorder IBMs into canonical_joints order and build skin_idx -> canonical_idx remap.
        canon_pos = {name: i for i, name in enumerate(canonical_joints)}
        skin_to_canon = np.array([canon_pos[name] for name in skin_joint_names], dtype=np.uint32)
        ordered_ibms = np.zeros((len(canonical_joints), 16), dtype=np.float32)
        for s_i, c_i in enumerate(skin_to_canon):
            ordered_ibms[c_i] = ibms[s_i]

        # Build material map for this GLB (including calibrated PBR Normal + linear ORM maps).
        mat_remap = {}
        shared_eye_orm = synthesize_eye_orm(512)
        shared_class_pbr = {
            k: synthesize_tactile_class_pbr(k, 512) for k in ("linen", "leather", "rubber", "metal")
        }
        for gm_idx, gm in enumerate(gltf.get("materials", [])):
            mname = gm.get("name", f"{aid}_mat_{gm_idx}")
            role, alpha_mode, sss, sheen, tint_mask, default_rough = role_from_material_name(mname)
            pbr = gm.get("pbrMetallicRoughness", {})
            bc_factor = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
            rough = float(pbr.get("roughnessFactor", default_rough))
            metal = float(pbr.get("metallicFactor", 0.0))
            if gm.get("alphaMode", "OPAQUE") in ("MASK", "BLEND"):
                alpha_mode = 1

            color_rgba = None
            color_tex = -1
            if "baseColorTexture" in pbr:
                tex_obj = gltf["textures"][pbr["baseColorTexture"]["index"]]
                color_rgba = read_image_rgba(gltf, bin_chunk, tex_obj["source"], max_size=1024)
                if role == 0:
                    color_rgba = clean_makehuman_logo(color_rgba, mname)
                elif role == 1:
                    color_rgba = refine_styleb_skin_albedo(color_rgba)
                color_tex = register_texture(0, color_rgba)

            raw_norm_rgba = None
            norm_scale = 1.0
            if "normalTexture" in gm:
                tex_obj = gltf["textures"][gm["normalTexture"]["index"]]
                norm_scale = float(gm["normalTexture"].get("scale", 1.0))
                raw_norm_rgba = read_image_rgba(gltf, bin_chunk, tex_obj["source"], max_size=1024)

            ao_rgba = None
            if "occlusionTexture" in gm:
                tex_obj = gltf["textures"][gm["occlusionTexture"]["index"]]
                ao_rgba = read_image_rgba(gltf, bin_chunk, tex_obj["source"], max_size=1024)

            norm_tex = -1
            orm_tex = -1
            if role == 1 and color_rgba is not None:
                # Style B refined velvet dermal micro-normal + linear skin ORM (AO, Roughness, SSS mask).
                skin_norm, skin_orm = synthesize_skin_pbr(color_rgba)
                norm_tex = register_texture(1, skin_norm)
                norm_scale = 0.36
                orm_tex = register_texture(2, skin_orm)
            elif role == 3:
                # Wet cornea / sclera ORM (deduplicated once across all archetypes).
                orm_tex = register_texture(2, shared_eye_orm)
                if raw_norm_rgba is not None:
                    norm_tex = register_texture(1, raw_norm_rgba)
            elif role == 2:
                # Multi-layer Hair Cards: keep strand normal + pack baked root-to-tip AO into linear ORM.
                if raw_norm_rgba is not None:
                    norm_tex = register_texture(1, raw_norm_rgba)
                    norm_scale = 0.85
                if ao_rgba is not None:
                    ao_v = ao_rgba[..., 0].astype(np.float32) / 255.0
                    h_orm = np.stack([
                        np.clip(np.rint(ao_v * 255.0), 0, 255).astype(np.uint8),
                        np.clip(np.rint((0.46 - 0.08 * ao_v) * 255.0), 0, 255).astype(np.uint8),
                        np.full(ao_v.shape, 210, dtype=np.uint8),
                        np.full(ao_v.shape, 255, dtype=np.uint8),
                    ], axis=-1)
                    orm_tex = register_texture(2, h_orm)
            elif role in (0, 4) and color_rgba is not None:
                # Fabric weave / leather grain micro-normal + real AO & calibrated roughness ORM.
                out_norm, out_orm = synthesize_cloth_leather_pbr(color_rgba, raw_norm_rgba, ao_rgba, is_leather=(role == 4))
                norm_tex = register_texture(1, out_norm)
                norm_scale = 0.88 if role == 0 else 0.85
                orm_tex = register_texture(2, out_orm)
            elif role in (0, 4):
                # Clean solid-color semantic PBR class (Tripo modular wardrobe kit): apply shared tileable weave/leather/rubber/brass!
                ckind = "metal" if mname.startswith("EX_METAL") else ("rubber" if mname.startswith("EX_RUBBER") else ("leather" if role == 4 else "linen"))
                c_norm, c_orm = shared_class_pbr[ckind]
                norm_tex = register_texture(1, c_norm)
                norm_scale = 0.85 if ckind == "linen" else (0.78 if ckind == "leather" else 0.55)
                orm_tex = register_texture(2, c_orm)
            elif raw_norm_rgba is not None:
                norm_tex = register_texture(1, raw_norm_rgba)

            mat_idx = len(materials)
            mat_remap[gm_idx] = mat_idx
            materials.append({
                "name": mname,
                "baseColor": [float(bc_factor[0]), float(bc_factor[1]), float(bc_factor[2]), float(bc_factor[3])],
                "pbr": [rough, metal, norm_scale, float(role)],
                "textures": [color_tex, norm_tex, orm_tex, alpha_mode],
                "extra": [sss, sheen, tint_mask, 0.0],
            })

        first_vertex = sum(len(v) for v in all_vertices)
        first_index = sum(len(ix) for ix in all_indices)
        model_verts = []
        model_indices = []
        model_vcount = 0

        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                attrs = prim["attributes"]
                pos = read_accessor(gltf, bin_chunk, attrs["POSITION"]).astype(np.float32)
                nrm = read_accessor(gltf, bin_chunk, attrs["NORMAL"]).astype(np.float32)
                uv = (
                    read_accessor(gltf, bin_chunk, attrs["TEXCOORD_0"]).astype(np.float32)
                    if "TEXCOORD_0" in attrs
                    else np.zeros((len(pos), 2), dtype=np.float32)
                )
                idx = read_accessor(gltf, bin_chunk, prim["indices"]).astype(np.uint32)
                raw_tan = read_accessor(gltf, bin_chunk, attrs["TANGENT"]) if "TANGENT" in attrs else None
                tan = compute_safe_tangents(pos, nrm, uv, idx, existing=raw_tan)

                jnt = read_accessor(gltf, bin_chunk, attrs["JOINTS_0"]).astype(np.uint32)
                wgt = read_accessor(gltf, bin_chunk, attrs["WEIGHTS_0"]).astype(np.float32)
                # Remap skin joint indices to canonical joint order and strictly re-normalize weights.
                jnt = skin_to_canon[jnt]
                wsum = np.sum(wgt, axis=1, keepdims=True)
                zero_w = wsum[:, 0] < 1e-5
                if np.any(zero_w):
                    wgt[zero_w] = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
                    jnt[zero_w] = 0
                    wsum = np.sum(wgt, axis=1, keepdims=True)
                wgt = wgt / wsum

                if not (np.all(np.isfinite(pos)) and np.all(np.isfinite(nrm)) and np.all(np.isfinite(tan)) and np.all(np.isfinite(wgt))):
                    raise ValueError(f"Non-finite vertex data in {aid}")

                mat_id = mat_remap[prim["material"]]
                v_dtype = np.dtype([
                    ("pos", "<3f4"),
                    ("nrm", "<3f4"),
                    ("tan", "<4f4"),
                    ("uv", "<2f4"),
                    ("joints", "<4u2"),
                    ("weights", "<4f4"),
                    ("material", "<u4"),
                    ("pad", "<u4"),
                ])
                assert v_dtype.itemsize == 80
                vbuf = np.zeros(len(pos), dtype=v_dtype)
                vbuf["pos"] = pos
                vbuf["nrm"] = nrm
                vbuf["tan"] = tan
                vbuf["uv"] = uv
                vbuf["joints"] = jnt.astype(np.uint16)
                vbuf["weights"] = wgt
                vbuf["material"] = mat_id

                model_indices.append(idx + np.uint32(first_vertex + model_vcount))
                model_verts.append(vbuf)
                model_vcount += len(pos)

        m_verts = np.concatenate(model_verts)
        m_inds = np.concatenate(model_indices)
        lo = m_verts["pos"].min(axis=0).tolist()
        hi = m_verts["pos"].max(axis=0).tolist()
        if abs(lo[1]) > 0.03:
            raise ValueError(f"Archetype {aid} ground datum out of tolerance: min Y = {lo[1]:.4f}m")

        src_meta_path = out_root / "sources" / aid / "source.json"
        walk_stride_m = float(recipe["stride_m"])
        if src_meta_path.exists():
            src_meta = json.loads(src_meta_path.read_text(encoding="utf-8"))
            measured = float(src_meta.get("mocap", {}).get("walk", {}).get("stride_m", 0.0))
            if measured > 0.4:
                walk_stride_m = measured
        model_strides.append(walk_stride_m)

        all_vertices.append(m_verts)
        all_indices.append(m_inds)
        models.append({
            "name": aid,
            "lo": lo,
            "hi": hi,
            "firstVertex": first_vertex,
            "vertexCount": len(m_verts),
            "firstIndex": first_index,
            "indexCount": len(m_inds),
            "ibms": ordered_ibms,
        })
        manifest_entries.append({
            "id": aid,
            "glb_sha256": sha256_file(glb_path),
            "vertices": len(m_verts),
            "triangles": len(m_inds) // 3,
            "height_m": round(hi[1] - lo[1], 4),
            "min_y_m": round(lo[1], 5),
            "walk_stride_m": round(walk_stride_m, 4),
            "ozz_files": {p.name: sha256_file(p) for p in ozz_files},
        })
        print(f"[cook] {aid}: {len(m_verts)} verts, {len(m_inds)//3} tris, height={hi[1]-lo[1]:.3f}m, minY={lo[1]:.4f}m, stride={walk_stride_m:.3f}m")

    # Pack characters.bin (CHR1).
    verts_cat = np.concatenate(all_vertices)
    inds_cat = np.concatenate(all_indices)
    out = bytearray()
    out += b"CHR1\x00\x00\x00\x00"
    out += struct.pack(
        "<7I",
        1,
        len(models),
        len(materials),
        len(textures),
        len(verts_cat),
        len(inds_cat),
        len(canonical_joints),
    )
    for jname in canonical_joints:
        raw_name = jname.encode("ascii")[:63]
        out += raw_name + b"\x00" * (64 - len(raw_name))
    for tex in textures:
        out += struct.pack("<5I", tex["w"], tex["h"], tex["mips"], tex["fmt"], len(tex["data"]))
        out += tex["data"]
    for mat in materials:
        out += struct.pack("<4f", *mat["baseColor"])
        out += struct.pack("<4f", *mat["pbr"])
        out += struct.pack("<4i", *mat["textures"])
        out += struct.pack("<4f", *mat["extra"])
    for m in models:
        raw_name = m["name"].encode("ascii")[:63]
        out += raw_name + b"\x00" * (64 - len(raw_name))
        out += struct.pack("<3f3f4I", *m["lo"], *m["hi"], m["firstVertex"], m["vertexCount"], m["firstIndex"], m["indexCount"])
        out += m["ibms"].astype("<f4").tobytes()
    out += verts_cat.tobytes()
    out += inds_cat.astype("<u4").tobytes()

    chr_path = bank_dir / "characters.bin"
    chr_path.write_bytes(bytes(out))

    plc_path, actors, spaceport_info = cook_placements(recipe, bank_dir, arch_index, model_strides)

    manifest = {
        "schema": "exolune.characters.bank.v1",
        "recipe_sha256": sha256_file(Path(args.recipe)),
        "canonical_joints": canonical_joints,
        "textures": len(textures),
        "materials": len(materials),
        "total_vertices": int(len(verts_cat)),
        "total_triangles": int(len(inds_cat) // 3),
        "characters_bin_bytes": chr_path.stat().st_size,
        "characters_bin_sha256": sha256_file(chr_path),
        "placements_bin_sha256": sha256_file(plc_path),
        "actor_count": len(actors),
        "archetypes": manifest_entries,
    }
    (bank_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[cook] DONE: {chr_path} ({chr_path.stat().st_size/1e6:.2f} MB), {len(textures)} textures, {len(materials)} materials, {len(actors)} actors")


if __name__ == "__main__":
    main()
