"""Harmless child process used only to test the local V&V runner."""

from __future__ import annotations

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdout", default="synthetic stdout")
    parser.add_argument("--stderr", default="synthetic stderr")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.0)
    args = parser.parse_args()
    print(args.stdout, flush=True)
    print(args.stderr, file=sys.stderr, flush=True)
    if args.sleep:
        time.sleep(args.sleep)
    return args.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
