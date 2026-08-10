---
doc_id: DOC-REF-006
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# References scientifiques et numeriques

Les donnees bibliographiques ci-dessous sont conservees dans le site hors
ligne. Les liens externes facilitent la consultation de la source originale,
mais ne sont jamais charges pour afficher le manuel.

## Formulation FEM

<a id="ref-hammer-stroud-1956"></a>
**REF-HAMMER-STROUD-1956.** P. C. Hammer et A. H. Stroud,
*Numerical Integration over Simplexes*, Mathematics of Computation 10(55),
137-139, 1956.
[DOI 10.1090/S0025-5718-1956-0086390-2](https://doi.org/10.1090/S0025-5718-1956-0086390-2).
Reference primaire des formules de quadrature sur simplexes utilisees pour
justifier les points symetriques dits de Hammer.

<a id="ref-fem-bathe"></a>
**REF-FEM-BATHE.** K. J. Bathe, *Finite Element Procedures for Solids and
Structures, Linear Analysis*, MIT OpenCourseWare, cours RES.2-002, 2010.
[Cours et guide d'etude officiels](https://ocw.mit.edu/courses/res-2-002-finite-element-procedures-for-solids-and-structures-spring-2010/video_galleries/linear/).
Source pedagogique de reference pour travaux virtuels, interpolation
isoparametrique, assemblage, statique, modal et dynamique.

<a id="ref-beam-timoshenko-1921"></a>
**REF-BEAM-TIMOSHENKO-1921.** S. P. Timoshenko, *On the correction for shear
of the differential equation for transverse vibrations of prismatic bars*,
Philosophical Magazine, 1921,
[DOI 10.1080/14786442108636264](https://doi.org/10.1080/14786442108636264).
Reference primaire pour la prise en compte de la deformation de cisaillement
dans les poutres.

<a id="ref-solid-industrial"></a>
**REF-SOLID-INDUSTRIAL.** Dassault Systemes, *Solid continuum elements*,
documentation elementaire Abaqus 2024.
[Documentation elementaire](https://docs.software.vt.edu/abaqusv2024/English/SIMACAEELMRefMap/simaelm-c-solidcont.htm).
Reference industrielle independante pour les domaines d'emploi compares des
tetraedres lineaires et quadratiques; ce n'est pas la specification du code.

<a id="ref-tetra-keast-1986"></a>
**REF-TETRA-KEAST-1986.** P. Keast, *Moderate-degree tetrahedral quadrature
formulas*, Computer Methods in Applied Mechanics and Engineering 55,
339-348, 1986. [DOI 10.1016/0045-7825(86)90059-9](https://doi.org/10.1016/0045-7825(86)90059-9).
Reference primaire pour les regles de quadrature tetraedriques, dont les
regles symetriques utilisees comme point de depart pour le controle Hammer.

## Coques MITC

<a id="ref-mitc4-plate-1985"></a>
**REF-MITC4-PLATE-1985.** K. J. Bathe et E. N. Dvorkin, *A four-node plate
bending element based on Mindlin/Reissner plate theory and a mixed
interpolation*, International Journal for Numerical Methods in Engineering
21, 367-383, 1985,
[DOI 10.1002/nme.1620210213](https://doi.org/10.1002/nme.1620210213).

<a id="ref-mitc4-dvorkin"></a>
**REF-MITC4-DVORKIN.** E. N. Dvorkin et K. J. Bathe, *A continuum mechanics
based four-node shell element for general nonlinear analysis*, Engineering
Computations 1, 77-88, 1984,
[DOI 10.1108/eb023562](https://doi.org/10.1108/eb023562).

<a id="ref-mitc-bathe"></a>
**REF-MITC-BATHE.** K. J. Bathe et E. N. Dvorkin, *A formulation of general
shell elements - the use of mixed interpolation of tensorial components*,
IJNME 22, 697-722, 1986,
[DOI 10.1002/nme.1620220312](https://doi.org/10.1002/nme.1620220312).

<a id="ref-mitc3-plus-2014"></a>
**REF-MITC3-PLUS-2014.** P.-S. Lee, Y. Lee et K.-J. Bathe, *The MITC3+ shell
element and its performance*, Computers & Structures 138, 12-23, 2014,
[DOI 10.1016/j.compstruc.2014.02.005](https://doi.org/10.1016/j.compstruc.2014.02.005).
Reference primaire pour la bulle cubique, les points de tying, le champ de
cisaillement covariant suppose et les benchmarks du triangle MITC3+.

<a id="ref-shell-obstacle"></a>
**REF-SHELL-OBSTACLE.** R. H. MacNeal et R. L. Harder, *A proposed standard
set of problems to test finite element accuracy*, Finite Elements in Analysis
and Design 1, 3-20, 1985,
[DOI 10.1016/0168-874X(85)90003-4](https://doi.org/10.1016/0168-874X(85)90003-4).

## Algebre lineaire

<a id="ref-cg-1952"></a>
**REF-CG-1952.** M. R. Hestenes et E. Stiefel, *Methods of conjugate gradients
for solving linear systems*, Journal of Research of the NBS 49, 409-436,
1952. [Article NIST](https://nvlpubs.nist.gov/nistpubs/jres/049/jresv49n6p409_A1b.pdf),
[DOI 10.6028/jres.049.044](https://doi.org/10.6028/jres.049.044).

<a id="ref-minres-1975"></a>
**REF-MINRES-1975.** C. C. Paige et M. A. Saunders, *Solution of sparse
indefinite systems of linear equations*, SIAM Journal on Numerical Analysis
12, 617-629, 1975,
[DOI 10.1137/0712047](https://doi.org/10.1137/0712047).

<a id="ref-gmres-1986"></a>
**REF-GMRES-1986.** Y. Saad et M. H. Schultz, *GMRES: A generalized minimal
residual algorithm for solving nonsymmetric linear systems*, SIAM J. Sci.
Stat. Comput. 7, 856-869, 1986,
[DOI 10.1137/0907058](https://doi.org/10.1137/0907058).

<a id="ref-bicgstab-1992"></a>
**REF-BICGSTAB-1992.** H. A. van der Vorst, *Bi-CGSTAB: A fast and smoothly
converging variant of Bi-CG for the solution of nonsymmetric linear systems*,
SIAM J. Sci. Stat. Comput. 13, 631-644, 1992,
[DOI 10.1137/0913035](https://doi.org/10.1137/0913035).

## Dynamique et non-lineaire

<a id="ref-newmark-1959"></a>
**REF-NEWMARK-1959.** N. M. Newmark, *A method of computation for structural
dynamics*, Journal of the Engineering Mechanics Division 85, 67-94, 1959,
[DOI 10.1061/JMCEA3.0000098](https://doi.org/10.1061/JMCEA3.0000098).

<a id="ref-direct-integration-1972"></a>
**REF-DIRECT-INTEGRATION-1972.** K. J. Bathe et E. L. Wilson, *Stability and
accuracy analysis of direct integration methods*, Earthquake Engineering &
Structural Dynamics 1, 283-291, 1972,
[DOI 10.1002/eqe.4290010308](https://doi.org/10.1002/eqe.4290010308).

<a id="ref-j2-simo-1985"></a>
**REF-J2-SIMO-1985.** J. C. Simo et R. L. Taylor, *Consistent tangent
operators for rate-independent elastoplasticity*, CMAME 48, 101-118, 1985,
[DOI 10.1016/0045-7825(85)90070-2](https://doi.org/10.1016/0045-7825(85)90070-2).

## Composites

<a id="ref-comp-jones"></a>
**REF-COMP-JONES.** R. M. Jones, *Mechanics of Composite Materials*, seconde
edition, Taylor & Francis, 1999. Reference theorique pour la reciprocite
orthotrope, la loi reduite en contraintes planes, les transformations de
lamelle et la theorie classique des stratifies.

Le livre constitue une reference de formulation. Les proprietes d'un materiau
industriel devront provenir de donnees d'essais controlees et tracables.

<a id="ref-comp-azzi-tsai"></a>
**REF-COMP-AZZI-TSAI.** V. D. Azzi et S. W. Tsai, *Anisotropic strength of
composites*, Experimental Mechanics 5, 283-288, 1965,
[DOI 10.1007/BF02326292](https://doi.org/10.1007/BF02326292).

<a id="ref-comp-tsai-wu"></a>
**REF-COMP-TSAI-WU.** S. W. Tsai et E. M. Wu, *A General Theory of Strength
for Anisotropic Materials*, Journal of Composite Materials 5, 58-80, 1971,
[DOI 10.1177/002199837100500106](https://doi.org/10.1177/002199837100500106).

<a id="ref-comp-calculix-s8r"></a>
**REF-COMP-CALCULIX-S8R.** CalculiX 2.20, coque quadratique S8R composite et
carte `SHELL SECTION, COMPOSITE`. La restriction S8R/S6 et l'expansion des
couches sont decrites dans le
[manuel officiel CalculiX](https://www.feacluster.com/CalculiX/ccx_2.18/doc/ccx/node41.html).
La correlation QF_solver conserve la version et l'image Docker executees dans
son manifeste.

<a id="ref-comp-code-aster"></a>
**REF-COMP-CODE-ASTER.** Code_Aster, commande `DEFI_COMPOSITE` et materiau
`ELAS_ORTH` pour les modelisations de coques stratifiees DKT/DST. La campagne
`VNV-COMP-NAFEMS-R0031-CODEASTER-004` execute Code_Aster 18.1.0 DST/DSQ dans
une image Docker epinglee et obtient un verdict `PASS_EXTERNAL_CORRELATION`.
La formulation et les commandes sont decrites dans les
[manuels Code_Aster](https://www.code-aster.org/V2/doc/v11/fr/man_u/u4/u4.42.03.pdf).

<a id="ref-comp-nafems-r0031"></a>
**REF-COMP-NAFEMS-R0031.** NAFEMS R0031/1,
[*Laminated strip under three-point bending*](https://www.nafems.org/publications/resource_center/r0031/).
La geometrie, l'empilement, les chargements et les valeurs publiques
`UZ(E)=-1,06 mm`, `S11(E)=684 MPa` et `S13(D)=-4,1 MPa` sont reproduits par le
[guide de verification Abaqus 2024](https://docs.software.vt.edu/abaqusv2024/English/SIMACAEBMKRefMap/simabmk-c-compositetest1.htm).
L'acceptation QF_solver actuelle porte sur `UZ(E)`; les contraintes restent
informatives ou ouvertes selon leur localisation.

## Calcul distribue

<a id="ref-petsc-ksp"></a>
**REF-PETSC-KSP.** PETSc Development Team, *KSP: Linear System Solvers*,
manuel utilisateur PETSc.
[Documentation officielle KSP](https://petsc.org/main/manual/ksp/).
La version effectivement utilisee doit toujours etre inscrite dans le dossier
de preuve; ce lien ne fige pas une version d'execution.

## Maillage et echange

<a id="ref-gmsh-41"></a>
**REF-GMSH-41.** C. Geuzaine et J.-F. Remacle, *Gmsh: a three-dimensional
finite element mesh generator with built-in pre- and post-processing
facilities*, International Journal for Numerical Methods in Engineering 79,
1309-1331, 2009. Le format MSH 4.1 et l'API sont decrits dans le
[manuel officiel Gmsh](https://gmsh.info/doc/texinfo/). La version executee est
inscrite dans chaque rapport d'import.
