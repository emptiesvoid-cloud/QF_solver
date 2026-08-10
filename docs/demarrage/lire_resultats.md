---
doc_id: DOC-START-004
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Lire les resultats

La lecture suit l'ordre `verdict -> maillage -> solveur -> equilibre -> champs`.
Commencer directement par le maximum de von Mises masque souvent une erreur de
modele.

| Bloc JSON | Interpretation |
| --- | --- |
| `status` | Fin numerique historique |
| `run_verdict` | Decision appliquee par le profil |
| `mesh_report` | Geometrie, connectivite, qualite et blocages |
| `solver` | Methode, iterations, residus et parametres |
| `audit` | Matrices, vecteurs, equilibre et energie |
| `element_results` | Champs recuperes par element |
| `nodal_results` | Moyennes nodales, non valeurs brutes aux points de Gauss |
| `qualification_summary` | Maturite, warnings et erreurs bloquantes |

Les contraintes extrapolees ou moyennees doivent etre distinguees des
contraintes directement calculees aux points d'integration. Une singularite
geometrique ou de chargement peut faire diverger un maximum sous raffinement.
