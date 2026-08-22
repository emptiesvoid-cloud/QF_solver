---
doc_id: DOC-RELEASE-V020-ALPHA-FREEZE-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0-alpha
reviewer: ""
approver: ""
---

# Dossier de gel V0.2.0-alpha QF_solver

## Objet

Ce dossier gele le contenu de la release QF_solver 0.2.0-alpha. Il ne cree
pas une nouvelle maturite mecanique. Il consolide les preuves deja produites,
les decisions Owner enregistrees et les limites conservees pour le post-alpha
V0.2.1.

La publication reste suspendue jusqu'a la relecture et a la decision de
Quentin Farinazzo.

## Etat du code et de la release

| Point | Etat |
| --- | --- |
| Branche de travail | `release/v0.2.0-alpha` |
| Historique de gel | `b1e6406` puis consolidation Owner dans le commit courant |
| Version Python | `0.2.0a0` |
| Code | Apache-2.0 |
| Documentation et exemples originaux | CC BY 4.0 |
| Audit public | a relancer apres durcissement du scan de contenu |
| Audit archive | a relancer sur le contenu exact du tag |
| Documentation web MkDocs historique | PASS lors du gel 0.2.0 ; retiree en 0.2.1a0 |
| Ruff et compilation ciblee | PASS |
| Tests documentaires/packaging/evidence/open-source cibles | 39 PASS |
| Suite pytest complete | PASS : 1091 passed, 17 skipped apres corrections de publication |
| Tag de release | a recreer localement apres corrections et nouvelle baseline |
| Push public | non realise |

## Contenu de la V0.2.0-alpha

La release rassemble le noyau de calcul EF, l'API Python et la CLI QF_solver.
Le perimetre gele comprend :

- statique lineaire TET4 isotrope, TET10 isotrope et MITC4 isotrope ;
- modal lineaire, Newmark lineaire et harmonique lineaire pour TET4, TET10 et
  MITC3 dans les domaines bornes acceptes par Owner ;
- MITC4 statique, verification shear-locking, Cook, Scordelis-Lo, cylindre
  pince et chargements de coque ;
- MITC3+ statique, dynamique lineaire et orientation projetee sur geometrie
  courbe, au statut experimental borne ;
- BEAM2 dynamique lineaire et entites discretes ressort-masse dans leur domaine
  SDOF ou lineaire documente ;
- materiaux isotropes, orthotropes solides et composites homogenises/stratifies
  dans les limites de leurs preuves ;
- plasticite J2 TET10 dans le domaine experimental borne documente ;
- contact sans frottement et contact avec frottement dans leurs campagnes
  experimentales respectives ;
- import Gmsh, exports JSON/CSV/VTU, audits boite blanche, rapports Markdown,
  documentation web MkDocs historique, profils de verification et mode grand modele
  optionnel PETSc/MPI.

Les preuves associees comprennent les patch tests, etudes de convergence,
comparaisons analytiques, campagnes Code_Aster et CalculiX, controles de
residu, energie, orthogonalite, masse, qualite de maillage, cartes de champs,
figures de deformee et rapports reproductibles. Les decisions et les limites
restent tracees dans `qualification/reviews/` et `qualification/vnv/`.

## Decisions Owner deja incluses

Le registre `qualification/reviews/owner_review_linear_dynamics_2026-08-02.json`
enregistre les decisions suivantes. Elles sont incluses dans le perimetre
gele, avec leurs limites et recommandations.

| Perimetre | Decision Owner | Limite conservee |
| --- | --- | --- |
| TET4 modal, Newmark, harmonique | accepted_for_bounded_engineering_use | petites deformations, dynamique lineaire |
| TET10 modal, Newmark, harmonique | accepted_for_bounded_engineering_use | raffinement Newmark complementaire recommande |
| MITC3 modal, Newmark, harmonique | accepted_for_bounded_engineering_use | raffinement maillage-frequence recommande |
| BEAM2 dynamique lineaire | accepted_for_bounded_engineering_use | domaine lineaire borne |
| Entites discretes dynamique lineaire | accepted_for_bounded_engineering_use | SDOF translationnel, sans amortissement ni couplage multi-DDL |

La correlation MITC3+ multicouche courbe a orientation projetee est incluse au
statut `experimental_owner_accepted`, selon
`qualification/reviews/mitc3_laminate_curved_projected_2026-08-09.json`.
Le TET10 J2 structurel est inclus pour l'usage experimental borne, selon
`qualification/reviews/tet10_j2_structural_code_aster_2026-08-09.json`.
Le MITC4 multicouche dynamique plan est inclus pour l'usage experimental
borne, selon
`qualification/reviews/mitc4_laminate_dynamic_2026-08-10.json`.

## Preuves et limites de la release

### TET10 J2 complexe

La campagne `VNV-TET10-J2-CODEASTER-COMPLEX-026` compare QF_solver TET10 et
Code_Aster TETRA10 sur un support en L soumis a des charges combinees.

| Indicateur | Valeur | Limite | Etat |
| --- | ---: | ---: | --- |
| RMS deplacement sur le chemin | 0,01245 % | 10 % | PASS |
| Ecart deplacement final | 0,00227 % | 10 % | PASS |
| RMS PEEQ moyenne | 1,84443 % | 15 % | PASS |
| Ratio petites deformations | 1,95357 % | 10 % | PASS |
| Residus QF maximal | 1,972e-09 | 1e-7 | PASS |

Cette preuve reste experimentale. Elle ne couvre pas le cyclage, les grandes
deformations, le contact, le dommage, la rupture ni les pics aux angles
rentrants.

### MITC4 multicouche dynamique

La campagne `VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021` couvre les trois
empilements `[0/90/90/0]`, `[45/-45/-45/45]` et `[0/45/45/0]`, le dernier
avec Newmark amorti.

| Empilement | Modal | Newmark | Harmonique | Etat |
| --- | ---: | ---: | ---: | --- |
| `[0/90/90/0]` | 1,678 % | 0,422 % | 0,205 % | PASS |
| `[45/-45/-45/45]` | 5,528 % | 3,449 % | 1,842 % | PASS |
| `[0/45/45/0]`, amorti | 1,823 % | 0,506 % | 0,305 % | PASS |

Cette famille est acceptee par l'Owner pour un usage engineering experimental
borne. La tentative a 10 000 QUAD4 conserve un
residu modal d'environ `7,383e-6` apres 30 000 iterations, au-dessus du seuil
`1e-7`. Elle ne doit pas etre presentee comme une fermeture de convergence
fine. Les extensions dynamiques courbes, dommage, delaminage et rupture sont
hors scope.

## Travaux post-alpha

Les travaux post-alpha ne font pas partie de la V0.2.0-alpha. Leur contenu
detaille sera defini apres la publication et apres l'audit Owner sur un grand
modele. Aucune fonctionnalite post-alpha n'est utilisee pour augmenter la
maturite de la release gelee.

## Conditions avant tag et publication

1. Relancer les tests longs par lots, puis la campagne complete avec un
   verdict archive et sans timeout. **GATE PASSED : 1091 passed, 17 skipped.**
2. Auditer par l'Owner l'historique Git, les fichiers suivis, les URLs et les
   artefacts publics.
3. Reproduire une histoire publique propre et recreer le tag local
   `v0.2.0-alpha`. Le push public reste interdit jusqu'a l'audit Owner du grand
   modele et au verdict final de confidentialite.

## Decision Owner du 2026-08-10

La decision est enregistree dans
`qualification/reviews/owner_review_v020_alpha_freeze_2026-08-10.json`.

| ID | Reponse Owner | Effet |
| --- | --- | --- |
| Q1 | OUI | Perimetre et exclusions acceptes. |
| Q2 | OUI | Decisions dynamiques du 2 aout incluses. |
| Q3 | OUI | TET10 J2 et MITC3+ courbe acceptes en experimental borne. |
| Q4 | OUI | MITC4 multicouche dynamique accepte pour usage experimental borne avec reserve. |
| Q5 | OUI | Les travaux post-alpha seront definis apres la publication. |
| Q6 | OUI | Le timeout de la suite complete est bloquant avant le tag. |
| Q7 | OUI sous condition | Tag local autorise apres le gate pytest ; push public non autorise. |

## Questions Owner

| ID | Question | Reponse |
| --- | --- | --- |
| Q1 | Le perimetre gele de la V0.2.0-alpha et ses exclusions sont-ils corrects ? | OUI |
| Q2 | Les decisions dynamiques Owner du 2 aout sont-elles incluses sans extrapolation de maturite ? | OUI |
| Q3 | Le TET10 J2 structurel et le MITC3+ courbe sont-ils acceptes dans leurs domaines experimentaux bornes ? | OUI |
| Q4 | Le MITC4 multicouche dynamique reste-t-il experimental avec la reserve modale 10 000 QUAD4 ? | OUI |
| Q5 | Les travaux post-alpha V0.2.1 sont-ils correctement separes de la release ? | OUI, ils seront definis apres publication |
| Q6 | Le timeout de la suite complete doit-il etre traite avant le tag ? | OUI |
| Q7 | L'arbre Git, les licences, les URLs et les artefacts publics sont-ils acceptables ? | OUI sous reserve de l'audit final |
| Q8 | Autorises-tu la creation du tag sans push public ? | OUI, apres le gate pytest |

## Decision

```text
Owner : Quentin Farinazzo
Date : 2026-08-10
Decision : accepted_with_recommendations
Commentaires : tag local autorise apres les gates techniques ; publication
interdite avant la verification finale de confidentialite et du grand modele.


Signature : Quentin Farinazzo (Owner review enregistree)
```

Une decision positive gele le perimetre de publication. Elle ne transforme pas
les fonctions `experimental` en fonctions certifiees ou qualifiees.
