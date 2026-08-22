---
doc_id: DOC-OWNER-TET10-J2-REFINED-001
revision: 0.1
status: ready_for_owner_review
review_mode: owner_review
promotion_target: stable
scope: tet10-material-nonlinear
---

# Owner review — TET10 J2 complexe raffiné

## Objet

Cette revue porte sur une équerre ré-entrante maillée en TET10, soumise à des charges combinées UX/UY et comparée sur maillages identiques avec Code_Aster 18.1.0 (`TETRA10`, `VMIS_ISOT_LINE`). La campagne complète contient trois niveaux de raffinement : 457, 911 et 2217 éléments.

La règle de promotion utilisée dans QF_solver impose désormais une erreur mécanique primaire inférieure ou égale à 1 %. Pour ce dossier, l'observable primaire est le PEEQ RMS sur le chemin de chargement. Les déplacements globaux et le résidu d'équilibre sont des contrôles complémentaires.

## Résultats à examiner

| Taille de maille | Éléments | PEEQ RMS | Déplacement RMS | Résidu maximal |
|---:|---:|---:|---:|---:|
| 0,32 | 457 | 1,8444 % | 0,01245 % | 1,972e-09 |
| 0,24 | 911 | 1,4881 % | 0,02885 % | 4,917e-11 |
| 0,16 | 2217 | **0,8867 %** | 0,008997 % | 4,666e-11 |

Le niveau fin passe donc le seuil technique de 1 %. Cette réussite ne vaut que pour le cas étudié et ne constitue pas une validation générale de la plasticité, des grandes déformations, du contact, de la rupture ou de l'endommagement.

## Questions Owner

### Q1 — Domaine démontré

Les trois niveaux de raffinement sur l'équerre ré-entrante, les charges combinées et la comparaison Code_Aster couvrent-ils suffisamment le domaine TET10 J2 à petites déformations revendiqué pour une promotion stable bornée ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Critère d'erreur

Le PEEQ RMS fin de 0,8867 %, inférieur au seuil primaire de 1 %, est-il acceptable comme preuve technique pour ce cas, en maintenant les contraintes ponctuelles singulières hors critère d'acceptation ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Limites

Les exclusions suivantes restent-elles explicites et acceptables : grandes déformations, chargement cyclique, contact, rupture, dommage, flambement et singularités ponctuelles ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Décision de maturité

Décision proposée : `accepted_with_recommendations`, `accepted_for_bounded_engineering_use`, `stable` ou `more_evidence_required`.

Commentaire :

Signature Owner :

Date :

## Artefacts reproductibles

- `qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/summary.json`
- `qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/refinement_report.md`
- `qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/refinement_convergence.png`
- `qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/manifest.json`
- Commande : `python scripts/build_tet10_j2_refinement_evidence.py`

## Avis technique interne

Le critère numérique primaire est franchi sur le niveau fin. Une promotion stable du scope complet doit toutefois attendre la réponse Owner et rester limitée aux hypothèses déclarées. Le résultat ne doit pas être extrapolé aux problèmes non linéaires non couverts.
