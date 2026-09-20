---
doc_id: DOC-029-WP09-OWNER-R3
revision: 1.0
status: owner-approved
applicable_version: 0.2.9-development
---

# WP09 Owner acceptance — HEX8 R3

The Owner accepts the WP09 R3 qualification for the explicitly bounded HEX8
scope only. The accepted evidence covers the H7/H8/H9 hierarchy, bounded
corotational J2 behavior, small local strain, the frozen mesh gates, the
independent material/affine-element observable recomputation, and the three
recorded replays.

This decision does not qualify TET4, HEX20, general finite-strain plasticity,
or a global independent FEM/Newton solve. Code_Aster correlation was not run
and is not claimed. Future element families require separate contracts and
qualification evidence.

## Decision

```text
OWNER_ACCEPTS_WP09_HEX8_R3 = YES
OWNER_AWARDS_WP09_POINTS = 8/8
WP09_OFFICIAL_POINTS = 8/8
GLOBAL_OFFICIAL_TOTAL_BEFORE = 70/100
GLOBAL_OFFICIAL_TOTAL_AFTER = 78/100
STATUS = APPROVED_WITH_LIMITATIONS
```

## Evidence lineage

- reviewed branch: `codex/wp09-hex8-formal-r3`
- reviewed source SHA: `397439f2d40d4a70375c6998b701428b4cd4cf40`
- contract SHA-256: `c2439513909cc7c640c96878ad6673b8b0377fea15cb16d269df43adae128b0d`
- policy code digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- H7/H8/H9 primary, reference, replay, and manifest artifacts are preserved
  under `qualification/0_2_9/wp09_hex8_formal_r3*`.

The historical R1/R2 evidence remains immutable and is not rewritten by this
decision.
