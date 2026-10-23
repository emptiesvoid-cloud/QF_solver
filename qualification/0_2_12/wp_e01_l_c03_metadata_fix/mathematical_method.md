# C03 rational math evaluator

## Scope

`rigorous_math.py` is a standalone exact-rational post-processing helper. It does
not import the solver, evaluate a constitutive kernel, assemble a system, or
validate the eight archived actions. Its synthetic tests are analytic inputs
only. The `mathematical_verdict` describes the supplied rational model;
`action_verdict` remains `INCONCLUSIVE` until the caller separately establishes
archive input identity/provenance and production branch linkage. A positive
action verdict also requires production rounding-budget evidence. These explicit
evidence booleans are assertions from that upstream process, not checks
performed by this module.

## Formula and extrema

For an affine deviatoric trial tensor `d(s)=d0+s*dd` and the Frobenius tensor
product, `q(s)^2=(3/2) d(s):d(s)`, so

```
A = (3/2) d0:d0
B = 3 d0:dd
C = (3/2) dd:dd
q(s)^2 = A+B*s+C*s^2.
```

`coefficients_from_affine_deviator` applies that identity to equally sized
component vectors. For flattened symmetric tensors, callers must include each
off-diagonal component twice to represent the Frobenius product. This helper
does not prove the constitutive trial stress is affine; fixed history and the
actual solver equations must establish that outside this module.

For exact coefficients, the range on closed `[l,u]` is found from endpoints
and, when it lies in the interval, the stationary point `-B/(2C)`. If `C=0`,
the polynomial is linear or constant and endpoints suffice. For coefficient
intervals, the evaluator forms lower and upper coefficient envelopes and
splits at `s=0`, where the extremizing endpoint for `B*s` changes. It minimizes
the lower and upper envelopes separately to bound the true segment minimum,
and maximizes them separately to bound the true segment maximum. This is
conservative for independent rectangular coefficient intervals.

For a nonnegative rational `x`, with `N=2^bits`, integer arithmetic computes
`k=floor(sqrt(floor(x*N^2)))`; the enclosure is `[k/N,k/N]` if equality is
exact, otherwise `[k/N,(k+1)/N]`. The implementation independently checks
`lower^2 <= x <= upper^2` and serializes those checked comparisons for both
radicand endpoints. A proven negative `q^2` is invalid for a squared quantity;
an enclosure extending below zero is inconclusive.

## Verdict and serialization

The evaluator separately encloses the minimum and maximum of `g` on the
segment. Plastic stability requires the minimum to be strictly positive;
elastic stability requires the maximum to be strictly negative. A decisive
extremum interval touching zero is inconclusive. `FAIL` in
`mathematical_verdict` means the relevant extremum proves a strict-sign
violation somewhere on the segment. An action-level `FAIL` additionally
requires validated archive inputs and the archived base branch identity;
positive rounding-budget evidence is required for action-level `PASS`.
Serialized rational endpoints are numerator/denominator
strings; decimal views use integer division with outward rounding. The strict
parser checks endpoint canonicalization and consistency of decimal displays.
This catches partial/inconsistent tampering, but not a coordinated edit of all
fields. Cryptographic hashes and archive provenance must be checked elsewhere.

`float` inputs are converted exactly from their binary64 `as_integer_ratio()`.
`Decimal` inputs are converted to their exact finite decimal rational. Neither
conversion establishes an enclosure of an underlying physical quantity or
validates how the archived value was produced.

## Production base-branch reconstruction

`production_branch_budget.py` follows only the frozen scalar code path:

```
shear = fl(E / fl(2 * fl(1 + nu)))
D     = fl(fl(3 * shear) + H)
dgamma = fl(yield_value / D)
```

Each exact rational operation result is bracketed by adjacent binary64 values
using a runtime check for radix 2, 53-bit significand, binary64 exponent bounds,
`nextafter` adjacency, and exact rational comparison on both bracket sides.
This encloses each operation under any standard IEEE rounding direction;
nonfinite, nonpositive-denominator, subnormal, overflow, or unverified source
cases are refused. Plastic archives replace `yield_function` with post-return
zero, so the module does not call that value the trial yield. It recovers an
interval for the pre-return quantity using
`[prev(plastic_multiplier), next(plastic_multiplier)] * D`. The reported
numeric value is explicitly unavailable for plastic points. Elastic records
use their stored pre-return `yield_function` as an exact binary64 value.

For `Yprod` and mathematical base interval `G0`, the module reports the exact
interval `E=Yprod-G0` and `B=max(abs(E.lo),abs(E.hi))`. It confirms branch
linkage only when the production and mathematical base signs strictly match
the expected branch and the base clearance strictly exceeds `B` (`G0.lo>B`
for plastic, `-G0.hi>B` for elastic). It separately checks the expected sign
of the certified segment extremum. Missing provenance or source identity leaves
the result inconclusive; explicit identity mismatch is invalid. `B` is an
a-posteriori base-state discrepancy bound. It is not an a-priori production
rounding budget and says nothing by itself about errors over the full segment.

## Verification boundary

Run the synthetic suite with the requested interpreter:

```
py -3.13 -B -m unittest -v qualification/0_2_12/wp_e01_l_c03_proof/test_rigorous_math.py
```

Even a mathematical `PASS` from these generic helpers is not a C03 action or
global certificate. No eight-action archive inputs, production branch result,
rounding budget, or proof manifest are assessed here.
