# WP08-D M2 step-3 mode forensic and remediation

## Scope

This record covers a diagnostic-only reconstruction of the committed M2 step-2
state and an independent enumeration of the eight fixed stick/slip masks for
the observed normal set `[3, 7, 11]`.  It awards no WP08-D points and does not
authorize M3.

## Initial provenance finding

The first step-2 checkpoint run was invoked through `python scripts/...`.
On this host that command could resolve `solveur` from the user site-packages
directory rather than from this checkout's `src/` tree.  Its artifacts remain
preserved, but are not sufficient for a qualification claim.  The runner now
selects the checkout source explicitly and rejects a preloaded external
package.  A replacement local-source checkpoint is required before using the
forensic result as remediation evidence.

## Independent fixed-mode result

The preliminary enumeration used the preserved step-2 checkpoint as input and
used only an independently assembled TET4 elastic KKT system and a NumPy/SciPy
Coulomb return map.  It did not import or invoke production contact code.

| Mode | Result |
| --- | --- |
| SSS | admissible |
| SSK, SKS, SKK, KSS, KSK, KKS, KKK | rejected: slip return-map residual above `1e-9` |

For SSS, the tangential force norms at contacts 3/7/11 were respectively
3.7008, 10.6346 and 5.4339, while their Coulomb limits were 15.9345, 31.7740
and 14.1690.  The post-root normal set remained `[3, 7, 11]`.

## Corrective change

When a normal active-set transition removes or adds contacts, the prior
tangential classification was obtained from a different constrained system.
The solver now re-seeds each retained closed frictional pair with the elastic
stick predictor for the next KKT solve.  The unchanged return map immediately
returns a pair to slip if that trial is on or outside the Coulomb cone.

No mesh, load, material, friction coefficient, tangential stiffness,
tolerance, iteration limit, backend, or fallback policy was changed.

## Required follow-up

Run an authorized local-source M2 diagnostic through step 2, verify its
manifest and checkpoint hashes, rerun the independent enumeration on that
checkpoint, then perform a separately authorized M2 requalification.  M3
remains blocked pending that M2 evidence and Owner review.
