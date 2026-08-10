---
doc_id: DOC-VV-000
revision: 0.1
status: draft controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Regles d'acceptation d'un calcul

Un calcul est acceptable dans son perimetre seulement si les cinq niveaux
suivants sont satisfaits:

1. entree conforme au schema et unites explicites;
2. maillage et conditions limites mecaniquement coherents;
3. solveur converge avec residu fini sous le seuil;
4. equilibre, energie et invariants compatibles;
5. capacite couverte par une preuve et une maturite adaptee a l'usage.

`PASS` signifie que les criteres programmes passent. `WARNING` impose une
decision justifiee. `FAIL` interdit l'acceptation. Le profil `qualification`
refuse en plus les fonctions experimentales et les preuves orphelines.

--8<-- "docs/generated/qualification_status.md"
