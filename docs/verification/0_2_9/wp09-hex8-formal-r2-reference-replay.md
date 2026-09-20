# WP09 HEX8 formal R2 — reference and replay review

## Status

```text
HEX8_SCOPE                         = PASS
STRICT_TOLERANCE                   = 1e-9
PRIMARY_H7_H8_H9_EVIDENCE          = PASS_HASHED
INDEPENDENT_REFERENCE              = PASS_INDEPENDENT_REFERENCE
DETERMINISTIC_REPLAY_H7_H8_H9     = PASS
M2_TO_M3_MESH_GATE                 = PASS
WP09_FORMAL_POINTS                 = 0/8
OWNER_REVIEW                       = PENDING
MERGE                              = NO
PUSH                               = NO
```

The package is a formal candidate only. The runner does not award points.

## What “independent reference” means here

The reference is a NumPy material-point and affine-element recomputation. Its
module is checked not to import `solveur.elements`, `solveur.materials` or
`solveur.core`. It validates the corotational/J2 constitutive and element
quantities, but it is not an independent global FEM/Newton solve.

Code_Aster was not used for this internal gate. A Code_Aster comparison would
be a separate external V&V activity because the current bounded corotational
J2 contract, load path and observable mapping would have to be translated and
frozen independently.

The HEX8 reference maximum relative error was `3.035292e-13`, below the
contract limit `1e-11`.

## Replay

One fresh production replay was run for each frozen level with the same HEX8
inputs, load path and tolerance `1e-9`:

| Stage | Level | Replay | Max relative difference against primary |
|---|---|---|---:|
| M1 | H7 | PASS | `0.000e+00` |
| M2 | H8 | PASS | `0.000e+00` |
| M3 | H9 | PASS | `0.000e+00` |

The comparison covers displacement, reaction, energy, von Mises, equivalent
plastic strain, free residual, force balance and moment balance.

## Mesh gate

The frozen M2→M3 comparison is:

```text
displacement = 3.048916 %   (limit 5 %)
reaction     = 0.000000 %   (limit 5 %)
energy       = 4.271186 %   (limit 5 %)
von Mises    = 3.678951 %   (limit 10 %)
```

All structural primary results also pass the strict equilibrium and envelope
gates. The historical H8/H9 runs at `1e-7` remain preserved; the strict runs
are the only evidence bound to this R2 candidate.

## Provenance

```text
CONTRACT_SHA256 = 271ad5cd182343ba9e03d9a5c3bdf1b7e8c27165e5c6c09bd47ef0f1ee701a9f
EVIDENCE_EXECUTION_SHA = 3d743f550186bab10cbe44669d49138597c936d8
H7_EXECUTION_SHA = a968a5857da7f1758e79827b78322e15edbadca5
H8_EXECUTION_SHA = e95021fb747f6411e42b55fd1b70c02354407d56
H9_EXECUTION_SHA = c8b3f1ea707ab73664068c7bae7c5d6373235ff5
POLICY_CODE_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
RUNTIME_POLICY_DIGEST = 895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

The raw primary hashes are frozen in the contract and rechecked before the
reference/replay package ran. The evidence manifest contains the campaign,
reference and replay artifacts; all listed hashes verify.

## Owner decision required

```text
WP09_CANDIDATE_STATUS = PASS_CANDIDATE
WP09_CANDIDATE_POINTS = 8/8
WP09_OFFICIAL_POINTS = 0/8
```

The Owner must decide whether to accept the bounded HEX8-only scope and its
limitations. This does not qualify the historical TET4 route, general finite
strain behavior, external-solver correlation, or a general nonlinear global
FEM claim.

## Evidence paths

- Contract: `qualification/0_2_9/wp09_hex8_formal_r2_contract.json`
- Campaign: `qualification/0_2_9/wp09_hex8_formal_r2_evidence/`
- H7/H8/H9 strict primary evidence:
  `qualification/0_2_9/wp09_hex8_accuracy_remediation_r3/`, `r2/`, `r1/`
