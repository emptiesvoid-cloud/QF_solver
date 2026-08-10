---
doc_id: DOC-REV-MITC4-LAMINATE-001
revision: 0.5
status: controlled
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Revue mecanique MITC4 multicouche

## Decision enregistree

Le `2026-07-26`, Quentin Farinazzo enregistre la decision
**accepted_with_recommendations** pour le scope `mitc4-laminate-static`.
La revue est une `self_review` d'usage engineering interne borne, sans
certification ni independance revendiquee.

## Domaine propose

- coque MITC4 multicouche, elasticite lineaire et petits deplacements;
- proprietes et orientation definies pli par pli;
- contraintes/deformations restituees aux faces de chaque pli;
- resultantes `A/B/D`, couplage membrane-flexion et cisaillement transverse;
- indicateurs non degradants de premier pli : contrainte/deformation maximale,
  Tsai-Hill et Tsai-Wu.

Sont exclus : delaminage, dommages progressifs, rupture, Hashin, Puck,
contraintes interlaminaires `S13` de dimensionnement, coques a fibres courbes
continues et grandes rotations.

## Preuves a examiner

| Preuve | Resultat | Point de revue |
| --- | --- | --- |
| `VNV-COMP-ANALYTIC-001` | PASS, six controles `< 1e-12` | matrices `A/B/D`, transformations et criteres |
| `VNV-COMP-STRUCTURAL-CONVERGENCE-002` | PASS | membrane, flexion et angle-ply sur maillages MITC4 |
| `VNV-COMP-CALCULIX-S8R-003` | PASS | fleche fine QF/CalculiX : `0,0310 %` |
| `VNV-COMP-NAFEMS-R0031-CODEASTER-004` | PASS | QF/NAFEMS : `0,458 %`; QF/Code_Aster : `0,251 %` |
| `VNV-COMP-PLY-STRESS-005` | PASS | contraintes par pli hors singularites; erreur L2 de `0,00389 %` a `1,056 %` |
| `VNV-COMP-CURVED-ASSEMBLY-006` | PASS interne | projection sur cylindre et convergence d'un assemblage plie |
| `VNV-COMP-CURVED-CALCULIX-S8R-007` | PASS externe borne | ecart vectoriel fin QF/CalculiX : `0,225 %` |
| `VNV-COMP-CURVED-ORIENTATION-008` | PASS externe borne | axe oblique `[1,1,0]`, ecart vectoriel fin : `1,839 %` |

Les rapports et figures sont presentes dans
[Verification des composites](../composites/verification_composites.md).

## Questions pour le validateur

- [x] Les conventions de pli, axes et signes sont suffisantes.
- [x] Les resultats analytiques `A/B/D` et les tests de couplage sont acceptes.
- [x] La resistance au shear locking est convaincante pour les cas multicouches testes.
- [x] Les correlations CalculiX et NAFEMS/Code_Aster sont acceptables.
- [x] Les exclusions `S13`, delaminage et dommage sont visibles et acceptables.
- [x] Le statut `experimental` reste adapte jusqu'aux cas courbes et charges combinees.

## Recommandations proposees

1. Campagne interne sur coque courbe, assemblage plie et charges combinees :
   **realisee** dans `VNV-COMP-CURVED-ASSEMBLY-006`. Garder le scope
   `experimental` jusqu'a une correlation externe sur coque composite courbe.
2. Interdire toute affirmation sur la delaminage ou le dommage progressif.
3. Ne pas utiliser `S13` comme valeur de dimensionnement avant post-traitement
   interlaminaire dedie.
4. Comparer les contraintes par pli hors zone singuliere : **realise** dans
   `VNV-COMP-PLY-STRESS-005`; les quatre seuils passent.
5. Correler une coque composite courbe : **realise pour l'axe materiau
   parallele a la generatrice** dans `VNV-COMP-CURVED-CALCULIX-S8R-007`.
6. Harmoniser l'orientation globale oblique : **realise** dans
   `VNV-COMP-CURVED-ORIENTATION-008`. L'anomalie de convention est fermee;
   conserver `REC-COMP-CURVED-MODELFORM-001` pour l'ecart residuel MITC4/S8R.

## Signature

Decision Owner : **accepted_with_recommendations**.

Validateur : **Quentin Farinazzo**, auteur et validateur mecanique.
Date : **2026-07-26**. Mode : `self_review`, non independant.

La signature est enregistree dans
`qualification/reviews/mitc4_laminate_static_pending.json`. Le
[PDF autonome de revue](../assets/reviews/revue_mitc4_multicouche.pdf) contient
la synthese et les figures sans dependance au rendu Markdown local.

Le suivi technique posterieur a la signature est enregistre dans
`qualification/reviews/mitc4_laminate_static_followup_2026-07-26.json`.
