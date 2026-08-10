# Baseline engineering QF_solver 0.2.0

## Decision

Quentin Farinazzo fige le 14 juillet 2026 la baseline `QF_solver 0.2.0` pour
un usage engineering interne dans les domaines explicitement verifies.

Cette decision est une auto-revue : Quentin Farinazzo est a la fois auteur et
validateur mecanique. Elle n'est pas independante et ne constitue ni une
certification externe, ni une qualification attribuee par une autorite.

## Configuration source

| Objet | Identifiant |
| --- | --- |
| Commit de gel initial | `14b7b864b83dd5a68e64a0d96103579a79c8e1ce` |
| Commit V&V torsion | `4f242a9dd97c9e5063b4a9ab248146979c3b8ab9` |
| Branche distante | `qf-solver-0.2.0` |
| Tag de livraison | `v0.2.0-engineering` |

Le tag vise le commit qui introduit le present manifeste. Les empreintes des
maillages, configurations, resultats sources et artefacts V&V restent dans les
manifestes propres a chaque etude.

## Controles locaux

- `ruff` : PASS ;
- typage progressif `mypy` : PASS ;
- `compileall` : PASS ;
- suite standard : 328 tests PASS, 11 deselectionnes ;
- documentation : 16 tests PASS et construction MkDocs stricte PASS ;
- campagne V&V ciblee : 51 tests PASS ;
- MITC4 quick : PASS ;
- readiness `tet4-linear-static` : PASS.

## Etudes controlees

- `VNV-TET4-CANTILEVER-ANALYTIC-001` : convergence en flexion face a la
  reference de Timoshenko ;
- `VNV-TET4-TORSION-ANALYTIC-001` : huit niveaux face a Saint-Venant, verdict
  automatique PASS et decision `accepted_with_reservations`.

Pour la torsion, la rotation terminale atteint `3,07 %` d'erreur et l'ordre
observe vaut `1,499`. Les contraintes locales restent hors domaine accepte,
avec `29,06 %` d'erreur L2 sur le niveau le plus fin.

## Limites

- comparaison Abaqus ou Ansys de torsion encore absente ;
- revue independante encore absente ;
- aucune revendication de certification ;
- TET10 avance et plasticite J2 toujours experimentaux.

Le registre machine-readable autoritatif est
`qualification/baselines/qf_solver_0.2.0_engineering.json`.
