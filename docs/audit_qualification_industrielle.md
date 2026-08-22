---
doc_id: DOC-AUD-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Audit de qualification industrielle du solveur EF

## Statut du document

- Identifiant: `AUDIT-QUAL-001`
- Version: `1.0`
- Statut: baseline d'audit interne
- Perimetre: solveur Python MITC4, TET4, TET10, analyses standard et grand modele
- Conclusion: outil preindustriel utilisable sous verification independante, non certifie

Ce document ne declare pas le solveur certifie. Il etablit les ecarts entre la
baseline actuelle et un outil d'ingenierie susceptible d'obtenir un credit de
qualification.

## Referentiel recommande

Le solveur est utilise comme outil de bureau d'etudes. La trajectoire principale
est donc RTCA DO-330 / EUROCAE ED-215, dans le contexte reconnu par la FAA dans
[AC 20-115D](https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentID/1032046).
DO-178C deviendrait le referentiel principal seulement si le solveur etait
embarque.

La qualification logicielle doit etre completee par une verification et une
validation de la mecanique selon les principes de
[ASME V&V 10](https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-solid-mechanics)
et de
[NASA-STD-7009B](https://standards.nasa.gov/standard/nasa/nasa-std-7009):
domaine d'emploi, verification du code, verification de solution, validation,
incertitudes et revue technique.

## Baseline P0 mesuree le 11 juillet 2026

- Le compteur de tests courant n'est plus recopie dans ce document. Il est
  collecte automatiquement par la generation des artefacts documentaires et
  enregistre avec la revision source.
- Couverture lignes et branches combinees: 85,30 %; seuil CI global
  fixe a 84 % et seuil des nouveaux modules P0 fixe a 90 %.
- `ruff` et `compileall`: PASS.
- Campagne interne: 10 cas sur 10 passent, dont 2 candidats remplacement.
- Registre machine-readable: 24 exigences; readiness TET4 statique candidate
  a 11/11 sans orphelin; scopes dynamique, grand modele et non-lineaire encore
  en developpement.
- MITC4 complet: PASS, erreur Scordelis-Lo 24x24 de 0,999 %.
- Artefact matrix-free: 1 029 000 ddl, 1 971 054 TET4, 1000 iterations,
  residu relatif 9,83e-9 et environ 473 s de resolution.
- PETSc et MPI ne sont pas installes dans l'environnement audite.
- 88 fichiers Python de production, 12 366 lignes, maximum 642 lignes/fichier.
- Git est initialise sans commit. La CI Windows/Linux, les baselines
  verrouillees et la couverture existent, mais la CI distante n'a pas encore
  ete executee dans ce depot local.

Cette section conserve les mesures historiques de l'audit P0. Les resultats
applicables sont ceux de `docs/generated/docs_manifest.json`, regeneres par
`scripts/build_docs.py` et relies a leurs empreintes SHA-256.

## Tableau de synthese

| Priorite | Axe | Constat | Risque | Action |
| --- | --- | --- | --- | --- |
| P0 | Configuration | Git sans commit; CI creee mais non executee a distance | Baseline non encore reproductible hors poste | Premier commit relu, CI verte, tag et SBOM |
| P0 | Verdict | `RunVerdict` et codes stables implementes | Politique a maintenir sur toute nouvelle commande | Tests contractuels CLI/API |
| P0 | Tracabilite | Registre de 24 exigences et readiness implementes | Trois scopes restent `development` | Completer references et preuves par scope |
| P0 | Plasticite | Tangente J2 consistante verifiee par differences finies | Loi toujours experimentale, petits deplacements | Benchmarks cycliques independants |
| P1 | Performance | Assemblage COO par listes et audits elementaires complets | Memoire et temps eleves | Preallocation, kernels compiles, audit par niveau |
| P1 | Dynamique | LU Newmark reutilisee et acceleration initiale sparse | Assemblage et historiques encore en memoire | Etendre aux chargements blocs et checkpoint |
| P1 | Modal | `eigsh` par defaut, `eigh` borne a 2000 ddl libres | ARPACK et stockage des modes restent limites | Shift configurable et diagnostics memoire |
| P1 | Grand modele | Vecteur PETSc sequentiel et donnees repliquees | MPI multi-rang non demontre | Partitionnement et I/O distribues |
| P1 | TET4 | Deformation constante et verrouillage volumique possible | Biais en flexion et nu proche de 0,5 | Convergence et domaine d'emploi |
| P1 | TET10 | Validation geometrique et masse simplifiees | Frequences et contraintes fragiles | Patch, quadrature, masse et jacobiens |
| P1 | MITC4 | Bonne verification actuelle, formulation facette plane et drilling penalise | Domaine coque limite | Sensibilite, distorsion et benchmarks publies |
| P1 | Erreurs | Taxonomie et diagnostics courts implementes | Etendre l'injection de fautes aux backends externes | Campagnes negatives multi-plateformes |
| P2 | Unites | Metadonnees sans conversion ni controle dimensionnel | Erreur d'echelle silencieuse | SI impose en qualification |
| P2 | Post-traitement | Moyennes nodales simples | Pics de contrainte masques | Points d'integration contractuels |
| P2 | Confiance | Score heuristique conserve et marque `non_certifying` | Mauvaise interpretation par un consommateur ancien | Retrait lors d'une prochaine version majeure |

## Points a conserver

- Separation `api`, `cli`, `core`, `elements`, `mesh`, `post`, `io` et `large`.
- Verification obligatoire du maillage avant resolution.
- Dossiers de preuve avec empreintes SHA-256.
- Tests de rigidite, symetrie, energie, residus et orthogonalite.
- Campagne MITC4 avec patch tests, shear-locking et Scordelis-Lo.
- Separation entre le chemin standard et le chemin grand modele.

## Roadmap

### Court terme: socle P0

- Baseline Git, CI, dependances verrouillees et documents de cycle de vie.
- Verdict de qualification obligatoire dans l'API, la CLI et les preuves.
- Exigences et scopes de qualification machine-readable.
- Correction J2, erreurs numeriques et validations Newmark/harmonique.
- Mesure de couverture et tests negatifs.

### Moyen terme: verification mecanique et noyau hybride

- TET4/TET10: solutions manufacturees, patch tests multi-elements,
  convergence energetique, distorsion et quasi-incompressibilite.
- MITC4: Scordelis systematique, sensibilite drilling/epaisseur/distorsion et
  benchmarks coques independants.
- Modal, Newmark et harmonique: solutions analytiques MDOF, convergence,
  bilans energetiques, participation modale et correlation directe/modale.
- Non-lineaire: cycles, decharge/recharge, tangente consistante, puis grandes
  transformations avant qualification de l'arc-length.
- API Python conservee; kernels critiques progressivement portes en
  C++/Fortran et compares au noyau de reference.

### Long terme: calcul distribue et dossier externe

- Assemblage et resolution PETSc/MPI reellement distribues.
- HDF5 parallele, checkpoint/restart et benchmarks multi-rangs.
- Correlations analytiques, logiciels tiers et essais physiques independants.
- Quantification des erreurs de discretisation et des incertitudes d'entree.
- Dossier DO-330 et revues externes par scopes progressifs.

## Criteres de sortie P0

- Aucun profil strict/qualification ne retourne 0 lorsque son verdict est FAIL.
- Chaque exigence d'un scope candidat possede conception, code, test et preuve.
- La tangente J2 concorde avec les differences finies a moins de 1e-6 relatif.
- Les erreurs utilisateur ont une categorie et un code de sortie documentes.
- Les preuves contiennent revision source, environnement, entree et couverture.
- Les campagnes engineering restent vertes; les gaps de qualification sont
  annonces comme tels.
