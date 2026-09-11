---
doc_id: DOC-029-007
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 Owner decision log

## OD-029-01 — bounded J2 plus geometric formulation

**Status:** OPEN. Required before WP09 implementation or any public claim.

The Owner must select one bounded physical direction after reviewing the
stress/strain measures, state transport and required validation basis:

| Option | Direction | Default status before approval |
| --- | --- | --- |
| A | Corotational/large-rotation model with explicitly bounded small-strain J2 | Not selected |
| B | Existing `total_lagrangian_j2` research formulation | Research only |
| C | Proper finite-strain multiplicative plasticity, \(F=F_eF_p\) | Not selected; substantial new work |
| D | Defer public J2 plus geometry claim | **Default** |

No option is selected by the existence of code alone. The selected option must
receive a prospective constitutive/objectivity contract, tangent and
state-transport verification, bounded external correlation and failure limits.
