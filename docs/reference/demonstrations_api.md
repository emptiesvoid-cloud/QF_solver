---
doc_id: DOC-REF-DEMO-001
revision: 0.4
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Demonstrations et API de reproductibilite

Cette page definit le contrat documentaire des demonstrations QF_solver.
Le catalogue contient vingt-huit demonstrations : onze benchmarks mailles,
dix cas de qualification cibles, six modeles JSON officiels et un plan grand
modele. Les extensions aux variantes de methode restent une etape de feuille
de route; elles ne doivent pas etre confondues avec une qualification.

## Une entree de demonstration

Le registre `qualification/demonstrations.json` contient une entree par cas
reproductible. Chaque entree relie au minimum :

| Champ | Role |
| --- | --- |
| `demo_id` | Identifiant stable et lisible |
| `family` / `method` | Element fini et methode de resolution |
| `maturity` | `stable`, `stable_after_reinforced_tests`, `experimental` ou `research` |
| `model` | Exemple JSON/HDF5 ou `generated:BM-*` pour un maillage et un setup construits deterministiquement par le benchmark |
| `runner` | Fonction ou commande publique qui regenere le cas |
| `execution` | `benchmark` pour un benchmark maille, `qualification_case` pour un cas V&V controle, `model` pour un exemple JSON ou `large_plan` pour un plan d'infrastructure |
| `case_id` | Identifiant du cas V&V lorsque `execution` vaut `qualification_case` |
| `documentation` | Page Markdown de formulation et de resultats |
| `requirements` / `tests` | Tracabilite vers exigences et tests |
| `references` | Identifiants `REF-*` et URL/DOI de la bibliographie |
| `outputs` | JSON, rapport, PNG, VTU et manifeste attendus |
| `limitations` | Conditions d'emploi et exclusions explicites |

## Acces depuis la librairie

L'API publique disponible est :

```python
from solveur.api import list_demonstrations, run_demonstration, run_qualification_case

catalog = list_demonstrations(family="MITC4", method="linear_static")
run = run_demonstration(
    catalog[0].demo_id,
    output_dir="results/demo",
    profile="engineering",
)

# Le profil du manifeste reste fige : cette execution produit une preuve V&V.
case = run_qualification_case("SOV-TET4-STATIC-001", "results/tet4_static")
```

Une entree `benchmark` transmet le profil choisi au runner de benchmark. Une
entree `qualification_case` execute le cas avec le profil et les criteres
figes dans `qualification/campaign.json`; l'argument `profile` de
`run_demonstration()` ne remplace donc jamais le contrat V&V.
Une entree `model` execute un exemple JSON officiel avec le profil demande,
puis produit `results.json`, `audit.md`, le rapport maillage et un manifeste
d'evidence v2. Elle est reservee aux capacites possedant deja une page et des
tests V&V, mais qui ne constituent pas un benchmark Gmsh.
La demonstration grand modele ne construit pas le modele : elle expose un plan
1M DDL et les prerequis PETSc/MPI. Les autres configurations grand modele
seront ajoutees apres leur campagne de verification; une absence du catalogue signifie donc
"non enregistre", pas "non implemente" ni "qualifie".

Le descripteur contient les references, la maturite, les tests, les limites et
les sorties attendues. L'execution retourne le resultat du runner controle avec
son verdict et ses chemins d'artefacts. Le code ne chargera aucune page
web pour executer une demonstration. Les solveurs externes seront optionnels,
versionnes et signales comme tels dans le manifeste.

Avant publication, la CI appelle `DemonstrationCatalog.validate_integrity()`.
Ce controle ne lance pas les calculs: il refuse une demonstration dont le
benchmark ou cas V&V, le modele d'entree ou generateur, la page, le runner, un
test, une exigence, une reference ou les sorties minimales sont absents. Les
benchmarks exigent `benchmark_summary.json` et `benchmark_manifest.json`; les
cas V&V exigent `qualification_case_summary.json` et `evidence_manifest.json`.
Les modeles JSON exigent `demonstration_summary.json`, `results.json` et
`evidence_manifest.json`.
Le plan grand modele exige `large_campaign.json`, `large_campaign.md` et
`evidence_manifest.json`; son verdict `PLANNED` ou `BLOCKED` n'est jamais un
resultat de resolution.
Le controle est
volontairement separe de `list_demonstrations()` afin qu'une installation de la
bibliotheque reste utilisable sans site MkDocs installe.

`list_benchmarks()` et `run_benchmark()` restent les interfaces compatibles du
catalogue de onze benchmarks mailles existant. Le futur registre transverse
pourra les inclure sans changer leur contrat.

## Contenu obligatoire d'une page

Chaque page devra expliquer la geometrie et la numerotation, les DDL, le repere
local, l'interpolation, le Jacobien, la quadrature, les matrices, les charges,
les blocages et le post-traitement. Pour une methode, elle devra ajouter
l'equation resolue, les hypotheses matricielles, l'algorithme, le critere
d'arret, les residus, la complexite et les modes d'echec.

La page affichera ensuite le modele, le maillage, les blocages, le chargement,
la deformee, un tableau de resultats, la convergence, les invariants, la
maturite et les limites. Les valeurs seront generees par l'API et associees a
un manifeste d'empreintes; elles ne seront pas saisies a la main.

## Bibliographie et tracabilite

Les formulations renverront aux entrees `REF-*` de
`docs/reference/references.md`. Une entree bibliographique devra donner les
auteurs, le titre, la revue ou l'editeur, l'annee et un DOI ou une URL stable.
Chaque demonstration reliera ensuite cette reference a la formulation, au
code, aux tests et aux artefacts de sortie.

Une page ou un cas sans reference, test, runner ou limite ne pourra pas etre
publie comme demonstration complete. Une demonstration complete reste une
preuve de reproductibilite et de verification; elle ne remplace pas une revue
mecanique humaine ni une qualification externe.
