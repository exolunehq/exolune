"""Capture the normal cockpit through flight controls on Windows (see docs/lancement.md)."""
import csv
import os
from multiprocessing.connection import Listener
from pathlib import Path
import struct
import subprocess
import uuid

INSTRUMENTS = "time wall x y z fx fy fz ux uy uz vx vy vz ground heat bank airspeed throttle headYaw headPitch seatLoad power airbrakes gpuMs".split()
CONTROLS = "mouseX mouseY wheel look centreHead brake burn boost roll finish".split()
_STATE = struct.Struct("<25d")
_INPUT = struct.Struct("<10d")


def record(executable, directory, pilot, environment, radio_meter=None):
    """Run one live flight. pilot takes the instrument tuple and returns raw mouse, wheel and button inputs."""
    directory = Path(directory).resolve()
    directory.mkdir(exist_ok=False, parents=True)
    executable = Path(executable).resolve()
    name = "ExoluneFlight-" + uuid.uuid4().hex
    env = {k: v for k, v in os.environ.items() if not k.startswith("MYPLANETENGINE_")}
    env.update(environment, MYPLANETENGINE_FLIGHT_PIPE=name, MYPLANETENGINE_FLIGHT_VIDEO=str(directory / "frames.mkv"))
    with Listener(address="\\\\.\\pipe\\" + name, family="AF_PIPE", authkey=None) as listener:
        with (directory / "engine.log").open("w") as log:
            game = subprocess.Popen([str(executable)], cwd=executable.parent, env=env,
                                    stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                with listener.accept() as connection, (directory / "flight.csv").open("w", newline="") as trace, \
                        (directory / "frames.timecodes").open("w") as pts:
                    rows = csv.writer(trace)
                    rows.writerow(INSTRUMENTS + CONTROLS + (["rxLevel"] if radio_meter else []))
                    pts.write("# timestamp format v2\n")
                    elapsed = 0.0
                    first_picture = None
                    frames = 0
                    while True:
                        state = _STATE.unpack(connection.recv_bytes(_STATE.size))
                        controls = tuple(pilot(state))
                        meter = (radio_meter(state),) if radio_meter else ()
                        connection.send_bytes(_INPUT.pack(*controls) + (struct.pack("<d", *meter) if meter else b""))
                        rows.writerow(state + controls + meter)
                        elapsed += state[1]
                        # Each new poll follows presentation of the preceding frame, including the last picture.
                        if frames:
                            if first_picture is None:
                                first_picture = elapsed
                            pts.write(f"{1000 * (elapsed - first_picture):.6f}\n")
                        if controls[-1]:
                            break
                        frames += 1
                if game.wait(timeout=60):
                    raise RuntimeError(f"Flight failed. See {log.name}")
            finally:
                if game.poll() is None:
                    game.terminate()
                    game.wait()
    return frames
