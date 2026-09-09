---
doc_id: DOC-028-WP06B-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP06B HEX8 buckling root-cause remediation

WP06B starts from commit
`be8fbd99d8a3d3b8e4ee3b8d867842389b063061` and does not rewrite the WP06
evidence or any 0.2.7 evidence. The frozen WP06 scope and tolerances are
reused unchanged in the [`WP06B contract`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp06b_hex8_buckling_contract.json).
The machine-readable result is the [`WP06B evidence`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp06b_hex8_buckling_vnv.json).

## Root-cause audit

The Euler formula was independently checked as
`Pcr = C*pi^2*E*I/L^2`, with `E=1000`, `I=1.2*1.0^3/12=0.1`, `L=4`,
and `C=0.25`/`1.0`. The resulting factors are 15.4212569 and 61.6850275
for total reference load 1.0. Units, preload scaling, `Kg` sign, eigenvalue
interpretation and residual conventions are coherent. The factor failure is
therefore a model/scope limitation: fully integrated low-order HEX8 bending
and the declared solid boundary conditions are not a pure Euler oracle. In
the pinned case, the single UX anchor leaves the remainder of the end-plane
axial degrees of freedom available; the first solid mode is predominantly
axial/warping rather than a pure Euler lateral mode.

The refinement sequence is a real generalized eigenvalue sequence, not a
serialization artifact. Its non-monotone behavior is attributed to section
discretization, aspect ratio, HEX8 bending/locking behavior and the pinned
boundary model. It is retained as a failed gate, not smoothed or reinterpreted.

The original invalid-orientation probe reversed all eight connectivity entries.
That permutation preserves the HEX8 orientation and correctly produced
positive Jacobians. The validator itself already rejected a true mirrored
connectivity. WP06B changes only the probe to exercise that actual invalid
case and records the `detJ < 0` diagnostic.

The replay digest difference was limited to floating-point tails in residual
and diagnostic reductions; critical factors and physical mode metrics did not
change materially. Existing mode-sign canonicalization was sufficient. A
fixed normalized ARPACK start vector was added to the existing sparse calls,
with no change to the generalized eigenproblem or tolerances. The complete
campaign now reproduces the same digest twice.

## WP06B result

| Gate | Result |
| --- | --- |
| Euler factor | `FAIL` |
| Mesh refinement | `FAIL` |
| Invalid geometry rejection | `PASS` |
| Replay determinism | `PASS` |
| Mode residuals / matching | `PASS` |
| Robustness | `PASS` |
| Current CalculiX oracle | `SKIPPED_EXTERNAL_UNAVAILABLE` |

The technical decision remains **`NOT_QUALIFIED`**. The correction of the
test case and replay noise does not close the frozen factor/refinement gates,
and WP06B does not change the boundary model or analytical tolerance after
observing results. No public promotion or Owner gate is applied.

The global technical state remains `32 QUALIFIED_BOUNDED`, `13 EXPERIMENTAL`
and `1 NOT_QUALIFIED`, exactly `COMB-HEX8-linear_buckling`. WEDGE6 static is
unchanged and distinct. A future attempt needs a new, explicitly approved
solid-buckling scope/oracle or a demonstrated HEX8 formulation improvement;
WP07 is not started here.
