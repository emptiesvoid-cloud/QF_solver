---
doc_id: DOC-COMP-004
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Criteres de premier pli

## Domaine et interpretation

Les criteres sont evalues dans les axes materiau `1-2` de chaque pli, aux
positions `lower`, `middle` et `upper`. Les resistances sont des magnitudes
strictement positives : `Xt`, `Xc`, `Yt`, `Yc` et `S12`.

Un indice inferieur ou egal a `1` est conforme au critere. Un indice superieur
a `1` signale une **rupture de premier pli predite**. QF_solver ne modifie pas
la rigidite apres ce franchissement : il ne s'agit ni d'un modele de dommage,
ni d'une simulation de rupture progressive.

## Contrainte maximale

Pour les contraintes materiau `sigma1`, `sigma2`, `tau12`, les utilisations
sont :

\[
r_1=\begin{cases}\sigma_1/X_t&\sigma_1\geq0\\-\sigma_1/X_c&\sigma_1<0\end{cases},
\quad
r_2=\begin{cases}\sigma_2/Y_t&\sigma_2\geq0\\-\sigma_2/Y_c&\sigma_2<0\end{cases},
\quad
r_6=|\tau_{12}|/S_{12}.
\]

\[
FI_{MS}=\max(r_1,r_2,r_6), \qquad RF_{MS}=1/FI_{MS}.
\]

Ce critere identifie directement le mode dimensionnant, mais ne represente
aucune interaction entre contraintes normales et cisaillement.

## Deformation maximale

La meme convention est appliquee aux deformations d'ingenieur avec les
limites positives `e1t`, `e1c`, `e2t`, `e2c` et `g12`. La composante de
cisaillement est `gamma12`, et non la composante tensorielle `epsilon12`.

\[
FI_{ME}=\max\left(
\frac{\varepsilon_1}{e_{1t/c}},
\frac{\varepsilon_2}{e_{2t/c}},
\frac{|\gamma_{12}|}{g_{12}}
\right).
\]

## Tsai-Hill

QF_solver utilise la convention Azzi-Tsai suivante, avec `X` et `Y` choisis
selon le signe des contraintes :

\[
FI_{TH}=\left(\frac{\sigma_1}{X}\right)^2
-\frac{\sigma_1\sigma_2}{X^2}
+\left(\frac{\sigma_2}{Y}\right)^2
+\left(\frac{\tau_{12}}{S_{12}}\right)^2.
\]

Le facteur de reserve sous chargement proportionnel est :

\[
RF_{TH}=1/\sqrt{FI_{TH}}.
\]

## Tsai-Wu

La forme en contraintes planes est :

\[
FI_{TW}=F_1\sigma_1+F_2\sigma_2
+F_{11}\sigma_1^2+F_{22}\sigma_2^2
+2F_{12}\sigma_1\sigma_2+F_{66}\tau_{12}^2,
\]

avec :

\[
F_1=\frac1{X_t}-\frac1{X_c},\quad
F_{11}=\frac1{X_tX_c},\quad
F_2=\frac1{Y_t}-\frac1{Y_c},\quad
F_{22}=\frac1{Y_tY_c},\quad
F_{66}=\frac1{S_{12}^2}.
\]

Le terme d'interaction est defini par :

\[
F_{12}=f_{12}^{*}\sqrt{F_{11}F_{22}}, \qquad -1<f_{12}^{*}<1.
\]

La valeur par defaut `f12_star=-0.5` est une hypothese documentee, pas une
donnee mesuree. Pour une utilisation industrielle, elle doit etre remplacee
par une valeur issue d'essais biaxiaux tracables. Le facteur de reserve est la
plus petite racine positive de :

\[
Q RF^2+L RF-1=0,
\]

ou `L` et `Q` sont respectivement les parties lineaire et quadratique de
Tsai-Wu sur l'etat de contrainte courant.

## Format JSON

```json
{
  "strengths": {
    "Xt": 1500000000.0,
    "Xc": 1200000000.0,
    "Yt": 50000000.0,
    "Yc": 200000000.0,
    "S12": 75000000.0,
    "f12_star": -0.5
  },
  "strain_allowables": {
    "e1t": 0.015,
    "e1c": 0.012,
    "e2t": 0.005,
    "e2c": 0.02,
    "g12": 0.03
  }
}
```

Les sorties `failure_indices` sont indexees par critere. Le champ
`failure_summary` donne le pli, la position, l'indice et le facteur de reserve
les plus critiques pour chaque critere.

References : [Azzi-Tsai](../reference/references.md#ref-comp-azzi-tsai) et
[Tsai-Wu](../reference/references.md#ref-comp-tsai-wu).

