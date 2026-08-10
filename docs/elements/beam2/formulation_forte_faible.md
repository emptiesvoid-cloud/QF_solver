---
doc_id: DOC-ELEM-BEAM2-02
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# BEAM2 - Formulation forte et formulation faible

## 1. Cinematique de Timoshenko

Dans le repere local $(x,y,z)$, l'axe moyen est $x$. Les inconnues de section
sont

$$
\mathbf q(x)=
\begin{bmatrix}u&v&w&\theta_x&\theta_y&\theta_z\end{bmatrix}^T.
$$

Les deformations generalisees sont

$$
\varepsilon_x=u',
\quad
\gamma_y=v'-\theta_z,
\quad
\gamma_z=w'+\theta_y,
$$

$$
\kappa_x=\theta_x',
\quad
\kappa_y=\theta_y',
\quad
\kappa_z=\theta_z'.
$$

## 2. Lois de comportement sectionnelles

Pour une poutre isotrope a section constante :

$$
N=EA\varepsilon_x,\qquad
T=GJ\kappa_x,
$$

$$
Q_y=\kappa_y^{s}GA\gamma_y,\qquad
Q_z=\kappa_z^{s}GA\gamma_z,
$$

$$
M_y=EI_y\kappa_y,\qquad
M_z=EI_z\kappa_z.
$$

Les facteurs de correction de cisaillement dependent de la forme de section
et doivent etre fournis comme donnees d'ingenierie.

## 3. Formulation forte

Sans inertie, l'equilibre local d'une poutre droite s'ecrit

$$
N'+p_x=0,\qquad
Q_y'+p_y=0,\qquad
Q_z'+p_z=0,
$$

$$
T'+m_x=0,\qquad
M_y'-Q_z+m_y=0,\qquad
M_z'+Q_y+m_z=0.
$$

Les efforts imposes aux extremites sont les quantites duales des six DDL.

## 4. Formulation faible

Le travail virtuel interne est

$$
\delta W_{int}=
\int_0^L
\left(
\delta\varepsilon_xN+
\delta\gamma_yQ_y+
\delta\gamma_zQ_z+
\delta\kappa_xT+
\delta\kappa_yM_y+
\delta\kappa_zM_z
\right)dx.
$$

Le travail externe regroupe charges reparties, couples repartis et efforts
d'extremite. Le probleme faible cherche $\mathbf q$ cinematiquement
admissible telle que

$$
\delta W_{int}=\delta W_{ext}
\qquad\forall\delta\mathbf q.
$$

## 5. Energie potentielle

Pour une loi elastique lineaire,

$$
\Pi(\mathbf q)=
\frac12\int_0^L
\begin{aligned}[t]
\bigl(&EA\varepsilon_x^2+
\kappa_y^sGA\gamma_y^2+
\kappa_z^sGA\gamma_z^2\\
&+GJ\kappa_x^2+
EI_y\kappa_y^2+
EI_z\kappa_z^2\bigr)
\end{aligned}
\,dx-W_{ext}.
$$

La stationnarite de $\Pi$ redonne la formulation faible. Elle montre pourquoi
la rigidite elementaire est symetrique et pourquoi les six mouvements rigides
ont une energie nulle.

## 6. Conditions de validite

La theorie suppose une poutre slender ou modérément epaisse, une section
indeformable dans son plan et de petites rotations. Elle ne represente pas
le gauchissement non uniforme de torsion, l'ovalisation, les effets locaux de
jonction ou une section plastifiee.

## 7. Tests associes

| ID | Cas | Reference |
| --- | --- | --- |
| BEAM2-FW-01 | traction uniforme | $u(L)=NL/(EA)$ |
| BEAM2-FW-02 | torsion uniforme | $\theta_x(L)=TL/(GJ)$ |
| BEAM2-FW-03 | flexion $y$ | Euler + correction Timoshenko |
| BEAM2-FW-04 | flexion $z$ | Euler + correction Timoshenko |
| BEAM2-FW-05 | six modes rigides | energie nulle |
| BEAM2-FW-06 | rotation globale | invariance de la reponse |

## 8. Exemple executable

```powershell
python .\qf_solver.py solve --input .\examples\beam2_cantilever.json `
  --output .\results\beam2_weak_form.json
python -m pytest tests\unit\test_beam2_element.py
```

## 9. Resultats a publier

Le rapport doit exposer fleches, rotations, reactions, efforts sectionnels,
energies axiale/cisaillement/torsion/flexion et ratio de cisaillement. Le
repere local et la direction de reference doivent accompagner toute figure.

## 10. References

`REF-BEAM-TIMOSHENKO-1921`, `REF-FEM-BATHE`, code
`solveur/elements/beam/beam2.py`, tests unitaires et correlation Code_Aster
`POU_D_E`. Le statut reste experimental hors du domaine effectivement
compare.
