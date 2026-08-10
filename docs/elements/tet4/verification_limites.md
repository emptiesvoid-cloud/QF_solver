---
doc_id: DOC-ELEM-TET4-05
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - Verification, convergence et limites

## Echelle de preuve

1. Les tests unitaires protegent volume, gradients, symetrie, masse et
   invariants.
2. Le test de modes rigides verifie le noyau de $\mathbf K_e$.
3. Le patch affine verifie interpolation, assemblage, conditions aux limites
   et recuperation de contrainte.
4. La traction et la compression analytiques verifient le signe du
   deplacement, la contrainte, l'energie et les reactions.
5. La force volumique constante verifie la resultante, le premier moment et
   le bilan global charge-reactions.
6. La convergence sur maillages raffines verifie la tendance, sans transformer
   une reference de poutre en solution exacte 3D.
7. Le panneau mince en traction dans son plan verifie le champ affine 3D, la
   contraction de Poisson libre et la resultante membranaire equivalente.
8. L'arbre circulaire en torsion, sur huit niveaux de convergence et une
   sonde h9 a `105 529` elements, verifie le
   cisaillement spatial, l'integration d'une traction lineaire, le couple et la
   convergence vers Saint-Venant.

Les valeurs fermees des cas 4 et 5 sont fournies par
`Tet4StaticClosedFormOracle`, un module scalaire sans dependance au noyau EF.
Cette separation evite qu'une comparaison de qualification reutilise la
matrice elementaire qu'elle est censee verifier.

Le benchmark `BM-SOL-CANTILEVER-001` calcule cette tendance sur six
maillages Gmsh. L'ordre observe est obtenu par regression de $\log(e_h)$ sur
$\log(h)$ et doit rester superieur ou egal a la limite de `REQ-SOL-004`.
L'intervalle de tailles, la fleche de chaque niveau, les residus et l'erreur
fine sont publies; aucune extrapolation hors de cet intervalle n'est
revendiquee.

## Identite energetique

En statique lineaire a forces conservatives,

$$
U=\frac12\mathbf u^T\mathbf K\mathbf u,
\qquad W=\mathbf u^T\mathbf f,
\qquad 2U=W.
$$

L'ecart relatif est publie dans l'audit et doit etre interprete avec le residu
libre et les reactions.

## Benchmarks associes

- [Patch TET4 3D](../../demonstrations/benchmarks/tet4_patch.md);
- [Panneau mince 3D en traction membranaire](../../demonstrations/benchmarks/tet4_membrane.md);
- [Arbre circulaire en torsion](../../demonstrations/benchmarks/tet4_torsion.md);
- [Poutre TET4/TET10](../../demonstrations/benchmarks/cantilever.md);
- cas de pression coherente du catalogue historique;
- bloc grand modele pour la seule scalabilite, pas pour une nouvelle preuve
  elementaire.

## Decision d'usage

Le TET4 statique lineaire isotrope est accepte pour un usage engineering
interne dans le domaine teste par Quentin Farinazzo le 14 juillet 2026. Cette
auto-revue non independante ne constitue pas une certification externe. Les
deplacements, reactions, energies et contraintes affines sont couverts. Les
pics ponctuels de contrainte de torsion, les singularites et les extrapolations hors du
domaine teste restent exclues de cette acceptation. Cette maturite
ne couvre pas automatiquement un materiau presque incompressible, une
geometrie tres courbe, une singularite de contrainte ou une extrapolation hors
des maillages verifies.

Le domaine machine-readable `tet4-linear-static-v1` borne explicitement la
loi materiau a `isotropic_3d`, $E>0$ Pa et $0\le\nu\le0.45$. Il reprend aussi
les seuils de qualite de maillage et de conditionnement presentes dans
l'[interface de qualification](../../verification/qualification.md). Ces
valeurs sont inscrites dans `audit.qualification.qualification_domain` et
dans le manifeste de preuve v2.

Tests: `tests/unit/test_tet4_element.py`,
`tests/verification/test_meshed_benchmarks.py`. Exigences:
`REQ-SOL-001`, `REQ-SOL-004`, `REQ-MESH-001`, `REQ-CMP-003`.
