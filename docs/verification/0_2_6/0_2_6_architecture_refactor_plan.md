# Architecture Refactor Plan

The first refactor target is the verification boundary, not numerical kernels.
Existing flat oracle and campaign modules remain authoritative until one narrow
structural batch has baseline fingerprints, public API smoke and V&V smoke
protection. Each migration is mechanical (`git mv` plus import updates) and is
separate from behavior changes.

Target stable domains are `framework`, `oracles`, `metrics`, `campaigns` and
`reporting`. A new package is introduced only when at least three related
modules share ownership. Modules near the repository 700-line limit are
inventory candidates, not automatic refactor targets.

### Migration Guard

Before every migration: capture fingerprints, run focused tests and keep the
compatibility facade. After it: rerun the same checks, compare results and
record the evidence. Stop on numerical drift, changed output schema or import
breakage.
