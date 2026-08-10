---
doc_id: QF-REV-LINDYN-001
revision: 0.2
status: superseded_by_owner_decision_2026-08-02
applicable_version: 0.2.0
---

# Dossier preparatoire Owner review - dynamique lineaire

> **Statut historique.** Ce dossier preparatoire est remplace par la decision
> datee du 2 aout 2026 dans
> `qualification/reviews/owner_review_linear_dynamics_2026-08-02.json`.
> Les perimetres dynamiques qu'il presentait comme a examiner ne sont plus
> `ready_for_owner_review`; leur statut courant est porte par
> `qualification/element_analysis_matrix.json` et le registre de cloture.

Ce dossier est une aide a la decision interne. Il ne constitue ni une
certification, ni une revue independante. Une decision doit etre enregistree
par scope; elle ne doit pas etre deduite de ce document global.

## 1. Perimetres presents

| Scope | Etat de preuve | Decision Owner possible | Limite principale |
| --- | --- | --- | --- |
| `discrete-linear-dynamics` | Code_Aster statique, modal, Newmark et harmonique: PASS | Oui, domaine borne | Masse translationnelle et ressort global seuls |
| `beam2-linear-dynamics` | Code_Aster Newmark et harmonique axiaux: PASS | Oui, domaine axial borne | Flexion/cisaillement Timoshenko dynamiques ouverts |
| `tet10-modal` | Masse coherente, modal et reference analytique: PASS | Oui, modal borne | Decision distincte; pas de dynamique externe |
| `tet10-transient-dynamic` | Preuve interne uniquement | Non | Convergence et correlation externe manquantes |
| `tet10-harmonic-response` | Preuve interne uniquement | Non | Convergence et correlation externe manquantes |
| `mitc3-modal` | Preuve interne uniquement | Non | Libre-libre, courbure et correlation externe manquants |
| `mitc3-transient-dynamic` | Preuve interne uniquement | Non | Pas de temps et correlation externe manquants |
| `mitc3-harmonic-response` | Preuve interne uniquement | Non | Contraintes frequentielles et correlation externe manquantes |

## 2. Preuves a lire

1. Ressort-masse: `qualification/vnv/external/code_aster_discrete/reference/report.md`
   et `summary.json`. Les ecarts statique, modal, Newmark et harmonique sont
   dans les checks machine-readable.
2. BEAM2: `qualification/vnv/external/code_aster_beam2_newmark/reference/report.md`
   et `summary.json`. Le deck compare le chemin axial uniquement avec
   `POU_D_E` Code_Aster 18.1.0.
3. TET10 modal: `qualification/vnv/linear_dynamic_families/tet10/report.md`
   et `qualification/vnv/tet10_mass_modal_loads/reference/report.md`.
4. Matrice complete: `qualification/element_analysis_matrix.json`.
5. Registre de cloture: `qualification/reviews/linear_dynamic_closure_register.json`.

## 3. Questions Owner - ressort-masse

| ID | Question | Reponse | Commentaire / evidence |
| --- | --- | --- | --- |
| D-01 | Le domaine masse translationnelle + ressort global est-il compris et accepte ? | `a renseigner` | `a renseigner` |
| D-02 | Les ecarts Code_Aster statique, modal, Newmark et harmonique sont-ils acceptables ? | `a renseigner` | `a renseigner` |
| D-03 | Les exclusions (inertie de rotation, couplages, excentricite) sont-elles visibles ? | `a renseigner` | `a renseigner` |
| D-04 | Decision `discrete-linear-dynamics` | `a renseigner` | `a renseigner` |

## 4. Questions Owner - BEAM2

| ID | Question | Reponse | Commentaire / evidence |
| --- | --- | --- | --- |
| B-01 | Le domaine axial lineaire est-il compris et accepte ? | `a renseigner` | `a renseigner` |
| B-02 | Les histoires Newmark et reponses harmoniques Code_Aster sont-elles acceptables ? | `a renseigner` | `a renseigner` |
| B-03 | Les exclusions flexion/cisaillement dynamique, amortissement et assemblages sont-elles acceptables ? | `a renseigner` | `a renseigner` |
| B-04 | Decision `beam2-linear-dynamics` | `a renseigner` | `a renseigner` |

## 5. Questions Owner - TET10 modal

| ID | Question | Reponse | Commentaire / evidence |
| --- | --- | --- | --- |
| T-01 | La masse coherente, les residus et orthogonalites modales sont-ils acceptables ? | `a renseigner` | `a renseigner` |
| T-02 | La convergence de frequence et la reference poutre sont-elles adequates au domaine borne ? | `a renseigner` | `a renseigner` |
| T-03 | Les exclusions Newmark/harmonique sont-elles explicitement conservees ? | `a renseigner` | `a renseigner` |
| T-04 | Decision `tet10-modal` | `a renseigner` | `a renseigner` |

## 6. Signature

| Champ | Valeur |
| --- | --- |
| Owner reviewer / approver | `a renseigner` |
| Date | `a renseigner` |
| Revision source | `a renseigner` |
| Signature | `a renseigner` |

Les decisions possibles sont `accepted_for_bounded_engineering_use`,
`accepted_with_recommendations`, `more_evidence_required` ou `rejected`.
Toute decision devra etre enregistree dans un JSON date sous
`qualification/reviews/`, sans modifier retrospectivement les preuves.
