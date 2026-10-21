# Audit et V&V RBE2 / RBE3

Date : 2026-10-21
Révision examinée : `d68554d8ca17fe4915fa8c761fb13051327a93ce`
Statut global : implémentation statique expérimentale; preuve bornée en statique linéaire, sans qualification générale.

## Périmètre et traçabilité

Le répertoire de travail indiqué initialement, `SAFRAN/solveur`, ne contient
pas l’arborescence `src/solveur` demandée. Il s’agit d’un dépôt d’accueil
minimal. L’audit et les corrections ont donc été réalisés dans le clone QF
Solver complet déjà présent sous
`solveur/tmp/wpc01-m4-kkt-full-capture`, branche
`codex/v0.2.12-wpc01-m4-kkt-full-capture`, origine
`https://github.com/emptiesvoid-cloud/QF_solver.git`. Le dépôt d’accueil et sa
branche `main` n’ont pas été modifiés. Cette sélection de dépôt est une limite
de provenance à garder à l’esprit lors de la reprise des changements.

Fichiers modifiés pour le code, les tests et la documentation :

* `src/solveur/core/rbe.py`
* `src/solveur/core/constraints.py`
* `src/solveur/io/constraint_schema.py`
* `src/solveur/mesh/validation.py`
* `src/solveur/mesh/validation_rank.py`
* `tests/unit/test_rbe_links.py`
* `tests/unit/test_mpc_reduction.py`
* `docs/elements/liaisons_mpc_rbe.md`

Le présent rapport est ajouté dans
`docs/elements/rbe2_rbe3_audit_vv.md`. Aucun code historique de qualification
ni route publique de résolution n’a été changé. Aucune référence externe n’a
été rejouée.

## Chemin logiciel observé

`FiniteElementModel.dof_manager()` ajoute les DDL cités par les éléments,
ressorts, charges et contraintes (`src/solveur/core/model.py:83`).
`linear_constraints()` combine les MPC déclarées aux équations générées par
`rbe2_constraints` et `rbe3_constraints` (`model.py:105`, `rbe.py:35,68`). La
validation JSON est faite avant la construction du modèle dans
`src/solveur/io/constraint_schema.py`.

En statique linéaire, `ConstraintReduction.from_system()` construit une
transformation affine creuse et réduit le système :

$$u=u_0+Tz,\quad K_r=T^TKT,\quad f_r=T^T(f-Ku_0).$$

Le solveur statique résout ensuite le système réduit, reconstruit les DDL
complets et calcule le résidu `Ku-f`
(`src/solveur/core/constraints.py:43-103`,
`src/solveur/core/solvers/static.py:152-244`). La symétrie est restaurée
explicitement sur `K_r`; elle est mathématiquement préservée si `K` est
symétrique et `T` correctement construit.

Les multiplicateurs et forces de liaison sont reconstruits après résolution
par moindres carrés sur `C.T lambda = -r`, avec la convention
`Ku-f+C.T lambda=0` (`constraints.py:153-222`). Les forces généralisées de
liaison et les réactions des blocages sont rapportées séparément. Si les
équations sont redondantes, les multiplicateurs peuvent ne pas être uniques,
même lorsque leur force résultante est unique; la solution LSMR est alors une
représentation de norme minimale, pas un multiplicateur physique unique.

Un solveur de référence par multiplicateurs de Lagrange existe pour les petits
problèmes (`constraints.py:116-151`). Il compare les stratégies de résolution
pour un même jeu d’équations; il ne constitue pas un oracle indépendant de la
définition mécanique des contraintes.

## Formulation RBE2

Pour `r=x_s-x_m`, les trois équations générées sont la forme cartésienne de
`u_s-u_m-theta_m×r=0`. Les signes sont cohérents avec
`u_s=u_m+theta_m×r`. Les rotations du maître sont activées dès que la
cinématique possède un bras non nul. Un bras nul n’ajoute pas artificiellement
des coefficients rotatifs.

`tie_rotations=True` ajoute les trois relations `theta_s=theta_m`; cela ne
fait pas partie du bras cinématique translationnel. Le gestionnaire de DDL
active ces rotations même pour un nœud de solide, dont l’élément ne fournit
normalement que des translations. Ces rotations supplémentaires sont alors
des coordonnées cinématiques sans raideur élémentaire propre. L’option est
pertinente pour les familles possédant des rotations physiques, selon la
modélisation, et doit être évitée sur un nœud solide si cette égalité n’est pas
voulue.

La liaison impose uniquement la relation rigide indiquée; elle n’ajoute pas
de raideur parasite. Un corps entier peut toutefois conserver ses modes de
corps rigide si les supports ne les éliminent pas. Plusieurs esclaves,
liaisons croisées, DDL bloqués ou `tie_rotations` peuvent créer des relations
redondantes ou incompatibles. Les cycles, pivots nuls, DDL répétés et conflits
détectés sont refusés par le validateur MPC; il ne s’agit pas d’un solveur
général de rang révélant toutes les dépendances linéaires possibles.

La conservation du torseur découle du travail virtuel des équations
cinématiques et est contrôlée dans les tests statiques et l’audit d’équilibre.
Une preuve analytique à plusieurs bras arbitraires obtient un résidu cinématique
maximal de `1.11e-16`. Un esclave de type solide et un esclave poutre/coque sont
couverts quant à l’activation des DDL disponibles; cela ne valide pas toutes
les assemblages ni toutes les familles d’éléments.

## Formulation RBE3

### Projection `rigid_body_projection`

Pour chaque indépendant `i`, `A_i=[I,-S(r_i)]`, où
`r_i=x_i-x_ref` et `S(r)v=r×v`. La solution pondérée minimise le résidu
translationnel et donne `H=(A.T W A)^-1 A.T W`, si la géométrie est de rang
plein. Le transfert dual `f_I=H.T p` découle du travail virtuel
`p.T dq_ref=(H.T p).T du_I`; comme `H A=I`, le torseur, force et moment,
est reproduit. Les poids de ce mode sont strictement positifs et la géométrie
doit porter les six mouvements rigides.

### Défaut démontré et correction

**P1 corrigé — test de rang dépendant des unités et perte de précision.** La
version initiale formait les équations normales `A.T W A` et comparait leur
rang à un seuil absolu au moins égal à `1e-12`. Un même trépied 3D de rang
plein était accepté à l’échelle de coordonnées 1 et refusé vers `1e-6` à
`1e-8`, puis refusé aussi pour de très grandes coordonnées. La géométrie
physique était identique à similitude près; le diagnostic dépendait des unités
et les équations normales élevaient le conditionnement au carré.

La correction centre les coordonnées au barycentre pondéré, met les colonnes
rotationnelles à l’échelle de la longueur du nuage et applique une SVD au
système pondéré, sans former `A.T W A` (`rbe.py:117-190`). Le rang est refusé
si `sigma_min/sigma_max <= 1e-12`. La translation ajustée au barycentre est
convertie au nœud de référence demandé. Un rapport de rang inférieur à ce
seuil demeure une géométrie refusée, même si un calcul avec davantage de
précision pourrait la distinguer du rang déficient.

Les tests vérifient les échelles géométriques `1e-8`, `1` et `1e8`, des
facteurs de poids communs `1e-200`, `1`, `1e200`, les géométries dégénérées et
quasi dégénérées, ainsi qu’une géométrie non symétrique. Un oracle de moindres
carrés construit séparément compare les coefficients de projection. Une
vérification numérique déterministe a mesuré : erreur maximale de `H` contre
l’oracle `7.77e-16`; `|HA-I|` maximal `1.78e-15`; erreur de résultante de force
`7.55e-15`; erreur de moment `1.15e-14`; variations de coefficients sous
changement d’échelle de translation `1.53e-15` et de rotation `2.59e-15`.
Ces nombres proviennent d’un diagnostic numérique dédié; les assertions pytest
ne les impriment pas comme métriques de campagne.

### Mode `weighted`

Ce mode impose une interpolation pondérée indépendante par composante. Les
poids sont normalisés par leur somme. Leur échelle commune n’a aucun effet;
des poids signés peuvent produire une extrapolation algébrique lorsque la
somme n’est pas presque annulée. Sans bras de levier géométrique, le mode ne
garantit pas la transmission du moment en 3D et ne doit pas être présenté comme
un distributeur spatial de charges. Il n’ajoute pas non plus de rigidité aux
nœuds indépendants : les termes sont des contraintes MPC.

La normalisation utilise maintenant les poids divisés par leur maximum
absolu, puis rejette une somme relative quasi nulle (`rbe.py:192-213` et
`constraint_schema.py:94-108`). Un essai a mis au jour une régression réelle :
un poids brut négatif pouvait devenir positif après normalisation par une
somme négative, contournant le contrat des poids strictement positifs de la
projection rigide. La validation de positivité a été déplacée avant la
normalisation; le test correspondant passe dans l’exécution finale.

### Équivalence Nastran

Les libellés RBE2/RBE3 décrivent ici le comportement du solveur, pas une
compatibilité complète de format ni de fonctionnalités Nastran. La projection
QF reconstruit les six coordonnées généralisées depuis les translations des
nœuds indépendants avec un jeu de poids positif commun aux trois directions.
Le mode pondéré fournit une équation par composante choisie. Les jeux de
composantes et pondérations plus généraux, systèmes d’axes locaux et variantes
de composantes indépendantes de type `UM` ne sont pas pris en charge. La
correlation Code_Aster historique citée dans la documentation est un seul
bras RBE2; elle ne valide pas RBE3. Elle n’a pas été rejouée ici : le moteur
Docker n’était pas disponible dans l’environnement.

## Réduction MPC, rang et réactions

**P2 corrigé — seuils absolus non invariants à l’échelle.** La validation
refusait un pivot dépendant inférieur à `1e-14` et le réducteur éliminait des
coefficients inférieurs à `1e-15`. Multiplier toute une équation par une
constante ne doit pas en changer le sens; les petits coefficients valides
pouvaient pourtant être supprimés ou rejetés. Le pivot est maintenant contrôlé
relativement au maximum des coefficients de sa ligne, et le réducteur ne
supprime que les zéros exacts (`constraints.py:226-240,280-310`,
`constraint_schema.py:135-163`). Des essais JSON et directs vérifient cette
invariance et la conservation d’un coefficient sous-femtoscopique.

Cette règle relative résout le cas du simple redimensionnement d’une équation.
Elle n’est pas une équilibration dimensionnelle générale pour des lignes
mélangeant translations, rotations et bras géométriques très différents; les
unités et le choix du DDL dépendant restent importants pour des modèles
extrêmes.

**P2 corrigé — faux diagnostics de mécanisme sous RBE/MPC.** La validation de
rang assemblait auparavant `K` en supprimant seulement les DDL fixes, sans
appliquer `T`; les rotations auxiliaires d’un RBE2 pouvaient donc être
signalées comme modes nuls alors qu’elles étaient liées par la cinématique.
Le graphe des composants ignorait également les connexions MPC/RBE. Les
petits modèles (au plus 180 DDL) vérifient désormais le rang de `T.T K T` et
le graphe réunit les nœuds liés (`validation_rank.py:12-66`,
`validation.py:358-382,596-701`). Un test avec un esclave RBE2 et deux
translations d’appui vérifie quatre DDL indépendants, un rang réduit 4 et
aucun mode nul.

**Limite restante P2.** Ce contrôle densifie le système réduit et ne tourne
que jusqu’à 180 DDL actifs. Son seuil spectral comprend un plancher absolu;
les modèles à rigidités de très petite échelle peuvent donc être classés de
façon conservatrice. Au-delà de 180 DDL, le rapport indique que le rang n’a pas
été vérifié et émet un avertissement. Cela améliore le diagnostic, mais ne
constitue pas un algorithme scalable de qualification du rang.

La construction récursive de `T` est creuse dans sa représentation, mais la
substitution peut provoquer du remplissage. Aucune mesure de mémoire ou de
temps sur grand modèle n’a été faite. L’assemblage et la résolution nominale
restent par élimination, pas par pénalisation. Les multiplicateurs sont un
contrôle de réaction après résolution, et non les inconnues du solveur nominal.

## Compatibilité des routes

Les MPC/RBE sont pris en charge dans la route `linear_static`. Le système
réduit conserve également la symétrie lorsque les hypothèses le permettent.
Une transformation dynamique cohérente serait mathématiquement
`K_r=T.T K T`, `M_r=T.T M T`, `C_r=T.T C T` et
`f_r=T.T(f-Ku_0)` (avec les termes cinématiques additionnels si `u_0` dépend
du temps), mais cette composition n’est pas activée. `PreparedDynamicSystem`
refuse explicitement MPC/RBE (`src/solveur/core/analyses/prepared_dynamic_system.py:380`).
Le contact les refuse aussi (`src/solveur/contact/solver.py:461`). Les voies
modal, Newmark, harmonique, statique non linéaire et contact ne sont donc pas
promues par les présents résultats. Les transformations de masse/amortissement,
les états non linéaires et le couplage contact restent à concevoir et vérifier.

## V&V et chronologie

Commande finale exécutée, avec un seul thread BLAS :

```powershell
$env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'
python -m pytest -q tests/unit/test_rbe_links.py tests/unit/test_mpc_reduction.py tests/unit/test_backend_edge_matrix_contracts.py tests/unit/test_mesh_validation.py tests/unit/test_mesh_validation_edge_contracts.py tests/unit/test_code_aster_rbe.py tests/unit/test_wp13_02_mixed_dynamic_validation.py
```

Résultat final observé : **89 passed, 0 failed**, en `2.70 s` pytest (`4.89 s`
temps de commande). Aucun solveur externe ou FEM natif n’a été exécuté. Les
tests Code_Aster du dépôt sont opt-in; aucune campagne externe n’a été lancée.

Les échecs intermédiaires sont conservés dans l’historique de travail :

1. Premier lot ciblé : 19 réussis, 2 échecs dus à des oracles de test mal
   construits (bras RBE2 nul dans le fixture et erreur d’échelle dimensionnelle
   dans la comparaison de projection); les fixtures ont été corrigés.
2. Une collecte ultérieure a rencontré une `IndentationError` introduite dans
   l’édition du test; corrigée avant exécution des assertions.
3. Un lot suivant : 20 réussis, 1 échec parce que le fixture n’activait qu’un
   bras sur X, donc la rotation RX n’était pas cinématiquement couplée; le
   fixture a été remplacé par un décalage 3D.
4. Lot complet ciblé : 87 réussis, 1 échec révélant la validation incorrecte
   d’un poids négatif après normalisation; correction de source effectuée.
5. Après correction : 88 réussis. Après ajout de la validation programmatique
   des nœuds RBE3 pondérés et du test de rang RBE2 à deux appuis : **89
   réussis**.

Contrôles statiques finaux : parsing AST Python des sept fichiers Python
modifiés réussi; `git diff --check` réussi. `ruff` n’est pas installé ou
accessible comme commande dans cet environnement et n’a donc pas été exécuté.
La revue finale est une **auto-revue source et V&V**, pas une revue numérique
indépendante par un second ingénieur.

## Tableau de maturité

| Fonctionnalité | État initial observé | Modification | Preuve | État final |
|---|---|---|---|---|
| Équations RBE2 et bras | Formulation `u_s=u_m+theta_m×r` déjà présente | Validation entrée finie; aucun changement de formule | Mouvement rigide arbitraire, offsets multiples, statique | Vérifié dans les cas statiques testés |
| `tie_rotations` / familles | Rotations générées par MPC, y compris pour un solide | Documentation de la sémantique et du risque | Tests d’activation solide/poutre | Limite explicitée; choix modèle requis |
| Projection RBE3 | Équations normales et test de rang dépendant des unités | Centrage, mise à l’échelle, SVD et poids stables | Oracle moindres carrés, invariances d’échelle, force/moment | Vérifié de façon bornée; seuil de rang `1e-12` |
| RBE3 `weighted` | Interpolation composante par composante | Normalisation commune robuste et validation des nœuds | Cas ressorts et entrée invalide | Vérifié pour ces cas; moment non garanti |
| Réduction MPC | Substitution affine sparse, seuils absolus | Pivot relatif et conservation des coefficients non nuls | Comparaison KKT, mise à l’échelle, cycles/conflits | Vérifié sur petits modèles |
| Récupération réactions | LSMR sur résidu complet | Pas de changement | Fermeture statique et torseur dans les cas couverts | Vérifié borné; multiplicateurs potentiellement non uniques |
| Rang avec MPC/RBE | Rang de K brut et heuristiques nodales | Rang du système réduit jusqu’à 180 DDL; graphe MPC | Fixture RBE2 avec mécanisme auxiliaire apparent | Amélioré; grands modèles et seuil d’échelle ouverts |
| Modal, Newmark, harmonique, non linéaire, contact | Routes distinctes et refus présents | Aucun changement | Tests de refus existants | Non pris en charge / refusés; non qualifiés |
| Corrélation externe | Preuve historique documentée pour un RBE2 | Aucune modification de résultat | Docker indisponible, preuve non rejouée | Historique seulement; pas de nouvelle validation externe |

## Gravité et limites restantes

* **P0 : aucun identifié** dans le domaine statique testé.
* **P1 corrigé :** rang de projection RBE3 dépendant des unités et conditionné
  par les équations normales.
* **P2 corrigés :** élagage/pivot MPC non invariant à l’échelle; poids RBE3
  sensibles à une échelle commune; faux modes et composants de maillage dus à
  l’ignorance des contraintes.
* **P2 ouverts :** seuil de rang conservateur pour géométries très mal
  conditionnées; test de rang dense limité à 180 DDL; remplissage/coût de `T`
  non mesurés; non-unicité des multiplicateurs avec contraintes redondantes;
  absence de validation externe RBE3 et absence de convergence au raffinement.

Les résultats montrent une vérification bornée du comportement statique,
pas une qualification structurelle générale. La charge redistribuée via
RBE3 n’a pas été validée sur une structure déformable complexe. Il n’y a pas
de démonstration de convergence au raffinement, d’analyses dynamiques, de
compatibilité contact, de toutes les topologies RBE2/RBE3 ni de qualification
Nastran/Code_Aster. Aucun résultat historique n’a été remplacé ou promu.

## Provenance des fichiers modifiés

SHA-256 calculés après les corrections (le présent rapport est ajouté après
ces calculs) :

| Fichier | SHA-256 |
|---|---|
| `src/solveur/core/rbe.py` | `3031c1c106c220e96c8b2e16dd0fe57a5efe028792891962867b8351ec95793c` |
| `src/solveur/core/constraints.py` | `428f9d2bd907859e37a2dc8ea7e86102d804c1ec61c3473051cf85ab4fca9b41` |
| `src/solveur/io/constraint_schema.py` | `08735d9c518097053597967dabc9f2aa2630a5b836d9daa1931502332ea50a6a` |
| `src/solveur/mesh/validation.py` | `2803f7ab6f736c0ee70bd1d70193c399d870a36578b17e17740ae3e06baa8911` |
| `src/solveur/mesh/validation_rank.py` | `b286c05fa98dd0d1eb6c14e6b6e51fa567c25b01c61838c870874d6bdb71ee7b` |
| `tests/unit/test_rbe_links.py` | `2986a75c6e224a65f30f05492fe29b0dd4b40c530ca48c0ac9f857701a759941` |
| `tests/unit/test_mpc_reduction.py` | `c6d2c0c5685ed9d614c4ae696db4fffe322409904e7fa19e9abff859880ea009` |
| `docs/elements/liaisons_mpc_rbe.md` | `6ebcecfaccccfb44342873ce8f42b3a7c4dd8e8c62d3c04573e357acd52afa39` |

Les modifications ne sont pas commitées. La révision Git reste
`d68554d8ca17fe4915fa8c761fb13051327a93ce`; le worktree du clone complet
contient les huit fichiers modifiés listés plus haut et ce rapport non suivi.
Le dépôt d’accueil reste inchangé.
