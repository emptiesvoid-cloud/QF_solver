---
doc_id: DOC-QUAL-002
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Plan de qualification de l'outil

## Objectif

Construire un dossier compatible avec une future demarche DO-330/ED-215 sans
revendiquer de qualification avant revue externe.

## Scopes progressifs

1. `tet4-linear-static`: TET4 isotrope, petits deplacements, SI.
2. `mitc4-linear-static`: coques facettes planes, statique lineaire.
3. `linear-dynamics`: modal, Newmark et harmonique lineaires.
4. `large-tet4-linear-static`: TET4 distribue PETSc/MPI.
5. `material-nonlinear`: petites deformations, lois non-lineaires qualifiees.

Chaque scope possede un statut `development`, `candidate` ou `qualified`.
Seule une decision externe peut attribuer `qualified`.

## Donnees de cycle de vie attendues

- exigences operationnelles et exigences detaillees;
- architecture et conception;
- plan et resultats de verification;
- gestion de configuration et index de baseline;
- assurance qualite, revues et anomalies;
- dossier de preuve et synthese d'accomplissement.

## Politique

- Les criteres sont fixes avant l'execution des benchmarks.
- Une non-regression interne ne constitue pas une reference independante.
- Un scope candidat exige une reference analytique, experimentale ou tierce.
- Les ecarts connus restent visibles dans la synthese de qualification.

## Baseline de couverture P0

- Mesure courante du 11 juillet 2026: `85,30 %` lignes et branches combinees sur
  `solveur/` et `mitc4/`.
- Plancher anti-regression CI: `84 %`, pour absorber les ecarts mineurs entre
  plateformes sans masquer une baisse d'un point complet.
- Plancher des nouveaux modules P0 (`core/errors.py` et
  `verification/traceability.py`): `90 %` controle par
  `scripts/check_p0_coverage.py`.
- Toute baisse volontaire doit etre justifiee dans le registre d'anomalies et
  approuvee lors de la revue de baseline.
