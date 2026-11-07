"""Fetch and stage only the SHA-bound QF Solver 0.2.12 PyPI files."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable


WHEEL_NAME = "qf_solver-0.2.12-py3-none-any.whl"
SDIST_NAME = "qf_solver-0.2.12.tar.gz"
CHECKSUM_NAME = "qf_solver-0.2.12-69d0718-normalized-SHA256SUMS.txt"
WHEEL_SHA256 = "147cab65e5970dc740ebc08d6ba5f4f0f4b655a69ea4e8db5a9b8bbbf6d9dfba"
SDIST_SHA256 = "ced24262abe4e31cd85d3c7adc0e0441f3e030513fceb0b55e82a8c97642ca6f"
CHECKSUM_SHA256 = "ad01264dc7104a16df0db1c80de68b86c1bfa4fbf3c8d0b375c38200272639bc"
WHEEL_BYTES = 1_709_907
SDIST_BYTES = 1_318_330
MAX_ASSET_BYTES = max(WHEEL_BYTES, SDIST_BYTES)
MAX_TOTAL_BYTES = WHEEL_BYTES + SDIST_BYTES + 190


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _download_https(url: str, expected_size: int) -> bytes:
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Asset URL is malformed.") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise ValueError("Asset URL must be a valid HTTPS URL on port 443 without embedded credentials.")

    request = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=45) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("Asset server must return the exact requested resource without redirects.")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("Asset server returned an encoded response.")
            declared_size = response.headers.get("Content-Length")
            if declared_size is not None:
                try:
                    declared_bytes = int(declared_size)
                except ValueError as exc:
                    raise ValueError("Asset server returned a malformed content length.") from exc
                if declared_bytes != expected_size:
                    raise ValueError("Asset server content length differs from the frozen asset size.")
            payload = response.read(expected_size + 1)
            if len(payload) != expected_size or response.read(1):
                raise ValueError("Downloaded asset size differs from the frozen asset size.")
            return payload
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError("Could not retrieve the selected asset over HTTPS.") from exc


def checksum_manifest(wheel_sha: str, sdist_sha: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", wheel_sha) or not re.fullmatch(r"[0-9a-f]{64}", sdist_sha):
        raise ValueError("Package hashes must be lowercase SHA-256 values.")
    return (
        f"{wheel_sha}  {WHEEL_NAME}\n"
        f"{sdist_sha}  {SDIST_NAME}\n"
    ).encode("ascii")


def _verify_payload(payload: bytes, expected_size: int, expected_sha256: str, label: str) -> None:
    if not isinstance(payload, bytes) or len(payload) != expected_size:
        raise ValueError(f"{label} byte count does not match the selected package record.")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"{label} SHA-256 does not match the selected package record.")


def _write_selected_assets(
    output_directory: Path,
    wheel: bytes,
    sdist: bytes,
    *,
    wheel_size: int = WHEEL_BYTES,
    sdist_size: int = SDIST_BYTES,
    wheel_sha256: str = WHEEL_SHA256,
    sdist_sha256: str = SDIST_SHA256,
    checksum_sha256: str = CHECKSUM_SHA256,
) -> dict[str, object]:
    """Verify frozen bytes, then create a fresh directory containing exactly 3 files."""
    output_directory = output_directory.resolve()
    if output_directory.exists():
        raise ValueError("The selected asset output directory must be new and empty.")

    _verify_payload(wheel, wheel_size, wheel_sha256, "Wheel")
    _verify_payload(sdist, sdist_size, sdist_sha256, "Sdist")
    checksum = checksum_manifest(wheel_sha256, sdist_sha256)
    if hashlib.sha256(checksum).hexdigest() != checksum_sha256:
        raise ValueError("Generated checksum manifest differs from its frozen SHA-256.")

    output_directory.mkdir(parents=True, exist_ok=False)
    files = {
        WHEEL_NAME: wheel,
        SDIST_NAME: sdist,
        CHECKSUM_NAME: checksum,
    }
    for name, payload in files.items():
        path = output_directory / name
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    return {
        "status": "PASS_EXACT_SELECTED_ASSETS_STAGED",
        "source_sha": "69d0718c805ea410ce5148ca0d1d39eae12736a1",
        "files": {
            name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            for name, payload in files.items()
        },
        "total_bytes": sum(map(len, files.values())),
        "fem_or_scientific_execution": False,
    }


def stage_assets(
    wheel_url: str,
    sdist_url: str,
    output_directory: Path,
    *,
    downloader: Callable[[str, int], bytes] = _download_https,
) -> dict[str, object]:
    wheel = downloader(wheel_url, WHEEL_BYTES)
    sdist = downloader(sdist_url, SDIST_BYTES)
    return _write_selected_assets(output_directory, wheel, sdist)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-workflow-sha", required=True)
    parser.add_argument("--confirm-stage-exact-assets", action="store_true")
    args = parser.parse_args()
    if not args.confirm_stage_exact_assets:
        parser.error("Pass --confirm-stage-exact-assets only from the approved manual staging workflow.")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_workflow_sha):
        parser.error("Supply the exact 40-character workflow commit SHA.")
    if os.environ.get("GITHUB_SHA") != args.expected_workflow_sha:
        parser.exit(2, "FAIL_CLOSED: workflow commit differs from its approved identity.\n")
    wheel_url = os.environ.get("QF0212_PYPI_WHEEL_URL", "")
    sdist_url = os.environ.get("QF0212_PYPI_SDIST_URL", "")
    if not wheel_url or not sdist_url:
        parser.exit(2, "FAIL_CLOSED: approved staging URL secrets are not configured.\n")
    try:
        import json

        result = stage_assets(wheel_url, sdist_url, args.output)
    except (OSError, ValueError):
        # Never echo URL-bearing exceptions, response headers, or server data.
        parser.exit(1, "FAIL_CLOSED: selected asset retrieval or verification failed.\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
