<div class="status-grid">
  <section class="status-panel"><h3>Release</h3><span class="value">0.2.8-development</span><span>release preparation; not published</span></section>
  <section class="status-panel"><h3>Qualification</h3><span class="value">BOUNDED</span><span>declared 0.2.8 scope; WP13-01C not validated</span></section>
  <section class="status-panel"><h3>Test inventory</h3><span class="value">2349</span><span>local collection at documentation freeze</span></section>
  <section class="status-panel"><h3>Source revision</h3><span class="value">generated at build</span><span>controlled source required</span></section>
</div>

The active public scope is bounded at its declared 0.2.8 boundaries. The 0.2.8
release remains in preparation and has not been published. Historical planning
snapshots and pre-release audit records remain available in the verification
archive and do not define the current release.

| Scope | Maturity | Public boundary |
| --- | --- | --- |
| TET4 linear static | <span class="maturity stable">bounded</span> | Recorded elastic scope |
| TET4/TET10/HEX8/HEX20 small-strain J2 | <span class="maturity reinforced">qualified bounded</span> | Declared material and analysis scope |
| Modal, transient and harmonic | <span class="maturity reinforced">supported with limitations</span> | Route-specific evidence |
| Frictionless contact | <span class="maturity reinforced">supported with limitations</span> | Bounded node-to-triangle cases |
| WEDGE6 static | <span class="maturity reinforced">qualified bounded</span> | Approved documented linear-elastic static scope |
| Structured TET4 PETSc/MPI | <span class="maturity reinforced">supported with limitations</span> | Recorded workloads and environments only |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture foundation only; two-rank force balance and three-rank/partition gates remain failed |
