# WP11 — Audit API, résultats et sérialisation

## Résultat d’ensemble

La façade `qf_solver` expose 77 noms documentés et classés : 30 `STABLE`, 47 `PROVISIONAL`. Les tests de dépôt qui vérifient l’inventaire, la classification, les pages de référence et les signatures critiques ont réussi sur l’état audité. Un type de construction utilisé par `FiniteElementModel` apparaît dans sa signature sans être exporté lui-même par la façade; `load_model()` reste le chemin d’entrée documenté. C’est un point d’ergonomie P2, pas un défaut de signature démontré.

Les API ordinaires de résultats n’ont ni schéma universel versionné ni désérialiseur générique partagé. Les pages de référence le disent déjà. Aucun contrat WP11 approuvé ne requiert explicitement `load_result()` ou un format commun; le dossier ne crée donc pas cette obligation.

## Défauts corrigés

| Finding | Correction | Vérification |
| --- | --- | --- |
| `JsonResultWriter.write()` écrivait sur une destination existante avec remplacement silencieux. | Ouverture exclusive `x`; destination existante refusée avec `InputValidationError`; signature publique inchangée. Le contrat de `save_result()` est documenté. | `test_json_writer_saves_result`, `test_json_writer_refuses_to_overwrite_existing_result`, `test_public_save_result_refuses_to_overwrite_an_existing_path`. |
| Le chemin d’échec HDF5 supprimait toute cible existante après une course entre le précontrôle et `h5py.File(..., "x")`. | Nettoyage limité à l’identité fichier (device/inode) observée après ouverture réussie; erreur d’ouverture exclusive ne supprime pas le fichier concurrent. | `test_hdf5_writer_does_not_remove_file_created_by_competing_writer`. |
| `HarmonicResult.to_dict()` utilisait `zip()` et pouvait ignorer des fréquences excédentaires. | Contrôle explicite de l’égalité des nombres de fréquences et de réponses avant sérialisation. | `test_harmonic_result_rejects_mismatched_frequency_and_response_counts`. |
| Les décodeurs v1 Modal-Newmark et harmonique réduit reconstruisaient le DTO sans confronter plusieurs champs dérivés redondants. | Vérification des alias d’état, du verdict, de la maturité, de la décision de qualification et des champs dérivés (`ndof`, `response_dof_count`, lignes fréquentielles). Un champ absent ou incohérent est refusé. | `test_versioned_experimental_result_dtos_round_trip_without_solver_execution`, avec métadonnées volontairement altérées. |

Les corrections ne changent ni formule, ni loi constitutive, ni solveur, ni seuil, ni statut scientifique. Aucun champ inconnu n’est automatiquement interprété comme une capacité commune et aucun format historique n’est réécrit.

## Inventaire de sérialisation

- `SolveResult`, `ModalResult`, `DynamicResult`, `HarmonicResult` : DTO propres à l’analyse, `to_dict()` et sorties dédiées; pas de version commune ou de `from_dict()` partagé. Les tests WP11 ajoutés exercent un DTO synthétique et la règle de refus d’écrasement, sans solveur.
- Modal-Newmark : schéma `qf-modal-newmark-result/v1`, cartes DOF et champs temps réels, `from_dict()` spécifique; maturité `EXPERIMENTAL`, qualification `NOT_ASSESSED`.
- Harmonique réduit : schéma `qf-reduced-harmonic-result/v1`, fréquences et phasors séparés en réel/imaginaire, disponibilité de réponse explicite, provenance de base/opérateurs; `from_dict()` spécifique; maturité `EXPERIMENTAL`, qualification `NOT_ASSESSED`.
- Flexibilité résiduelle D01 : configuration stricte `qf-harmonic-residual-flexibility-config/v1`, résultat imbriquant sans réécriture le résultat WP05 et le schéma `qf-reduced-harmonic-residual-flexibility-result/v1`; test synthétique de round-trip réussi.
- Rotor/Campbell : payloads complexes spécifiques et helpers complexes présents; pas de lecteur commun. Les routes restent expérimentales et leur contrat ne permet pas d’inférer une qualification générale en rotordynamique.
- HDF5 : lecteur, écrivain, sélecteurs et digest sémantique version `1.0`; blocs homogènes TET4/WEDGE6/HEX8. Un round-trip synthétique sans assemblage vérifie le champ et l’égalité du digest logique. Le test d’API existant relit aussi un artefact historisé.
- D02 : `qf-dynamic-solid-stress/v1` documente convention, ordre, unités, identité et statut expérimental; wrappers sans lecteur générique dédié.
- Checkpoints : contrats spécifiques conservent identités d’opérateurs, sources, bases et clés d’exécution lorsqu’ils s’appliquent; ils ne sont pas un chargeur universel de résultats.

## Compatibilité et limites résiduelles

Le changement `save_result` est additif en signature mais plus strict en comportement : un script qui s’attendait à remplacer son JSON doit maintenant choisir explicitement une destination nouvelle ou gérer le fichier existant. Ce durcissement est demandé par le gate d’absence d’écrasement silencieux.

Les tests de cette campagne ne rejouent pas les solveurs ou analyses. Les fichiers d’API documentent les routes, mais leur disponibilité n’étend pas les limites d’éléments, de matériaux, de backend, de maturité ou de qualification définies par leurs work packages propriétaires.
