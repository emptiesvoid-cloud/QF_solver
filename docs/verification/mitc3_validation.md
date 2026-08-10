---
doc_id: DOC-VNV-MITC3-001
revision: 0.3
status: ready for owner review
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Perimetre V&V MITC3+

## Verdict actuel

Le noyau MITC3+ et les campagnes raffinees sont **PASS**. Le statut produit
reste `experimental` jusqu'a la decision finale de l'Owner. La correlation
externe sur coque doublement courbe est desormais fermee par l'hemisphere
pince a quatre quadrants; une reference NAFEMS triangulaire supplementaire
reste une recommandation non bloquante.

Le 30 juillet 2026, une revue de l'equation (17) de Lee, Lee et Bathe a
corrige le parenthesage du terme croise dans le cisaillement suppose. La
baseline precedente est conservee comme historique `SUPERSEDED`; toutes les
valeurs ci-dessous proviennent de la baseline V2 corrigee.

Les invariants suivants passent:

- champ affine, cisaillement transverse constant et interface MITC3/MITC4;
- modes rigides, objectivite et matrice symetrique;
- masse coherente, residus modaux et orthogonalite;
- conservation d'energie Newmark;
- limite harmonique a zero hertz;
- six modes rigides libre-libre, coque cylindrique raffinee, objectivite par
  rotation et comparaison `eigh/eigsh` sans conversion dense;
- charges coherentes;
- post-traitement isotrope et contraintes complexes par pli.

La campagne raffinee atteint:

| Cas | Maillage fin | Mesure |
| --- | ---: | ---: |
| plaque mince | 2 048 triangles | fleche/reference = 0,97951 |
| Cook | 2 048 triangles | erreur = 0,6435 % |
| Scordelis-Lo | 2 048 triangles | erreur = 3,5392 % |
| Scordelis-Lo raffine | 20 000 triangles | erreur = 0,4044 % |
| cylindre pince | 4 096 triangles | erreur = 10,2320 % |
| cylindre pince raffine | 19 600 triangles | erreur = 2,0899 % |
| hemisphere pince, quart fin | 2 048 triangles | erreur reference = 0,5912 % |

Ces quatre controles passent les seuils de developpement declares. Ils ne
remplacent pas la revue du domaine d'emploi.

## Correlation Code_Aster

Le meme maillage de `32 x 8` cellules, soit 512 triangles, est execute avec
MITC3+ et Code_Aster 18.1.0 DKT.

| Cas | QF_solver | Code_Aster DKT | Ecart relatif |
| --- | ---: | ---: | ---: |
| membrane `UX` | 7.1464303228e-6 | 7.1464307488e-6 | 5.9607e-8 |
| flexion `UZ` | -2.7984802834e-4 | -2.7986794339e-4 | 0.007116 % |

Verdict: **PASS_EXTERNAL_CORRELATION**. DKT est Kirchhoff et MITC3+
Reissner-Mindlin; l'accord est observable, pas une identite de formulation.

![Membrane MITC3+ et DKT](../assets/reviews/mitc3_code_aster_membrane.png)

![Flexion MITC3+ et DKT](../assets/reviews/mitc3_code_aster_bending.png)

## Hemisphere pince a quatre quadrants

Le benchmark classique utilise un rayon `R=10`, une ouverture polaire de
`18 deg`, une epaisseur `t=0,04`, `E=6,825e7` et `nu=0,3`. Deux paires de
forces radiales opposees de magnitude `2` pincent l'equateur. Le calcul porte
sur un quart; chaque noeud charge situe sur un plan de symetrie recoit donc
une demi-force de magnitude `1`.

| N | Triangles quart | QF_solver | Code_Aster DKT | Ecart QF/Aster |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 32 | 0,093420110 | 0,096451115 | 3,1425 % |
| 8 | 128 | 0,092771329 | 0,094173879 | 1,4893 % |
| 12 | 288 | 0,092441231 | 0,093188031 | 0,8014 % |
| 16 | 512 | 0,092447139 | 0,092823080 | 0,4050 % |
| 24 | 1 152 | 0,092704110 | 0,092747000 | 0,0462 % |
| 32 | 2 048 | 0,092946225 | 0,092860185 | 0,0927 % |

La valeur publiee est `0,0924`. Sur le maillage fin, l'ecart QF_solver /
reference vaut `0,5912 %`, l'ecart du champ nodal complet QF_solver /
Code_Aster vaut `0,1536 %` et l'increment final vaut `0,2605 %`. Le verdict
est **PASS_EXTERNAL_CORRELATION**.

![Geometrie quatre quadrants](../assets/reviews/mitc3_hemisphere_geometry.png)

![Convergence QF_solver et Code_Aster](../assets/reviews/mitc3_hemisphere_convergence.png)

![Deformees QF_solver et Code_Aster](../assets/reviews/mitc3_hemisphere_qf_aster.png)

![Champ de deplacement Code_Aster](../assets/reviews/mitc3_hemisphere_code_aster.png)

## Temoin CalculiX S3

CalculiX S3 donne un accord membrane de `0,0086 %`, mais une fleche environ
deux fois trop faible: l'ecart de flexion atteint `113,086 %`. Ce resultat est
conserve et trace comme **WARNING**. Il illustre la faiblesse du triangle S3
sur ce cas et ne doit pas etre utilise comme oracle positif de flexion.

![Temoin CalculiX S3](../assets/reviews/mitc3_calculix_bending.png)

## Reproduction

```powershell
python .\scripts\run_mitc3_vnv.py --quick
python .\scripts\run_mitc3_dynamic_extended_vnv.py
python .\scripts\run_mitc3_refined_shell_vnv.py
python .\scripts\run_code_aster_mitc3_vnv.py
python .\scripts\run_mitc3_hemisphere_code_aster_vnv.py
python .\scripts\run_calculix_mitc3_vnv.py
```

Les dossiers controles actifs sont:

- `qualification/vnv/mitc3/reference_v2`;
- `qualification/vnv/mitc3/refined_h20k`;
- `qualification/vnv/mitc3_dynamic_extended/reference`;
- `qualification/vnv/external/code_aster_mitc3/reference_v2`;
- `qualification/vnv/external/code_aster_mitc3/hemisphere_v1`;
- `qualification/vnv/external/calculix_mitc3/reference_v2`.

## Points encore ouverts

1. Decision finale et date de l'Owner.
2. Reference NAFEMS triangulaire supplementaire, non bloquante.

Le patch de flexion explicite `kappa_x/kappa_y/kappa_xy` et la correlation
coque courbe sur maillage identique sont fermes. Les contraintes au point de
charge de l'hemisphere restent informatives, car la force ponctuelle y cree
une singularite.
