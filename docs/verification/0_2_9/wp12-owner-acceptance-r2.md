# WP12 Owner acceptance — bounded Code_Aster correlation

Decision date: 2026-09-23

Decision ID: `OD-029-WP12-CODE-ASTER-R2-01`
Status: **ACCEPTED WITH LIMITATIONS — 4/4**

## Owner decision

The Owner accepts the frozen WP12 R2 external-correlation perimeter and its
documented limitations, awards **WP12 = 4/4**, and authorizes the official
ledger update, integration into `0.2.9-unified-nonlinear`, and push of the
reviewed lineage.

The global official total changes from **90/100 to 94/100**. This decision
does not alter the contract, thresholds, raw results, or prior decisions.

## Evidence basis

WP12 R2 compares the bounded linear-static results for TET4, HEX8, TET10, and
HEX20 with Code_Aster 18.1 on the same frozen discrete models. The contract,
74-file raw manifest, final audit, and final decision record are preserved in
the repository. All 74 R2 manifest entries were independently rehashed during
this closure; sizes and SHA-256 values match.

The supplementary R4 gallery audit reports **864/864 PASS_CANDIDATE** cases
(1,008 cumulative with the preceding R3.6 cases), across six topologies,
three material parameter sets, four element families, three longitudinal
mesh levels, and four load cases. Its 14,692 raw files (243,014,078 bytes)
remain local and ignored by Git; the contract, manifest, summaries, and
audits are versioned. External archival of the large raw gallery is deferred
to WP16. R4 is supplementary evidence and is not required to reinterpret or
change the R2 point allocation.

## Accepted scope and limitations

- Same-mesh numerical correlation for the frozen linear-static cases; this is
  not experimental validation or proof of general physical accuracy.
- R2 covers the bounded single-element/family cases and observables in its
  frozen contract; R4 adds the stated model gallery but refines only the
  longitudinal direction at H1/H2/H3.
- No general mesh-convergence, stress-field equivalence, nonlinear material,
  geometric-nonlinear, contact, friction, dynamics, buckling, or MPI/scaling
  claim is made.
- The independent audit recomputes observables from raw data; it is not a
  second independent FEM/Newton implementation.
- Large R4 raw files are not in Git pending the planned WP16 archive; their
  local manifest and audit hashes were verified at this decision.
- Broader validation and additional physical/nonlinear comparisons remain
  future work, including the planned 0.3 validation program.

## Immutable provenance

```text
GOVERNING_BRANCH_BEFORE_INTEGRATION = 0.2.9-unified-nonlinear
GOVERNING_SHA_BEFORE_INTEGRATION = 754664836c0e30232d38b31e21c3d98e4b3092bd
WP12_R2_CONTRACT_SHA256 = f6154660635670c026354429894c9c7a6f7fa6d8bd6849edf44717a4bd43824a
WP12_R2_MANIFEST_SHA256 = 7a912a795bd57db6505ae100dd77a8480d3bf41a1229fd39644c298b294c4e8c
WP12_R2_AUDIT_SHA256 = 0be63ce3f98e7e785f0cdff8fda94b4495d4d95f5ae0ee50c5809ad181acbdcf
WP12_R2_FINAL_SHA256 = f81b09b5007f9b761ced253e5e7a81003211441d29a75c1939ea9efb24c8cb96
WP12_R4_EXECUTION_SHA = c3c52449eb41e9b5a79e98f35b4bdb5591ba6980
WP12_R4_CONTRACT_SHA256 = 7588d0962776e02fe4ffba83ccc1611afbb5d606bd502c51d8f544954bc48ef2
WP12_R4_MANIFEST_SHA256 = 02b4c6a799835dd6908a2ea297d11ad86d27e22947fdb778ab44af7403a9980d
WP12_R4_AUDIT_SHA256 = 50ba73ec784452931b000ca750f4885c1eb63acb3510ffb4d8296b7e0db0a8c5
WP12_R4_EVIDENCE_COMMIT = fe93a6a64caa04c13c4e8c63d05f61bb711687ac
```

## Authorization and ledger

```text
OWNER_ACCEPTS_WP12_R2_EXTERNAL_CORRELATION = YES
OWNER_ACCEPTS_WP12_LIMITATIONS = YES
OWNER_AWARDS_WP12_POINTS = 4/4
OWNER_AUTHORIZES_LEDGER_UPDATE = YES
OWNER_AUTHORIZES_GOVERNING_INTEGRATION = YES
OWNER_AUTHORIZES_GOVERNING_PUSH = YES

WP12_POINTS_BEFORE = 0/4
WP12_POINTS_AFTER = 4/4
GLOBAL_TOTAL_BEFORE = 90/100
GLOBAL_TOTAL_AFTER = 94/100
```

Historical R1 launch failure and all later blocked/failed attempts remain
preserved and are not reclassified by this acceptance.
