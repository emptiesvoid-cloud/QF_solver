# External Correlation Plan

Analytical references come first for clean cases. Code_Aster is the primary
optional external numerical oracle; CalculiX is SHOULD only when the element,
kinematics, integration and output measures are comparable. Abaqus is COULD
when a licensed, reproducible environment exists.

For every external cell, preserve geometry, mesh, material, boundary
conditions, load history, solver deck, observable mapping and source digest.
Compare histories where the method is path dependent. Numerical correlation is
not physical validation. Missing external software produces
`SKIPPED_EXTERNAL_UNAVAILABLE`, never PASS.
