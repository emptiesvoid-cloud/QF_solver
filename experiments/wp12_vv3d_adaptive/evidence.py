"""Create-only archival primitive for future VV3D observables; no solver execution."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def write_observables(root: Path, case_id: str, attempt_id: str, payload: dict[str, Any]) -> dict[str, str]:
    """Write synthetic or authorized-run data once; this function grants no execution permission.

    Missing observables can be represented as {'status':'NOT_EXPOSED'} and must not
    be silently coerced to zero. The caller must obtain the output root from its
    official controller, preserve failure data, and write before assertions.
    """
    if not SAFE_ID.fullmatch(case_id) or not SAFE_ID.fullmatch(attempt_id):
        raise ValueError("unsafe case or attempt ID")
    if not isinstance(payload,dict) or payload.get("schema") != "qf-wp12-vv3d-observables-v1":
        raise ValueError("unsupported observables schema")
    if payload.get("case_id") != case_id or payload.get("attempt_id") != attempt_id:
        raise ValueError("observables identity mismatch")
    for field in ("mesh_sha256","scientific_fingerprint","controller_fingerprint","manifest_sha256"):
        if not isinstance(payload.get(field),str) or not SHA256.fullmatch(payload[field]):
            raise ValueError(f"invalid {field}")
    if not isinstance(payload.get("observables"),dict) or not isinstance(payload.get("criteria"),dict):
        raise ValueError("observables and criteria must be explicit mappings")
    # Serialize before creating output paths: NaN, infinity and unsupported types fail closed.
    encoded=(json.dumps(payload,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf-8")
    base=root.resolve()
    base.mkdir(parents=True,exist_ok=True)
    case_dir=base/case_id
    case_dir.mkdir(exist_ok=True)
    if case_dir.resolve().parent != base:
        raise ValueError("case directory escapes the evidence root")
    attempt_dir=case_dir/attempt_id
    attempt_dir.mkdir(exist_ok=False)
    descriptor,tmp_name=tempfile.mkstemp(prefix=".evidence-",dir=attempt_dir)
    tmp=Path(tmp_name)
    target=attempt_dir/"observables.json"
    try:
        with os.fdopen(descriptor,"wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp,target)
    finally:
        tmp.unlink(missing_ok=True)
    return {"path":str(target.resolve()),"sha256":hashlib.sha256(encoded).hexdigest()}
