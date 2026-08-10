from pathlib import Path

import pytest

from solveur.verification.calculix_j2 import (
    evaluate_calculix_j2_correlation,
    parse_calculix_j2_dat,
    write_calculix_j2_figure,
)


def test_calculix_j2_parser_reads_final_homogeneous_state():
    state = parse_calculix_j2_dat(_sample_dat())

    assert state.time == pytest.approx(1.0)
    assert state.axial_stress_mpa == pytest.approx(300.0)
    assert state.lateral_stress_mpa < 1.0e-12
    assert state.equivalent_plastic_strain == pytest.approx(0.001)
    assert state.axial_strain == pytest.approx(0.002428571)
    assert state.internal_energy_density_mpa == pytest.approx(0.4886411)


def test_calculix_j2_correlation_passes_theory_and_qf_solver():
    summary = evaluate_calculix_j2_correlation(parse_calculix_j2_dat(_sample_dat()))

    assert summary["status"] == "PASS_INTERNAL"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    energy = next(check for check in summary["checks"] if check["id"] == "calculix_vs_theory_internal_energy_density")
    assert 1.0e-3 < energy["value"] < energy["limit"]


def test_calculix_j2_parser_rejects_incomplete_output():
    with pytest.raises(ValueError, match="complete J2"):
        parse_calculix_j2_dat("Job finished without requested fields")


def test_calculix_j2_figure_is_nonempty(tmp_path):
    summary = evaluate_calculix_j2_correlation(parse_calculix_j2_dat(_sample_dat()))
    path = write_calculix_j2_figure(summary, tmp_path)

    assert path.stat().st_size > 20_000


def test_controlled_calculix_input_requests_isotropic_hardening():
    root = Path(__file__).resolve().parents[2]
    text = (
        root / "qualification" / "vnv" / "external" / "calculix_j2" / "j2_uniaxial_isotropic.inp"
    ).read_text(encoding="utf-8")

    assert "*PLASTIC,HARDENING=ISOTROPIC" in text
    assert "S,PEEQ,E,ENER" in text
    assert "NLGEOM=NO" in text


def _sample_dat() -> str:
    def rows(width: int, values: str) -> str:
        return "\n".join(f" 1 {index} {values}" for index in range(1, 9))

    return "\n\n".join(
        [
            "stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set EALL and time  0.1000000E+01\n\n"
            + rows(6, "3.000000E+02 0.0 0.0 0.0 0.0 0.0"),
            "equivalent plastic strain (elem, integ.pnt.,pe)for set EALL and time  0.1000000E+01\n\n"
            + rows(1, "1.000000E-03"),
            "strains (elem, integ.pnt.,exx,eyy,ezz,exy,exz,eyz) for set EALL and time  0.1000000E+01\n\n"
            + rows(6, "2.428571E-03 -9.285714E-04 -9.285714E-04 0.0 0.0 0.0"),
            "internal energy density (elem, integ.pnt.,energy) for set EALL and time  0.1000000E+01\n\n"
            + rows(1, "4.886411E-01"),
        ]
    )
