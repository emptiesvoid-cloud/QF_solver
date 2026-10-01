---
doc_id: DOC-029-WP12-EXTERNAL-VV-R3-5-RESULTS
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP12 R3.5 — corrélation externe élargie

## Conclusion

`PASS_WITH_LIMITATIONS` — les 144 comparaisons gelées entre QF Solver et Code_Aster 18.1 passent les gates numériques. Il s’agit d’une preuve complémentaire de corrélation FEM sur le périmètre linéaire statique décrit ci-dessous, pas d’une validation expérimentale, d’une preuve de convergence de maillage, ni d’une décision Owner sur les points WP12.

```text
R3_5_CASES = 144/144 PASS_CANDIDATE
INDEPENDENT_AUDIT = PASS_WITH_LIMITATIONS; 0 errors
MANIFEST = 2452 files; SHA-256 verified by the auditor
OFFICIAL_POINTS_CHANGED = NO
LEDGER_CHANGED = NO
MERGE_OR_PUSH = NO
```

## Matrice exécutée

La campagne croise quatre familles d’éléments, trois géométries, trois maillages et quatre directions de charge : `4 × 3 × 3 × 4 = 144` cas. Chaque cas a été généré une fois et résolu sur le même maillage par la voie linéaire directe de QF Solver puis par un processus Code_Aster frais.

| Dimension | Périmètre |
|---|---|
| Familles | TET4, HEX8, TET10, HEX20 — 36 cas chacune |
| Géométries | poutre élancée `2 × 0,5 × 0,5 m`; poutre rectangulaire `2 × 1 × 0,5 m`; bloc court `1 × 0,75 × 0,75 m` |
| Maillages | H1 `1×1×1`; H2 `2×1×1`; H3 `2×2×1` |
| Charges résultantes | axiale X `[1000, 0, 0] N`; transverse Y `[0, 1000, 0] N`; transverse Z `[0, 0, -1000] N`; combinée `[577.350269, 577.350269, -577.350269] N` |
| Matériau | élasticité isotrope 3D, `E = 210 GPa`, `ν = 0,3` |
| Conditions | déplacements bloqués sur tout le plan `x=0`; traction uniforme sur toute la face `x=L`, intégrée en forces nodales cohérentes |

Les nombres de nœuds, éléments et DDL ne dépendent ici que de la famille et du niveau de maillage :

| Famille | Maillage | Nœuds | Éléments | DDL |
|---|---:|---:|---:|---:|
| TET4 | H1 / H2 / H3 | 8 / 12 / 18 | 6 / 12 / 24 | 24 / 36 / 54 |
| HEX8 | H1 / H2 / H3 | 8 / 12 / 18 | 1 / 2 / 4 | 24 / 36 / 54 |
| TET10 | H1 / H2 / H3 | 27 / 45 / 75 | 6 / 12 / 24 | 81 / 135 / 225 |
| HEX20 | H1 / H2 / H3 | 20 / 32 / 51 | 1 / 2 / 4 | 60 / 96 / 153 |

H1/H2/H3 sont des niveaux de diversité de modèles, **pas** une revendication de convergence de maillage. La hiérarchie raffine selon les subdivisions gelées au contrat; elle ne constitue pas un raffinement 3D isotrope.

## Résultats recalculés

Le vérificateur indépendant a rehashé le manifeste, vérifié les cartes de maillage et de chargement, puis recalculé les comparaisons à partir des résultats bruts. Pour chaque métrique, la valeur rapportée est le maximum sur les 144 cas.

| Métrique | Maximum observé | Seuil | Résultat |
|---|---:|---:|---|
| Déplacement relatif L2 | `1,622e-12` | `1e-8` | PASS |
| Déplacement relatif L∞ | `1,689e-12` | `1e-8` | PASS |
| Réaction relative L2 | `1,649e-12` | `1e-8` | PASS |
| Réaction relative L∞ | `1,670e-12` | `1e-8` | PASS |
| Énergie (travail externe) relative | `2,011e-12` | `1e-8` | PASS |
| Résidu libre QF relatif L2 | `1,393e-12` | `1e-8` | PASS |
| Équilibre force QF relatif | `2,228e-12` | `1e-8` | PASS |
| Équilibre force Code_Aster relatif | `2,854e-15` | `1e-8` | PASS |
| Équilibre moment QF relatif | `1,903e-12` | `1e-8` | PASS |
| Équilibre moment Code_Aster relatif | `6,479e-16` | `1e-8` | PASS |
| Déplacement bloqué absolu maximal | `1,434e-22 m` | `1e-12 m` | PASS |

Répartition : TET4 `36/36`, HEX8 `36/36`, TET10 `36/36`, HEX20 `36/36`. Aucun cas non démarré, aucune comparaison en échec, aucun code de sortie non nul. Les 144 exécutions Code_Aster ont utilisé 144 conteneurs distincts, séquentiels, chacun limité à un CPU et sans MPI. Le temps cumulé rapporté des processus Code_Aster est `732,7 s`; la fenêtre murale d’exécution est d’environ `14 min 06 s`.

## Provenance et intégrité

```text
BRANCH = codex/wp12-expanded-correlation
AUTHORIZED_BASE_SHA = c5e842d5e589358633221ecd9f29c2ff1ef003aa
CONTRACT_PREPARATION_SHA = 49dd598a865ebade6c48446f56ef9289e4746a1d
CONTRACT_COMMIT / EXECUTION_SHA = e98fc34729b41d992a863296fef41f2c05e6df12
CONTRACT_SHA256 = 9459613354787bbfdaef7e2d2dbdc5ddbf200e5ee9fea44004e8e7a39c4e2b6c
RUNNER_SHA = 397d3bd4187716ffc7fd0a03aaabd4bcdce61569
MODEL_BUILDER_SHA = 53a0b86cc7d0f1f15451f748ef6d5514f1bc5621
AUDITOR_SHA = 397d3bd4187716ffc7fd0a03aaabd4bcdce61569
CODE_ASTER_IMAGE = sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435
AUDIT_STATUS = PASS_WITH_LIMITATIONS
AUDIT_ERRORS = 0
MANIFEST_SHA256 = 28efddda1e4e15d7152adc3b46a716f79685e5f30bf6f660e264aa672e5110f4
```

Les sorties brutes sont conservées localement sous `qualification/0_2_9/wp12_external_vv_r3_5_expanded_raw/`, exclues de Git; leur manifeste SHA-256 et le rapport d’audit sont versionnés. Aucun fichier de `src/` ne diffère de la base autorisée sur cette branche. La suite complète du dépôt n’a pas été exécutée.

## Historique conservé

- R3.2 reste archivé avec `132/144` candidats et l’échec fail-closed des 12 cas HEX20 H3, causé par une ligne `.mail` de 81 caractères tronquée après la limite Code_Aster de 80 colonnes.
- R3.3 reste archivé : Code_Aster a rejeté les identifiants de nœuds numériques; 20 cas en échec, un interrompu, 123 non démarrés.
- R3.4 reste archivé : le premier cas a échoué parce que les noms alphabétiques de nœuds n’étaient pas valides dans la carte `FORCE_NODALE/NOEUD`; 143 cas non démarrés.
- En R3.5, les nœuds utilisent `N1`, `N2`, … et les éléments des identifiants courts, ce qui respecte les conventions Code_Aster et la limite de ligne. Le smoke H3 à quatre familles est distinct de la corrélation formelle.
- Le premier smoke R3.5 à quatre PASS est préservé, mais exclu du gel car son libellé de tentative était erroné. Le smoke suivant, correctement identifié « attempt 4 », est celui lié au contrat.

Aucune preuve historique ni aucun résultat brut antérieur n’a été écrasé ou reclassé comme s’il provenait de R3.5.

## Limites et gouvernance

Cette corrélation est bornée à des solides 3D homogènes isotropes, petites déformations et statique linéaire. Les deux solveurs reçoivent le même maillage, matériau, chargement nodal cohérent et conditions aux limites. Elle ne démontre pas une équivalence expérimentale, une convergence asymptotique, l’équivalence de champs de contraintes, ni le comportement non linéaire, le contact, le frottement, la dynamique ou la scalabilité parallèle.

WP12 R2, ses décisions Owner, les points officiels et le ledger restent inchangés. Ce dossier R3.5 est une preuve supplémentaire à soumettre à revue Owner; aucun merge ni push n’a été effectué.

## Artefacts

- Contrat gelé : `qualification/0_2_9/wp12_external_vv_r3_5_expanded_contract.json`
- Audit indépendant : `qualification/0_2_9/wp12_external_vv_r3_5_expanded_audit.json`
- Manifeste des sorties brutes locales : `qualification/0_2_9/wp12_external_vv_r3_5_expanded_manifest.json`
- Résumé détaillé brut local : `qualification/0_2_9/wp12_external_vv_r3_5_expanded_raw/wp12_expanded_summary.json`
- Plan de campagne et historique R3.2–R3.5 : `docs/verification/0_2_9/wp12-expanded-correlation-r3-plan.md`

## Vérifications

- Tests ciblés WP12 : `10 passed`.
- `compileall` sur runner, auditeur, builder de contrat, smoke et générateur de modèles : PASS.
- Parsing JSON du contrat, de l’audit et du manifeste : PASS.
- Vérification whitespace du commit (`git -c core.whitespace=cr-at-eol show --check HEAD`) : PASS; les JSON générés sous Windows sont conservés en CRLF.
- Suite complète : non exécutée.
