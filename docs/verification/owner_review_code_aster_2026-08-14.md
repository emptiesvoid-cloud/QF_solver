---
doc_id: DOC-VV-CODEASTER-OWNER-2026-08-14
revision: 0.3
status: owner_accepted_with_recommendations
applicable_version: 0.2.1-alpha
owner_review: completed
reviewer: "Quentin Farinazzo"
approver: "Quentin Farinazzo"
---

# Owner review - correlations Code_Aster du 2026-08-14

**Document :** `DOC-VV-CODEASTER-OWNER-2026-08-14`  
**Statut :** `owner_accepted_with_recommendations`  
**Decision :** `accepted_with_recommendations`, enregistree le `2026-08-14`  
**Scope :** correlations externes et preuves internes executees le 2026-08-14

## Documents a lire

1. [Correlation composite NAFEMS R0031 / Code_Aster](composite_code_aster_nafems_2026-08-14.md)
2. [Campagne Code_Aster complete](code_aster_correlation_campaign_2026-08-14.md)
3. [Correlation MITC3 courbe Code_Aster](mitc3_laminate_curved_code_aster.md)
4. [Revue TET4 total-lagrangien structurel](tet4_total_lagrangian_structural_v2.md)
5. [Revue des solides orthotropes](revue_solides_orthotropes.md)
6. Archive de preuves release r14 : `qualification/evidence/release_vv_artifacts_2026-08-14-r14/README.md`

## Decision Owner enregistree

La revue est cloturee avec la decision globale
`accepted_with_recommendations`. Elle accepte les correlations dans leurs
domaines documentes, sans promotion automatique des fonctions experimentales
ou de recherche. Le gate `release-vv` reste distinct et ouvert.

| ID | Decision | Commentaire Owner enregistre |
| --- | --- | --- |
| Q1 | `accepted` | Digest Docker et version Code_Aster documentes. |
| Q2 | `accepted` | NAFEMS est une cible scalaire, pas une asymptote maillage par maillage. |
| Q3 | `accepted` | Les exclusions composites sont visibles aussi dans la documentation utilisateur. |
| Q4 | `accepted` | Les campagnes internes restent des preuves complementaires. |
| Q5 | `accepted` | Le TET4 total-lagrangien reste une recherche bornee. |
| Q6 | `accepted_with_recommendations` | Accepte pour le TET4 orthotrope statique/modal/Newmark documente; extensions structurelles et grand modele ouverts. |
| Q7 | `accepted` | Large-scale orthotrope et MPC/RBE2 restent hors maturite. |
| Q8 | `accepted_with_recommendations` | Reserve de convergence conservee; raffinement supplementaire ou Richardson recommande. |
| Q9 | `accepted` | Hemisphere pince accepte avec exclusion des contraintes ponctuelles singulieres. |
| Q10 | `accepted_with_recommendations` | La revue ne ferme pas le gate `release-vv`. |

**Owner :** Quentin Farinazzo  
**Date :** 2026-08-14  
**Type :** `declared_owner_review`, `not_independent`

## Questions de validation archivees

Repondre par `OUI`, `NON` ou `OUI AVEC RECOMMANDATIONS`, puis ajouter un
commentaire si necessaire.

### Correlation Code_Aster et composite

**Q1.** L'identification de Code_Aster 18.1.0, de l'image Docker epinglee par
le digest `sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`
et des fichiers de calcul est-elle suffisante pour la tracabilite externe ?

**Q2.** La convergence du deplacement `UZ` du benchmark NAFEMS R0031/1 est-elle
acceptable sur les cinq maillages, avec `0,458 %` d'ecart QF/NAFEMS au niveau
fin et `0,251 %` d'ecart QF/Code_Aster ? La valeur NAFEMS publiee est une
cible scalaire; la stabilisation se lit aussi avec les increments finaux sous
`0,1 %` et l'accord QF/Code_Aster, sans pretendre identifier une asymptote
exacte a partir de cette seule valeur.

**Q3.** La comparaison `S11` est-elle acceptee comme resultat informatif, avec
`S13` interlaminaire, delaminage, rupture progressive et calibration d'essai
explicitement hors perimetre ?

**Q4.** Les campagnes composites internes analytique, structurelle, par pli,
assemblage courbe et decoupe conique peuvent-elles rester au statut de preuves
techniques sans promotion automatique ?

### TET4 total-lagrangien

**Q5.** Les resultats noyau, assemblage, sensibilite aux increments, contrainte,
flambement, post-flambement et raffinement `98 304` elements sont-ils juges
suffisants pour l'usage de recherche borne, sans les declarer stables ?

### Solides orthotropes

**Q6.** Les correlations statiques Code_Aster des eprouvettes perforee et
equerre 3D, ainsi que les campagnes modal/Newmark, sont-elles acceptables dans
le perimetre experimental documente ? Les ecarts de champ deplacement
Code_Aster sont respectivement `3,60e-11 %` et `3,42e-10 %`; les ecarts
CalculiX sont `0,000132 %` et `0,000116 %`. Le test modal fin a `0,0309 %`
de la theorie, et les controles Newmark, modal et Code_Aster sont PASS.

**Q7.** Confirme-t-on que le grand modele orthotrope, les preuves large-scale
et la liaison MPC/RBE2 restent des actions ouvertes et ne sont pas inclus dans
la maturite actuelle ?

### MITC3 courbe et hemisphere pince

**Q8.** La correlation MITC3 multicouche courbe a orientation projetee est-elle
acceptable comme preuve statique experimentale bornee, avec `0,578 %` d'ecart
QF/Code_Aster au niveau `64 x 32` ? Le suivi `96 x 48` ramene les increments
a `3,381 %` QF_solver et `3,818 %` Code_Aster, avec un ecart vectoriel de
`0,996 %`; il reste recommande de conserver une reserve car cet ecart n'est
pas monotone. La projection d'orientation et le statut `experimental`
restent-ils clairement limites aux facettes et au petit deplacement ?

**Q9.** La correlation de l'hemisphere pince MITC3/Code_Aster est-elle
acceptable comme evidence complementaire, avec six niveaux de maillage et un
ecart final de `0,0927 %`, en excluant les contraintes ponctuelles singulieres,
les grandes rotations et toute extrapolation dynamique ?

### Decision de revue

**Q10.** Decision globale : `accepted`, `accepted_with_recommendations` ou
`more_evidence_required` ?

## Position automatique du solveur

Les campagnes calculees ont des verdicts positifs et la revue Owner est
enregistree. Elle ne ferme aucune exigence au-dela des domaines explicitement
acceptes. Le gate `release-vv` reste `FAIL` tant que les maturites, les preuves
grand modele et la campagne complete ne sont pas fermees.
