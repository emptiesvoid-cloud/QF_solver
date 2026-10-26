# Mémoire technique — HEX8-SRI

## État de référence

- Branche de recherche : `research/hex8-sri-equilibrium`.
- HEAD auquel les six calculs historiques sont liés : `452f31f742ce4ce8356c68c691cbb3484a627920`.
- Fingerprint source de ces calculs : `e14217217a6044ca9cb7c64a0f187864121589463c00e1eaac53251696b60c29`.
- Contrôleur historique : `codex/hex8sri-controller-registration`, HEAD `0d6286ecf75eea62ecafe63ec81cc816ad95226d`.
- Résultat : `EXPERIMENTAL_GLOBAL_PASS_BOUNDED`; convergence de cette campagne `SPATIAL_CONVERGENCE_NOT_ASSESSED`; décision `RESEARCH_ONLY`.

## Résultat mathématique stable

La règle centrée volumique sur `[-1,1]³` exige le poids 8. Sur cube affine unité et déformation constante `ε=I`, l’ancien opérateur donne `9κ/16` au lieu de `9κ/2`; le correctif restaure le facteur 8. Localement, les preuves archivées montrent `Kvol,corr=8Kvol,historique`, `ΔKdev=0`. Cette exactitude ne se généralise pas automatiquement à un `J` variable d’élément non affine.

## Six calculs historiques

Campagne `20×1×1 m`, `4×2×2`, `E=1 MPa`, `ν=.3/.4999`, HEX8 standard/SRI historique/SRI corrigé. Les six archives et relations SHA sont dans `investigations/hex8_sri_equilibrium_20261026/consolidated/EVIDENCE_INDEX.json`. Les NPZ ont été post-traités sans nouvelle résolution; les sidecars restent intacts. Résultat notable à `.4999`: `UZ` moyen standard `−.474211 mm`, SRI corrigé `−3.410621 mm`, `cond₂(Kff)=8.586e8`. Un seul maillage, donc aucune convergence ici.

## Limites et garde-fous

- Ne pas lancer FEM, assemblage global, eigensolve ou modal sans manifeste/autorisation Owner propre.
- Ne pas intégrer en `emptiesvoid-cloud/0.2.12`.
- Les six PASS portent seulement sur leurs critères gelés; énergie/équilibre n’avaient pas de seuil additionnel.
- Le champ historique `energy_defect_normalized` est dimensionnel. Le rapport recalcule `|2U−W|/|W|` sans modifier les preuves.
- Un sous-agent a produit par erreur un eigensolve sur `Kff` archivée lors de l’audit; ses valeurs sont exclues et l’écart est consigné.

## Dossier consolidé

Point d’entrée : `investigations/hex8_sri_equilibrium_20261026/consolidated/README.md`. Les matrices suivantes restent `PREPARED_NOT_AUTHORIZED` : 60 cas convergence/quasi-incompressibilité et 115 contrôles complémentaires. Les tests de ce dossier sont synthétiques, unitaires et ne chargent pas le solveur.

## Livraison de recherche

Le code d’audit/outillage est commit `8ffec8c2`; le dossier documentaire et les preuves consolidées sont commit `4ca399d8`, tous deux poussés sur la branche de recherche. Contrôles finaux : 14 tests synthétiques ciblés PASS, Ruff check/format et compilation PASS, liens Markdown PASS. Aucun FEM, assemblage, eigensolve ou calcul modal n’a été exécuté par l’agent principal.
