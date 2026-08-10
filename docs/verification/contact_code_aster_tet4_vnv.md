---
doc_id: DOC-VNV-CONTACT-CODEASTER-TET4-004
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Correlation Code_Aster : face maitre TET4 deformable

## Objet

`VNV-CONTACT-CODEASTER-TET4-MASTER-004` compare QF_solver avec Code_Aster
`18.1.0`, execute dans l'image Docker epinglee, pour une face frontiere TET4
deformable. Le maillage, le materiau isotrope, les blocages, le ressort de
l'esclave et la charge normale sont identiques.

Le cas est connu actif. Code_Aster emploie donc une contrainte cinematique
`LIAISON_DDL` egale a la fermeture QF_solver :

$$
u_{s,z}-0.5u_{1,z}-0.25u_{2,z}-0.25u_{3,z}=-g_0.
$$

Les deplacements normaux de l'esclave et des trois noeuds de la face sont
compares sous une tolerance relative de `1e-10`.

## Execution

```powershell
python .\scripts\run_code_aster_contact_tet4_vnv.py `
  --output .\results\VNV-CONTACT-CODEASTER-TET4-MASTER-004
```

Le test Docker opt-in correspondant est
`tests/verification/test_code_aster_contact_tet4_vnv.py` avec la variable
`QF_SOLVER_RUN_EXTERNAL=1`.

## Portee et limites

Cette correlation controle le transfert EF couple et la cinematique d'un etat
de contact ferme. La correlation `LIAISON_UNIL` existante garde la preuve de
l'ouverture et de la fermeture active-set. Aucune de ces etudes ne prouve une
recherche de surfaces generale, le contact surface-surface, le grand
glissement, la normale actualisee ou le frottement. Le statut reste
`experimental`.
