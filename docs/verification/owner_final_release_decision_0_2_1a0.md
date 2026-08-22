---
doc_id: DOC-OWNER-REL-021-FINAL-001
revision: 0.1
status: owner_decision_recorded
applicable_version: 0.2.1a0
owner_review: accepted_for_release_preparation
certification_claim: none
---

# Decision finale Owner - QF_solver 0.2.1a0

## Objet

Cette fiche prepare la decision de publication de `0.2.1a0`. Elle ne cree ni
commit, ni tag, ni publication PyPI. Une decision positive autorise seulement
la preparation du checkout de release propre.

## Etat technique au 22 aout 2026

| Controle | Etat | Preuve |
| --- | --- | --- |
| Campagne engineering | PASS, 13/13 cas | `results/release_vv_0_2_1_campaign_replay_20260822/campaign/qualification_campaign_summary.json` |
| Scopes stables | 28 PASS | `qualification/element_analysis_matrix.json` |
| Scopes bornes/recherche | 8, non bloquants pour le gate stable | registre de maturite et exclusions ci-dessous |
| Audit public | PASS, 1554 fichiers, 0 finding | `qualification/publication_audit_0_2_1.json` |
| Distribution locale | PASS | `results/distribution_preflight_0_2_1/` |
| Checkout Git | ouvert | nettoyage requis avant tag |

## Perimetre stable publie

TET4/TET10 lineaires, MITC3+ classique, MITC4 isotrope, MITC4 multicouche
plane et orthotrope mono-pli, BEAM2, entites discretes lineaires et solides
orthotropes dans les geometries, chargements, maillages et analyses documentes.
Les documents V&V associes definissent les exclusions exactes.

## Perimetres livres mais non stables

| Scope | Statut conserve | Limite principale |
| --- | --- | --- |
| TET4/TET10 J2 | `accepted_for_bounded_engineering_use` | petites deformations, pas de dommage/rupture/contact general |
| TET4 total-lagrangien structurel | `research` | campagne grande taille arretee par limite ressources |
| MITC3 multicouche general et courbe axial | `accepted_for_bounded_engineering_use` | layups/geometries limites, contraintes hors-plan exclues |
| Contact normal et frottant | `accepted_for_bounded_engineering_use` / `experimental` | petits glissements et domaines de contact documentes |
| Grand modele TET4 | `accepted_for_bounded_engineering_use` | configuration PETSc/MPI mesuree uniquement |
| MITC4 orthotrope courbe | `out_of_acceptance` | diagnostic interne sans revendication d'usage |

## Questions de decision

Decision Owner enregistree le 22 aout 2026 :

| Question | Decision |
| --- | --- |
| Q1 - Perimetre stable et limites | `OUI` |
| Q2 - Huit perimetres non stables exclus des revendications stables | `OUI` |
| Q3 - Campagne 13/13 et audits | `OUI` |
| Q4 - Nettoyage Git avant tag/PyPI | `OUI` |
| Q5 - Decision Owner | `accepted_for_release_preparation` |

## Enregistrement Owner

- Owner : Quentin Farinazzo
- Date : 2026-08-22
- Decision : `accepted_for_release_preparation`
- Commentaire : Les criteres techniques sont respectes, les limites sont
  visibles, les scopes non stables sont isoles. Le nettoyage Git et le rejeu
  final restent obligatoires avant toute publication.
- Renommage du dossier local externe : non requis et laisse hors perimetre.
- Signature ou reference d'enregistrement : decision Owner declaree dans ce document

Une decision Owner n'est pas une certification externe. Elle doit etre
enregistree dans `qualification/reviews/` avant la creation d'un tag.
