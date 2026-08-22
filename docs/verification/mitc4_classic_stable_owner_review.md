---
doc_id: DOC-OWNER-MITC4-CLASSIC-STABLE-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
promotion_target: stable
scope: mitc4-linear-static, mitc4-modal, mitc4-transient-dynamic, mitc4-harmonic-response
date: 2026-08-21
---

# Owner review — MITC4 classique, statique et dynamique linéaire

Cette revue porte uniquement sur le MITC4 isotrope homogène, en petits
déplacements, pour des coques facettisées admissibles. Elle ne couvre pas les
stratifiés, les grandes rotations, le contact, l'endommagement ni les charges
dynamiques non linéaires.

## Synthèse quantitative

| Scope | Observable primaire fine | Valeur | Limite | Statut |
| --- | --- | ---: | ---: | --- |
| `mitc4-linear-static` | différence Code_Aster de déplacement | `0,726108 %` | `1 %` | PASS |
| `mitc4-modal` | erreur maximale de fréquence, 10 modes | `0,782014 %` | `1 %` | PASS |
| `mitc4-modal` | MAC minimal | `0,99999981` | `0,95` | PASS |
| `mitc4-transient-dynamic` | RMS Newmark contre propagation modale | `0,09867227 %` | `1 %` | PASS |
| `mitc4-transient-dynamic` | dérive énergétique sans amortissement | documentée | `1e-4` | PASS |
| `mitc4-harmonic-response` | erreur finale de réponse harmonique | `0,547102 %` | `1 %` | PASS |
| `mitc4-harmonic-response` | limite statique à `0 Hz` | `4,519e-11` | `1e-8` | PASS |

Les niveaux intermédiaires dépassant parfois `1 %` restent archivés. La
promotion proposée repose sur les niveaux finaux explicitement déclarés et ne
masque pas l'historique de convergence. Pour le transitoire, les écarts de
pics Code_Aster liés à la différence de formulation spatiale restent des
diagnostics séparés; la grandeur primaire de Newmark est l'erreur RMS face à
la propagation modale indépendante.

## Domaine proposé

Plaques et coques facettisées MITC4 isotropes, matériau homogène, épaisseur
constante, intégration `2x2`, quatre points de tying, masse cohérente pour les
cas dynamiques et chargements linéaires déclarés. Les critères de maillage
restent aspect ratio `<= 10`, warpage `<= 5 degrés`, angles internes entre
`30` et `150 degrés` et planéité conforme au périmètre MITC4.

Les stratifiés, l'amortissement calibré, les géométries courbes fortement
distordues, le dommage, la délamination et les contraintes ponctuelles aux
singularités restent exclus de cette cible stable. Le MITC4 multicouche
dynamique conserve son dossier expérimental séparé.

## Questions Owner

### Q1 — Statique

La convergence et la corrélation finale sous `1 %` couvrent-elles le domaine
MITC4 isotrope statique explicitement borné ?

Réponse Owner : `OUI`.

### Q2 — Modal

Les dix fréquences, le MAC minimal `0,99999981` et les résidus modaux sont-ils
suffisants pour promouvoir le MITC4 modal dans ce domaine ?

Réponse Owner : `OUI`.

### Q3 — Newmark

L'erreur RMS `0,09867227 %`, la stabilité énergétique et les exclusions
déclarées sont-elles acceptables pour le domaine transitoire sans amortissement
calibré ?

Réponse Owner : `OUI`.

### Q4 — Harmonique

L'erreur finale `0,547102 %`, la réponse finie et la limite statique à `0 Hz`
suffisent-elles pour le domaine harmonique déclaré ?

Réponse Owner : `OUI`.

### Q5 — Limites

Les exclusions des stratifiés, grandes rotations, contact, dommage,
délamination, fortes distorsions et singularités ponctuelles sont-elles
explicites et acceptables ?

Réponse Owner : `OUI`.

### Q6 — Décision

Décision Owner enregistrée : `stable` pour les quatre scopes isotropes
classiques, dans le domaine documenté. Le registre machine-readable conserve
`accepted_with_recommendations` avec une cible `stable`.

Décision statique : `stable`

Décision modale : `stable`

Décision Newmark : `stable`

Décision harmonique : `stable`

Owner : Quentin Farinazzo (déclaration électronique)

Date : 2026-08-21

## Traçabilité

- Statique : `output/pdf/mitc4_static_code_aster_refinement_owner_review.pdf`.
- Modal : `output/pdf/mitc4_modal_refinement_owner_review.pdf`.
- Harmonique : `output/pdf/mitc4_harmonic_refinement_owner_review.pdf`.
- Campagne transitoire et métriques : `qualification/maturity_criteria_0_2_1.json`.
- Périmètre exclu multicouche : `docs/verification/mitc4_laminate_dynamic_extended_owner_review.md`.

La signature Owner doit être enregistrée dans un fichier JSON dédié avant toute
modification de la matrice de maturité ou du gate de release.
