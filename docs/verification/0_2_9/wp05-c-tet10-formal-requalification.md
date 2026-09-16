# WP05-C — requalification structurelle TET10

**Statut intégré : `PASS_WITH_LIMITATIONS` — 1/1 point WP05-C.**

La campagne TET10 H1/H2/H3 satisfait les gates gelés. Les calculs sont
séquentiels, ont accepté 12/12 incréments par maillage et n’ont utilisé aucun
fallback. Le replay H1 en nouveau processus passe. Les résultats bruts et
leurs SHA-256 sont conservés sous
`qualification/0_2_9/wp05c_formal_requalification/` ; le replay H1 est sous
`qualification/0_2_9/wp05c_formal_requalification_replay/`.

## Résultats

| Maillage | Nœuds / éléments / DOFs | Statut | Newton total | Fallbacks |
|---|---:|---|---:|---:|
| H1 — 4×2×2 | 225 / 96 / 675 | PASS | 145 | 0 |
| H2 — 8×4×4 | 1 377 / 768 / 4 131 | PASS | 156 | 0 |
| H3 — 16×8×8 | 9 537 / 6 144 / 28 611 | PASS | 156 | 0 |

Les douze incréments convergent pour chaque cas. La vérification canonique
H2→H3 donne :

| Observable | Écart relatif | Limite | Résultat |
|---|---:|---:|---|
| Déplacement en bout | 0,77633 % | 2 % | PASS |
| Résultante de réaction | 3,05×10⁻¹² % | 2 % | PASS |
| Moment de réaction | 0,002290 % | 2 % | PASS |
| Énergie de déformation | 0,77588 % | 2 % | PASS |
| `sigma_xx` contractuelle commune | 4,23950 % | 8 % | PASS |

L’équilibre force/moment est sous `1e-8` et l’enveloppe de déformation passe
sur H1/H2/H3. Le replay H1 reproduit les observables, l’historique de charge,
le compte Newton (145) et le hash des données brutes.

## Provenance et limites

- SHA d’exécution : `72282a6ca6e6574a32c6182eccb001d9816febbc`.
- Contrat historique SHA-256 :
  `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680`.
- Binding de politique runtime :
  `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5`.
- Mécanique de production et seuils modifiés : `NO`.
- Comparaison indépendante avec Code_Aster/autre solveur : `DEFERRED` ; elle
  demeure une validation externe future, sans revendication de corrélation.

Cette acceptation est bornée au benchmark cantilever, à la famille TET10, aux
maillages H1/H2/H3 et aux observables du contrat. Elle ne généralise pas la
précision des contraintes à d’autres géométries ou maillages.

Le dossier d’intégration C/D/E et la décision Owner sont décrits dans
[`wp05-cde-owner-integration.md`](wp05-cde-owner-integration.md) et
`qualification/0_2_9/wp05cde_integration/wp05_cde_integration_audit.json`.
