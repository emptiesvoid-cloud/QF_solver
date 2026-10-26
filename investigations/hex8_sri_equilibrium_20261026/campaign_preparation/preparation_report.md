# HEX8-SRI — Préparation de la campagne structurelle limitée

**État :** préparation terminée; aucune exécution FEM autorisée ou lancée.

**Branche :** `research/hex8-sri-equilibrium`

**Worktree :** `E:\QFSolverAgents\hex8-sri-research`

**Commit de gel des sources mesurées :** `344bb385b905544e8d94df496c312d5904edb55f`

**Empreinte de sources par l’algorithme du contrôleur :** `60131a66dcafefd55c5b3300c505da3c3a495f2e79619c7006202e051919ef7f`

## 1. Compatibilité du contrôleur et limite actuelle

Le worktree de recherche **n’est pas enregistré et ne peut pas actuellement lancer de FEM** avec `scripts/development_autonomous.py`.

- `load_policy()` exige que la table des worktrees contienne exactement `d01`, `c01` et `e01`; son contrat n’accepte pas l’ajout actuel de `hex8sri`.
- Les budgets configurés sont obligatoirement à trois tentatives par nodeid; une campagne bornée à une tentative par node nécessite une extension explicite du validateur.
- Le préflight exposé par le contrôleur est D01-spécifique. Aucun reçu de collecte général n’est disponible pour ces six nodes.
- Le contrôleur vérifie la racine Git, la branche, l’ascendance du commit de référence, l’existence du module dans la racine de tests fixe, l’allowlist exacte et une empreinte du code source/importé. La cible doit donc être enregistrée après gel du harness exécutable.
- `Hex8SRIElement` n’est pas dans `ElementRegistry`. Le modèle global standard ne peut pas sélectionner SRI sans un adaptateur d’essai isolé. Le protocole proposé garde cet adaptateur local au processus de recherche, sans inscription publique persistante.

Contrats hashés au moment de la préparation : contrôleur `d17a026f8f3688777c42c741be34905eed3d706a074443407b086c4a81298e74`; plugin pytest `c1cf6238bba05fa24de5c455beac9ddd6844935999e8b4556d3b13e5f6e9ee16`; politique `2e2fb54a0c2dcfea5312008c5985acf7df4fd5eb9367d777fddf6ac31e6d0822`. Aucun de ces trois fichiers n’a été modifié.

La proposition d’inscription sous l’identifiant `hex8sri` et les six manifestes restent inactifs (`execution_authorized=false`). Il faudra une décision Owner pour étendre le contrôleur/politique et préparer le harness exécutable. Les manifestes courants décrivent l’état de préparation; toute modification ultérieure du test ou du contrôleur impose un nouveau gel et de nouvelles empreintes avant exécution.

## 2. Configurations communes figées

| Élément | Configuration préparée |
|---|---|
| Géométrie | Porte-à-faux régulier `20×1×1 m`; axes `x=[0,5,10,15,20]`, `y,z=[0,0.5,1]` |
| Maillage | `4×2×2`, soit 16 HEX8 affines; 45 nœuds; volume total 20 m³; volume par élément 1,25 m³; `det(J)=0,15625 m³` au centre et aux huit points |
| Matériau | Élasticité isotrope linéaire; `E=1,0e6 Pa`; `ν=0,3` ou `0,4999`; densité inutilisée |
| Appuis | Face `x=0` bloquée en `UX, UY, UZ`; 9 nœuds et 27 DDL fixés |
| DDL libres | Ordre par nœud `UX, UY, UZ`; 135 DDL au total, indices fixés `0–26`, libres `27–134` (108 DDL) |
| Charge | Traction cohérente uniforme `t=(0,0,−1) Pa` sur la face `x=20`, aire 1 m²; 9 forces nodales intégrées identiques pour les six cas |
| Résultante de charge | `F=(0,0,−1) N`; moment externe à l’origine `(−0,5, 20, 0) N·m` |
| Solveur proposé | Statique linéaire, méthode directe, backend SciPy; contrat existant `residual_failure_tolerance=1e−7` conservé |

Les trois opérateurs sont : `HEX8` standard; `HistoricalHex8SRIElement`, qui surcharge uniquement le bloc central volumique avec l’expression du parent sans le poids 8; `Hex8SRIElement` corrigé. Le reproducteur historique est dans le module de test préparatoire, sans retour arrière du source corrigé ni mutation des archives.

## 3. Nodeids collectés et six manifestes

Collecte seule exécutée :

```text
python -m pytest --collect-only -q tests/verification/test_hex8_sri_structural_campaign.py
```

Résultat : six nodes collectés, aucun corps de test exécuté. Le module porte un marqueur `skip` explicite et n’est pas dans l’allowlist active. Ces identifiants sont donc exacts et collectés, mais ne sont pas encore des cibles FEM exécutables.

| Cas | Nodeid proposé exact | SHA-256 du manifeste |
|---|---|---|
| HEX8 standard, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[hex8_standard_nu_0p3]` | `43fa298abddff229d18ae88f74244b10daac5820e88ad1eb7c995e313e7d2580` |
| SRI historique, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_historical_nu_0p3]` | `261044f2f26afdc74d9415c87a2f430c2994d0430e8e7ef0532ce4a51aa60b9f` |
| SRI corrigé, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_corrected_nu_0p3]` | `cc78972d2222f275125b94ca19eac25da5cd12ebd257151296390d1b1124835f` |
| HEX8 standard, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[hex8_standard_nu_0p4999]` | `c75464745552f8ef853a042003224c3a812740f3e2c00978b1f7bcc2c9a7f7bb` |
| SRI historique, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_historical_nu_0p4999]` | `db9c99e046160466560a4a632aeac65bcc175c447f9dc0c41d5c5c75cc9d7234` |
| SRI corrigé, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_corrected_nu_0p4999]` | `d876f36039dc0949d82c038c8244d2c69ca33e21cc5a1cdd1577b8eea920cde9` |

Manifeste commun : `003c8551d05c0ea4029e8ce5b552d6900abf306788d10bb43a829ad0be7737dc`.

Proposition d’inscription et empreintes : `873e8cfae6cfc58040e0ab5801ac44681de6dd4fcfec1c5c35a37287507fd326`.

## 4. Observables, unités et critères préalables

Les six cas utilisent le même vecteur nodal, les mêmes coordonnées, connectivités, `E`, ordre des DDL, appuis, méthode directe et tolérance. Chaque sortie doit préserver :

- moyenne **signée et pondérée par l’aire** de `UZ` sur la face chargée, en m; vecteur complet des déplacements;
- déformations aux huit points de Gauss de chacun des 16 éléments, sans dimension;
- énergie interne `0,5 uᵀKu` et travail `uᵀF`, en J; défaut `2U−W` et défaut normalisé par `max(|W|, 1 J)`;
- résidu libre `Kff uf−Ff`, vecteur et norme en N, ainsi que la mesure relative utilisée par le solveur;
- réactions individuelles aux 27 DDL fixés, résultante et fermeture globale des forces en N;
- fermeture des moments `Σ x×(F+R)` autour de `(0,0,0)`, en N·m;
- condition `κ₂(Kff)` calculée sur le système réduit dense `108×108`, valeur et méthode;
- temps total du contrôleur et temps internes assemblage/solve/post-traitement; RSS maximal observé et volumes archivés.

Avant résultats, la validité numérique est définie par des valeurs finies, des déterminants positifs au centre et aux points de Gauss, et le respect du contrat direct existant `1e−7` pour le résidu relatif. Les fermetures et défauts d’énergie sont des observables rapportés avec formules et échelles fixes; **aucun seuil de fermeture ou de réponse structurelle nouveau n’est inventé**. Aucun critère ne sera ajusté après lecture des sorties.

Budgets proposés par cas : 180 s; RSS 1 024 MiB (moniteur souple); 8 processus; stdout/stderr 8 MiB chacun, 16 MiB agrégés; temporaires et archive 64 MiB surveillés; au moins 1 024 MiB libres; BLAS mono-thread; une tentative par nodeid, six au total. Ces budgets restent à approuver et à faire accepter par l’extension du contrôleur. Les matrices `K`, `Kff`, 16 matrices élémentaires, `F`, `u`, résidus, réactions, connectivités et déformations sont prévues dans des artefacts de moins de 64 MiB par cas.

## 5. Séparation des conclusions prévues

Le contrôle analytique de `Kvol` établit déjà le facteur quadrature et reste distinct des résultats structurels. La variation de déplacement/énergie entre standard, SRI historique et SRI corrigé mesurera un effet de réponse pour ce seul maillage. Les résidus et fermetures décriront équilibre et robustesse numérique. Le contraste à `ν=0,4999` donnera un indice de verrouillage, pas une preuve isolée. Avec un seul maillage, aucune convergence spatiale ne peut être conclue.

## Décision Owner requise

Décider si le contrôleur/politique peut recevoir une inscription de recherche séparée `hex8sri`, un préflight exact pour ces six nodes, un budget d’une tentative par node et une capture vérifiable des empreintes de manifestes. Le harness exécutable doit ensuite être implémenté et gelé; les manifestes et empreintes seront recalculés s’il change. **Aucune des six résolutions ne doit commencer avant cette décision et la validation du gel final.**
