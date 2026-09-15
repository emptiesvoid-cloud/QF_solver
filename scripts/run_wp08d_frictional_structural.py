"""WP08-D Phase-1 frictional structural runner.

The default is fail-closed.  ``--dry-run`` performs only frozen contract,
mesh, load and artifact-layout checks.  Structural/contact/reference execution
requires a separately versioned Owner authorization file and is intentionally
not enabled by this repository task.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    _repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_repository_root))
    sys.path.insert(0, str(_repository_root / "src"))

from scripts.wp08d_phase1_common import (
    ARTIFACT_ROOT,
    UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED,
    dry_run,
    execute_phase1,
    repository_root,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", choices=("M1", "M2", "M3"), required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute-phase1", action="store_true")
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=repository_root() / ARTIFACT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.dry_run and not args.execute_phase1:
        print(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED, file=sys.stderr)
        return 2
    try:
        if args.dry_run:
            report = dry_run(args.mesh, args.output_dir)
            print(f"DRY_RUN_ONLY mesh={report['mesh']} output={args.output_dir}")
            return 0
        execute_phase1(args.mesh, args.output_dir, args.authorization_file)
        print(f"PHASE1_COMPLETED mesh={args.mesh} output={args.output_dir}")
        return 0
    except RuntimeError as error:
        if str(error) == UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED:
            print(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED, file=sys.stderr)
            return 2
        print(f"WP08D_PHASE1_FAIL_CLOSED: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
