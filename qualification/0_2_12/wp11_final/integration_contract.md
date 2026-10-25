# WP11 — Contrat d’intégration et périmètre retenu

## État et portée

Ce dossier évalue le WP11 opérationnel v0.2.12 (« intégration, résultats, API et sérialisation »). Il ne concerne pas le WP11 prospectif « generalized-alpha » de la partie II de la roadmap.

Le travail reprend le checkout `emptiesvoids-cloud/0.2.12` au SHA `4bd6abb704f39cda758a3f0a36d8cd71d81da554`. La mission présente autorise la reprise du WP11. Elle n’efface pas les entrées historiques `WP11=PAUSED_BY_OWNER` du ledger et ne vaut pas décision de clôture. La roadmap opérationnelle porte `WP11=OPEN` et demande encore la démonstration du gate d’intégration complet.

## Contrat retenu

1. `qf_solver` reste la façade Python publique. L’inventaire versionné dans `docs/reference/qf_solver_api.md` comprend 77 exports : 30 `STABLE` et 47 `PROVISIONAL`. Les signatures publiques existantes restent inchangées.
2. Les entrées modèle utilisent le JSON v1 documenté. `read_inp` reste limité au sous-ensemble annoncé. Les validations et erreurs typées documentées demeurent le contrat.
3. Les résultats ordinaires gardent leurs DTO et sérialiseurs propres. Ils exposent `to_dict()` et des sorties JSON/CSV/VTU selon le résultat. Aucun `load_result()` universel ni schéma commun versionné n’est promis. L’absence de ce schéma n’est pas qualifiée de défaut sans exigence Owner explicite.
4. Les contrats qui déclarent un schéma ou un round-trip restent spécifiques : `qf-modal-newmark-result/v1`, `qf-reduced-harmonic-result/v1`, le wrapper D01 `qf-reduced-harmonic-residual-flexibility-result/v1`, le stress D02 `qf-dynamic-solid-stress/v1` et le stockage HDF5 mixte `qf_solver.mixed_results.hdf5` version `1.0`.
5. Les payloads complexes conservent des parties réelle et imaginaire explicites là où le contrat le prévoit. Identités de source, opérateur, base et exécution restent contrôlées lorsqu’exigées par le DTO concerné.
6. `save_result(result, path)` garde sa signature stable et refuse désormais atomiquement une destination JSON existante. Le stockage HDF5 conserve son mode création exclusive; un nettoyage d’échec ne peut supprimer que le fichier que cet écrivain a ouvert et identifié.
7. Les implémentations C01, C02, D01, D02 et E01 présentes dans le checkout sont inventoriées ci-dessous avec leurs statuts propres. L’intégration de code ou une réussite de sérialisation ne vaut pas preuve numérique ou qualification FEM.

## Capacités présentes et maturité

- **C01 B*** : route de transfert tangentiel `small_rotation_work_conjugate` opt-in pour une paire esclave/triangle maître figée et des petites rotations analyste-imposées. Le défaut reste `legacy`. La glissade finie, la tangente globale cohérente de glissement et la convergence spatiale restent non acquises. `WP_C01_HISTORICAL=CLOSED_NEGATIVE`, remédiation ouverte.
- **C02** : le code et le rapport d’intégration sont présents. `CLOSED_BOUNDED` couvre uniquement le benchmark fabriqué WP-C02-AR/N03 TET4 à face plane figée. Qualification générale du contact, équivalence Docker et convergence asymptotique restent `NOT_ACQUIRED`; les échecs historiques N06/N08 et Docker restent inchangés.
- **D01** : la flexibilité résiduelle est raccordée comme option strictement opt-in à `harmonic_response/modal_superposition`; l’absence de configuration conserve le chemin WP05 antérieur. Les schémas de configuration et de résultat sont versionnés. Le statut technique reste `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED`, `WP05_FEM_QUALIFICATION=NOT_EVALUATED`; aucun calcul FEM n’est fait dans cette reprise.
- **D02** : `CLOSED_BOUNDED` uniquement pour la récupération de contraintes dynamiques expérimentale et ses fixtures documentées. Cette clôture ne qualifie pas une récupération générale.
- **E01** : `OPEN_WITH_BOUNDED_CERTIFICATES`. Le certificat historique GF4 est limité au sous-système esclave TET4 et à son identité gelée. `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`, le verdict global BA demeure `FAIL`, la tangente J2 globale demeure non résolue et la qualification scientifique générale demeure `NOT_ACQUIRED`. Les noyaux Hencky, C1 et le chemin corotationnel/polaire restent expérimentaux et bornés.

## Gate WP11 et exclusions

Les vérifications de ce dossier démontrent l’inventaire de façade, les signatures ciblées, les contrats JSON/HDF5 et plusieurs refus/round-trips synthétiques. Elles constituent des preuves de contrat et de non-régression uniquement.

Aucun solveur, assemblage ou test FEM n’a été exécuté. Les campagnes C01/C02/D01/D02/E01, les tests de solveur réduits, Docker, MPI et solveurs externes n’ont pas été relancés. La mission ne fournissait pas de manifeste d’exécution FEM gelé avec identité d’entrées, budget et allowlist Owner distincte. Cette absence ne doit pas être masquée par les tests DTO ou les preuves historiques.

La recommandation est donc **`OPEN_WITH_ACTIONS`**. Voir `closure_gate_assessment.md` et `owner_decision_request.md` pour les décisions encore nécessaires. Aucun statut de roadmap n’est modifié par ce dossier.
