---
doc_id: DOC-029-038
revision: 0.1
status: evidence
applicable_version: 0.2.9-development
---

# WP04-C2 — TET4 finer-mesh requalification

The C2 contract was frozen before result execution at
`715bdd655601508170d60c4715a53d658890bdb2`. It preserves the original C
failure (`a5c3031f6b28b00476e328daff4845a741a5c161`) and C1 diagnosis
(`f52465b008f0171c26386a7e24824f5d1cc9d807`). No production source,
formulation, tolerance, load, or maturity claim changed.

## Outcome

C2 is **UNRESOLVED_RESOURCE_LIMIT**. The required linear preflight used the
unchanged direct sparse route and reached C2-M3 = 64x32x32 (393,216 TET4,
approximately 212k DOFs) without returning a result after at least 5,976 CPU
seconds and an observed private working set of about 5.42 GB. The process was
interrupted while still active. Because the required linear preflight did not
complete, nonlinear C2-M1/M2/M3 were not started and no G04-10 pass decision
is possible. C2-M4 = 96x48x48 was not attempted.

The completed inherited same-benchmark linear values at 32 and 48 cells per
length are tip displacement `-0.1883825853`, `-0.1973397995`, energy
`4.7095646330`, `4.9334949866`, and representative stress `5547.19399`,
`5972.39967`. The 48-level changes remain 4.7548% (tip/energy) and 7.6652%
(stress) relative to the 32-level value; these are planning evidence only and
cannot qualify G04-10.

The predeclared physical benchmark and frozen limits remain unchanged:
displacement/reaction/energy ≤ 2%, representative stress ≤ 10%. No result is
reclassified as pass, and the original M1/M2/M3 C failure remains immutable.

## Governance

`G04-10 = UNRESOLVED_RESOURCE_LIMIT`; WP04 remains 0/12 and 29/100. TET4 and
HEX8 remain `RESEARCH_ONLY`. WP04-D is not authorized. Owner must decide
whether to provide a separately approved resource-capable execution plan,
accept TET4 as non-qualifiable for this scope, or re-scope the roadmap. No C3
mesh series is launched automatically.

Machine-readable evidence is in
`qualification/0_2_9/wp04_c2_tet4_requalification.json` and raw diagnostic
arrays are in `qualification/0_2_9/wp04_c2_tet4_requalification_raw.npz`.
