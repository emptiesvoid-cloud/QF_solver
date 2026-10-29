"""Independent quadrature of error norms for an externally supplied nodal field.

No stiffness or load assembly, solve or modal computation occurs here. Samples
use independently coded reference shapes and affine mappings. The two quadrature
orders are candidate rules, not a proof of convergence or acceptance.
"""
from __future__ import annotations

import math
from experiments.wp12_vv3d_adaptive import oracle, quadrature, sampling


def integrated_errors(prepared_mesh: dict, nodal_displacements: list, *, order: int) -> dict[str,float]:
    family=prepared_mesh["family"]
    tet=family.startswith("TET")
    rule=quadrature.tetrahedron_duffy_rule(order) if tet else quadrature.hexahedron_rule(order)
    lam,mu=oracle.lame()
    u2=energy2=stress2=strain2=exact_u2=exact_energy2=exact_stress2=exact_strain2=0.0
    for cell in prepared_mesh["connectivity_zero_based"]:
        for r,s,t,reference_weight in rule:
            sample=sampling.sample_cell(family,cell,prepared_mesh["nodes_integer"],
                                        prepared_mesh["integer_coordinate_denominator"],nodal_displacements,(r,s,t))
            exact=oracle.field(sample["point_m"])
            weight=reference_weight*sample["jacobian_det_m3"]
            du=tuple(a-b for a,b in zip(sample["displacement_m"],exact["u_m"]))
            de=tuple(a-b for a,b in zip(sample["strain"],exact["strain"]))
            ds=tuple(a-b for a,b in zip(sample["stress_pa"],exact["stress_pa"]))
            def elastic_density(e):
                return lam*sum(e[:3])**2+2*mu*(sum(v*v for v in e[:3])+0.5*sum(v*v for v in e[3:]))
            def stress_density(s):
                return sum(v*v for v in s[:3])+2*sum(v*v for v in s[3:])
            u2+=weight*sum(v*v for v in du)
            energy2+=weight*elastic_density(de)
            stress2+=weight*stress_density(ds)
            strain2+=weight*(sum(v*v for v in de[:3])+0.5*sum(v*v for v in de[3:]))
            exact_u2+=weight*sum(v*v for v in exact["u_m"])
            exact_energy2+=weight*elastic_density(exact["strain"])
            exact_stress2+=weight*stress_density(exact["stress_pa"])
            exact_strain2+=weight*(sum(v*v for v in exact["strain"][:3])
                                   +0.5*sum(v*v for v in exact["strain"][3:]))
    if not all(math.isfinite(x) and x >= 0 for x in (u2,energy2,stress2,strain2,exact_u2,exact_energy2,
                                                      exact_stress2,exact_strain2)):
        raise ValueError("nonfinite or negative quadrature norm")
    if min(exact_u2,exact_energy2,exact_stress2,exact_strain2) <= 0:
        raise ValueError("exact-reference norm vanishes")
    return {"displacement_l2_m_5_2":math.sqrt(u2),"displacement_relative_l2":math.sqrt(u2/exact_u2),
            "energy_error_norm_sqrt_j":math.sqrt(energy2),"energy_error_relative":math.sqrt(energy2/exact_energy2),
            "strain_error_l2_m_3_2":math.sqrt(strain2),"strain_error_relative":math.sqrt(strain2/exact_strain2),
            "stress_error_l2_pa_m_3_2":math.sqrt(stress2),"stress_error_relative":math.sqrt(stress2/exact_stress2),
            "quadrature_order":order,"status":"DIAGNOSTIC_UNQUALIFIED"}
