---
doc_id: DOC-VNV-CONTACT-CODEASTER-001
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Correlation externe Code_Aster: contact unilateral normal

## Objectif et domaine strict

`VNV-CONTACT-CODEASTER-LIAISON-UNIL-001` compare l'ouverture et la fermeture
du contact normal V1 de QF_solver a Code_Aster `18.1.0`, execute dans une
image Docker epinglee. Cette etude cible volontairement l'inegalite normale
scalaire, et non une equivalence de toute formulation de contact.

Le point esclave est initialement a `z = 0.1 m`, porte un ressort de
`1000 N/m` suivant `z` et est soumis a deux charges: `-200 N` (fermeture) et
`+20 N` (separation). La contrainte comparee est:

$$
g = z + U_Z \geq 0.
$$

QF_solver l'impose avec un active-set et multiplicateur de Lagrange sur un
triangle maitre. Code_Aster emploie
`DEFI_CONTACT(... FORMULATION="LIAISON_UNIL")`; la face maitre est reduite a
la meme condition plane afin d'isoler la loi normale.

## Execution reproductible

```powershell
python .\scripts\run_code_aster_contact_vnv.py `
  --output .\results\VNV-CONTACT-CODEASTER-LIAISON-UNIL-001
```

Le lanceur utilise l'image immuable declaree dans
`solveur/verification/code_aster_tl_structural.py`. Il produit les decks
`.mail` et `.comm`, les logs Docker, `summary.json`, `report.md`, une figure
PNG et un manifeste SHA-256. Une execution Docker indisponible est une erreur
d'infrastructure: aucune valeur externe ne doit etre simulee.

## Criteres

| Critere | Seuil |
| --- | ---: |
| Ecart QF_solver / Code_Aster sur `UZ`, fermeture | `1e-10` relatif |
| Ecart QF_solver / Code_Aster sur `UZ`, separation | `1e-10` relatif |
| Gap Code_Aster ferme | `1e-10 m` |
| Branche active-set QF_solver | aucune inversion |

Les resultats publies sont generes par le script, jamais recopies manuellement.

## Interpretation et exclusions

Une reussite confirme la convention de signe, l'ouverture sans traction et la
fermeture normale du cas discret. Elle ne valide pas: les faces deformables,
le contact surface-a-surface, les normales mises a jour, le grand glissement,
le frottement Coulomb ou l'usure. Ces capacites restent `experimental` et
necessitent des campagnes externes distinctes.
