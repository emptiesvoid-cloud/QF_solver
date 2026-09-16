# WP05-E — comparaison inter-familles TET10 / HEX20

**Résultat : `PASS — OWNER_ACCEPTED_WITH_LIMITATIONS` — 1/1 point WP05-E dans l’intégration locale.**

Cette clôture est un audit evidence-only des résultats H3 déjà produits pour WP05-C et WP05-D. Aucun solve structurel n’a été relancé pour WP05-E. L’audit machine-readable et ses comparaisons se trouvent dans [`wp05e_cross_family_audit.json`](../../../qualification/0_2_9/wp05e/wp05e_cross_family_audit.json).

**Disposition Owner ultérieure :** WP05-E est accepté à 1/1 candidate après intégration formelle des preuves WP05-C et WP05-D. La comparaison Code_Aster/autre solveur est différée et n’est pas revendiquée dans cette clôture bornée. Voir le [dossier d’intégration Owner](wp05-cde-owner-integration.md).

## Prérequis et provenance

WP05-C a terminé H1/H2/H3 en `PASS` : 12 incréments acceptés par cas, zéro fallback, équilibre et enveloppe de déformation conformes. Les cinq écarts H2→H3 passent les seuils gelés : déplacement 0,7763 % / 2 %, résultante 0,0000000000031 % / 2 %, moment 0,00229 % / 2 %, énergie 0,7759 % / 2 %, et contrainte du contrat commun 4,2395 % / 8 %. Le replay H1 passe : mêmes observables et même historique de charge, compteur Newton identique (145), hash `raw.npz` identique.

WP05-D est `PASS_CANDIDATE`; la décision Owner locale indique explicitement l’acceptation technique `1/1` dans son périmètre HEX20. Le ledger governing n’a pas encore été intégré : WP05-D y demeure 0/1 en attente d’intégration. La « référence indépendante » D est un recalcul NumPy de l’observable à partir des données brutes du solveur de production, et non une résolution FEM indépendante.

Les résultats comparés proviennent du même SHA d’exécution `72282a6ca6e6574a32c6182eccb001d9816febbc`, du même digest de politique runtime `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5` et du même contrat historique `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680`. Les hashes des résultats et données brutes sont liés dans le JSON.

## Comparabilité physique

Les deux H3 représentent le même domaine `L=4, H=0.5, D=0.5`, le même matériau isotrope linéaire `E=1e6, nu=0.30`, l’encastrement complet sur `x=0`, et les mêmes cellules parent `16×8×8`. Les familles ont naturellement des maillages/DOFs distincts : TET10 `9537/6144/28611`, HEX20 `5121/1024/15363` (nœuds/éléments/DOFs).

La charge physique est la même : résultante `[0,-50,0]`, moment de référence `[12.5,0,-200]`. L’intégration nodale diffère selon la face d’élément — T6 trois points pour TET10, Q8 Gauss 2×2 pour HEX20 — et cette différence de représentation est divulguée. L’équivalence de charge H3 du contrat est satisfaite à `8.53e-14` en résultante et `3.41e-13` en moment.

Pour `sigma_xx`, E compare l’observable historique commun `observables.representative_sigma_xx`, défini sur la même boîte de coordonnées de référence `(x/L=[0.4,0.6], y/H=[0.7,0.95], z/D=[0.2,0.8])` et pondéré par le volume de référence des points d’intégration (`w_q det(J0)`). Les populations discrètes ne sont pas identiques : H3 TET10 compte 736 points et un volume échantillonné de `0.0299479167`; H3 HEX20 compte 840 points et `0.0306471836`. Cette différence est conservée et signalée.

La nouvelle fenêtre exacte/clippée de WP05-D donne `sigma_xx=3104.950356` en HEX20, mais **n’est pas utilisée** pour la comparaison E : elle est approuvée uniquement pour HEX20 et aucun observable TET10 correspondant n’existe dans ce dossier. E compare donc les deux valeurs produites sous le contrat historique commun, sans mélanger les définitions.

## Résultats H3

La formule relative reprend la convention du précédent audit inter-familles WP04-E : `delta(a,b)=|a-b|/max(|a|,|b|,1e-12)`. Pour les réactions et moments vectoriels, la comparaison porte sur les normes euclidiennes, puis applique cette formule scalaire. Les seuils WP05-E n’ont pas été modifiés.

| Observable | TET10 H3 | HEX20 H3 | Écart relatif | Seuil | Verdict |
|---|---:|---:|---:|---:|---|
| Déplacement moyen chargé Y | -0,204200597 | -0,204429380 | 0,11191 % | 3 % | PASS |
| Norme de la résultante de réaction | 50,00000000000002 | 49,99999999999996 | 1,28e-13 % | 2 % | PASS |
| Norme du moment de réaction | 200,077473527 | 200,076891007 | 0,000291 % | 3 % | PASS |
| Énergie de déformation | 5,098363014 | 5,104069785 | 0,11181 % | 3 % | PASS |
| `sigma_xx` historique commun | 3082,376242 | 3254,144092 | 5,27843 % | 10 % | PASS |

Les cinq comparaisons passent. Le résultat est **borné à ces cas H3 et observables déclarés** ; il ne prétend pas établir l’interchangeabilité générale des familles.

## Vérification ciblée

- `python -m pytest -q tests/verification/test_wp05e_cross_family.py tests/verification/test_wp05_cd_structural_harness.py` : **25 passed**.
- Ruff sur le nouveau test : **PASS**.
- `compileall` sur le nouveau test : **PASS**.
- Parsing du JSON d’audit : **PASS**.
- `git diff --check` : **PASS**.
- Mypy : non exécuté ; cette clôture ne modifie que les preuves, la documentation et le test d’audit, pas le code de production.
- Suite complète du dépôt : non exécutée, conformément à la politique de campagne.

## Gouvernance et suite

`WP05-E = 1/1` est intégré au ledger local après la décision Owner et l’intégration des preuves C/D ; WP05 est à 5/5 et le total local à 61/100. Le remote governing reste à 58/100 car aucun push n’a été effectué. La suite complète du dépôt n’a pas été lancée, conformément à l’autorisation de campagne qui l’interdit ; les vérifications ciblées de cet audit sont consignées dans le JSON après exécution.

Limites maintenues : benchmark statique borné, maillages HEX20 affines/TET10 déclarés, observables et boîte de contrainte spécifiques au contrat, différences de populations d’intégration divulguées, aucune revendication de corrélation avec un solveur FEM externe ou d’équivalence générale entre éléments. Une comparaison Code_Aster ou autre solveur reste une validation externe future distincte.
