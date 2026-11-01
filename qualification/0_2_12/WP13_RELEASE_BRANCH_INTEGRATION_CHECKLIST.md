# WP13 — checklist d’intégration de la candidate 0.2.12

Date de contrôle : 2026-11-01  
PR #114 : <https://github.com/emptiesvoid-cloud/QF_solver/pull/114>  
Branche WP13 : `codex/wp13-release-engineering-20261031`  
Destination visée : `emptiesvoids-cloud/0.2.12` · base observée `ab137051d920d7fa9aae9a3012a48b2b26e2198b`

## Intégrité et traçabilité

| Contrôle | État | Preuve / action restante |
| --- | --- | --- |
| PR #114 | PASS — PR ouverte | GitHub rapporte base `emptiesvoids-cloud/0.2.12` et la branche source WP13. Les préflights et six smoke tests ont été exécutés sur le HEAD contrôlé `d0a3df9bd7265429d433b44560c0cd0606aedbf0`; le commit documentaire de ce rapport avance ensuite la tête de la PR. |
| Source du package v7 | PASS | Blobs distribués reconstruits depuis `7a78cc673da2abb7c3d0afd6cabd378aa327f424`; contrat prospectif lié à cette identité. |
| Contrat v7 | PASS | `f466a5b901fe77755e45d18e3831ad72be1e1381`, SHA-256 `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43`. |
| Smoke controller v7 | PASS — compilé et lié aux nouveaux artifacts | `c3c10f2f30c82550261eeb436df8468614c742e6`, SHA-256 `cba01759b5b3b1cc41cfcc23c405adef55a6cccdaffcec85ac4a057b8b7e2ed7`. |
| Modifications WP13 depuis le HEAD initial | PASS — traçables | `7a78cc6` documentation/structure, `f466a5b` contrat v7, `c3c10f2` bindings du controller; rapports finaux et matrice sont ensuite commités sur la même branche. |
| Working tree pendant les smoke tests | PASS — propre | `git status --porcelain` était vide sur le HEAD d0a3 pendant les préflights et les exécutions. Les artefacts, environnements, manifestes, rapports bruts et ledgers sont hors dépôt. Les seuls changements de ce commit sont les rapports publics expurgés. |
| Conflits avec la destination | NOT_RUN | Aucun merge simulé ni merge réel n’est inclus dans ce mandat; vérifier l’état PR GitHub avant toute intégration ultérieure. |

## Documentation, structure et surface publiée

- README global maintenu comme porte d’entrée de toutes les grandes capacités, installations, exemples, interfaces et limites; 0.2.11 reste identifié comme release publiée et 0.2.12 comme candidate.
- Site officiel `https://qfsolver.org/`; pages d’entrée, projet, versions, roadmap et capacités vérifiées. Les routes spécialisées sont reliées aux fichiers `docs/` ou à une cible versionnée équivalente.
- Build MkDocs strict, 55 cibles existantes; `docs/ai/**` reste exclu du site.
- 106 liens README vérifiés : 90 cibles locales/ancres valides et 16 URL HTTP 200. Huit pages techniques modifiées ont été rescannées; 753 autres documents ont été réutilisés seulement après identité de contenu prouvée.
- Rapports d’audit, de README et de reconstruction ne contiennent pas de chemins privés. Les outputs du package et du préflight restent hors dépôt.
- Quatre fichiers de rapports d’opérations locales ont quitté la racine vers une archive privée vérifiée; aucun commit ancien n’a été réécrit. Aucun déplacement massif de `qualification/`, manifests, ledgers ou rapports scientifiques n’a eu lieu.

## Distribution et qualité

- Wheel v7 et sdist normalisée reconstruits deux fois indépendamment; hashes identiques entre reconstructions et Twine PASS.
- Installations fraîches Windows/Python 3.13.1 depuis wheel et sdist; imports, version, CLI et `pip check` PASS.
- Six contrôles `check-mesh` TET4/BEAM2/MITC4 ont passé sans assemblage/résolution.
- Préflight principal et synthétique `PASS_NO_FEM`; le ledger synthétique est séparé et contient deux événements, sans réservation réelle ni FEM. Puis les six smoke tests autorisés ont passé `EXECUTION_PASS` et `NUMERICAL_ORACLE_PASS`, sous le contrôleur officiel et depuis les packages installés. Voir [`WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md`](WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md); aucune septième tentative.
- Matrice CI de politique Owner PASS sur le commit `698e858e79d6b6ded7cdf764f5e0dd26c710c301`, run #41328516423. Les changements documentaires ultérieurs ont eu des contrôles ciblés; aucune deuxième exécution complète de la matrice n’a été lancée.
- G03 reste `FAIL_PRESERVED`; revue juridique indépendante `NOT_ACQUIRED`; les conclusions négatives et non acquises de WP12 demeurent inchangées.

## Restrictions de cette intégration

- **Aucune fusion** dans `emptiesvoids-cloud/0.2.12`, `main` ou une autre branche.
- Aucun tag `v0.2.12`, GitHub Release, téléversement PyPI, dépôt Zenodo ou DOI de version.
- Aucun déploiement ou synchronisation du site officiel.
- Aucun ledger, manifeste scientifique ou résultat WP12 modifié; aucune campagne FEM indépendante exécutée.

## Décision de sortie

La branche contient une candidate documentaire et d’artefacts cohérente, et les six smoke tests installés v7 passent dans leur portée. La fusion/release reste bloquée par les gates indépendants ouverts, dont G03 et la revue juridique. Le verdict global demeure **`WP13_PARTIAL_OR_BLOCKED`**; le statut smoke limité est **`WP13_V7_INSTALLED_PACKAGE_SMOKES_PASS`**, sans qualification scientifique globale.
