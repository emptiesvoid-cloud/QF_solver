---
doc_id: DOC-AUDIT-PROJECT-021-001
revision: 0.1
status: controlled_snapshot
applicable_version: 0.2.1a0
audit_date: 2026-08-15
certification_claim: none
reviewer: ''
approver: ''
---
# Audit hygiene, architecture et manques - QF_solver 0.2.1 alpha
## Verdict
**Le code publiable est propre du point de vue des marqueurs controles, mais la baseline de developpement n'est pas gelable aujourd'hui.**
- Audit de confidentialite du lot publiable : `PASS`, 1928 fichiers, 0 finding.
- Gate `release-vv` courant : `PENDING_FINAL_CAMPAIGN`.
- Git : HEAD `969352a`, tag `none`, 0 fichiers modifies et 0 fichiers non suivis.
- Tests collectes : 1187.
- Limite 700 lignes : 0 depassement; 21 fichiers au-dessus de 600 lignes.
## Confidentialite et publication
Le scanner controle les chemins de poste, adresses privees, secrets courants, ancienne marque et vocabulaire d'assistance interne dans les sources candidates. Aucun finding n'est present dans le lot courant. Les fichiers locaux de configuration et le cache de graphe ne sont pas suivis par Git : `aucun`.
L'identite complete de l'auteur/Owner reste volontairement presente dans 149 fichiers de metadonnees, attribution et revues signees. Ce n'est pas une donnee de poste, mais c'est bien une information personnelle publiee; elle doit rester un choix explicite du proprietaire.
Cette verification ne prouve pas l'absence absolue de secret dans tout l'historique binaire. L'audit d'historique existant est un prefiltre sur les chemins; une revue manuelle de l'archive `git archive` reste obligatoire avant publication.
## Structure
Points solides : paquet `src/solveur` organise par responsabilite, elements separes, API et CLI dediees, MITC4 canonique sous `src/solveur/elements/shell/mitc4`, facade `src/solveur/compat/mitc4` de compatibilite, tests unitaires/integration/V&V distincts, seuil de 700 lignes et imports de couches controles.
Points a corriger :
1. `scripts/` contient 241 fichiers Python a plat, dont 138 runners `run_*`. Les classer sous `scripts/vnv/code_aster`, `scripts/vnv/calculix`, `scripts/vnv/internal`, `scripts/docs` et `scripts/release`, avec wrappers temporaires si un chemin public est documente.
2. `src/solveur/verification` contient 188 modules. Le separer progressivement par familles sans changer les imports publics.
3. Plusieurs modules sont proches de la limite de 700 lignes. Les extractions doivent suivre les responsabilites et etre protegees par snapshots/V&V.
4. `src/solveur/documentation` ne contient plus de source active. Supprimer le repertoire vide local; ne pas recreer un runtime web tant que cette decision produit reste retiree.
5. La facade historique `src/solveur/compat/mitc4` est acceptable en 0.2.x, mais sa date de retrait 0.3.0 doit rester documentee et testee.
6. La couverture standard omet `src/solveur/verification/*`. Ajouter une mesure separee de couverture des gates et generateurs, sans confondre couverture logicielle et preuve mecanique.
## Plus gros fichiers Python
| Fichier | Lignes |
| --- | ---: |
| `scripts/build_scope_closure_owner_review_pack.py` | 699 |
| `src/solveur/verification/mitc4_modal_extended.py` | 697 |
| `scripts/build_owner_review_audit_pack.py` | 697 |
| `src/solveur/verification/maturity_promotion.py` | 694 |
| `scripts/build_release_0_2_3_owner_review_pdf.py` | 693 |
| `src/solveur/verification/release_vv.py` | 687 |
| `src/solveur/core/audit.py` | 684 |
| `src/solveur/core/modal.py` | 683 |
| `src/solveur/mesh/validation.py` | 674 |
| `src/solveur/core/dynamic.py` | 674 |
## Etat des Owner reviews
Le paquet de promotion contient 33 scopes : 22 techniquement prets et 11 bloques uniquement par une decision Owner. Le total-lagrangien exige en plus une relecture independante; il ne peut pas etre ferme par auto-revue. Aucune promotion ne doit etre appliquee en bloc.
## Manques fonctionnels et industriels
### Priorite 0 - fermeture 0.2.1 alpha
- Enregistrer les decisions scope par scope et conserver les recommandations.
- Obtenir la relecture independante du TET4 total-lagrangien ou maintenir `research`.
- Relancer `release-vv`, la campagne complete, le build de distribution et l'audit d'archive sur un checkout propre.
- Verifier les artefacts PyPI dans un environnement neuf Python 3.10 et 3.13.
### Priorite 1 - robustesse
- Etendre la correlation du contact frictionnel a plusieurs geometries externes.
- Ajouter une seconde plateforme PETSc/MPI et ameliorer le weak scaling avant toute revendication multi-machine.
- Renforcer les campagnes orthotropes et composites courbes, notamment contraintes par pli dynamiques.
- Stabiliser les diagnostics des solveurs iteratifs : choix automatique, conditionnement, stagnation et fallback trace.
- Etendre le typage au noyau, aux I/O et aux gates de release.
### Priorite 2 - concurrence industrielle
- Contact surface-surface robuste, grand glissement et frottement avec tangente consistante.
- Non-linearite geometrique et materiau couplees, plasticite grandes deformations, endommagement et rupture.
- Composite pli par pli plus complet : S13/S23, criteres, degradation et delamination.
- Grand modele au-dela du TET4 statique : dynamique, modal, autres elements et I/O parallele qualifiee.
- Pre/post-traitement industriel : ensembles, champs, reprises, checkpoints, XDMF/HDF5 parallele et comparaisons reproductibles.
## Decision de cet audit
Le projet est techniquement riche et nettement mieux structure qu'un prototype. Il n'est toutefois pas pret a etre gele en `0.2.1a0` tant que le worktree reste massif et que les decisions Owner ne sont pas enregistrees. Le constat de confidentialite est **PASS pour les fichiers candidats actuels**, avec la reserve normale d'une revue finale de l'archive et de l'historique avant publication.
