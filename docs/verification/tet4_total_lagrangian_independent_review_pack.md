---
doc_id: DOC-INDEPENDENT-REVIEW-TET4-TL-001
revision: 0.1
status: ready_for_independent_review
applicable_version: 0.2.1a0
scope: tet4-total-lagrangian-structural-v2
---

# Dossier de revue indépendante - TET4 Total Lagrangian

## Objet

Ce dossier prépare une revue indépendante de la formulation TET4
Total-Lagrangian pour petits et grands déplacements, flambement et
post-flambement. Il ne constitue pas une décision Owner et ne permet aucune
promotion vers `stable` tant qu'un relecteur indépendant n'a pas répondu et
signé la fiche associée.

## Périmètre proposé

Le périmètre est limité à l'élasticité isotrope, aux petits déplacements pour
les contrôles noyau, puis aux grandes rotations et au post-flambement sur les
cas explicitement listés. Le contact, la rupture, l'endommagement, la
plasticité et l'extrapolation à des structures non testées sont exclus.

## Preuves à examiner

| Preuve | Artefact | Contrôle attendu |
| --- | --- | --- |
| Formulation | `docs/verification/tet4_total_lagrangian_structural_v2.md` | Référentiel, hypothèses, signes et linéarisation |
| Noyau | `results/VNV-TET4-TL-KERNEL-001/summary.json` | États finis, invariants et assemblage élémentaire |
| Assemblage | `results/VNV-TET4-TL-ASSEMBLY-002/summary.json` | Patch multiélément et énergie |
| Incréments | `results/VNV-TET4-TL-STEPS-004/summary.json` | Sensibilité au nombre de pas |
| Contraintes | `results/VNV-TET4-TL-STRESS-005/summary.json` | Contraintes hors singularités |
| Flambement | `results/VNV-TET4-TL-BUCKLING-H5-010/summary.json` | Convergence de charge critique |
| Post-flambement | `results/VNV-TET4-TL-POSTBUCKLING-007/summary.json` | Branches imparfaites et stabilité |
| Oracle externe | `qualification/vnv/external/code_aster_tl_structural/reference/summary.json` | Même géométrie, chargement et observables |

## Critères de revue

1. Le domaine et les exclusions sont-ils suffisamment précis ?
2. Les trois familles d'observables, déplacement, charge critique et
   contrainte hors singularité, sont-elles correctement définies ?
3. Les raffinements de maillage et de pas montrent-ils une tendance vers une
   asymptote ?
4. Les erreurs finales des grandeurs principales sont-elles inférieures ou
   égales à 1 % lorsqu'une référence comparable est disponible ?
5. Les pics aux points singuliers sont-ils séparés des observables
   d'acceptation ?
6. Les imperfections initiales, les chemins de charge et les éventuelles
   branches instables sont-ils suffisamment documentés ?
7. Les exclusions contact, rupture et dommage sont-elles acceptables ?
8. La recommandation de maintenir le statut `research` est-elle confirmée ?

## Décision attendue du relecteur indépendant

```text
Q1 : ____________________
Q2 : ____________________
Q3 : ____________________
Q4 : ____________________
Q5 : ____________________
Q6 : ____________________
Q7 : ____________________
Q8 : ____________________

Decision : maintain_research / more_evidence_required / bounded_use
Nom      : ____________________
Organisme: ____________________
Date     : ____________________
Signature: ____________________
```

## Règle de maturité

Une réponse positive du relecteur ne suffit pas à promouvoir ce scope vers
`stable` si la convergence, l'erreur à 1 %, la reproductibilité ou la
comparaison externe restent incomplètes. En l'état, le registre conserve le
gate `TET4-TL-C04` ouvert.

