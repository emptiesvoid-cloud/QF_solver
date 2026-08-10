---
doc_id: DOC-ELEM-MITC4-05
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Verification, locking et limites

## Pyramide de verification

- partition de l'unite, Jacobien et invariance au mouvement rigide;
- patch membrane, flexion et cisaillement;
- comparaison MITC contre Q4 a cisaillement complet;
- etude d'epaisseur pour detecter le shear locking;
- benchmarks Cook, Scordelis-Lo et cylindre pince;
- controle des signes aux faces superieure et inferieure;
- invariance sous rotation globale et coherence des reperes voisins.

## Indicateur de locking

Une plaque de plus en plus mince doit tendre vers la theorie de
Kirchhoff-Love sans que sa fleche numerique s'effondre artificiellement. La
campagne compare le rapport

$$
R(h/t)=\frac{w_{FE}}{w_{ref}}
$$

pour MITC4 et pour l'element temoin a cisaillement complet. Une amelioration
sur un seul rapport $h/t$ ne suffit pas; la tendance complete est publiee.

La campagne controlee `VNV-MITC4-SHEAR-LOCKING-001` croise cinq maillages,
quatre rapports $t/L$ et quatre niveaux de distorsion. La reference est la
fleche de Timoshenko

$$
w_{ref}=\frac{PL^3}{3EI}+\frac{PL}{\kappa GA},
\qquad I=\frac{bt^3}{12},\quad A=bt.
$$

Le premier terme mesure la flexion et le second la deformation de
cisaillement physique. Sur la matrice complete de 160 calculs, l'erreur MITC4
maximale du maillage fin est de 2,08 %, le ratio limite mince vaut 0,979 et le
Q4 temoin tombe a environ $3,2\,10^{-5}$. Cette comparaison distingue une vraie
deformation de cisaillement d'un verrouillage numerique.

## Benchmarks mailles

- [Membrane de Cook](../../demonstrations/benchmarks/cook.md): distorsion et membrane;
- [Scordelis-Lo](../../demonstrations/benchmarks/scordelis.md): coque courbe sous charge repartie;
- [Cylindre pince](../../demonstrations/benchmarks/pinched.md): flexion severe et action membrane.

## Domaine de maturite

Le MITC4 statique est `candidate` dans le perimetre V&V renforce. Le modal et
Newmark restent `development` jusqu'a correlation Abaqus et Owner review. Le
noyau actuel reste une facette plane en petits deplacements. Grandes rotations,
contact, flambement non lineaire, composites multicouches et offset de coque
ne sont pas qualifies.

Le perimetre complet et les criteres sont decrits dans le
[plan de validation MITC4](../../verification/mitc4_validation.md).

Tests: `tests/verification/test_mitc4_verification.py`,
`tests/verification/test_meshed_benchmarks.py`. References:
[REF-MITC4-DVORKIN](../../reference/references.md#ref-mitc4-dvorkin),
[REF-MITC-BATHE](../../reference/references.md#ref-mitc-bathe).
