# J16 NAFEMS 13H harmonic mesh comparison assets

These three files are byte-identical copies of the J16 mesh study 003, site-assets attempt 004 outputs. They were not regenerated in J17. The amplitude/phase figure marks rejected QF points with x markers and labels raw diagnostic curves; it does not promote those points to accepted results.

Source branch: work/0.3.0-j16-science
Source commit: 36b1bc4c67cdb9d990264864984856c306321f4d
Source asset manifest SHA-256: e6b38a599ab3284bd4e8a104ad645055e50f5bfee416ea16d43699ae640985e2

The source report documents a flat 10 m by 10 m MITC4 plate, 0.05 m thick, 100 Pa pressure toward -Z, Rayleigh damping, and the Navier thin-plate and published NAFEMS/Abaqus comparisons. Near-peak vectors remain rejected by the QF residual guard. Abaqus was not run locally.
