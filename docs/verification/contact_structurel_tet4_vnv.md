---
doc_id: DOC-VNV-CONTACT-TET4-001
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# V&V contact unilateral : convergence structurelle TET4

## Objet

`VNV-CONTACT-TET4-STRUCTURAL-001` ajoute une preuve de convergence spatiale au
contact unilateral V1. Une barre deformable en TET4 est encastree a droite et
son noeud central gauche est pousse vers un plan rigide triangulaire. La
reaction de contact est donc influencee par la compliance de la structure,
contrairement au bloc analytique a ressorts.

Le maitre est un triangle fixe dans le plan `x=0`, de normale initiale `+x`.
Le noeud esclave est initialement a `x=0.1 m`. Une force `-4000 N` suivant
`x` ferme le contact. Le materiau est isotrope lineaire (`E=10000 Pa`,
`nu=0.3`). Les quatre niveaux sont `4x2x2`, `8x4x4`, `12x6x6` et `16x8x8`
cellules structurelles, soit de `96` a `6144` TET4.

## Ce que demontre la campagne

Le gap impose par multiplicateur de Lagrange est nul lorsque le contact est
actif. La reaction normale est une quantite dependante du maillage : elle doit
donc tendre vers une valeur stable avec le raffinement. Le dernier ecart relatif
de reaction est exige inferieur a `3 %`; le residu libre reste inferieur a
`1e-10` et l'active-set doit converger en trois iterations ou moins.

--8<-- "docs/generated/contact_structural_checks.md"

![Convergence de la reaction normale](../assets/generated/contact_structural_convergence.png)

![Maillage et deformee amplifiee](../assets/generated/contact_structural_deformation.png)

## Interpretation et limites

Cette etude est une preuve interne de couplage entre un TET4 deformable et la
contrainte normale noeud-triangle. Elle ne constitue pas une preuve de contact
surface-a-surface, de grand glissement, de normale mise a jour, ni une
correlation Code_Aster ou CalculiX. Ces extensions et la correlation externe
restent necessaires avant toute hausse de maturite.

Les resultats sont regeneres par `scripts/build_docs.py` dans
`docs/generated/contact_structural/`, avec `summary.json`, rapport Markdown,
figures et manifeste SHA-256. La page est liee a `REQ-CONTACT-001`,
`FORM-CONTACT-001` et
`tests/verification/test_frictionless_contact_structural_vnv.py`.

## Execution consolidee

Les preuves normale et frottement sont egalement generees ensemble par :

```powershell
python .\qf_solver.py verify-contact --output .\results\contact_v1 --json-report .\results\contact_v1.json
```

L'API equivalente est `solveur.api.run_contact_verification(output_dir)`. Le
verdict `PASS_INTERNAL` confirme uniquement les deux preuves internes; il ne
change pas la maturite `experimental` du contact.
