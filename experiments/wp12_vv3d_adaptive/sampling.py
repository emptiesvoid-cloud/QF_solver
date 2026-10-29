"""Pointwise interpolation for postprocessing supplied displacement data; no solve or assembly."""
from __future__ import annotations

from experiments.wp12_vv3d_adaptive import basis, load_assembly_draft, oracle


def _inverse3(j):
    a,b,c=j
    det=load_assembly_draft._det3(j)
    if det <= 0:
        raise ValueError("nonpositive mapping Jacobian")
    return (( (b[1]*c[2]-b[2]*c[1])/det, (a[2]*c[1]-a[1]*c[2])/det, (a[1]*b[2]-a[2]*b[1])/det),
            ( (b[2]*c[0]-b[0]*c[2])/det, (a[0]*c[2]-a[2]*c[0])/det, (a[2]*b[0]-a[0]*b[2])/det),
            ( (b[0]*c[1]-b[1]*c[0])/det, (a[1]*c[0]-a[0]*c[1])/det, (a[0]*b[1]-a[1]*b[0])/det))


def sample_cell(family, cell, coordinates_integer, denominator, nodal_displacements, reference_point):
    """Interpolate one affine cell at a reference point from externally supplied displacements.

    Input nodal displacements are node-major triples; the result is an unqualified
    point sample. This function does not assemble element stiffness or load or solve.
    """
    if len(nodal_displacements) != len(coordinates_integer):
        raise ValueError("displacement/node count mismatch")
    origin,jacobian,det=load_assembly_draft._affine_cell_geometry(family,cell,coordinates_integer,denominator)
    inverse=_inverse3(jacobian)
    shape=basis.shape_values(family,reference_point)
    grads=basis.shape_gradients(family,reference_point)
    if len(shape) != len(cell):
        raise ValueError("shape/connectivity mismatch")
    point=tuple(origin[a]+sum(jacobian[a][b]*reference_point[b] for b in range(3)) for a in range(3))
    displacement=tuple(sum(shape[i]*nodal_displacements[node][a] for i,node in enumerate(cell)) for a in range(3))
    grad=[[0.0]*3 for _ in range(3)]
    for local,node in enumerate(cell):
        physical_gradient=tuple(sum(grads[local][q]*inverse[q][axis] for q in range(3)) for axis in range(3))
        for component in range(3):
            for axis in range(3):
                grad[component][axis]+=nodal_displacements[node][component]*physical_gradient[axis]
    strain=(grad[0][0],grad[1][1],grad[2][2],grad[0][1]+grad[1][0],
            grad[1][2]+grad[2][1],grad[0][2]+grad[2][0])
    lam,mu=oracle.lame()
    trace=sum(strain[:3])
    stress=tuple(lam*trace+2*mu*x for x in strain[:3])+tuple(mu*x for x in strain[3:])
    return {"point_m":point,"displacement_m":displacement,"strain":strain,"stress_pa":stress,"jacobian_det_m3":det}
