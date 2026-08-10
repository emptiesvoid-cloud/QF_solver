---
doc_id: DOC-FEM-002
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Conventions, tenseurs et reperes

## Solides 3D

Le vecteur de deformation utilise l'ordre d'ingenieur:

$$
\boldsymbol\varepsilon=
[\varepsilon_{xx},\varepsilon_{yy},\varepsilon_{zz},
\gamma_{xy},\gamma_{yz},\gamma_{xz}]^T,
$$

et le vecteur de contrainte:

$$
\boldsymbol\sigma=
[\sigma_{xx},\sigma_{yy},\sigma_{zz},
\tau_{xy},\tau_{yz},\tau_{xz}]^T.
$$

Les cisaillements de deformation sont donc les cisaillements d'ingenieur,
$\gamma_{xy}=2\varepsilon_{xy}$. Les ddl solides suivent l'ordre `UX, UY, UZ`.

## Coques

Chaque noeud MITC4 porte `UX, UY, UZ, RX, RY, RZ`. Le repere local
$(\mathbf e_1,\mathbf e_2,\mathbf e_3)$ est orthonorme direct, avec
$\mathbf e_3=\mathbf e_1\times\mathbf e_2$. Les contraintes de faces sont
rapportees a $z=+t/2$ et $z=-t/2$ suivant cette normale locale.

## Signes

- traction normale positive en tension;
- pression positive appliquee suivant l'oppose de la normale sortante;
- volume TET positif pour une connectivite directe;
- moments nodaux ordonnes apres les forces dans les bilans globaux;
- frequences exprimees en hertz et pulsations en rad/s.

Toute transformation de repere doit conserver la norme et le travail virtuel.
Les tests de rotation rigide des chargements MITC4 protegent cette invariance.
