# WP12-B / HEX8-SRI — correction prospective et état de campagne

**Statut : correction locale vérifiée par tests d’élément ; campagne scientifique BLOCKED / NOT_RUN.** Ce document décrit le correctif prospectif et les décisions restantes. Il ne remplace aucun résultat historique, ne constitue pas une qualification et n’autorise aucun calcul scientifique de campagne.

## Identités et conservation des preuves

- Base de correction : release `emptiesvoids-cloud/0.2.12`, commit `8e594c3a331d5a9a1d081b5911dc3e7c8b56e567`.
- Branche dédiée : `emptiesvoids-cloud/wp12b-hex8sri-formulation-fix-20261029`.
- Rapport d’audit prospectif antérieur, inchangé : `qualification/0_2_12/WP12B_HEX8SRI_PROSPECTIVE_INVESTIGATION_20261029.md`, commit d’origine `d57ee12029b27fb0c786e5decae84998a80fc726`, SHA-256 `8d4eb26fa014ccc5635ce96bd0e109d17275d925a18d35ca67d778e35d292829`.
- Les deux échecs historiques restent `PYTEST_FAILED / CLOSED_NEGATIVE`, avec leurs NPZ, rapports, empreintes et tentatives consommées inchangés. Aucun test historique n’a été rejoué.
- Aucun préflight, manifeste de campagne, réservation ou ledger n’a été créé ou modifié dans cette correction.

## Défauts démontrés et limites causales

### Poids de quadrature volumique absent

La règle de Gauss réduite évalue le terme volumique au centre de l’élément dans le domaine de référence `[-1,1]^3`. Son poids tensoriel est `2 × 2 × 2 = 8`. Le code historique calculait `det(J) Bᵀ Dvol B` au centre sans ce poids. Le jacobien transforme l’élément de référence vers le volume physique ; il n’intègre pas à lui seul le volume de référence 8.

Pour un cube unité affine et le champ `u(x)=x`, `ε=(1,1,1,0,0,0)`, `κ=E/[3(1−2ν)]`, et l’énergie volumique exacte vaut `½ κ (tr ε)² V = 9κ/2`. Avec `E=1000`, `ν=0.3`, cela donne 3750 dans les unités cohérentes choisies. Sans poids 8, on obtient 468.75, soit exactement un huitième. C’est un défaut local de formulation démontré par identité analytique et patch élémentaire.

Ce défaut **n’est pas démontré comme la cause des résidus et fermetures globales** des deux échecs historiques. Les contrôles multiprécision antérieurs réduisent le résidu libre et l’écart énergie-travail du système archivé, tandis que les fermetures de résultantes et de moments persistent. Ces faits ne permettent pas d’attribuer les échecs au seul poids de quadrature ni à SRI seul.

### Stabilité de la décomposition constitutive

Le code historique obtenait `Ddev` par soustraction `D − Dvol`. À grand `ν`, les grandes composantes volumiques sont soustraites pour retrouver les composantes déviatoriques plus petites. Le correctif calcule directement, en notation de Voigt à cisaillement ingénieur, `Ddev_normal = 2μ(I−11ᵀ/3)` et `Ddev_shear = μI`, avec `μ=E/[2(1+ν)]`, et conserve `Dvol=κ11ᵀ`. Cela évite la soustraction catastrophique. Le test vérifie `Ddev + Dvol` contre la matrice élastique actuelle jusqu’à `ν=0.499999999`.

Cette amélioration de stabilité n’établit pas qu’elle explique les échecs historiques à `ν=0.4999`.

### Jacobien au centre

HEX8-SRI utilise un terme volumique intégré au centre. La validation précédente n’examinait que les huit points de la règle complète. Un contre-exemple déterministe a des déterminants positifs aux huit points standards et un déterminant négatif au centre : le validateur HEX8 standard l’accepte, tandis que le nouveau garde SRI le refuse. Le changement vérifie les déterminants finis et positifs aux huit points déviatoriques **et** au point volumique effectivement utilisé. Le test porte seulement sur la garde géométrique ; aucune résolution FEM n’a été lancée.

## Correctif et preuves unitaires

Fichiers proposés dans la PR technique :

- `src/solveur/elements/solid/hex8_sri.py` : poids volumique explicite 8, séparation constitutive déviatorique directe, validation du centre volumique.
- `tests/unit/test_hex8_sri_element.py` : six tests déterministes de patch affine, énergie analytique/comparaison HEX8 standard et ancien poids, stabilité près de l’incompressibilité, symétrie, six modes rigides, rang local numérique 18, fermeture des forces internes locales, Jacobien central inversé et coordonnées non finies.
- `.github/workflows/hex8-sri-element-unit.yml` : CI ciblée Ubuntu/Windows limitée à ces six tests d’élément, Ruff et compilation. Elle ne lance pas de vérification maillée ni de benchmark.

Résultats locaux : les six nodeids unitaires PASS individuellement ; Ruff PASS ; compilation Python PASS ; `git diff --check` PASS. Ces tests ne comprennent ni assemblage d’un modèle global, ni résolution d’équilibre, ni récupération des réactions d’appuis, ni comparaison à une solution physique indépendante. Le rang 18 est un contrôle numérique de la matrice d’un seul élément régulier, pas un test global de modes parasites sur maillages distordus.

Les workflows généraux existants lancent des campagnes d’ingénierie/benchmarks sur certaines bases de PR. Le workflow ajouté ici est limité aux nodeids unitaires indiqués. La CI de cette PR doit être lue comme preuve de tests d’élément, pas de qualification de campagne.

## État historique et gouvernance

- Les deux diagnostics `wp12_elements` restent chacun à une tentative consommée `PYTEST_FAILED`; le ledger historique garde son mandat `DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1`, tandis que la politique courante attend `DEVELOPMENT_AUTONOMOUS-WP12-ELEMENTS-2026-10-26-v1`. Cette divergence n’est ni migrée ni contournée ici.
- Le scope distinct `hex8sri-convergence24` reste `execution_authorized=false`. Son ledger n’existe pas dans le run-store du contrôleur observé. L’absence d’un ledger dans ce store ne prouve pas qu’il n’existe aucun historique ailleurs et ne justifie pas de créer un ledger vierge.
- La politique recense les trois cas appariés 8×4×4 (HEX8 standard, SRI historique, SRI corrigé), 675 DDL totaux, 75 bloqués et 600 libres. Ces valeurs doivent être revalidées contre les sources réelles avant toute campagne.
- La garde de critères scientifique actuelle accepte seulement les six nodeids 4×2×2 du premier lot. Elle n’a pas gelé de critères pour le lot 8×4×4. L’allowlist n’est pas un gel de critères ni une autorisation.

**Résultat pour la campagne 8×4×4 : BLOCKED / NOT_RUN.** Les manifestes de cas annoncés ne sont pas présents dans le checkout d’intégration contrôlé ; les anciens préflights sont liés à d’autres identités ; la garde de critères refuse les nodeids 8×4×4 ; le ledger courant du scope dédié est absent. Aucun de ces contrôles n’a été assoupli.

## Protocole scientifique à préparer après résolution des gates

Pour chaque niveau, conserver les trois formulations appariées avec matériau, géométrie, charge, appuis et observables identiques. Pour `8×4×4`, vérifier par les données réelles 225 nœuds, 675 DDL totaux, 75 bloqués et 600 libres avant toute sélection. Comparer les champs de déplacement, réactions, résultantes et moments, énergie interne, travail, résidus, contraintes/déformations et conditionnement, si ces observables sont effectivement archivées. Employer au moins trois niveaux de maillage cohérents pour estimer un ordre spatial ; deux niveaux ne suffisent pas. Ajouter séparément des cas minces, skew et distordus avec critères gelés avant exécution. Une référence de poutre Timoshenko est indicative pour le cas de poutre et ne constitue pas un oracle 3D indépendant pour une section mince/skew.

### Décisions Owner nécessaires avant les nouveaux calculs

1. Approuver une révision prospective et append-only du contrat de critères pour les nodeids exacts 8×4×4, sans réutiliser le gel 4×2×2 et sans changer les seuils historiques.
2. Choisir une résolution traçable de la divergence de mandat `wp12_elements` et confirmer la provenance/historique du ledger du scope `hex8sri-convergence24`; aucune réinitialisation ni migration silencieuse.
3. Après revue et intégration des changements techniques, confirmer les identités source/contrôleur, créer des manifestes distincts pour chaque cas, réaliser les préflights officiels admissibles, puis autoriser explicitement chaque tentative selon le contrat applicable.

Jusqu’à ces décisions, aucun préflight, manifeste d’exécution, réservation ou calcul de campagne n’est autorisé par le présent document.
