# WP13 G03 — Rapport de remédiation et de limites

Date : 1 novembre 2026

PR : [#114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
État G03 : **FAIL_PRESERVED**

## Résumé

La remédiation prospective retire de l’archive source deux sélections qui n’y sont pas nécessaires : le fichier `AGENTS.md` racine et les sorties JSON sous `docs/generated/results/`. Le contenu Markdown généré, référencé par la documentation, reste inclus. Le test ciblé de règle et l’inspection `git check-attr` confirment ce périmètre; l’audit complet confirme que ces chemins interdits ne sont plus exportés.

Cette correction ne supprime pas les commits qui ont contenu ces chemins. L’audit complet de contenu de l’archive reste lui aussi en `FAIL`, et le préfiltre d’historique demeure en `WARNING`; le critère G03 n’est donc pas satisfait. Le statut historique reste **FAIL_PRESERVED** malgré le succès du contrôle ciblé de sélection des chemins.

## Chemins de l’archive prospective

Les règles ajoutées dans `.gitattributes` sont :

```gitattributes
/AGENTS.md export-ignore
docs/generated/results export-ignore
docs/generated/results/** export-ignore
```

La règle de racine est ancrée afin de ne pas filtrer d’éventuels fichiers `AGENTS.md` imbriqués. L’inventaire du dépôt contient actuellement un seul chemin suivi de ce nom, à la racine. Vérifications observées :

| Chemin | `export-ignore` | Résultat attendu |
|---|---|---|
| `AGENTS.md` | set | exclu de `git archive` |
| `docs/generated/results/large_block_documentation.json` | set | exclu de `git archive` |
| `docs/generated/mitc4_locking_results.md` | unspecified | conservé |
| `docs/AGENTS.md` et `qualification/0_2_12/AGENTS.md` | unspecified | aucune règle d’exclusion héritée |

Le test `tests/unit/test_public_release_audit.py::test_archive_rules_exclude_local_and_working_evidence_trees` a réussi après l’ancrage (1 passé, 0,65 s lors de la dernière exécution). Ruff, `py_compile` et `git diff --check` ont également réussi pour le changement ciblé.

## Audit de l’archive et du contenu source

Le seul scan complet d’archive de cette phase a utilisé `scripts/audit_release_archive.py --ref HEAD`, `attribute_source=worktree`, sur le snapshot source `3ced76d841402fc53e64545ebc37acb8361fa369`. Le processus d’archivage a démarré avec la règle non ancrée `AGENTS.md export-ignore`; la règle a ensuite été resserrée à `/AGENTS.md`. Comme le dépôt ne contient qu’un seul `AGENTS.md` suivi et qu’il est à la racine, la sélection effective des chemins est identique. Le scan a rendu **FAIL** : 6 711 fichiers, 7 060 constats répartis sur 618 chemins. Il n’a relevé aucun `forbidden_path`; les règles `export-ignore` ont donc corrigé les deux expositions de chemin visées. Les constats de contenu restants sont : `internal_workflow` 822, `private_environment` 3 130, `workstation_path` 3 098 et `private_email` 10. Aucun extrait ni contenu d’identité n’est repris ici.

L’échantillonneur a mesuré 17 min 20,44 s murales (début 2026-11-01 18:23:00.9026960 UTC, fin 18:40:21.3434183 UTC), 1 030,03 s CPU et 148,29 Mio de RSS maximale. La lenteur vient du passage d’analyse de contenu sur les 6 711 fichiers exportés. Le résultat JSON, conservé hors dépôt, mesure 2 948 773 octets. Ce scan n’est pas exécuté une seconde fois.

Le scan complet `audit_public_release.py` du contenu source suivi n’a pas été lancé : les 7 060 constats d’archive et l’avertissement historique établissent déjà que G03 ne peut pas passer; son exécution globale, coûteuse, ne lèverait aucun de ces deux bloqueurs. Les scans de sélection v6 restent acquis pour leurs 585 chemins de paquet et 773 chemins documentaires inchangés. La liste de chemins de l’archive finale sera comparée rapidement après commit, sans refaire l’analyse complète du contenu.

## Historique Git

Le préfiltre historique relu pour cette phase indique `WARNING` sur 2 587 commits atteignables et 1 429 événements : 1 346 constats de métadonnées d’auteur, 59 événements de chemin `AGENTS.md` et 24 autres événements de chemins sensibles. Ces catégories comprennent des sorties de résultats WP12 et des chemins de résultats de solveurs externes. Les données d’identité et extraits de chemins ne sont pas reproduits dans ce rapport.

Le préfiltre n’est pas une preuve de nettoyage de l’historique. `export-ignore` agit sur les archives Git produites avec les attributs du dépôt; il ne retire pas les fichiers des commits, ne modifie pas l’historique atteignable et ne contrôle pas l’archive source créée automatiquement par l’hébergeur. Aucune réécriture de l’historique n’a été faite ni autorisée.

## Décision et limites

**G03 = FAIL_PRESERVED.** La correction d’archive est acquise dans sa portée de sélection. Elle ne suffit pas à lever le critère du dépôt complet en présence des événements de l’historique, et le statut ne sera pas reclassé à partir des seuls contrôles des distributions sélectionnées.

Les suites possibles d’une décision Owner ultérieure sont de conserver l’historique actuel avec G03 en échec, ou de demander une revue séparée d’un historique public propre tout en conservant l’historique existant comme archive contrôlée. La seconde option demanderait un mandat distinct. Ce rapport n’autorise pas de réécriture, de fusion, de tag ni de publication.

Les résultats WP12, les manifestes et les ledgers n’ont pas été modifiés.
