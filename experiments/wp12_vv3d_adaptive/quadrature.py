"""Reference Gauss rules for later integration; generating points is not FEM assembly."""
from __future__ import annotations
import math
from itertools import product

_GAUSS = {
    4: ((-0.8611363115940526,0.34785484513745385),(-0.3399810435848563,0.6521451548625461),
        (0.3399810435848563,0.6521451548625461),(0.8611363115940526,0.34785484513745385)),
    8: ((-0.9602898564975363,0.10122853629037626),(-0.7966664774136267,0.22238103445337448),
        (-0.5255324099163290,0.31370664587788727),(-0.1834346424956498,0.3626837833783620),
        (0.1834346424956498,0.3626837833783620),(0.5255324099163290,0.31370664587788727),
        (0.7966664774136267,0.22238103445337448),(0.9602898564975363,0.10122853629037626)),
}


def _gauss_12() -> tuple[tuple[float,float], ...]:
    """Gauss-Legendre roots via Newton iteration; mathematical rule construction only."""
    degree=12
    points=[]
    for i in range(1,degree//2+1):
        x=math.cos(math.pi*(i-0.25)/(degree+0.5))
        for _ in range(50):
            previous,current=1.0,x
            for k in range(2,degree+1):
                previous,current=current,((2*k-1)*x*current-(k-1)*previous)/k
            derivative=degree*(x*current-previous)/(x*x-1)
            update=current/derivative
            x-=update
            if abs(update)<1e-15:
                break
        else:
            raise ArithmeticError("Gauss-Legendre Newton iteration did not converge")
        weight=2/((1-x*x)*derivative*derivative)
        points.extend(((-x,weight),(x,weight)))
    return tuple(sorted(points))


_GAUSS[12] = _gauss_12()


def hexahedron_rule(order: int) -> tuple[tuple[float,float,float,float], ...]:
    if order not in _GAUSS:
        raise ValueError("only the proposed 4, 8 and 12 point rules are available")
    return tuple((x[0],y[0],z[0],x[1]*y[1]*z[1]) for x,y,z in product(_GAUSS[order],repeat=3))


def tetrahedron_duffy_rule(order: int) -> tuple[tuple[float,float,float,float], ...]:
    if order not in _GAUSS:
        raise ValueError("only the proposed 4, 8 and 12 point rules are available")
    transformed = tuple(((x+1)/2,w/2) for x,w in _GAUSS[order])
    result=[]
    for (a,wa),(b,wb),(c,wc) in product(transformed,repeat=3):
        r=a
        s=(1-a)*b
        t=(1-a)*(1-b)*c
        result.append((r,s,t,wa*wb*wc*(1-a)**2*(1-b)))
    return tuple(result)
