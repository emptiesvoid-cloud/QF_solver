# Écart de procédure des tests — 2026-10-24

Le mandat de délégation imposait des tests mathématiques sans pytest. Le worker
d'extraction a néanmoins exécuté les deux commandes suivantes dans ce dossier :

1. `C:\Python313\python.exe -B -m pytest -q test_archive_inputs.py` :
   `7 passed in 0.39s`, code 0, selon son compte rendu.
2. `C:\Python313\python.exe -B -m pytest -q test_archive_inputs.py test_integrate_proofs.py` :
   `10 passed in 0.41s`, code 0, selon son compte rendu.

Leur sortie détaillée et la liste des modules effectivement chargés n'ont pas
été archivées. La revue indépendante a examiné les ancêtres du dossier sans
trouver de `conftest.py`. La configuration pytest du dépôt ajoute `src` et
déclare `testpaths = ["tests"]`, sans `addopts` ni `pytest_plugins`.
L'environnement installé dispose toutefois de plugins automatiques ; leur
chargement exact lors de ces deux processus n'est pas démontrable après coup.
Les modules de tests examinés ne contiennent aucun appel d'assemblage, de
résolution ou d'évaluation du noyau scientifique. Aucun appel FEM n'est établi
par les éléments disponibles ; l'absence d'une trace d'importation interdit
d'affirmer quels modules les plugins ont chargés.

Les tests ont ensuite été convertis en `unittest.TestCase`, sans dépendance
pytest. La validation finale de référence est celle de `verify_non_fem.py`,
qui lance `C:\Python313\python.exe -I -S -B -m unittest discover ...` : mode
isolé, initialisation `site` désactivée, fichiers de bytecode désactivés,
bibliothèque standard et modules locaux de preuve seulement. Le résultat et
les empreintes des sources testées sont archivés dans
`non_fem_verification_record.json`, avec stdout et stderr.

La revue vérifie également les empreintes des archives et l'identité propre du
checkout historique. Les deux lancements pytest précédents ne servent pas de
validation de l'évaluateur final et n'entraînent aucune promotion scientifique.
