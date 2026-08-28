# Risk Register

| ID | Risk | Severity | Mitigation | Gate |
| --- | --- | --- | --- | --- |
| `RISK-026-001` | Planned cases are mistaken for completed evidence. | high | READY/PLANNED state and runner exclusion | `026-G03` |
| `RISK-026-002` | A V&V refactor changes numerical behavior or public API. | high | baseline fingerprints and focused API smoke | `026-G00/026-G14` |
| `RISK-026-003` | External tool absence is represented as a pass. | high | explicit SKIPPED_EXTERNAL_UNAVAILABLE outcome | `026-G13` |
| `RISK-026-004` | Large artifacts obscure source history and inflate clones. | medium | artifact policy and digest-first summaries | `026-G01` |
| `RISK-026-005` | Performance comparisons use incompatible hardware or one noisy sample. | medium | hardware metadata, repeated medians and profile bands | `026-G12` |
| `RISK-026-006` | Research paths are promoted by test count alone. | high | claim matrix and Owner-only maturity decision | `026-G15` |
