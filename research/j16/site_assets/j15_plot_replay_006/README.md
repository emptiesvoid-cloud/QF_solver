# J15 NAFEMS 13H complete plot replay

Prepared for review; **not published**. This figure replays archived J15
post-processing data and does not call a solver. It includes the 151 dense
frequency rows and the additional probe at the exact damped Navier peak
(2.375818178440047 Hz), for 152 plotted points total. All 152 remain
`QF_GUARD_REJECTED`; the J15 source run remains `PYTEST_FAILED`.

The frozen input and code provenance, statuses, output SHA-256, elapsed time
and resource observation are in `replay_manifest.json`,
`replay_attempt_receipt.json`, and
`research/j16/contracts/j15_plotter_replay_006.json`. The exact probe is a
separate diagnostic from the dense grid and is labelled by its preserved
route status. This artifact is a descriptive figure, not an accepted harmonic
response or a solver correlation.
