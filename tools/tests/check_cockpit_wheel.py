"""Exercise the interactive cockpit on a private Windows desktop (Python with pywin32)."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

import win32api
import win32con as wc
import win32event
import win32gui
import win32process
import win32service


TITLE = re.compile(r"cockpit, ([\d.,]+) m/s.*?verticale ([+\-\d.,]+) m/s.*?chauffe ([\d.,]+) %")
LEVER = re.compile(r"molette ([\d.,]+) \(([^)]*)\)")
POSITION = re.compile(r" \| position ([\d.,+-]+) ([\d.,+-]+) ([\d.,+-]+) ")
SPACE = "Wheel test space at rest | 250000 38.1445 103.5352 0 90 v=0 | 22 135"


def window_title(hwnd):
    # The engine puts its route label after its telemetry in a long Unicode caption.
    data = ctypes.create_unicode_buffer(4096)
    ctypes.windll.user32.GetWindowTextW(wintypes.HWND(hwnd), data, len(data))
    return data.value


def observations(hwnd, seconds):
    start = time.monotonic()
    previous = None
    records = []
    while time.monotonic() - start < seconds:
        title = window_title(hwnd)
        match = TITLE.search(title)
        if match and title != previous:
            speed, vertical, heat = (float(x.replace(",", ".")) for x in match.groups())
            # The HUD caption rounds total speed to 1 m/s and vertical speed to 0.1 m/s.
            low = math.sqrt(max(0, max(0, speed - .5)**2 - (abs(vertical) + .05)**2))
            high = math.sqrt(max(0, (speed + .5)**2 - max(0, abs(vertical) - .05)**2))
            record = dict(t=round(time.monotonic() - start, 2), speed=speed, vertical=vertical,
                          horizontal=round(math.sqrt(max(0, speed**2 - vertical**2)), 1),
                          horizontal_bounds=[round(low, 1), round(high, 1)], heat=heat)
            if lever := LEVER.search(title):
                record.update(notch=float(lever[1].replace(",", ".")), command=lever[2])
            if position := POSITION.search(title):
                record["altitude"], record["latitude"], record["longitude"] = (
                    float(x.replace(",", ".")) for x in position.groups())
            records.append(record)
            previous = title
        time.sleep(.055)
    if len(records) < 3 or records[-1]["t"] < seconds - .8:
        raise RuntimeError("Cockpit telemetry stopped updating.")
    return records


def select(hwnd, row, label):
    win32gui.SendMessageTimeout(hwnd, wc.WM_KEYDOWN, wc.VK_F1 + row, 1, wc.SMTO_ABORTIFHUNG, 3000)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        title = window_title(hwnd)
        if "test : " + label in title and TITLE.search(title):
            return
        time.sleep(.05)
    raise RuntimeError(f"Route selection did not reach {label!r}. Latest caption: {title[:950]}")


def wheel(hwnd, ticks):
    # WM_MOUSEWHEEL uses a signed high word. Send one real detent per message.
    delta = (120 if ticks > 0 else -120) & 0xffff
    for _ in range(abs(ticks)):
        win32gui.SendMessageTimeout(hwnd, wc.WM_MOUSEWHEEL, delta << 16, 0, wc.SMTO_ABORTIFHUNG, 3000)


def run(exe, route, directory, heat):
    rows = [s for s in route.read_text(encoding="utf-8-sig").splitlines()
            if s.strip() and not s.lstrip().startswith("#")]
    if len(rows) < 6 or len(rows) > 11:
        raise ValueError("Expected the assisted flight route with F3 sea, F5 entry and F6 fast level flight.")
    rows.append(SPACE)
    route_copy = directory / "route.txt"
    route_copy.write_text("\n".join(rows) + "\n", encoding="utf-8")
    labels = [r.partition("|")[0].strip() for r in rows]
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("MYPLANETENGINE_")}
    env.update(MYPLANETENGINE_TESTS=str(route_copy), MYPLANETENGINE_FIRST_TEST="3",
               MYPLANETENGINE_MODELE_VAISSEAU="chasseur", MYPLANETENGINE_VAISSEAU="cockpit",
               MYPLANETENGINE_AUDIO="0 0 0 0", MYPLANETENGINE_FULLSCREEN="0",
               MYPLANETENGINE_RESOLUTION="640 360", MYPLANETENGINE_VSYNC="1")
    name = "ExoluneWheel_" + uuid.uuid4().hex
    original = win32service.GetThreadDesktop(win32api.GetCurrentThreadId())
    desktop = win32service.CreateDesktop(name, 0, wc.MAXIMUM_ALLOWED, None)
    process, hwnd = None, None
    try:
        # Attach only this test thread. SwitchDesktop would display it and is never needed.
        desktop.SetThreadDesktop()
        info = win32process.STARTUPINFO()
        info.lpDesktop = name
        process, thread, pid, _ = win32process.CreateProcess(
            str(exe), subprocess.list2cmdline([str(exe)]), None, None, False,
            wc.CREATE_UNICODE_ENVIRONMENT, env, str(exe.parent), info)
        thread.Close()
        print(f"Dedicated PID {pid} on private desktop {name}", flush=True)
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            matches = []
            def window(w, _):
                if win32process.GetWindowThreadProcessId(w)[1] == pid and win32gui.GetClassName(w) == "MyD3DWindowClass":
                    matches.append(w)
                return True
            win32gui.EnumWindows(window, None)
            if matches:
                hwnd = matches[0]
                if TITLE.search(window_title(hwnd)):
                    break
            if win32event.WaitForSingleObject(process, 0) == wc.WAIT_OBJECT_0:
                raise RuntimeError("The test instance exited before cockpit telemetry was available.")
            time.sleep(.2)
        else:
            raise TimeoutError("The private cockpit did not finish startup.")

        result = {}
        for place, row in (("sea", 2), ("space", len(rows) - 1)):
            select(hwnd, row, labels[row])
            moves = result[place] = {}
            for label, ticks in (("one", 1), ("three", 2), ("back_to_one", -2)):
                wheel(hwnd, ticks)
                # At 190 m even an unpowered ship needs more than six seconds to hit the sea.
                moves[label] = observations(hwnd, 1.55)
                print(place, label, moves[label][-1], flush=True)
        if heat:
            for scenario, row, seconds in (("entry", 4, 23), ("level", 5, 6)):
                select(hwnd, row, labels[row])
                result[scenario] = observations(hwnd, seconds)
                print(scenario, "peak", max(r["heat"] for r in result[scenario]),
                      "end", result[scenario][-1], flush=True)
        return result
    finally:
        if process:
            if hwnd and win32gui.IsWindow(hwnd):
                win32gui.PostMessage(hwnd, wc.WM_CLOSE, 0, 0)
            if win32event.WaitForSingleObject(process, 4500) != wc.WAIT_OBJECT_0:
                win32process.TerminateProcess(process, 1)
                win32event.WaitForSingleObject(process, 4500)
            process.Close()
        original.SetThreadDesktop()
        desktop.CloseDesktop()


def ground_speed_bounds(samples):
    # Skip the caption which predates the command. Five decimal places give at
    # most one full unit of rounding on each coordinate difference. Polling for
    # a new caption adds up to one interval of uncertainty to elapsed time.
    a, b = next(s for s in samples if s["t"] > .055), samples[-1]
    if "latitude" not in a:  # older telemetry supplied speed and vertical speed alone
        return (0.0, math.inf)
    lat = abs(b["latitude"] - a["latitude"])
    lon = abs(b["longitude"] - a["longitude"])
    east = math.cos(math.radians(a["latitude"]))
    low = math.hypot(max(0, lat - .00001), east * max(0, lon - .00001))
    high = math.hypot(lat + .00001, east * (lon + .00001))
    duration = b["t"] - a["t"]
    return ((6378000 + min(a["altitude"], b["altitude"])) * math.radians(low) / (duration + .07),
            (6378000 + max(a["altitude"], b["altitude"])) * math.radians(high) / (duration - .07))


def verify(result):
    for place in ("sea", "space"):
        end = [s[-1] for s in result[place].values()]
        if "notch" in end[0] and [s["notch"] for s in end] != [1, 3, 1]:
            raise SystemExit(f"The input did not reach the requested wheel settings at {place}.")
        one, three, reduced = (s["horizontal_bounds"] for s in end)
        first = result[place]["one"]
        motion = any(s["horizontal_bounds"][0] > 0 for s in first if s["t"] >= .25)
        # The last rounded scalar speed can conceal forward motion during free fall.
        # Actual travel offers a second observable, independent of gravity.
        gps_one, gps_three, gps_reduced = (ground_speed_bounds(s) for s in result[place].values())
        if not motion and gps_one[0] <= 0:
            raise SystemExit(f"The first wheel detent produced no measurable horizontal speed at {place}.")
        increased = three[0] > one[1] or gps_three[0] > gps_one[1]
        decreased = three[0] > reduced[1] or gps_three[0] > gps_reduced[1]
        if not (increased and decreased):
            raise SystemExit(f"Wheel response too small or throttle reduction failed at {place}.")
    if "entry" in result:
        entry, level = result["entry"], result["level"]
        if entry[0]["heat"] > 2 or max(s["heat"] for s in entry) < 20 or entry[-1]["heat"] > 2:
            raise SystemExit("No transient entry heat followed by extinction.")
        if max(s["heat"] for s in level) > 1 or max(s["speed"] for s in level) < 6500:
            raise SystemExit("Fast level control did not stay cold.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("route", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--heat", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="exolune_wheel_") as tmp:
        result = run(args.exe.resolve(strict=True), args.route.resolve(strict=True), Path(tmp), args.heat)
    result["source"] = {"exe_sha256": hashlib.sha256(args.exe.read_bytes()).hexdigest(),
                        "route_sha256": hashlib.sha256(args.route.read_bytes()).hexdigest()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    verify(result)


if __name__ == "__main__":
    main()
