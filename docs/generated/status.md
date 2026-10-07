<div class="status-grid">
  <section class="status-panel"><h3>Project version</h3><span class="value">0.2.11</span><span>release status and citation identifiers are maintained in README and CITATION.cff</span></section>
  <section class="status-panel"><h3>Evidence status</h3><span class="value">ROUTE-SPECIFIC</span><span>0.2.8 registry remains historical authority; inherited nonlinear evidence and 0.2.11 experimental rotating routes are separately scoped; WP14 HOLD_NOT_PROMOTED and G03 FAIL_PRESERVED</span></section>
  <section class="status-panel"><h3>Distribution scope</h3><span class="value">SELECTED</span><span>wheel and sdist only; whole-repository source archives are not cleared</span></section>
</div>

The 0.2.8 published registry remains bounded at its declared historical
boundaries. The full-suite test inventory is recorded by the final Gate-E evidence; this generated overview deliberately does not hard-code a collection count. Inherited 0.2.10 evidence and experimental 0.2.11 evidence have separate decisions; this status panel does not assert publication or whole-repository G03 clearance.

| Scope | Maturity | Public boundary |
| --- | --- | --- |
| TET4 linear static | <span class="maturity stable">bounded</span> | Recorded elastic scope |
| TET4/TET10/HEX8/HEX20 small-strain J2 | <span class="maturity reinforced">qualified bounded</span> | Declared material and analysis scope |
| Modal, transient and harmonic | <span class="maturity route-dependent">route-dependent</span> | See the capability index for route-specific evidence |
| Frictionless contact | <span class="maturity experimental">experimental bounded</span> | Bounded node-to-triangle cases |
| Corotational J2 | <span class="maturity stable">qualified bounded</span> | Owner-accepted HEX8 route; large rotations with small local strain |
| Total-Lagrangian geometry | <span class="maturity route-dependent">audit with limitations</span> | Selected serial static TET4/HEX8; no maturity promotion |
| Coupled nonlinear static | <span class="maturity route-dependent">Owner-accepted bounded</span> | Selected TET4/TET10/HEX8/HEX20 cases; declared exclusions apply |
| WEDGE6 static | <span class="maturity stable">qualified bounded</span> | Approved documented static scope |
| PETSc/MPI linear static | <span class="maturity route-dependent">Owner-accepted bounded</span> | Two-rank cases with replicated input/root-side assembly; no scaling claim |
| Mixed distributed PETSc/MPI runtime (including nonlinear routes) | <span class="maturity not-validated">not validated</span> | No general nonlinear distributed evidence |
| Gyroscopic modal analysis | <span class="maturity experimental">experimental</span> | Straight circular BEAM2 shafts with centered rigid axisymmetric disks; dense serial QEP only |
| Campbell diagrams | <span class="maturity experimental">experimental</span> | Explicit complex-mode tracking; high-frequency ambiguity at 100 rad/s preserved; GYRO-06 is internal mesh-convergence evidence, not independent physical validation |
