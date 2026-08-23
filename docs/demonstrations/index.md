---
doc_id: DOC-DEMO-000
revision: 0.3
status: genere et controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Catalogue des demonstrations executables

Une demonstration documentaire n'est acceptee que si elle possede:

- un modele d'entree versionne ou genere de facon deterministe;
- une grandeur d'interet definie avant le calcul;
- une reference analytique, un invariant ou un benchmark identifie;
- une tolerance explicite;
- un verdict et une empreinte SHA-256;
- une figure produite a partir du resultat du meme run.

--8<-- "docs/generated/demo_catalog.md"

## Registre public de la librairie

La table suivante est generee depuis `qualification/demonstrations.json`. Elle
est le contrat de recherche de l'API `list_demonstrations()` et d'execution
`run_demonstration()`.

--8<-- "docs/generated/demonstration_registry.md"

## Modeles JSON documentes

Six exemples mecaniques, distincts des benchmarks Gmsh, sont executes par la
meme API publique et produisent un dossier de preuve v2 :

- TET4 orthotrope oriente : [formulation solide](../composites/solides_orthotropes.md) ;
- TET10 orthotrope en transitoire Newmark : [domaine et limites](../composites/solides_orthotropes.md) ;
- MITC4 multicouche `[0/90]s` : [formulation stratifiee](../composites/mitc4_multicouche.md).
- MITC4 modal a masse coherente : [modes propres](dynamique.md) ;
- MITC4 transitoire Newmark : [reponse temporelle](dynamique.md) ;
- MITC4 harmonique direct : [amplitude et phase](avancees.md).

```python
from qf_solver import run_demonstration

run_demonstration(
    "DEMO-MITC4-LAMINATE-STATIC-001",
    output_dir="results/mitc4_laminate",
    profile="engineering",
)
```

Les trois cas composites restent `experimental`. Les trois cas dynamiques
MITC4 sont bornes par leur masse coherente, les petits deplacements et les
limites publiees dans les revues associees. Chaque rapport de verification et
chaque limite d'emploi fait partie du resultat.

## Plan grand modele

La demonstration `DEMO-LARGE-PETSC-PLAN-001` evalue un bloc TET4 cible a un
million de DDL sans le construire ni le resoudre. Elle publie les dimensions,
les estimations memoire, l'espace disque et la disponibilite HDF5/MPI/PETSc.
Une execution reste une campagne controlee sur infrastructure identifiee.

```python
from qf_solver import run_demonstration

plan = run_demonstration("DEMO-LARGE-PETSC-PLAN-001", "results/large_plan")
```

Voir aussi [la methode grand modele](grand_modele.md) pour les limites de
partitionnement, les sorties distribuees et les campagnes 1M/3M DDL.

## Ce qu'une demonstration prouve

Un patch test prouve la reproduction d'un champ polynomial donne. Un benchmark
prouve une correlation pour une geometrie et des parametres donnes. Une etude
de convergence montre une tendance sous raffinement. Aucun de ces objets ne
prouve seul la validite universelle d'un element.

Les temps de calcul sont reportes a titre informatif. Ils ne participent pas
aux verdicts mecaniques, car ils dependent de la machine et de la bibliotheque
BLAS.

## Campagne de structures maillees

Le registre `qualification/benchmarks.json` definit onze cas controles, dont
un cas BEAM2 cree sans Gmsh :

- [porte-a-faux BEAM2 statique et modal](benchmarks/beam2_cantilever.md);
- [patch TET4 3D](benchmarks/tet4_patch.md);
- [panneau mince TET4 en traction membranaire](benchmarks/tet4_membrane.md);
- [arbre circulaire TET4 en torsion](benchmarks/tet4_torsion.md);
- [poutre TET4/TET10](benchmarks/cantilever.md);
- [quart de cylindre de Lame TET10](benchmarks/tet10_lame.md);
- [membrane de Cook](benchmarks/cook.md);
- [toiture de Scordelis-Lo](benchmarks/scordelis.md);
- [cylindre pince](benchmarks/pinched.md);
- [porte-a-faux modal, Newmark et harmonique](benchmarks/dynamic_cantilever.md);
- [barre elastoplastique J2](benchmarks/j2_bar.md).

La generation des artefacts documentaires relance les onze cas. Un critere stable en echec
interrompt la publication. Les cas experimentaux doivent terminer avec des
criteres `PASS` mais conservent un verdict global `WARNING`.

Les cas V&V unitaires et analytiques sont egalement exposes par le registre
`qualification/demonstrations.json` et l'API `run_qualification_case()`. Ils
completent les benchmarks mailles par des preuves ciblees de statique TET4,
MITC4, TET10, modal, Newmark, harmonique et J2; ils ne remplacent pas une
campagne de convergence maillée.
