"""Independent symbolic derivation of manufactured elasticity; never imports QF Solver."""
from __future__ import annotations
import sympy as s


def audit() -> None:
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
    print("Independent symbolic force and energy identities verified; no FEM executed.")


if __name__ == "__main__":
    audit()
