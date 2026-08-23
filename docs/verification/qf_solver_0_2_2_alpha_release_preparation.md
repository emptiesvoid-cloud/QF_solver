---
doc_id: DOC-RELEASE-PREP-0-2-2-001
revision: 0.1
status: draft
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# Préparation de release QF_solver 0.2.2a0

## Objet

Cette fiche prépare le tag `v0.2.2a0`, la construction des distributions et
la publication PyPI. Elle ne crée pas le tag, ne pousse aucun commit et ne
publie aucun paquet. La décision de release reste distincte de la revue
Owner du backend numérique.

## État actuel

| Point | État | Observation |
| --- | --- | --- |
| Version package | `READY` | `pyproject.toml`, `src/solveur/version.py` et README ciblent `0.2.2a0` |
| Changelog | `READY` | section `0.2.2a0` ajoutée avec les limites connues |
| Citation | `READY` | version logicielle et date alignées sur `0.2.2-alpha` |
| Licence | `READY` | Apache-2.0 pour le code, CC BY 4.0 pour la documentation et les exemples originaux |
| API publique | `READY` | contrat `from qf_solver import ...` vérifié |
| Couverture CI | `PASS` | gate `80 %`, campagne locale à `88,67 %` |
| Audit public | `PASS` | `qualification/publication_audit_0_2_2.json`, `1755` fichiers, zéro finding |
| Backend V&V | `PASS_BOUNDED` | périmètre borné, revue Owner `accepted_with_recommendations` |
| Tag Git | `PENDING` | à créer uniquement après revue finale du commit |
| Publication PyPI | `PENDING` | déclenchée uniquement par un tag `v*` ou une release GitHub publiée |

## Contrôles locaux avant tag

Les commandes suivantes sont à exécuter sur le commit candidat, après revue
des fichiers suivis. Elles ne doivent pas être remplacées par une publication
manuelle depuis un répertoire de travail non inspecté.

```powershell
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist/*
python scripts/audit_public_release.py --output qualification/publication_audit_0_2_2.json
python scripts/audit_git_history.py --output git_history_audit.json
python scripts/audit_release_archive.py --ref HEAD --output release_archive_audit.json
python scripts/release_readiness.py --output release_readiness.json
```

Le résultat attendu est `DISTRIBUTION CHECK: PASS` pour wheel et sdist, un
audit public `PASS` sans finding, puis `READY` pour `release_readiness.py`.
Avant le tag, `release_readiness.py` peut rester `NOT_READY` à cause du
worktree modifié et de l'absence de tag : ce sont des contrôles de gel, pas
des erreurs du package.

## Contenu attendu des distributions

La wheel doit contenir le runtime `qf_solver/` et `solveur/`, sans tests,
scripts, outils ni corpus V&V de travail. Le sdist doit contenir le README,
la licence et les sources `src/solveur/`. Les exemples et registres déclarés
dans `pyproject.toml` doivent rester lisibles après installation.

Après construction, vérifier localement :

```powershell
python -m pip install --force-reinstall dist/qf_solver-0.2.2a0-py3-none-any.whl
qf-solver --version
qf-solver methods
python -c "from qf_solver import solve_model; print(solve_model.__name__)"
```

## Création du tag, à faire séparément

Le tag ne doit être créé qu'après validation du contenu staged et après
confirmation Owner de la release :

```powershell
git status --short
git diff --cached --check
git diff --cached --name-only
git tag -a v0.2.2a0 -m "Release QF_solver 0.2.2a0"
```

Après création du tag, rejouer l'audit d'archive avec les attributs commités :

```powershell
python scripts/audit_release_archive.py --ref v0.2.2a0 --committed-attributes --output release_archive_audit_tag.json
```

Le push du tag est une action séparée et n'est pas inclus dans cette fiche de
préparation.

## Publication PyPI

Le workflow `.github/workflows/publish-pypi.yml` construit et vérifie les
distributions avant publication. La publication est maintenant conditionnée
à une release GitHub publiée ou à un tag Git `v*`; un lancement manuel sur une
branche ne peut donc pas publier accidentellement un paquet.

L'environnement GitHub `pypi` doit contenir le secret `PYPI_API_TOKEN`. Le
secret n'est jamais écrit dans le dépôt, le changelog, les artefacts ou les
logs. Le compte PyPI et le projet `qf-solver` doivent être vérifiés par
l'Owner avant le premier déclenchement.

Après publication, les contrôles externes sont :

```powershell
python -m pip index versions qf-solver
python -m pip install --no-cache-dir "qf-solver==0.2.2a0"
qf-solver --version
```

## Réserves à conserver dans la release

- Le backend 0.2.2 alpha est validé dans un périmètre borné ; cela ne vaut pas
  une qualification générale de tous les modèles.
- Le modal SLEPc à environ 2M DDL reste bloqué par la limite de ressources.
- La tentative matrix-free à 1M DDL reste `BLOCKED_TIMEOUT` après 900 s.
- Les scopes mécaniques non stables restent exclus de toute revendication
  stable et de toute extrapolation.
- La publication PyPI ne doit pas être déduite du seul statut `PASS` des tests.

## Décision de préparation

Le dossier technique et les métadonnées de distribution sont préparés. La
release est prête pour la revue finale du commit candidat, mais elle n'est
pas encore gelée, taguée ou publiée.
