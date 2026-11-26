# HEX8 EAS experimental route and exact diagnostic integration review

## Proposed local integration lot

Decision A. The lot is ready for local integration review of the opt-in
element and its optional residual diagnostic. The element remains
`EXPERIMENTAL / NOT_ASSESSED`. The static diagnostic is off by default.

The direct remote check of `refs/heads/0.3.0` returned
`c4de3ff6bf4549bf68d34652bcf6fb05e36f43c4`. This is the parent of the
tested code commit `00195b8ba46173ed573d425fbce4190e445bb8e1`.
The source head `b2f256be188b5e5c147801155211f6cec1ea6e25` differs from
the previously tested `795b96209a86ce85aeb68ac89e24ef57b60f1975` only
by the earlier wheel report. The new lot selects the runtime route
and element tests from `4d86ceb403c857603040599ce28cfc2af50926f7` and
the packaged diagnostic, extra and tests from `795b9620`. The
research runners, their policy and archive helpers, and their evidence
remain in the source history. The route relies on existing NumPy,
SciPy, the element infrastructure and the linear guard. The only added
package dependency is optional `psutil>=5.9` via `eas-diagnostic`.

## Review findings and corrections

- The EAS element is selected by its explicit type and has a distinct
  registry entry. The kernel uses six mean-free enriched strains, a locally
  condensed deviatoric block and mean divergence for volumetric stiffness.
  The recovered amplitudes are used in stress and energy postprocessing.
  The route is restricted to direct linear statics with a homogeneous,
  isotropic, small-strain mesh. Existing HEX8 and HEX8-SRI kernels are unchanged.
- The supervisor hashes copies of CSR values, indices and pointers, the
  right-hand side, candidate, dimensions, dtypes, and the binary64 threshold.
  The spawned worker recomputes the identity and the response is checked
  against it. Exact arithmetic compares squared norms for
  `||Ax-b||₂ / max(||Ax||₂, ||b||₂)` on the stored values. Undefined
  normalization, noncanonical CSR and invalid input are refused.
- The archive interface binds both NPZ byte streams to expected SHA-256
  values, which the caller obtains from a trusted manifest. It checks names,
  compressed and uncompressed sizes, and now checks each NPY header and its
  declared byte count against actual bytes before array loading. It expects
  the minimal numeric format with NPY v1 or v2 headers. A bad digest or
  incomplete layout returns `NOT_RUN / INCONCLUSIVE` before the guard.
- A response observed after the deadline can arrive between two polling
  iterations. The parent now checks the deadline after child exit before
  interpreting the response. Invalid resource limits and malformed
  response fields are refused. Both ends of the pipe close on exit.
- The genuine production guard runs first and a rejection rethrows the
  original exception. If the guard replay disagrees, or the supervisor
  returns no usable report, the supplement is `INCONCLUSIVE`. Even a
  matching exact PASS leaves the original rejection in force. The guard and
  its threshold of `1e-7` are unchanged.

## Tests and wheel

The selected source tests reported 60 passes for the EAS element,
compatibility and diagnostic, and 15 more for HEX8, HEX8-SRI and two
distributed load checks. Ruff passed for the new diagnostic and EAS
files checked. Compilation and Git whitespace checks passed.

The clean code commit produced a 1,728,912 byte wheel using
`python -m pip wheel --no-deps --no-build-isolation --wheel-dir <wheel-dir> .`.
The SHA-256 of `qf_solver-0.3.0-py3-none-any.whl` is
`4b8ebb25316e0a7675cc68245648d6d8e63fb1c2869ad055f3345816371b42cf`.

Two fresh Windows AMD64 Python 3.13.1 venvs installed the local wheel
with and without `[eas-diagnostic]`. Both used NumPy 2.5.5, SciPy
1.18.1, Matplotlib 3.11.2 and pytest 9.2.0. The extra installed psutil
7.2.2 and the base venv had no psutil. Both installations passed
`python -I -m pip check`. Module origins were checked against
`site-packages`, the installed wheel hash was checked against pip
metadata, and `research` was absent from both imports and wheel files.

From the external directory of copied test files,
`python -I -m pytest -q --import-mode=importlib` with the extra gave
73 passes in 12.80 s, with zero failures or skips. The base environment
ran the single `no_psutil` static route case and gave one pass. A real
spawned child exercises valid archive replay, exact PASS and FAIL,
timeout and forced interruption. The late observation regression uses
a deterministic process/clock double. Substituted and incomplete
responses and monitor errors use injected faults. The static tests
use synthetic systems and doubles for assembly, reduction and the
linear candidate. The accepted `SolveResult` test verifies the
postprocessor call with synthetic outputs. Separate element tests
exercise actual sparse assembly, enriched recovery and VTU output.

## Limits

The supervisor observes a deadline once synchronous startup returns.
RSS is sampled and process cleanup checks cover the direct
multiprocessing child. Strict Windows quotas and arbitrary OS
descendant cleanup are outside these checks. The wheel evidence is
specific to the stated Windows and Python versions. Global FEM,
mechanical qualification, other platforms and CI are `NOT_RUN`.
PYTEST_FAILED, J7 FAIL and J14 development PASS evidence is preserved.

The Git lot contains source, tests, package metadata and compact
documentation. It excludes raw archives and the research lineage.
Any future use of exact evidence to authorize a rejected candidate
requires a separate design and decision.
