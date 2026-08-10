---
doc_id: DOC-ELEM-MITC4-07
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Formulation forte, faible et interpolation mixte

## 1. Hypotheses de coque

La surface moyenne est parametree par $(x,y)$ et l'epaisseur par
$z\in[-t/2,t/2]$. La cinematique de Reissner-Mindlin utilise

$$
\mathbf u(x,y,z)=
\begin{bmatrix}
u_0(x,y)+z\theta_y(x,y)\\
v_0(x,y)-z\theta_x(x,y)\\
w_0(x,y)
\end{bmatrix}.
$$

Les normales restent droites mais ne sont pas contraintes a rester
orthogonales a la surface moyenne. Le cisaillement transverse est donc
present.

## 2. Deformations generalisees

Les deformations sont separees en membrane, courbure et cisaillement :

$$
\boldsymbol\varepsilon_m=
\begin{bmatrix}u_{0,x}&v_{0,y}&u_{0,y}+v_{0,x}\end{bmatrix}^T,
$$

$$
\boldsymbol\kappa=
\begin{bmatrix}\theta_{y,x}&-\theta_{x,y}&
\theta_{y,y}-\theta_{x,x}\end{bmatrix}^T,
$$

$$
\boldsymbol\gamma_s=
\begin{bmatrix}w_{0,x}+\theta_y&
w_{0,y}-\theta_x\end{bmatrix}^T.
$$

Les conventions de signe sont liees au trièdre local
$(\mathbf e_1,\mathbf e_2,\mathbf e_3)$ et a la face superieure
$z=+t/2$.

## 3. Formulation forte en resultantes

Pour une coque plane sans inertie, les equations locales d'equilibre des
resultantes s'ecrivent schematiquement

$$
\nabla_s\cdot\mathbf N+\mathbf p_t=\mathbf0,
$$

$$
\nabla_s\cdot\mathbf Q+p_n=0,
$$

$$
\nabla_s\cdot\mathbf M-\mathbf Q+\mathbf m=\mathbf0.
$$

$\mathbf N$, $\mathbf M$ et $\mathbf Q$ sont respectivement les resultantes
de membrane, moments de flexion et efforts tranchants. Les conditions de bord
portent soit sur les deplacements/rotations, soit sur les resultantes
conjuguees.

## 4. Formulation faible

Le travail virtuel interne est

$$
\delta W_{int}=
\int_A
\left(
\delta\boldsymbol\varepsilon_m^T\mathbf N+
\delta\boldsymbol\kappa^T\mathbf M+
\delta\boldsymbol\gamma_s^T\mathbf Q
\right)dA.
$$

Pour une couche isotrope :

$$
\mathbf N=\mathbf A\boldsymbol\varepsilon_m,
\qquad
\mathbf M=\mathbf D\boldsymbol\kappa,
\qquad
\mathbf Q=\mathbf A_s\boldsymbol\gamma_s,
$$

avec $\mathbf A=t\mathbf C_m$,
$\mathbf D=t^3\mathbf C_m/12$ et
$\mathbf A_s=\kappa_st\mathbf C_s$.

Le probleme faible impose

$$
\delta W_{int}=\delta W_{ext}
\qquad\forall\delta\mathbf q\in\mathcal V.
$$

## 5. Discretisation Q4

Les translations et rotations sont interpolees par les quatre fonctions
bilineaires $N_a(\xi,\eta)$. Les contributions membrane et flexion sont
obtenues par derivation du mapping local.

Une interpolation bilineaire directe du cisaillement impose trop de
contraintes lorsque $t/L\rightarrow0$ : l'element devient artificiellement
raide. C'est le shear locking.

## 6. Interpolation MITC du cisaillement

MITC4 remplace les composantes de cisaillement calculees directement par des
champs reconstruits depuis quatre points de tying situes sur les aretes :

$$
\widetilde\gamma_{\xi z}(\xi,\eta)
=\frac{1-\eta}{2}\gamma_{\xi z}^{A}
+\frac{1+\eta}{2}\gamma_{\xi z}^{C},
$$

$$
\widetilde\gamma_{\eta z}(\xi,\eta)
=\frac{1-\xi}{2}\gamma_{\eta z}^{D}
+\frac{1+\xi}{2}\gamma_{\eta z}^{B}.
$$

Cette projection reduit les contraintes parasites tout en conservant les
patchs de cisaillement. Elle ne dispense pas des controles de distorsion.

## 7. Rigidite et drilling

La rigidite locale est

$$
\mathbf K_e=
\int_A
\left(
\mathbf B_m^T\mathbf A\mathbf B_m+
\mathbf B_b^T\mathbf D\mathbf B_b+
\widetilde{\mathbf B}_s^T\mathbf A_s
\widetilde{\mathbf B}_s
\right)dA+\mathbf K_d.
$$

La rotation de drilling n'est pas fournie par la theorie de
Reissner-Mindlin plane. Une faible penalisation $\mathbf K_d$ stabilise
l'assemblage. Son energie doit rester negligeable devant l'energie physique.

## 8. Integration et objectivite

QF_solver utilise une quadrature $2\times2$. Le repere local est construit a
partir de la geometrie nodale, puis toutes les matrices sont transformees
globalement. Une rotation rigide de la facette ne doit modifier ni energie,
ni valeurs propres physiques, ni resultantes locales apres reprojection.

## 9. Matrice minimale de tests

| ID | Preuve | Critere |
| --- | --- | --- |
| MITC4-FW-01 | Six modes rigides | energie proche de zero |
| MITC4-FW-02 | Patch membrane | erreur `< 1e-10` |
| MITC4-FW-03 | Patch flexion | erreur `< 1e-10` regulier |
| MITC4-FW-04 | Patch cisaillement | tying reproduit le champ |
| MITC4-FW-05 | Invariance de repere | matrices/resultats transformes |
| MITC4-FW-06 | Pression | force et moment conserves |
| MITC4-FW-07 | Faces superieure/inferieure | signes membrane +/- flexion |
| MITC4-FW-08 | Shear locking | ratio mince `>= 0.90` |
| MITC4-FW-09 | Energie drilling | `< 1 %` de l'energie totale |
| MITC4-FW-10 | Distorsion | erreur dans le domaine borne |

## 10. Demonstrations et limites

```powershell
python .\mitc4_solver.py verify --quick
python -m pytest tests\verification\test_mitc4_verification.py
```

Les preuves structurelles sont Cook, Scordelis-Lo, cylindre pince et la
matrice de shear locking en epaisseur/distorsion. Les limites sont : petites
transformations, facettes de qualite bornee, drilling penalise, pas de
delaminage ni dommage, et aucune extrapolation hors du domaine V&V.

References primaires : `REF-MITC4-DVORKIN`, `REF-MITC-BATHE`,
`REF-FEM-BATHE`; code `mitc4/element.py`; exigences `REQ-SOL-002`,
`REQ-SOL-005` et `REQ-MESH-002`.
