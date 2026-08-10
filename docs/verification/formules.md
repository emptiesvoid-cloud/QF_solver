---
doc_id: DOC-VV-007
revision: 0.1
status: draft controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Revue documentaire et tracabilite des formules

Cette page separe trois decisions qui ne doivent jamais etre confondues:

- le controle automatique des liens entre formule, exigence, code, test et
  reference;
- la Owner review independante des demonstrations et conventions;
- l'identification d'une revision Git propre et approuvee.

Une couverture automatique complete ne remplace ni le relecteur ni
l'approbateur. Les champs de revue restent volontairement vides jusqu'a une
decision Owner nominative.

## Readiness P0 generee

--8<-- "docs/generated/review_readiness.md"

Le rapport machine-readable correspondant est
`docs/generated/review_readiness.json`. Le profil `qualification` reste
bloquant tant que la Owner review et la baseline source ne sont pas toutes
deux en `PASS`.

## Registre des formules critiques

--8<-- "docs/generated/formula_traceability.md"

La source autoritative est `qualification/formulas.json`. Une section
documentaire supprimee, une fonction renommee, un test absent ou une
reference inconnue fait echouer la construction documentaire.

