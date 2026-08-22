---
doc_id: DOC-REF-004
revision: 0.2
status: suivi
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Feuille de route

La feuille de route autoritative reste `prochaines_etapes.md`. Les blocs
fonctionnels V1 sont integres : `BEAM2`, ressorts, masses, MPC/RBE, contact
borne et MITC3+ disposent de preuves, limites et decisions Owner separees.
Les priorites restantes sont volontairement de nature publication, evidence
complementaire ou V2 :

1. terminer la preparation de publication V1 : `external_audit` de l'historique,
   choix de licence, URLs publiques, archive relue, CI Linux et tag de la
   revision approuvee;
2. conserver visibles les ecarts MITC4 statiques encore ouverts : audit
   independant du cas Cook, puis comparaison externe des contraintes de faces
   et de l'energie du panneau conique. Les deplacements et la resultante sont
   deja correles a Code_Aster sur le meme maillage;
3. conserver la reference NAFEMS triangulaire MITC3+ comme recommandation
   supplementaire non bloquante, sans changer le scope deja accepte;
4. traiter les stratifies dynamiques MITC3/MITC4 comme scopes distincts :
   correlation externe par pli, cas courbe a orientation projetee et nouvelle
   Owner review avant toute hausse de maturite;
5. etendre la politique de solveurs aux matrices dynamiques distribuees PETSc
   seulement avec un post-traitement par blocs et des preuves propres;
6. reporter en V2 le grand glissement, l'usure, la cohesion, le dommage, la
   delaminage, HEX8/WEDGE, thermique et les grandes deformations de coques.

--8<-- "docs/generated/roadmap_status.md"
