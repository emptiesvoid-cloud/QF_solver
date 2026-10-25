# Glossary

**Scope:** concise QF Solver usage; release-specific contracts take precedence.
**Revision:** 2026-10-25.

| Term | Meaning |
|---|---|
| FEM | Finite-element method: discretization of a continuum or structural model into elements and assembled degrees of freedom. |
| DOF | Degree of freedom. QF Solver maps model variables to a global DOF set; constraints and route-specific reductions can change the solved set. |
| MPC | Multi-point constraint coupling two or more DOFs through a linear relation. |
| RBE2 / RBE3 | Rigid-element constraint definitions exposed by the model/API. Their kinematic/weighting behavior is route- and contract-specific. |
| QEP | Quadratic eigenvalue problem. The rotating route solves a dense complex QEP associated with its signed-speed gyroscopic model. |
| MAC | Modal assurance criterion. In Campbell tracking, the repository uses a complex-mode association policy defined by its contract; this is not an operating-risk criterion. |
| WP | Work package. Numbering is release-specific; cite both release and WP identifier. |
| Gate | A decision boundary with stated scope, evidence and acceptance conditions. Passing a gate does not imply all project physics are qualified. |
| Oracle | Independent or defined reference used to judge an observable, such as an analytical solution, invariant, convergence target, or external implementation. |
| Provenance | Identifiable origin and context of source, model, mesh, environment, command, run and evidence. |
| Manifest | Structured declaration of a planned or executed campaign, its inputs, operations, environment, resources, and outputs. A prepared manifest is not authorization. |
| Checkpoint | Serialized solver state used for restart or recovery. Schema compatibility and state identity are separate from result serialization. |
| Maturity | Recorded development/qualification label such as EXPERIMENTAL or QUALIFIED_BOUNDED. Do not promote it based on code presence or a local test. |
| Bounded qualification | Accepted evidence limited to named configurations and exclusions; it is not general-purpose qualification. |
| Regression | Check that an identified behavior remains acceptable across a change. Its evidential strength depends on the oracle and exact source/input identity. |
| Scientific validation | Evidence that the model and numerical predictions are adequate for an intended physical use. A software test or external code correlation alone is not automatically validation. |
| Historical PASS | A recorded PASS tied to its historical manifest, source, inputs, environment and scope; not a result for current HEAD. |
