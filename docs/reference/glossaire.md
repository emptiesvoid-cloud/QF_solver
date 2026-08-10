---
doc_id: DOC-REF-003
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Glossaire

**AIJ**
: Format de matrice creuse PETSc analogue a CSR/CSC distribue.

**Audit boite blanche**
: Rapport exposant ddl, matrices, vecteurs, assemblage, residus, energies et
  decisions, au lieu de retourner uniquement des champs finaux.

**Ddl / DOF**
: Degre de liberte. `UX`, `UY`, `UZ` sont des translations; `RX`, `RY`, `RZ`
  des rotations.

**Jacobian / Jacobien**
: Transformation entre coordonnees naturelles et physiques. Son determinant
  porte l'orientation et le changement de volume ou d'aire.

**Locking / verrouillage**
: Raideur numerique artificielle creee par une cinematique discrete trop
  contraignante, par exemple le cisaillement d'une plaque mince.

**Patch test**
: Test d'un assemblage d'elements soumis a un champ polynomial connu.

**Point de tying**
: Point d'echantillonnage utilise par MITC4 pour reconstruire le cisaillement
  transverse covariant.

**Preuve independante**
: Reference analytique, equilibre ferme, logiciel tiers controle ou essai qui
  ne reutilise pas la meme implementation que le resultat verifie.

**Residuel / residu**
: Desequilibre de l'equation discrete apres application d'une solution.

**Scope**
: Perimetre borne d'element, materiau, analyse, chargement et environnement
  auquel une decision de maturite s'applique.
