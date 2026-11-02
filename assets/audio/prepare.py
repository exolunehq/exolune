"""Cook genuine contact takes; see README.md for CC0 / CC BY 3.0 credits.

Development only: Python/numpy, ffmpeg and 7-Zip. The game reads the shipped WAVs.
"""
from pathlib import Path
import argparse
import array
import hashlib
import io
import json
import shutil
import subprocess
import urllib.request
import wave
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parent
RATE = 48000
SOURCES = {
    "fantozzi": ("https://opengameart.org/sites/default/files/Fantozzi-footsteps.7z", "fantozzi.7z",
                 "415d360e0911c1c1c5355ee94023b772e6f4044f59b9b580610e7dbffd1840fd"),
    "mastered": ("https://opengameart.org/sites/default/files/footsteps_0.zip", "mastered.zip",
                 "542564e7f6b3a0b89a0d08542438e030e77a46303855fe5bf1644a48185861e9"),
    "grass": ("https://cdn.freesound.org/previews/389/389625_4103633-hq.mp3", "grass.mp3",
              "8ff6b8ea11ddd0fd7a1f22e29e29474f1a223e7d32834754ac30b650568f349a"),
    "snow": ("https://cdn.freesound.org/previews/453/453168_6253486-hq.mp3", "snowfresh.mp3",
             "23eb61a5699cb16f53ba5e9cd05ba43951eed7fc44b8d31856dfe6e0b632a599"),
    "birds": ("https://opengameart.org/sites/default/files/birds-isaiah658_0.ogg", "birds.ogg",
              "359e4e3f9da9d75aac64cede511c7e3ef8b461f9d9f8c230f8f80e44c4b3e35f"),
}


def decode(data, contacts=True):
    args = ["ffmpeg", "-v", "error", "-i", "pipe:0"]
    if contacts:
        args += ["-af", "highpass=f=55,lowpass=f=16000"]
    args += ["-f", "f32le" if contacts else "s16le", "-ac", "1", "-ar", str(RATE), "pipe:1"]
    raw = subprocess.run(args, input=data, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64) if contacts else array.array("h", raw)


def write(name, pcm):
    with wave.open(str(ROOT / (name + ".wav")), "wb") as f:
        f.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        f.writeframes(pcm)


def trim_contact(pcm):
    pcm = pcm.copy() - np.mean(pcm)
    block = RATE // 200
    envelope = np.sqrt(np.mean(np.pad(pcm, (0, (-len(pcm)) % block)).reshape(-1, block)**2, axis=1))
    active = np.flatnonzero(envelope > max(float(np.max(envelope)) * 0.035, 1e-6))
    if len(active) == 0:
        raise ValueError("Empty contact")
    begin = max(0, int(active[0]) * block - 384)
    end = min(len(pcm), (int(active[-1]) + 1) * block + 480, begin + int(0.55 * RATE))
    pcm = pcm[begin:end]
    edge = np.arange(len(pcm))
    pcm *= np.minimum(np.minimum(edge / 144, (len(pcm) - 1 - edge) / 720), 1)
    return pcm


def bank(name, clips, rms):
    # One gain per material keeps the six performances' dynamics intact.
    levels = [np.sqrt(np.mean(p[:int(0.28 * RATE)]**2)) for p in clips]
    gain = min(rms / max(float(np.median(levels)), 1e-6), 0.72 / max(np.max(np.abs(p)) for p in clips))
    hashes = set()
    for i, pcm in enumerate(clips):
        data = np.rint(np.clip(pcm * gain, -1, 1) * 32767).astype("<i2").tobytes()
        hashes.add(hashlib.sha256(data).hexdigest())
        write(f"step-{name}-{i}", data)
    if len(hashes) != 6:
        raise ValueError(f"{name} needs six distinct performances")


def bird_bank(original):
    # Preserve the initial bird bank bit-for-bit; this revision only changes feet.
    birds = decode(original, contacts=False)
    length = int(1.8 * RATE)
    candidates = list(range(0, len(birds) - length, length))
    candidates.sort(key=lambda start: sum(x*x for x in birds[start:start+length]), reverse=True)
    for i, start in enumerate(sorted(candidates[:6])):
        pcm = birds[start:start+length]
        mean = sum(pcm) / len(pcm)
        gain = 0.65 * 32767 / max(max(abs(x - mean) for x in pcm), 1)
        out = array.array("h", (round(max(-32767, min(32767, (x - mean) * gain *
                    min(j / 480, (len(pcm) - 1 - j) / 480, 1)))) for j, x in enumerate(pcm)))
        write(f"bird{i}", out.tobytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT.parents[1] / "x64/WalkingChecks/footstep-sources")
    parser.add_argument("--sevenzip", default=shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    originals = {}
    for key, (url, filename, expected) in SOURCES.items():
        path = args.cache / filename
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Source changed: {key}")
        originals[key] = data

    archive = zipfile.ZipFile(io.BytesIO(originals["mastered"]))
    for target, folder, level in [("soil", "grass", 0.09), ("gravel", "gravel", 0.10)]:
        bank(target, [trim_contact(decode(archive.read(f"footsteps/{folder}/{i}.ogg"))) for i in range(6)], level)
        (ROOT / "licenses").mkdir(exist_ok=True)
        (ROOT / "licenses" / f"{target}-original.txt").write_bytes(archive.read(f"footsteps/{folder}/license.txt"))
    for target, material, level in [("rock", "Stone", 0.10), ("sand", "Sand", 0.065)]:
        clips = []
        for side in "LR":
            for i in range(1, 4):
                member = f"Fantozzi-footsteps/flac/Fantozzi-{material}{side}{i}.flac"
                data = subprocess.run([args.sevenzip, "e", "-so", str(args.cache / "fantozzi.7z"), member],
                                      capture_output=True, check=True).stdout
                clips.append(trim_contact(decode(data)))
        bank(target, clips, level)
    for target, peaks, level in [
            ("grass", [4.71, 5.78, 8.17, 10.62, 12.06, 14.24], 0.055),
            ("snow", [1.17, 2.10, 4.07, 6.13, 7.22, 9.53], 0.095)]:
        pcm = decode(originals[target])
        bank(target, [trim_contact(pcm[int((t - 0.18) * RATE):int((t + 0.36) * RATE)]) for t in peaks], level)
    bird_bank(originals["birds"])
    # These five prototype contacts have been replaced, including the old mud-as-soil fallback.
    for name in ["soil", "leaves1", "leaves2", "gravel", "stone"]:
        (ROOT / (name + ".wav")).unlink(missing_ok=True)
    manifest = {key: {"url": url, "sha256": sha} for key, (url, _, sha) in SOURCES.items()}
    manifest["outputs"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.glob("*.wav"))}
    (ROOT / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(manifest['outputs'])} mono PCM16 recordings at {RATE} Hz; {sum(p.stat().st_size for p in ROOT.glob('*.wav')):,} bytes")


if __name__ == "__main__":
    main()
