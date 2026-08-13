"""Typed model entities for distributed mechanical loads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class GravityLoad:
    """Acceleration field applied through material density."""

    acceleration: Vector3
    elements: tuple[int, ...] | None = None
    type: str = "gravity"


@dataclass(frozen=True)
class BodyLoad:
    """Constant force per unit volume in global or element-local axes."""

    value: Vector3
    elements: tuple[int, ...] | None = None
    coordinate_system: str = "global"
    type: str = "body_force"


@dataclass(frozen=True)
class SurfaceLoad:
    """Pressure or traction integrated on one element face or shell surface."""

    element: int
    kind: str
    value: float | Vector3
    face: int | None = None
    coordinate_system: str = "global"
    follower: bool = False

    @property
    def type(self) -> str:
        return self.kind


@dataclass(frozen=True)
class EdgeLoad:
    """Constant line traction on one MITC3 or MITC4 edge."""

    element: int
    edge: int
    value: Vector3
    coordinate_system: str = "global"
    type: str = "edge_traction"


@dataclass(frozen=True)
class LineLoad:
    """Constant force per unit length on one BEAM2 element."""

    element: int
    value: Vector3
    coordinate_system: str = "global"
    type: str = "line_load"


DistributedLoad: TypeAlias = GravityLoad | BodyLoad | SurfaceLoad | EdgeLoad | LineLoad


def parse_distributed_loads(values: list[dict[str, Any]] | None) -> list[DistributedLoad]:
    """Build typed loads after JSON or API shape validation."""
    parsed: list[DistributedLoad] = []
    for index, item in enumerate(values or []):
        try:
            if not isinstance(item, dict):
                raise TypeError("definition must be an object")
            load_type = str(item["type"]).lower()
            if load_type == "gravity":
                parsed.append(GravityLoad(_vector(item["acceleration"]), _targets(item.get("elements"))))
            elif load_type == "body_force":
                parsed.append(
                    BodyLoad(
                        _vector(item["value"]),
                        _targets(item.get("elements")),
                        str(item.get("coordinate_system", "global")).lower(),
                    )
                )
            elif load_type in {"pressure", "surface_traction"}:
                value: float | Vector3
                value = float(item["value"]) if load_type == "pressure" else _vector(item["value"])
                parsed.append(
                    SurfaceLoad(
                        element=int(item["element"]),
                        kind=load_type,
                        value=value,
                        face=int(item["face"]) if item.get("face") is not None else None,
                        coordinate_system=str(item.get("coordinate_system", "global")).lower(),
                        follower=bool(item.get("follower", False)),
                    )
                )
            elif load_type == "edge_traction":
                parsed.append(
                    EdgeLoad(
                        element=int(item["element"]),
                        edge=int(item["edge"]),
                        value=_vector(item["value"]),
                        coordinate_system=str(item.get("coordinate_system", "global")).lower(),
                    )
                )
            elif load_type == "line_load":
                parsed.append(
                    LineLoad(
                        element=int(item["element"]),
                        value=_vector(item["value"]),
                        coordinate_system=str(item.get("coordinate_system", "global")).lower(),
                    )
                )
            else:
                raise ValueError(f"unsupported type {load_type!r}")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid distributed load {index}: {exc}.") from exc
    return parsed


def _vector(value: object) -> Vector3:
    return tuple(float(component) for component in value)  # type: ignore[return-value]


def _targets(value: object | None) -> tuple[int, ...] | None:
    if value is None or value == "all":
        return None
    return tuple(int(index) for index in value)  # type: ignore[arg-type]
