"""Batch-export ready Tripo rigged GLBs to multi-clip Exolune GLBs via Blender 5.2."""
import argparse
import json
import subprocess
from pathlib import Path


BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
BUILD_SCRIPT = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\tripo-poc\build_aaa_tripo_v2.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cast-json", default=r"E:\ExoluneAssets\characters-m1-2026-11-21\cast-20\cast_20.json")
    ap.add_argument("--ids", default="", help="Optional comma-separated archetype IDs")
    ap.add_argument("--force", action="store_true", help="Re-export even if *_aaa.glb already exists")
    args = ap.parse_args()

    cast = json.loads(Path(args.cast_json).read_text(encoding="utf-8"))
    models_dir = Path(cast["models_dir"])
    glbs_dir = Path(cast["glbs_dir"])
    glbs_dir.mkdir(parents=True, exist_ok=True)
    want = {s.strip() for s in args.ids.split(",") if s.strip()}

    done, skipped, failed = [], [], []
    for entry in cast["characters"]:
        cid = entry["id"]
        if want and cid not in want:
            continue
        if "existing_rigged_glb" in entry:
            rigged = Path(entry["existing_rigged_glb"])
        else:
            rigged = models_dir / cid / f"{cid}_rigged.glb"
        if not rigged.exists():
            skipped.append((cid, "missing_rigged"))
            continue

        out_glb = glbs_dir / f"{cid}_aaa.glb"
        lm_json = glbs_dir / f"{cid}_landmarks.json"
        if out_glb.exists() and lm_json.exists() and not args.force:
            skipped.append((cid, "already_exported"))
            continue

        clip_list = ",".join(dict.fromkeys(entry["clips"].values()))
        cmd = [
            str(BLENDER_EXE),
            "--background",
            "--python", str(BUILD_SCRIPT),
            "--",
            "--rigged-glb", str(rigged),
            "--out-glb", str(out_glb),
            "--landmarks-out", str(lm_json),
            "--target-height", str(entry.get("target_height", 1.70)),
            "--target-tris", str(entry.get("target_tris", 60000)),
            "--clips", clip_list,
            "--skip-renders",
        ]
        if cid != "pilot_explorer":
            cmd.append("--skip-polish-tex")

        print(f"[batch-blender] exporting {cid} ({entry.get('target_tris', 60000)} tris, h={entry.get('target_height')}m)...", flush=True)
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode != 0 or not out_glb.exists():
            print(f"[batch-blender] FAILED {cid}:\n{res.stdout[-800:]}\n{res.stderr[-400:]}", flush=True)
            failed.append(cid)
        else:
            print(f"[batch-blender] OK {cid} -> {out_glb.name} ({out_glb.stat().st_size/1e6:.2f} MB)", flush=True)
            done.append(cid)

    print(json.dumps({"done": done, "skipped": skipped, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
