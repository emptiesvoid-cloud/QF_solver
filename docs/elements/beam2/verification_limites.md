---
doc_id: DOC-ELEM-BEAM2-04
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# BEAM2 - Verification, convergence et limites

## 1. Hierarchie V&V

La validation suit quatre niveaux : tests algebriques elementaires, solutions
analytiques de poutre, convergence multi-elements et correlation externe sur
le meme modele.

## 2. Traction

Pour une barre encastree chargee par $N$ :

$$
u(L)=\frac{NL}{EA},
\qquad
U=\frac{N^2L}{2EA}.
$$

Le test controle deplacement, reaction, effort axial et energie.

## 3. Torsion

Pour une torsion de Saint-Venant :

$$
\theta_x(L)=\frac{TL}{GJ},
\qquad
U_T=\frac{T^2L}{2GJ}.
$$

$J$ doit provenir d'une definition de section coherente; l'element ne calcule
pas le gauchissement.

## 4. Flexion avec cisaillement

Pour une force transverse $P$ en bout :

$$
v(L)=\frac{PL^3}{3EI}+\frac{PL}{\kappa_sGA}.
$$

La premiere contribution est la flexion Euler-Bernoulli, la seconde la
deformation de cisaillement. Les deux doivent etre comparees separement.

## 5. Convergence

Un porte-a-faux est discretise avec 1, 2, 4, 8, 16 et 32 elements. On publie
les erreurs de fleche, rotation, energie et effort de section. La convergence
ne doit pas etre jugee uniquement sur un deplacement d'extremite.

## 6. Modes propres

La masse coherente est controlee sur les premieres frequences de flexion :

$$
f_n=\frac{\beta_n^2}{2\pi L^2}
\sqrt{\frac{EI}{\rho A}}
$$

dans la limite Euler-Bernoulli elancee. Pour une poutre epaisse, la reference
Timoshenko ou une correlation externe est requise.

## 7. Correlation Code_Aster

Le cas `VNV-BEAM2-CODEASTER-POUDE-001` compare axial, torsion et flexion sur
un maillage et des proprietes identiques. L'ecart doit etre publie avec la
version Code_Aster, la commande, les empreintes et l'explication des
differences de theorie.

Le cas additionnel `VNV-BEAM2-NEWMARK-CODEASTER-POUDE-003` applique une
impulsion axiale lisse a la pointe d'un porte-a-faux elance et compare chaque
pas Newmark au calcul `DYNA_VIBRA` de Code_Aster. Il verifie le chemin axial
masse coherente, chargement temporel et reduction des DDL. Il ne vaut pas une
validation de la dynamique de flexion Timoshenko ni de l'harmonique.

## 8. Matrice de dix tests

| ID | Cas | Observable |
| --- | --- | --- |
| BEAM2-VV-01 | traction | $u$, $N$, reaction |
| BEAM2-VV-02 | torsion | $\theta_x$, $T$ |
| BEAM2-VV-03 | flexion locale $y$ | $v$, $\theta_z$, $M_z$ |
| BEAM2-VV-04 | flexion locale $z$ | $w$, $\theta_y$, $M_y$ |
| BEAM2-VV-05 | cisaillement epais | part $PL/(\kappa GA)$ |
| BEAM2-VV-06 | charge repartie | force/moment |
| BEAM2-VV-07 | repere tourne | objectivite |
| BEAM2-VV-08 | libre-libre | six modes rigides |
| BEAM2-VV-09 | modal | frequences et residus |
| BEAM2-VV-10 | assemblage spatial | equilibre aux jonctions |

## 9. Commandes

```powershell
python -m pytest tests\unit\test_beam2_element.py `
  tests\unit\test_beam2_benchmark.py `
  tests\verification\test_code_aster_beam2_vnv.py
```

## 10. Decision de maturite

Une page complete et dix tests verts ne suffisent pas a qualifier l'element.
La maturite exige une Owner review, des seuils traces, une baseline
reproductible et une campagne couvrant effectivement les poutres epaisses,
charges reparties, assemblages et dynamique revendiques.
