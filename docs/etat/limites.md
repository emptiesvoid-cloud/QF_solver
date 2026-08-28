---
doc_id: DOC-STATE-003
revision: 0.4
status: draft
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Limites connues

## Limites de la release 0.2.5a0

- Les claims sont bornes par famille d'elements, formulation, maillage,
  chargement, historique et domaine de deformation effectivement preuves.
- Le J2 qualifie est le modele small-strain existant. Il ne couvre pas une
  plasticite finite-strain generale, un ecrouissage anisotrope ou une
  validation physique universelle.
- G02 qualifie l'elasticite Total-Lagrangian TET4/HEX8 dans le domaine
  pre-limite teste avec `det(F) > 0`. TET10/HEX20 finite-kinematic et J2
  finite-kinematic restent experimentaux.
- G03 qualifie un premier seuil d'instabilite tangentielle sparse dans le
  domaine mesure. Ce n'est pas une prediction generale de ruine,
  post-flambement ou sensiblite aux imperfections.
- G05 est borne au contact sans frottement noeud/patch vers surface
  triangulee, avec la recherche et les transitions documentees. Il ne s'agit
  pas d'une formulation mortar, segment-a-segment, auto-contact ou impact.
- L'arc-length FEM complet, les chemins J2 finite-kinematic et les couplages
  non lineaires restent `EXPERIMENTAL / NOT QUALIFIED` ou `DEFERRED`.
- Le contact avec frottement est `NOT IN RELEASE SCOPE`; la friction n'est pas
  une capacite de production de cette alpha.
- Les comparaisons Code_Aster et CalculiX sont des correlations numeriques
  bornees. Elles ne constituent pas une certification logicielle ou physique.
- Aucune revendication nouvelle de solveur non lineaire a plusieurs millions
  de DDL n'est faite. PETSc/SLEPc restent optionnels et non obligatoires.

## Limites numeriques

- Le conditionnement, le preconditionneur et la disponibilite des backends
  influencent les solveurs iteratifs.
- Les chemins sparse sont privilegies, mais certains post-traitements et
  configurations modales peuvent encore consommer une memoire importante.
- Les performances publiees sont des mesures de caracterisation sur les
  configurations tracees, pas des garanties de scaling universel.
- Les methodes non lineaires hors scope qualifie doivent faire l'objet d'une
  revue du modele, des residus, de la convergence et des etats internes.

## Limites de preuve

Les preuves controllees sont rattachees a un SHA source, a un environnement et
a des empreintes d'artefacts. Une modification du code numerique ou d'une
donnee de qualification impose une nouvelle campagne pour les preuves
affectees. Les artefacts generes apres checkout sont des sorties derivees et
ne doivent pas etre edites manuellement.

La roadmap post-release est volontairement prudente : `0.2.6` vise la maturite,
la V&V, la robustesse et la scalabilite ; `0.2.7` est le candidat pour une
formulation J2 finite-strain et la requalification G06.
