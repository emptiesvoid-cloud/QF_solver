---
doc_id: DOC-REF-OSS-001
revision: 0.1
status: controlled
applicable_version: 0.2.0
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

## Etat de la readiness locale

La baseline Windows du 29 juillet 2026 est techniquement verte :

- `926` tests passent et `12` tests optionnels sont ignores;
- le profil engineering passe avec `886` tests;
- le site strict regenere `625` artefacts;
- l'audit de source analyse `579` fichiers sans constat;
- l'archive prospective contient `407` fichiers sans contenu interdit et
  exclut explicitement les instructions de travail internes.

La publication reste `NOT_READY` pour deux raisons de release : l'arbre Git
n'est pas fige et la revision n'est pas taggee `0.2.0`. Le prefiltre historique
trouve aussi `145` chemins d'etudes dans `13` commits; ils doivent etre relus
ou remplaces par un historique public propre avant mise en ligne.
