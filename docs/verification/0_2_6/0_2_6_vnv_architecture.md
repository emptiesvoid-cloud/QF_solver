# V&V Architecture

Authoritative definitions live in `qualification/0_2_6/case_registry.json`.
The registry validates identifiers and selection. `VnvRunner` executes only
READY cases whose JSON model is under `examples/`; it intentionally has no
arbitrary command field. PLANNED cases are visible but cannot run.

Each case result and manifest records source SHA, dirty state, UTC timestamp,
solver version, configuration, threshold policy, environment and digests.
Results stay runtime artifacts, while small definitions and manifests remain
versionable. External adapters are explicit, optional and must report an
unavailable tool as `SKIPPED_EXTERNAL_UNAVAILABLE`.
