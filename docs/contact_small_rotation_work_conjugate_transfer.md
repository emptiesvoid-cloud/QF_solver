# Experimental small-rotation tangential contact transfer

## Maturity and provenance

For the internal 0.2.12 integration candidate, this B* sub-capability is
classified `EXPERIMENTAL_BOUNDED`. This is a scoped maturity label, not a
scientific certificate or a statement about the published 0.2.11 release. The
mode is opt-in; omission of the transfer parameter continues to select the
legacy behavior. The dedicated record at
[`qualification/0_2_12/wp_c01_bstar_capability_record.json`](../qualification/0_2_12/wp_c01_bstar_capability_record.json)
tracks the classification and the R13–R18 provenance.

R13 supplies algebraic and exploratory stick evidence. R14 observed nine
accepted steps with stick at 1–7 and slip at 8–9. R16 reproduced the fixture
from the integrated solver; its original pytest parsing failure remains
preserved. R17/R18 replayed the archived output offline and independently
reconstructed the raw moment. These observations do not qualify finite
sliding, a global consistent slip tangent, or general mesh convergence.
There is no numeric angle threshold: remaining in the small-rotation regime
is an analyst-enforced scope condition.

## Scope and conventions

`contact_tangential_transfer="small_rotation_work_conjugate"` is an explicit,
experimental option for the linear-static node-to-triangle active-set contact
route. The default remains `legacy`. The experimental option requires the
frozen initial master face and projection, frictional contact, and reference
geometry. It rejects updated search and finite sliding. It is a first-order
small-rotation transfer law; it does not define a finite-slip surface update,
transport of friction history between faces, or a general mortar formulation.

The ordered master triangle has reference vertices `X_j`, linear shape
functions `N_j`, barycentric projection weights `β_j`, unit normal `n`, and
constant reference surface gradients `a_j = ∇_s N_j`. The slave reference
position is `X_s`; the projected master point is
`X_p = Σ_j β_j X_j`; the signed initial normal gap is
`g0 = n · (X_s - X_p)`. Positive `g0` means the slave starts on the positive
normal side. The master node ordering determines `n`, and this mode does not
silently reverse it.

For tangent basis vector `t_a` and translational virtual displacements, the
linearized normal variation is

```text
δn = -Σ_j a_j (n · δu_j)
```

and the experimental relative tangential variation is

```text
B*_a δu = t_a · (δu_s - Σ_j β_j δu_j - g0 δn).
```

If `F_t = Σ_a F_a t_a` is the local tangential force in the existing return
map's sign convention, the work-conjugate generalized nodal force is

```text
q_s = F_t
q_j = -β_j F_t + g0 (a_j · F_t) n.
```

These are the contact generalized-force contributions assembled by the
solver. They are the transpose map of `B*`; they do not represent additional
physical nodal couples. The extra master-node terms have zero resultant
because `Σ_j a_j = 0`, and cancel the reference gap couple because
`Σ_j X_j (a_j · F_t) = F_t` for a tangent force on a planar linear triangle.
Thus the pair has zero resultant moment about any point in the reference
configuration. An infinitesimal common rigid translation or rotation also has
zero virtual work.

## Units and constitutive branches

Coordinates and displacements are in metres; `g0` is metres; `a_j` has units
`m⁻¹`; `B*` is dimensionless; `B* δu` is metres; tangential stiffness is
`N/m`; `F_t` and each `q` are newtons; moments are `N·m`.

The stick matrix is the derivative of the work-conjugate elastic force:

```text
K_t = k_t Σ_a B*_aᵀ B*_a.
```

The existing Coulomb return map still chooses stick/slip/open state and the
local force magnitude. In slip, this option changes the generalized force
mapping to `B*ᵀ F_t`; it does not alter the yield rule, hysteresis, or active-set
transition policy. The existing slip force is supplied through the current
outer/root solve rather than by adding a new global consistent slip tangent.
Open and zero-force pairs create no tangential transfer. At `g0=0`, `B*`
reduces exactly to the legacy operator.

## Boundaries

The result is a reference-pair, first-order kinematic contract. Terms of order
`O(|u|²)` and `O(|θ|²)` are omitted. A finite tangential separation, changing
master face, curved surface, large rotation, or evolving projection requires
a separate finite-sliding derivation and must not use this mode. The raw
0.002 `N·m` moment check remains unchanged; the legacy post-processing moment
correction is bypassed only when this assembled transfer mode is selected.
The implementation rejects unsupported route/projection options, but it does
not impose a numerical angle cutoff at runtime. The caller must keep the
kinematics within the small-rotation regime; reported rotations are diagnostics,
not an automatic admissibility certificate.

The bounded example and archived comparison notes are in
[`examples/contact/frictional_bstar_small_rotation/`](../examples/contact/frictional_bstar_small_rotation/README.md).

## Verification

`tests/unit/test_wpc01_r13_small_rotation_transfer.py` checks the operator and
its conjugate force formula independently, force and moment resultants,
infinitesimal rigid motions, the stick tangent, slip branch behavior, zero-gap
reduction, mode guards, restart identity, and the uncorrected raw moment
diagnostic. These are algebraic and model-admissibility tests; they do not
constitute a FEM campaign or qualification.
