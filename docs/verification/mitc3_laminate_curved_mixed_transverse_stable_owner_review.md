---
doc_id: DOC-OWNER-MITC3-LAM-CURVED-MT-STABLE-001
revision: 0.1
status: owner_confirmed_pending_audit_application
review_mode: owner_review
promotion_target: stable
scope: mitc3-laminate-static-curved-mixed-transverse
---

# Owner review : MITC3 multicouche courbe, mixte et transverse

Ce dossier propose un sous-périmètre explicite de la campagne courbe MITC3+.
Il ne revendique pas la stabilité du chargement axial : celui-ci reste exclu
à cause de son incrément de maillage supérieur à 5 % et de sa divergence de
comparaison lors du raffinement ciblé.

## Domaine proposé

Le domaine est limité à un panneau cylindrique facettisé, à l'empilement
symétrique `[0/90/90/0]`, à une orientation globale projetée sur chaque
facette, aux petits déplacements et aux chargements mixte et transverse.
L'observable primaire est le vecteur de déplacement hors des singularités.

| Observable | Mixte | Transverse | Limite |
| --- | ---: | ---: | ---: |
| Écart QF_solver / Code_Aster au niveau `64x32` | 0,5780 % | 0,4975 % | 1 % |
| Incrément de maillage QF_solver | 4,4755 % | 4,6023 % | 5 % |
| Résidu libre QF_solver | 5,22e-11 | 3,03e-9 | 1e-8 |
| Erreur de projection d'orientation | 1,48e-6 deg | 1,48e-6 deg | 1e-4 deg |

## Exclusions obligatoires

Le chargement axial, les autres géométries courbes, les empilements non
symétriques, la dynamique courbe, les contraintes par pli comme observable
d'acceptation, `S13/S23`, les singularités, le dommage, la rupture et la
délamination restent hors de ce sous-périmètre.

## Confirmation Owner du 22 aout 2026

Decision Owner declaree : **stable borne** pour les chargements mixte et
transverse sur le panneau cylindrique facettise, l'empilement `[0/90/90/0]`
et l'orientation projetee. Cette confirmation est un enregistrement
electronique de decision ; elle n'est pas une signature manuscrite et ne vaut
pas promotion du scope axial general.

La marge proche de `5 %` sur le dernier increment de maillage reste une
recommandation. La seconde geometrie, les autres layups, la dynamique courbe,
les contraintes interlaminaires, le dommage et la delamination restent exclus.

## Questions Owner

### Q1 — Domaine

Le domaine limité au panneau cylindrique facettisé, à l'empilement
`[0/90/90/0]`, à l'orientation projetée et aux chargements mixte/transverse
est-il suffisamment défini pour une cible `stable` ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Convergence et corrélation

Les erreurs inférieures à 1 %, les incréments inférieurs à 5 % et les
résidus documentés sont-ils acceptables pour ce sous-périmètre ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Exclusions

L'exclusion explicite du chargement axial et des phénomènes interlaminaires,
de dommage et de délamination est-elle acceptable ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Décision

Décision proposée : `stable / accepted_with_recommendations /
accepted_for_bounded_engineering_use / more_evidence_required`.

Signature Owner :

Date :

## Références et artefacts

- `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` ;
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_refinement_027/reference/` ;
- `qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/` ;
- `docs/verification/mitc3_laminate_curved_code_aster.md`.

La décision ne doit pas être extrapolée au scope général
`mitc3-laminate-static-curved` ni au chargement axial.
