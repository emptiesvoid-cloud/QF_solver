---
doc_id: DOC-VNV-CONTACT-CODEASTER-FOLDED-006
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Correlation Code_Aster : normale finale sur surface pliee

`VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006` compare QF_solver et Code_Aster
`18.1.0` dans l'image Docker epinglee. La normale de la facette finale est :

$$
\mathbf n = [-0.408248,-0.408248,0.816497]^T.
$$

Le point esclave porte trois ressorts de `1000 N/m`, une charge
`(600,0,-200) N` et la contrainte normale inclinee. Les deplacements `UX`,
`UY`, `UZ` et le gap sont compares au seuil relatif `1e-10`.

```powershell
python .\scripts\run_code_aster_contact_folded_vnv.py `
  --output .\results\VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006
```

## Portee

Cette correlation valide la cinematique normale finale et son couplage entre
`UX` et `UZ`. Code_Aster recoit cette normale avec `LIAISON_DDL`; il ne choisit
pas lui-meme la facette. Elle ne valide donc pas la detection de commutation,
le grand glissement ni le contact surface-surface. Le statut reste
`experimental`.
