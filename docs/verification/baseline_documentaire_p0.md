---
doc_id: DOC-VV-P0-CLOSURE-001
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Cloture technique de la baseline documentaire P0

## Decision automatique

La baseline documentaire P0 est **fermee techniquement** pour la version
`0.2.0` : les pages sont enregistrees, les liens et ressources publiees sont
controles, les demonstrations sont regenerees et les preuves V&V possedent des
empreintes. Cette decision ne vaut ni `owner_review` ni certification.

Le fichier machine-readable associe est
`qualification/baselines/documentation_baseline_p0.json`.

| Controle | Evidence | Etat |
| --- | --- | --- |
| Registre documentaire | `docs/document_registry.json` | PASS automatique |
| Formules tracees | `qualification/formulas.json` | 44/44 PASS |
| Demonstrations et empreintes | `docs/generated/docs_manifest.json` | PASS engineering |
| Liens et images documentaires | tests documentation cibles | PASS technique |
| Generation controlee | `scripts/build_docs.py --profile engineering` | PASS technique |
| Owner review complete | `docs/generated/review_readiness.json` | BLOCKED, attendu |
| Revision Git propre approuvee | `docs/generated/review_readiness.json` | BLOCKED, attendu |

## Ce qui est ferme

- le site est la source technique detaillee unique ;
- chaque page Markdown est referencee par un identifiant documentaire ;
- les ressources locales de la revue TET4 autonome sont presentes et
  testees ;
- les figures orthotropes modal/Newmark et leur correlation Code_Aster sont
  publiees avec leur rapport de preuve ;
- les references de tests ne sont plus recopiees manuellement dans les pages
  de statut.

## Verrous qui ne peuvent pas etre fermes automatiquement

1. Une Owner review doit renseigner `reviewer` et `approver` pour toute page
   dont la maturite doit devenir `controlled` ou `approved`.
2. Une revue independante reste necessaire avant toute revendication de
   qualification externe. Une auto-revue peut accepter un usage engineering
   interne, jamais l'independance.
3. Les comparaisons Abaqus/Ansys demandent un jeu de resultats obtenu sous une
   licence et une version tracees. Code_Aster et CalculiX restent les oracles
   externes reproductibles disponibles localement.
4. La construction de profil `qualification` restera refusee tant que l'arbre
   source est sale ou que la revision de reference n'est pas approuvee.

## Decision Owner ciblee du 26 juillet 2026

Quentin Farinazzo accepte la politique de references externes ci-dessus en
`self_review` : les correlations Abaqus/Ansys sont differees jusqu'a reception
de resultats sous licence, versionnes et exportes de maniere controlee. Code_Aster
et CalculiX sont retenus entre-temps comme oracles reproductibles locaux.

La revue page par page de l'ensemble de la documentation est reportee a la fin
du developpement. Ce report ne transforme pas les pages `draft` en pages
`controlled` et ne leve pas le verrou du profil `qualification`.

La decision est tracee dans
`qualification/reviews/documentation_baseline_p0_2026-07-26.json`.

La politique active est desormais
`qualification/external_oracle_policy.json` : une licence Abaqus ou Ansys ne
conditionne plus aucun test actif, gate de livraison ou decision engineering.
Les valeurs publiees Abaqus existantes sont conservees uniquement comme
references historiques tracees.

## Owner review minimale

1. Executer `python .\scripts\build_docs.py --profile engineering`.
2. Ouvrir le site avec un navigateur systeme si une inspection visuelle est
   requise.
3. Relire les pages de decision TET4, TET10, MITC4 et solides orthotropes.
4. Signer uniquement les scopes et les documents effectivement revus dans
   `qualification/reviews/`; ne pas pre-remplir les autres signatures.

La feuille de route conserve les sujets mecaniques et externes ouverts dans
`P1+`; ils ne sont pas des anomalies de publication P0.
