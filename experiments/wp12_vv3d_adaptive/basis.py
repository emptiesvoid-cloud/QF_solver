"""Reference shape values for prospective load integration; no assembly or solve."""
from __future__ import annotations

from experiments.wp12_vv3d_adaptive.mesh import HEX_CORNERS, HEX_EDGES, TET_EDGES


def shape_values(family: str, point: tuple[float, float, float]) -> tuple[float, ...]:
    r,s,t = point
    if family in {"TET4", "TET10"}:
        bary = (1-r-s-t,r,s,t)
        if min(bary) < -1e-12 or max(bary) > 1+1e-12:
            raise ValueError("point outside reference tetrahedron")
        if family == "TET4":
            return bary
        return tuple(x*(2*x-1) for x in bary)+tuple(4*bary[a]*bary[b] for a,b in TET_EDGES)
    if family not in {"HEX8", "HEX20"} or max(abs(r),abs(s),abs(t)) > 1+1e-12:
        raise ValueError("unknown family or point outside reference hexahedron")
    signs = tuple(tuple(2*v-1 for v in corner) for corner in HEX_CORNERS)
    xi = (r,s,t)
    products = [((1+sgn[0]*r)*(1+sgn[1]*s)*(1+sgn[2]*t)) for sgn in signs]
    if family == "HEX8":
        return tuple(value/8 for value in products)
    corners = tuple(value*(sum(sgn[i]*xi[i] for i in range(3))-2)/8 for value,sgn in zip(products,signs))
    edges = []
    for a,b in HEX_EDGES:
        free = next(i for i in range(3) if signs[a][i] != signs[b][i])
        fixed = [i for i in range(3) if i != free]
        edges.append((1-xi[free]**2)*(1+signs[a][fixed[0]]*xi[fixed[0]])
                     *(1+signs[a][fixed[1]]*xi[fixed[1]])/4)
    return corners+tuple(edges)


def shape_gradients(family: str, point: tuple[float, float, float]) -> tuple[tuple[float,float,float], ...]:
    """Analytic reference derivatives, Voigt-independent; no element assembly."""
    shape_values(family,point)  # Validate reference-domain membership.
    r,s,t=point
    if family in {"TET4","TET10"}:
        bary=(1-r-s-t,r,s,t)
        db=((-1.0,-1.0,-1.0),(1.0,0.0,0.0),(0.0,1.0,0.0),(0.0,0.0,1.0))
        if family == "TET4":
            return db
        corners=tuple(tuple((4*bary[i]-1)*db[i][axis] for axis in range(3)) for i in range(4))
        edges=tuple(tuple(4*(bary[a]*db[b][axis]+bary[b]*db[a][axis]) for axis in range(3))
                    for a,b in TET_EDGES)
        return corners+edges
    xi=(r,s,t)
    signs=tuple(tuple(2*v-1 for v in corner) for corner in HEX_CORNERS)
    gradients=[]
    for sign in signs:
        factors=tuple(1+sign[i]*xi[i] for i in range(3))
        product=factors[0]*factors[1]*factors[2]
        scalar=sum(sign[i]*xi[i] for i in range(3))-2
        components=[]
        for axis in range(3):
            others=[i for i in range(3) if i != axis]
            deriv=sign[axis]*factors[others[0]]*factors[others[1]]
            components.append(deriv/8 if family == "HEX8" else (deriv*scalar+product*sign[axis])/8)
        gradients.append(tuple(components))
    if family == "HEX20":
        for a,b in HEX_EDGES:
            free=next(i for i in range(3) if signs[a][i] != signs[b][i])
            fixed=[i for i in range(3) if i != free]
            components=[]
            for axis in range(3):
                if axis == free:
                    deriv=(-2*xi[free])*(1+signs[a][fixed[0]]*xi[fixed[0]])*(1+signs[a][fixed[1]]*xi[fixed[1]])/4
                else:
                    other=next(i for i in fixed if i != axis)
                    deriv=(1-xi[free]**2)*signs[a][axis]*(1+signs[a][other]*xi[other])/4
                components.append(deriv)
            gradients.append(tuple(components))
    return tuple(gradients)
