# Public Volumetric TET10 Sample

This is a bounded paired TET10/TET4 execution sample. TET10 connectivity is created by deterministic straight-sided mid-edge elevation of the accepted TET4 mesh; it is not a TET10 qualification campaign.

- QF source SHA: `96f82692c5e00f21d48b286134d13ea81c1f84af`
- Worktree dirty at capture: `True`
- Selected cases: `24` of `24` requested
- Selection limit (source TET4 nodes): `10000` nodes
- Status counts: `{'PASS': 17, 'FAIL': 7, 'TIMEOUT': 0}`

| Case | TET4 status | TET10 status | TET10 nodes | TET10 elements | displacement relative difference | duration ratio | RSS ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| FCL-0086 | PASS | PASS | 303 | 108 | 0.5339479929151175 | 1.5018926966493613 | 1.0352879944482998 |
| FCL-0083 | PASS | PASS | 959 | 398 | 0.6008330394903174 | 2.4943143462161377 | 1.339255473104043 |
| FCL-0100 | PASS | PASS | 1358 | 623 | 0.7932410334735823 | 3.4978721992582544 | 1.4462925627240144 |
| FCL-0048 | PASS | PASS | 1515 | 711 | 0.494297089146561 | 3.2637063033073574 | 1.8993543179983858 |
| FCL-0099 | PASS | PASS | 1908 | 1000 | 0.7336849842765968 | 3.879484922664615 | 2.0839564758891767 |
| FCL-0098 | PASS | PASS | 1933 | 985 | 0.5241092644107566 | 3.818977924188204 | 1.9825134511913913 |
| FCL-0027 | PASS | PASS | 2041 | 993 | 0.13309085455384667 | 4.106159082444966 | 2.1620725180289972 |
| FCL-0072 | PASS | PASS | 2007 | 912 | 0.04039616141244181 | 4.214690169095987 | 1.8543839053472366 |
| FCL-0051 | FAIL | FAIL | 2335 | 1161 | None | 3.8363350648773404 | 2.4217953471128 |
| FCL-0057 | FAIL | FAIL | 2339 | 1078 | None | 3.883028962144375 | 1.9892611309575674 |
| FCL-0004 | FAIL | FAIL | 2575 | 1243 | None | 4.193897787360939 | 1.8396684922563564 |
| FCL-0002 | PASS | PASS | 2748 | 1358 | 0.33096353196723133 | 5.702268662045237 | 2.0746877585974635 |
| FCL-0097 | PASS | PASS | 2802 | 1377 | 0.46481566663603374 | 4.809816973546158 | 2.0504446546830652 |
| FCL-0091 | PASS | PASS | 2901 | 1534 | 0.133141913477554 | 6.200350305620181 | 2.3671080251897303 |
| FCL-0039 | PASS | PASS | 3397 | 1736 | 0.266469508356455 | 5.554253395541553 | 1.9756708572833739 |
| FCL-0040 | FAIL | FAIL | 3960 | 2101 | None | 4.734618843216315 | 2.1270335608646187 |
| FCL-0033 | PASS | PASS | 3990 | 1881 | 0.9821484825837631 | 4.994690375013375 | 3.188489421512058 |
| FCL-0024 | PASS | PASS | 4450 | 2264 | 0.6907223594880133 | 5.102673862733866 | 2.0757682291666666 |
| FCL-0035 | PASS | PASS | 3986 | 1693 | 0.6934208163149873 | 5.302250014021263 | 1.9897416767695608 |
| FCL-0014 | FAIL | FAIL | 4805 | 2439 | None | 5.096102271111214 | 2.1003955686453315 |
| FCL-0030 | PASS | PASS | 5159 | 2682 | 0.4846619279529685 | 7.771101136618758 | 2.1292608685549643 |
| FCL-0034 | PASS | PASS | 6726 | 2963 | 0.7519477316729479 | 8.689366864322311 | 2.188349787823677 |
| FCL-0050 | FAIL | FAIL | 12067 | 7027 | None | 6.296317193908293 | 2.7791641340807276 |
| FCL-0047 | FAIL | FAIL | 16476 | 7555 | None | 6.382361222324783 | 2.3103121159990168 |

## Interpretation

The paired comparison uses the same neutral support and 1,000 N loading convention, while changing only the element order. Reactions, external work and strain energy are retained when the QF result is available. The TET10 mesh is a straight-sided elevation of the same TET4 geometry, which avoids treating curved Gmsh high-order node placement as a QF TET10 ordering contract. A failed or timed-out TET10 case is evidence about the current robustness envelope, not evidence of a solver defect by itself.

Large TET10 meshes above the selection limit were intentionally not executed in this bounded run to avoid an uncontrolled memory experiment. HEX8/HEX20 are absent from this corpus and are not inferred.
