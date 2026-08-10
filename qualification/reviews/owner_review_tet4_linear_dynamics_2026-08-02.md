---
doc_id: QF-REV-TET4-DYN-020
revision: 0.1
status: owner_accepted_with_supplementary_refinement
applicable_version: ">=0.3.0"
---

# Owner review - TET4 dynamique lineaire

## Identification

| Champ | Valeur |
| --- | --- |
| Famille | TET4 isotrope 3D, petites deformations |
| Etude principale | `VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020` |
| Oracle externe | Code_Aster 18.1.0 `3D/TETRA4`, image Docker epinglee |
| Preuve | `qualification/vnv/tet4_dynamic_code_aster/reference/summary.json` |
| Revision source | `a renseigner` |
| Date | `2026-08-02` |
| Owner reviewer / approver | `Quentin Farinazzo` |

## Resultats a examiner

| Chemin | Ecart QF_solver / Code_Aster | Seuil | Statut |
| --- | ---: | ---: | --- |
| Modal, six frequences | `1,34e-10 %` | 5 % | PASS |
| Newmark, meme grille temporelle | `3,38e-10 %` RMS | 5 % | PASS |
| Harmonique, meme grille frequentielle | `1,02e-10 %` RMS | 5 % | PASS |
| Increment modal du maillage final | `3,417 %` | 10 % | PASS |
| Raffinement temporel Newmark | `1,281 %` RMS | `5,115 %` RMS | PASS |

Le diagnostic de fleche statique au raffinement vaut `42,01 %`, mais il est
non bloquant pour cette etude dynamique: le chargement est nodal et sa
distribution change lorsque la face libre est remaillee. Les campagnes
statiques TET4 a chargements coherents restent la preuve a utiliser pour la
convergence en contrainte et en fleche.

La campagne complementaire `VNV-TET4-DYNAMIC-SPATIAL-REFINEMENT-021` porte le
maillage a **9 893 TET4** sous charge resultante conservee. Son increment final
de fleche vaut `3,745 %`, sous la limite de `10 %`. Elle est une preuve interne
de convergence spatiale; la correlation Code_Aster meme maillage demeure la
preuve externe pour modal, Newmark et harmonique.

## Questions Owner

| ID | Question | Reponse Owner | Commentaire / evidence |
| --- | --- | --- | --- |
| Q1 | Les hypotheses TET4 lineaires, isotropes et les DDL translationnels sont-ils acceptes ? | `oui` | Domaine borne accepte. |
| Q2 | Les six frequences, residus et la masse coherente sont-ils acceptables ? | `oui` | Modal accepte. |
| Q3 | Newmark montre-t-il une convergence temporelle et une correlation externe suffisantes ? | `oui` | Transitoire accepte. |
| Q4 | La reponse harmonique complexe et les frequences hors resonance sont-elles acceptables ? | `oui` | Harmonique accepte. |
| Q5 | Le diagnostic de fleche nodale et la separation avec les campagnes statiques sont-ils compris ? | `oui` | Raffinement complementaire a 9 893 TET4 ajoute. |
| Q6 | Les exclusions sont-elles suffisantes et visibles ? | `oui` | Non-linearites et contact dynamique exclus. |

## Decision par scope

Une decision doit etre renseignee separement pour `tet4-modal`,
`tet4-transient-dynamic` et `tet4-harmonic-response`.

| Scope | Decision | Domaine accepte | Exclusions / recommandations |
| --- | --- | --- | --- |
| `tet4-modal` | `accepted_for_bounded_engineering_use` | TET4 isotrope, petits deplacements, masse coherente | Non-linearite dynamique exclue. |
| `tet4-transient-dynamic` | `accepted_for_bounded_engineering_use` | Newmark lineaire, charges tabulees, amortissement documente | Contact et grandes transformations exclus. |
| `tet4-harmonic-response` | `accepted_for_bounded_engineering_use` | Reponse lineaire hors resonance non amortie | Contact harmonique et amortissement non proportionnel exclus. |

Les valeurs admises sont `accepted_for_bounded_engineering_use`,
`accepted_with_recommendations`, `more_evidence_required` ou `rejected`.
Cette revue ne constitue pas une certification externe.
