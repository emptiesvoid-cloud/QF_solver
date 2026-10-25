# WP11-B — Consolidation des API, résultats et maturités

Date : 2026-10-23
Branche : `codex/v0.2.12-integration`
HEAD audité : `a0846af0249ac3f3a37ec4e9c4900f1311c86238`
Tree audité : `b3b9886b7aa96874e5dfade5ea0e1c22c3b137ca`

## Conclusion exécutive

Le paquet WP11-B consolide la trace des capacités réellement présentes, actualise les pages API pour le candidat 0.2.12, ajoute un contrôle documentaire et des tests de sérialisation sans solveur, et conserve les limites scientifiques historiques. **Le statut officiel reste `WP11=OPEN`.** La décision descriptive proposée est **C — `OPEN_WITH_INTEGRATION_READY`** : les interfaces et preuves disponibles sont inventoriées, mais le critère roadmap « gate d’intégration complet à démontrer » ne définit pas assez précisément un critère d’acceptation qui permettrait de certifier sa clôture sans décision Owner.

Ce travail n’exécute aucun solveur FEM global, aucun `solve_model`, aucun Docker ni campagne de qualification. Les tests Hencky portent sur les seules fonctions matériau et les adaptateurs locaux bornés; ils ne vérifient ni l’assemblage global ni Newton. Aucun résultat historique négatif n’est remplacé.

## Baseline et provenance

L’identité de départ correspond à WP11-B. Les trois livrables WP11-A qui étaient non suivis ont été vérifiés avant intégration :

| Artefact WP11-A | SHA-256 vérifié |
|---|---|
| `wp11_a_consolidation_audit.md` | `a9cd4464562172a22f4140d7a9c784b4b3ae3120914553f6944e73c9a5f3bfd6` |
| `wp11_a_python_module_inventory.txt` | `a8b0c0fd3c29a425f3382419acaef9547d2b5a0d1c70a2e67160d600a254a2cb` |
| `wp11_a_branch_tree_differences.tsv` | `b17645e005869ff59c920417886b240eea0f61e9619dce1094f4d72262e16f04` |

Le rapport WP11-A reste l’audit historique du checkout initial. WP11-B l’étend sans réécrire ses constats ni les snapshots Owner antérieurs. L’inventaire consolidé est dans [`wp11_b_capability_traceability_matrix.tsv`](wp11_b_capability_traceability_matrix.tsv) : 17 lignes par famille, 12 colonnes, couverture vérifiée des 77 exports publics par comparaison avec `EXPECTED_PUBLIC_SYMBOLS`.

Le hash WP11-A du fichier `test_result_serialization_contracts.py` reste un hash historique de l’audit A. WP11-B ajoute à ce test un round-trip synthétique `to_dict/from_dict` pour les deux DTO versionnés; aucun solveur ne sert à construire ces objets. Le SHA-256 courant figure ci-dessous.

## Contrats API et résultats constatés

- La façade publique contient 77 noms : 30 `STABLE`, 47 `PROVISIONAL`, selon le contrat exécuté dans `tests/unit/test_public_api_contract.py`. Les signatures principales `load_model`, `check_mesh`, `solve_model` et `save_result` restent sous test.
- Le lecteur JSON de modèle accepte uniquement la version d’entrée 1; les champs et combinaisons pris en charge sont validés par le lecteur. `read_inp` demeure limité au sous-ensemble documenté, et n’est pas un parseur complet de format.
- Les résultats ordinaires (`SolveResult`, `ModalResult`, `DynamicResult`, `HarmonicResult`) exposent principalement `to_dict()` et sont écrits via des formats spécifiques. Ils ne partagent pas un identifiant de schéma de résultat versionné commun et il n’existe pas de `from_dict` générique pour les restaurer. Ce constat est documenté, sans créer ici de nouveau contrat ni considérer cette absence comme une incompatibilité prouvée par la roadmap.
- `ModalNewmarkResult` utilise `qf-modal-newmark-result/v1`; `ReducedHarmonicResult` utilise `qf-reduced-harmonic-result/v1`. Les deux sérialisent/désérialisent leur DTO et gardent `maturity=EXPERIMENTAL` et `qualification_decision=NOT_ASSESSED`.
- Le stockage mixte utilise `qf_solver.mixed_results.hdf5`, version `1.0`, avec writer, reader et digest sémantique. Le chemin documenté couvre TET4/WEDGE6/HEX8 et consomme des résultats existants.
- Les wrappers D02 `recover_solid_stress_field`, `recover_harmonic_stress` et `recover_modal_transient_stress` sont `PROVISIONAL`; leur sortie est `qf-dynamic-solid-stress/v1`, `EXPERIMENTAL`, `NOT_ASSESSED`. Le domaine fermé du D02 intégré reste linéaire isotrope TET4/TET10/HEX8/HEX20; les refus contact, BEAM2, matériau non linéaire, source/opérateurs obsolètes et champs incomplets restent applicables.
- Les deux kernels Hencky E01-BC sont des imports directs, expérimentaux et opt-in. Ils ne sont pas exposés par la fabrique de matériaux, l’API publique, le dispatch élémentaire, l’assemblage global ou la route Newton. Aucune classe Result Hencky ou sérialisation Hencky n’est revendiquée.

## Matrice de maturité E01 et D02

| Capacité | Statut conservé | Portée réelle / exclusion |
|---|---|---|
| WP-D02 — récupération de contraintes dynamiques | `CLOSED_BOUNDED` | Statut du rapport de clôture; limites de matériau, familles et refus ci-dessus. Ce statut n’est pas une qualification générale. |
| Hencky matériau au point matériel | `VERIFIED_BOUNDED` historique, 41/41 dans son identité documentée | Kinematics, stress/énergie et références ponctuelles; pas de global FEM. |
| Hencky tangente directionnelle au point matériel | `VERIFIED_BOUNDED` historique, 35/35 dans son identité documentée | La convergence en plateau n’est pas établie par les seuls minima d’erreur; pas d’intégration Newton. |
| Hencky force locale TET4/HEX8 | Seulement dans le périmètre borné du module matériau à 41 cas | Force locale, pas de scatter multi-éléments, conditions imposées, réactions ou tangent d’élément global. |
| Newton–Armijo GF4 TET4, sous-système esclave | `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` historique | Un scénario/maillage/gel exact et sous-système esclave. Le résultat ne qualifie pas le maître ni d’autres routes. |
| Verdict brut global BA | `FAIL` préservé | Ne pas le remplacer par le certificat borné esclave. |
| Équilibre maître + montage | `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED` | Explicitement hors du certificat esclave. |
| Tangente globale J2 | `UNRESOLVED` | Les échecs et directions faibles historiques persistent; pas de gate scientifique approuvé. |
| Qualification scientifique générale | `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED` | Aucun élargissement à d’autres matériaux, éléments, routes ou scénarios. |

## Dépendances WP et décisions

L’audit WP11-A compare les arbres de la branche courante avec C02, D01 et E01 et n’a démontré aucune dépendance directe de code/API C02 ou D01 nécessaire au périmètre courant. Les chemins divergents et les risques de conflit C02 restent documentés; l’absence de dépendance directe ne vaut pas autorisation d’intégrer ces branches. L’ordre de séquencement de la roadmap est conservé. Il n’est pas converti ici en obligation de clôture implicite : si un contrat historique approuvé impose explicitement un gate C02/D01, il reste applicable et doit être signalé comme conflit à l’Owner.

WP12 peut préparer les travaux dont les entrées, sorties et identités sont établies par cette matrice. Aucun blocage direct de code envers WP12 n’a été démontré. Une campagne WP12 qui exigerait un schéma portable générique ou un domaine C02/D01 devra d’abord faire approuver ce contrat spécifique. WP12 et WP13 restent ouverts et suivent leurs propres critères.

## Vérifications exécutées

Environnement numérique : un seul processus pytest, avec `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.

| Commande / portée | Résultat |
|---|---:|
| Tests ciblés API, résultat/sérialisation, WP11 J2, nœuds non solveur multifamily, garde d’arrondi D02, nœuds D02 affine/refus, Hencky material-point et tangent | **109 passed, 14 deselected**, 4.23 s |
| `test_gate_b_release_surface.py::test_hdf5_api_smoke_with_optional_dependency` — lecture d’un artefact mixte archivé | **1 passed**, 2.66 s |
| `python -m py_compile tests/unit/test_public_api_contract.py tests/unit/test_result_serialization_contracts.py` | PASS |
| `python -m ruff check tests/unit/test_public_api_contract.py tests/unit/test_result_serialization_contracts.py` | PASS — `All checks passed!` |
| Validation TSV par `csv.reader`, couverture des exports et nombre de colonnes | PASS — 77/77 symboles, 17 lignes, 12 colonnes |
| `git diff --check` | PASS |

La suite de 109 a désélectionné le workflow documenté `solve_model`, les quatre paramètres `build_and_solve_is_finite` (qui assemblent et résolvent) et les neuf autres nœuds du module D02 dynamique qui construisent des opérateurs ou exécutent une réponse dynamique. Les nœuds D02 retenus sont les quatre références uniaxiales de post-traitement et le refus fail-closed pour entrées invalides/incomplètes. Les tests E01 exécutent seulement les fonctions Hencky matériau et force locale définies par leur module; ils n’effectuent aucun assemblage global ni solveur Newton. Le test HDF5 lit un résultat archivé et ne crée pas de modèle.

La politique pytest racine vérifie la disponibilité de Gmsh par un import optionnel pendant la collecte; aucun maillage Gmsh ni backend natif n’a été lancé. Aucun Docker, solveur public, `solve_model`, campagne FEM qualifiante ou preuve nouvelle de convergence n’a été exécuté.

## Revue indépendante et décision de clôture

La revue indépendante de WP11-B par `<reviewer-workspace>` est favorable, sans P0/P1. Elle a demandé deux corrections P2 avant commit : le libellé de maturité API-04 et le hash du rapport de clôture. Les deux ont été corrigés et les pins du tableau d’empreintes revérifiés sur les octets courants. La revue WP11-A antérieure avait aussi confirmé l’exactitude des 27 lignes d’empreintes et des trois annexes historiques.

Le détail des gates et la recommandation sont dans [`wp11_b_closure_gate_assessment.md`](wp11_b_closure_gate_assessment.md). Recommandation provisoire : **C — `OPEN_WITH_INTEGRATION_READY`** en tant que description seulement; statut officiel `WP11=OPEN` jusqu’à la décision Owner sur le critère de clôture existant.

## Identités et empreintes

Les SHA-256 des livrables et fichiers modifiés (hors hash propre de ce rapport) sont :

| Fichier | SHA-256 |
|---|---|
| `wp11_a_consolidation_audit.md` | `a9cd4464562172a22f4140d7a9c784b4b3ae3120914553f6944e73c9a5f3bfd6` |
| `wp11_a_python_module_inventory.txt` | `a8b0c0fd3c29a425f3382419acaef9547d2b5a0d1c70a2e67160d600a254a2cb` |
| `wp11_a_branch_tree_differences.tsv` | `b17645e005869ff59c920417886b240eea0f61e9619dce1094f4d72262e16f04` |
| `wp11_b_capability_traceability_matrix.tsv` | `9dc9b92e4fe313f9580fbf78d61f10301c2452757814c599c8b5534f1910c48e` |
| `wp11_b_closure_gate_assessment.md` | `c0543afe5b1118b9ab1c22458e61deed172f2443500720753a20d43c85bd352e` |
| `docs/reference/qf_solver_api.md` | `69c191860d304f1d5115999b2b2f42972185169aed192d27d80d75056ef51149` |
| `docs/reference/api_stability.md` | `502a1c7c616c36caade77ea4db7dc449682254be731cdb665c681dfc977be20c` |
| `qualification/0_2_12/ROADMAP.md` | `23732eb3fb3a700ad53c1f6d5a576d3628751c63fd725e1e3ae1b523b5014c4f` |
| `qualification/0_2_12/v0_2_12_integration_progress_ledger.md` | `91055639166dce0cb050eab66765b9bdef7db1d9d161626c41fd58b3e1cf660a` |
| `tests/unit/test_public_api_contract.py` | `302a716ffa93aee8b9a29057a84457623b90a42dbf4d57d60bf8a174b1962ada` |
| `tests/unit/test_result_serialization_contracts.py` | `de3bc0a2ab1fb453be6296c5e96dd8e7288240a80c56b7b311723ca871680708` |

Le hash propre du présent rapport est communiqué dans le résumé final, pour éviter une auto-référence circulaire.
L’identité historique de ce test dans le tableau WP11-A était `b7de742efa0cb8ca23161ca74864049e143d0c6d678cc0cf4de1c9e05659652b`.

Pas de modification d’équation, critère scientifique, source solveur, route publique, branche `main`, tag ou publication.
