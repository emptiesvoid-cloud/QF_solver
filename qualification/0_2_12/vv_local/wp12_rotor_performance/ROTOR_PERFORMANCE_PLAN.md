# WP12-D — Matrice de régression rotordynamique et protocoles de performance

**Statut : PREPARATION_ONLY — NOT_AUTHORIZED — NOT_RUN**
**Date de l’audit : 2026-10-26**
**Worktree :** C:\Users\fari\.codex\worktrees\wp12-rotor-performance\qf_solver
**Branche / HEAD audité :** verify/wp12-rotor-performance / cbdd54aadbb640a96c6b6b5b9726e1247da36012
**Référence historique :** tag v0.2.11, commit afd2efa469a18e66581720ff4801f50de7d29eb4

Aucun test, solveur, calcul FEM ni benchmark n’a été exécuté pendant cet audit. Les contrôles effectués sont des lectures de fichiers, empreintes Git et vérifications statiques du code et des politiques. Cette note ne change ni le solveur, ni les tests, ni le runner, ni la politique.

## Décision et interprétation

Les preuves v0.2.11 montrent des vérifications numériques bornées des formulations gyro-QEP et Campbell. Elles ne constituent ni une validation physique d’un rotor réel, ni une qualification formelle, ni une preuve de performance du HEAD actuel.

Le suivi à 100 rad/s contient une ambiguïté modale explicitement conservée : deux modes sur quatre sont suivis. Cette ambiguïté doit rester visible dans toute comparaison future; aucun appariement forcé ne doit être introduit pour produire artificiellement une convergence complète.

Le HEAD candidat n’est pas identique au code source qui a généré les preuves historiques. Les sentinelles décrites ci-dessous doivent donc être réinscrites sur le HEAD et les empreintes actuels avant leur exécution.

## Cinq affirmations à garder séparées

| Axe | Ce que les éléments historiques établissent | Ce qu’ils n’établissent pas |
|---|---|---|
| Résultat scientifique | Les oracles analytiques, résidus QEP, invariants gyro et tendances de maillage ont satisfait les critères enregistrés dans les cas historiques. | Exactitude universelle des réponses d’un rotor, validité de toute géométrie ou matériau, ou validation par mesures expérimentales. |
| Fiabilité de la route logicielle | Il existe des tests unitaires et d’intégration pour les routes rotating-modal et Campbell, la sérialisation complexe et l’exposition publique. | Réussite de ces routes sur le HEAD cbdd54a; aucune sentinelle n’a été relancée ici. |
| Performance | Un benchmark historique caractérise l’eig généralisé dense sur des matrices synthétiques de taille définie. | Performance d’un rotor assemblé, d’un cas de production, d’un solveur itératif ou du HEAD courant. |
| Scalabilité | Le contrat historique borne une caractérisation synthétique jusqu’à 1000 DDL physiques, sans extrapolation au-delà du plus grand palier terminé. | Scalabilité industrielle, mémoire/temps pour un grand rotor physique, calcul parallèle ou promesse sur des tailles supérieures. |
| Qualification physique | Le statut enregistré des capacités rotor est EXPERIMENTAL. | Qualification physique/formelle, conformité à un essai rotor, libération générale de rotating-modal ou de Campbell. |

## Inventaire des preuves historiques examinées

Les SHA-256 identifient les fichiers présents sous qualification/0_2_11 dans le checkout audité.

| Fichier | SHA-256 | Portée utile |
|---|---|---|
| qualification/0_2_11/wp05_gyroscopic_contract.json | 9e5e3ca372aee4431dffd21f1ed92ee051612d268f5e81935da2132e8161dd17 | Équations, unités, invariants, tolérances et benchmark dense WP05. |
| qualification/0_2_11/wp05_gyro_verification_records.json | 78f731a42d072da1b87d0b5e7c80eef3fb4b4565da866076d53860504f4b8bd1 | Enregistrements GYRO-01 à GYRO-04; source f2690bcac8f1b5b34c6b01a6cf5a9e19ecb725a9; maturité EXPERIMENTAL. |
| qualification/0_2_11/wp05_dense_characterization.json | beac46466f7b1b1fb37eda7fa0706397ead77e24d433d951c7d5d900dd757618 | Résultats de l’eig dense sur matrices synthétiques, trois répétitions par taille. |
| qualification/0_2_11/wp05_gate_summary.json | b2bf32735b88eaf890cb0133a69305f1844b3641fc299742720ac26f96f3da9a | Statut de gate historique; contient aussi G03: FAIL_PRESERVED, distinct de GYRO-03. |
| qualification/0_2_11/wp06_campbell_contract.json | 8caa305017b7d0ff9eae8b756d246261a2172a6f37c951795db30e4893a466c2 | Contrat WP06, neuf vitesses pour GYRO-05 et quatre maillages pour GYRO-06. |
| qualification/0_2_11/gyro_05_campbell_analytical.json | d37bc5efee522dce6a4cea4b372f871954d050bb1285c17d3fade40572cbf0ad | Comparaison Campbell analytique historique, source bf59bac3d38f19139a401ec8665b326e05917629. |
| qualification/0_2_11/gyro_06_beam2_convergence.json | 601029ffede0e8882c89c613e39b6025620ce4cc52cbdc6eaf9e91d54f6983f0 | Résultats Campbell/maillage BEAM2 historiques, source bf59bac3d38f19139a401ec8665b326e05917629. |

Le tag v0.2.11 est afd2efa469a18e66581720ff4801f50de7d29eb4. Les commits source f2690bcac8f1b5b34c6b01a6cf5a9e19ecb725a9 (WP05) et bf59bac3d38f19139a401ec8665b326e05917629 (WP06) sont ancêtres du tag. Le champ logiciel du record WP06 indique qf_solver 0.2.10; le résultat est inclus dans les preuves de la release v0.2.11, mais ne doit pas être décrit comme une exécution du paquet 0.2.11.

### Contrat gyro à préserver

Le modèle historique est M q̈ + Ω G q̇ + K q = 0. G est une matrice unitaire en vitesse, ne contient pas Ω et doit être antisymétrique, Gᵀ = −G. La vitesse signée Ω, en rad/s, est appliquée exactement une fois. Le bloc de G a les unités généralisées de M; pour les rotations, il s’agit de kg·m². La conversion RPM doit rester explicite. L’axe est défini selon la règle de la main droite globale; les blocs doivent suivre le même mapping global des DDL que M et K.

Pour un disque sur l’axe local x, le bloc gyro rotationnel RY/RZ du contrat est [[0, Jp], [−Jp, 0]]. L’assemblage ne doit pas corriger l’antisymétrie après coup par projection. Les critères WP05 historiques incluent une antisymétrie relative ≤ 1e−12, une symétrie M/K ≤ 1e−12, et des résidus QEP relatifs bornés à 1e−8 en général (oracle simple ≤ 1e−10).

## Matrice des régressions rotor

Les statuts historiques ci-dessous ne sont pas des statuts de régression du HEAD actuel. Chaque sentinelle reste NOT_RUN ici.

| Régression | Sentinelle existante ou preuve | Historique et constat | Statut HEAD courant |
|---|---|---|---|
| GYRO-01, limite Ω=0 | tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces | PASS enregistré; retrouve fréquences, multiplicités et sous-espaces modaux à vitesse nulle. | NOT_RUN; empreintes à réinscrire. |
| GYRO-02, unités et bloc disque | tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract | Sentinelle d’unités et de convention de signe pour masse et G à vitesse unitaire. | NOT_RUN. |
| GYRO-02, mapping d’assemblage | tests/unit/test_rotating_disk_gyro.py::test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work | Contrôle du mapping DDL global et du travail quadratique nul de G antisymétrique. | NOT_RUN. |
| GYRO-02, covariance de repère | tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_gyro_are_covariant_under_global_frame_rotation | Contrôle du transport du bloc disque sous rotation globale. Sentinelle complémentaire recommandée. | NOT_RUN. |
| GYRO-03, oracle QEP signé | tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0] et [-100.0] | Cas historiques inclus dans les résultats WP05; les deux signes sont requis pour vérifier l’application de Ω une seule fois. | NOT_RUN. |
| GYRO-04, inversion du spin | tests/unit/test_rotating_qep.py::test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies | Le changement de signe inverse le terme du crayon QEP et conserve les fréquences non ordonnées prévues par le contrat. | NOT_RUN. |
| GYRO-04, dédoublement | tests/unit/test_rotating_qep.py::test_gyro04_splitting_increases_with_absolute_signed_spin | Tendance du dédoublement en fonction de |Ω|. | NOT_RUN. |
| Ambiguïté d’affectation | tests/unit/test_modal_tracking.py::test_competing_source_modes_make_the_global_assignment_ambiguous | Vérifie qu’une affectation concurrente est signalée comme ambiguë. | NOT_RUN. |
| Ambiguïté de sous-espace dégénéré | tests/unit/test_modal_tracking.py::test_degenerate_basis_rotation_is_reported_as_cluster_ambiguity | Vérifie qu’une rotation de base dans un cluster ne produit pas de branche individuelle artificielle. | NOT_RUN. |
| Route Campbell et sérialisation | tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results | Contrôle une route Campbell à plusieurs vitesses et les résultats complexes sérialisés. | NOT_RUN. |
| Schéma et route d’analyse | tests/unit/test_campbell.py::test_campbell_is_exposed_through_model_schema_and_analysis_router | Contrôle l’exposition dans le schéma et le routeur. | NOT_RUN. |
| API publique JSON | tests/integration/test_rotating_modal_public_api.py::test_public_json_load_solve_and_save_support_experimental_rotating_modal | Contrôle de bout en bout de chargement, solve et sauvegarde via l’API publique. Test d’intégration distinct. | NOT_RUN. |

Les sentinelles de prévol existantes pour les restrictions de modèles, conversion RPM explicite, refus de la route modale classique et résultat séparé marqué expérimental sont à garder comme sentinelles de fiabilité de route complémentaires. Elles ne remplacent pas les oracles gyro ni l’analyse Campbell.

## Résultats quantitatifs historiques

### GYRO-05 — Campbell analytique

Le record couvre neuf vitesses signées, de −100 à +100 rad/s, et 18 comparaisons de fréquence. L’erreur relative maximale de fréquence est 1.8773089469619775e−15 et le résidu QEP maximal est 2.9154413849188606e−15.

Limite : l’oracle construit un crayon QEP dense SciPy localement. Il ne suit pas la route de production d’assemblage G et de résolution QEP. À Ω=0, le cas dégénéré est rapporté en cluster ambigu; aucune arête d’appariement modale individuelle n’est engagée. C’est une bonne vérification algébrique, pas une validation de la route physique.

### GYRO-06 — convergence de maillage et ambiguïté à 100 rad/s

Le protocole historique utilise 4, 8, 16 et 32 éléments BEAM2, les vitesses 0, 100 et 250 rad/s, quatre modes positifs demandés, soit 12 résolutions Campbell/QEP au total. Le résidu QEP relatif maximal est 1.6173500115243727e−9, inférieur à la limite historique 1e−8. La différence relative maximale entre maillages adjacents 16→32, sur les branches communes suivies, est 0.00011432898981305986, inférieure à la limite 0.005.

À 100 rad/s, seulement 2 modes sur 4 sont suivis à chaque maillage; le record qualifie la couverture de PASS_WITH_RECORDED_AMBIGUITY. Les deux branches hautes restent non suivies :

| Éléments BEAM2 | Fréquences non suivies rapportées (Hz) |
|---:|---:|
| 4 | 423.066905 et 423.492723 |
| 8 | 422.068494 et 422.490145 |
| 16 | 421.863411 et 422.284225 |
| 32 | 421.815436 et 422.236056 |

La convergence 16→32 ne s’applique qu’aux modes suivis communs; elle ne résout pas les deux branches ambiguës. Le PASS historique est donc une convergence bornée avec couverture partielle, pas une preuve de suivi complet.

### Performance historique — crayon synthétique dense WP05

Les matrices M, K et G sont générées synthétiquement; ce benchmark n’est pas un modèle rotor FEM. Le crayon linéarisé a une dimension 2n. Trois répétitions ont été faites par taille, avec un thread BLAS dans le protocole historique.

| DDL physiques n | Dimension QEP 2n | Temps médian historique (s) | RSS max (octets) | Résidu QEP max |
|---:|---:|---:|---:|---:|
| 50 | 100 | 0.0457263 | 74 477 568 | 8.11954e−15 |
| 100 | 200 | 0.1511772 | 78 495 744 | 2.41488e−14 |
| 250 | 500 | 2.1760630 | 102 916 096 | 9.66752e−14 |
| 500 | 1000 | 25.3042731 | 186 372 096 | 5.78238e−13 |
| 1000 | 2000 | 271.2178427 | 516 771 840 | 5.03602e−12 |

La somme des médianes par taille est environ 896.7 s pour les 15 résolutions. Cette somme n’est pas le temps total mesuré d’une campagne; les temps sont un historique synthétique d’une machine et d’une pile logicielle précises. Le contrat ne justifie aucune extrapolation au-delà de 1000 DDL. Il réduit le dernier palier de support si son RSS max dépasse 50 % de la mémoire disponible et s’arrête si la projection atteint le seuil de sécurité enregistré.

## Écart entre l’évidence v0.2.11 et le HEAD candidat

Les empreintes des composants rotor clés ne sont pas identiques entre l’évidence v0.2.11 et le HEAD cbdd54a. Une réinscription source-bound est nécessaire; l’évidence précédente ne se substitue pas à la régression du HEAD courant.

| Fichier | SHA-256 v0.2.11 | SHA-256 au HEAD cbdd54a |
|---|---|---|
| src/solveur/core/assembly/rotating_disk_gyro.py | 85e1ac04d0432cf0e6d1d9057703a7748498104ae4c7d43a4d81e875872d6ed4 | 750577a6277e10306ee9f08787da7abc2112eefd4d5cf5e162818c8f4b2f0b37 |
| src/solveur/core/analyses/qep.py | c6b080cfaa6df18b486dbf985208881de14f06639b467f908baa5812a1d00b32 | 34d7330394dda4c5df87741e4d5b1ca7e179122921b82e96bb28938ebcd69527 |
| src/solveur/core/analyses/rotating_modal.py | 9f6558288307aa6331af5955e11ea365ef122e9b8e5dc38aa77e039dbf74719d | 918eed99be91e25fd43f2ee846fc809608ee313b6580973825bbbbdc57969d54 |
| src/solveur/core/analyses/campbell.py | a82cc884141a477a173efb9ad205eae41776b0e157189026b736ab99f21e6137 | a1a6974b80d232aa613b8d2cae8f50a4789462ab79339a31f2ba6e5c4f106cdb |
| src/solveur/core/analyses/modal_tracking.py | 95a53071c8103074501a322374dd8c027760c954a00b7428c09e81eef1886952 | c2a6bd3aff65c7b47db830bce3a4ff00fdca7b3fe675d2b7415e8638650f0b76 |
| src/solveur/core/analyses/rotating_input_validator.py | d0c96425935c25c2d51aeed12688d849167f35f35d8b2a3516821b7039ab52b5 | 1989f306c826cba847f539a1c38c40a5ba75c374e6b3cf8d39190ce4e19f392c |

Cette comparaison est une comparaison de contenu, pas un diagnostic de régression : elle indique qu’un retest au HEAD courant est requis, pas qu’un défaut a été trouvé.

## Sentinelles minimales proposées

Conserver les nodeids existants; ne pas créer de nouvelles expériences pour cette phase. Les 12 nodeids unitaires et un nodeid d’intégration de la matrice sont le minimum proposé pour séparer invariants, branchement en vitesse, ambiguïté de suivi et fiabilité de route. Le replay GYRO-06 et le benchmark dense restent deux campagnes distinctes, pas des ajouts implicites à pytest.

La politique development_autonomous_policy.json examinée n’enregistre aucun nodeid rotating/gyro/Campbell ni entrée de benchmark rotor. Le scope WP12 dynamique existant concerne projection modale, Newmark, harmonique réduit et accélération de base. Les budgets ci-dessous sont une proposition pour décision et enregistrement; ils ne sont pas une autorisation courante.

## Protocoles de benchmark et budgets prévisionnels

### A. Sentinelles existantes

- Réinscrire chaque nodeid exact sur le HEAD et le fingerprint source courants.
- Exécuter un seul nodeid exact par tentative et conserver une preuve distincte pour chaque invocation.
- Budget proposé : 300 s maximum et 4096 MiB RSS soft par nodeid unitaire; 300 s et 4096 MiB RSS soft pour le nodeid d’intégration. Une tentative par nodeid, sans retry automatique.
- Plafond théorique si toutes les invocations atteignent leur timeout : 65 minutes au total (12 × 300 s unitaires + 300 s intégration). Ce plafond est une enveloppe, pas une prévision du temps réel.
- Les scopes standards actuels indiquent 900 s / 4096 MiB pour unit et 1200 s / 4096 MiB pour integration, mais ils ne constituent pas une inscription rotor et n’autorisent pas ces cas.

### B. Replay de convergence Campbell GYRO-06

- Cas fixe : 4/8/16/32 éléments BEAM2 × 0/100/250 rad/s × quatre modes positifs demandés; 12 résolutions QEP attendues.
- Une tentative unique. Enveloppe proposée : 1800 s de temps mur total, RSS soft 4096 MiB; aucun retry. Ces limites sont des plafonds préparatoires, pas un coût mesuré. Le record v0.2.11 ne contient pas de durée utilisable pour prévoir le replay.
- Le point 100 rad/s doit rester évalué comme suivi partiel avec les ambiguïtés explicitement conservées.
- Le script historique scripts/run_wp06_verification.py exécute GYRO-05 et GYRO-06 ensemble puis écrit dans des chemins versionnés fixes sous qualification/0_2_11 et docs/assets. Ne pas l’exécuter dans le checkout des preuves historiques ni écraser ces fichiers. Avant tout replay autorisé, le run doit avoir une sortie isolée et un inventaire de preuve par tentative; si le chemin de sortie isolé ne peut être assuré sans toucher au runner, ne pas lancer.

### C. Référence de performance de l’eig dense synthétique

- Reprendre exactement les matrices/formules, les tailles physiques 50/100/250/500/1000, les dimensions linéarisées 100/200/500/1000/2000 et trois répétitions par taille du contrat WP05.
- Fixer un thread BLAS; enregistrer les variables de threads, bibliothèques BLAS/LAPACK chargées, OS, CPU, RAM, Python, NumPy, SciPy, commit, empreintes du script et contrat, médiane/min/max, dispersion, RSS, résidu et taille du problème.
- Budget proposé : 1800 s de temps mur agrégé, 4096 MiB RSS soft, une campagne sans retry. Limite interne d’un worker à 600 s; un contrôleur doit imposer le plafond total de 1800 s. Le paramètre --timeout-seconds du script est par worker et n’est pas à lui seul un budget de campagne.
- Repère historique : somme des médianes ≈896.7 s. Ce nombre justifie une enveloppe initiale prudente, mais ne prédit pas la performance du HEAD actuel. Respecter les arrêts mémoire du contrat; arrêter si l’environnement ou le RSS rend le palier suivant non sûr. Le script accepte une sortie explicite; elle doit être un chemin inédit du run, jamais un résultat v0.2.11.
- Ce benchmark caractérise uniquement l’eig dense synthétique et la route SciPy de l’environnement enregistré. Il ne constitue pas un benchmark FEM ni un engagement de capacité produit.

### D. Comparaison direct / itératif

Le code QEP actuel appelle scipy.linalg.eig sur un crayon généralisé dense. La disponibilité de PETSc/SLEPc dans les extras de dépendances ne signifie pas qu’une route backend existe. À l’audit, petsc4py et slepc4py ne sont pas installés dans l’environnement utilisé et aucune route iterative correspondante n’est implémentée dans le QEP examiné.

Ne pas publier de comparaison direct/itératif ni créer une mesure proxy. Une étude ne devient pertinente qu’après disponibilité réelle d’un backend, identification de ses options numériques, et comparaison sur les mêmes M/K/G, modes, résidus, vitesses et règles d’appariement. Son budget est donc non chiffrable et non autorisé ici.

## Environnement de référence à consigner

Snapshot d’audit statique courant : Windows 10 10.0.19045, Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, psutil 7.2.2, AMD64 Family 25 Model 80, 12 processeurs logiques / 6 physiques, RAM totale rapportée 102 963 109 888 octets. Les variables d’environnement BLAS n’étaient pas définies; aucune mesure QEP n’a été lancée et aucun pool BLAS actif n’a été observé avant le chargement d’un solveur.

Le record benchmark v0.2.11 a forcé un thread BLAS et rapporte des bibliothèques OpenBLAS différentes dans NumPy/SciPy. Chaque nouvelle campagne doit inventorier les bibliothèques réellement chargées après initialisation, et ne doit pas supposer que l’environnement courant est identique à l’environnement de release.

## Recommandation de release

1. Garder rotating-modal et Campbell au statut EXPERIMENTAL.
2. Préserver GYRO-01 à GYRO-06 comme preuves historiques bornées, sans les présenter comme résultats du HEAD cbdd54a.
3. Préserver séparément G03: FAIL_PRESERVED du gate WP05; il ne doit pas être confondu avec le cas GYRO-03.
4. Maintenir visible la couverture partielle et les deux modes non appariés à 100 rad/s. Ne pas forcer l’affectation pour faire passer la convergence.
5. Ne revendiquer ni validation physique, ni scalabilité au-delà des 1000 DDL synthétiques caractérisés, ni solveur itératif.
6. Avant toute exécution, obtenir une inscription spécifique rotor des nodeids exacts et des budgets, un manifeste/run ID inédit, l’autorisation Owner applicable et un emplacement de preuve sans écrasement.
7. Réexaminer le statut seulement après résultats reproductibles du HEAD identifié, analyse séparée des cinq axes ci-dessus, preuve archivée complète et décision de release explicite.

## Résumé d’exécution de cette mission

- Branche créée et conservée : verify/wp12-rotor-performance.
- HEAD : cbdd54aadbb640a96c6b6b5b9726e1247da36012.
- Worktree propre avant rédaction de cette note.
- Aucun nodeid rotor ou benchmark rotor enregistré dans la politique examinée.
- Aucun calcul, test ou benchmark exécuté.
- Les budgets de ce document sont des propositions, pas une autorisation.

## Controleur et preparation des inscriptions

Le chemin de controleur designe par les instructions du depot, E:/QFSolverAgents/wp12-policy-final, est au commit 4bf52792f46988b84fecf11ebe3bd5fe078975ef, sur codex/wp12-policy-finalization. Il est six commits derriere la ref courante origin/emptiesvoids-cloud/0.2.12, aujourd’hui au commit 98456355f0a85dff9edf7f37d53c7c6fff59bf37, et son fichier development_autonomous_policy.json porte des modifications locales. Identites observees sur ce checkout : runner SHA-256 509c5e5d875bf165bf7e4c0937faafa4466a3fff0de6b6a5e7f4957be527cf626; politique de l’arbre de travail SHA-256 a805f55dc0535f12658afbb4b14b9bb903b56d8dfe1d1b35011fc11668dbc79c9. Aucune modification n’a ete faite dans ce worktree.

Le HEAD courant 98456355f0a85dff9edf7f37d53c7c6fff59bf37 ajoute uniquement des documents de roadmap depuis cbdd54aadbb640a96c6b6b5b9726e1247da36012. Le runner et la politique suivis dans ce HEAD restent identiques aux fichiers du worktree propre de preparation : runner SHA-256 9d23d4028dcfeb9eb854c83b463042c15dd749ae36704178bc4d84398611f6dc; politique SHA-256 79010807fe75cc62f3cb08801f860b32df08911dd015f9e321d516a583aee149. Le worktree E:/QFSolverAgents/wp12-policy-registration-consolidation etait propre au HEAD cbdd54, mais il est maintenant six commits derriere; le worktree de preparation isole est au HEAD 98456355. Aucun manifeste n’a ete emis par l’un ou l’autre. Les empreintes runner/politique ne remplacent pas l’identite complete du controleur attendue par un manifeste.

Le runner courant ne permet register-nodeid et prepare-manifest que pour quatre scopes WP12 : wp12_wp07, wp12_tet4, wp12_elements et wp12_dynamics. Les deux commandes refusent tout autre worktree_id; la politique n'a pas de scope rotor. L'inscription sous wp12_dynamics reutiliserait a tort son worktree, sa branche et son mandat Newmark/harmonique/base-motion. Un nouveau scope rotor necessiterait une evolution du controleur/runner, interdite par la presente mission. En consequence, aucun manifeste controleur-valide ne peut encore etre produit pour verify/wp12-rotor-performance. Ne pas fabriquer de manifestes manuels ni reaffecter ces cas a un autre scope.

Decision de configuration requise avant la suite : fixer quelle identite du controleur est canonique, puis fournir une voie d'inscription et de preparation de manifestes pour un scope rotor isole, sans modifier l'historique des quatre scopes existants. Les lignes de sentinelles et budgets proposees dans ce plan restent des elements de demande, etat NOT_AUTHORIZED.
