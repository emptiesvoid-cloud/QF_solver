---
doc_id: DOC-STATE-003
revision: 0.3
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Limites connues

## Limites mecaniques

- Formulations en petits deplacements; pas de cinematique de grandes rotations
  qualifiee.
- Elasticite isotrope uniquement pour le perimetre solide stable.
- TET4 sensible au verrouillage volumique lorsque $\nu\rightarrow0.5$ et peu
  adapte aux gradients de contrainte avec un maillage grossier.
- TET10 courbe controle par echantillonnage du Jacobien, sans preuve globale de
  positivite sur tout le volume parametrique.
- MITC4 fonde sur Reissner-Mindlin; le traitement du cisaillement reduit le
  locking sans supprimer l'obligation d'une etude de convergence.
- Plasticite J2 et solveurs de chemin non lineaire maintenus hors du perimetre
  qualifiable courant.
- Le MITC4 composite reste experimental et limite a la statique lineaire. Les
  effets thermiques, la masse dynamique composite, les criteres de rupture,
  la delamination et l'endommagement ne sont pas disponibles.
- `BEAM2`, ressorts, masses concentrees, MPC/RBE et contact sont disponibles.
  Le contact sans frottement est `engineering_ready_bounded` uniquement dans
  sa campagne acceptee; toutes les extensions restent `experimental`. Les proprietes
  de section BEAM2 variables, les poutres courbes, la dynamique de poutres
  epaisses et les correlations externes d'assemblages deformables sont
  ouvertes. Un bras RBE2 ponctuel est correle a Code_Aster, mais RBE3 et les
  reactions de multiplicateurs externes ne le sont pas.
- Le contact V1 est borne aux petites transformations, a la statique lineaire
  et au couple noeud-triangle. Le mode `updated` reconstruit de facon bornee
  la facette et sa normale sans frottement; un patch de trois noeuds et une
  recherche Code_Aster autonome sur surface pliee sont correles. Le grand
  glissement, les faces EF deformables generalisees, le contact thermique,
  l'usure, la cohesion et les lois dependantes de la vitesse sont reportes en
  V2.
- La transition de contact doit etre raffinee. La correlation passe de
  `5,2565 %` sur `576` TET4 a `4,3400 %` sur `768` TET4, puis a
  `3,3029e-12 %` sur `9 984` TET4 face a Code_Aster.
- Pour le frottement, seule la branche de glissement sature est correlee a
  Code_Aster. L'adhesion depend de regularisations tangentielles non encore
  equivalentes; elle ne doit pas etre presentee comme une correlation externe.
- HEX8, WEDGE, PYRAMID, thermique, thermoelasticite et les autres extensions
  multiphysiques sont volontairement reportes en V2.

## Limites numeriques

- Les methodes iteratives restent dependantes du conditionnement et du
  preconditionneur.
- Le solveur dense modal est refuse au-dela d'une limite explicite; `eigsh`
  est la voie normale pour les matrices creuses.
- Le mode standard materialise le post-traitement en memoire et n'est pas la
  voie des modeles a plusieurs millions de ddl.
- Le backend PETSc/MPI est optionnel et n'est pas qualifie multi-rang.
- Les temps de calcul publies sont indicatifs et ne sont jamais un critere
  mecanique d'acceptation.

## Limites documentaires

Les champs de revue du site restent `a affecter` tant qu'un ingenieur
mecanique et un specialiste des methodes numeriques n'ont pas signe la page.
Le depot ne possedant pas encore de revision Git de reference, un build de
profil `qualification` doit etre refuse.
