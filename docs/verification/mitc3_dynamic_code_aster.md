---
doc_id: DOC-VNV-MITC3-DYNAMICS-CODEASTER-DKT-017
revision: 0.1
status: owner_accepted_with_recommendations
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Correlation dynamique MITC3+ et Code_Aster DKT

## Objet et configuration comparee

`VNV-MITC3-DYNAMICS-CODEASTER-DKT-017` compare QF_solver `MITC3+` avec
Code_Aster `18.1.0`, element `DKT/TRIA3`, sur la meme plaque mince en
porte-a-faux. Les `16 x 4` cellules generent 128 triangles dont la
connectivite, les coordonnees, l'epaisseur, le materiau, les blocages et la
resultante de charge sont identiques. Les deux formulations ne sont pas
identiques : `DKT` est Kirchhoff alors que `MITC3+` est Reissner-Mindlin. Le
cas est donc mince et le resultat est une correlation d'observables, pas une
egalite de formulation.

La sonde est la moyenne de `UZ` sur les cinq noeuds du bord libre. Cette
definition est appliquee des deux cotes afin que la comparaison ne depenne
pas d'un choix de noeud particulier.

## Resultats

| Controle | Ecart relatif QF_solver / Code_Aster | Seuil | Verdict |
| --- | ---: | ---: | --- |
| Six frequences propres | 1,7367 % | 10 % | PASS |
| Historique Newmark | 0,5496 % RMS normalise | 10 % | PASS |
| Reponse harmonique complexe | 0,2998 % RMS normalise | 10 % | PASS |

![Modes, Newmark et harmonique compares](../assets/generated/content_closure/mitc3_dynamic_code_aster.png){ .result-figure }

## Modal, Newmark et harmonique

Le modal calcule les six premieres frequences. Newmark utilise
`beta = 0,25`, `gamma = 0,5`, un pas de `T1/40` et une impulsion sinusoidale
tabulee. La reponse harmonique est evaluee aux frequences `0,10 f1`,
`0,25 f1`, `0,50 f1` et `0,75 f1`, volontairement sous la premiere resonance
sans amortissement. Les historiques et les valeurs complexes brutes sont
conserves dans `summary.json`.

## Reproduction

```powershell
python .\scripts\run_code_aster_mitc3_dynamic_vnv.py `
  --output .\results\VNV-MITC3-DYNAMICS-CODEASTER-DKT-017
```

L'image Docker est referencee par empreinte dans
`solveur/verification/code_aster_tl_structural.py`. Docker indisponible est
une erreur d'infrastructure explicite, jamais un resultat numerique.

## Portee et decision Owner

Les scopes `mitc3-modal`, `mitc3-transient-dynamic` et
`mitc3-harmonic-response` ont ete acceptes par l'Owner le `2026-08-02`, avec
une recommandation de raffinement maillage-frequence. Ils ne couvrent pas la
dynamique stratifiee, l'amortissement, les contraintes harmoniques ni le
non-lineaire. Ces restrictions restent visibles dans les registres de
qualification.
