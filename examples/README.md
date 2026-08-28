# Exemples officiels

Ces fichiers JSON sont des cas minimaux maintenus par les tests
d'integration. Ils servent a verifier rapidement la CLI, l'API Python et
l'audit boite blanche.

## Cas disponibles

- `tet4_static.json`: solide 3D TET4 en statique lineaire.
- `tet4_compression.json`: compression TET4 avec solution fermee signee et
  bilan des reactions.
- `tet4_body_force.json`: force volumique constante TET4 avec resultante et
  reactions analytiques.
- `tet10_static.json`: solide 3D TET10 en statique lineaire.
- `mitc4_shell_static.json`: coque MITC4 en statique lineaire.
- `tet4_modal_unit.json`: solide TET4 modal avec frequence analytique de
  cisaillement.
- `tet4_nonlinear_static.json`: solide TET4 avec materiau non-lineaire simple.
- `tet4_linear_buckling.json`: facteur critique tangent sparse borne pour TET4;
  preuve de recherche, sans revendication de post-flambement.
- `tet4_elastoplastic_static.json`: solide TET4 avec loi Von Mises
  elastoplastique simple.
- `tet4_transient_dynamic.json`: solide TET4 dynamique transitoire Newmark.
- `tet4_dynamic_free_vibration.json`: vibration libre non amortie avec
  deplacement initial.
- `tet4_dynamic_sdof_free_vibration.json`: vibration libre Newmark 1 ddl avec
  energie initiale analytique.
- `tet4_dynamic_tabulated_load.json`: dynamique Newmark avec chargement
  temporel tabule.
- `tet4_harmonic_response.json`: reponse harmonique frequentielle TET4.
- `tet4_harmonic_sdof_response.json`: reponse harmonique 1 ddl avec amplitude
  et phase analytiques.
- `invalid_inverted_tet4.json`: cas volontairement invalide pour tester
  `inspect` et les messages de validation.

## Commandes utiles

Depuis la racine du projet:

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver inspect --input .\examples\tet4_static.json --markdown .\results\tet4_audit.md
qf-solver inspect --input .\examples\invalid_inverted_tet4.json --markdown .\results\invalid_audit.md
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4_results.json --audit-md .\results\tet4_audit.md --csv-dir .\results\tet4_csv --vtu .\results\tet4.vtu --audit-gate fail
```

Pour lancer tous les exemples:

```powershell
python -m pytest tests\integration\test_examples.py
```

L'API correspondante utilise le namespace public `qf_solver` :

```python
from qf_solver import load_model, solve_model

model = load_model("examples/tet4_static.json")
result = solve_model(model)
```

Les exemples non lineaires, de flambement et de contact sont des entrees
executables de demonstration. Leur statut de maturite est celui de la matrice
de release ; ils ne doivent pas etre lus comme une qualification generale.

## Demonstrations documentaires

Les modeles plus volumineux de poutres TET4/TET10 et de plaque MITC4 sont
generes dans `docs/generated/models/` par :

```powershell
python .\scripts\build_docs.py --profile engineering
```

Ils ne constituent pas une seconde collection manuelle. Leur entree, version,
unites, tolerance, verdict et empreinte sont publies dans
`docs/generated/docs_manifest.json` et dans le catalogue du site local.
