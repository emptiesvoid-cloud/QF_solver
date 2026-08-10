---
doc_id: DOC-ELEM-MITC3-05
revision: 0.1
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Post-traitement et qualite

## Grandeurs au barycentre

Le post-traitement reconstruit au barycentre:

- $\boldsymbol\varepsilon_m$, $\boldsymbol\kappa$ et
  $\boldsymbol\gamma_s$;
- les resultantes $\mathbf N$, $\mathbf M$ et $\mathbf Q$;
- les contraintes aux faces $z=-t/2$ et $z=+t/2$;
- les contributions d'energie membrane, flexion, cisaillement et drilling.

Pour un isotrope,

$$
\boldsymbol\sigma(z)=\mathbf C_m
(\boldsymbol\varepsilon_m+z\boldsymbol\kappa).
$$

Pour un stratifie, les contraintes sont calculees aux positions lower,
middle et upper de chaque pli, dans les axes elementaires puis materiau.
En harmonique, chaque composante conserve partie reelle, partie imaginaire,
amplitude et phase. Les indices de rupture ne sont pas appliques directement
a une contrainte complexe.

## Indicateurs de maillage

Le controle calcule l'aire, les trois longueurs d'arete, le ratio
$\ell_{\max}/\ell_{\min}$ et un indicateur de qualite triangulaire. Il rejette:

- noeuds repetes;
- aire nulle ou trop petite;
- connectivite hors plage;
- orientation incoherente entre facettes;
- arete partagee par plus de deux coques.

Les maillages mixtes MITC3/MITC4 utilisent le meme graphe d'aretes et les
memes conventions de normale.

## Singularites

Une contrainte ponctuelle au voisinage d'un encastrement, d'une charge
ponctuelle ou d'un angle rentrant peut diverger avec le raffinement. Ces pics
ne doivent pas devenir un critere d'acceptation sans protocole de chemin,
bande ou linearisation. Les resultantes globales et contraintes hors zone
singuliere restent exploitables dans le domaine documente.

