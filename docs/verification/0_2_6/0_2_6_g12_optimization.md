---
doc_id: DOC-VNV-026-G12-OPT-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.6a0
contract_id: 026-G12-OPTIMIZATION
start_sha: c967903956c82fcae6a23c9a946ddcd8bf93306e
measurement_sha: 7860ade85f0020b68e23c43787c77f28a863d8d6
---

# 026-G12 — optimisation contrôlée de l’assemblage linéaire

## Périmètre et décision technique

Le diagnostic Lot-2 identifiait le chemin Python d’assemblage des charges et
du bilan `load_balance` comme premier poste mesurable. Cette optimisation
reste limitée à la route `linear_static`, famille TET4, et conserve la
formulation élémentaire, la méthode de résolution, les seuils de convergence,
les valeurs par défaut et la taille des blocs d’assemblage.

Les changements autorisés sont :

- accumulation directe des charges nodales sans vecteur global temporaire
  lorsque les vecteurs individuels ne sont pas demandés ;
- voie vectorisée pour les charges de translation contiguës et voie indexée
  pour les ensembles de DDL mixtes ;
- cache sensible aux mutations pour les métriques de qualité dépendant
  uniquement de la géométrie, de la connectivité et des seuils.

Aucune modification de formulation, de physique, de Newton/TL, de contact,
de l’eigensolver, de la politique numérique ou des autres gates n’est incluse.

## Comparaison A/B

Les deux points ont la même topologie, les mêmes DDL, les mêmes charges et
les mêmes conditions aux limites. `actual_dofs` est la valeur réellement
construite par le générateur ; le point demandé 10 000 produit 10 125 DDL.

| actual DOFs | A assembly (s) | B assembly (s) | assembly speedup | A load balance (s) | B load balance (s) | B total wall (s) | total speedup | RSS ratio | nnz/checksum |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 000 | 2.671346 | 0.400887 | 6.664× | 2.394764 | 0.000996 | 1.770523 | 2.341× | 1.0185× | equal/equal |
| 10 125 | 19.296384 | 1.363555 | 14.152× | 18.149961 | 0.002477 | 6.093912 | 3.993× | 1.0047× | equal/equal |

Les speedups `load_balance` correspondants sont environ 2 404× et 7 327×.
Les checksums de déplacement sont identiques (`d1ef…2584f` et
`b0ab…8d3e72`), les `global_stiffness_nnz` sont identiques (95 172 et
338 727), les résidus relatifs sont inchangés (`8.5852e-12` et
`6.0232e-12`) et toutes les métriques sont finies.

Les valeurs complètes et les SHA de provenance sont dans
`qualification/0_2_6/g12_optimization_evidence.json`.

## Scaling full solve optimisé

| cible DOFs | actual DOFs | assembly (s) | validation mesh (s) | load assembly (s) | load balance (s) | solve (s) | wall (s) | RSS (MiB) | global nnz | résultat |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 000 | 3 000 | 0.400887 | 1.226609 | 0.002586 | 0.000996 | 0.019903 | 1.770523 | 91.65 | 95 172 | PASS |
| 10 000 | 10 125 | 1.363555 | 4.410178 | 0.005211 | 0.002477 | 0.091505 | 6.093912 | 125.29 | 338 727 | PASS |
| 30 000 | 31 944 | 4.668655 | 15.261603 | 0.011839 | 0.007941 | 0.769673 | 21.351989 | 240.97 | 1 233 480 | PASS |
| 100 000 | 107 811 | 17.097760 | 54.182970 | 0.029244 | 0.029153 | 3.578757 | 76.864999 | 638.49 | 3 813 789 | PASS |

Les exposants log-log observés sur ces quatre points sont environ 1.050 pour
l’assemblage, 1.487 pour la résolution, 1.056 pour le temps total et 0.544
pour le RSS du processus parent. Ils décrivent cette campagne et ne sont pas
des garanties générales pour toutes les topologies ou toutes les familles.

## Probes de très grande taille

Les probes 300 000 et 1 000 000 sont explicitement `assembly_only` : aucune
résolution ni construction de charges n’est exécutée.

- 300 000 demandés : 311 469 DDL, 584 016 éléments, 11 168 199 entrées non
  nulles, 135 264 268 octets de stockage CSR, 46.278 s d’assemblage et
  222.959 s de wall ; `PASS`, 1 483 046 912 octets de RSS parent.
- 1 000 000 demandés : arrêt contrôlé après 300 s sans rapport enfant ;
  `RESOURCE_LIMITED`, 1 472 012 288 octets de RSS parent. Ce résultat n’est
  pas présenté comme un succès et n’est pas une exécution full solve.

La politique d’arrêt est 300 s ou 4 GiB RSS dans un processus enfant isolé,
avec arrêt après la première limite. Voir
`scripts/benchmark_g12_assembly.py` et
`qualification/0_2_6/g12_optimization_assembly_probes.json`.

## Profil et cache

Le profil propre à 10 125 DDL après optimisation donne, avec l’overhead de
`cProfile`, environ 71.43 % pour la validation de qualité du maillage,
23.75 % pour l’assemblage, 0.08 % pour `load_balance` et 0.89 % pour la
résolution. Le goulot mesuré suivant est donc le calcul des métriques de
qualité TET4, pas le bilan de charges.

Sur le même modèle et le même `LinearStaticSolver`, le premier passage a
pris 6.810739 s et le second 2.177550 s ; checksum et résidu sont identiques
et les deux statuts sont `PASS`. Le test de mutation de la géométrie invalide
le cache et force le recalcul. Le cache ne contient aucune donnée dépendant de
l’état de résolution.

## Intégrité numérique et validation

La preuve A/B vérifie le statut, le nombre global d’entrées CSR, le checksum
de déplacement, le résidu relatif fini et la finitude des métriques. Les
tests de charges distribuées et de charges nodales mixtes couvrent la voie
générique ; le test de validation vérifie la réutilisation et l’invalidation
du cache.

La même commande de suite complète a donné 1 828 PASS / 184 SKIP / 20 FAIL
sur `c967903…` et 1 830 PASS / 184 SKIP / 20 FAIL sur le SHA de mesure
`7860ade…`; les 20 noms de tests en échec sont identiques. Après extraction
du runner, le contrôle final B donne 1 831 PASS / 184 SKIP / 19 FAIL : la
seule différence est un test d’audit de pack qui est sensible au snapshot
généré par l’environnement. Il n’y a aucun `FIX_ONLY_FAILURE` ni différence
de comportement numérique. Les échecs de release/audit historiques
(version publique, audit de publication, registre contrôlé et limite de taille
de certains scripts) sont suivis séparément ; ils ne constituent pas une
preuve de défaut numérique de cette optimisation. La table A/B et les
extraits d’erreurs sont dans `g12_optimization_regression_triage.json`.

## Limites et travaux différés

La cache de métriques TET4 est volontairement limitée aux dépendances
géométriques immuables et sensibles aux mutations. La vectorisation d’autres
familles, la réduction du coût des métriques qualité, la normalisation des DDL
et toute optimisation sparse sont différées : elles nécessiteraient une
nouvelle campagne et ne sont pas présumées sûres par cette preuve.

Cette preuve G12 ne ferme pas automatiquement une gate globale et ne change
aucune maturité d’élément ou de route.
