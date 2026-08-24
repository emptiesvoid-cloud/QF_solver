## Couverture technique regeneree

Cette table ferme la lacune documentaire en distinguant une preuve disponible d'un ecart V&V documente.
Un ecart documente n'est jamais transforme en validation mecanique.

- couples element-analyse declares : **40** ;
- contrats de chargement : **8** ;
- methodes correlees : **12** ;
- ecarts V&V explicites : **0**.

### Contrats de chargement

| Famille | Actions supportees | Documentation |
| --- | --- | --- |
| TET4 | nodal_load, pressure, surface_traction, gravity, body_force | `docs/elements/tet4/matrices_charges.md` |
| TET10 | nodal_load, pressure, surface_traction, gravity, body_force | `docs/elements/tet10/matrices_charges.md` |
| MITC4 | nodal_load, pressure, surface_traction, edge_traction, gravity, body_force | `docs/elements/mitc4/matrices_charges.md` |
| MITC3 | nodal_load, pressure, surface_traction, edge_traction, gravity, body_force | `docs/elements/mitc3/matrices_charges.md` |
| BEAM2 | nodal_load, beam_distributed | `docs/elements/beam2/interpolation_matrices.md` |
| SPRING_MASS | nodal_load, grounded_spring, concentrated_mass | `docs/elements/entites_discretes.md` |
| ORTHOTROPIC_SOLID | nodal_load, pressure, surface_traction, gravity, body_force | `docs/verification/orthotropic_static_extended_owner_review.md` |
| CONTACT | contact_normal, coulomb_regularized | `docs/elements/contact_sans_frottement.md` |

### Couples element-analyse et oracles

| Couple | Statut mecanique conserve | Oracle | Etat de preuve | Conclusion bornee |
| --- | --- | --- | --- | --- |
| TET4 / linear_static | `stable` | analytical | `available` | Affine patch, traction/compression, pressure, body force, membrane and Saint-Venant torsion. |
| TET4 / modal | `stable` | code_aster | `available` | Eigen residuals, first-mode oscillator reduction and same-mesh Code_Aster TETRA4 modes were accepted by the Owner on 2026-08-02. |
| TET4 / transient_newmark | `stable` | code_aster | `available` | Closed-form first-mode response, energy invariant and same-time-grid Code_Aster TETRA4 history were accepted by the Owner on 2026-08-02. |
| TET4 / harmonic | `stable` | code_aster | `available` | Static limit, resonance checks and same-frequency-grid Code_Aster TETRA4 response were accepted by the Owner on 2026-08-02. |
| TET4 / material_nonlinear_static | `owner_accepted_experimental_bounded_use` | analytical | `available` | Uniaxial J2 path and CalculiX comparison; bounded small-strain scope. |
| TET4 / geometric_nonlinear_static | `research` | code_aster | `available` | Total-Lagrangian structural paths correlated with Code_Aster within the reviewed scope. |
| TET10 / linear_static | `stable` | internal_reference | `available` | Affine, bending, torsion, curved geometry and h-convergence evidence; same-mesh external linear TET10 static correlation remains recommended. |
| TET10 / modal | `stable` | analytical | `available` | Consistent mass, modal residuals and bending mode convergence. |
| TET10 / transient_newmark | `stable` | code_aster | `available` | Internal first-mode response and a structural time-step study are complemented by the same-mesh Code_Aster TETRA10 Newmark history; accepted by the Owner on 2026-08-02. |
| TET10 / harmonic | `stable` | code_aster | `available` | Static limit, resonance checks, spatial frequency convergence and a same-mesh Code_Aster TETRA10 sweep were accepted by the Owner on 2026-08-02. |
| TET10 / material_nonlinear_static | `owner_accepted_experimental_bounded_use` | code_aster | `available` | The straight-bar monotone TET10/TETRA10 correlation was accepted by the Owner for experimental internal use. A re-entrant combined-load campaign also passes automatically, but its Owner review remains open; general maturity stays experimental. |
| MITC4 / linear_static | `stable` | code_aster | `available` | Patch, locking, Cook, Scordelis, pinched cylinder and same-mesh conical-cutout correlations; Code_Aster closes the resultant check. |
| MITC4 / modal | `stable` | code_aster | `available` | Consistent mass and ten-mode Code_Aster correlation. |
| MITC4 / transient_newmark | `stable` | analytical | `available` | Exact modal oscillator is the accepted temporal oracle; refined external structural correlation remains recommended. |
| MITC4 / harmonic | `stable` | published_benchmark | `available` | NAFEMS/theory and direct/modal-superposition checks within the reviewed band. |
| MITC4 / laminate_linear_static | `stable` | code_aster | `available` | ABD, ply stresses and bounded curved laminate comparisons; NAFEMS R0031 is the controlled external reference. |
| MITC4 / laminate_dynamic | `stable` | code_aster | `available` | Planar symmetric four-ply modal/Newmark/harmonic use is Owner-accepted as experimental and bounded. Dynamic curved shells, non-symmetric coupling, damage and delamination remain excluded; the 10 000 QUAD4 modal reservation remains open. |
| MITC3 / linear_static | `stable` | code_aster | `available` | Membrane, bending, hemisphere, Scordelis and pinched-shell evidence; active Code_Aster archive replaces obsolete versioned folder aliases. |
| MITC3 / modal | `stable` | code_aster | `available` | Modal invariants, free-free modes, curved-shell h-refinement, eigsh, same-mesh Code_Aster DKT correlation and dedicated 8x2/16x4/24x6 refinement are available; stable promotion remains subject to Owner review. |
| MITC3 / transient_newmark | `stable` | code_aster | `available` | First-mode time-history, energy, curved-shell time-step convergence, same-mesh Code_Aster DKT history and dedicated 8x2/16x4/24x6 refinement are available; stable promotion remains subject to Owner review. |
| MITC3 / harmonic | `stable` | code_aster | `available` | Static limit, resonance, curved-shell broadband stress output, same-mesh Code_Aster DKT sweep and dedicated 8x2/16x4/24x6 refinement are available; stable promotion remains subject to Owner review. |
| MITC3 / laminate_linear_static | `owner_accepted_experimental_bounded_use` | code_aster | `available` | The flat symmetric [0/90/90/0] affine membrane patch is correlated with Code_Aster. The separate curved projected static scope is Owner-accepted with recommendations. |
| MITC3 / laminate_dynamic | `owner_accepted_experimental_bounded_use` | code_aster | `available` | Planar symmetric [0/90/90/0] modal/Newmark/harmonic responses are externally correlated on the same TRIA3 mesh with Code_Aster DST. Curved projected orientation remains outside the dynamic scope. |
| MITC3 / laminate_linear_static_curved | `owner_accepted_experimental_bounded_use` | code_aster | `available` | The Owner accepted the same faceted curved geometry with Code_Aster DST/TRIA3 and projected global reference vector as an experimental bounded static scope with recommendations. Ply stress, S13, damage, delamination and curved dynamic use remain outside the evidence. |
| MITC3 / laminate_dynamic_thin_planar | `stable` | internal_reference | `available` | The stable declaration is documented for the thin planar symmetric laminate only; automated dynamic evidence and the pending Owner review remain traceable, while curved, non-symmetric, damped and damaged use stays excluded. |
| MITC3 / laminate_static_curved_mixed_transverse | `stable` | internal_reference | `available` | The stable declaration is limited to the documented faceted curved mixed/transverse sub-domain; the axial-complete observable remains bounded and no general curved-laminate extrapolation is claimed. |
| BEAM2 / linear_static | `stable` | analytical | `available` | Timoshenko closed form and Code_Aster POU_D_E test route. |
| BEAM2 / modal | `stable` | code_aster | `available` | Six-mode axial and slender-transverse comparisons were accepted by the Owner on 2026-08-02. |
| BEAM2 / transient_newmark | `stable` | code_aster | `available` | Same mesh/time-grid axial and slender-transverse histories were accepted by the Owner on 2026-08-02. |
| BEAM2 / harmonic | `stable` | code_aster | `available` | Same-mesh axial and slender-transverse frequency responses were accepted by the Owner on 2026-08-02. |
| SPRING_MASS / linear_static | `stable` | code_aster | `available` | Grounded spring displacement. |
| SPRING_MASS / modal | `stable` | code_aster | `available` | Single-degree-of-freedom frequency is externally correlated and was accepted by the Owner on 2026-08-02. |
| SPRING_MASS / transient_newmark | `stable` | code_aster | `available` | Same time-grid transient response is externally correlated and was accepted by the Owner on 2026-08-02. |
| SPRING_MASS / harmonic | `stable` | code_aster | `available` | Same frequency-grid response is externally correlated and was accepted by the Owner on 2026-08-02. |
| CONTACT / linear_static | `owner_accepted` | code_aster | `available` | Bounded small-sliding normal-contact scope. |
| CONTACT / frictional_static | `experimental` | code_aster | `available` | Saturated sliding is correlated; adhesion remains non-comparable. |
| MITC4 / orthotropic_homogeneous_ply | `stable` | internal_reference | `available` | The stable declaration is limited to the homogeneous orthotropic one-ply shell domain and documented material orientations; it is not a ply-by-ply composite qualification and curved harmonic diagnostics remain excluded. |
| ORTHOTROPIC_SOLID / linear_static | `stable` | internal_reference | `available` | TET4/TET10 homogeneous orthotropic static behavior is covered by the controlled review and external-correlation test route; the scope excludes ply-by-ply composites, damage and singular stress acceptance. |
| ORTHOTROPIC_SOLID / modal | `stable` | internal_reference | `available` | The stable declaration is limited to the documented homogeneous orthotropic modal domain with the recorded mass and orientation conventions; nonlinear, damaged and ply-by-ply composite behavior remain excluded. |
| ORTHOTROPIC_SOLID / transient_newmark | `stable` | internal_reference | `available` | The stable declaration is limited to the documented homogeneous orthotropic Newmark domain with the recorded time-step and mass assumptions; nonlinear, damaged and ply-by-ply composite behavior remain excluded. |

### Correlation des methodes

| Methode | Base de comparaison | Preuve |
| --- | --- | --- |
| `direct` | assembled residual and energy balance | `tests/unit/test_solver.py` |
| `cg` | direct sparse solution | `tests/unit/test_solver.py` |
| `minres` | direct sparse solution | `tests/unit/test_solver.py` |
| `gmres` | direct sparse solution | `tests/unit/test_solver.py` |
| `bicgstab` | direct sparse solution | `tests/unit/test_solver.py` |
| `modal` | eigen residual, M/K orthogonality and analytical/external frequencies | `tests/unit/test_analysis_features.py` |
| `newmark` | closed-form oscillator, energy and external histories | `tests/unit/test_analysis_features.py` |
| `harmonic` | zero-frequency static limit, phase and external sweeps | `tests/unit/test_analysis_features.py` |
| `newton_j2` | uniaxial return mapping and external material paths | `tests/verification/test_j2_material_vnv.py` |
| `arc_length` | elastica reference; structural breadth remains experimental | `tests/unit/test_elastica_reference.py` |
| `total_lagrangian` | Code_Aster and CalculiX structural paths | `qualification/reviews/tet4_total_lagrangian_structural_v2_2026-07-18.json` |
| `large_model` | SciPy/PETSc small-model equivalence and MPI diagnostics | `tests/integration/test_large_model.py` |

### Vues comparees et convergences

![Convergence structurelle TET10.](../assets/generated/content_closure/tet10_structural_convergence.png){ .result-figure }

*Convergence structurelle TET10. Empreinte SHA-256 : `577d9384ca2c54d84af899fe6355c9453899d6e5a675f51b6b8dafa16fee91bd`.*

![Deformee CalculiX C3D10 de reference.](../assets/generated/content_closure/tet10_calculix_deformation.png){ .result-figure }

*Deformee CalculiX C3D10 de reference. Empreinte SHA-256 : `ce463693e78cc14e99ccd8a20b665f2476925cd2d94329072ddfc5393b32ce02`.*

![Panneau conique ajoure QF_solver.](../assets/generated/content_closure/mitc4_conical_qf_deformation.png){ .result-figure }

*Panneau conique ajoure QF_solver. Empreinte SHA-256 : `0a80a6ed13678f33811c20dc69514063212e78573a34ce43ec78855ffb7c5749`.*

![Panneau conique ajoure CalculiX.](../assets/generated/content_closure/mitc4_conical_calculix_deformation.png){ .result-figure }

*Panneau conique ajoure CalculiX. Empreinte SHA-256 : `912e3e8b1e1abf3d4453d1336a6931f2c1a4606fcbde9157444ee92d0f40150e`.*

![Frequences MITC4 et Code_Aster.](../assets/generated/content_closure/mitc4_modal_code_aster_frequencies.png){ .result-figure }

*Frequences MITC4 et Code_Aster. Empreinte SHA-256 : `d880cd9797997c3300c0eef7ef289e2f6e3eba6f126bca0674a44baca7d3c62e`.*

![Hemisphere MITC3, vues QF_solver et Code_Aster.](../assets/generated/content_closure/mitc3_hemisphere_qf_code_aster.png){ .result-figure }

*Hemisphere MITC3, vues QF_solver et Code_Aster. Empreinte SHA-256 : `8230fa9f036fd09120c1b2cd8b15eee942a3bad33fba1bc62a540de0d3763d76`.*

![Convergence de l'hemisphere MITC3.](../assets/generated/content_closure/mitc3_hemisphere_convergence.png){ .result-figure }

*Convergence de l'hemisphere MITC3. Empreinte SHA-256 : `2a77ec2a35ba0966eca3e689ac72da4fcdd1e916b41c469615adaf7e2a97883d`.*

![Convergence composite NAFEMS/Code_Aster.](../assets/generated/content_closure/composite_nafems_convergence.png){ .result-figure }

*Convergence composite NAFEMS/Code_Aster. Empreinte SHA-256 : `3dfca83b0833bc7d94056b1eab88226816a01e1b306c01c7f9b786381844331f`.*

![Equerre orthotrope QF_solver.](../assets/generated/content_closure/orthotropic_lbracket_qf.png){ .result-figure }

*Equerre orthotrope QF_solver. Empreinte SHA-256 : `df3ed2f05fe3dd100658eae27b362d556e91906d549056f6d40be809d5ad2d9f`.*

![Equerre orthotrope Code_Aster.](../assets/generated/content_closure/orthotropic_lbracket_code_aster.png){ .result-figure }

*Equerre orthotrope Code_Aster. Empreinte SHA-256 : `3a18ce8e78cdab4876f7f20f7c3a975c091235579c728e64160fb780a7802cdf`.*

![Equerre orthotrope CalculiX.](../assets/generated/content_closure/orthotropic_lbracket_calculix.png){ .result-figure }

*Equerre orthotrope CalculiX. Empreinte SHA-256 : `e4f642beff0f8e4e9a160885ddfe9dc974f58f4ff6b571596334c93adcf156a2`.*

![Contraintes Total-Lagrangian comparees a Code_Aster.](../assets/generated/content_closure/tet4_tl_code_aster_stress.png){ .result-figure }

*Contraintes Total-Lagrangian comparees a Code_Aster. Empreinte SHA-256 : `701e36818b0ba8b12644f70464e7f387599efd5fe8ae6df78c315784c76814d9`.*

![Contact normal compare a Code_Aster.](../assets/generated/content_closure/contact_code_aster_comparison.png){ .result-figure }

*Contact normal compare a Code_Aster. Empreinte SHA-256 : `bfa3dd28ab41ab2e76b6083ed8fdd7078af12aa04ae9ec26cd50de442856c819`.*

![MITC3+ modal, Newmark et harmonique compares a Code_Aster DKT.](../assets/generated/content_closure/mitc3_dynamic_code_aster.png){ .result-figure }

*MITC3+ modal, Newmark et harmonique compares a Code_Aster DKT. Empreinte SHA-256 : `de92d228e8134e5e1ebc80800a83479bda94efd7fe2c9612db8ead0faa9778fa`.*

![TET10 modal, Newmark et harmonique compares a Code_Aster TETRA10.](../assets/generated/content_closure/tet10_dynamic_code_aster.png){ .result-figure }

*TET10 modal, Newmark et harmonique compares a Code_Aster TETRA10. Empreinte SHA-256 : `d7a02003b8d23213b36c92c5808a88c86b0d343424cef66963ff41f74351a9f7`.*

![BEAM2 transverse modal, Newmark et harmonique compares a Code_Aster POU_D_E.](../assets/generated/content_closure/beam2_transverse_dynamic_code_aster.png){ .result-figure }

*BEAM2 transverse modal, Newmark et harmonique compares a Code_Aster POU_D_E. Empreinte SHA-256 : `283c62ac36c44ecf7169eaf1c7ea5aea52b59287d015180e7c7c75fa2f454957`.*

![TET4 modal, Newmark et harmonique compares a Code_Aster TETRA4.](../assets/generated/content_closure/tet4_dynamic_code_aster.png){ .result-figure }

*TET4 modal, Newmark et harmonique compares a Code_Aster TETRA4. Empreinte SHA-256 : `701e36818b0ba8b12644f70464e7f387599efd5fe8ae6df78c315784c76814d9`.*

![BEAM2: QF_solver et Code_Aster.](../assets/generated/content_closure/beam2_code_aster_dynamic.png){ .result-figure }

*BEAM2: QF_solver et Code_Aster. Empreinte SHA-256 : `78c936387d1c39e1b3750514755f6e0a1e7cf36f424071a516653d73e9434907`.*

![Ressort et masse concentree: QF_solver et Code_Aster.](../assets/generated/content_closure/discrete_code_aster_dynamic.png){ .result-figure }

*Ressort et masse concentree: QF_solver et Code_Aster. Empreinte SHA-256 : `93e30e9f5cf4efa0df79677c95f8e5219abd1c77281ad8e339cf6460931c0747`.*

### Ecarts V&V maintenus ouverts


Ces ecarts ne bloquent pas la lisibilite du manuel, mais interdisent toute extrapolation de maturite.
