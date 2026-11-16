# J5C contract errata

## ER-001 — author attribution for DOI 10.1137/0521030

The pre-execution contract
`independent_modal_postprocess.json` (SHA-256
`465a5a6a7ef0a5c3909d9de15f52bf686ac1fd8b33f521d1fe78228be327c3f6`)
records the correct title and DOI for *The Plate Paradox for Hard and Soft
Simple Support*, but gives the wrong authors as D. N. Arnold and R. S. Falk.

The publisher's SIAM record identifies the authors as **I. Babuška and
J. Pitkäranta**, *SIAM Journal on Mathematical Analysis*, 21(3), 551–576
(1990), DOI [10.1137/0521030](https://doi.org/10.1137/0521030). The online
publisher record is available at
<https://epubs.siam.org/doi/abs/10.1137/0521030?journalCode=sjmaah>.

The original contract remains unchanged so its SHA-256 continues to identify
the exact pre-execution record. This is a bibliographic correction only; the
support definition used in the Ritz calculation (`w=0` with free rotations),
inputs, criteria, calculations, and results are unchanged.
