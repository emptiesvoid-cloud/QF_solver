---
doc_id: DOC-REF-004
revision: 0.4
status: draft
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Feuille de route

La release `0.2.5a0` est figee sur un scope qualifie borne. Les fonctionnalites
non fermees restent visibles comme experimental, research ou hors scope ; la
roadmap ne constitue pas une promesse de date.

## 0.2.6 — maturite et robustesse

- renforcer la V&V massive des chemins deja presents ;
- fermer les dettes de robustesse et de diagnostics ;
- augmenter la couverture des chemins critiques sans tests artificiels ;
- caracteriser plus largement assemblage, memoire et scalabilite ;
- corriger uniquement les defauts numeriques demontres ;
- conserver SciPy utilisable seul et PETSc/SLEPc optionnels.

## 0.2.7 candidate — J2 finite-strain et G06

- retenir une formulation J2 finite-strain explicitement approuvee ;
- verifier les mesures de deformation et de contrainte, le tangent et l'etat ;
- construire une V&V independante et des correlations Code_Aster ;
- requalifier G06 sur un scope borne ;
- traiter la friction comme un chantier separe uniquement apres decision Owner.

## Hors engagement

Pas de date promise, pas de nouvelle physique arbitraire et pas de promotion
automatique d'une voie experimentalement observee en capacite qualifiee.
