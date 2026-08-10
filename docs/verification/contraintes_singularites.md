---
doc_id: DOC-VV-SINGULAR-STRESS-001
revision: 0.3
status: development
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Contraintes proches des singularites

## Objet

Cette methode transforme les contraintes proches d'un trou, d'un angle rentrant,
d'une charge ponctuelle ou d'un encastrement idealise en preuves lisibles. Elle
ne cherche pas a rendre artificiellement fini un pic mathematiquement singulier.
Elle accepte une grandeur seulement si son domaine d'observation, son maillage,
sa comparaison de reference et sa convergence sont explicites.

Le premier usage est le scope orthotrope TET4/TET10. La methode est generique et
pourra ensuite etre appliquee aux autres elements.

## Etape 1 - Classer le phenomene

| Classe | Exemple | Pic au point | Grandeur a accepter |
| --- | --- | --- | --- |
| concentration finie | trou ou congé de rayon connu | doit converger avec le raffinement | contrainte locale, chemin et moyenne de bande |
| singularite mathematique | angle rentrant ideal, force ponctuelle, blocage ponctuel | peut diverger avec `h -> 0` | chemin a distance fixee, moyenne de bande, resultant ou facteur asymptotique |

Un pic nodal n'est jamais une grandeur suffisante a lui seul. Pour une
singularite mathematique, il reste informatif mais n'entre pas dans un verdict
PASS ou FAIL.

## Etape 2 - Definir les observables

Pour chaque niveau de maillage, le rapport enregistre les memes positions
physiques `r1, r2, ...` mesurees depuis la singularite. Elles doivent respecter
`r / h >= 2` sur tous les maillages, afin que le point d'observation ne tombe
pas dans la premiere couronne d'elements.

Les deux observables obligatoires sont :

1. la contrainte ou l'invariant le long d'un chemin a distance fixe ;
2. une moyenne de contrainte sur une bande, une couronne ou un petit volume de
   controle explicite.

Pour une geometrie de rayon fini, le rapport ajoute le ratio `h / R` et un
nombre suffisant d'elements a travers le rayon. Pour une vraie singularite, une
pente log-log peut etre fournie a titre de comparaison avec Williams, mais ne
remplace pas les chemins et moyennes.

## Etape 3 - Raffiner et comparer

La campagne requiert au moins quatre maillages. Sur les deux derniers :

- variation maximale du chemin <= `5 %`;
- variation de la moyenne de bande <= `5 %`;
- distance minimale `r/h >= 2`;
- ecart final <= `5 %` contre une reference analytique, Code_Aster, CalculiX
  ou essai, sur les memes zones d'observation.

Une comparaison externe doit reutiliser la geometrie, les constantes,
l'orientation materiau, les charges et les chemins de mesure. La comparaison
sur maillage identique est privilegiee pour separer les ecarts de formulation
des ecarts de discretisation.

## Decision d'acceptation

| Situation | Decision |
| --- | --- |
| concentration de rayon fini, quatre maillages et tous les seuils respectes | contrainte locale acceptee dans le domaine mesure |
| vraie singularite, chemins/moyennes convergents et correlation externe respectee | resultat structurel accepte; pic ponctuel indique comme non convergent |
| chemin trop pres de la singularite, maillages insuffisants ou reference absente | WARNING, pas de valeur locale de conception publiee |
| absence d'equilibre, zones de mesure differentes ou divergence des observables | FAIL, calcul a reprendre |

## Comparaisons prevues

`VNV-ORTHOTROPIC-SINGULAR-STRESS-005` comportera une plaque orthotrope trouee
avec rayon fini et une equerre orthotrope a angle rentrant. Les trois niveaux de
reference recherches sont, dans cet ordre : solution analytique adaptee,
Code_Aster et CalculiX sur maillage identique, puis essai si disponible.

Le protocole machine-readable est
`qualification/vnv/orthotropic_singular_stress/study.json`. Le composant
`SingularityStressAssessor` applique les seuils sur les chemins et moyennes;
la campagne est executee par
`scripts/run_orthotropic_singularity_vnv.py`.

## Execution controlee h1 a h8

La campagne finale du `2026-07-29` compare QF_solver, Code_Aster 18.1.0 et
CalculiX 2.20 sur les memes maillages TETRA4/C3D4, les memes constantes
orthotropes, les memes axes materiau, les memes blocages et les memes charges.
Elle utilise huit niveaux et une recuperation compacte quadratique ponderee par
le volume des TET4.

| Cas | Maillage fin | Increment chemin | Increment bande | Code_Aster fin |
| --- | ---: | ---: | ---: | ---: |
| trou de rayon fini | `86 469` TET4 | `1,342 %` | `0,125 %` | `< 6,0e-11 %` |
| angle rentrant | `237 358` TET4 | `1,625 %` | `3,420 %` | `< 5,4e-9 %` |

Le verdict est **PASS_STRESS_ACCEPTANCE** : les chemins a distance physique
fixe et les moyennes de bande convergent sous le seuil de `5 %`. Le pic au
sommet de l'angle rentrant reste informatif et ne devient pas une contrainte de
dimensionnement.

Code_Aster aux points d'integration est l'oracle externe bloquant. CalculiX
fournit un champ nodal extrapole avec un operateur different : son ecart sur la
bande fine de l'angle rentrant vaut `6,357 %` et reste donc un `WARNING`
diagnostique. Son ecart de chemin fin vaut `0,306 %`. Cette reserve concerne le
post-traitement nodal, pas la formulation elementaire, correlee avec Code_Aster.

Le digest public et son empreinte de manifeste sont dans
`qualification/external_reference_digests/orthotropic_singular_stress_h8.json`.
