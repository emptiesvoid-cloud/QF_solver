# QF Solver 0.2.11 — WP03 V&V, data and documentation foundation

**Status:** prospective foundation; it does not qualify a capability or alter a historical result.

## Scope and preservation boundary

WP03 extends the existing `solveur.verification.v2` harness and adds a small
public-record projection. It does not introduce a parallel campaign runner.
Existing 0.2.6 registries, manifests, results, policies and decisions remain
readable and unchanged. Existing V&V-v2 schema-1 cases and evidence remain
readable; their legacy expected-failure semantics are retained only for those
historical records. New campaign catalogs must explicitly load as case schema
2, and each case must declare `expected_failure` as either `null` or a
structured contract. No solver formulation, numerical tolerance, maturity, qualification result,
G03 status or WP14 decision changes in this work package.

The 0.2.6 command-line runner cannot establish the full identity needed for a
safe reuse. If `--resume` finds an existing result, it now raises a `ValueError`
with an explicit `REFUSE_RESUME` diagnostic instead of reusing an output on
source SHA alone. The previous file is left byte-for-byte unchanged. An explicit
`resume=False` starts a new execution; the strict schema-2 resume assessor is available for prospective
records once the caller supplies their complete identity and artifact bytes.

## Execution identity

Case schema 2 has a required `execution_identity` block and an explicit
`expected_failure` declaration. The runner combines
that declared block with the actual case contract, model input, oracle,
observables, expected-failure contract, tolerance values and executed source
SHA. The canonical identity schema is version 1. It binds:

- full source commit SHA and case-contract version;
- resolved-unit case definition and model/input data;
- mesh, material, boundary conditions, loads and actual input-file digests;
- solver settings and resolved overrides;
- oracle/reference identity and reference-file digests;
- tolerance policy and metric definitions;
- relevant package/tool and numerical-environment versions;
- a rotation-configuration object reserved for future gyro cases (empty for
  current non-rotating cases; no gyro behavior is implemented here).

Input files are represented by logical role and identifier, byte length,
SHA-256, provenance kind, availability classification and optional public
identifier. Digest and byte length are both null only for explicitly missing
or optional-unavailable content; no placeholder hash is fabricated.
`InputFileIdentity.from_bytes` calculates the digest from the bytes read by the
caller. Absolute local paths and `file://` URIs are rejected from
identity/public provenance; the storage locator remains outside the record.
Units must already be resolved. Non-finite numbers, non-JSON values, unknown
identity fields and duplicate logical file identifiers fail closed.

`ExecutionIdentity.execution_key()` hashes deterministic UTF-8 JSON with
sorted object keys, stable compact separators and a domain/version prefix.
Order is retained for scientific sequences and normalized for the input-file
set. File availability labels and local operational metadata do not enter the
scientific key; file role, logical identity, size and actual bytes' digest do.
Timestamps, output directories and temporary paths are out-of-band
`operational_context`, never silently filtered from scientific case data. A
scientifically meaningful field named `timestamp`, for example, remains in
the identity if it is part of the declared case definition.

## Safe resume and replay

`SafeResumeRecord` is a versioned, path-free record containing the execution
key and every required result artifact's logical identifier, SHA-256 and byte
length; at least one result artifact must be declared. `assess_safe_resume`
returns `REUSE` only when the schema is declared
compatible, the current key matches, and every required artifact exists as
bytes with the recorded length and digest. An identity mismatch, missing
artifact or corrupt artifact returns `REEXECUTE`; a malformed record, invalid
key or incompatible schema returns `REFUSE_RESUME`. Callers must not treat
anything except `REUSE` as permission to consume old output. V&V-v2 replay
also rejects a schema-2 record with a missing or mismatched execution key
before rerunning its executor.

Schema-1 0.2.6 results contain no complete execution key and are not adapted
into one by guessing. They remain readable as historical evidence but are not
eligible for safe resume. This explicit no-reuse boundary avoids claiming that
an old source-only key proves the identity of its scientific inputs.

## Expected failures

Case schema 1 remains readable with its historical free-text
`expected_failure` field. Prospective schema-2 cases instead require a
structured object: `expected_stage`, fully qualified `expected_error_type`,
and exact `expected_reason`, with optional `expected_error_code` and
`optional_message_pattern`. A schema-2 expected failure passes only if all
declared fields match the exception actually observed. An unrelated exception
does not satisfy the contract; absent stage/code/reason is not inferred from a
substring. An unexpected success remains `FAIL`. Optional-dependency and
resource-limit outcomes remain `SKIPPED_EXTERNAL_UNAVAILABLE` and
`RESOURCE_LIMITED`, never expected-failure passes.

## Provenance and availability

Provenance kind (`REPOSITORY`, `GENERATED`, `EXTERNAL_VERSIONED`, `LOCAL_ONLY`,
`MISSING`, `RECONSTRUCTED`, `OPTIONAL`) is distinct from evidence availability
(`AVAILABLE_AND_REPRODUCIBLE`, `AVAILABLE_HISTORICAL_ONLY`,
`AVAILABLE_LOCAL_ONLY`, `RECONSTRUCTED`, `OPTIONAL_DEPENDENCY`, `MISSING`).
Availability is not a numerical verdict: a numerical `PASS` paired with
`AVAILABLE_LOCAL_ONLY` remains local-only and is not represented as fully
reproducible. Actual content hashes and sizes are recorded where bytes are
available; absent bytes are classified, not fabricated.

Internal execution/storage details are not copied wholesale into public
records. `PublicBenchmarkRecord` is an allowlisted projection containing
benchmark/source/key, numerical status, metrics, limitations, content-addressed
public provenance, evidence availability, an explicit maturity decision and
its authority/record ID, plus a public evidence link. Unknown fields and local
absolute paths are rejected. `render_public_benchmark` emits deterministic
Markdown. The caller must supply the maturity decision; numerical PASS never
derives or promotes it. This is a reusable projection mechanism for a few
high-value future benchmark summaries, not a repository-wide documentation
rewrite or generator.

## Historical schemas and WP02 finding

The case loader remains a compatibility reader for v1 and v2. New catalogs use
`load_prospective_cases`, which rejects any case not explicitly marked schema
2. The 0.2.6 schema and tolerance policy are not rewritten, and no old record
is migrated in place. If old data is ever needed in a new in-memory workflow,
it must pass an explicit adapter; its original file and hash remain untouched.

WP02 found that common compatibility preflight does not separately inspect
discrete entities in a mixed finite-element/discrete model. WP03 records this
as a future route-local fail-closed validation requirement for WP05 and binds
the location in the contract. This package adds no model-preflight behavior,
no disk type and no gyro check.

## Validation and foundation gate

The focused WP03 tests cover deterministic identity, changed mesh/material/
solver/tolerance/reference/file bytes, exclusion of out-of-band timestamps and
paths, schema-2 expected-failure matching, safe-resume mismatch/missing/
corrupt-artifact rejection, legacy schema/evidence reading, public projection
stability and private-path rejection, and the 0.2.6 resume refusal. Required
repository workflows are reported separately on the exact WP03 commit. A
green infrastructure test establishes only this data-contract foundation; it
does not qualify any mechanics capability or close QF0211-G07's later final
documentation/V&V gate.
