"""Family-aware HDF5 storage for bounded mixed-solid results.

The format stores one homogeneous element block per family.  It is deliberately
independent from the solver formulation: the writer consumes the existing
``GenericDistributedModel`` and ``FamilyAwareResults`` envelopes and never
reassembles a global finite-element model.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from solveur.core.errors import InputValidationError
from solveur.large.generic_distributed import (
    SUPPORTED_DISTRIBUTED_FAMILIES,
    FamilyAwareResults,
    GenericDistributedModel,
)


MIXED_RESULTS_FORMAT = "qf_solver.mixed_results.hdf5"
MIXED_RESULTS_SCHEMA_VERSION = "1.0"
_FAMILY_WIDTHS = {"TET4": 4, "WEDGE6": 6, "HEX8": 8}
_REQUIRED_ROOT_ATTRIBUTES = (
    "format",
    "schema_version",
    "qf_solver_version_or_dev_state",
    "source_sha",
    "metadata_json",
)


def write_mixed_results_hdf5(
    path: str | Path,
    model: GenericDistributedModel,
    results: FamilyAwareResults,
    *,
    reactions: np.ndarray | None = None,
    source_sha: str,
    metadata: Mapping[str, Any] | None = None,
    qf_solver_version_or_dev_state: str = "0.2.8-development",
) -> Path:
    """Write one family-aware result file, rejecting an existing target.

    The target is opened with HDF5 exclusive-create mode.  Element blocks are
    written with their native connectivity widths, so mixed families never
    share a padded connectivity array.
    """

    target = Path(path)
    if target.exists():
        raise InputValidationError(f"Refusing to overwrite existing mixed result file: {target}")
    if not isinstance(model, GenericDistributedModel):
        raise InputValidationError("Mixed result storage requires a GenericDistributedModel.")
    if not isinstance(results, FamilyAwareResults):
        raise InputValidationError("Mixed result storage requires FamilyAwareResults.")
    if not isinstance(source_sha, str) or not source_sha.strip():
        raise InputValidationError("Mixed result storage requires a non-empty source_sha.")

    displacement = _finite_array(results.nodal_displacement, (model.node_count, 3), "nodal displacement")
    reaction = None
    if reactions is not None:
        reaction = _finite_array(reactions, (model.node_count, 3), "nodal reaction")

    elements = tuple(model.iter_elements())
    expected_ids = {element.element_id for element in elements}
    result_by_id = {int(item.element_id): item for item in results.element_results}
    if set(result_by_id) != expected_ids:
        missing = sorted(expected_ids - set(result_by_id))
        extra = sorted(set(result_by_id) - expected_ids)
        raise InputValidationError(f"Element result ids do not match the model; missing={missing}, extra={extra}.")
    for element in elements:
        result = result_by_id[element.element_id]
        if str(result.family).upper() != element.family:
            raise InputValidationError(
                f"Element result family mismatch for {element.element_id}: {result.family!r} != {element.family!r}."
            )

    metadata_payload = {
        "model_metadata": _json_safe(dict(model.metadata)),
        "node_count": model.node_count,
        "element_count": model.element_count,
        "family_counts": model.element_counts(),
        "units_metadata": _json_safe(dict(model.metadata).get("units", {})),
    }
    if metadata is not None:
        metadata_payload["result_metadata"] = _json_safe(dict(metadata))
    metadata_json = _canonical_json(metadata_payload)

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with h5py.File(target, "x") as handle:
            handle.attrs["format"] = MIXED_RESULTS_FORMAT
            handle.attrs["schema_version"] = MIXED_RESULTS_SCHEMA_VERSION
            handle.attrs["qf_solver_version_or_dev_state"] = str(qf_solver_version_or_dev_state)
            handle.attrs["source_sha"] = source_sha
            handle.attrs["metadata_json"] = metadata_json

            mesh = handle.create_group("mesh")
            nodes = mesh.create_group("nodes")
            _write_dataset(nodes, "id", np.arange(model.node_count, dtype=np.int64))
            _write_dataset(nodes, "coordinates", np.asarray(model.nodes, dtype=np.float64))

            result_group = handle.create_group("results")
            nodal = result_group.create_group("nodal")
            _write_dataset(nodal, "displacement", displacement)
            if reaction is not None:
                _write_dataset(nodal, "reaction", reaction)

            blocks_group = mesh.create_group("element_blocks")
            block_by_family = {block.family: block for block in model.blocks}
            if not block_by_family:
                raise InputValidationError("Mixed result storage requires at least one element block.")
            for family in SUPPORTED_DISTRIBUTED_FAMILIES:
                block = block_by_family.get(family)
                if block is None:
                    continue
                group = blocks_group.create_group(family)
                _write_dataset(group, "connectivity", block.connectivity)
                _write_dataset(group, "element_ids", block.element_ids)
                _write_dataset(group, "material_ids", block.material_ids)
                _write_dataset(group, "region_ids", block.region_ids)
                _write_string_dataset(group, "material_names", block.material_names)
                fields_group = group.create_group("fields")
                block_elements = [element for element in elements if element.family == family]
                block_results = [result_by_id[element.element_id] for element in block_elements]
                _write_fields(fields_group, block_results, block.element_count)
    except Exception:
        if target.exists():
            target.unlink()
        raise
    return target


def read_mixed_results_hdf5(
    path: str | Path,
    *,
    families: Sequence[str] | None = None,
    fields: Sequence[str] | None = None,
    region_id: int | None = None,
) -> dict[str, Any]:
    """Read and validate a mixed result file, optionally selecting data.

    Shape and identity checks are performed for every block.  Array values for
    non-selected fields or families are not returned, which keeps the public
    selective-read path bounded by the requested result subset.
    """

    source = Path(path)
    if not source.is_file():
        raise InputValidationError(f"Mixed result file does not exist: {source}")
    selected_families = _normalize_families(families)
    selected_fields = None if fields is None else {str(field) for field in fields}
    if region_id is not None and (isinstance(region_id, bool) or not isinstance(region_id, (int, np.integer))):
        raise InputValidationError("region_id must be an integer when supplied.")

    with h5py.File(source, "r") as handle:
        for name in _REQUIRED_ROOT_ATTRIBUTES:
            if name not in handle.attrs:
                raise InputValidationError(f"Mixed result file is missing root attribute {name!r}.")
        if _text(handle.attrs["format"]) != MIXED_RESULTS_FORMAT:
            raise InputValidationError("Unsupported mixed result format identifier.")
        if _text(handle.attrs["schema_version"]) != MIXED_RESULTS_SCHEMA_VERSION:
            raise InputValidationError("Unsupported mixed result schema version.")
        try:
            metadata = json.loads(_text(handle.attrs["metadata_json"]))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InputValidationError("Mixed result metadata_json is not valid JSON.") from exc
        if not isinstance(metadata, dict):
            raise InputValidationError("Mixed result metadata_json must contain an object.")

        nodes_group = _require_group(handle, "mesh/nodes")
        node_ids = _read_required_array(nodes_group, "id", ndim=1, dtype=np.int64)
        coordinates = _read_required_array(nodes_group, "coordinates", ndim=2, dtype=np.float64)
        if coordinates.shape != (node_ids.size, 3):
            raise InputValidationError("Node id and coordinate array lengths are inconsistent.")
        if np.unique(node_ids).size != node_ids.size or not np.all(np.isfinite(coordinates)):
            raise InputValidationError("Node ids must be unique and coordinates finite.")

        nodal_group = _require_group(handle, "results/nodal")
        displacement = _read_required_array(nodal_group, "displacement", ndim=2, dtype=np.float64)
        if displacement.shape != coordinates.shape or not np.all(np.isfinite(displacement)):
            raise InputValidationError("Nodal displacement shape or values are invalid.")
        reaction = None
        if "reaction" in nodal_group:
            reaction = _read_required_array(nodal_group, "reaction", ndim=2, dtype=np.float64)
            if reaction.shape != coordinates.shape or not np.all(np.isfinite(reaction)):
                raise InputValidationError("Nodal reaction shape or values are invalid.")

        blocks_group = _require_group(handle, "mesh/element_blocks")
        names = sorted(str(name) for name in blocks_group.keys())
        if not names:
            raise InputValidationError("Mixed result file contains no element blocks.")
        if any(name not in _FAMILY_WIDTHS for name in names):
            raise InputValidationError("Mixed result file contains an unsupported element family block.")
        unknown_selected = set(selected_families or ()) - set(names)
        if unknown_selected:
            raise InputValidationError(f"Requested element families are absent: {sorted(unknown_selected)}")

        all_available_fields: set[str] = set()
        for family in names:
            fields_group = _require_group(_require_group(blocks_group, family), "fields")
            all_available_fields.update(str(name) for name in fields_group.keys())
        if selected_fields is not None:
            missing = sorted(selected_fields - all_available_fields)
            if missing:
                raise InputValidationError(f"Requested element fields are absent from the result: {missing}")

        selected_blocks: dict[str, dict[str, Any]] = {}
        all_element_ids: list[int] = []
        for family in names:
            group = _require_group(blocks_group, family)
            count = _validate_block_shapes(group, family, node_ids.size)
            element_ids = _read_required_array(group, "element_ids", ndim=1, dtype=np.int64)
            all_element_ids.extend(int(value) for value in element_ids)
            if selected_families is not None and family not in selected_families:
                continue
            connectivity = _read_required_array(group, "connectivity", ndim=2, dtype=np.int64)
            material_ids = _read_required_array(group, "material_ids", ndim=1, dtype=np.int64)
            regions = _read_required_array(group, "region_ids", ndim=1, dtype=np.int64)
            material_names = _read_string_array(group, "material_names")
            if np.any(material_ids < 0) or np.any(material_ids >= len(material_names)):
                raise InputValidationError(f"{family} material ids reference an unknown material.")
            mask = np.ones(count, dtype=bool) if region_id is None else regions == int(region_id)
            fields_group = _require_group(group, "fields")
            block_fields: dict[str, np.ndarray] = {}
            available_fields = set(str(name) for name in fields_group.keys())
            requested_fields = available_fields if selected_fields is None else available_fields & selected_fields
            for field_name in sorted(requested_fields):
                field_values = _read_field(fields_group, field_name, count)
                block_fields[field_name] = field_values[mask]
            selected_blocks[family] = {
                "connectivity": connectivity[mask],
                "element_ids": element_ids[mask],
                "material_ids": material_ids[mask],
                "region_ids": regions[mask],
                "material_names": tuple(material_names),
                "fields": block_fields,
            }
        if len(all_element_ids) != len(set(all_element_ids)):
            raise InputValidationError("Element ids must be unique across all family blocks.")

        return {
            "format": MIXED_RESULTS_FORMAT,
            "schema_version": MIXED_RESULTS_SCHEMA_VERSION,
            "qf_solver_version_or_dev_state": _text(handle.attrs["qf_solver_version_or_dev_state"]),
            "source_sha": _text(handle.attrs["source_sha"]),
            "metadata": metadata,
            "nodes": {"id": node_ids, "coordinates": coordinates},
            "results": {"displacement": displacement, **({"reaction": reaction} if reaction is not None else {})},
            "element_blocks": selected_blocks,
        }


def load_mixed_results_hdf5(
    path: str | Path,
    *,
    families: Sequence[str] | None = None,
    fields: Sequence[str] | None = None,
    region_id: int | None = None,
) -> dict[str, Any]:
    """Compatibility alias for the public HDF5 result reader."""
    return read_mixed_results_hdf5(path, families=families, fields=fields, region_id=region_id)


def mixed_results_semantic_digest(path: str | Path) -> str:
    """Return a deterministic digest of logical result content, not HDF5 bytes."""

    payload = read_mixed_results_hdf5(path)
    digest = hashlib.sha256()
    _update_digest(digest, "root", payload)
    return digest.hexdigest()


def _write_fields(group: h5py.Group, records: list[Any], count: int) -> None:
    names = sorted({str(name) for record in records for name in record.fields})
    for name in names:
        if any(name not in record.fields for record in records):
            raise InputValidationError(f"Element field {name!r} is missing from at least one family element.")
        values = [np.asarray(record.fields[name]) for record in records]
        try:
            array = np.stack(values, axis=0).astype(np.float64, copy=False)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Element field {name!r} must be a numeric fixed-shape field.") from exc
        if array.shape[0] != count or not np.all(np.isfinite(array)):
            raise InputValidationError(f"Element field {name!r} has an invalid shape or non-finite value.")
        _write_dataset(group, name, array)


def _validate_block_shapes(group: h5py.Group, family: str, node_count: int) -> int:
    required = ("connectivity", "element_ids", "material_ids", "region_ids", "material_names", "fields")
    for name in required:
        if name not in group:
            raise InputValidationError(f"{family} block is missing required member {name!r}.")
    connectivity = group["connectivity"]
    element_ids = group["element_ids"]
    material_ids = group["material_ids"]
    region_ids = group["region_ids"]
    expected_width = _FAMILY_WIDTHS[family]
    if connectivity.ndim != 2 or connectivity.shape[1] != expected_width:
        raise InputValidationError(f"{family} connectivity has the wrong native width.")
    count = int(connectivity.shape[0])
    if element_ids.shape != (count,) or material_ids.shape != (count,) or region_ids.shape != (count,):
        raise InputValidationError(f"{family} block arrays have inconsistent lengths.")
    if np.any(np.asarray(connectivity) < 0) or np.any(np.asarray(connectivity) >= node_count):
        raise InputValidationError(f"{family} connectivity references a missing node.")
    if np.any(np.apply_along_axis(lambda row: np.unique(row).size != expected_width, 1, np.asarray(connectivity))):
        raise InputValidationError(f"{family} connectivity contains duplicate nodes.")
    if np.unique(np.asarray(element_ids)).size != count:
        raise InputValidationError(f"{family} element ids are not unique.")
    return count


def _write_dataset(group: h5py.Group, name: str, values: np.ndarray) -> None:
    array = np.asarray(values)
    kwargs: dict[str, Any] = {}
    if array.ndim > 0 and array.size:
        kwargs.update({"chunks": True, "compression": "gzip", "compression_opts": 4, "shuffle": True})
    group.create_dataset(name, data=array, **kwargs)


def _write_string_dataset(group: h5py.Group, name: str, values: Sequence[str]) -> None:
    dtype = h5py.string_dtype(encoding="utf-8")
    group.create_dataset(name, data=np.asarray([str(value) for value in values], dtype=object), dtype=dtype)


def _read_required_array(group: h5py.Group, name: str, *, ndim: int, dtype: Any) -> np.ndarray:
    if name not in group:
        raise InputValidationError(f"Missing required dataset {group.name}/{name}.")
    array = np.asarray(group[name], dtype=dtype)
    if array.ndim != ndim:
        raise InputValidationError(f"Dataset {group.name}/{name} has invalid rank.")
    return array


def _read_field(group: h5py.Group, name: str, count: int) -> np.ndarray:
    array = np.asarray(group[name], dtype=np.float64)
    if array.ndim < 1 or array.shape[0] != count or not np.all(np.isfinite(array)):
        raise InputValidationError(f"Element field {group.name}/{name} has an invalid shape or value.")
    return array


def _read_string_array(group: h5py.Group, name: str) -> list[str]:
    if name not in group:
        raise InputValidationError(f"Missing required dataset {group.name}/{name}.")
    return [_text(value) for value in np.asarray(group[name]).tolist()]


def _require_group(parent: h5py.Group, name: str) -> h5py.Group:
    if name not in parent or not isinstance(parent[name], h5py.Group):
        raise InputValidationError(f"Missing required HDF5 group {parent.name}/{name}.")
    return parent[name]


def _normalize_families(values: Sequence[str] | None) -> set[str] | None:
    if values is None:
        return None
    normalized = {str(value).upper() for value in values}
    if not normalized or not normalized.issubset(_FAMILY_WIDTHS):
        raise InputValidationError(f"Unsupported family selector {sorted(normalized)}.")
    return normalized


def _finite_array(values: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise InputValidationError(f"{label} must have finite shape {shape}.")
    return array


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise InputValidationError(f"Metadata contains unsupported value type {type(value).__name__}.")


def _text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _update_digest(digest: hashlib._Hash, path: str, value: Any) -> None:
    digest.update(path.encode("utf-8"))
    digest.update(b"\0")
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(b"array\0")
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(array.shape).encode("ascii"))
        digest.update(array.tobytes(order="C"))
        return
    if isinstance(value, Mapping):
        digest.update(b"mapping\0")
        for key in sorted(value):
            _update_digest(digest, f"{path}/{key}", value[key])
        return
    if isinstance(value, (list, tuple)):
        digest.update(b"sequence\0")
        for index, item in enumerate(value):
            _update_digest(digest, f"{path}/{index}", item)
        return
    digest.update(_canonical_json(value).encode("utf-8"))
