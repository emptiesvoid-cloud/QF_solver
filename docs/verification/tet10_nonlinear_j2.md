---
doc_id: DOC-VNV-TET10-NL-J2-001
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# V&V TET10 non lineaire J2

Cette etude verifie le chemin non lineaire petits deformations du TET10 avec
plasticite J2 isotrope et ecrouissage isotrope. Elle ne couvre ni les grandes
deformations, ni le flambement, ni la plasticite cinematique, ni le dommage.

## Modele et reference

Une barre 3D est maillee en TET10 droits. Une traction repartie uniforme est
appliquee sur la face opposee a l'encastrement axial. Deux blocages ponctuels
retirent les modes rigides transverses sans imposer artificiellement la
contraction de Poisson. Le chargement signe contient chargement, decharge,
inversion et rechargement.

La reference est le retour radial J2 uniaxial du meme materiau, evalue
independamment a chaque increment. Le critere compare la deformation plastique
equivalente commise et la contrainte axiale moyenne de la barre. Chaque TET10
utilise les quatre points de Hammer; l'etat interne est donc porte et restitue
par point d'integration.

## Preuves et resultats

La campagne `VNV-J2-TET10-CYCLIC-001` produit le maillage, le modele, les
resultats JSON, le VTU, la courbe du cycle et un resume machine-readable dans
`qualification/vnv/tet10_nonlinear_j2/reference/`.

Les limites automatiques sont les suivantes : erreur relative du chemin
plastique `<= 1e-8`, erreur de contrainte axiale `<= 1e-8`, residu relatif par
increment `<= 1e-7`. La campagne est `PASS_INTERNAL` avec une erreur de chemin
plastique de `8.73e-10`, une erreur de contrainte de `5.96e-11` et un residu
maximal de `4.14e-9`.

![Cycle J2 TET10](../assets/generated/tet10_j2_cyclic_response.png){ .result-figure }

## Conclusion et limite de maturite

Le couple TET10 plus J2 est desormais `verified_development_external_correlation`
pour cette barre homogene, le chemin cyclique et le material point de reference.
Une correlation structurelle externe TET10/TETRA10 avec Code_Aster est disponible
dans la page dediee au benchmark structurel. Le statut reste `experimental` et
ne devient pas `owner_accepted` sans Owner review, geometrie plus complexe et
chargement non monotone trace.
