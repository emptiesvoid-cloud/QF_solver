# J19 — bounded archived NAFEMS 13H harmonic replay

Contract: J19-NAFEMS13H-ARCHIVED-REPLAY-003.

Five SHA-pinned J16 impedance/RHS archives were solved again. No FEM assembly or local Abaqus execution was performed.
The JSON is atomically updated at each frequency and retains the solved vector before guard/exact post-processing.
Guard and exact represented-system statuses are separate; this is not a qualification of assembly or physical accuracy.

See replay.csv and replay.json for frequencies, amplitudes, phases, input hashes, residual statuses and timings.
The figure uses only discrete archived points; published NAFEMS/Abaqus peaks are peak-only context.
