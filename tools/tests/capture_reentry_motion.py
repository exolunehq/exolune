"""Film the same atmospheric passage from the pilot's seat or around the moving hull."""
import argparse
import math
import os
from pathlib import Path
import subprocess

from PIL import Image

from capture_flight_immersion import ENTRY_HISTORY_SECONDS, NATIVE_TIMEOUT, PROFILES, ROOT, entry_travel


FPS = 30
WARM = 30
RADIUS = 6_378_000
# Surveyed pilot-eye positions used as camera witnesses, in metres ahead and up.
SEATS = {"classique": (0.9192, 1.07), "chasseur": (0.9192, 1.03), "navigateur": (0.65, 0.70)}
# Manufactured centres in the same local coordinates as the seat.
CENTRES = {"classique": (2.15, 0.05), "chasseur": (0.25, 0.55), "navigateur": (0, 0)}


def shifted_pose(lat, lon, alt, heading, forward, right, up):
    bearing = math.radians(heading)
    north = forward * math.cos(bearing) - right * math.sin(bearing)
    east = forward * math.sin(bearing) + right * math.cos(bearing)
    radius = RADIUS + alt
    return (lat + math.degrees(north / radius),
            lon + math.degrees(east / (radius * math.cos(math.radians(lat)))), alt + up)


def solar_point(lat, lon, bearing, elevation):
    lat, bearing, elevation = map(math.radians, (lat, bearing, elevation))
    zenith = math.pi / 2 - elevation
    sublat = math.asin(math.sin(lat) * math.cos(zenith) + math.cos(lat) * math.sin(zenith) * math.cos(bearing))
    delta = math.atan2(math.sin(bearing) * math.sin(zenith) * math.cos(lat),
                       math.cos(zenith) - math.sin(lat) * math.sin(sublat))
    return f"{math.degrees(sublat):.7f} {(lon + math.degrees(delta) + 180) % 360 - 180:.7f}"


def shot_frames(shot):
    # Preserve six seconds for glass inspection. Entry includes a cold approach,
    # the complete luminous passage and fast flight after its permanent extinction.
    return (WARM, 6 * FPS) if shot == "verre" else (ENTRY_HISTORY_SECONDS * FPS, 18 * FPS)


def exterior_camera(ship, heading, tilt, centre, t):
    # Cross the bow, broadside and wake in one continuous shot. Track the ship
    # itself so a detached front and the depth of the flank can both be seen.
    phase = min(1.0, max(0.0, (t - 1.5) / 13))
    azimuth = math.radians(24 + 128 * phase * phase * (3 - 2 * phase))
    forward, right, up = 12.0 * math.cos(azimuth), 12.0 * math.sin(azimuth), 3.25
    c, s = math.cos(tilt), math.sin(tilt)
    eye = shifted_pose(*ship, heading, (centre[0] + forward) * c - (centre[1] + up) * s,
                       right, (centre[0] + forward) * s + (centre[1] + up) * c)
    horizontal = forward * c - up * s
    yaw = heading + math.degrees(math.atan2(-right, -horizontal))
    pitch = math.degrees(math.atan2(-(forward * s + up * c), math.hypot(horizontal, right)))
    return (*eye, yaw, pitch, 0)


def write_shot(path, shot, profile, view):
    if shot == "verre":
        lat, lon, alt, heading, pitch, speed = -20.47, -75.45, 1300, 160, -1, 72
        sun = solar_point(lat, lon, heading - 15, 13)
    else:
        lat, lon, alt, heading, pitch = 30.68685, 120.10788, 57000, 76, -12
        speed = 250 if shot == "temoin" else 7750
        sun = "12 -161"
    seat_ahead, seat_up = SEATS[profile]
    tilt = math.radians(pitch)
    first, frames = shot_frames(shot)
    lines = [f"fps {FPS}"]
    for frame in range(first + frames):
        t = (frame - first) / FPS
        if shot == "verre":
            travel = speed * (t - 3)
            horizontal, vertical = travel * math.cos(tilt), travel * math.sin(tilt)
        else:
            horizontal, vertical = entry_travel(speed, t - 10, level=shot == "palier")
        ship = shifted_pose(lat, lon, alt, heading, horizontal, 0, vertical)
        if view != "cockpit":
            cam = exterior_camera(ship, heading, tilt, CENTRES[profile], t)
            mode, fov = ("pleine" if view == "decor" else "exterieur"), 43
        else:
            # Pause at each end so particles can move independently of the camera.
            phase = min(1.0, max(0.0, (t - (0.65 if shot == "verre" else 4.5)) / 4.7))
            glance = math.sin(math.pi * phase) ** 2
            ahead = seat_ahead * math.cos(tilt) - seat_up * math.sin(tilt)
            height = seat_ahead * math.sin(tilt) + seat_up * math.cos(tilt)
            side = -1 if shot == "verre" else 1
            eye = shifted_pose(*ship, heading, ahead, side * 0.09 * glance, height + 0.025 * glance)
            cam = (*eye, heading + side * 32 * glance, pitch - 4.58 + 6 * glance, 0)
            mode, fov = "cabine", 63
        values = (*ship, heading, pitch, 0, *cam, fov, 0)
        drive = "" if shot == "verre" else " coast"
        lines.append(f"{frame} {mode} " + " ".join(f"{v:.10f}" for v in values) + drive)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sun


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shot", choices=("rentree", "palier", "temoin", "verre"), default="rentree")
    parser.add_argument("--profile", choices=PROFILES, default="chasseur")
    parser.add_argument("--view", choices=("cockpit", "exterieur", "decor"), default="cockpit",
                        help="decor uses the exterior camera to record the background for silhouette checks")
    parser.add_argument("--still-at", type=float, metavar="SECONDS", help="Save a single frame from this shot as a PNG")
    parser.add_argument("--height", type=int, choices=(720, 1080), default=720)
    parser.add_argument("--exe", type=Path, default=ROOT / "x64/Release/MyPlanetEngine.exe")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/vol-immersion-2026-11-20/revision")
    args = parser.parse_args()
    exe = args.exe.resolve(strict=True)
    out = args.out.resolve()
    name = f"{args.profile}-{args.shot}" + (f"-{args.view}" if args.view != "cockpit" else "")
    work = out / name
    work.mkdir(parents=True, exist_ok=True)
    poses = work / "poses.txt"
    native = work / "native.mp4"
    clip = out / f"{name}.mp4"
    first, frames = shot_frames(args.shot)
    if args.still_at is not None:
        if not math.isfinite(args.still_at) or not 0 <= args.still_at < frames / FPS:
            parser.error("--still-at must be inside the shot")
        still = min(frames - 1, round(args.still_at * FPS))
        first, frames = first + still, 1
    sun = write_shot(poses, args.shot, args.profile, args.view)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MYPLANETENGINE_")}
    env.update(MYPLANETENGINE_RESOLUTION=f"{args.height * 16 // 9} {args.height}", MYPLANETENGINE_FULLSCREEN="0",
               MYPLANETENGINE_SCANS=str(ROOT.parent / "scans"), MYPLANETENGINE_SUN=sun,
               MYPLANETENGINE_MODELE_VAISSEAU=args.profile, MYPLANETENGINE_COORDINATES="0",
               MYPLANETENGINE_CINE=str(poses), MYPLANETENGINE_CINE_OUT=str(work),
               MYPLANETENGINE_CINE_RANGE=f"{first} {frames} {WARM}")
    if args.still_at is None:
        native.unlink(missing_ok=True)
        env["MYPLANETENGINE_CINE_VIDEO"] = str(native)
    else:
        bitmap = work / f"frame_{first:05d}.bmp"
        bitmap.unlink(missing_ok=True)
    subprocess.run([exe], env=env, cwd=exe.parent, creationflags=subprocess.CREATE_NO_WINDOW,
                   timeout=NATIVE_TIMEOUT, check=True)
    if args.still_at is not None:
        image = out / f"{name}-{still:03d}.png"
        with Image.open(bitmap) as frame:
            frame.convert("RGB").save(image)
        print(image, flush=True)
        return
    count = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                                     "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(native)], text=True)
    if int(count.strip()) != frames:
        raise ValueError(f"{native} contains {count.strip()} frames, expected {frames}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(native), "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)], check=True)
    print(clip, flush=True)


if __name__ == "__main__":
    main()
