"""Independent symbolic derivation of manufactured elasticity; never imports QF Solver."""
from __future__ import annotations
import math
try:
    import sympy as s
except ModuleNotFoundError:  # optional CAS aid; the standard test baseline omits SymPy
    s = None


def audit() -> None:
    if s is None:
        raise RuntimeError("the optional symbolic audit requires SymPy; install it to run this audit")
    x,y,z,lx,ly,lz,a,lam,mu=s.symbols("x y z Lx Ly Lz A lambda mu", real=True, positive=True)
    variables=(x,y,z)
    kx,ky,kz=s.pi/lx,s.pi/ly,s.pi/lz
    w=a*s.sin(kx*x)*s.sin(ky*y)*s.sin(kz*z)
    u=s.Matrix((0,0,w))
    grad=u.jacobian(variables)
    strain=(grad+grad.T)/2
    stress=lam*s.trace(strain)*s.eye(3)+2*mu*strain
    force=s.Matrix([-sum(s.diff(stress[i,j],variables[j]) for j in range(3)) for i in range(3)])
    expected=s.Matrix((-(lam+mu)*a*kx*kz*s.cos(kx*x)*s.sin(ky*y)*s.cos(kz*z),
                       -(lam+mu)*a*ky*kz*s.sin(kx*x)*s.cos(ky*y)*s.cos(kz*z),
                       (mu*(kx*kx+ky*ky+kz*kz)+(lam+mu)*kz*kz)*w))
    if any(s.simplify(v) != 0 for v in force-expected):
        raise AssertionError("manufactured force differs from independent symbolic -div(sigma)")
    density=(lam*s.trace(strain)**2+2*mu*sum(strain[i,j]**2 for i in range(3) for j in range(3)))/2
    energy=s.integrate(density,(x,0,lx),(y,0,ly),(z,0,lz))
    expected_energy=a*a*lx*ly*lz/8*(mu*(kx*kx+ky*ky)/2+(mu+lam/2)*kz*kz)
    if s.simplify(energy-expected_energy) != 0:
        raise AssertionError("manufactured energy differs from symbolic volume integral")

    # Cross-check the independently differentiated tensor field against the
    # runtime analytic oracle without importing or calling the FEM solver.
    from experiments.wp12_vv3d_adaptive import oracle

    lam_value, mu_value = oracle.lame()
    common = {lx: 1.0, ly: 1.0, lz: 1.0, a: oracle.AMPLITUDE_M,
              lam: lam_value, mu: mu_value}
    strain_vector = (strain[0, 0], strain[1, 1], strain[2, 2],
                     2 * strain[0, 1], 2 * strain[1, 2], 2 * strain[0, 2])
    stress_vector = (stress[0, 0], stress[1, 1], stress[2, 2],
                     stress[0, 1], stress[1, 2], stress[0, 2])
    for point in ((0.19, 0.37, 0.61), (0.43, 0.52, 0.71)):
        substitutions = common | dict(zip(variables, point))
        symbolic_values = {
            "u_m": (0.0, 0.0, float(u[2].subs(substitutions))),
            "strain": tuple(float(value.subs(substitutions)) for value in strain_vector),
            "stress_pa": tuple(float(value.subs(substitutions)) for value in stress_vector),
            "body_force_n_m3": tuple(float(value.subs(substitutions)) for value in force),
        }
        numeric_values = oracle.field(point)
        for field_name, symbolic_components in symbolic_values.items():
            numeric_components = numeric_values[field_name]
            if len(symbolic_components) != len(numeric_components) or any(
                not math.isclose(actual, expected, rel_tol=3.0e-13, abs_tol=1.0e-10)
                for actual, expected in zip(numeric_components, symbolic_components)
            ):
                raise AssertionError(f"runtime oracle differs from independent symbolic {field_name}")
    substitutions = common | {lx: 1.0, ly: 1.0, lz: 1.0}
    symbolic_energy = float(energy.subs(substitutions))
    if not math.isclose(symbolic_energy, oracle.exact_energy_j(), rel_tol=3.0e-13, abs_tol=1.0e-24):
        raise AssertionError("runtime oracle energy differs from independent symbolic volume integral")
    print("Independent symbolic force, field, stress and energy agree with analytic oracle; no FEM executed.")


if __name__ == "__main__":
    audit()
