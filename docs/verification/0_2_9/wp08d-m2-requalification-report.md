# WP08-D M2 requalification after stick-predictor remediation

The authorized M2 production requalification completed with the checkout
source selected explicitly by the runner.

- production status: `PASS`
- accepted increments: `7/7`
- fallback: `0`
- contact active set: three contacts
- final tangential state: contacts 3, 7 and 11 are `slip`; remaining contacts
  are `open`
- active-set iterations by increment: `1, 1, 4, 4, 4, 4, 1`
- force equilibrium relative error: `2.359249378146216e-14`
- moment equilibrium relative error: `4.591631339243615e-14`
- evidence-manifest hashes: `PASS`

This run verifies the corrected production route through the complete frozen
M2 load history.  It did not run an independent reference, replay, M3, or a
full repository suite.  Therefore it remains requalification evidence only;
it does not by itself award WP08-D points.
