---

doc_id: DOC-OWNER-MITC3-CLASSIC-STABLE-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
promotion_target: stable
scope: mitc3-modal, mitc3-transient-dynamic, mitc3-harmonic-response
date: 2026-08-21
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner review — MITC3 isotrope classique

Cette revue concerne le MITC3 isotrope plane en dynamique linéaire. Elle est
strictement séparée du MITC3 stratifié, du MITC3 courbe à orientation projetée
et des contraintes par pli. La corrélation externe utilise Code_Aster DKT/
TRIA3 comme oracle complémentaire; elle ne signifie pas identité de
formulation.

## Résultats de la campagne de raffinement

| Maillage | Triangles | Erreur modale | Erreur Newmark | Erreur harmonique |
| ---: | ---: | ---: | ---: | ---: |
| `8x2` | 32 | `7,719395 %` | `1,453716 %` | `0,787341 %` |
| `16x4` | 128 | `1,736652 %` | `0,549633 %` | `0,299811 %` |
| `24x6` | 288 | `0,673329 %` | `0,174158 %` | `0,096638 %` |

Les incréments de fréquence entre les deux derniers niveaux sont `0,128902 %`
pour QF_solver et `0,038776 %` pour Code_Aster. Les valeurs grossières
supérieures à `1 %` restent dans l'historique; la proposition s'appuie sur le
niveau final identifié et ne les efface pas.

## Invariants internes

| Contrôle | Valeur | Limite | Statut |
| --- | ---: | ---: | --- |
| Résidu modal maximal | `4,391e-9` | `1e-8` | PASS |
| Orthogonalité masse | `2,310e-16` | `1e-8` | PASS |
| Orthogonalité raideur | `4,017e-11` | `1e-8` | PASS |
| RMS Newmark contre premier mode | `0,014369 %` | `1 %` | PASS |
| Dérive énergétique | `6,877e-13` | `1e-4` | PASS |
| Résidu dynamique maximal | `6,556e-14` | `1e-7` | PASS |
| Limite harmonique à `0 Hz` | `1,521e-13` | `1e-8` | PASS |

## Domaine proposé

Coques MITC3 isotropes planes, matériau homogène, petits déplacements,
épaisseur constante, chargement linéaire, modal, Newmark moyen accélération
et harmonique sans amortissement calibré. Les maillages doivent respecter les
contrôles de qualité MITC3 et les résultats ponctuels sur singularités restent
informatifs uniquement.

Sont exclus : coques courbes, stratifiés, couplage matériau non symétrique,
amortissement calibré, non-linéarité, contact, grandes rotations, contraintes
par pli et dommage. Ces exclusions sont obligatoires pour la cible stable.

## Questions Owner

### Q1 — Maillage

Les niveaux `8x2`, `16x4` et `24x6`, avec le niveau final sous `1 %`, sont-ils
suffisants pour le cas isotrope plane explicitement borné ?

Réponse Owner : `OUI`.

### Q2 — Modal

L'erreur modale finale `0,673329 %`, le résidu et les orthogonalités sont-ils
acceptables pour ce périmètre ?

Réponse Owner : `OUI`.

### Q3 — Newmark et harmonique

Les erreurs finales `0,174158 %` et `0,096638 %`, ainsi que les invariants
énergétiques et la limite à `0 Hz`, sont-ils acceptables ?

Réponse Owner : `OUI`.

### Q4 — Oracle externe

La corrélation Code_Aster DKT/TRIA3 est-elle acceptable comme vérification
complémentaire, en conservant explicitement la différence de formulation ?

Réponse Owner : `OUI`.

### Q5 — Exclusions

Les exclusions des coques courbes, stratifiés, amortissement calibré,
non-linéarité, contact, grandes rotations, contraintes par pli et dommage
sont-elles suffisamment visibles et acceptables ?

Réponse Owner : `OUI`.

### Q6 — Décision

Décision Owner enregistrée : `stable` pour les trois scopes classiques
isotropes plans. Le registre machine-readable conserve
`accepted_with_recommendations` avec une cible `stable`.

Décision modal :

Décision Newmark :

Décision harmonique :

Owner : Quentin Farinazzo (déclaration électronique)

Date : 2026-08-21

## Traçabilité

- `qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json`
- `qualification/evidence/linear_dynamic_families_2026-08-14/mitc3/summary.json`
- `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/mitc3_dynamic/summary.json`
- `qualification/reviews/mitc3_dynamic_refinement_owner_review_pending.json`
- `qualification/vnv/mitc3_dynamic_extended/reference/summary.json`

La décision Owner ne modifie pas le statut du MITC3 stratifié ou courbe. Une
promotion stable éventuelle ne concerne que les trois scopes isotropes de ce
dossier.
