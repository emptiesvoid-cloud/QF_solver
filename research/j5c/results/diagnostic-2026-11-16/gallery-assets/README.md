# J5B modal shape image for the future gallery

`j5b_qf_candidate_mode_shapes.png` plots the first four transverse vectors
stored in the 16×16 MITC4 J5B archive. It is a display of computed candidate
modes, not an independent validation result.

Each mode is normalized independently to its own maximum absolute `UZ` value.
The plotted sign is arbitrary. Modes 2 and 3 span the repeated (1,2)/(2,1)
pair, so their individual basis vectors can rotate or swap. The colors do not
show physical forced-response amplitudes.

J5B attempt `j5b-6bb4e32988af`, source `dc1315693715eb7322bd7e4647c2e36e635d4b0d`,
remains **INCONCLUSIVE** on all five meshes. This image does not change that
status and does not establish frequencies, residuals, or mass orthogonality.

Regenerate from the J5C worktree with:

```powershell
python scripts/j5c_archive_mode_gallery.py
```

The plot-only asset manifest records the archive, plotting script, output hash,
and the limitation that no solver or reference calculation is run by this
utility.
