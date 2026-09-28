# WP14 G06/G08 — Résultats R2.1 et feuille de route

## Conclusion

R2.1 corrige et vérifie la cohérence automatisée du registre documentaire et de ses builds. Les six commandes G06 gelées ont réussi sur le commit exécuté. Cela ne clôt pas G06 : l’analyseur de readiness reste bloqué parce que 92 des 111 dossiers du périmètre de revue n’ont pas de valeurs complètes et attribuables pour `reviewer` et `approver`. Ces valeurs ne peuvent pas être inventées par l’outil.

G08 n’a pas été exécuté : aucun workflow GitHub Actions n’a été déclenché. WP14 reste donc `HOLD`, `0/1` point officiel, total machine `95/100` inchangé.

## Provenance et périmètre

- Branche de travail : `codex/wp14-g06-g08-remediation`.
- Commit testé (`EXECUTION_SHA`) : `16f3199154f92546bda228c6dafbe60c5bbf9f7b`.
- Commit des corrections : `3337107aca2587166e1c649a481892eba1c343f5`.
- Contrat R2.1 : `qualification/0_2_9/wp14/wp14_g06_g08_remediation_r2_1_contract.json`.
- SHA-256 du contrat : `d378e500726f31486e89aec2229c7ff18a6fff1ac952a9b843db269ef73e1e02`.
- Les commandes ont commencé avec un arbre propre sur `EXECUTION_SHA`. Les seuls changements depuis la base sous `src/` : aucun.
- Les résultats R2 antérieurs, dont les échecs, restent historiques et inchangés.
- Rapport machine et journaux R2.1 : `wp14_g06_g08_r2_1_execution.json` et `logs/` dans ce répertoire.

## G06 — registre, build et readiness

| Gate distinct | Résultat R2.1 | Preuve / réserve |
|---|---|---|
| Couverture du registre | PASS, 589/589 documents contrôlés ; 0 manquant, extra ou invalide | `test_docs_generation.py` ; normalisation des alias de statut |
| Présence des champs de schéma | PASS : `revision`, `applicable_version`, `reviewer`, `approver` sont présents | La présence d’une clé n’atteste pas qu’une revue a eu lieu |
| Génération documentaire | PASS, code 0 ; 700 artefacts annoncés | Log `02-build-docs.log` |
| Tests documentaires | PASS, 56 passés, 6 ignorés | Log `03-pytest-documentation.log` |
| Build MkDocs strict | PASS, code 0 ; 40 messages INFO, aucun WARNING/ERROR | Les liens vers des preuves hors site restent informatifs et non bloquants dans cette configuration |
| Tests ciblés de génération | PASS, 30 passés, 2 ignorés | Log `05-docs-generation-targeted.log` |
| Tests packaging | PASS, 13 passés | Log `06-packaging-targeted.log` |
| Readiness des métadonnées de revue | **BLOCKED : 19/111 complets, 92/111 incomplets** | `review_readiness.json`, SHA-256 `cd03ada03a1a84990b0c65fe69749b2651ec3472e5579e539466af639d3e52b7` |

Le dernier point est un blocage de gouvernance, distinct de la correction du registre. Les champs vides ne peuvent pas être remplacés par `N/A`, un nom générique ou une approbation déduite. Les statuts `owner_approved` ne doivent être utilisés que lorsque l’approbation existe réellement.

### Actions G06 restantes

1. Examiner les 92 entrées incomplètes et confirmer qu’elles appartiennent bien au périmètre de revue gelé de 111 documents.
2. Pour chaque dossier conservé dans ce périmètre, obtenir du responsable réel les noms/identifiants de reviewer et approver et la décision de revue correspondante. Les décisions groupées sont possibles seulement si elles listent sans ambiguïté chaque document couvert.
3. Si certains documents n’exigent pas de revue, demander une décision Owner prospective qui modifie explicitement le périmètre et justifie chaque exclusion ; ne pas réduire le dénominateur par filtre technique.
4. Enregistrer les décisions authentiques dans les métadonnées, geler un contrat suivant lié au nouveau commit, puis régénérer `review_readiness` et rejouer les commandes G06 que ce nouveau contrat exige.
5. N’attribuer aucun statut global G06 PASS avant que la règle R1 applicable aux métadonnées de revue soit satisfaite ou révisée explicitement par l’Owner.

## G08 — matrice plateformes

Statut actuel : `NOT_RUN`, **0/4 legs**. `.github/workflows/quality.yml` définit `standard-baseline` pour Ubuntu et Windows, Python 3.10 et 3.13. Aucun run, identifiant de workflow ou SHA testé n’existe dans ce dossier.

Le job comprend l’installation de la baseline, Ruff, mypy progressif, tests unitaires/intégration avec couverture de branche et seuil de couverture, gate P0, compileall et vérifications rapides. Un résultat local Windows/Python 3.13 ne remplace aucun des trois autres legs.

### Actions G08 restantes

1. Décider du déclenchement distant : `workflow_dispatch` sur une référence exactement liée au commit candidat, ou PR vers `main` avec vérification explicite du SHA réellement testé. Une exécution PR qui teste un commit de merge ne doit pas être présentée comme testant le SHA tête sans le vérifier.
2. Autoriser séparément, si nécessaire, le push de la branche candidate ou la création d’un PR. Aucun push/PR n’a été créé dans R2.1.
3. Archiver le run ID, le SHA réellement checkouté, les quatre résultats de jobs, leurs logs et artefacts de couverture. G08 ne passe que si les quatre legs requis sont terminés avec succès sur le candidat admissible.
4. En cas d’échec, conserver le log et corriger la cause réelle. Toute modification de code impose un nouveau SHA candidat et une nouvelle liaison contractuelle ; ne pas réutiliser un résultat d’un autre SHA.

## Autres gates et gouvernance

- G03, G04 et G05 n’ont pas été rejoués par R2.1 ; leurs échecs précédents restent ouverts, non effacés par le succès G06.
- G09 (publication, tag et clôture release) reste Owner-gated.
- Aucun solve, suite complète, changement mécanique, seuil, ledger, point, push, tag ou publication n’a été effectué.
- Les sorties générées volumineuses ont été archivées hors Git avec inventaires et SHA-256 ; elles ne sont pas incluses dans le paquet versionné.

## Décision / prochaine étape

Les corrections du registre et du rendu documentaire sont prêtes à être intégrées localement. Pour fermer WP14, il reste nécessaire de traiter séparément les 92 métadonnées de revue, d’exécuter la matrice G08 sur le SHA autorisé, puis de reprendre G03–G05 et G09 selon leurs contrats. Jusqu’alors : `WP14 = HOLD`, points officiels `0/1`, total officiel inchangé `95/100`.
