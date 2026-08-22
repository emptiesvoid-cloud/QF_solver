---
doc_id: DOC-LEGACY-ANALYSIS-001
revision: 0.1
status: draft
applicable_version: 0.2.1-alpha
reviewer: ""
approver: ""
---

# Analyse du solveur EF MITC4 + tetra 3D

## Objectif

Le projet fournit maintenant un socle de solveur elements finis lineaire
statique utilisable en ligne de commande et comme librairie Python.

La base actuelle couvre:

- coques MITC4 via l'implementation existante et verifiee;
- solides 3D TET4 et TET10 avec elasticite lineaire isotrope;
- validation obligatoire du modele et du maillage avant resolution;
- analyse statique lineaire avec choix de methode lineaire;
- analyse modale TET4 avec masse coherente;
- analyse modale TET4 et TET10;
- analyse dynamique transitoire lineaire TET4/TET10 avec schema de Newmark;
  historique temporel, energies, chargement tabule et export CSV dedie;
- reponse harmonique frequentielle lineaire TET4/TET10 avec amplitudes,
  phases et export CSV dedie;
- contraintes/deformations TET4/TET10 avec von Mises, invariants et valeurs
  principales en post-traitement;
- resultantes MITC4 au centre: membrane, flexion et cisaillement transverse;
- contraintes locales MITC4 estimees aux faces superieure et inferieure;
- analyse statique non-lineaire TET4/TET10 en petits deplacements avec Newton et
  loi elastique non-lineaire cubique;
- loi elastoplastique Von Mises 3D simple avec retour radial et etat interne
  chemin-dependant stocke par point d'integration;
- audit boite blanche des matrices, vecteurs, ddl, connectivites et conditions
  aux limites;
- audit local par element: geometrie, materiau, ddl globaux, matrice locale,
  rang estime et valeurs propres extremes des matrices symetriques;
- audit de post-traitement par element: ddl globaux, deplacement de calcul
  local, deformations, contraintes, von Mises ou resultantes MITC4;
- estimation spectrale et conditionnement des petites matrices globales et
  matrices reduites;
- audit d'equilibre statique: residu libre, reactions, travail externe et
  energie interne secante;
- controles automatiques audites avec verdicts `PASS`, `WARNING`, `FAIL`;
- historique de convergence `solver.residual_history` pour les solveurs
  lineaires;
- entree JSON et sortie JSON documentees dans `docs/schema_json.md`;
- validation stricte du schema JSON avant construction du modele;
- guide court de creation de cas dans `docs/creer_cas.md`;
- configuration `ruff` et commandes de controle dans
  `docs/controle_qualite.md`;
- exports CSV et VTU pour les resultats statiques, avec grandeurs solides
  principales, points d'integration, resultats nodaux et invariants quand
  disponibles;
- rapport JSON detaille de `check-mesh`, avec composantes connectees,
  noeuds isoles, qualite elementaire, estimation de rang mecanique et
  contraintes par composante;
- seuils qualite maillage centralises et documentes dans
  `docs/qualite_maillage.md`;
- conventions de post-traitement documentees dans
  `docs/conventions_resultats.md`;
- exemples JSON officiels verifies via API et CLI;
- snapshots JSON/CSV de non-regression sur les exemples officiels;
- verification automatique de la limite de 700 lignes par fichier Python;
- packaging `pyproject.toml` avec installation editable, dependance dev `ruff`
  et script `qf-solver`;
- options CLI `--version` pour le solveur general et le lanceur MITC4;
- API publique stable dans `solveur.api`.

La continuation arc-length est disponible pour les chargements proportionnels
sur les modeles TET4 non-lineaires actuellement supportes.

TET10 est implemente pour les analyses statiques lineaires, modales,
dynamiques transitoires et non-lineaires en petits deplacements.

## Architecture

Le nouveau paquet `solveur/` est organise par responsabilite:

```text
solveur/
  api/              API publique load/check/solve/save
  cli/              commandes terminal sans logique metier
  core/             modele, ddl, assemblage, solveur, resultats
  elements/         elements shell et solid separes
  io/               lecture/ecriture JSON
  materials/        materiaux coque et solide
  mesh/             validation et qualite de maillage
  post/             contraintes, deformations, audits et resultats derives
  verification/     points d'entree de verification
examples/           modeles JSON officiels testes
```

Le paquet historique `mitc4/` reste conserve pour ne pas casser les
verifications mecaniques deja validees.

## Interfaces

CLI:

```powershell
qf-solver check-mesh --input model.json --json-report mesh_report.json
qf-solver inspect --input model.json --markdown audit.md
qf-solver solve --input model.json --output results.json --audit-md audit_resolution.md --csv-dir csv_results --vtu result.vtu --audit-gate fail
qf-solver methods
qf-solver --version
python .\qf_solver.py check-mesh --input model.json --json-report mesh_report.json
python .\qf_solver.py inspect --input model.json --output audit.json
python .\qf_solver.py inspect --input model.json --markdown audit.md
python .\qf_solver.py inspect --input model.json --audit-gate warning
python .\qf_solver.py inspect --input model.json --output audit_values.json --detail values
python .\qf_solver.py solve --input model.json --output results.json
python .\qf_solver.py solve --input model.json --output results.json --audit-md audit_resolution.md
python .\qf_solver.py solve --input model.json --output results.json --csv-dir csv_results --vtu result.vtu
python .\qf_solver.py solve --input model.json --output results.json --audit-gate fail
python .\qf_solver.py solve --input model.json --output results.json --method cg
python .\qf_solver.py methods
python .\qf_solver.py --version
python .\qf_solver.py verify --quick
```

API Python:

```python
from solveur.api import load_model, check_mesh, inspect_model, solve_model, save_result, save_audit_markdown, save_result_csv, save_result_vtu, list_methods

model = load_model("model.json")
report = check_mesh(model)
audit = inspect_model(model)
detailed_audit = inspect_model(model, detail="values")
save_audit_markdown(audit, "audit_inspection.md")
result = solve_model(model)
save_result(result, "results.json")
save_audit_markdown(result, "audit_resolution.md")
save_result_csv(result, "csv_results", model)
save_result_vtu(result, model, "result.vtu")
print(list_methods())
```

## Analyses et methodes

Les methodes sont choisies dans le JSON via `analysis` ou surchargees depuis
la CLI avec `--method`.

Analyses disponibles:

- `linear_static`: statique lineaire assemblee sous forme `K u = f`.
- `modal`: probleme generalise `K phi = lambda M phi`, actuellement pour TET4/TET10.
- `nonlinear_static`: resolution incrementale avec force interne, tangente et
  convergence sur le residu, actuellement pour TET4/TET10.

Methodes lineaires:

- `direct` / `spsolve`: resolution sparse directe de type LU.
- `cg` / `conjugate_gradient`: gradient conjugue pour systemes symetriques
  definis positifs.
- `gmres`: methode de Krylov pour systemes generaux.
- `bicgstab`: methode de Krylov pour systemes non symetriques.
- `minres`: methode Krylov pour systemes symetriques indefinis.

Parametre optionnel:

- `preconditioner: "jacobi"` pour les methodes iteratives supportees.
- `preconditioner: "ilu"` pour factorisation LU incomplete sparse.

Methodes modales:

- `eigh`: resolution dense robuste pour petits modeles et verification.
- `eigsh` / `lanczos`: extraction sparse des premiers modes.

Methodes dynamiques:

- `newmark`: integration implicite Newmark en dynamique lineaire;
- `newmark_average_acceleration`: alias explicite du schema moyen
  inconditionnellement stable pour les cas lineaires usuels.

Methodes non-lineaires:

- `newton_raphson`: tangente reassemblee a chaque iteration;
- `modified_newton`: tangente figee pendant un pas de charge;
- `newton_line_search`: Newton-Raphson avec recherche lineaire par
  backtracking sur la norme du residu;
- `arc_length`: continuation arc-length avec inconnues couplees
  deplacement/facteur de charge.

Le non-lineaire accepte aussi un controle de pas de charge adaptatif:

- `adaptive_load_steps: true`;
- `initial_load_increment`, `min_load_increment`, `max_load_increment`;
- `cutback_factor` et `growth_factor`;
- seuils `grow_below_iterations` et `shrink_above_iterations`.

Parametres arc-length disponibles:

- `target_load_factor`;
- `arc_length_radius`;
- `arc_length_load_scale`;
- `max_arc_steps`;
- `min_arc_length_radius`.

Ces noms sont exposes par:

```powershell
python .\qf_solver.py methods
```

## Format JSON v1

Le schema complet d'entree/sortie est maintenu dans `docs/schema_json.md`.
L'exemple minimal ci-dessous reste volontairement court.

Le lecteur JSON refuse les champs structurants invalides avant la construction
du modele: racine non objet, champs requis manquants, connectivites de mauvaise
taille, indices hors bornes, materiaux inconnus, valeurs non numeriques,
analyses/methodes incompatibles et ddl inconnus.

```json
{
  "analysis": {"type": "linear_static", "method": "direct"},
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [
    {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}
  ],
  "materials": {
    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]}
  ],
  "loads": [
    {"node": 1, "dof": "UX", "value": 1000.0}
  ]
}
```

Exemple lineaire iteratif preconditionne:

```json
{
  "analysis": {
    "type": "linear_static",
    "method": "bicgstab",
    "preconditioner": "ilu",
    "rtol": 1.0e-10
  },
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [
    {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}
  ],
  "materials": {
    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3}
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]}
  ],
  "loads": [
    {"node": 1, "dof": "UX", "value": 1000.0}
  ]
}
```

Exemple modal:

```json
{
  "analysis": {"type": "modal", "method": "eigh", "modes": 3},
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [
    {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}
  ],
  "materials": {
    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]}
  ]
}
```

Exemple TET10 lineaire:

```json
{
  "analysis": "linear_static",
  "nodes": [
    [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
    [0.5, 0, 0], [0.5, 0.5, 0], [0, 0.5, 0],
    [0, 0, 0.5], [0.5, 0, 0.5], [0, 0.5, 0.5]
  ],
  "elements": [
    {"type": "TET10", "nodes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "material": "steel"}
  ],
  "materials": {
    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]},
    {"node": 6, "dofs": ["UX", "UY", "UZ"]},
    {"node": 7, "dofs": ["UX", "UY", "UZ"]},
    {"node": 9, "dofs": ["UX", "UY", "UZ"]}
  ],
  "loads": [
    {"node": 1, "dof": "UX", "value": 1000.0}
  ]
}
```

Exemple non-lineaire TET4:

```json
{
  "analysis": {
    "type": "nonlinear_static",
    "method": "newton_raphson",
    "load_steps": 5,
    "max_iterations": 50,
    "tolerance": 1.0e-9,
    "adaptive_load_steps": true,
    "initial_load_increment": 1.0,
    "min_load_increment": 0.05,
    "cutback_factor": 0.5,
    "growth_factor": 1.5
  },
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [
    {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}
  ],
  "materials": {
    "rubber": {
      "type": "nonlinear_isotropic_3d",
      "E": 1000.0,
      "nu": 0.25,
      "hardening": 1000000.0
    }
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]}
  ],
  "loads": [
    {"node": 1, "dof": "UX", "value": 10.0}
  ]
}
```

Exemple continuation arc-length:

```json
{
  "analysis": {
    "type": "nonlinear_static",
    "method": "arc_length",
    "load_steps": 5,
    "max_arc_steps": 12,
    "max_iterations": 50,
    "tolerance": 1.0e-9,
    "target_load_factor": 1.0
  },
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [
    {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}
  ],
  "materials": {
    "rubber": {
      "type": "nonlinear_isotropic_3d",
      "E": 1000.0,
      "nu": 0.25,
      "hardening": 1000000.0
    }
  },
  "fixed_dofs": [
    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
    {"node": 3, "dofs": ["UX", "UY", "UZ"]}
  ],
  "loads": [
    {"node": 1, "dof": "UX", "value": 10.0}
  ]
}
```

## Verification maillage

La validation controle:

- presence des noeuds et elements;
- coordonnees finies;
- absence de noeuds dupliques exacts;
- connectivites completes;
- indices de noeuds valides;
- absence de noeuds repetes dans un element;
- existence et compatibilite des materiaux;
- compatibilite des ddl de charges et blocages;
- geometrie MITC4 via jacobien positif;
- geometrie TET4 via volume signe positif;
- qualite TET4/TET10: longueurs d'aretes, aspect ratio, volume relatif et skew;
- qualite MITC4: ratio d'aretes, planarity et angles internes.
- estimation de rang mecanique sur petits modeles pour signaler des modes
  rigides probables.
- densite positive obligatoire en analyse modale et dynamique TET4/TET10.
- non-lineaire statique actuellement disponible pour TET4/TET10.
- composantes connectees du maillage;
- noeuds isoles non references par les elements;
- contraintes et charges par composante pour signaler les risques de modes
  rigides.

Le rapport retourne `PASS`, `WARNING` ou `FAIL`. La CLI peut ecrire un rapport
JSON detaille avec `check-mesh --json-report mesh_report.json`.

## Audit boite blanche

Le solveur ecrit une section `audit` dans les sorties de resolution et fournit
la commande:

```powershell
python .\qf_solver.py inspect --input model.json --output audit.json
python .\qf_solver.py inspect --input model.json --markdown audit.md
```

Cette trace documente:

- numerotation globale des ddl;
- ddl fixes et libres;
- `mesh_details`: composantes connectees, noeuds isoles, types d'elements,
  qualite elementaire, rang mecanique estime, ddl fixes et charges par
  composante;
- types d'elements et materiaux references;
- connectivites elementaires et indices de ddl globaux;
- vecteurs assembles, dont le chargement;
- matrices globales et reduites avec `shape`, `nnz`, densite, norme et erreur
  relative de symetrie, plus conditionnement estime et positivite quand
  l'estimation spectrale est disponible;
- audits locaux par element dans `element_audits`, avec qualite geometrique,
  donnees materiau, matrices locales, rang estime et valeurs propres extremes;
- bilan `equilibrium` apres resolution statique: convention de signe, facteur
  de charge, norme du residu libre, reactions, travail externe et energie;
- controles `checks`: validation maillage, ddl fixes/libres, symetrie des
  matrices, conditionnement des matrices reduites, geometrie elementaire,
  residu libre et identite energetique lineaire;
- historique de convergence des solveurs lineaires dans `solver.residual_history`
  et section `Solveur numerique` des rapports Markdown de resolution;
- export Markdown lisible via `save_audit_markdown` ou `--audit-md`;
- gate CLI via `--audit-gate fail` ou `--audit-gate warning`;
- mode detaille `detail="values"` / `--detail values` avec valeurs de matrices
  locales et trace d'assemblage elementaire vers les indices globaux;
- statut du rapport maillage.

## Post-traitement contraintes

Le champ `element_results` de la sortie JSON contient:

- pour `TET4`: deformations 3D, contraintes 3D, contraintes principales,
  deformations principales, pression hydrostatique, deviateur, point
  d'integration centroidal, resultats nodaux moyennes et von Mises;
- pour `TET10`: deformations et contraintes 3D au centre, avec les memes
  invariants solides, quatre points d'integration de Hammer et resultats
  nodaux moyennes;
- pour `MITC4`: resultantes locales au centre de l'element:
  `membrane_strain`, `curvature`, `shear_strain`, `membrane_force`,
  `bending_moment`, `shear_force`, `shell_faces`, `integration_points`,
  `nodal_results`, et le `local_frame`.

## Regles de code

- architecture orientee classes;
- fichiers source principaux inferieurs a 700 lignes;
- une responsabilite principale par classe;
- pas de logique metier dans la CLI;
- pas de parsing JSON dans les elements;
- pas de calcul EF dans les modules I/O;
- exceptions explicites avec messages utiles;
- tests ajoutes pour les nouveaux modules;
- MITC4 conserve dans son paquet valide.

## Tests

Les tests sont organises en:

- `tests/unit/` pour materiaux, TET4, validation, JSON, assemblage;
- `tests/integration/` pour API, CLI, modal, coques et exports;
- `tests/verification/` pour les verifications mecaniques rapides.

Commandes recommandees:

```powershell
python -m pytest
python .\mitc4_solver.py verify --quick
python .\qf_solver.py verify --quick
```

Etat verifie:

- le nombre de tests collectes et le statut de campagne sont recalcules par
  `python .\scripts\build_docs.py --profile engineering` puis publies dans le
  tableau de bord local; aucun compteur n'est maintenu manuellement ici;
- `python .\qf_solver.py methods`: liste les methodes lineaires,
  modales, dynamiques et non-lineaires ciblees.

## Prochaines etapes robustesse

- Generaliser arc-length aux cas multi-parametres et grands deplacements.
- Ajouter grands deplacements pour TET4/TET10.
- Ajouter contraintes nodales extrapolees ou moyennees.
- Ajouter resultats par point d'integration.
- Ajouter preconditionneurs avances: incomplete Cholesky, AMG.
