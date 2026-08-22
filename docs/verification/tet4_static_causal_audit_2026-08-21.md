# Audit causal TET4 statique : ecarts et trajectoire vers 1 %

| Champ | Valeur |
| --- | --- |
| Document | `DOC-AUDIT-TET4-STATIC-001` |
| Date | `2026-08-21` |
| Statut | `open - evidence based` |
| Domaine | TET4 isotrope, statique lineaire, petites deformations |
| Objet | Distinguer l'accord d'implementation de la convergence physique en flexion |

## Conclusion directe

La synthese multi-scope est disponible dans
[`tet4_error_causal_audit_2026-08-21.md`](tet4_error_causal_audit_2026-08-21.md).
Elle distingue explicitement le cas statique du pas de temps et reprend les
indicateurs modal, Newmark et harmonique sans modifier le statut de promotion.

La version machine-readable de cet audit est
[`tet4_static_causal_audit_2026-08-21.json`](../../qualification/vnv/tet4_static_causal_audit_2026-08-21.json).
Elle constitue la source structurée des valeurs, du gate et des actions
requises ; ce document Markdown reste la lecture technique détaillée.

Oui, un ecart inferieur a `1 %` est maintenant demontre pour le sous-cas de
flexion structuree et raffinee. Le niveau Docker/PETSc a `24 576 000` TET4
atteint `0,818328 %`, avec un residu relatif de `2,09e-16`. Il ne s'agit pas
d'une qualification generale de toutes les flexions TET4. Il est aussi
demontre que QF_solver et Code_Aster produisent la meme reponse TET4 sur un
maillage identique : l'ecart maximal mesure est `2.08e-10 %`, tres inferieur
au seuil de `1 %`.

L'ecart qui reste en flexion ne provient donc pas, a ce stade, d'une divergence
entre les deux solveurs. Il provient principalement de l'approximation de
deplacement lineaire du TET4, qui donne une deformation constante par element
et est peu efficace en flexion. Un raffinement fort est necessaire.
La campagne corrigee atteint `1,507 %` a `1,572` million de TET4, puis
`1,217644 %` a `3,072` millions. Le niveau 80 atteint ensuite `0,818328 %`.
La tendance est monotone sur les niveaux archives. Cette conclusion vaut pour
la reference de poutre et le chargement de face documentes ; elle ne doit pas
etre extrapolee aux geometries courbes, au contact ou aux grandes rotations.

## Questions auxquelles repond cet audit

1. QF_solver et Code_Aster appliquent-ils differemment le TET4 ?
2. La convergence lente est-elle numerique, liee au maillage ou liee a la formulation ?
3. Un raffinement seul peut-il raisonnablement amener l'erreur sous `1 %` ?
4. Faut-il modifier maintenant la formulation TET4 ?

## Preuve d'accord entre implementations

La campagne
[`VNV-TET4-STATIC-CODEASTER-TETRA4-021`](tet4_static_code_aster_correlation_2026-08-21.md)
utilise le meme maillage, les memes noeuds bloques et la meme charge faciale
nodalisee dans QF_solver et dans Code_Aster `18.1.0` avec `TETRA4`.

| TET4 | Ecart relatif moyen `UZ` QF_solver / Code_Aster |
| ---: | ---: |
| 100 | `3.96e-12 %` |
| 135 | `1.71e-11 %` |
| 202 | `2.08e-10 %` |
| 313 | `8.05e-11 %` |

Le critere de correlation externe `< 1 %` est donc passe avec une marge de
plusieurs ordres de grandeur. Cette preuve confirme une parite de
discretisation et d'assemblage ; elle ne prouve pas a elle seule la precision
de la discretisation par rapport a l'elasticite 3D continue.

## Convergence physique mesuree

Le second protocole emploie un porte-a-faux prismatique structure, une face
encastree et une force terminale distribuee par poids de surface. La fleche
de reference est la somme des contributions Euler-Bernoulli et Timoshenko :

```text
u_ref = F L^3 / (3 E I) + F L / (kappa G A), avec kappa = 5 / 6.
```

Cette reference est un indicateur de convergence en flexion. Une solution 3D
d'ordre eleve reste utile pour le diagnostic du voisinage de l'encastrement et
de la charge, mais l'oracle primaire de l'implementation TET4 est la
correlation TET4/TETRA4 sur maillage identique.

| Maillage structure centre | TET4 | Erreur de fleche relative |
| --- | ---: | ---: |
| `32 x 8 x 8`, 12 TET4/cellule | 24 576 | `11.711981 %` |
| `64 x 16 x 16`, 12 TET4/cellule | 196 608 | `3.791534 %` |
| `128 x 32 x 32`, 12 TET4/cellule | 1 572 864 | `1.507279 %` |
| `160 x 40 x 40`, 12 TET4/cellule | 3 072 000 | `1.217644 %` |
| `320 x 80 x 80`, 12 TET4/cellule | 24 576 000 | **`0.818328 %`** |

Le solveur iteratif du dernier niveau a converge avec un residu relatif de
`2.09e-16` apres `252` iterations au niveau PETSc a 24,576 millions d'elements.
L'ecart n'est donc pas une non-convergence lineaire. Comme l'analyse est
statique, il n'y a ni pas de temps ni integrateur temporel a raffiner.

## Causes techniques etablies

### 1. Interpolation TET4 a deformation constante

Le noyau [`tet4.py`](../../src/solveur/elements/solid/tet4.py) definit des
fonctions de forme lineaires. Les gradients sont constants dans l'element ; la
matrice deformation-deplacement `B` est donc constante et la rigidite est
calculee exactement avec une integration a un point :

```text
K_e = V B^T D B.
```

Il ne s'agit pas d'une quadrature insuffisante. Pour une elasticite lineaire
et une geometrie TET4 affine, l'integrande est constant. Augmenter seulement
le nombre de points de Gauss ne corrigera pas la precision de flexion.

Une flexion impose un champ de deplacement courbe et un gradient qui varie
dans l'epaisseur. Le TET4 ne peut le representer que par une succession de
champs constants. Cela produit une rigidite apparente excessive sur un
maillage grossier et explique la fleche sous-estimee.

### 2. Maillages Gmsh non imbriques

Les quatre maillages de la correlation Code_Aster sont non imbriques. Leur
dernier increment de fleche vaut `4.64 %` dans les deux solveurs. Cette valeur
ne mesure pas une erreur de formulation entre solveurs, mais elle rend une
estimation d'ordre de convergence peu fiable. Une sequence structuree ou
transfinie, chaque niveau etant le raffinement du precedent, est necessaire.

### 3. Reference poutre et effet 3D local

La formule Timoshenko est une reference analytique pertinente pour la fleche
globale d'une poutre elancee. Elle n'est pas une solution 3D exacte autour de
l'encastrement et de la repartition de charge. Pour fermer un gate `< 1 %`,
il faut donc comparer simultanement :

1. QF_solver TET4 et Code_Aster `TETRA4` sur le meme maillage ;
2. QF_solver TET4 et une reference 3D convergee d'ordre eleve, par exemple
   Code_Aster `TETRA10` ou QF_solver TET10 sur un maillage suffisamment fin ;
3. les deux a la reference de poutre, hors zone de perturbation locale.

## Probe 3D TET10 sur le meme maillage

Avec la decomposition centree et la charge `surface_consistent`, le niveau
fin de `24 576` TET4 compare a son TET10 conforme donne `11,009264 %` d'ecart
TET4/TET10, tandis que le TET10 est a `0,789652 %` de la poutre. La reference
TET10 est donc sous 1 % dans ce probe, alors que l'erreur TET4 reste
dominante. Cette preuve isole l'erreur d'interpolation du TET4 sur une
connectivite et un chargement identiques ; elle ne remplace pas Code_Aster
`TETRA10`.

Les artefacts sont archives sous
`qualification/vnv/tet4_tet10_corrected_reference_002/`.

## Correlation 3D externe TETRA10

Une correlation Code_Aster `TETRA10` a ensuite ete executee sur le niveau
intermediaire de `3 072` TET4 et `4 721` noeuds TET10, avec connectivite,
coordonnees, blocages et charges identiques. QF_solver TET10 et Code_Aster
TETRA10 donnent un ecart relatif de `3.87208e-09 %`. Sur ce meme niveau, le
TET4 QF_solver reste a `32.296413 %` de la reponse TETRA10. Cette comparaison
confirme la hierarchie de reference : le TET10 interne est coherent avec
Code_Aster, tandis que le TET4 reste l'approximation limitante.

Les artefacts sont archives sous
`qualification/vnv/external/code_aster_tet10_static_reference_001/`.
Cette preuve ne transforme pas le TET4 en element stable ; elle rend le
blocage mecanique explicite et reproductible.

## Faisabilite du seuil de 1 %

Le niveau 80 mesure `0,818328 %`, apres `1,507279 %` a `1,572` million et
`1,217644 %` a `3,072` millions. Le seuil de `1 %` est donc demontre pour le
sous-cas structure centre, avec la reference poutre et le chargement de face
documentes. Cette valeur ne devient pas une limite universelle du TET4.

Cette taille est accessible au chemin PETSc/MPI du projet, mais elle est peu
adaptee au solveur direct ou aux listes Python du chemin standard. Le resultat
La preuve est archivee apres execution, controle du residu, manifeste Docker
et correlation de meme ordre. Les effets 3D locaux justifient de conserver la
reference TET10/TETRA10 comme diagnostic, sans en faire une condition de
promotion du sous-cas deja couvert.

## Preuve grand modele PETSc/GAMG

Une campagne PETSc a ete executee sur le porte-a-faux TET4 structure, avec
`CG + GAMG`, assemblage PETSc et sortie fichier des deplacements. Le motif
centre et la charge de face coherente sont utilises. Les valeurs suivantes
comparent le deplacement de pointe a la reference de poutre de Timoshenko :

| Elements TET4 | DDL | Deplacement UZ pointe (m) | Ecart poutre | Iterations GAMG | Residu final |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 24 576 | 8 019 | -1.271095218e-7 | 11.711981 % | 161 | 2.00e-17 |
| 196 608 | 56 355 | -1.385127036e-7 | 3.791534 % | 193 | 3.40e-17 |
| 1 572 864 | 814 659 | -1.418013773e-7 | **1.507279 %** | 212 | 6.47e-17 |
| 24 576 000 | 12 462 243 | -1.427932701e-7 | **0.818328 %** | 252 | 2.09e-16 |

Le dernier niveau mesure passe le seuil de `1 %`. C'est une preuve du
sous-cas de flexion structuree, pas une promotion automatique du TET4 statique
general : le calcul a ete fait sur un seul rang MPI et utilise la reference
poutre. La correlation TET4/TETRA4 sur maillage identique est PASS ; TET10/
TETRA10 reste une comparaison d'ordre utile, mais non bloquante pour ce
sous-cas.

La campagne reproductible finale est archivee dans
`qualification/vnv/tet4_structured_petsc_refined_004_docker/`; son manifeste
conserve l'image PETSc/GAMG, le digest et les empreintes. Les anciennes valeurs
restent visibles comme historique mais ne remplacent pas cette preuve finale.

## Decision sur la formulation

La formulation TET4 ne doit pas etre modifiee sur la base de cet ecart. Les
tests de patch, les modes rigides, la symetrie et la correlation meme-maillage
ne signalent pas d'anomalie d'implementation. Modifier la quadrature ou
assouplir artificiellement la rigidite masquerait potentiellement une erreur
au lieu de la traiter.

Pour les modeles domines par la flexion, le choix conseille reste TET10. TET4
reste approprie lorsque la precision recherchee est compatible avec son ordre
d'interpolation ou lorsque le maillage peut etre suffisamment raffine.

## Suite avant une promotion stable

1. Faire statuer l'Owner sur le sous-scope documente ; le gate technique est
   `PASS` et le statut de promotion est `READY_FOR_OWNER_REVIEW`.
2. Conserver la limite d'usage : TET4 isotrope lineaire, statique, geometrie
   structuree de type porte-a-faux et chargement terminal documente.
3. Ajouter plus tard une seconde geometrie et une seconde famille de charges
   avant toute extension vers un TET4 statique general.
4. Ne pas modifier le noyau TET4, la quadrature ou la tolerance lineaire sur la
   base de cet ecart ; le probleme etait spatial, pas temporel.

## References

- [Gmsh reference manual](https://gmsh.info/doc/texinfo/gmsh.html) : maillage
  transfinite et extrusion pour des sequences structurees reproductibles.
- [Code_Aster R3.01.01](https://code-aster.org/doc/v12/en/man_r/r3/r3.01.01.pdf)
  : familles d'elements mecaniques et conventions de discretisation.
- [Felippa, 1992](https://doi.org/10.1016/0045-7949(92)90407-Q) : rigidites
  fermees pour tetraedres a deformation lineaire et quadratique.
- [Wang et al., 2017](https://doi.org/10.1017/jmech.2016.113) : raideur
  artificielle des tetraedres lineaires et techniques d'amelioration.

## Reproductibilite

```powershell
python .\scripts\run_code_aster_tet4_static_vnv.py `
  --output .\tmp\tet4_static_code_aster_corrected
```

Les artefacts de correlation meme-maillage sont sous
`qualification/vnv/external/code_aster_tet4_static/reference/`.

La campagne structuree executablee et son contrat sont detailles dans
[`tet4_structured_convergence_campaign.md`](tet4_structured_convergence_campaign.md).
