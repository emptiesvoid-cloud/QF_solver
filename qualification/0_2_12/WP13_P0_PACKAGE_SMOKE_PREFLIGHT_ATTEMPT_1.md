# WP13 P0 package smoke controller preflight — attempt 1

**Classification:** `CONTROLLER_PREFLIGHT_FAIL_CLOSED`  
**Observed:** 2026-10-31 UTC  
**FEM executed:** no  
**Attempt reservations:** 0

The first preflight invocation used local controller commit
`3202161266ec064ffcc939e15dd0cce473232344`, controller SHA-256
`83dbd60bbc481ee7dbae90dd5052454508ec3da65e42039888d9b92a9a386571`, and
manifest SHA-256
`2dc2badf59c1a35aff44fcb5763eaac4e0e55b73857be878b660c3bd0430addb`.

Command:

```text
python scripts/wp13_package_smoke.py preflight --manifest qualification/0_2_12/wp13_p0_package_smoke_manifest_20261031_v1.json --expected-manifest-sha256 2dc2badf59c1a35aff44fcb5763eaac4e0e55b73857be878b660c3bd0430addb
```

Captured controller output:

```text
WP13 PACKAGE SMOKE STOP: [WinError 267] Nom de r�pertoire non valide
```

The controller had not created the configured evidence directory before
using it as a subprocess working directory. The stop occurred before package
probes, FEM, or ledger reservation. A follow-up filesystem check confirmed no
preflight report, evidence directory, or attempt ledger was created.

The runner was corrected to create the empty evidence directory before the
non-solving probes. On the corrected PR head
`e99703e5ed4ef90c030872f07b649fa44bee9f77`, controller SHA-256
`16df6eba0f902c332cace9e9a5624d1b8b59c3e051bfcc4063782123cc9a7f2f`, and
manifest SHA-256
`dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b`, the
no-FEM preflight and synthetic CLI-to-reservation check both passed. Their
report hashes are recorded in the package-smoke decision dossier. This
controller defect is not a solver or numerical result.
