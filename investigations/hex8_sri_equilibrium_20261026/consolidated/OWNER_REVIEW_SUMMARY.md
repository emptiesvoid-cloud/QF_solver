# HEX8-SRI — résumé pour revue Owner

## Décision proposée

Conserver le correctif et la formulation au statut **`RESEARCH_ONLY`**. Le statut des preuves structurelles actuelles est **`EXPERIMENTAL_GLOBAL_PASS_BOUNDED`**, limité à six calculs sur le même maillage. La convergence spatiale de ces six cas reste **`SPATIAL_CONVERGENCE_NOT_ASSESSED`**. Ne pas intégrer ce changement dans v0.2.12 ni promouvoir HEX8-SRI sur cette base.

## Fait mathématique établi

Une règle d’intégration à un point sur le cube de référence `[-1,1]³` a un poids `8`. L’ancienne expression volumique de SRI en omettait le facteur. Sur le cube unité physique, `detJ=1/8`; pour la déformation uniforme `ε=I`, l’énergie volumique exacte est `9κ/2`. L’ancien opérateur la ramenait exactement à `9κ/16`, tandis que la correction la restaure. Le test antérieur est rouge sur le source historique et vert sur le corrigé. Les matrices élémentaires confirment `Kvol,corr=8Kvol,hist`, `ΔKdev=0` et `ΔKtotal=ΔKvol` pour ce cas analytique.

## Ce que montrent les six calculs

La campagne appariée `20×1×1 m`, maillage `4×2×2`, `E=1 MPa`, charge transverse `1 N`, couvre HEX8 standard, SRI historique et corrigé à `ν=.3` et `.4999`. Les six reçus historiques sont PASS, chaque archive contient une tentative, et les SHA des manifestes, reçus, sidecars et états ont été vérifiés. Les six matrices `K`, états `u` et charges sont cohérents avec les sidecars au float64.

À `ν=.3`, le déplacement moyen signé est −2,991 mm (standard), −3,162 mm (historique), −3,036 mm (corrigé). À `.4999`, il est −0,474 mm, −3,411 mm et −3,411 mm. Le contraste suggère le verrouillage volumétrique de l’HEX8 standard sur ce cas seulement. Le SRI corrigé a un `cond₂(Kff)` de `8,59e8` à `.4999`; la stabilité globale n’est donc pas résumée par le seul déplacement.

Les résultats de poutre d’environ 3,4 mm sont très inférieurs à l’ordre de grandeur Timoshenko (~32 mm). C’est un avertissement de sous-résolution/discrétisation, pas une validation absolue. Les six PASS portent sur finitude, jacobiens échantillonnés et résidu libre enregistré. Énergie et fermeture force/moment n’avaient pas de seuil de campagne supplémentaire. De plus, le champ `energy_defect_normalized` historique a un dénominateur minimal de 1 J et n’est donc pas sans dimension; le rapport recalcule séparément `|2U−W|/|W|` sans altérer les sidecars.

## Preuves manquantes

- Aucun raffinement global de cette campagne : les résultats actuels ne mesurent pas de convergence.
- Aucun oracle 3D indépendant vérifié; Timoshenko ne sert qu’au contrôle de grandeur.
- Distorsion, étirement sévère et non-structuré non validés avec un Jacobien positif certifié partout.
- Pas de spectre de stabilité nouveau dans cette mission; un calcul eigensolve exécuté par erreur par un sous-agent a été exclu du dossier.
- Robustesse à `ν→0.5`, erreurs de champs, mémoire à grande échelle et interactions avec les autres routes non établies.

## Prochaine porte proposée

Geler les seuils et l’oracle, puis demander une campagne distincte de 60 cas : 3 formulations × 5 coefficients de Poisson × 4 maillages all-axis (`4×2×2` à `32×16×16`). Ajouter 115 cas préparatoires patch, géométrie, distorsion et stabilité dans la matrice complémentaire. L’enveloppe cumulée séquentielle des 175 cas proposés est ~23,31 h au maximum des budgets, RSS plafond 16 GiB et une tentative par cas; 42 cas de spectre sont différés et exigent une autorisation d’eigensolve distincte. C’est une proposition, non une autorisation ni un manifeste. Démarrer après une décision Owner propre à chaque sous-campagne et son préflight de ressources/provenance.

## Recommandation

Q1 et Q2 sont partiellement supportées dans leur domaine affine/structurel observé; Q3 n’est pas évaluée sur les six calculs; Q4 reste inconclusive; Q5 est partiellement spécifiée. Garder la branche et ses preuves, demander revue indépendante du protocole, ne pas annoncer une validation générale.
