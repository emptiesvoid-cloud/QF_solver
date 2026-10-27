# Première campagne de convergence HEX8-SRI

**État : `PREPARED_NOT_AUTHORIZED`.** Aucun cas de convergence n’a été préflighté ou exécuté.

## Périmètre

La première sélection est le sous-ensemble apparié de 24 cas : HEX8 standard, SRI historique figé et SRI corrigé; `ν=0.3` et `ν=0.4999`; maillages `4×2×2`, `8×4×4`, `16×8×8` et `32×16×16`. Chaque formulation utilise la même géométrie `20×1×1 m`, `E=1 MPa`, encastrement complet en `x=0` et traction uniforme de `−1 Pa` sur la face `x=20 m` d’aire `1 m²`, soit `−1 N` selon `Z`.

Les 24 nodeids proposés utilisent le motif exact :

```text
tests/verification/test_hex8_sri_convergence.py::test_convergence_case[<formulation>-nu_<0p3|0p4999>-<nx>x<ny>x<nz>]
```

Les anciens résultats `4×2×2` restent des preuves historiques avec leurs identités d’origine. Aucun de leurs reçus d’autorisation n’est réutilisé pour cette campagne.

| Maillage | HEX8 | Nœuds | DDL | Bloqués / libres | Budget par cas proposé |
|---|---:|---:|---:|---:|---:|
| `4×2×2` | 16 | 45 | 135 | 27 / 108 | 180 s, 512 MiB RSS souple |
| `8×4×4` | 128 | 225 | 675 | 75 / 600 | 300 s, 1 024 MiB RSS souple |
| `16×8×8` | 1 024 | 1 377 | 4 131 | 243 / 3 888 | 900 s, 4 096 MiB RSS souple |
| `32×16×16` | 8 192 | 9 537 | 28 611 | 867 / 27 744 | 3 600 s, 16 384 MiB RSS souple |

Six cas par niveau donnent un maximum de 8,3 h séquentielles. Une tentative par nodeid, sans retry. L’assemblage global doit être creux à tous les niveaux. Le dernier niveau ne peut pas utiliser le chemin dense historique; la fonction FEM nouvelle utilise COO→CSR, puis factorisation creuse. Le plafond RSS reste une observation souple du contrôleur, pas une limite OS. L’archive propose 256 MiB par cas pour conserver `K` creuse, le champ d’état et les observables, sans stocker les 24×24 matrices locales de chaque élément.

## Observables et règles proposées

Conserver avant assertions : déplacement signé moyen de la face chargée, déplacement de référence nodal, déformations aux huit points, énergie interne, travail externe, réactions complètes, résidu libre, fermetures de forces et moments, symétrie, déterminants Jacobien centre/Gauss, estimation `cond₁(Kff)`, temps, RSS et état creux `K` avec `F` et `u`.

La moyenne de face est l’intégrale surfacique de la trace Q1, obtenue par les poids nodaux cohérents de traction, et non la moyenne arithmétique des nœuds. Le rapport d’échelle Timoshenko est enregistré comme `trend_difference`, jamais comme erreur ou verdict de précision.

Seuils existants dans la matrice générale, encore à geler explicitement par Owner pour ce lot : résidu libre relatif `≤1e−7`; fermetures de forces et moments `≤1e−6`; identité énergétique `|2U−W|/|W|≤1e−8`; changement entre les deux derniers niveaux `≤2 %` pour déplacement moyen et énergie. Le seuil proposé contre un oracle 3D est `≤5 %` sur déplacement et énergie, mais ne peut pas être activé tant que cet oracle n’est pas implémenté, vérifié et identifié. Aucun seuil ne sera ajusté après accès aux résultats.

Après acquisition des sidecars, `experiments/hex8_sri_equilibrium/convergence_analysis.py` valide les unités, refuse les doublons et les empreintes altérées, puis écrit un CSV et des SVG dérivés sans remplacer un fichier existant. L’indicateur de pente est calculé à partir des différences successives des trois derniers niveaux et étiqueté **auto-convergence diagnostique**; ce n’est ni une erreur de champ ni une preuve de limite continue. Une erreur contre référence n’est produite que si elle est déclarée qualifiée et porte une incertitude `≤0,5 %` pour le déplacement et l’énergie.

## Vérification du repère de poutre

Le chargement historique est cohérent avec le repère de poutre pour les résultantes : face terminale centrée, traction uniforme, force `−1 N` sans couple autour du centre de section; le support bloque les trois translations sur la face entière. L’observable historique est une moyenne surfacique Q1 de `UZ`. Dans l’hypothèse de section de poutre qui reste plane et d’une trace affine de section, cette moyenne représente la translation de l’axe centroidal. Elle ne retire pas les effets locaux 3D de l’encastrement ou de l’application de traction.

Avec `A=1 m²`, `I_y=1/12 m⁴`, `G=E/[2(1+ν)]`, la formule de poutre est

```text
w(L) = P L³/(3 E I_y) + P L/(k G A).
```

Le terme de flexion est `32,000 mm`. Pour `k=5/6`, les totaux en valeur absolue sont `32,0624 mm` (`ν=.3`) et `32,0720 mm` (`ν=.4999`). Le facteur rectangulaire de Cowper `k=10(1+ν)/(12+11ν)` donne respectivement `32,0612 mm` et `32,0700 mm`. Le choix du facteur ne change ici le total que de `0,0012–0,0020 mm`, car le cisaillement représente environ `0,2 %` de la réponse.

Le rapport `h/L=1/20` rend ce cas suffisamment élancé pour que Timoshenko soit un contrôle physique utile de signe, unités, ordre de grandeur et tendance. La théorie de poutre ne résout toutefois pas la solution 3D des couches limites d’extrémité et n’est pas un oracle d’erreur serré pour le HEX8. Les `3–3,4 mm` historiques sur quatre éléments axiaux et deux éléments par dimension de section sont très éloignés des `32 mm`; cela justifie une convergence mesurée, pas la présomption que le modèle le plus souple est le plus exact.

Référence du facteur de cisaillement : Cowper (1966), [The Shear Coefficient in Timoshenko’s Beam Theory](https://doi.org/10.1115/1.3625046). Une documentation de poutres Timoshenko rappelle également les hypothèses d’élancement et les facteurs de section : [Abaqus, Choosing a beam element](https://abaqus.uclouvain.be/English/SIMACAEELMRefMap/simaelm-c-beamelem.htm). Ces références valident le modèle réduit, pas la réponse 3D QF.

## Oracle de précision indépendant

Un oracle quantitatif reste absent. L’interpréteur de préparation actuel n’a pas `dolfinx`, `fenics`, `petsc4py` ni `skfem`; aucune dépendance n’a été installée. Le plan est un solveur indépendant de l’élasticité mixte déplacement–pression sur maillage tétraédrique, avec espaces d’ordre supérieur et inf-sup stable (proposition : DOLFINx/FEniCSx vectoriel P2 / scalaire P1). Son environnement, version, source et empreinte doivent être gelés avant tout manifeste d’exécution.

Avant de servir d’oracle, il doit réussir ses patch tests indépendants, vérifier le résultant et la définition de moyenne de face, puis montrer une stabilisation sous raffinement pour déplacement et énergie; l’incertitude estimée doit être `≤0,5 %`. Les données HEX8 seront alors comparées à une valeur de référence qualifiée, avec erreur absolue et relative. Une différence à Timoshenko restera affichée à part.

## Contrôleur et point d’arrêt

Le contrôleur courant n’inscrit que les six anciens nodeids dans `test_hex8_sri_structural_campaign.py`, impose un plafond par nodeid de 180 s et 1 024 MiB, et valide exactement six manifests. Il ne peut ni collecter ni autoriser cette nouvelle matrice de 24 cas. Le test de convergence et le pilote creux sont préparés, mais les nodeids restent `PLANNED_NOT_REGISTERED`; aucun preflight reçu n’existe. Une extension minimale de configuration/runner sur la branche de configuration HEX8-SRI est nécessaire et doit préserver les six anciens bindings ainsi que D01/C01/E01. Elle doit permettre les budgets par nodeid sans élargir les autres domaines. Voir [la demande de configuration](../campaign_preparation/first_convergence_24/CONTROLLER_EXTENSION_REQUEST.md).

Le contrôleur doit passer au child le chemin de manifeste inscrit dans `QF_DEV_MANIFEST_PATH` et en vérifier le SHA. Ce chemin provient exclusivement de l’entrée enregistrée; le test refuse tout chemin hors worktree ou mal nommé. La campagne reste `PREPARED_NOT_AUTHORIZED` jusqu’à l’extension, aux préflights acceptés et à une décision Owner qui porte sur les identités finales.

## Identités et brouillons préparés

Le source de recherche est commité à `7ff2809a854e1434619c261195e78b901be0ea78`, fingerprint `1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555`. Le contrôleur provisoire est `codex/hex8sri-controller-registration` à `0d6286ecf75eea62ecafe63ec81cc816ad95226d`; les SHA runner/plugin/policy restent provisoires jusqu’à extension. Le dossier `../campaign_preparation/first_convergence_24/drafts/` contient les 24 manifests à `execution_authorized=false`, `do_not_execute=true`, la table nodeid/budget/SHA, `registration_request.json` et `SHA256SUMS.txt`. Chaque SHA de manifeste correspond au checksum; aucun reçu de préflight n’a été produit. Voir [la demande Owner précise](../campaign_preparation/first_convergence_24/drafts/OWNER_DECISION_REQUEST.md). Ces empreintes de draft ne sont pas les identités finales d’exécution et devront être régénérées si le contrôleur évolue.

L’oracle 3D n’étant pas encore identifié ni empaqueté, l’exécution des 24 comparaisons ne permettrait pour l’instant que l’auto-convergence et le contrôle de tendance de poutre. L’autorisation scientifique doit donc couvrir séparément la qualification de l’oracle et le lot HEX8, ou repousser le critère d’erreur physique jusqu’à l’achèvement de l’oracle.
