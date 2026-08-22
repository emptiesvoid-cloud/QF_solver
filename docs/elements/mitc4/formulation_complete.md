---
doc_id: DOC-ELEM-MITC4-06
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 : derivation complete

Le MITC4 implemente une coque Reissner-Mindlin isotrope lineaire. Chaque noeud
porte $(u,v,w,r_x,r_y,r_z)$ dans une base locale elementaire. La formulation
de cisaillement est mixte afin de limiter le verrouillage des coques minces.

## 1. Base locale et cinematique

Pour les diagonales $\mathbf d_{13}$ et $\mathbf d_{24}$, la base est

$$
\mathbf e_x=\frac{\mathbf d_{13}}{\|\mathbf d_{13}\|},\qquad
\mathbf e_z=\frac{\mathbf e_x\times\mathbf d_{24}}
{\|\mathbf e_x\times\mathbf d_{24}\|},\qquad
\mathbf e_y=\mathbf e_z\times\mathbf e_x.
$$

Les ddl globaux sont projetes vers cette base. A travers l'epaisseur $z$,
la cinematique Reissner-Mindlin s'ecrit, de maniere schematique,

$$
u(x,y,z)=u_0-zr_y,\quad v(x,y,z)=v_0+zr_x,\quad w(x,y,z)=w_0.
$$

Les rotations restent donc independantes de la pente de $w$, ce qui permet le
cisaillement transverse, au contraire de Kirchhoff-Love.

## 2. Interpolation Q4 et resultantes de coque

Les quatre fonctions bilineaires sont

$$
N_i(\xi,\eta)=\frac14(1+\xi_i\xi)(1+\eta_i\eta).
$$

Elles interpolent les translations et rotations. Les deformations generalisees
sont separees en membrane $\boldsymbol\varepsilon_m$, courbure
$\boldsymbol\kappa$ et cisaillement transverse $\boldsymbol\gamma_s$ :

$$
\boldsymbol\varepsilon(z)=\boldsymbol\varepsilon_m+z\boldsymbol\kappa.
$$

Sous contrainte plane,

$$
\mathbf D_p=\frac{E}{1-\nu^2}
\begin{bmatrix}1&\nu&0\\\nu&1&0\\0&0&(1-\nu)/2\end{bmatrix},
\quad \mathbf A=t\mathbf D_p,\quad \mathbf D_b=\frac{t^3}{12}\mathbf D_p,
\quad \mathbf S=\kappa_sGt\mathbf I.
$$

## 3. Tying MITC et rigidite

Une interpolation directe Q4 de $\boldsymbol\gamma_s$ impose des contraintes
parasites lorsque $t/L$ devient petit. MITC4 evalue les composantes
covariantes aux points A $(0,-1)$, C $(0,1)$ pour $\gamma_\xi$ et B $(1,0)$,
D $(-1,0)$ pour $\gamma_\eta$, puis interpole

$$
g_\xi(\eta)=\tfrac12[(1-\eta)g_A+(1+\eta)g_C],\qquad
g_\eta(\xi)=\tfrac12[(1-\xi)g_D+(1+\xi)g_B].
$$

La transformation par le Jacobien de surface reconstruit le cisaillement
physique. La rigidite locale assemblee est

$$
\mathbf K_l=\int_A\left(
\mathbf B_m^T\mathbf A\mathbf B_m+
\mathbf B_b^T\mathbf D_b\mathbf B_b+
\mathbf B_s^T\mathbf S\mathbf B_s+
\mathbf B_d^Tk_d\mathbf B_d\right)dA.
$$

L'integration $2\times2$ porte les termes usuels; le terme de drilling
$\gamma_d=r_z-\tfrac12(v_{,x}-u_{,y})$ stabilise le ddl $r_z$ avec une faible
penalisation $k_d$. Cette penalisation doit faire l'objet d'une sensibilite.

## 4. Demonstrations de comportement

Le patch membrane isole $\mathbf B_m$, le patch de flexion isole
$\mathbf B_b$ et le patch cisaillement verifie le tying $\mathbf B_s$. Les
benchmarks [Cook](../../demonstrations/benchmarks/cook.md),
[Scordelis-Lo](../../demonstrations/benchmarks/scordelis.md) et
[cylindre pince](../../demonstrations/benchmarks/pinched.md) examinent ensuite
deformation, convergence et sensibilite au locking sur des maillages reels.
Une bonne reponse unique ne remplace pas l'etude de raffinement.

## 5. Contraintes aux faces et limites

Les contraintes de membrane-flexion sont calculees aux faces
$z=\pm t/2$ par $\mathbf D_p(\varepsilon_m+z\kappa)$. La convention de signe
de $z$ suit la normale locale $\mathbf e_z$. Les limites connues incluent le
gauchissement, les grandes rotations, la pression suiveuse et la dependance
eventuelle a la penalisation de drilling.

## Tracabilite

| Objet | Code | Preuve | Exigence |
| --- | --- | --- | --- |
| Base, cinematique et matrices | `solveur/elements/shell/mitc4/element.py` | modes rigides et patch membrane | `REQ-SOL-002` |
| Tying MITC | `solveur/elements/shell/mitc4/element.py` | patch cisaillement et locking | `REQ-SOL-002` |
| Coques maillees | `mitc4/benchmarks.py` | Cook, Scordelis-Lo, cylindre pince | `REQ-CMP-003` |

References : [REF-MITC4-DVORKIN](../../reference/references.md#ref-mitc4-dvorkin)
et [REF-MITC-BATHE](../../reference/references.md#ref-mitc-bathe).
