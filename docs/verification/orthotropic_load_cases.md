---
doc_id: DOC-VNV-ORTHO-LOAD-007
revision: 0.2
status: controlled_candidate
applicable_version: 0.2.1-alpha
owner_review: pending
reviewer: ""
approver: ""
---

# VNV orthotrope : orientations et chargements combinés

**Identifiant :** `VNV-ORTHOTROPIC-SOLID-LOAD-CASES-007`  
**Statut technique :** `PASS_TECHNICAL_VERIFICATION`  
**Périmètre :** TET4 et TET10, élasticité orthotrope homogène, petites déformations  
**Maturité :** preuve technique, sans promotion automatique vers `stable`

## Objectif

Cette campagne isole la partie constitutive qui pouvait être confondue avec
l'erreur de discrétisation d'une pièce. Elle vérifie que la déformation est
projetée dans les axes matériau, que la loi est évaluée dans ce repère, puis
que la contrainte est reprojetée correctement dans le repère global.

Les essais utilisent cinq orientations autour de l'axe global `Z` : `0`, `17`,
`31`, `45` et `73` degrés. Trois états sont appliqués : biaxial, cisaillement
combiné et état mixte. Chaque état est imposé comme un champ affine sur un
TET4 puis sur un TET10.

## Résultats

Le rapport et les valeurs machine-readable sont dans :

- `qualification/vnv/orthotropic_load_cases_007/reference/summary.json` ;
- `qualification/vnv/orthotropic_load_cases_007/reference/report.md` ;
- `qualification/vnv/orthotropic_load_cases_007/reference/vnv_manifest.json`.

Les 15 combinaisons orientation/chargement passent. L'erreur de projection de
contrainte et l'erreur d'invariance énergétique restent sous `1e-12`. Les
déformations et contraintes élémentaires TET4/TET10 restent sous `1e-10`, ce
qui est attendu pour un champ affine exactement représenté.

| Vérification | Seuil | Verdict |
| --- | ---: | --- |
| Projection contrainte global vers matériau | `1e-12` | PASS |
| Invariance de l'énergie | `1e-12` | PASS |
| Déformation affine TET4/TET10 | `1e-10` | PASS |
| Contrainte affine TET4/TET10 | `1e-10` | PASS |

## Interprétation mécanique

Cette preuve confirme la transformation d'axes et la convention de
cisaillement d'ingénieur. Elle ne prouve pas qu'un TET4 suffisamment grossier
restitue correctement une flexion structurelle orthotrope. La campagne de
convergence structurale séparée reste donc obligatoire : le dernier résultat
TET4 disponible est à environ `1,329 %` de la référence TET10 et son incrément
final reste au-dessus du seuil de stabilisation retenu. Le TET10 fin est à
environ `0,292 %` dans la campagne structurelle correspondante.

## Reproduction

```powershell
python .\scripts\run_orthotropic_load_cases_vnv.py `
  --output .\results\VNV-ORTHOTROPIC-SOLID-LOAD-CASES-007
```

La campagne ne nécessite ni solveur externe ni données personnelles. La
corrélation Code_Aster/CalculiX demeure référencée par la spécification
`orthotropic-solid-tet4-tet10`, mais elle n'est pas remplacée par cette preuve
locale.
