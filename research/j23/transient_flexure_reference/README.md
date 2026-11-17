# J23 — comparaison externe du transitoire TET10 en flexion

## État

Paquet préparé depuis les artefacts J13 archivés. Le deck Abaqus n'a pas été
exécuté : le seul lanceur détecté localement (`abaqus.bat`) pointe vers un
`abq2019.bat` absent. Aucun résultat Abaqus ni aucune corrélation externe ne
sont revendiqués.

Le paquet réutilise un calcul QF terminé en statut `COMPLETED_EXPLORATORY` et
un historique Euler–Bernoulli continu. Il ne relance pas QF et ne modifie pas
les verdicts J12/J13.

## Modèle comparé

- Solide droit : longueur 2 m, section 0,1 × 0,1 m.
- Matériau linéaire isotrope : E = 210 GPa, ν = 0,30, ρ = 7800 kg/m³.
  La masse géométrique attendue est 156 kg pour 0,02 m³.
- Maillage commun : 768 TET10, 1 377 nœuds, 4 131 DDL solides; indices de
  nœuds d'archive convertis en labels Abaqus à partir de 1.
- Encastrement : UX = UY = UZ = 0 pour tous les nœuds de x = 0; autres
  translations libres; les solides n'ont pas de DDL de rotation.
- Amortissement physique : nul. Conditions initiales : déplacement et vitesse
  nuls.
- Charge : force équivalente à une traction uniforme +UZ sur la face x = L,
  aire 0,01 m², résultante de pointe 100 N. Facteur temporel linéaire par
  morceaux (0, 0), (10 ms, 1), (20 ms, 0), puis zéro jusqu'à 80 ms.
- Pas visé : 0,1 ms; durée : 80 ms; 800 incréments positifs. Abaqus est réglé
  avec α = 0, β = 1/4 et γ = 1/2, correspondant au trapèze/Newmark sans
  amortissement numérique selon la documentation Abaqus.
- Observables : UZ aux nœuds exacts (1, 0,05, 0,05) m et
  (2, 0,05, 0,05) m; résultante et moment des réactions d'encastrement.

`prepare_abaqus_case.py` vérifie le maillage et intègre indépendamment la
charge constante sur les triangles quadratiques de la face terminale. Il
produit le deck C3D10 avec les mêmes forces nodales que l'archive QF. Cette
comparaison contrôle donc la réponse de deux assemblages/résolutions sur une
même géométrie et un même second membre nodal; elle ne teste pas l'intégration
d'une charge surfacique propre à Abaqus.

Les matrices de masse et de raideur ne sont pas partagées. Pour une géométrie
droite comme celle archivée, QF utilise la règle tétraédrique Hammer à quatre
points pour la raideur et une règle Duffy d'ordre 5 pour la masse. La
documentation Abaqus décrit le tétraèdre quadratique avec quatre points de
raideur et quinze points pour sa masse consistante. Ces choix peuvent intégrer
exactement les termes polynomiaux de ce cas, mais aucun test matriciel
croisé n'a été fait. Les conventions de solveur, l'assemblage global et la
version Abaqus restent à vérifier. Les courbes QF/Abaqus compareront donc deux
résolutions mécaniques indépendantes sur la même géométrie, le même RHS et le
même pas, sans établir à elles seules une validation générale.

## Référence et portée

La seule comparaison mécanique exécutée disponible demeure la série continue
Euler–Bernoulli à 64 modes de J12/J13. J13 vérifie la troncature 32/64 sur ses
grilles à une différence maximale de 1e-5 du pic. La poutre néglige le
cisaillement transverse, l'inertie de rotation, la couche limite 3D de
l'encastrement et la discrétisation de section. Elle reste une référence
indépendante de l'assemblage QF, mais pas une solution exacte du solide.

Pour le TET10 8×4×4, les indicateurs recalculés avec les données J13 donnent :

| Position | Pic QF | Pic Euler–Bernoulli | Erreur max / pic EB | RMS / pic EB |
|---|---:|---:|---:|---:|
| Mi-longueur, UZ | 0,05686 mm à 68,8 ms | 0,05793 mm à 69,4 ms | 10,948 % | 4,268 % |
| Extrémité, UZ | 0,16765 mm à 45,5 ms | 0,16935 mm à 45,9 ms | 10,488 % | 4,065 % |

Ces nombres sont descriptifs. Ils ne séparent pas l'erreur spatiale du solide
de l'écart de modèle entre poutre et solide et ne qualifient pas toute la
route dynamique.

Les autres niveaux conservés par J13 donnent un contexte utile, sans être une
nouvelle campagne J23 :

| Maillage | Pic UZ bout | Écart max à EB / pic EB | RMS à EB / pic EB |
|---|---:|---:|---:|
| 8×1×1 (J12) | 0,166927 mm à 45,3 ms | 15,376 % | 5,944 % |
| 8×2×2 | 0,167512 mm à 45,4 ms | 11,371 % | 4,407 % |
| 8×4×4 | 0,167647 mm à 45,5 ms | 10,488 % | 4,065 % |
| 16×2×2 | 0,168378 mm à 45,8 ms | 4,818 % | 1,808 % |

Sur le même 8×2×2, le changement de pas de 0,1 à 0,05 ms produit une
différence d'histoire maximale, normalisée au pic EB, de 0,0348 % au bout
(RMS 0,0105 %) et 0,0497 % à mi-longueur (RMS 0,0168 %). À pas et longueur
fixés (`nx=8`), le 2×2→4×4 transverse change l'histoire de 0,882 % du pic EB
au bout et 0,957 % à mi-longueur; le 8×2×2→16×2×2 longitudinal change
l'histoire de 6,647 % et 7,877 %, respectivement. Ces comparaisons indiquent
que l'erreur temporelle observée est beaucoup plus petite que les variations
spatiales et l'écart à la poutre; elles ne démontrent pas une convergence 3D
complète.

## Reproduction locale sans solveur

Depuis la racine du dépôt :

```powershell
python research/j23/transient_flexure_reference/prepare_abaqus_case.py
python -m pytest tests/unit/test_j23_transient_reference.py::test_archived_tet10_mesh_and_load_match -q
python -m pytest tests/unit/test_j23_transient_reference.py::test_generated_deck_model_and_time_contract -q
python -m pytest tests/unit/test_j23_transient_reference.py::test_qf_reference_export_is_physical_time_aligned -q
python -m pytest tests/unit/test_j23_transient_reference.py::test_external_history_comparison_accepts_synthetic_identical_curves -q
```

Ces vérifications manipulent seulement des archives et génèrent le deck, des
CSV/JSON et une figure. Elles n'assemblent ni ne résolvent un modèle FEM.

## Exécution externe à l'avenir

1. Installer/disposer d'une version licenciée et fonctionnelle d'Abaqus/Standard.
2. Régénérer les artefacts avec la commande de préparation ci-dessus et
   vérifier les SHA de `data/` et le contrat J23.
3. Se placer dans le dossier du paquet. Exécuter un `datacheck`; s'il réussit,
   lancer une seule tentative de calcul :

   ```text
   cd research/j23/transient_flexure_reference
   abaqus job=j23_tet10_transient_flexure input=j23_tet10_transient_flexure.inp datacheck cpus=1 interactive
   abaqus job=j23_tet10_transient_flexure input=j23_tet10_transient_flexure.inp cpus=1 interactive
   ```

4. Extraire les états calculés :

   ```text
   abaqus python extract_abaqus_history.py j23_tet10_transient_flexure.odb abaqus_history.csv
   python compare_external_history.py --external-csv abaqus_history.csv
   ```

Le contrat J23 borne l'exécution future à un calcul, 1 800 s, 4 GiB RSS
observée (contrôle souple), 1 CPU et 1 GiB de sorties. Toute erreur de
datacheck ou interruption arrête l'étude; une reprise nécessite une nouvelle
classification et une nouvelle trace. Les écarts de courbes sont rapportés
avec des normes RMS et maximum divisées par le pic QF au même point sur
l'intervalle commun; aucune tolérance de corrélation n'est déclarée PASS.

## Artefacts

- `j23_tet10_transient_flexure.inp` : deck Abaqus/Standard généré et non exécuté.
- `load_preflight.json` : vérification géométrique et de charge.
- `contract.json` : contrat externe J23 `FROZEN_NOT_RUN` avec sources, entrées,
  budgets, indicateurs et conditions d'arrêt.
- `artifact_manifest.json` : tailles et empreintes SHA-256 des données,
  deck, préflight et assets.
- `data/j13_tet10_8x4x4_model_inputs.npz` : coordonnées, connectivité, volumes
  et charges nodales archivés.
- `data/j13_tet10_8x4x4_qf_history.npz` : historique QF et Euler–Bernoulli.
- `data/j13_tet10_8x4x4_qf_result.json` : indicateurs et wrenches QF J13
  archivés.
- `data/j13_tet10_8x4x4_qf_animation_states.npz` : états de déplacement QF
  retenus pour l'animation.
- `extract_abaqus_history.py` et `compare_external_history.py` : extraction
  ODB et comparaison future après un calcul Abaqus réellement exécuté.
- `site_assets/j13_tet10_8x4x4_qf_animation.gif` : animation QF des
  checkpoints réellement calculés; 101 images couvrant 100 intervalles de
  0 à 80 ms, amplification de déplacement ×1000, 10 images/s d'affichage. Les
  10 images/s ne représentent pas la durée physique.
- `site_assets/j13_animation_manifest.json` : manifeste de déduplication du
  dernier état, bit à bit identique, et provenance de l'animation.
- `site_assets/j13_tet10_8x4x4_mesh_and_bcs.png` : maillage et appuis/charge.
- `site_assets/qf_euler_bernoulli_probe_histories.csv` et `.png` : historiques
  et courbes QF/référence préparés depuis les données archivées.
- `site_assets/qf_support_reaction_checkpoints.csv` et
  `site_assets/qf_equilibrium_summary.json` : 101 lignes d'archive, dont le
  checkpoint final 80 ms est répété deux fois de façon identique; le
  comparateur supprime seulement cette ligne dupliquée après vérification
  d'égalité, sans changer l'archive historique.

Les fichiers du site sont des brouillons préparés localement. Rien n'a été
publié.

## Documentation externe

- [Abaqus: C3D10 element index](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEELMRefMap/simaelm-c-stdelementindex.htm)
- [Abaqus: integration points for tetrahedral elements](https://docs.software.vt.edu/abaqusv2025/English/SIMACAETHERefMap/simathe-c-tritetwedge.htm)
- [Abaqus: implicit direct dynamics and Newmark/HHT parameters](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEANLRefMap/simaanl-c-dynamic.htm)
- [Abaqus: `*DYNAMIC` keyword](https://docs.software.vt.edu/abaqusv2026/English/SIMACAEKEYRefMap/simakey-r-dynamic.htm)
- [Abaqus: field output time intervals](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEKEYRefMap/simakey-r-output.htm)
