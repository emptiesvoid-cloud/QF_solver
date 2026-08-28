---
doc_id: DOC-REF-OSS-001
revision: 0.1
status: controlled
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Licence et publication open source

QF_solver est une bibliotheque Python personnelle de calcul elements finis
publiee sous une licence ouverte pour permettre l'etude, la reutilisation et
l'usage commercial. Le code source est sous `Apache-2.0`. La documentation et
les exemples originaux sont sous `CC BY 4.0`.

La licence ne couvre pas automatiquement les publications, maillages,
sorties de solveurs externes ou autres composants tiers. Leurs droits sont
recenses dans `THIRD_PARTY_LICENSES.md` et doivent rester attaches a chaque
artefact publie.

La licence autorise la reutilisation et l'usage commercial. Elle ne constitue
ni une garantie de resultat mecanique, ni une certification, ni une
autorisation d'utiliser le nom QF_solver comme marque ou approbation.

Les contributions futures suivront `CONTRIBUTING.md`. Les anomalies de calcul
et les propositions V&V auront des formulaires distincts afin de ne pas
confondre un defaut logiciel avec une limite de domaine mecanique.

## Attribution

Le projet est porte par Quentin Farinazzo. Les utilisateurs sont invites a
citer QF_solver et sa version au moyen de `CITATION.cff`. Les contributions
sont regies par `CONTRIBUTING.md`; elles restent sous Apache-2.0 sauf accord
explicite different.

## Etat de la readiness 0.2.5a0

La documentation publique accompagne un candidat dont le scope qualifie est
explicitement borne. La preuve de reference indique `1719` tests passes,
`0` echec, `88.37 %` de couverture et `64/64` controles externes passes.
Les gates G04 et G06 restent visibles comme experimentales/non qualifiees,
et le frottement G07 est hors scope.

La creation du tag, le push Git et le televersement PyPI restent des actions
separees controlees par l'Owner. Cette page ne transforme pas une readiness
documentaire en publication automatique.
