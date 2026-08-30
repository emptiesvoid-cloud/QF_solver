---
doc_id: DOC-VNV-026-G12-FINAL-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.6a0
contract_id: 026-G12-FINAL-CAMPAIGN
start_sha: 51b3a7c8ace6731830109984a01ce31f79c44401
measurement_sha: 81443c20b3f1ec9b742292bc5f880cc10e112a96
---

# 026-G12 — campagne technique finale

## Décision technique

La campagne caractérise les routes existantes et complète la preuve de
performance de l’optimisation d’assemblage déjà introduite. Elle ne change
aucune formulation, politique de solveur, tolérance, valeur par défaut ou
maturité de route.

Le runner est
`scripts/benchmark_g12_route_matrix.py`. Chaque cas est exécuté deux fois
avec un modèle reconstruit, un échantillonnage RSS local et une vérification
de finitude. Les champs sont distingués comme `MEASURED`,
`MEASURED_REUSED_EXISTING_G12_EVIDENCE` ou `NOT_MEASURED` dans
`qualification/0_2_6/g12_final_campaign.json`.

## Matrice runtime mesurée

| Route | Famille | DOF | éléments | Assemblage médian (s) | Solve médian (s) | Total médian (s) | RSS max (MiB) | Statut | Replay |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| linear_static | TET4 | 375 | 384 | 0.034319 | 0.003427 | 0.226604 | 112.32 | PASS | PASS |
| linear_static | TET10 | 300 | 10 | 0.017307 | 0.001514 | 0.128300 | 112.56 | PASS | PASS |
| linear_static | HEX8 | 375 | 64 | 0.171033 | 0.002383 | 0.197220 | 112.85 | PASS | PASS |
| linear_static | HEX20 | 300 | 5 | 0.160876 | 0.001379 | 0.270626 | 112.85 | PASS | PASS |
| modal | TET4 | 12 | 1 | 0.000677 | non exposé | 0.063663 | 113.38 | PASS | PASS |
| linear_buckling | TET4 | 12 | 1 | 0.006558 | 0.001647 | 0.015685 | 113.74 | PASS | PASS |
| nonlinear_static (J2 borné) | TET4 | 36 | 10 | 0.086689 | 0.026932 | 0.172299 | 113.80 | PASS | PASS |
| geometric_nonlinear_static (TL borné) | TET4 | 24 | 5 | 0.010570 | 0.002266 | 0.021443 | 113.80 | PASS | PASS |
| nonlinear_static/contact (G09 borné) | TET4 | 24 | 5 | 0.050704 | 0.023106 | 0.121724 | 113.81 | PASS | PASS |

Résultat : 18/18 exécutions PASS, toutes les métriques finies et replay
déterministe. Pour buckling, le replay porte sur statut, facteur critique et
résidu de mode ; le checksum binaire du vecteur propre n’est pas utilisé
comme oracle strict de représentation.

## Scaling et mémoire

Les points full-solve optimisés G12 sont réutilisés depuis
`g12_optimization_optimized_scaling.json` : 3k, 10k, 30k et 100k DOF,
tous PASS. Le point 100k atteint 107 811 DOF, 3 813 789 entrées CSR et
638.49 MiB de RSS. Les exposants observés sont environ 1.050 pour
l’assemblage, 1.487 pour le solve, 1.056 pour le temps total et 0.544 pour
le RSS ; ils décrivent cette campagne uniquement.

Les probes larges ne sont pas relancées :

- 300k : preuve existante réutilisée, assembly-only PASS à 311 469 DOF,
  RSS ≈ 1.48 GiB ;
- 1M : `REUSE_EXISTING_EVIDENCE`, assembly-only `RESOURCE_LIMITED` à 300 s,
  sans solve et sans claim de succès.

## Goulot mesuré

Le profil propre à 10 125 DOF reste la référence la plus informative :

- validation qualité mesh : 8.335 s, environ 71.43 % du profil ;
- assemblage : 2.772 s, environ 23.75 % ;
- `load_balance` : 0.009 s, environ 0.08 % ;
- solve : 0.103 s, environ 0.89 %.

Le goulot après optimisation est donc `MESH_VALIDATION / TET4 quality
metrics`. Une vectorisation ou un cache plus large des métriques qualité
reste différé : aucune vérification ne doit être supprimée et une nouvelle
campagne serait nécessaire.

## Intégrité numérique et limitations

La preuve A/B existante établit l’égalité des NNZ, checksums de déplacement
et résidus aux points 3k et 10k, avec des métriques finies et aucun
`FIX_ONLY_FAILURE`. La matrice présente ici n’ajoute pas de modification
fonctionnelle du solveur.

Les mesures modal et buckling sont des cas compacts ; le temps eigensolve
modal n’est pas séparément exposé par la route publique et est donc
`NOT_MEASURED`, jamais assimilé à zéro. J2, TL et contact sont des
caractérisations bornées sur les routes G06/G07/G09 existantes. Aucun claim
industriel, universel ou de scaling combinatoire n’est formulé.

La full regression est `SKIPPED_BY_POLICY` pour ce lot ; elle est réservée
au Owner Closeout après stabilisation.

## Provenance

- contrat source : `qualification/0_2_6/g12_optimization_contract.json` ;
- matrice runtime : `qualification/0_2_6/g12_final_campaign.json` ;
- runner : `scripts/benchmark_g12_route_matrix.py` ;
- SHA de mesure : `81443c20b3f1ec9b742292bc5f880cc10e112a96` ;
- solveur fonctionnel modifié dans ce lot : non.
