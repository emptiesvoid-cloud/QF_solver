# WP08-R1 — Force and tangent specification

**Status:** equations frozen for implementation design; no source change and no numerical pass.

## A. Integration-point algorithm

Inputs are reference coordinates \(X_a\), nodal displacement \(u_a\), reference shape gradients \(N_{a,J}\), reference integration measure \(w_q\), and the immutable accepted material state \(\xi_n\). All tensors below are evaluated independently at every quadrature point.

1. Form \(F_{iJ}=\delta_{iJ}+\sum_a u_{ai}N_{a,J}\). Reject non-finite input and the existing inadmissible determinant condition \(J\le10^{-10}\).
2. Compute the proper right polar decomposition \(F=RU\). Verify \(R^TR=I\), \(U=U^T>0\), reconstruction residual, and the frozen \(\|U-I\|_F\le0.05\) cap.
3. Set \(E_B=U-I\). Do not rotate the accepted material state using the current/previous \(R\).
4. Evaluate the existing isotropic J2 return map from \((E_B,\xi_n)\), obtaining symmetric \(T_B\), algorithmic local tangent \(C_{\rm alg}=\partial T_B/\partial E_B|_{\xi_n}\), and detached trial state \(\xi_{n+1}^{\rm tr}\). Every nonlinear trial is based on \(\xi_n\), not a preceding Newton trial.
5. In a spectral basis of \(U\), form \(\bar P=L_U^*[T_B]\) by \(\bar P_{ii}=T_{ii}\), \(\bar P_{ij}=2\lambda_iT_{ij}/(\lambda_i+\lambda_j)\) for \(i\ne j\). Rotate the two reference indices back with \(V\), then set \(P=R\bar P\).
6. Assemble \(f^{\rm int}_{ai}=\sum_q w_qP_{iJ}N_{a,J}\). Return trial states and fields without mutating accepted state.
7. After global convergence only, commit the accepted material states once. On rejection, cutback, line-search rejection, or exception, discard trial state.

The J2 law is the same isotropic small-strain radial return applied to the bounded Biot stretch strain. The new element kernel must call/reuse the existing material update and must not implement an independent J2 law.

## B. Polar derivative and work identity

For an arbitrary perturbation \(\delta F\), set \(A=R^T\delta F\). Solve the skew Sylvester equation

$$
\Omega U+U\Omega=A-A^T,\qquad \Omega^T=-\Omega,
$$

then \(\delta U=\mathrm{sym}(A-\Omega U)\) and \(\delta R=R\Omega\). In a principal basis, \(\Omega_{ij}=(A_{ij}-A_{ji})/(\lambda_i+\lambda_j)\) for \(i\ne j\), and \(\delta U_{ii}=A_{ii}\).

The adjoint \(L_U^*\) is defined by \(T_B:\delta U=L_U^*[T_B]:A\). Its explicit spectral components are in the companion formulation record. This gives, for every perturbation,

$$
P:\delta F=T_B:\delta U,\qquad
\bar P U=U\bar P^T.
$$

The second identity is the angular-momentum condition for a simple (non-polar) continuum. It implies symmetry of both reconstructed \(S=F^{-1}P\) and \(\sigma=PF^T/J\). Never replace \(P\), \(S\), or \(\sigma\) by a symmetrized projection.

## C. Element algorithmic tangent

Let \(L_U:\delta F\mapsto\delta U\). On a smooth elastic or active-plastic return branch:

$$
\delta P=R\{\Omega\bar P+\delta\bar P\},\qquad
\delta\bar P=(D_U L_U^*[\delta U])[T_B]
+L_U^*[C_{\rm alg}:\delta U].
$$

This includes (i) the derivative of the rotation, (ii) the derivative of the polar-stretch adjoint with respect to \(U\), and (iii) the local algorithmic material tangent and hardening update. A consistent fourth-order operator \(A_{\rm alg}=\partial P/\partial F\) is obtained from this map and the polar differential. The element tangent is

$$
K_{ai,bk}^{\rm int}=\sum_qw_qN_{a,J}A_{{\rm alg}\,iJkL}N_{b,L}.
$$

Implementation may use analytic spectral/Frechet derivatives or automatic differentiation of the complete smooth branch, but must handle repeated/near-repeated stretches without differentiating arbitrary eigenvectors. The Sylvester equation and divided-difference/Frechet formulations are preferred at eigenvalue multiplicity. Any eigenvalue-based implementation must be basis-invariant within repeated eigenspaces.

The raw algorithmic tangent is the diagnostic result. Do not symmetrize it to obtain Newton input. Associative return from a smooth incremental potential implies a symmetric Hessian under the stated assumptions, but this is a property to test, not a reason to overwrite a computed skew. At yield switching points the classical derivative may be nonsmooth; specify and test the active-set/generalized derivative or use an explicitly justified semismooth Newton policy. The existing global Newton solver can be reused; its damping, line search, cutback, and convergence defaults are not part of this rescope.

## D. Independent directional reference

The acceptance reference independently differentiates the complete corrected force from a fixed accepted state:

$$
K_{\rm FD}v=
\frac{f_{\rm int}(u+h v;\xi_n)-f_{\rm int}(u-hv;\xi_n)}{2h}.
$$

Use a dimensionless direction normalized in Euclidean norm and a perturbation length based on element-local invariant scales, e.g. \(h_u=h_{\rm rel}L_{\rm char}\), where \(L_{\rm char}=V_0^{1/3}\) for a 3-D solid, not \(\max|X|\) or absolute origin. Evaluate a preregistered sequence \(h_{\rm rel}\in\{10^{-4},3\cdot10^{-5},10^{-5},3\cdot10^{-6}\}\); compare the analytic/AD tangent against the central-difference plateau and record truncation/roundoff behavior. At plastic branch switches use one-sided directional checks and do not claim a classical derivative.

The reference must use an independent implementation of the polar differential / constitutive return or an independently coded local incremental-potential gradient. Calling the same production helper twice is not an independent oracle. The force comparison is scaled by \(\max(\|f_{\rm ref}\|,\|f_{\rm obs}\|,F_{\rm char})\), with \(F_{\rm char}=\sigma_{\rm char}V_0^{2/3}\) and \(\sigma_{\rm char}=\max(\|T_B\|_F,E\|E_B\|_F,\sigma_y,1\text{ Pa})\), preventing a meaningless relative error near zero.

## E. Expected cost and diagnostics

The element currently evaluates the constitutive response once per point for force, then central-differences every nodal DOF and evaluates plus/minus states. The corrected closed-form/AD consistent tangent is expected to replace this \(2n_{\rm dof}\)-response pattern; actual cost is not claimed here. R2 records force and polar identities; R3 measures the final tangent and whole-element cost for each supported family.

Required raw diagnostics per tested state: \(\|P\|,\|T_B\|,\|U-I\|\), \(\det F\), \(\lambda_{\min},\lambda_{\max}\), polar residual, \(\|P F^T-(P F^T)^T\|\), \(\|S-S^T\|\), work-virtual residual, force finite-difference error by step, raw tangent skew, yield branch and state hash. A failed invariant is a failure, not a warning that can be cleared by output symmetrization.

## F. Stop boundaries

Stop and request a new rescope if the existing radial return cannot supply the local conjugate stress/algorithmic tangent for \(E_B\), if the state requires a multiplicative plastic deformation gradient, if the polar map is used outside the frozen local-strain domain, if an element family needs a new kinematic formulation, or if the corrected force requires changes to the global Newton algorithm beyond ordinary nonsymmetric/consistent tangent support.

WP09's general origin-invariant finite-difference robustness is not started by this specification. The corrected route's force derivative is a WP08-R3 dependency; any generic tangent framework or broader element/tangent hardening remains separately authorized work.
