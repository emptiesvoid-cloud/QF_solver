# WP05-C/D/E — intégration Owner bornée

**Décision : `APPROVED_WITH_LIMITATIONS`.** Les preuves WP05-C, WP05-D et
WP05-E sont intégrées dans la lignée locale de gouvernance : WP05 passe de
2/5 à **5/5** et le total de **58/100 à 61/100** dans cette lignée.

La décision Owner WP05-E accepte `1/1 candidate` pour le benchmark H3 TET10 /
HEX20 et ses observables déclarés, sous réserve de l’intégration formelle de
WP05-C et WP05-D. Cette intégration rassemble maintenant C, D et E. Le message
Owner de suivi autorise cette intégration et reporte la comparaison avec
Code_Aster ou un autre solveur à une étape ultérieure. Cette comparaison
externe est donc différée ; aucune corrélation externe n’est revendiquée.

## Attribution

| Sous-paquet | Preuve | Points intégrés |
|---|---|---:|
| WP05-A/B | Identités TET10/HEX20 déjà intégrées | 2/2 |
| WP05-C | TET10 H1/H2/H3, équilibre, enveloppe et replay H1 PASS | 1/1 |
| WP05-D | HEX20 H1/H2/H3 et replay PASS ; décision Owner technique enregistrée | 1/1 |
| WP05-E | Comparaison inter-familles H3 ; cinq métriques dans les seuils ; décision Owner ACCEPT | 1/1 |
| **WP05** | **Clôture bornée avec limitations** | **5/5** |

Le total de branche après intégration locale est **61/100**. La branche locale
`0.2.9-unified-nonlinear` a été fast-forwardée jusqu’à
`a61cb0bc96a14e3a44aa4fd8458a28b82c87e462`, depuis la base governing autorisée
`a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe`. Le remote n’a pas été modifié :
`origin/0.2.9-unified-nonlinear` reste à cette base et son total publié reste
58/100 jusqu’au push. Aucun push n’a été effectué dans cette étape.

## Résultat inter-familles et limites conservées

WP05-E compare exclusivement l’observable commun historique `representative_sigma_xx`.
La valeur HEX20 issue de la fenêtre exacte/clippée reste spécifique à WP05-D
et n’est pas substituée à l’observable commun. Les populations discrètes
d’intégration de contrainte diffèrent entre TET10 et HEX20 ; cette différence
est documentée. La concordance stress de 5,2784 % est donc bornée à cette
mesure commune et ne démontre pas une équivalence générale des champs de
contrainte ou des familles d’éléments.

Limitations retenues : benchmark statique déclaré seulement, maillages H1/H2/H3
et familles TET10/HEX20 couvertes seulement, pas d’équivalence générale des
éléments, pas de corrélation externe à ce stade. La comparaison Code_Aster ou
autre solveur reste une action future distincte.

## Intégrité et vérification

- Les `FAIL_CLOSED` historiques WP05-D sont conservés sans réécriture.
- Les NPZ bruts C/D et les résultats JSON, leurs SHA-256, le replay et l’audit
  E sont liés dans le dossier machine-readable.
- Aucune mécanique de production, aucun seuil, aucune charge ou paramètre
  solver n’a changé.
- Vérifications ciblées : 52 tests WP05 A/B/C/D/E, harness, intégration et
  manifeste de hashes PASS (dont 25 tests E/harness), Ruff, compileall et
  parsing JSON PASS.
- La suite complète n’a pas été exécutée : l’autorisation de campagne WP05 la
  désactive explicitement.

Voir [WP05-C](wp05-c-tet10-formal-requalification.md), [WP05-D](../../../qualification/0_2_9/wp05d_formal_requalification/formal_requalification_report.md),
[WP05-E](wp05-e-cross-family-closure.md) et
`qualification/0_2_9/wp05cde_integration/wp05_cde_integration_audit.json`.
