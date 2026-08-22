"""Parse and compare PETSc ``-log_view`` performance profiles."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Sequence

from solveur.io.manifest import sha256, write_json_file
from solveur.large.evidence import write_large_manifest

_LOCAL_RE = re.compile(
    r"^(LocalTimes|LocalMessages|LocalMessageLens|LocalReductions|LocalFlop|LocalMemory)"
    r"\[(\d+)\] = (.+)$"
)
_EVENT_RE = re.compile(
    r'^Stages\["(?P<stage>[^"]+)"\]\["(?P<event>[^"]+)"\]\[(?P<rank>\d+)\] = (?P<data>\{.*\})$'
)
_FOCUS_EVENTS = (
    "PCSetUp",
    "PCApply",
    "KSPSolve",
    "MatMult",
    "VecScatterBegin",
    "VecScatterEnd",
    "MatAssemblyBegin",
    "MatAssemblyEnd",
    "PCSetUp_GAMG+",
    " GAMG Coarsen",
    " PCGAMGProl",
    " PCGAMGCreateL",
)


def parse_petsc_log_view(path: str | Path) -> dict[str, Any]:
    """Parse PETSc ``ascii_info_detail`` output without executing its content."""
    source = Path(path)
    local: dict[str, dict[int, float]] = {}
    events: dict[str, dict[int, dict[str, float]]] = {}
    mpi_size: int | None = None
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("size ="):
            mpi_size = int(line.split("=", 1)[1].strip())
            continue
        local_match = _LOCAL_RE.match(line)
        if local_match:
            name, rank_text, value_text = local_match.groups()
            local.setdefault(name, {})[int(rank_text)] = float(value_text)
            continue
        event_match = _EVENT_RE.match(line)
        if event_match:
            payload = ast.literal_eval(event_match.group("data"))
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid PETSc event payload in {source}.")
            key = f"{event_match.group('stage')}::{event_match.group('event')}"
            events.setdefault(key, {})[int(event_match.group("rank"))] = {
                str(name): float(value) for name, value in payload.items()
            }
    if mpi_size is None or mpi_size <= 0:
        raise ValueError(f"PETSc profile has no valid MPI size: {source}")
    rank_times = local.get("LocalTimes", {})
    if len(rank_times) != mpi_size:
        raise ValueError(f"PETSc profile contains {len(rank_times)} rank times, expected {mpi_size}: {source}")
    event_summaries = [_aggregate_event(name, values, mpi_size) for name, values in events.items()]
    event_summaries.sort(key=lambda item: float(item["time_max_seconds"]), reverse=True)
    total_time_max = max(rank_times.values())
    focus = {
        event: _event_by_name(event_summaries, event)
        for event in _FOCUS_EVENTS
        if _event_by_name(event_summaries, event) is not None
    }
    return {
        "profile_schema_version": 1,
        "source": str(source),
        "source_sha256": sha256(source),
        "mpi_size": mpi_size,
        "rank_time_seconds": _rank_statistics(rank_times),
        "communication": {
            "messages_sum": _sum_local(local, "LocalMessages"),
            "message_length_units_sum": _sum_local(local, "LocalMessageLens"),
            "reductions_max": _max_local(local, "LocalReductions"),
        },
        "flop_sum": _sum_local(local, "LocalFlop"),
        "memory_units_max": _max_local(local, "LocalMemory"),
        "focus_events": focus,
        "top_events": event_summaries[:20],
        "event_count": len(event_summaries),
        "total_time_max_seconds": total_time_max,
    }


def write_petsc_profile_report(
    profile_paths: Sequence[str | Path],
    output_dir: str | Path,
    *,
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Write a machine-readable and reader-oriented comparison of PETSc profiles."""
    paths = tuple(Path(path) for path in profile_paths)
    if not paths:
        raise ValueError("At least one PETSc profile is required.")
    names = tuple(labels) if labels is not None else tuple(path.stem for path in paths)
    if len(names) != len(paths) or any(not str(name).strip() for name in names):
        raise ValueError("Profile labels must be non-empty and match the number of inputs.")
    if len(set(names)) != len(names):
        raise ValueError("Profile labels must be unique.")
    profiles = []
    for label, path in zip(names, paths, strict=True):
        profile = parse_petsc_log_view(path)
        profile["label"] = str(label)
        profiles.append(profile)
    summary = {
        "profile_comparison_schema_version": 1,
        "status": "PASS",
        "kind": "petsc_log_view_comparison",
        "profiles": profiles,
        "interpretation": _interpret_profiles(profiles),
    }
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    write_json_file(root / "petsc_profile_comparison.json", summary)
    (root / "petsc_profile_comparison.md").write_text(_profile_markdown(summary), encoding="utf-8")
    manifest = write_large_manifest(root, {"kind": summary["kind"], "status": summary["status"]})
    return {**summary, "evidence_manifest": str(manifest)}


def _aggregate_event(name: str, values: dict[int, dict[str, float]], mpi_size: int) -> dict[str, Any]:
    times = [values.get(rank, {}).get("time", 0.0) for rank in range(mpi_size)]
    stage, event = name.split("::", 1)
    time_max = max(times, default=0.0)
    time_mean = sum(times) / mpi_size
    active = [value for value in times if value > 0.0]
    return {
        "stage": stage,
        "event": event,
        "time_max_seconds": time_max,
        "time_mean_seconds": time_mean,
        "time_imbalance": time_max / time_mean if time_mean > 0.0 else 0.0,
        "active_ranks": len(active),
        "count_max": max((values.get(rank, {}).get("count", 0.0) for rank in range(mpi_size)), default=0.0),
        "messages_sum": sum(values.get(rank, {}).get("numMessages", 0.0) for rank in range(mpi_size)),
        "message_length_units_sum": sum(
            values.get(rank, {}).get("messageLength", 0.0) for rank in range(mpi_size)
        ),
        "reductions_max": max(
            (values.get(rank, {}).get("numReductions", 0.0) for rank in range(mpi_size)), default=0.0
        ),
        "flop_sum": sum(values.get(rank, {}).get("flop", 0.0) for rank in range(mpi_size)),
    }


def _event_by_name(events: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((event for event in events if event["event"] == name), None)


def _rank_statistics(values: dict[int, float]) -> dict[str, float]:
    ordered = list(values.values())
    minimum = min(ordered)
    maximum = max(ordered)
    mean = sum(ordered) / len(ordered)
    return {
        "min": minimum,
        "max": maximum,
        "mean": mean,
        "spread": maximum - minimum,
        "imbalance": maximum / mean if mean > 0.0 else 0.0,
    }


def _sum_local(local: dict[str, dict[int, float]], name: str) -> float:
    return float(sum(local.get(name, {}).values()))


def _max_local(local: dict[str, dict[int, float]], name: str) -> float:
    return float(max(local.get(name, {0: 0.0}).values()))


def _interpret_profiles(profiles: list[dict[str, Any]]) -> list[str]:
    messages = []
    for profile in profiles:
        focus = profile["focus_events"]
        total = float(profile["total_time_max_seconds"])
        ksp = focus.get("KSPSolve")
        setup = focus.get("PCSetUp")
        if ksp is not None and total > 0.0:
            messages.append(
                f"{profile['label']}: KSPSolve represente {float(ksp['time_max_seconds']) / total:.1%} "
                "du temps PETSc maximal mesure."
            )
        if setup is not None and total > 0.0:
            messages.append(
                f"{profile['label']}: PCSetUp represente {float(setup['time_max_seconds']) / total:.1%} "
                "du temps PETSc maximal mesure."
            )
    messages.append(
        "Les temps d'evenements PETSc peuvent se recouvrir; leurs fractions sont des diagnostics, pas une decomposition additive."
    )
    return messages


def _profile_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Profilage PETSc des grands modeles",
        "",
        f"Statut: **{summary['status']}**",
        "",
        "| Profil | Rangs | Temps max [s] | Desequilibre temps | Messages | Longueur PETSc | Reductions | KSPSolve [s] | PCSetUp [s] |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for profile in summary["profiles"]:
        focus = profile["focus_events"]
        lines.append(
            f"| {profile['label']} | {profile['mpi_size']} | {_display(profile['total_time_max_seconds'])} | "
            f"{_display(profile['rank_time_seconds']['imbalance'])} | "
            f"{_display(profile['communication']['messages_sum'])} | "
            f"{_display(profile['communication']['message_length_units_sum'])} | "
            f"{_display(profile['communication']['reductions_max'])} | "
            f"{_event_time(focus, 'KSPSolve')} | {_event_time(focus, 'PCSetUp')} |"
        )
    lines.extend(["", "## Interpretation", ""])
    lines.extend(f"- {message}" for message in summary["interpretation"])
    lines.extend(
        [
            "",
            "Les longueurs de messages sont conservees dans les unites natives du journal PETSc. "
            "Elles ne sont pas converties en octets sans information complementaire sur le type de donnees.",
        ]
    )
    return "\n".join(lines) + "\n"


def _event_time(focus: dict[str, Any], name: str) -> str:
    event = focus.get(name)
    return _display(event.get("time_max_seconds")) if event is not None else ""


def _display(value: object) -> str:
    return f"{value:.6g}" if isinstance(value, float) else str(value)
