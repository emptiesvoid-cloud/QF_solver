---
doc_id: DOC-ELEM-TET4-01
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - Geometrie, orientation et ddl

## Domaine geometrique

Le TET4 est l'image affine du tetraedre de reference

$$
\hat\Omega=\{(r,s,t)\mid r\ge0,\ s\ge0,\ t\ge0,\ r+s+t\le1\}.
$$

Les noeuds locaux 1 a 4 correspondent a $(0,0,0)$, $(1,0,0)$,
$(0,1,0)$ et $(0,0,1)$. L'ordre est oriente. Avec

$$
\mathbf A=[\mathbf x_2-\mathbf x_1\quad
\mathbf x_3-\mathbf x_1\quad\mathbf x_4-\mathbf x_1],
$$

le volume signe vaut $V_s=\det(\mathbf A)/6$. QF_solver exige $V_s>0$;
un volume nul ou negatif interdit la resolution.

## Degres de liberte

Chaque noeud possede trois translations globales:

$$
\mathbf u_e=[u_1,v_1,w_1,\ldots,u_4,v_4,w_4]^T\in\mathbb R^{12}.
$$

Il n'existe aucun ddl de rotation. Une rotation rigide est representee par les
translations nodales $\mathbf u_i=\boldsymbol\omega\times\mathbf x_i$.

## Six modes rigides

Un element libre doit annuler trois translations et trois rotations. Les
vecteurs associes satisfont $\mathbf K_e\mathbf r_j\simeq0$. Cette propriete
est controlee par valeurs propres et residus, avec une tolerance relative a la
norme de $\mathbf K_e$.

## Connectivite globale

Les identifiants Gmsh sont remappes vers des indices contigus et
deterministes. Pour TET4, une reorientation explicite echange les sommets 2 et
3. Aucune reparation silencieuse n'est permise: l'option doit etre demandee et
la modification est inscrite dans le rapport d'import.

## Consequence mecanique

Une geometrie affine donne une deformation constante par element. Le TET4 est
robuste pour des champs proches de l'affine mais raide en flexion et sensible
au verrouillage volumique lorsque $\nu\rightarrow0.5$.

Code: `solveur/elements/solid/tet4.py`. Exigence: `REQ-SOL-001`.

