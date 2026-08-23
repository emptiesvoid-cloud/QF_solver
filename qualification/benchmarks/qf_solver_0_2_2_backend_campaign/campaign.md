# Campagne backend 0.2.2 alpha

Statut technique : **PASS_BOUNDED_BACKEND_CAMPAIGN**. Le statut de maturite reste **development** jusqu a la revue Owner.

## Preuves fermees dans le perimetre borne

- Statique PETSc contigu : campagne 2M/4M DDL, efficacites fortes `0.651` et `0.615`.
- Statique PETSc graphe/PT-Scotch : 2M DDL, efficacite forte `0.621`.
- Matrix-free : `107811` DDL, residu relatif `1.104e-12`.
- Comparaison SciPy/matrix-free/PETSc : statut `PASS`, trois backends completes.
- Modal SLEPc : `107811` DDL, trois modes, residu relatif maximal `2.789e-12`.
- Newmark PETSc/GAMG : `2044416` DDL, `10` pas, residu relatif maximal `1.968e-06`.

## Limites explicitement conservees

- La preuve est executee dans une image Docker epinglee, sur une seule configuration hote.
- Le statique couvre 2M et 4M DDL ; le Newmark couvre 2M DDL avec PETSc/GAMG.
- Le modal SLEPc est demontre jusqu a 107811 DDL ; le shift-invert direct 2M a ete tue par la limite de ressources.
- Le matrix-free est demontre a 107811 DDL ; la tentative 1M reste une limite de performance.
- Les resultats restent development jusqu a la revue Owner et ne constituent pas une promotion stable.

Les manifestes d evidence sont verifies dans chaque dossier de campagne. Les comparaisons numeriques ne constituent pas une qualification des formulations FEM ni une decision de release.
