---
doc_id: DOC-REQ-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Exigences operationnelles de l'outil

## Statut

- Identifiant: `TOR-SOLVEUR-001`
- Version: `0.1`
- Statut: brouillon controle, a approuver avec le responsable certification

## Usage prevu

Le solveur produit des resultats de mecanique structurale pour revue par un
ingenieur. Tant qu'un scope n'est pas approuve, ses resultats doivent etre
verifies par une methode independante.

## Exigences principales

- `TOR-001`: refuser toute entree non conforme au schema actif.
- `TOR-002`: refuser un maillage contenant un element invalide.
- `TOR-003`: identifier separement succes numerique et verdict de qualification.
- `TOR-004`: ne jamais retourner un succes qualification pour une fonction hors scope.
- `TOR-005`: tracer entree, version, environnement, options et sorties.
- `TOR-006`: produire des residus normalises et un diagnostic de convergence.
- `TOR-007`: conserver les resultats aux points d'integration sans les confondre
  avec les moyennes nodales de visualisation.
- `TOR-008`: utiliser exclusivement le systeme SI dans un scope qualifiable v1.
- `TOR-009`: detecter valeurs non finies, singularites et non-convergences.
- `TOR-010`: permettre de verifier l'integrite d'un dossier de preuve hors calcul.
- `TOR-011`: integrer les charges reparties avec les fonctions de forme,
  tracer leur resultante et leur premier moment, et refuser les charges
  suiveuses tant que leur formulation non lineaire n'est pas qualifiee.

## Limites actuelles

- Le mode grand modele qualifiable est limite au TET4 statique lineaire.
- Le backend matrix-free accepte seulement les blocs structures generes.
- PETSc/MPI multi-rang n'est pas encore qualifie.
- TET10 et les analyses non-lineaires restent experimentaux.
- Les moyennes nodales ne sont pas des valeurs de dimensionnement contractuelles.
