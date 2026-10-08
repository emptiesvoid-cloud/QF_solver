# WP08-R2 — Internal-force verification

## Force equation

R2 implements the R1 adjoint of the right-polar stretch differential. Let `F=R U`, `A=R^T deltaF`, and solve the skew Sylvester equation `Omega U+U Omega=A-A^T`; then `deltaU=sym(A-Omega U)`. The local return produces symmetric Biot-conjugate stress `T_B` at `E_B=U-I`. In a principal basis of `U`, the adjoint `Pbar=L_U^*[T_B]` has diagonal entries `T_B,ii` and off-diagonal entries `2 lambda_i T_B,ij/(lambda_i+lambda_j)`. The first Piola stress is `P=R Pbar`.

Thus `P:deltaF=T_B:deltaU` for the implemented map. The exact polar rotation variation is included in `deltaU`; the adjoint's rotation-power term vanishes by objectivity. `Pbar U=U Pbar^T` is checked as the angular-momentum identity. The element internal force is integrated as `f_int[a,i]=sum_q w_q P[i,J] N[a,J]` using reference gradients. No artificial symmetrization of `P`, PK2, Cauchy, or an internal moment is performed.

## Independent oracles and frozen acceptance

R1 preregistered property-specific thresholds were used without modification:

- polar reconstruction, orthogonality, and stress-transformation identities: `1e-12`;
- polar differential versus independent central-difference plateau: `2e-7`;
- polar-adjoint virtual-work residual normalized by `W_char`: `5e-12`;
- raw PK2/Cauchy relative skew: `1e-10` (absolute skew used when norm is below 1 Pa);
- normalized angular-momentum/resultant-moment residual: `1e-9`;
- element force versus independently coded incremental-potential gradient: `2e-6` at the preregistered plateau.

Oracles comprise (a) independent NumPy/SVD right-polar calculations, (b) an independently solved polar Sylvester derivative plus SVD finite differences, (c) a separately authored tensor J2 radial return, and (d) a separately coded local incremental potential differentiated in nodal displacement. The latter checks elastic, active-plastic, and noncoaxial smooth-branch force gradients. The force oracle does not use `StressPostProcessor` or the production polar-adjoint helper to generate its expected gradient.

## Results

All bounded force, transformation, work, moment, and four-family element checks passed. The test coverage explicitly instantiates TET4, TET10, HEX8, and HEX20 and applies the family-specific integration rules already supported by those elements. The R2 evidence JSON stores the TET4 directional-gradient error sequence and noncoaxial skew/moment metrics.

The legacy noncoaxial Cauchy skew is reproduced as a legacy-path observation; the corrected raw stresses satisfy the frozen symmetry criteria. The internal-force difference from legacy is not hidden: the cited noncoaxial TET4 relative difference is `5.4769e-3`, an expected semantic change. No force calibration or empirical factor was introduced.

## What this does not verify

R2 does not provide a production global tangent. The existing legacy finite-difference tangent differentiates the legacy force/state path and cannot be assumed to differentiate corrected `P`. A local potential-gradient oracle verifies the corrected internal force for selected fixed-state smooth branches; it is not the algorithmic element/global tangent implementation, and it does not establish Newton convergence.

No claim is made about active-set switching derivatives, generalized Newton behavior, global equilibrium, checkpoint restarts, stress aggregation, or general finite-strain plasticity. These are explicitly held for R3 or outside the approved scope.
