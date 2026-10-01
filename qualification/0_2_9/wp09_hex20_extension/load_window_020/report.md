# WP09 HEX20 lower-load sensitivity diagnostic

Status: `PASS_DIAGNOSTIC_ONLY`

This diagnostic is separate from the frozen HEX20 load-scale 0.25 contract.

| Stage | Cells | Status | max ||U-I||F |
|---|---:|---|---:|
| H1 | 1 | PASS | 3.300842e-02 |
| H2 | 2 | PASS | 4.032905e-02 |
| H3 | 3 | PASS | 4.740368e-02 |

H2→H3 mesh deltas: `{"energy": 0.0876717427846366, "reaction_norm": 4.758943239497074e-11, "selected_displacement": 0.1087361797745023, "von_mises_max": 0.03762818562951062}`

This evidence is diagnostic only and does not modify the accepted HEX8 score or WP09 official ledger.
