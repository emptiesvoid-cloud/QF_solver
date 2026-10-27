# Limites connues et écarts de mesure

## Limites des six calculs globaux

1. Un seul maillage `4×2×2`; aucune convergence spatiale mesurée pour la campagne six cas.
2. La géométrie est régulière et affine par élément. Il n’y a aucun test global de distortion ou d’élément mal conditionné.
3. Élasticité isotrope linéaire, petites déformations, statique, matériaux `E=1 MPa`, deux valeurs de `ν`; aucun comportement non linéaire, dynamique, contact, plasticité ou matériau anisotrope.
4. HEX8-SRI reste hors du registre public. Le résultat n’est pas une qualification ni un support de production.
5. Le contrôle de Jacobien couvre le centre et huit points de Gauss. Pour les géométries distordues, cette sélection n’établit pas la positivité en chaque point du volume.
   Un écran purement géométrique a depuis mesuré sept familles aux mêmes neuf points; elles sont toutes échantillonnées positives, mais aucune matrice de rigidité n’a été assemblée, et aucune des familles n’a de certificat Jacobien continu. Les métriques figurent dans `DISTORTION_STABILITY_PROTOCOL.md`.
6. Le résidu, les fermetures globales et la condition proviennent de `K`, `F`, `u` du même calcul. Ils contrôlent l’algèbre et le solve, non l’exactitude constitutive.
7. L’énergie et la fermeture force/moment n’avaient pas de seuil d’acceptation gelé. La valeur historique `energy_defect_normalized` n’est pas sans dimension, car le dénominateur est au moins `1 J`; les sidecars ne sont pas corrigés.
8. Le `run.json` ne porte pas directement les hashes du sidecar ou NPZ. La liaison est reconstituée de façon unique, mais n’est pas un lien direct signé.
9. L’agent principal a écarté des résultats numériques d’eigensolve exécuté par erreur par un sous-agent sur une matrice `Kff` déjà archivée. Aucun de ces résultats n’a été utilisé ni reproduit; cet écart de processus est conservé dans `DECISION_LOG.md`.

## Limites de la preuve du facteur 8

Le poids rétablit exactement l’intégrale volumique constante sur un cube affine pour une déformation constante. Le point central unique ne devient pas une quadrature exacte pour un déterminant et une déformation variables sur un HEX8 non affine. Le correctif est la réparation du facteur de mesure de la règle, pas une preuve d’exactitude universelle de l’intégration SRI.

## Limites des preuves historiques connexes

- WP10 a évalué des raffinements axiaux 4/8/16 avec un oracle de poutre Timoshenko et rapporté une erreur décroissante et une réduction d’erreur SRI de 76,0 % à `ν=0.30` et 61,9 % à `ν=0.4999`. C’est une tendance bornée à cette géométrie, pas une validation de convergence 3D indépendante.
- WP13-12 garde un contrat qui rapporte énergie et équilibre FAIL; la décision historique a retenu le statut expérimental. Son gate quasi incompressible vérifie uniquement la finitude. Le cas nommé `stretched` est identique au maillage `regular` dans le générateur. Le contrôle de Jacobien n’échantillonne que les huit points de Gauss, pas le centre SRI ni tout le volume. Les replays comparent un digest sémantique de l’evidence, pas les tableaux NPZ de chaque replay, malgré l’étiquette `full_array_comparison`. Ces limites empêchent de traiter ses gates comme une certification des familles annoncées.
- Une étude locale antérieure des matrices affines a des résultats spectraux archivés; cette mission n’a pas exécuté ni utilisé de nouveau spectre. Un sous-agent a toutefois fait une analyse spectrale non sollicitée sur `Kff` archivée; sa sortie est exclue.

## Formulation du statut

Les six `PASS` sont les états de test aux critères historiques (finitude, Jacobiens échantillonnés, résidu libre). Ils ne changent pas les statuts `NOT_ASSESSED_SINGLE_MESH`, `REPORTED_NO_ADDITIONAL_THRESHOLD`, ni la recommandation `RESEARCH_ONLY`.
