---
doc_id: DOC-COMP-001
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Lamelle orthotrope en contraintes planes

## Conventions d'axes

- `1` : direction principale des fibres;
- `2` : direction transverse dans le plan du pli;
- `3` : normale positive au pli;
- `x-y` : axes locaux de l'element de coque;
- `theta` : rotation positive antihoraire de `x` vers `1`, vue suivant `+3`.

La transformation complete d'une future coque stratifiee suivra deux etapes :
global vers repere local MITC4, puis repere local `x-y` vers repere materiau
`1-2`. Seule la seconde transformation est active dans ce premier socle.

Les vecteurs utilisent le cisaillement d'ingenieur :

\[
\boldsymbol\varepsilon =
\begin{bmatrix}\varepsilon_x&\varepsilon_y&\gamma_{xy}\end{bmatrix}^{T},
\qquad
\boldsymbol\sigma =
\begin{bmatrix}\sigma_x&\sigma_y&\tau_{xy}\end{bmatrix}^{T}.
\]

## Reciproquite et admissibilite

Les donnees independantes sont `E1`, `E2`, `nu12` et `G12`. La symetrie de la
loi elastique impose :

\[
\nu_{21}=\nu_{12}\frac{E_2}{E_1},
\qquad
\Delta=1-\nu_{12}\nu_{21}>0.
\]

QF_solver refuse les modules non positifs, les valeurs non finies, une densite
negative et toute combinaison donnant `Delta <= 0`. Ces controles garantissent
la positivite de la loi reduite, mais ne qualifient pas un materiau reel : les
constantes doivent encore provenir d'essais et d'un domaine de temperature et
d'humidite documente.

## Matrice reduite Q

Sous l'hypothese `sigma_3=tau_13=tau_23=0` :

\[
\begin{bmatrix}\sigma_1\\\sigma_2\\\tau_{12}\end{bmatrix}
=
\underbrace{\begin{bmatrix}
E_1/\Delta & \nu_{12}E_2/\Delta & 0\\
\nu_{12}E_2/\Delta & E_2/\Delta & 0\\
0&0&G_{12}
\end{bmatrix}}_{\mathbf Q}
\begin{bmatrix}\varepsilon_1\\\varepsilon_2\\\gamma_{12}\end{bmatrix}.
\]

La classe `OrthotropicLamina` expose `nu21`, `reduced_stiffness` et controle
que les trois valeurs propres de `Q` sont positives.

## Transformation Qbar

Pour eviter une ambiguite de signe dans les formules developpees, le code
reconstruit les tenseurs symetriques, applique la rotation orthogonale, puis
revient aux vecteurs de Voigt. Avec

\[
\mathbf R(\theta)=
\begin{bmatrix}\cos\theta&-\sin\theta\\
\sin\theta&\cos\theta\end{bmatrix},
\]

les transformations sont :

\[
\boldsymbol\varepsilon^{12}_{\mathrm{tensor}}
=\mathbf R^T\boldsymbol\varepsilon^{xy}_{\mathrm{tensor}}\mathbf R,
\qquad
\boldsymbol\sigma^{xy}_{\mathrm{tensor}}
=\mathbf R\boldsymbol\sigma^{12}_{\mathrm{tensor}}\mathbf R^T.
\]

La matrice `Qbar(theta)` est obtenue en appliquant cette operation aux trois
deformations unitaires. Cette construction garantit simultanement la symetrie
et l'invariance de l'energie :

\[
\frac12(\boldsymbol\varepsilon^{xy})^T\overline{\mathbf Q}
\boldsymbol\varepsilon^{xy}
=\frac12(\boldsymbol\varepsilon^{12})^T\mathbf Q
\boldsymbol\varepsilon^{12}.
\]

## Demonstration numerique 0, 90 et +/-45 degres

Pour `E1=135 GPa`, `E2=10 GPa`, `nu12=0,3` et `G12=5 GPa`, on obtient
`nu21=0,0222222`. Les matrices ci-dessous sont en GPa.

| Angle | Qbar11 | Qbar22 | Qbar12 | Qbar16 | Qbar26 | Qbar66 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 135,906 | 10,067 | 3,020 | 0 | 0 | 5,000 |
| +45 | 43,003 | 43,003 | 33,003 | 31,460 | 31,460 | 34,983 |
| -45 | 43,003 | 43,003 | 33,003 | -31,460 | -31,460 | 34,983 |
| 90 | 10,067 | 135,906 | 3,020 | 0 | 0 | 5,000 |

Les tests prouvent que `0 deg` redonne `Q`, que `90 deg` permute les directions
principales, que `+/-45 deg` inverse seulement les couplages extension-
cisaillement et que l'energie reste invariante pour plusieurs angles.

## Interface et limite volontaire

```python
from qf_solver import OrthotropicLamina

ply = OrthotropicLamina(E1=135e9, E2=10e9, nu12=0.3, G12=5e9)
q = ply.reduced_stiffness
qbar = ply.transformed_stiffness(45.0)
```

Le type JSON `orthotropic_lamina` est valide par le parseur, mais aucun element
ne l'accepte encore. Cette barriere est intentionnelle : utiliser ce materiau
dans un MITC4 produit un echec de compatibilite maillage tant que `A/B/D`, les
cisaillements transverses et les resultats par pli ne sont pas verifies.

Reference theorique : [REF-COMP-JONES](../reference/references.md#ref-comp-jones).

