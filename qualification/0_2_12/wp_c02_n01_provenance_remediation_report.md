# WP-C02-N01 — audit de provenance et remediations candidates

Date d'audit: 2026-10-23. Perimetre: lecture seule du worktree partage `wp-c02-ar`, calcul offline de SHA-256, analyse des diffs Git, puis remediations dans le worktree isole `wp-c02-n01-remediation`. Aucun Docker, calcul FEM, collect, merge, publication ou commit.

## 1. Decision de provenance du P1

Le rapport de preparation tel que revu a le SHA-256 fichier `614b177d77308b7fea67a8282c305852c189f69b9817331998bb2f57ca4eac2e`; ce hash correspond a la copie conservee sous `qualification/0_2_12/provenance/wp_c02_ar_native_preparation_report_as_reviewed.md`. Il indique l'agregat source `c0a29b1244d9d4d308769528a8a03e3b703ab123fce595ece069cc15199bd3c5`. Le manifeste refuse SHA-256 `dd17e77d6b9776508e26642a33636df2920a612542caff93cae2134cf02bc105` indique `c7fcd94bcab8d25d45c9387e7f41af15777ba7a83f2d4003458c4e9d92463e15`.

Recalcul independant du manifeste partage:

- 525 entrees `source_files_sha256`; les 525 fichiers existent et leurs SHA-256 individuels correspondent, zero ecart.
- L'agregat `c7fcd94...` est reproduit exactement par SHA-256 sur les chemins tries lexicographiquement, en encodant chaque enregistrement UTF-8 sous la forme `path + deux espaces ASCII + hash hexadecimal minuscule`, separe par LF sans LF final.
- `c0a29...` ne correspond pas a l'agregat du mapping present. Aucun mapping historique ayant produit `c0a29...` n'est archive dans le worktree ou dans Git; l'origine exacte de cette ancienne valeur ne peut donc pas etre determinee (typo vs ancien mapping, contenu ou perimetre).
- L'algorithme n'etait pas defini dans le manifeste original et le runner original ne recalculait pas `source_set_sha256`; il ne comparait que les hashes individuels. La formule ci-dessus est recuperee par recomputation exacte de `c7f...`, puis rendue contractuelle et executable dans le nouveau candidat.
- Le manifeste original contient 525 chemins. Ni le rapport de preparation ni le manifeste ne figurent parmi eux. La revue precedente affirmait a tort que le rapport etait hash dans le manifeste; l'inspection du mapping confirme qu'il ne l'est pas.

Conclusion: le P1 de coherence rapport/manifeste est explique comme une reference documentaire obsolete dans le rapport. La provenance de la valeur `c0a29...` reste historiquement non reconstructible; le gel initial conserve donc son statut refuse `FAIL_CLOSED`. Le nouveau candidat ne s'appuie pas sur cette valeur et publie un nouveau mapping, un contrat explicite et des controles qui le recalculent. Statut du correctif: `PREPARED_PENDING_INDEPENDENT_REVIEW`, pas ferme/qualifie.

### Classification demandee

1. Reference documentaire obsolete: demontree; le rapport cite `c0a29...` alors que la liste presente donne `c7f...`.
2. Modification effective des sources: aucune divergence entre les 525 hashes du manifeste et les fichiers du worktree partage. Cela ne permet pas d'exclure un changement ancien avant l'archivage du mapping `c0a29...`.
3. Perimetre: le compte actuel est 525. Le rapport et le manifeste etaient exclus du mapping. Le nouveau candidat ajoute un test de contrat statique, donnant 526 chemins; il n'ajoute aucune source scientifique.
4. Construction du manifeste: mapping individuel cohérent et agregat present reproductible; defaut de contrat/validation, car l'algorithme n'etait ni specifie ni verifie par le runner.
5. Divergence historique: origine des inputs exacts de `c0a29...` non resolue faute de mapping archivé. Le nouveau candidat corrige le gel prospectif; la preuve initiale n'est pas reecrite.

## 2. Huit fichiers WP-C02-AT modifies dans le worktree partage

Au premier releve du 2026-10-23, huit fichiers suivis etaient modifies, et non six comme annonce par le rapport initial. Pendant l'audit, le HEAD partage est passe de `cd02eef59d3345643d617035be96190811d370bb` a `b635c3693b61159b8452ce93f6fb688566b5ef3a`; les huit diffs ont ete commites dans `b635c369` (parent `cd02eef5`, auteur/committer Git `Codex <codex@openai.com>`, 2026-10-23 11:43:32+02:00, message `Fix WP-C02-AT preflight result capture lifecycle`). Je n'ai effectue aucun commit ni ecriture dans ce worktree. Git identifie le committeur configure, pas l'agent ou l'autorisation Owner qui a declenche l'operation. Au dernier controle, les huit chemins etaient propres contre ce nouveau HEAD; les 525 hashes du manifeste natif restaient tous conformes. Les lignes du tableau donnent les deltas du commit `cd02eef5..b635c369` et l'historique juste avant cette edition.

| Chemin relatif exact | Diff | Historique/auteur disponible et provenance | Incidence / conflit probable |
|---|---:|---|---|
| `qualification/0_2_12/test_wpc02_at_docker_contract_static.ps1` | +25/-4 | Base `cd02eef5`, Codex, 2026-10-23 11:10; mtime local 11:40. Attend campagne AT `...-08` et build `...-05`; ajoute assertions d'ordre capture/attente/copie/ack. Edits ensuite inclus dans b635 (auteur Git Codex; acteur non identifie). | Test du worker Docker; hors manifeste AR. Suit probablement BB. |
| `qualification/0_2_12/test_wpc02_at_launcher_capture_integration.ps1` | +27/-4 | Base `fe67a843`, Codex, 11:09; mtime 11:36. ID AT `...-08`; ajoute marqueur de disponibilite et fixtures de resultat/ack du shim Docker. | Test d'integration transport Docker; hors AR; probablement BB. |
| `qualification/0_2_12/test_wpc02_at_worker_contract.py` | +99/-3 | Base `fe67a843`, Codex, 11:09; mtime 11:38. Ajoute tests du hash de resultat, noms autorises et acknowledgement. Fixtures contiennent `wp-c02-az-unit-01`. | Code de test AT; les fixtures AZ ne prouvent pas une execution AZ. Aucun lien direct BA observe. |
| `qualification/0_2_12/wpc02_at_bounded_capture.cs` | +4/-1 | Base `721e3e53`, Codex, 08:59; mtime 11:32. Rend le flux resultat lisible pendant capture et flush le marqueur. | Capture de resultats Docker; hors AR; potentiellement partage avec campagne BB. |
| `qualification/0_2_12/wpc02_at_build.ps1` | +2/-2 | Base `fe67a843`, Codex, 11:09; mtime 11:40. Verrouille branche `codex/wp-c02-bb-result-artifact-20261023`, digest source attendu `25e3dcd1cf274baeacdcf5697cb7709d42e3c25b9e16fb9e607f4e470c1b16ad`, campagne build `wp-c02-at-build-20261023-05`. | Provenance probable BB explicite; conflit si utilise depuis AR/AZ/BA. |
| `qualification/0_2_12/wpc02_at_docker_worker.py` | +94/-8 | Base `fe67a843`, Codex, 11:09; mtime 11:40. Verrouille BB et ajoute limites d'ack 4096 octets/60 s et publication verifiee. | Worker d'execution Docker; hors AR; risque de conflit direct avec le travail BB. |
| `qualification/0_2_12/wpc02_at_freeze_manifest.ps1` | +3/-2 | Base `fe67a843`, Codex, 11:09; mtime 11:40. Verrouille branche/digest BB et ID campagne AT `...-08`, ajoute les limites d'ack. | Construction du gel Docker BB; hors AR; conflit probable avec toute preparation AZ/BA. |
| `qualification/0_2_12/wpc02_at_guarded_docker.ps1` | +162/-37 | Base `fe67a843`, Codex, 11:09; mtime 11:40. Verrouille branche/digest BB et ID `...-08`; remplace capture simple par lancement attache, handshake resultat/ack et copie bornee. | Orchestration Docker AT; hors AR; conflit le plus eleve avec le travail BB. |

Au premier suivi de refs, le worktree `wp-c02-bb` etait sur `cc162482`; son merge-base avec `b635c369` etait `b635c369`. Au dernier controle, le worktree BB avait avance a `bcc17755e92acd62710783918e696acdbfc07d99` et etait sale: cinq fichiers WP-C02-AT modifies et six artefacts natifs AR non suivis (manifest, baseline, rapport, deux scripts et test). Je n'ai ni ouvert leurs diffs ni ecrit dans ce worktree, car il peut appartenir a une campagne parallele active. La presence de ces artefacts rend le risque de conflit concret; leur auteur et leur contenu ne sont pas attribues ici.

Les quatre scripts de build/worker/freeze/launcher nomment explicitement la branche BB et la campagne `...-08`; le digest de source attendu est un digest de 64 hex (pas un OID Git). Les tests `...-08` et les changements du protocole d'ack sont coherents avec ce theme. Les references AZ sont des fixtures de test. Aucun lien direct vers BA n'apparait dans les huit diffs inspectes. La branche BB est maintenant visible et partage b635 comme merge-base dans un instantane de refs; cela donne un lien Git direct entre ce changement AT et la ligne BB. L'auteur Git de b635 est Codex, mais cela n'attribue pas l'action a un agent ou a l'Owner. L'etat BB changeait encore pendant l'audit; son contenu local n'a pas ete inspecte. Aucune archive ni verdict Docker AZ/BA/BB n'a ete modifie. Les huit fichiers ne sont pas dans le mapping natif partage ou candidat et n'affectent pas les equations AR. Les utiliser dans une autre campagne pourrait faire echouer les gardes branche/ID; ils ont ete laisses intacts et exclus du candidat.

## 3. Remediation candidate isolee

- Worktree: `C:/Users/fari/Documents/projet/SAFRAN/.codex-worktrees/wp-c02-n01-remediation`, cree detache de la base; les huit diffs AT partages n'ont pas ete copies.
- HEAD de base: `cd02eef59d3345643d617035be96190811d370bb`; tree OID de base: `4d24fbebcc4c08f63d17f41c693394a01d040bd5`.
- Le test scientifique natif reste byte-identique au fichier precedent (`d04f3c4d315adcc7d0d3f9d176b8afdbc4942d1cd8f9069bf513fe8b34e54451`). Les hashes du plan AR, protocole AR, baseline M1-M3 et fixture AJ sont conserves.
- Seuls changements de code: le runner recalcule et verifie l'agregat source; un nouveau test unitaire couvre la formule, les 526 hashes individuels, l'agregat falsifie et les portes pytest. Aucun changement d'equation, maillage, contact, seuil, condition limite ou chemin de solveur.
- Nouveau source set: 526 entrees; SHA-256 `511ce75d8b45deb5f760a22ea3cfe937cef2c8c04aa00cf4b126538980ec1e6b`.
- Nouveau manifeste SHA-256 `2c37b55bf5364b8542319ea07e3c2dc05a9397bcf4e40fa88304f5c32f1fbaf9`; schema v2, contrat d'agregation explicite, `source_file_count=526`, archive distincte `qualification/0_2_12/wpc02_ar_native_campaign_n01_20261023_01`.
- Rapport de preparation candidat et copie du rapport historique sont hors du jeu source hash; leurs empreintes sont independantes. Le candidat est staged mais non commite. Son tree OID d'index est calcule et communique hors du tree pour eviter une reference circulaire.

## 4. Controle preparatoire (sans FEM)

- `tests/unit/test_wpc02_ar_native_manifest_contract.py`: `6 passed in 1.95s`.
- Nodeids `test_wpc02_ar_native_m4` et `test_wpc02_ar_native_m5`, avec GO Owner absent: `2 skipped in 1.42s`. La porte skippe avant `_scenario_diagnostic`; aucun appel `LinearStaticSolver.solve`.
- AST parse: runner, rapporteur, test scientifique et test de contrat, tous reussis.
- Versions: Python 3.13.1; NumPy 2.2.6; SciPy 1.15.2; pytest 8.4.1; psutil 7.2.2; threadpoolctl 3.6.0.
- `git diff --cached --check`: reussi apres staging du candidat.
- Aucun calcul FEM, assemblage, `solve_model`, Docker, collect ou retry. Les deux scenarios restent desactives.

## 5. Findings et decision Owner

1. P1 du gel refuse: reference rapport/manifeste obsolete demontree et corrigee dans ce candidat, mais gel historique non reecrit; origine du mapping `c0a29...` non archivée.
2. Provenance des huit edits AT: auteur local inconnu; origine probable BB. Le conflit potentiel reste ouvert jusqu'a confirmation du proprietaire de cette campagne.
3. Nouvelle revue independante du manifeste candidat: non effectuee. La revue independante anterieure a conclu FAIL et n'est pas reutilisee comme approbation de ce nouveau gel.
4. Recommandation: Owner peut autoriser une revue independante du candidat exact, apres prise en compte du statut des huit edits AT. Toute modification post-revue invalide les identites.
5. Conditions exactes d'un futur RUN FEM: revue independante favorable du manifeste SHA-256 `2c37b55bf5364b8542319ea07e3c2dc05a9397bcf4e40fa88304f5c32f1fbaf9`; candidat/sources inchanges; puis autorisation Owner separee explicite `GO-RUN-FEM-NATIF` liee a ce SHA exact. L'execution conserve un seul essai M4 puis M5, 900 s et 4 GiB RSS par scenario, un thread numerique, sans retry. Aucun GO Docker ou collect n'est inclus.

Etat final: candidat `PREPARED_PENDING_INDEPENDENT_REVIEW`; resultats scientifiques `NOT_ACQUIRED`; gel precedent `FAIL_CLOSED`; aucun claim Docker-equivalent, `VERIFIED_BOUNDED`, merge ou publication.
