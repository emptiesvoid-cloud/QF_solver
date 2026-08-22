---

doc_id: DOC-OWNER-MITC3-LAM-DYN-DKT-THIN-001
revision: 0.1
status: owner_confirmed_pending_audit_application
review_mode: owner_review
promotion_target: stable
scope: mitc3-laminate-dynamic-thin-planar
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner Review — MITC3+ multicouche dynamique, sous-périmètre mince

Cette revue porte uniquement sur un stratifié plan symétrique `[0/90/90/0]`,
en petits déplacements, avec un rapport épaisseur/longueur de `0,01`. La
référence externe Code_Aster utilise `DKT/TRIA3`, interprété comme référence de
limite mince. Elle ne remplace pas la campagne `DST`, qui reste une preuve
diagnostique distincte.

## Résultats

| Maillage | Triangles | Modal | Newmark RMS | Harmonique | Résidu modal | Résidu dynamique |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `12x3` | 72 | `3,1228 %` | `0,2027 %` | `0,0862 %` | `3,96e-9` | `1,09e-11` |
| `16x4` | 128 | `1,3705 %` | `0,0813 %` | `0,0168 %` | `8,03e-9` | `1,68e-11` |
| `24x6` | 288 | `0,3940 %` | `0,1968 %` | `0,0880 %` | `1,08e-8` | `5,11e-11` |

Le niveau fin est inférieur à `1 %` pour les trois observables principales.
Les niveaux intermédiaires restent publiés, notamment le dépassement modal à
`12x3` et `16x4`; ils ne sont pas supprimés ni remplacés par le seul résultat
final.

## Confirmation Owner du 22 aout 2026

Decision Owner declaree : **stable**, strictement pour le sous-perimetre mince,
plan, symetrique et documente dans cette page. Cette confirmation est un
enregistrement electronique de decision ; elle n'est pas une signature
manuscrite et ne constitue pas une revue independante.

Les niveaux intermediaires restent publies, le leger depassement du residu
modal strict `1e-8` reste une recommandation, et aucune extension aux coques
epaisses, courbes, amorties, non symetriques, endommagees ou delaminees n'est
autorisee.

## Questions Owner

### Q1 — Domaine revendiqué

Le domaine « MITC3+ stratifié plan mince symétrique `[0/90/90/0]`, petits
déplacements, modal/Newmark/harmonique » est-il suffisamment borné ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Résultats sous 1 %

Les valeurs fines `0,3940 %`, `0,1968 %` et `0,0880 %` sont-elles acceptables
pour ce sous-périmètre ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Niveaux intermédiaires

La conservation des niveaux `12x3` et `16x4`, dont l'erreur modale dépasse
encore `1 %`, permet-elle une décision honnête fondée sur le niveau fin et la
tendance documentée ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Référence DKT

DKT est-il acceptable comme référence de limite mince, tout en conservant
explicitement la différence de formulation avec MITC3+ ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q5 — Exclusions

Les exclusions des coques épaisses, courbes, non symétriques, du couplage `B`
non nul, de l'amortissement calibré, des contraintes dynamiques par pli, du
dommage et de la délamination sont-elles acceptables ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q6 — Décision

Décision proposée : `stable` pour ce sous-périmètre, `accepted_with_recommendations`,
`accepted_for_bounded_engineering_use` ou `more_evidence_required`.

Décision Owner :

Signature :

Date :

## Artefacts

- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/report.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/mitc3_laminate_dynamic_refinement.png`
- `qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/summary.json`
- `qualification/vnv/mitc3_mass_quadrature_audit_2026-08-21/summary.json`
- `docs/verification/mitc3_dynamic_causal_audit_2026-08-21.md`
