---
doc_id: DOC-VNV-MITC3-CURVED-PROJECTED-001
revision: 0.2
status: owner_accepted_experimental
applicable_version: 0.2.0-alpha
owner_review: accepted_for_v020_alpha
reviewer: ""
approver: ""
---

# MITC3+ multicouche courbe a orientation projetee

Cette page conserve la preuve historique CalculiX `S6` acceptee par Owner pour
la V0.2.0-alpha. La correlation Code_Aster `DST/TRIA3` ajoutee ensuite est
documentee dans [l'etude dediee](mitc3_laminate_curved_code_aster.md).

La preuve CalculiX reste utile pour comparer deux formulations de coque sur la
meme surface facettisee. La preuve Code_Aster apporte une seconde reference
externe avec projection du meme vecteur global dans chaque facette. Les deux
resultats restent experimentaux et bornes au modele, au maillage, au layup et
aux chargements decrits dans leurs rapports.

Les contraintes par pli, `S13`, le dommage, la rupture et le delaminage ne sont
pas couverts par ces correlations de deplacements globaux.
