# Public Volumetric TET10 Sample

This is a bounded paired TET10/TET4 execution sample. TET10 connectivity is created by deterministic straight-sided mid-edge elevation of the accepted TET4 mesh; it is not a TET10 qualification campaign.

- QF source SHA: `c9324bb7662f689c81d743e084fe0dbc58077fb8`
- Worktree dirty at capture: `False`
- Selected cases: `24` of `24` requested
- Selection limit (source TET4 nodes): `10000` nodes
- Status counts: `{'PASS': 17, 'FAIL': 7, 'TIMEOUT': 0}`

| Case | TET4 status | TET10 status | TET10 nodes | TET10 elements | displacement relative difference | duration ratio | RSS ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| FCL-0086 | PASS | PASS | 303 | 108 | 0.5339479929151175 | 1.502280246675904 | 1.0273346169715307 |
| FCL-0083 | PASS | PASS | 959 | 398 | 0.6008330394903174 | 2.4972826603745717 | 1.3348206043448827 |
| FCL-0100 | PASS | PASS | 1358 | 623 | 0.7932410334735823 | 3.42211437939187 | 1.816027756621816 |
| FCL-0048 | PASS | PASS | 1515 | 711 | 0.494297089146561 | 3.2630859495564266 | 1.5003485628485629 |
| FCL-0099 | PASS | PASS | 1908 | 1000 | 0.7336849842765968 | 3.756116217220573 | 2.0689277638938472 |
| FCL-0098 | PASS | PASS | 1933 | 985 | 0.5241092644107566 | 3.757793025373038 | 2.0527424163551182 |
| FCL-0027 | PASS | PASS | 2041 | 993 | 0.13309085455384667 | 4.346436427259532 | 2.0026948542223253 |
| FCL-0072 | PASS | PASS | 2007 | 912 | 0.04039616141244181 | 4.160519579660995 | 2.091523263224984 |
| FCL-0051 | FAIL | FAIL | 2335 | 1161 | None | 3.780298646585123 | 2.2074829154572257 |
| FCL-0057 | FAIL | FAIL | 2339 | 1078 | None | 3.827226987207276 | 1.7702776584527669 |
| FCL-0004 | FAIL | FAIL | 2575 | 1243 | None | 4.19493041550354 | 2.259752108413627 |
| FCL-0002 | PASS | PASS | 2748 | 1358 | 0.33096353196723133 | 6.3148116351385974 | 1.8759805882659895 |
| FCL-0097 | PASS | PASS | 2802 | 1377 | 0.46481566663603374 | 4.812262632076394 | 2.076335000287406 |
| FCL-0091 | PASS | PASS | 2901 | 1534 | 0.133141913477554 | 5.868804976296119 | 2.306650658373846 |
| FCL-0039 | PASS | PASS | 3397 | 1736 | 0.266469508356455 | 5.151632213522567 | 2.0949708857877103 |
| FCL-0040 | FAIL | FAIL | 3960 | 2101 | None | 4.696556952447423 | 2.0529798602548293 |
| FCL-0033 | PASS | PASS | 3990 | 1881 | 0.9821484825837631 | 4.880441910504796 | 2.5556168311917498 |
| FCL-0024 | PASS | PASS | 4450 | 2264 | 0.6907223594880133 | 5.0299138031309365 | 2.2032781345049 |
| FCL-0035 | PASS | PASS | 3986 | 1693 | 0.6934208163149873 | 5.031955989811872 | 1.983830037446229 |
| FCL-0014 | FAIL | FAIL | 4805 | 2439 | None | 5.163419284764011 | 2.116765129325324 |
| FCL-0030 | PASS | PASS | 5159 | 2682 | 0.4846619279529685 | 7.2660859261045525 | 2.137387334932576 |
| FCL-0034 | PASS | PASS | 6726 | 2963 | 0.7519477316729479 | 8.866275706601229 | 2.1838370309563415 |
| FCL-0050 | FAIL | FAIL | 12067 | 7027 | None | 6.052241269848751 | 3.116828913442796 |
| FCL-0047 | FAIL | FAIL | 16476 | 7555 | None | 6.367849257662119 | 1.9931588479041815 |

## Interpretation

The paired comparison uses the same neutral support and 1,000 N loading convention, while changing only the element order. Reactions, external work and strain energy are retained when the QF result is available. The TET10 mesh is a straight-sided elevation of the same TET4 geometry, which avoids treating curved Gmsh high-order node placement as a QF TET10 ordering contract. A failed or timed-out TET10 case is evidence about the current robustness envelope, not evidence of a solver defect by itself.

Large TET10 meshes above the selection limit were intentionally not executed in this bounded run to avoid an uncontrolled memory experiment. HEX8/HEX20 are absent from this corpus and are not inferred.
