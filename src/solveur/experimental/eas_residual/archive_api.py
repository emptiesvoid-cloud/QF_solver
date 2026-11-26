"""Hash-bound archive entry point for the optional EAS residual diagnostic.

The current static solver route passes its reduced system in memory. This
separate API is for a previously captured system: it verifies both archive
byte streams before decoding them and before invoking the historical guard or
the exact-residual child process.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import math
import re
import zipfile
import zlib
from pathlib import Path
from typing import Any

import numpy as np

from .bounded_exact_supervisor import supervise


_MATRIX_MEMBERS = {
    "reduced_data.npy",
    "reduced_indices.npy",
    "reduced_indptr.npy",
    "reduced_shape.npy",
    "rhs.npy",
}
_CANDIDATE_MEMBERS = {"candidate.npy"}
_DEFAULT_MAX_ARCHIVE_BYTES = 8 * 2**20


def _inconclusive(reason: str) -> dict[str, Any]:
    return {
        "historical_decision": "NOT_RUN",
        "supplemental": "INCONCLUSIVE",
        "reason": reason,
        "archive_validation": "REJECTED",
    }


def _read_bound_archive(path: str | Path, expected_sha256: str, max_archive_bytes: int) -> bytes:
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256) is None:
        raise ValueError("INVALID_EXPECTED_SHA256")
    if not isinstance(max_archive_bytes, int) or isinstance(max_archive_bytes, bool) or max_archive_bytes <= 0:
        raise ValueError("INVALID_ARCHIVE_LIMIT")
    with Path(path).open("rb") as stream:
        payload = stream.read(max_archive_bytes + 1)
    if len(payload) > max_archive_bytes:
        raise ValueError("ARCHIVE_SIZE_LIMIT")
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if not hmac.compare_digest(actual_sha256, expected_sha256.lower()):
        raise ValueError("ARCHIVE_SHA256_MISMATCH")
    return payload


def _load_npz(payload: bytes, expected_members: set[str], max_uncompressed_bytes: int) -> dict[str, np.ndarray]:
    arrays = {}
    with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)) or set(names) != expected_members:
            raise ValueError("ARCHIVE_MEMBERS_INVALID")
        if any(member.flag_bits & 0x1 for member in members):
            raise ValueError("ARCHIVE_ENCRYPTED")
        if sum(member.file_size for member in members) > max_uncompressed_bytes:
            raise ValueError("ARCHIVE_UNCOMPRESSED_SIZE_LIMIT")
        for member in members:
            with archive.open(member) as entry:
                buffer = io.BytesIO(entry.read(member.file_size + 1))
            version = np.lib.format.read_magic(buffer)
            if version == (1, 0):
                shape, _, dtype = np.lib.format.read_array_header_1_0(buffer)
            elif version == (2, 0):
                shape, _, dtype = np.lib.format.read_array_header_2_0(buffer)
            else:
                raise ValueError("ARCHIVE_NPY_VERSION_UNSUPPORTED")
            remaining = len(buffer.getbuffer()) - buffer.tell()
            if (len(shape) != 1 or shape[0] < 0 or dtype.kind not in "fiu"
                    or math.prod(shape) * dtype.itemsize != remaining):
                raise ValueError("ARCHIVE_NPY_LAYOUT_INVALID")
            buffer.seek(0)
            arrays[member.filename[:-4]] = np.load(buffer, allow_pickle=False)
    return arrays


def supervise_npz_archives(
    matrix_archive: str | Path,
    candidate_archive: str | Path,
    *,
    matrix_sha256: str,
    candidate_sha256: str,
    threshold: float = 1e-7,
    timeout: float = 10.0,
    rss_limit: int = 256 * 2**20,
    input_limit: int = 8 * 2**20,
    max_archive_bytes: int = _DEFAULT_MAX_ARCHIVE_BYTES,
) -> dict[str, Any]:
    """Verify a minimal hash-bound NPZ pair, then run the diagnostic.

    The matrix archive must contain exactly ``reduced_data``,
    ``reduced_indices``, ``reduced_indptr``, ``reduced_shape`` and ``rhs``.
    The candidate archive must contain exactly ``candidate``. Expected SHA-256
    digests must come from a separately trusted manifest. Any invalid or
    incomplete input returns NOT_RUN/INCONCLUSIVE before the historical guard
    runs. A supplemental PASS never changes the guard's decision.
    """
    if type(input_limit) is not int or input_limit <= 0:
        return _inconclusive("INVALID_INPUT_LIMIT")
    try:
        matrix_bytes = _read_bound_archive(matrix_archive, matrix_sha256, max_archive_bytes)
        candidate_bytes = _read_bound_archive(candidate_archive, candidate_sha256, max_archive_bytes)
        matrix_arrays = _load_npz(matrix_bytes, _MATRIX_MEMBERS, input_limit)
        candidate_arrays = _load_npz(candidate_bytes, _CANDIDATE_MEMBERS, input_limit)
        shape_array = matrix_arrays["reduced_shape"]
        if shape_array.shape != (2,) or shape_array.dtype.kind not in "iu":
            return _inconclusive("ARCHIVE_SHAPE_INVALID")
        shape = tuple(int(value) for value in shape_array)
        result = supervise(
            matrix_arrays["reduced_data"],
            matrix_arrays["reduced_indices"],
            matrix_arrays["reduced_indptr"],
            shape,
            matrix_arrays["rhs"],
            candidate_arrays["candidate"],
            threshold,
            timeout=timeout,
            rss_limit=rss_limit,
            input_limit=input_limit,
        )
        return {
            **result,
            "archive_validation": "PASS",
            "matrix_archive_sha256": hashlib.sha256(matrix_bytes).hexdigest(),
            "candidate_archive_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        }
    except FileNotFoundError:
        return _inconclusive("ARCHIVE_NOT_FOUND")
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, EOFError,
            RuntimeError, OverflowError, zlib.error) as exc:
        return _inconclusive(str(exc) if str(exc) else type(exc).__name__)
