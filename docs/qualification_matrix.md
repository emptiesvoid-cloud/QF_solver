---
doc_id: DOC-QUAL-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Matrice de qualification du solveur EF

Ce document organise la qualification du solveur en exigences tracables. Il ne
declare pas le code certifie; il definit les preuves minimales pour le rendre
qualifiable et verifiable.

Le registre autoritatif et exploitable par la machine est
`qualification/requirements.json`. Ce Markdown est une vue de lecture et ne
doit pas etre modifie sans mise a jour correspondante du registre. La commande
`qualification-readiness` bloque un scope candidat si une exigence est
orpheline ou pointe vers une preuve absente.

Les formules critiques sont reliees separement dans
`qualification/formulas.json`. La vue generee est disponible dans la page
[Revue documentaire et formules](verification/formules.md).

## Niveaux de maturite

| Niveau | Signification | Utilisation |
| --- | --- | --- |
| `stable` | Fonction protegee par tests, audit et exemple officiel. | Autorise en profil `qualification`. |
| `stable_after_reinforced_tests` | Fonction utilisable mais demandant des benchmarks supplementaires. | Autorise jusqu'au profil `strict`. |
| `experimental` | Fonction utile mais preuve mecanique incomplete. | Bloquee en profil `qualification`. |
| `research` | Prototype ou comportement non qualifie. | Revue expert obligatoire. |

## Profils de verification

| Profil | Usage | Politique |
| --- | --- | --- |
| `quick` | Developpement local rapide. | Compile et smoke checks. |
| `engineering` | Usage courant recommande. | Tests, compilation et verifications rapides. |
| `strict` | Revue technique. | Les warnings deviennent bloquants. |
| `qualification` | Candidat livraison qualifiable. | Preuves completes et fonctions experimentales refusees. |

## Exigences et preuves

| ID | Exigence | Preuve attendue | Statut |
| --- | --- | --- | --- |
| REQ-IO-001 | Le format JSON v1 est strict, versionne et documente. | `docs/schema_json.md`, tests JSON, exemples officiels. | stable |
| REQ-IO-002 | Les unites sont explicites dans l'audit. | `units` JSON, audit Markdown, evidence bundle. | stable |
| REQ-MESH-001 | Le maillage invalide bloque la resolution. | Tests element inverse, connectivite, materiau inconnu. | stable |
| REQ-MESH-002 | La qualite faible produit un warning tracable. | `docs/qualite_maillage.md`, details `element_quality`. | stable |
| REQ-SOL-001 | La statique lineaire TET4 conserve l'equilibre. | Traction/compression signees, residu libre, resultante des reactions, bilan des moments et energie interne/externe. | stable |
| REQ-SOL-002 | MITC4 reste protege par benchmarks existants. | `verify --quick`, tests verification MITC4. | stable |
| REQ-SOL-005 | MITC4 ne se verrouille pas dans le domaine mince borne. | Matrice 160 cas, Timoshenko, energie shear, Q4 temoin et correlation Abaqus S4R partielle. | candidate |
| REQ-SOL-003 | TET10 conserve masse, patch affine et champ quadratique. | Jacobien/quadrature, convergence h, masse/modal/charges, CalculiX C3D10 et quasi-incompressibilite. | stable_after_reinforced_tests |
| REQ-SOL-004 | La convergence h TET4 est quantitative sur un domaine declare. | Six maillages Gmsh en flexion, huit en torsion et cinq en traction/compression, ordres observes, monotonie, erreurs fines et residus. | stable_after_reinforced_tests |
| REQ-LOAD-001 | Les charges reparties conservent resultante et premier moment. | Pression et force volumique canoniques, tests analytiques TET4/TET10/MITC4, audit charge-reactions et bilan force/moment. | stable_after_reinforced_tests |
| REQ-MOD-001 | Le modal donne residus et orthogonalites auditables. | Audit modal, `eigsh` par defaut, garde dense et tests unitaires. | stable_after_reinforced_tests |
| REQ-MOD-002 | MITC4 fournit une masse coherente sans inertie fictive de drilling. | Masse analytique, objectivite, condensation et modes propres. | development |
| REQ-DYN-001 | Newmark expose historique, residu et energie. | Tests energie, LU sparse reutilisee, chargement tabule et exemple 1 ddl analytique. | stable_after_reinforced_tests |
| REQ-DYN-002 | Une reprise Newmark refuse tout etat incompatible. | Round-trip NPZ, corruption, reprise intermediaire et comparaison au calcul continu. | stable_after_reinforced_tests |
| REQ-DYN-003 | Newmark MITC4 opere sur le systeme physique condense. | Energie libre, amortissement massique, residu et reconstruction. | development |
| REQ-HAR-001 | Harmonique direct expose amplitude, phase, pic et contraintes complexes MITC4. | Test 0 Hz vs statique, exemple 1 ddl analytique, reponse modale MITC4, complement de Schur Rayleigh, large bande et correlation `S11` Navier/NAFEMS/Abaqus. | stable_after_reinforced_tests |
| REQ-NL-001 | Le non-lineaire declare sa maturite experimentale. | Audit, solver settings, qualification summary. | experimental |
| REQ-AUD-001 | Chaque resultat contient un audit boite blanche. | `audit`, `checks`, `qualification_summary`. | stable |
| REQ-EVD-001 | Un dossier de preuve reproductible est exportable et verifiable. | CLI/API `evidence`, `verify-evidence`, fichiers JSON/MD/CSV/VTU, manifeste SHA-256. | stable |
| REQ-CMP-001 | La campagne souveraine applique des criteres numeriques executables. | `qualification/campaign.json`, commande `qualify`, tests campagne. | stable |
| REQ-CMP-002 | La campagne distingue les cas suivis des cas candidats remplacement. | Champs `replacement_candidate`, `replacement_ready`, tests readiness. | stable |
| REQ-CMP-003 | La campagne compare les grandeurs cles a des references explicites. | Operateurs `abs_error`, `relative_error`, champs `reference_type`, formules fermees. | stable |
| REQ-CMP-004 | Un cas candidat remplacement exige une reference independante. | Readiness bloque les cas avec seule non-regression. | stable |
| REQ-LRG-001 | Le solveur dispose d'un chemin grand modele separe pour TET4 statique lineaire. | `convert-model`, `inspect-large`, `solve-large`, `generate-large-tet4-block`, `large-readiness`, `benchmark-large`, `qualify-large`, tests HDF5/NPZ et comparaison solveur standard. | experimental |
| REQ-LRG-002 | Un benchmark grand modele produit des preuves reproductibles sans deplacements en JSON monolithique. | `input_fingerprint.json`, `benchmark_large.json`, `benchmark_large.md`, `displacements.h5/npz`, `evidence_manifest.json`, `verify-evidence`. | experimental |
| REQ-LRG-003 | Le jalon 1M ddl dispose d'un pipeline executable de qualification. | `qualify-large --target-dofs 1000000`, test manuel `QF_SOLVER_RUN_LARGE_1M=1`, manifest racine et manifest benchmark. | experimental |
| REQ-LRG-004 | Les runs 1M refusent les backends ou machines non prets avant assemblage. | `large_readiness.json`, garde-fou SciPy > 200000 ddl, tests dependances PETSc manquantes. | experimental |
| REQ-LRG-005 | Un dossier 1M resolu est verifiable apres coup sans relancer le calcul. | `verify-large`, controle manifests, DDL cible, displacements HDF5/NPZ, residu solveur et absence JSON monolithique. | experimental |
| REQ-LRG-006 | Un backend sans assemblage global existe pour qualifier les blocs structures generes. | Backend `matrix_free`, comparaison tests avec SciPy, sortie HDF5 et `verify-large`. | experimental |
| REQ-LRG-007 | Un run grand modele trace l'environnement numerique qui a produit les resultats. | `runtime_environment.json`, roles manifeste, `verify-large`, tests API/benchmark/qualification. | experimental |
| REQ-REL-001 | Une release suit une checklist qualite. | `CHANGELOG.md`, `docs/controle_qualite.md`. | stable |

## Checklist release qualifiable

- `python -m ruff check solveur mitc4 scripts tests`
- `python -m pytest`
- `python -m compileall -q solveur mitc4 scripts tests qf_solver.py main_solveur.py mitc4_solver.py`
- `python .\qf_solver.py verify --quick`
- `python .\mitc4_solver.py verify --quick`
- `python .\qf_solver.py verify-all --profile engineering`
- `python .\qf_solver.py benchmarks`
- `python -m pytest -m benchmark`
- `python .\qf_solver.py qualify --manifest .\qualification\campaign.json --output .\results\qualification_campaign`
- Les exemples officiels produisent un dossier `evidence`.
- Les limites connues sont a jour dans `README.md` et `prochaines_etapes.md`.
- Aucun fichier Python principal ne depasse 700 lignes.
