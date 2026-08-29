# Public Volumetric TET10 Sample

This is a bounded paired TET10/TET4 execution sample. TET10 connectivity is created by deterministic straight-sided mid-edge elevation of the accepted TET4 mesh; it is not a TET10 qualification campaign.

- QF source SHA: `b9e947a300108869e1642957c1be572aa69011ca`
- Worktree dirty at capture: `False`
- Selected cases: `24` of `24` requested
- Selection limit (source TET4 nodes): `10000` nodes
- Status counts: `{'PASS': 17, 'FAIL': 7, 'TIMEOUT': 0}`

| Case | TET4 status | TET10 status | TET10 nodes | TET10 elements | displacement relative difference | duration ratio | RSS ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| FCL-0086 | PASS | PASS | 303 | 108 | 0.5339479929151175 | 1.5008108714699693 | 1.0424084678119034 |
| FCL-0083 | PASS | PASS | 959 | 398 | 0.6008330394903174 | 2.4957097350581523 | 1.3207431479551168 |
| FCL-0100 | PASS | PASS | 1358 | 623 | 0.7932410334735823 | 3.4199064709114944 | 1.6219576207973037 |
| FCL-0048 | PASS | PASS | 1515 | 711 | 0.494297089146561 | 3.2604464891901914 | 1.9313343575112476 |
| FCL-0099 | PASS | PASS | 1908 | 1000 | 0.7336849842765968 | 3.817398795157893 | 1.8646602309293963 |
| FCL-0098 | PASS | PASS | 1933 | 985 | 0.5241092644107566 | 3.757304038553565 | 1.744622462569111 |
| FCL-0027 | PASS | PASS | 2041 | 993 | 0.13309085455384667 | 4.158762171633153 | 1.7524199931002293 |
| FCL-0072 | PASS | PASS | 2007 | 912 | 0.04039616141244181 | 4.215900914215346 | 1.708954602249063 |
| FCL-0051 | FAIL | FAIL | 2335 | 1161 | None | 3.889035984531235 | 2.238474870017331 |
| FCL-0057 | FAIL | FAIL | 2339 | 1078 | None | 3.772688327948354 | 1.7888840932276544 |
| FCL-0004 | FAIL | FAIL | 2575 | 1243 | None | 4.192731980882433 | 2.2603792926704256 |
| FCL-0002 | PASS | PASS | 2748 | 1358 | 0.33096353196723133 | 5.660180750759312 | 2.310900188970967 |
| FCL-0097 | PASS | PASS | 2802 | 1377 | 0.46481566663603374 | 4.720849972893567 | 2.2102313403833174 |
| FCL-0091 | PASS | PASS | 2901 | 1534 | 0.133141913477554 | 5.99076937119219 | 2.8994302800113134 |
| FCL-0039 | PASS | PASS | 3397 | 1736 | 0.266469508356455 | 5.154372730595975 | 2.374630405322163 |
| FCL-0040 | FAIL | FAIL | 3960 | 2101 | None | 4.685147087034455 | 2.058322924244712 |
| FCL-0033 | PASS | PASS | 3990 | 1881 | 0.9821484825837631 | 4.919064695084538 | 3.1630890101092843 |
| FCL-0024 | PASS | PASS | 4450 | 2264 | 0.6907223594880133 | 4.787863678693282 | 2.088022729058106 |
| FCL-0035 | PASS | PASS | 3986 | 1693 | 0.6934208163149873 | 5.0301333503595735 | 2.448756313732965 |
| FCL-0014 | FAIL | FAIL | 4805 | 2439 | None | 4.889857724619022 | 2.1050750536097214 |
| FCL-0030 | PASS | PASS | 5159 | 2682 | 0.4846619279529685 | 7.200897277571856 | 2.14263426901538 |
| FCL-0034 | PASS | PASS | 6726 | 2963 | 0.7519477316729479 | 9.320879070677021 | 2.180023994552588 |
| FCL-0050 | FAIL | FAIL | 12067 | 7027 | None | 6.283310911497051 | 2.4322769007051024 |
| FCL-0047 | FAIL | FAIL | 16476 | 7555 | None | 6.422283768937687 | 2.453957979903432 |

## Interpretation

The paired comparison uses the same neutral support and 1,000 N loading convention, while changing only the element order. Reactions, external work and strain energy are retained when the QF result is available. The TET10 mesh is a straight-sided elevation of the same TET4 geometry, which avoids treating curved Gmsh high-order node placement as a QF TET10 ordering contract. A failed or timed-out TET10 case is evidence about the current robustness envelope, not evidence of a solver defect by itself.

Large TET10 meshes above the selection limit were intentionally not executed in this bounded run to avoid an uncontrolled memory experiment. HEX8/HEX20 are absent from this corpus and are not inferred.
