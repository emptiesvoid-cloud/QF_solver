"""Reference Gauss rules for later integration; generating points is not FEM assembly."""
from __future__ import annotations
from itertools import product

_GAUSS = {
    4: ((-0.8611363115940526,0.34785484513745385),(-0.3399810435848563,0.6521451548625461),
        (0.3399810435848563,0.6521451548625461),(0.8611363115940526,0.34785484513745385)),
    8: ((-0.9602898564975363,0.10122853629037626),(-0.7966664774136267,0.22238103445337448),
        (-0.5255324099163290,0.31370664587788727),(-0.1834346424956498,0.3626837833783620),
        (0.1834346424956498,0.3626837833783620),(0.5255324099163290,0.31370664587788727),
        (0.7966664774136267,0.22238103445337448),(0.9602898564975363,0.10122853629037626)),
}


def hexahedron_rule(order: int) -> tuple[tuple[float,float,float,float], ...]:
    if order not in _GAUSS:
        raise ValueError("only the proposed 4 and 8 point rules are available")
    return tuple((x[0],y[0],z[0],x[1]*y[1]*z[1]) for x,y,z in product(_GAUSS[order],repeat=3))


def tetrahedron_duffy_rule(order: int) -> tuple[tuple[float,float,float,float], ...]:
    if order not in _GAUSS:
        raise ValueError("only the proposed 4 and 8 point rules are available")
    transformed = tuple(((x+1)/2,w/2) for x,w in _GAUSS[order])
    result=[]
    for (a,wa),(b,wb),(c,wc) in product(transformed,repeat=3):
        r=a
        s=(1-a)*b
        t=(1-a)*(1-b)*c
        result.append((r,s,t,wa*wb*wc*(1-a)**2*(1-b)))
    return tuple(result)
