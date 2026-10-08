# WP08-R1 — Corrected corotational J2 formulation

**Record kind:** implementation design; not implementation, qualification, or gate closure
**Design baseline:** codex/v0.2.12-wp08-constitutive-feasibility-audit at 0eb52ed65a0a6891f30ca51e68371b37210a0fc8
**Owner rescope:** RESCOPE_MINIMAL_CORRECTION
**Prospective maturity:** EXPERIMENTAL
**Prospective qualification:** NOT_ASSESSED; numerical PASS does not imply qualification
**Implementation state:** not started; WP08 remains release-blocking

## Decision and bounded claim

This specification retains the existing additive, associative, isotropic small-strain J2 return map with linear isotropic hardening, but applies it to the bounded right-stretch strain

$$
\mathbf E_B = \mathbf U-\mathbf I,\qquad
\mathbf F=\mathbf R\mathbf U,\qquad
\|\mathbf E_B\|_F\le 0.05.
$$

The constitutive state is attached to the reference/material frame. A spatial superposed rotation does not rotate or otherwise update that state. The local symmetric J2 response is the stress conjugate to \(\mathbf E_B\). The element nominal stress is the adjoint of the exact derivative of the right polar stretch, not the shortcut \(\mathbf R\mathbf T\).

This is a bounded objective corotational small-local-strain model. It is not multiplicative finite-strain plasticity, a general finite-strain material, nor a claim that the existing route is already corrected. Its force and state semantics change and therefore require an explicit formulation identity. No result or evidence from the legacy formulation is promoted.

## 1. Kinematics and frames

At each solid integration point, use the reference gradient and displacement interpolation already used by the element:

$$
\mathbf F = \mathbf I + \nabla_X\mathbf u,\quad
\mathbf F=\mathbf R\mathbf U,\quad
\mathbf R^T\mathbf R=\mathbf I,\quad
\mathbf U=\mathbf U^T>0,\quad J=\det\mathbf F>0.
$$

Frames are fixed as follows:

| Quantity | Definition | Frame / type |
|---|---|---|
| \(\mathbf E_B=\mathbf U-\mathbf I\) | Biot right-stretch strain | material/reference, symmetric |
| \(\mathbf T_B\) | derivative/conjugate returned by the local J2 update with respect to \(\mathbf E_B\) | material/reference, symmetric; Biot-conjugate stress |
| \(\mathbf P\) | derivative of the incremental material potential with respect to \(\mathbf F\) | two-point nominal stress, current-force/reference-gradient |
| \(\mathbf S=\mathbf F^{-1}\mathbf P\) | second Piola–Kirchhoff stress | material/reference, symmetric |
| \(\boldsymbol\sigma=J^{-1}\mathbf P\mathbf F^T\) | Cauchy stress | current/spatial, symmetric |
| Plastic strain tensor | additive J2 internal variable | material/reference |
| Equivalent plastic strain and accumulated scalar work/dissipation | isotropic invariants | scalar |

“Local stress” alone is not an adequate measure or frame. The implementation may retain a local name only with explicit stress_measure and stress_frame metadata. The existing engineering-Voigt convention remains: strain shear entries are engineering shears \(2E_{ij}\), stress shear entries are tensor shears \(T_{ij}\), so their vector dot product equals the tensor contraction.

For a superposed spatial rotation \(\mathbf Q\in SO(3)\), \(\mathbf F^*=\mathbf Q\mathbf F\) implies \(\mathbf R^*=\mathbf Q\mathbf R\), \(\mathbf U^*=\mathbf U\). Thus \(\mathbf E_B\), the material state, and \(\mathbf T_B\) are unchanged; \(\mathbf P^*=\mathbf Q\mathbf P\), \(\mathbf S^*=\mathbf S\), and \(\boldsymbol\sigma^*=\mathbf Q\boldsymbol\sigma\mathbf Q^T\). This invariance is the required objectivity statement for this model.

## 2. Local J2 material update and history

At accepted increment \(n\), state contains a symmetric trace-free plastic strain \(\mathbf E^p_n\), equivalent plastic strain \(\alpha_n\ge0\), and the material/configuration identity. For a trial \(\mathbf E_B\), use the existing isotropic elastic constants \(\lambda,\mu\), yield stress \(\sigma_y>0\), and linear hardening modulus \(H\ge0\):

$$
\mathbf E^e_{\rm tr}=\mathbf E_B-\mathbf E^p_n,\quad
\mathbf T_{\rm tr}=2\mu\,\mathrm{dev}(\mathbf E^e_{\rm tr})
+\lambda\,\mathrm{tr}(\mathbf E^e_{\rm tr})\mathbf I,\quad
q_{\rm tr}=\sqrt{\tfrac32\,\mathrm{dev}(\mathbf T_{\rm tr}):
\mathrm{dev}(\mathbf T_{\rm tr})},\quad
f_{\rm tr}=q_{\rm tr}-(\sigma_y+H\alpha_n).
$$

For \(f_{\rm tr}\le0\), the step is elastic: \(\mathbf T_B=\mathbf T_{\rm tr}\), \(\mathbf E^p_{n+1}=\mathbf E^p_n\), \(\alpha_{n+1}=\alpha_n\). For an active smooth plastic step:

$$
\Delta\gamma=\frac{f_{\rm tr}}{3\mu+H},\quad
\mathbf N=\frac{\mathrm{dev}(\mathbf T_{\rm tr})}{q_{\rm tr}},\quad
\mathbf E^p_{n+1}=\mathbf E^p_n+\tfrac32\Delta\gamma\mathbf N,\quad
\alpha_{n+1}=\alpha_n+\Delta\gamma,
$$

$$
\mathbf T_B=K\,\mathrm{tr}(\mathbf E_B-\mathbf E^p_n)\mathbf I
+\left(1-\frac{3\mu\Delta\gamma}{q_{\rm tr}}\right)
\mathrm{dev}(\mathbf T_{\rm tr}),\qquad K=\lambda+\tfrac23\mu.
$$

These equations state the existing local radial-return model in tensor form; implementation must cross-check the existing engineering-Voigt routine rather than introduce a second constitutive law. The local tangent is the algorithmic derivative at fixed accepted state, including the return-map branch.

For this linear isotropic-hardening model, the thermodynamic split is elastic recoverable energy plus stored hardening energy \(H\alpha^2/2\), and intrinsic rate-independent dissipation increment \(\sigma_y\Delta\alpha\ge0\). The legacy field plastic_dissipation is currently accumulated from a trapezoidal stress–plastic-strain work expression; it must not be silently relabeled as the corrected intrinsic dissipation. Corrected state must distinguish plastic_work_legacy (only if preserved as provenance), plastic_dissipation, and hardening_energy, or omit unneeded legacy work from the new state.

Trial updates always start from the last accepted state. Newton, line-search, and rejected increment evaluations must not mutate accepted state. Commit exactly once after global convergence; rollback discards every trial value. Because \(\mathbf U\) and \(\mathbf E_B\) are in the fixed reference/material frame, changing \(\mathbf R\) alone causes no state transport. Any display in a spatial frame is a derived rotation and never becomes the state used for the next return map.

## 3. Incremental work and exact polar derivative

For a fixed accepted state, the associative radial return has a local incremental potential: minimize elastic energy plus hardening energy and the rate-independent dissipation \(\sigma_y\Delta\alpha\), subject to the J2 flow/equivalent-plastic-strain constraints. The returned \(\mathbf T_B\) is the derivative of that minimized local incremental potential with respect to \(\mathbf E_B\) on a smooth active/inactive branch. This is an incremental statement, not a claim of a path-independent global elastic energy for plastic histories.

Let \(\delta\mathbf F=\mathbf R\mathbf A\) and \(\boldsymbol\Omega=\mathbf R^T\delta\mathbf R\), where \(\boldsymbol\Omega^T=-\boldsymbol\Omega\). Differentiating \(\mathbf F=\mathbf R\mathbf U\) gives

$$
\mathbf A=\boldsymbol\Omega\mathbf U+\delta\mathbf U,\qquad
\mathbf A-\mathbf A^T=\boldsymbol\Omega\mathbf U+\mathbf U\boldsymbol\Omega.
$$

Thus \(\boldsymbol\Omega\) is obtained from the Sylvester equation above and \(\delta\mathbf U=\mathrm{sym}(\mathbf A-\boldsymbol\Omega\mathbf U)\). In a principal-stretch basis \(\mathbf U=\mathrm{diag}(\lambda_1,\lambda_2,\lambda_3)\):

$$
\Omega_{ij}=\frac{A_{ij}-A_{ji}}{\lambda_i+\lambda_j},\qquad
\delta U_{ij}=\frac{\lambda_iA_{ij}+\lambda_jA_{ji}}{\lambda_i+\lambda_j}\quad(i\ne j),
\qquad \delta U_{ii}=A_{ii}.
$$

The incremental potential depends on \(\mathbf U\), not independently on \(\mathbf R\). Its variation is \(\delta\psi_{\rm inc}=\mathbf T_B:\delta\mathbf U\). Define \(\bar{\mathbf P}=\mathbf R^T\mathbf P\) by the adjoint identity

$$
\bar{\mathbf P}:\mathbf A=\mathbf T_B:\delta\mathbf U
\quad\text{for every }\mathbf A.
$$

For \(\hat{\mathbf T}=\mathbf V^T\mathbf T_B\mathbf V\), \(\mathbf U=\mathbf V\,\mathrm{diag}(\lambda_i)\mathbf V^T\), the implementation-ready components are

$$
\hat{\bar P}_{ii}=\hat T_{ii},\qquad
\hat{\bar P}_{ij}=\frac{2\lambda_i}{\lambda_i+\lambda_j}\hat T_{ij}
\quad(i\ne j),\qquad
\mathbf P=\mathbf R\mathbf V\hat{\bar{\mathbf P}}\mathbf V^T.
$$

\(\bar{\mathbf P}\) need not be symmetric. Its skew part is not a defect to remove: the exact identity \(\bar{\mathbf P}\mathbf U=\mathbf U\bar{\mathbf P}^T\) makes \(\mathbf P\mathbf F^T\) symmetric and supplies the zero-couple angular-momentum condition. The polar-rotation contribution has not been dropped: the adjoint stress satisfies \(\bar{\mathbf P}:(\boldsymbol\Omega\mathbf U)=0\), so the rotation variation contributes zero to material power, as required by objectivity. The exact power/work-virtual identity is

$$
\mathbf P:\delta\mathbf F=\mathbf T_B:\delta\mathbf U.
$$

This derivation does not assert that \(\mathbf T_B\) is itself Cauchy stress or that \(\mathbf P=\mathbf R\mathbf T_B\). The latter holds only in coaxial/commuting cases (including the isotropic elastic controls in the audit).

## 4. Reconstructed stress measures

Use the corrected \(\mathbf P\) above, then

$$
\mathbf S=\mathbf F^{-1}\mathbf P=\mathbf U^{-1}\bar{\mathbf P},\qquad
\boldsymbol\sigma=\frac1J\mathbf P\mathbf F^T
=\frac1J\mathbf R(\bar{\mathbf P}\mathbf U)\mathbf R^T.
$$

Since \(\bar{\mathbf P}\mathbf U=\mathbf U\bar{\mathbf P}^T\), both \(\mathbf S\) and \(\boldsymbol\sigma\) are symmetric in exact arithmetic. Compute these formulas without symmetrizing them. A symmetry violation is diagnostic evidence and must fail the corrected route; post-hoc averaging is forbidden. The local output is \(\mathbf T_B=\mathrm{sym}(\mathbf R^T\mathbf P)\), named biot_stress or equivalently with explicit measure=BIOT_STRESS and frame=REFERENCE_MATERIAL.

Principal values and von Mises values in the corrected generic stress result are derived from the declared spatial Cauchy stress. Other measures may be exported separately, but must not be mixed in one average or generic aggregate. Integration-point fields carry measure, frame, formulation ID, semantic version, and availability. Historical corotational fields remain LEGACY_UNSPECIFIED_COROTATIONAL_STRESS; historical second_piola_stress is not reinterpreted.

## 5. Element force and tangent

With reference shape gradients \(N_{a,J}\) and reference quadrature measure \(w_q\):

$$
f^{\rm int}_{ai}=\sum_q w_q P_{iJ}^{(q)}N_{a,J}^{(q)}.
$$

The force is changed because the exact constitutive map changes \(\mathbf P\). This is required for the virtual-work identity; it is not a post-processing correction. Details of force assembly and the compatible tangent are frozen in wp08_r1_force_tangent_specification.md.

## 6. Domain, guards, and exclusions

Corrected v1 is limited to the existing solid element families TET4, TET10, HEX8, HEX20; isotropic linear elasticity plus the existing associative J2/isotropic-hardening return; reference-gradient solid kinematics; homogeneous fixed boundary constraints; and the existing local stretch-strain cap \(\|\mathbf U-\mathbf I\|_F\le0.05\). No shell, beam, contact, finite-strain/multiplicative plasticity, anisotropic material orientation, follower load, general finite sliding, or new constitutive law is added.

Reject non-finite \(\mathbf F\), \(J\le10^{-10}\) (the existing determinant floor), non-positive polar stretches, failed polar reconstruction, non-finite return-map output, and any strain outside the frozen cap. In this cap, singular/near-singular stretch is already excluded by \(\|\mathbf U-\mathbf I\|_F\le0.05\); do not enlarge the cap without a new review. On a guard failure, report an element/integration-point diagnostic and do not emit transformed stress as valid.

## 7. Formulation and migration IDs

Use distinct IDs:

- legacy_corotational_j2/v1: current force/state/output semantics; absent version on old input resolves only to this legacy ID.
- corrected_corotational_biot_j2/v1: this specification, explicit selection required.

No automatic fallback from corrected to legacy is allowed. Corrected state uses corotational_j2_state/v2, semantic result version corotational_stress/v2, and records kinematics=F_RU_BIOT_SMALL_STRAIN, material-state frame, measure/frame of each output, material parameters, integration rule, source/operator identity, and state hash. A legacy checkpoint without complete formulation/state identity is readable where the existing parser supports it but is not safe to resume under corrected v1. No legacy checkpoint migration is implied. A new analysis may start from a fresh zero state. The checkpoint and result rules are detailed in wp08_r1_constitutive_state_contract.json.

Historical statuses remain WP08_STATUS=BLOCKED, QF0212_G03_NL=BLOCKED, QF0212_G04_NL=BLOCKED, HISTORICAL_G03=FAIL_PRESERVED, HISTORICAL_WP14=HOLD_NOT_PROMOTED, and WHOLE_REPOSITORY_ARCHIVE_CLEARED=NO. If later implemented, the corrected route starts at MATURITY=EXPERIMENTAL and QUALIFICATION=NOT_ASSESSED. A numerical pass is not qualification or maturity promotion.

## References and provenance

1. WP08 read-only evidence and derivation: wp08_constitutive_feasibility_report.md, wp08_constitutive_feasibility_evidence.json, wp08_constitutive_options_comparison.md, wp08_constitutive_rescope_proposal.md.
2. WP00/WP01: wp00_baseline_scope_contract.json, wp01_shared_contracts.json.
3. Vitral & Hanna, “Quadratic-stretch elasticity,” Mathematics and Mechanics of Solids (2022), DOI: https://doi.org/10.1177/10812865211022417. Used for the distinction between right-stretch/Biot-strain constitutive quantities and the first Piola stress/rotational balance, not as validation of this plastic model.
4. Simo, Fox & Hughes, “Formulations of finite elasticity with independent rotations,” Computer Methods in Applied Mechanics and Engineering 95(2), 277–288 (1992), https://doi.org/10.1016/0045-7825(92)90144-9. Context for variational treatment of polar rotations; this design does not claim to implement that formulation.
5. Ortiz & Martin, “Symmetry-preserving return mapping algorithms and incrementally extremal paths: A unification of concepts,” International Journal for Numerical Methods in Engineering 28(8), 1839–1853 (1989), https://doi.org/10.1002/nme.1620280810. Context for incremental potentials, return-map symmetry, and tangent symmetry conditions.

**R1 disposition:** the equations and interfaces are specified for R2/R3; no numerical implementation has been run or validated by this design record.

One independent inline NumPy sanity calculation of the written spectral adjoint (seed 812, no production code imported) returned relative work residual \(1.35\times10^{-15}\), angular identity residual \(1.33\times10^{-16}\), PK2 skew \(2.31\times10^{-16}\), and Cauchy skew \(3.34\times10^{-16}\). This is only an algebraic one-sample design check; all future implementation/V&V checks remain NOT_RUN. A scratch basis mismatch in the first calculation was caught and corrected before these values were recorded.
