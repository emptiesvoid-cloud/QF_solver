# WP13 — rapport de reconstruction du candidat d’artefacts v7

- Date : 2026-11-01
- Dépôt : `emptiesvoid-cloud/QF_solver` · PR #114
- Branche : `codex/wp13-release-engineering-20261031`

## Identités gelées

| Élément | Identité |
| --- | --- |
| HEAD initial du mandat | `357b4b5398c1d3e5059e0a1049f8494f4096f13e` |
| Source sélectionnée v7 | Commit `7a78cc673da2abb7c3d0afd6cabd378aa327f424` |
| Contrat prospectif v7 | `QF-0212-WP13-SELECTED-CANDIDATE-20261101-07`; SHA-256 `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43` |
| Commit du contrat | `f466a5b901fe77755e45d18e3831ad72be1e1381` |
| Commit de la candidate du smoke controller | `c3c10f2f30c82550261eeb436df8468614c742e6` |
| HEAD de préflight | `c3c10f2f30c82550261eeb436df8468614c742e6` |
| Baseline de la branche de destination | `ab137051d920d7fa9aae9a3012a48b2b26e2198b` |
| Version package candidate | `0.2.12`; la version publique reste `0.2.11` |

La preuve v6 est conservée historiquement, mais ne s’applique pas aux nouveaux octets sélectionnés : README, `pyproject.toml`, `CITATION.cff`, politique MkDocs et liens documentaires ont changé. V7 lie les blobs exacts de la source ci-dessus. Aucun code du solveur, oracle, seuil, entrée scientifique, manifeste de qualification ni résultat WP12 n’a changé dans cette consolidation.

## Reconstruction et reproductibilité

Environnement commun : Windows 10, Python 3.13.1, `build 1.5.0`, `setuptools 82.0.1`, `wheel 0.47.0`, `twine 7.0.0`, `SOURCE_DATE_EPOCH=1793444684`. Les builds A et B ont utilisé deux dossiers de sortie neufs et indépendants; la vérification de source a matérialisé les blobs sélectionnés du commit v7.

| Résultat | Reconstruction A | Reconstruction B | Verdict |
| --- | --- | --- | --- |
| Wheel `qf_solver-0.2.12-py3-none-any.whl` | 1 690 080 octets · `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518` | 1 690 080 octets · même SHA-256 | PASS, octets identiques |
| Sdist brute `qf_solver-0.2.12.tar.gz` | 1 321 283 octets · `1734073c361617160adc5474894665236f929d71ca6df092f56a3ac3bc71cd65` | 1 321 293 octets · `317bddd118e32e1c1a04b9d9b79b87d07a8491a46e33683c6104e800b78e30bb` | Les enveloppes gzip brutes diffèrent; la comparaison contrôlée porte sur la sdist normalisée. |
| Sdist normalisée v7 | 1 295 214 octets · `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174` | 1 295 214 octets · même SHA-256 | PASS, octets normalisés identiques |
| Contrôle d’archive | 585 fichiers sélectionnés, 501 modules wheel; zéro constat dans wheel (585 fichiers) et sdist (593 entrées) | Mêmes comptes et mêmes contenus sélectionnés | PASS |
| Twine | Wheel, sdist brute et sdist normalisée : PASS | Wheel, sdist brute et sdist normalisée : PASS | PASS |

Les résultats enregistrés par le runner après le gel des sources sont respectivement 51,36 s et 47,82 s; le sous-processus `python -m build` a pris 24,40 s et 22,82 s. Le runner ne chronomètre pas sa matérialisation Git préalable et ne mesure ni CPU ni RSS; ces métriques restent `NOT_ACQUIRED`. Aucun nouveau scan complet de l’archive Git n’a été lancé.

Le candidat sdist retenu pour les contrôles d’installation et le manifeste smoke est la sdist **normalisée** de 1 295 214 octets, hash `56c607…9174`. La sdist brute A/B n’est pas substituée silencieusement à cette identité.

## Installation fraîche, métadonnées et interfaces

Deux environnements séparés et vierges ont résolu les dépendances locales du wheel et de la sdist normalisée sous les contraintes de `requirements/baseline-standard.txt`.

| Contrôle | Wheel | Sdist normalisée |
| --- | --- | --- |
| Rapport `pip install` | SHA-256 `12c6d1a755d19a53f0418f73b3beda2e15f413716b70d0085c01723c4086ee91` | SHA-256 `fb2c839745bcc98f0ab439bd2c07243f4a4b25cf5cdd88df94b758930ee25755` |
| Durée de résolution / installation | 49,506 s | 50,661 s |
| Version installée / Python / OS | `0.2.12` / 3.13.1 / Windows | `0.2.12` / 3.13.1 / Windows |
| Origine imports | `solveur`, `qf_solver` et CLI sous l’environnement installé; fichiers d’exemples concordants avec les blobs v7 | Même vérification depuis l’environnement sdist |
| `pip check`, CLI `--version`, CLI `--help` | PASS | PASS |
| `check-mesh` TET4 `tet4_static.json` | PASS · 1,732 s | PASS · 1,784 s |
| `check-mesh` BEAM2 `beam2_cantilever.json` | PASS · 1,679 s | PASS · 1,664 s |
| `check-mesh` MITC4 `mitc4_shell_static.json` | PASS · 1,630 s | PASS · 1,723 s |

Ces six commandes valident le chargement du modèle et le contrôle du maillage seulement; elles n’assemblent ni ne résolvent un modèle. Les rapports JSON wheel/sdist des trois exemples sont identiques par hash. La vérification de package no-deps a aussi confirmé 501 modules installés, les trois launchers versionnés et le refus attendu de `verify-all` hors checkout Git; aucun processus solveur n’a été lancé.

## Confidentialité, documentation et provenance

Le scan du package v7 a trouvé zéro constat dans les 585 fichiers sélectionnés et dans les 593 entrées de sdist. Pour la documentation publique, le scan v4 précédent (`wp13_candidate_public_scope_scan_20261031_v4.json`, SHA-256 `11ddf8812d0b810502a36a18d088a293f3c1bc31d29ff12908becc02486da19c`) avait zéro constat sur 773 fichiers. Le scan différentiel v7 a vérifié les identités Git exactes :

- 761 documents sélectionnés dans la politique v7; 753 réutilisés uniquement après égalité SHA-256 et taille avec une preuve antérieure sans constat;
- les huit documents publics modifiés rescannés par le scanner strict lié à la source v7; zéro constat;
- 12 fichiers `docs/ai/` ajoutés à l’exclusion de publication, portant les fichiers exclus de 229 à 241;
- SHA-256 de `.github/pages/mkdocs.yml` : `165ea45e8a23b1b7d4e79da80664655b1005e0aa5dd1a9ccba631f80c25319ab`.

Rapport différentiel externe : SHA-256 `5099066a3657fa12fd1af9374622c3923f14f628d97472e799f3bcc8fae71992`; mapping exact des 761 blobs : `71371c8e431200bd14ceb406498d4de1f862feb62597080dd7443b2b5f568eb2`. Il s’agit d’un scan borné de surface publique; il ne change ni ne clôt G03.

Build MkDocs strict : PASS; 55 cibles de navigation présentes. Le contrôle du README a vérifié 106 liens Markdown : 90 cibles locales/ancres valides, zéro cassée; les 16 URL HTTP(S) uniques répondent HTTP 200. Les liens vers les anciennes pages techniques ont été mappés un à un vers `docs/`; les pages du site officiel n’ont été choisies que lorsqu’elles sont équivalentes. Le build n’a pas été déployé.

## Vérifications ciblées et preuves non répétées

- 22 tests ciblés de statut de version, contrats API candidats et règle d’exclusion MkDocs : PASS en 2,55 s.
- Ruff sur les deux modules de test modifiés : PASS; `py_compile` des deux modules et du smoke controller v7 : PASS.
- Le test de cohérence documentaire a été corrigé : les deux contrats API `controlled_candidate` de 0.2.12 ne sont plus testés comme s’ils devaient avoir le front matter publié 0.2.11; une assertion candidate dédiée a été ajoutée.
- La matrice qualité Owner #41328516423 demeure une preuve acquise pour le commit de workflow `698e858e79d6b6ded7cdf764f5e0dd26c710c301`. Elle n’a pas été relancée après la seule consolidation documentaire; les changements de tests documentaires ont reçu leur validation ciblée ci-dessus.
- Aucune suite complète, campagne FEM, smoke solve, comparaison physique ni benchmark n’a été exécuté dans cette reconstruction.

Le v6 reste conservé comme preuve de ses propres artefacts. Il n’est pas utilisé comme hash du v7. Les dépendances, extras et licences n’ont pas changé par rapport au v6; l’inventaire technique est réutilisable pour cette portée, mais l’avis juridique indépendant reste `NOT_ACQUIRED`.

## Statut du gate artefacts

**PASS dans la sélection contractuelle v7** : identité de source, contenu sélectionné, wheel reproductible, sdist reproductible après normalisation, Twine, installations propres et contrôles non résolvants sont acquis. Ce PASS ne ferme pas G03, ne qualifie pas de fonction scientifique, n’autorise pas les six calculs smoke et ne donne aucune permission de tag, merge ou publication.

G03 reste `FAIL_PRESERVED`; les résultats WP12 restent inchangés; la candidate 0.2.12 n’est pas annoncée comme publiée.
