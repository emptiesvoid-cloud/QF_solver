---
doc_id: DOC-029-WP14-R1-REPORT
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
---

# WP14 R1 — rapport de qualification release

Contrat : [`QF-029-WP14-RELEASE-QUALIFICATION-R1`](wp14-r1-release-qualification-contract.md)

Record machine : [`wp14_r1_final.json`](../../../qualification/0_2_9/wp14/wp14_r1_final.json)

Branche candidate : branche de qualification WP14

Source gouvernante/exécutée : `b2485f98260c7ca9892997eefa3a327637d83cd3` / `2b27b1bc7d26f5e599c68465b7f13e80f06528a8`

SHA-256 du contrat : `f34d6db9d2a3fbd882ae182b9986c2fc7a9e48ce98e77645aa2f6af3b91aa6ac`

## Verdict

**`WP14_STATUS = HOLD_OWNER_REVIEW`**. Le dossier est reproductible et prêt à
la revue Owner, mais la release n’est pas qualifiée : les gates qualité,
engineering, documentation et hygiène de publication échouent. Aucun point
WP14 n’est attribué par ce run.

```text
WP14_CANDIDATE_STATUS = HOLD
WP14_CANDIDATE_POINTS = 0/1
WP14_OFFICIAL_POINTS = 0/1
OFFICIAL_TOTAL_BEFORE = 95/100
OFFICIAL_TOTAL_AFTER = 95/100
PRODUCTION_SOURCE_CHANGED = NO
THRESHOLDS_CHANGED = NO
WP14_BRANCH_PUSHED_AFTER_QUALIFICATION = YES
WP14_INITIAL_PUSH_SHA = `3e41cbc315b6790279199ef3251e6d3122a60c12`
MERGE_OR_TAG_OR_PUBLICATION = NO
```

## Ce qui passe

- Provenance : le contrat R1 est prospectif et gelé depuis le SHA gouvernant
  exact. La branche de qualification ne change aucun fichier de mécanique de
  production ni seuil solver.
- Ledger : `progress.json`, `progress.md` et la décision
  `OD-029-WP13-R2.1-01` concordent sur `95/100`, WP14 `0/1` et l’allocation
  active WP13/WP14/WP15 `1/1/2`. La roadmap historique n’a pas été réécrite.
- Mypy ciblé : PASS sur 4 fichiers. Couverture P0 : 37 passés, 2 ignorés ;
  couverture `errors.py` 100 %, `traceability.py` 92,16 %. Compileall et les
  deux vérifications rapides PASS.
- Vérification MITC4 complète : PASS. Tests benchmark gelés : 23 passés,
  1 ignoré.
- MkDocs strict : code retour 0, zéro warning et zéro erreur. Il reste 31
  avis informatifs de références hors site et un groupe d’avis de navigation.
- Tests packaging : 13 passés. Wheel et sdist construits, puis installation
  et imports vérifiés dans une cible temporaire isolée.
- Registry de capacités : PASS, 33 entrées.

## Gates bloquants

| Gate | Résultat | Constat |
|---|---|---|
| Ruff | FAIL | 22 diagnostics, tous dans des fichiers inchangés depuis la base gouvernante. |
| Suite standard | FAIL | 2 912 passés, 23 échoués, 107 désélectionnés ; couverture 85,74 %. |
| Profil engineering | FAIL | 3 278 passés, 31 échoués, 14 ignorés, 187 désélectionnés. MITC4 seul passe. |
| Génération docs engineering | FAIL | `DOC-029-WP04-F-001` n’a pas de métadonnée reviewer ; aucune valeur n’a été inventée. |
| Tests documentation | FAIL | 42 passés, 1 échoué, 6 ignorés. Le test du verdict PDF attend `0 finding`, alors que l’audit de confidentialité trouve des problèmes. |
| Audit arbre public | FAIL | 4 292 fichiers parcourus, 5 540 constats dans 276 fichiers : chemins de poste/environnement, références de flux internes et un marqueur d’adresse. Les extraits et adresses ne sont pas recopiés ici. |
| Audit archive Git | FAIL | 5 409 entrées examinées, 5 538 constats. |
| Audit historique Git | WARNING | 2 161 commits accessibles, 1 351 marqueurs d’identité/chemin. Aucun historique n’a été réécrit. |
| Readiness globale | NOT_READY | Les contrôles de gouvernance, licence, changelog et worktree propre passent ; hygiène publique, archive, historique et version/tag ne passent pas. |

La suite standard révèle également des échecs de contact frictionnel, de
contrat arc-length WP06, de diagnostic Newton WP01, de validation de schéma,
de vocabulaire publié et des tests de maturité/ledger historiques. Le profil
engineering ajoute des échecs de convergence WP04-C et des incohérences
d’évidence WP04/WP05/WP09. Les noms exacts des tests, sorties et hashes sont
dans les journaux externes référencés par le record machine ; aucun échec n’a
été masqué ou supprimé.

## Paquet construit

La wheel et la sdist s’installent, mais leurs métadonnées déclarent toujours
**0.2.8**. Elles ne constituent donc pas un artefact publiable en 0.2.9.
Leur construction ne vaut ni changement de version ni autorisation de
publication. Les SHA-256 des deux fichiers figurent dans le record machine.

## Intégrité des sorties de campagne

Les tests et générateurs ont produit environ 4,94 Go de sorties temporaires.
Ces sorties ont été préservées hors du worktree avant de restaurer les
artefacts historiques aux blobs Git d’origine. Un JSON WP04-C1 modifié par
une commande de vérification a été capturé séparément puis restauré ; il n’est
pas présenté comme une nouvelle preuve. Le worktree est propre après cette
restauration.

## Décisions Owner requises

1. Définir si et comment assainir les chemins présents dans la surface publique,
   sans réécrire silencieusement les preuves historiques.
2. Décider du traitement des marqueurs d’identité/chemin dans l’historique ;
   aucune réécriture n’a été faite.
3. Assigner le triage des échecs standard et engineering, notamment contact,
   arc-length et les gates WP04/WP05/WP09.
4. Fournir ou autoriser la métadonnée reviewer manquante WP04-F ; elle ne peut
   pas être inventée par ce run.
5. Si une publication 0.2.9 est souhaitée, autoriser séparément la version
   package, le changelog/citation, le tag et les étapes de publication.

```text
OWNER_REVIEW_STATUS = REQUIRED
OWNER_ACCEPTS_WP14 = PENDING
OWNER_AWARDS_WP14_POINTS = PENDING (maximum 1/1 after all frozen gates close)
LEDGER_UPDATE = NOT_AUTHORIZED / NOT_PERFORMED
PUSH_DURING_QUALIFICATION = NOT_PERFORMED
POST_QUALIFICATION_BRANCH_PUSH = OWNER_REQUESTED_AND_PERFORMED
MERGE = NOT_PERFORMED
PUBLICATION = NOT_AUTHORIZED / NOT_PERFORMED
NEXT_STEP = OWNER DECISION ON REMEDIATION SCOPE; THEN RERUN FAILED FROZEN GATES
```

Le push de la branche gouvernante effectué séparément était déjà à jour ;
cette branche WP14 demeure locale et non fusionnée afin de s’arrêter à la
revue Owner.
