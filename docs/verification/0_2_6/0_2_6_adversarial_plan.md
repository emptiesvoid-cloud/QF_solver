# Adversarial Plan

Expected safe failures are distinct from numerical failures. Planned families
cover invalid connectivity, inverted elements, singular systems, NaN/Inf,
invalid material data, invalid time steps, solver failures and impossible
contact states. Every expected failure must fail closed with a structured
category and without state corruption.

Metamorphic checks cover numbering and element ordering invariance, rigid
translation where appropriate, load scaling, sign-invariant modes and
trial/commit/rollback reproducibility. Failures become anomaly records rather
than tolerance changes.
