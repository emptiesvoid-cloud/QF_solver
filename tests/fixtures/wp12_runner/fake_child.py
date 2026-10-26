"""Synthetic subprocess used only to exercise WP12 runner supervision."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time


def main() -> int:
    if len(sys.argv) != 3:
        return 64
    case = sys.argv[1]
    pid_path = Path(sys.argv[2])
    if case == "success":
        print("WP12_RUNNER_SYNTHETIC_SUCCESS", flush=True)
        return 0
    if case == "exit":
        print("WP12_RUNNER_SYNTHETIC_NONZERO", file=sys.stderr, flush=True)
        return 17
    if case == "sleep":
        time.sleep(60)
        return 0
    if case == "tree":
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "hold", str(pid_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        deadline = time.monotonic() + 2.0
        while not pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        print("WP12_RUNNER_SYNTHETIC_DESCENDANT", flush=True)
        time.sleep(60)
        return 0
    if case == "hold":
        pid_path.write_text(str(os.getpid()), encoding="ascii")
        time.sleep(60)
        return 0
    if case == "flood":
        sys.stdout.buffer.write(b"x" * (1024 * 1024))
        sys.stdout.flush()
        return 0
    if case == "memory":
        payload = bytearray(256 * 1024 * 1024)
        for offset in range(0, len(payload), 4096):
            payload[offset] = 1
        print("WP12_RUNNER_SYNTHETIC_MEMORY_ALLOCATION_COMPLETED", flush=True)
        return 0
    if case == "cpu":
        deadline = time.monotonic() + 10.0
        accumulator = 0
        while time.monotonic() < deadline:
            accumulator = (accumulator + 1) % 1_000_003
        print(f"WP12_RUNNER_SYNTHETIC_CPU_COMPLETED {accumulator}", flush=True)
        return 0
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
