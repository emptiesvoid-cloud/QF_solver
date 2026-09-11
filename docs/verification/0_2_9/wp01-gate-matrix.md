---
doc_id: DOC-029-WP01-006
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 prospective acceptance gates

| Gate | Requirement | Frozen threshold |
| --- | --- | --- |
| G01 | One global Newton lifecycle | Zero alternate public/global lifecycles; adapters delegate. |
| G02 | Common composition | Four fixtures: material, geometric, penalty-contact, combined. |
| G03 | Rollback integrity | Exact pre-trial/post-rejection component and composite digest equality. |
| G04 | No silent commit | Zero contribution-level commits outside driver acceptance. |
| G05 | J2 preservation | Existing frozen tolerances plus relative error ≤ `1e-9`, absolute floor `1e-12`. |
| G06 | Geometric preservation | Existing frozen tolerances plus relative error ≤ `1e-9`, absolute floor `1e-12`. |
| G07 | Penalty-contact preservation | Existing frozen tolerances plus relative error ≤ `1e-9`, absolute floor `1e-12`. |
| G08 | Explicit deterministic failure | Two replays with identical terminal reason/retry class/diagnostic digest. |
| G09 | No maturity expansion | Zero changes to maturity records or public maturity claims. |
| G10 | Adapter integrity | Zero adapter-owned global Newton loops. |

These gates must be applied prospectively. A failure may not be cured by
loosening a threshold; a revised contract would require explicit review.
