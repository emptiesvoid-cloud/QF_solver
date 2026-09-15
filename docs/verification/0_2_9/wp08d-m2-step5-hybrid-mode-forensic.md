# WP08-D M2 step-5 hybrid stick/slip forensic

This is an independent diagnostic based on the committed contract-aligned M2
step-4 checkpoint. It enumerates all eight fixed stick/slip masks for the
stable normal active set [3, 7, 11]. It imports no production contact routine
and changes no production mechanics.

Exactly one mode is admissible: SSK.

- contact 3: stick, force norm 15.0905 below limit 18.4073;
- contact 7: stick, force norm 30.7730 below limit 36.2984;
- contact 11: slip, force norm 15.5905 equal to limit 15.5905;
- post-root normal set: [3, 7, 11];
- independent root residual infinity norm: 2.2753e-10.

The other seven masks are rejected. The contract-aligned production route
currently reaches the same qualitative SSK state during direct iteration but
does not converge it, then sends all closed pairs to an all-slip root. The
forensic result therefore identifies a missing hybrid stick/slip root route.

This is not a qualification pass and does not authorize a production mechanics
change, replay, or M3. A separate Owner-reviewed remediation scope is required.
