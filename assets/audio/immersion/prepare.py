"""Cook and verify the Exolune immersion bank. Authoring only, no cloud calls."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np


ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def squelch(rate, duration, opening):
    count = int(duration * rate)
    t = np.arange(count) / rate
    noise = np.random.default_rng(77 if opening else 79).standard_normal(count)
    broad = np.convolve(noise, np.ones(5) / 5, "same")
    body = broad - np.convolve(broad, np.ones(29) / 29, "same")
    return (0.065 * body * np.exp(-t * 34) * np.minimum(t * 350, 1))[:, None]


def cook(master, section, rate):
    channels = section.getint("channels")
    loop = section.getboolean("loop")
    filters = "highpass=f=28" if loop else "highpass=f=300,lowpass=f=3200"
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(master), "-af", filters,
                              "-ar", str(rate), "-ac", str(channels), "-f", "f32le", "-"],
                             check=True, stdout=subprocess.PIPE).stdout
    pcm = np.frombuffer(decoded, "<f4").astype(np.float64).reshape(-1, channels)
    if not len(pcm) or not np.isfinite(pcm).all():
        raise ValueError(f"Invalid decoded samples in {master}")
    pcm -= pcm.mean(axis=0)
    if loop:
        # Join the end to the beginning at matching slopes, then rotate the splice away from the wrap.
        pcm = pcm[:round(section.getfloat("seconds") * rate)]
        count = round(0.032 * rate)
        a = np.linspace(0, 1, count)[:, None]
        a = a * a * (3 - 2 * a)
        splice = pcm[-count:] * (1 - a) + pcm[:count] * a
        pcm = np.concatenate((pcm[count:-count], splice))
    else:
        pcm = np.tanh(pcm * 1.7)
        pcm = np.concatenate((squelch(rate, .10, True), pcm, squelch(rate, .14, False)))
    rms = np.sqrt(np.mean(pcm * pcm))
    if rms < 1e-5:
        raise ValueError(f"Silent master {master}")
    gain = min((.14 if loop else .19) / rms, .81 / max(abs(pcm.min()), abs(pcm.max())))
    return np.rint(pcm * gain * 32767).astype("<i2")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--masters", type=Path, default=ROOT.parents[2] / "x64/ImmersionAudio/masters")
    parser.add_argument("--check", action="store_true", help="verify the shipped WAVs without the original downloads")
    args = parser.parse_args()
    bank = configparser.ConfigParser(interpolation=None)
    bank.read(ROOT / "bank.ini", encoding="utf-8")
    rate = bank["bank"].getint("sample_rate")
    receipt = ROOT / "cooked.json"
    outputs = {}
    for role in (s for s in bank.sections() if s != "bank"):
        section = bank[role]
        wav = ROOT / f"{role}.wav"
        if not args.check:
            master = args.masters / f"{role}.master"
            if digest(master) != section["source_sha256"]:
                raise ValueError(f"Wrong source for {role}")
            pcm = cook(master, section, rate)
            with wave.open(str(wav), "wb") as out:
                out.setparams((section.getint("channels"), 2, rate, 0, "NONE", "not compressed"))
                out.writeframes(pcm.tobytes())
        with wave.open(str(wav), "rb") as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (
                section.getint("channels"), 2, rate)
            frames = stream.getnframes()
            samples = np.frombuffer(stream.readframes(frames), "<i2").reshape(frames, -1)
            assert frames > rate and 100 < np.abs(samples.astype(float)).max() < .82 * 32768
            if section.getboolean("loop"):
                assert frames == round(rate * section.getfloat("seconds")) - round(.032 * rate)
                steps = np.abs(np.diff(samples.astype(float), axis=0))
                seam = np.abs(samples[0].astype(float) - samples[-1])
                assert np.all(seam <= steps.max(axis=0)), f"Invalid seam in {role}"
        outputs[wav.name] = {"frames": frames, "sha256": digest(wav)}
    if args.check:
        if outputs != json.loads(receipt.read_text(encoding="utf-8")):
            raise ValueError("Cooked audio differs from its receipt")
    else:
        receipt.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    print(f"{len(outputs)} verified PCM16 recordings at {rate} Hz")


if __name__ == "__main__":
    main()
