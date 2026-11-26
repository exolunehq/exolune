"""Resumable Tripo H3.1 image_to_model + animate_rig runner for the 20-character Exolune cast.

Uses the authenticated `tripo` CLI (~/.tripo/config.json) matching validated H3.1 detailed PBR
and Mixamo biped rigging parameters (85 credits per new character). Stops cleanly if balance is
insufficient or upon errors, saving full task provenance JSONs alongside each GLB.
"""
import argparse
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path


TRIPO_BIN = shutil.which("tripo") or shutil.which("tripo.cmd") or "tripo.cmd"


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    full_cmd = [TRIPO_BIN, *cmd[1:]] if cmd[0] == "tripo" else cmd
    res = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()


def get_balance() -> dict:
    rc, out, err = run_cmd(["tripo", "balance", "--json"])
    if rc != 0:
        raise RuntimeError(f"tripo balance failed: {out}\n{err}")
    return json.loads(out)


def extract_json(text: str) -> dict:
    start = text.rfind("{")
    while start >= 0:
        try:
            return json.loads(text[start:])
        except Exception:
            start = text.rfind("{", 0, start)
    raise ValueError(f"Could not parse JSON from tripo CLI output:\n{text[:800]}")


def download_url(url: str, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dst)


def run_character(entry: dict, cast_dir: Path, stop_on_low_balance: bool = True) -> str:
    cid = entry["id"]
    if "existing_rigged_glb" in entry:
        return "existing"

    alts = list((cast_dir / "portraits").glob(f"{cid}_front.*"))
    if not alts:
        return "missing_portrait"
    portrait = alts[0]

    mdir = cast_dir / "models" / cid
    mdir.mkdir(parents=True, exist_ok=True)
    raw_glb = mdir / f"{cid}_raw.glb"
    rig_glb = mdir / f"{cid}_rigged.glb"
    task_i2m = mdir / "task_img2model.json"
    task_rig = mdir / "task_rig.json"

    if rig_glb.exists() and rig_glb.stat().st_size > 100_000:
        return "already_rigged"

    bal = get_balance()
    need = 25 if raw_glb.exists() and task_i2m.exists() else 85
    if stop_on_low_balance and bal.get("balance", 0) < need:
        raise RuntimeError(f"LOW_BALANCE: balance={bal.get('balance')} < need={need} for {cid}")

    # Step 1: image_to_model (60 credits, H3.1 detailed + PBR)
    if not (raw_glb.exists() and task_i2m.exists() and raw_glb.stat().st_size > 100_000):
        print(f"[tripo] {cid}: starting generate image-to-model from {portrait.name} (balance={bal.get('balance')})...", flush=True)
        i2m_out_dir = mdir / "_out_i2m"
        i2m_out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            "tripo", "generate", "image-to-model",
            str(portrait),
            "--model", "v3.1-20260211",
            "-p", "texture=true",
            "-p", "pbr=true",
            "-p", "texture_quality=detailed",
            "-p", "texture_alignment=original_image",
            "-p", "enable_image_autofix=false",
            "-p", "export_uv=true",
            "-p", "geometry_quality=detailed",
            "--timeout", "600",
            "--json", "--yes", "--no-open",
            "-o", str(i2m_out_dir),
        ]
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            raise RuntimeError(f"image-to-model failed for {cid} (rc={rc}):\n{out}\n{err}")
        data = extract_json(out)
        task_i2m.write_text(json.dumps(data, indent=2), encoding="utf-8")
        glbs = sorted(i2m_out_dir.rglob("*.glb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if glbs:
            glbs[0].replace(raw_glb)
        else:
            res_out = data.get("output", {}) or data.get("result", {})
            url = res_out.get("pbr_model") or res_out.get("model")
            if isinstance(url, dict):
                url = url.get("url")
            if not url:
                raise RuntimeError(f"No raw GLB produced for {cid}: {out[:500]}")
            download_url(url, raw_glb)

    i2m_data = json.loads(task_i2m.read_text(encoding="utf-8"))
    orig_task_id = i2m_data.get("task_id") or (i2m_data.get("data", {}) if isinstance(i2m_data.get("data"), dict) else {}).get("task_id")
    if not orig_task_id:
        raise RuntimeError(f"Missing task_id in {task_i2m}")

    # Step 2: riggability check (0 cr) + anim rig (25 cr, v1.0 Mixamo spec)
    print(f"[tripo] {cid}: starting anim rig for task {orig_task_id}...", flush=True)
    rc_pre, out_pre, _ = run_cmd(["tripo", "anim", "check", orig_task_id, "--json", "--yes", "--no-open"])
    if rc_pre == 0 and "{" in out_pre:
        (mdir / "task_prerigcheck.json").write_text(json.dumps(extract_json(out_pre), indent=2), encoding="utf-8")

    rig_out_dir = mdir / "_out_rig"
    rig_out_dir.mkdir(parents=True, exist_ok=True)
    cmd_rig = [
        "tripo", "anim", "rig",
        orig_task_id,
        "--model", "v1.0-20240301",
        "--rig-type", "biped",
        "--spec", "mixamo",
        "--out-format", "glb",
        "--timeout", "600",
        "--json", "--yes", "--no-open",
        "-o", str(rig_out_dir),
    ]
    rc_r, out_r, err_r = run_cmd(cmd_rig)
    if rc_r != 0:
        raise RuntimeError(f"anim rig failed for {cid} (rc={rc_r}):\n{out_r}\n{err_r}")
    rig_data = extract_json(out_r)
    task_rig.write_text(json.dumps(rig_data, indent=2), encoding="utf-8")
    rig_cands = sorted(rig_out_dir.rglob("*.glb"), key=lambda p: p.stat().st_mtime, reverse=True)
    if rig_cands:
        rig_cands[0].replace(rig_glb)
    else:
        res_r = rig_data.get("output", {}) or rig_data.get("result", {})
        url = res_r.get("model")
        if isinstance(url, dict):
            url = url.get("url")
        if not url:
            raise RuntimeError(f"No rigged GLB produced for {cid}: {out_r[:500]}")
        download_url(url, rig_glb)

    print(f"[tripo] {cid}: DONE -> {rig_glb} ({rig_glb.stat().st_size/1e6:.2f} MB)", flush=True)
    return "completed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cast-json", default="E:/ExoluneAssets/characters-m1-2026-11-21/cast-20/cast_20.json")
    ap.add_argument("--ids", default="", help="Comma-separated subset of IDs to run")
    ap.add_argument("--allow-frozen", action="store_true", help="Do not stop locally if balance < 85 (test API)")
    args = ap.parse_args()

    cast = json.loads(Path(args.cast_json).read_text(encoding="utf-8"))
    cast_dir = Path(cast["cast_dir"])
    want = {s.strip() for s in args.ids.split(",") if s.strip()}

    summary = {}
    for entry in cast["characters"]:
        cid = entry["id"]
        if want and cid not in want:
            continue
        try:
            st = run_character(entry, cast_dir, stop_on_low_balance=not args.allow_frozen)
            summary[cid] = st
        except Exception as exc:
            summary[cid] = f"STOPPED: {exc}"
            print(f"[tripo] STOP on {cid}: {exc}", flush=True)
            if "LOW_BALANCE" in str(exc) or "credit" in str(exc).lower() or "insufficient" in str(exc).lower():
                break
    print(json.dumps({"balance": get_balance(), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
