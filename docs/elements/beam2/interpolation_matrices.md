---
doc_id: DOC-ELEM-BEAM2-03
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# BEAM2 - Interpolation, matrices et repere

## 1. Repere local

L'axe $\mathbf e_1$ joint les deux noeuds. Le vecteur utilisateur
`reference_vector` est projete dans le plan normal a $\mathbf e_1$ :

$$
\widetilde{\mathbf e}_2=
\mathbf r-(\mathbf r\cdot\mathbf e_1)\mathbf e_1,
\qquad
\mathbf e_2=\frac{\widetilde{\mathbf e}_2}
{\|\widetilde{\mathbf e}_2\|},
\qquad
\mathbf e_3=\mathbf e_1\times\mathbf e_2.
$$

Un vecteur presque colineaire a l'axe est refuse. La matrice de rotation
orthogonale doit verifier $\mathbf R^T\mathbf R=\mathbf I$ et
$\det\mathbf R=+1$.

## 2. Interpolation

Les translations axiale et de torsion utilisent des fonctions lineaires. Les
plans de flexion emploient la solution exacte de la poutre de Timoshenko a
coefficients constants, ce qui introduit les parametres

$$
\phi_y=\frac{12EI_z}{\kappa_y^sGAL^2},
\qquad
\phi_z=\frac{12EI_y}{\kappa_z^sGAL^2}.
$$

Lorsque $\phi\rightarrow0$, la limite Euler-Bernoulli est retrouvee. Lorsque
le cisaillement devient significatif, la souplesse supplementaire est
conservee.

## 3. Blocs de rigidite

Les rigidites axiale et de torsion sont

$$
\mathbf K_N=\frac{EA}{L}
\begin{bmatrix}1&-1\\-1&1\end{bmatrix},
\qquad
\mathbf K_T=\frac{GJ}{L}
\begin{bmatrix}1&-1\\-1&1\end{bmatrix}.
$$

Chaque bloc de flexion couple une translation transverse et une rotation aux
deux extremites. Il est symetrique et tend vers le bloc Euler-Bernoulli quand
$\phi\rightarrow0$.

## 4. Transformation globale

La transformation nodale contient la meme rotation pour translations et
rotations :

$$
\mathbf T_n=
\begin{bmatrix}\mathbf R&0\\0&\mathbf R\end{bmatrix},
\qquad
\mathbf K_e^g=\mathbf T^T\mathbf K_e^\ell\mathbf T.
$$

L'energie doit etre invariante :

$$
(\mathbf d^g)^T\mathbf K_e^g\mathbf d^g
=(\mathbf d^\ell)^T\mathbf K_e^\ell\mathbf d^\ell.
$$

## 5. Masse coherente

La masse comprend translation et inerties rotatoires de section. Les
controles minimaux sont la symetrie, la positivite, la masse totale
$\rho AL$ et les moments d'inertie attendus. La masse concentree reste hors
du scope modal accepte tant qu'elle n'est pas verifiee separement.

## 6. Charges coherentes

Une charge lineique constante est integree dans le repere choisi. Les forces
nodales et couples d'extremite conservent la resultante et le moment :

$$
\sum_a\mathbf f_a=\int_0^L\mathbf p\,dx,
\qquad
\sum_a(\mathbf x_a-\mathbf x_0)\times\mathbf f_a+\mathbf m_a
=\int_0^L(\mathbf x-\mathbf x_0)\times\mathbf p\,dx.
$$

## 7. Tests matriciels

| Controle | Attendu |
| --- | --- |
| symetrie | $\|K-K^T\|/\|K\|<10^{-12}$ |
| modes rigides | six valeurs propres nulles |
| positivite deformable | six valeurs propres positives |
| objectivite | reponse identique apres rotation |
| limite Euler | erreur tend vers zero lorsque $\phi\to0$ |
| masse totale | erreur relative `< 1e-10` |

## 8. Exemple

```powershell
python -m pytest tests\unit\test_beam2_element.py -q
python .\qf_solver.py solve --input .\examples\beam2_cantilever.json `
  --output .\results\beam2_matrices.json
```

## 9. Limites

Section constante, axe droit, pas d'offset, pas de relachement, pas de
gauchissement de Vlasov et pas de non-linearite de section.

## 10. Tracabilite

Code `solveur/elements/beam/beam2.py`, materiau/section
`solveur/materials/beam.py`, exigences `REQ-BEAM-001` et `REQ-LOAD-001`.
