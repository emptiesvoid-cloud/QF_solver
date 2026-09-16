# WP05-D formal requalification authorization

The Owner explicitly authorizes a formal WP05-D HEX20 requalification after
the read-only audit of the diagnostic H1/H2/H3 replay.

The authorized scope is limited to the frozen H1, H2 and H3 physical cases,
the exact reference-window candidate observable
`EXACT_REFERENCE_WINDOW_CLIPPED_HEX20_TENSOR_GAUSS_5`, an independent NumPy
reference, the contract replay, and all frozen qualification gates.

The historical WP05-D `FAIL_CLOSED` evidence remains authoritative and must
not be overwritten. The candidate changes only the numerical realization of
the representative stress post-processing window for straight-sided affine
HEX20 elements. It does not change the mesh, material, loads, boundary
conditions, thresholds, solver parameters, fallback policy, or production
mechanics.

The two policy identifiers must remain explicit and separate:

* frozen policy code digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`;
* runtime policy-binding digest: computed from the frozen execution settings
  and reported separately by the runner.

The formal run must stop fail-closed on any provenance or numerical gate
failure. WP05-E must not be started automatically by this authorization.

Machine-readable record: `qualification/0_2_9/wp05d_formal_requalification_authorization.json`.
