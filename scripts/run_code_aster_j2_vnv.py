"""Run the pinned Code_Aster isotropic J2 material correlation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.verification.code_aster_j2 import CodeAsterJ2Campaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / CodeAsterJ2Campaign.study_id,
    )
    parser.add_argument(
        "--digest",
        type=Path,
        default=PROJECT_ROOT
        / "qualification"
        / "external_reference_digests"
        / "code_aster_j2.json",
    )
    arguments = parser.parse_args()
    summary = CodeAsterJ2Campaign(arguments.output).run()
    manifest = arguments.output.resolve() / "vnv_manifest.json"
    digest = {
        key: summary[key]
        for key in (
            "study_id",
            "status",
            "maturity",
            "external_solver",
            "code_aster",
            "qf_solver",
            "theory",
            "checks",
            "limitations",
        )
    }
    digest["evidence_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    arguments.digest.parent.mkdir(parents=True, exist_ok=True)
    arguments.digest.write_text(
        json.dumps(digest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Code_Aster J2 V&V: {summary['status']}")
    print(json.dumps({item["id"]: item["value"] for item in summary["checks"]}, indent=2))
    print(f"output: {arguments.output.resolve()}")
    print(f"digest: {arguments.digest.resolve()}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
