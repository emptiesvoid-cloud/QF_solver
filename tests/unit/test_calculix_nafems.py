import numpy as np
import pytest

from solveur.verification.calculix_nafems import (
    CalculixNafems13HParser,
    extrapolate_shell_surface_stress,
)


def test_trilinear_gauss_extrapolation_recovers_shell_face_value() -> None:
    gauss = 1.0 / np.sqrt(3.0)
    coordinates = (
        (-gauss, -gauss, -gauss),
        (gauss, -gauss, -gauss),
        (gauss, gauss, -gauss),
        (-gauss, gauss, -gauss),
        (-gauss, -gauss, gauss),
        (gauss, -gauss, gauss),
        (gauss, gauss, gauss),
        (-gauss, gauss, gauss),
    )

    def field(xi: float, eta: float, zeta: float) -> complex:
        return 2.0 + 3.0 * xi - 4.0 * eta + (5.0 + 2.0j) * zeta + xi * eta * zeta

    values = {index: field(*point) for index, point in enumerate(coordinates, start=1)}
    recovered = extrapolate_shell_surface_stress(values, xi=1.0, eta=-1.0, face=1.0)
    assert recovered == pytest.approx(field(1.0, -1.0, 1.0))


def test_gauss_extrapolation_rejects_incomplete_input() -> None:
    with pytest.raises(ValueError, match="Eight"):
        extrapolate_shell_surface_stress({1: 1.0}, xi=1.0, eta=1.0, face=1.0)


def test_parser_pairs_real_and_imaginary_blocks(tmp_path) -> None:
    gauss = 1.0 / np.sqrt(3.0)
    coordinates = (
        (-gauss, -gauss, -gauss),
        (gauss, -gauss, -gauss),
        (gauss, gauss, -gauss),
        (-gauss, gauss, -gauss),
        (-gauss, -gauss, gauss),
        (gauss, -gauss, gauss),
        (gauss, gauss, gauss),
        (-gauss, gauss, gauss),
    )
    sections = []
    for displacement, multiplier in ((2.0, 10.0), (3.0, 4.0)):
        stress_rows = []
        for element in range(1, 5):
            for point, (_, _, zeta) in enumerate(coordinates, start=1):
                stress_rows.append(
                    f"{element} {point} {multiplier * zeta} 0 0 0 0 0 shell"
                )
        sections.extend(
            [
                "displacements (vx,vy,vz) for set NMID and time 1.0",
                f"45 0 0 {displacement}",
                "stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) "
                "for set EMID and time 1.0",
                *stress_rows,
            ]
        )
    dat = tmp_path / "sample.dat"
    dat.write_text("\n".join(sections), encoding="utf-8")
    points = CalculixNafems13HParser().parse(
        dat,
        center_node=45,
        center_element_corners={
            1: (1.0, 1.0),
            2: (-1.0, 1.0),
            3: (1.0, -1.0),
            4: (-1.0, -1.0),
        },
    )
    assert len(points) == 1
    assert points[0].center_uz == 2.0 + 3.0j
    assert points[0].center_top_s11_pa == pytest.approx(10.0 + 4.0j)
