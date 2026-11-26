# HEX8 EAS — route expérimentale intégrée localement

Date : 2026-11-25
Statut : **port local préparatoire, route explicitement expérimentale**.

## Résumé

Une route distincte `HEX8_EAS_EXPERIMENTAL` raccorde le prototype à six
déformations enrichies et divergence moyenne au registre d’éléments, à
l’assemblage sparse, aux charges solides prises en charge et à la
récupération des résultats. Elle n’est pas activée par `HEX8`, n’est pas
qualifiée et n’est pas utilisable par défaut. Les analyses non linéaires,
dynamiques, modales et de flambement, les matériaux non isotropes, les
maillages mixtes, la masse, le contact et les contraintes discrètes sont
refusés.

Les tests locaux établissent l’assemblage et le post-traitement élémentaires
sur des témoins synthétiques. **Aucune résolution globale n’a été exécutée** :
ce nouveau cas n’a pas de nodeid, contrat, scope, préflight ou ledger
enregistré dans la politique opérationnelle. Cette preuve ne suffit donc pas
à établir le comportement de la route dans un calcul statique QF Solver.

## Provenance

| Élément | Identité |
|---|---|
| Branche de travail isolée | `emptiesvoids-cloud/hex8-eas-port-readiness` |
| Base préparatoire | `e7ec33e101959fe3860fac2ed46f070fd4762bb4` |
| Produit distant `0.3.0` vérifié en lecture seule | `c4de3ff6bf4549bf68d34652bcf6fb05e36f43c4` |
| Prototype de référence | `emptiesvoids-cloud/hex8-eas-nonaffine-followup`, `270581c42219bfbeabd961b8864a2ba1b6dab244` |
| Fichier du prototype | `research/hex8sri_bending/restricted_prototype.py`, SHA-256 `a73c245e8bcde9a6f37fe64083c9d10324d737541d4f3426a269dc7b8fd8a7318` |

Le worktree utilisateur et les archives de recherche n’ont pas été modifiés.
Les verdicts historiques J7 FAIL et J14 PASS de développement restent
inchangés.

## Formulation et restrictions

L’élément emploie les fonctions et la quadrature `2×2×2` d’HEX8. Les neuf
modes bulle incompatibles sont projetés sur six amplitudes transverses aux
tangentes au centre, puis centrés par rapport à leur moyenne pondérée. La
partie déviatorique et les couplages sont condensés localement :

\[
K_c = K_{dd} - G H^{-1}G^T + K_{\mathrm{vol}},\qquad
K_{\mathrm{vol}} = K\,V\,\bar B_{\mathrm{div}}^T\bar B_{\mathrm{div}}.
\]

Le bloc local `H` doit être défini positif et son conditionnement estimé ne
doit pas dépasser `1e12`. Une géométrie, une condensation ou une donnée
matérielle invalide produit une erreur explicite ; aucun repli vers HEX8
standard n’est effectué. Cette vérification de conditionnement est
flottante et n’est pas une borne d’erreur certifiée.

L’activation demande le type explicite `HEX8_EAS_EXPERIMENTAL`. `HEX8`
continue de désigner l’élément existant à intégration complète. Le type EAS
est homogène dans le maillage et accepte un unique `SolidMaterial` isotrope,
petites déformations, analyse `linear_static` avec méthode `direct`. Les
charges nodales, de volume, gravité et tractions/pressions surfaciques non
suiveuses sont routées sur la topologie HEX8. Le type n’a pas de matrice de
masse.

Le post-traitement recalcule les six variables enrichies \(\alpha\), les
déformations et contraintes à chaque point de Gauss, la contrainte
volumique moyenne, ainsi que les énergies volumique et déviatorique. Il
retourne aussi la force d’intégration, l’action matricielle et leur écart.
Les amplitudes enrichies ont la dimension d’une longueur dans le système
d’unités du modèle ; la contrainte volumique est positive en traction.
L’export VTU marque ces cellules comme expérimentales seulement lorsqu’un
élément EAS est présent.

## Vérifications exécutées

Onze fonctions de test explicites ont passé, une fonction par invocation :

- cinq nouvelles fonctions `test_hex8_eas_*` : identité/activation, assemblage,
  charges et refus de masse ; mouvements rigides, patch affine et dérivée
  directionnelle ; entrées invalides et condensation ; refus de portée par
  le validateur et le préflight ; récupération EAS et export VTU ;
- trois tests de descripteurs de compatibilité, dont la distinction entre
  route expérimentale et routes qualifiées ;
- trois régressions HEX8 existantes sur rigidités/modes, champ affine et
  pression/traction de face.

Dans les tests, la matrice sparse assemblée correspond à la matrice
élémentaire sur un cube régulier et une carte gauchie à `ν=0,3` et
`ν=0,4999`. Les patchs affines, les six mouvements rigides, la symétrie et
la dérivée directionnelle des forces condensées sont vérifiés aux deux
valeurs de Poisson sur les deux géométries. Ces témoins sont synthétiques et
ne remplacent pas une campagne mécanique.

Une comparaison séparée du noyau local avec le prototype de recherche, à
`E=1e6` dans les deux implémentations, a donné les écarts relatifs de
Frobenius suivants :

| Géométrie | `ν` | Écart relatif des matrices |
|---|---:|---:|
| régulière | 0,3 | `5,105e-16` |
| régulière | 0,4999 | `6,667e-16` |
| gauchie | 0,3 | `5,222e-16` |
| gauchie | 0,4999 | `4,987e-16` |

Cette comparaison confirme l’implémentation locale sur ces quatre matrices,
pas l’équivalence de calculs globaux ni les performances mécaniques.

Contrôles de qualité : Ruff passe sur tous les fichiers modifiés ;
`py_compile` passe sur les fichiers Python modifiés ; `git diff --check`
ne signale pas d’espace fautif.

## Limites et décision

- Le test de post-traitement vérifie la cohérence force–action matricielle
  avec les mêmes opérateurs de l’élément ; ce n’est pas une vérification
  indépendante de l’assemblage global. La matrice du prototype constitue le
  seul contrôle croisé séparé réalisé ici.
- Aucune résolution par le solveur global, aucune comparaison de solution
  et aucun rejeu d’archive FEM n’ont été effectués dans cette mission.
- Les charges ne sont pas encore couvertes par un calcul global ; les
  réactions, le travail global et les sorties de résultats d’analyse restent
  à contrôler.
- Les résultats de recherche antérieurs restent limités aux géométries,
  chargements et niveaux de maillage archivés. Les bilans près de
  l’incompressibilité se dégradent et les modes faibles ne démontrent pas
  une stabilité générale. Les erreurs de contraintes restent plus élevées
  que celles des déplacements dans les essais de recherche.
- Aucun dépendance tierce nouvelle n’est ajoutée ; la route s’appuie sur
  NumPy et l’infrastructure sparse SciPy déjà utilisées par le solveur.

Le lot est prêt pour une **revue locale du port préparatoire**, pas pour
qualification, fusion à distance ni revendication de précision générale.
Avant d’envisager une intégration, la prochaine étape est un contrat
expérimental borné pour un unique cas linéaire global, avec nodeid, scope,
préflight et ledger neufs, puis vérification des réactions, bilans et
résultats complets après résolution. Aucun tel calcul n’est lancé ici.
