---
doc_id: DOC-VV-CONTENT-CLOSURE-001
revision: 0.3-candidate
status: ready_for_owner_review
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Complements de champs, convergence et correlation

## Portee de cette revision

Cette page complete le dossier technique apres la validation du PDF 0.2.0 du
1er aout 2026. Elle ne modifie pas retroactivement ce PDF et ne transforme
aucune demonstration en qualification. Les contenus ajoutes seront integres a
une revision candidate distincte, soumise a une nouvelle Owner review.

La source de verite transverse est
`qualification/technical_content_coverage.json`. Elle relie chaque famille
d'element a son contrat de chargement, chaque couple element-analyse a une base
de comparaison et chaque methode a ses invariants. Lorsqu'un oracle externe ou
analytique n'est pas disponible, le registre porte explicitement
`gap_documented`; cette valeur n'est jamais assimilee a un resultat mecanique
`PASS`.

## Grandeurs representees

Les cartes de solides utilisent la deformation equivalente de von Mises issue
du vecteur de Voigt a cisaillements d'ingenieur

\[
\boldsymbol\varepsilon_V =
\begin{bmatrix}
\varepsilon_{xx} & \varepsilon_{yy} & \varepsilon_{zz} &
\gamma_{xy} & \gamma_{yz} & \gamma_{zx}
\end{bmatrix}^{\mathsf T}.
\]

Le tenseur de deformation est reconstruit avec
\(\varepsilon_{xy}=\gamma_{xy}/2\), puis la partie deviatorique
\(\boldsymbol e=\boldsymbol\varepsilon-\operatorname{tr}(\boldsymbol\varepsilon)
\boldsymbol I/3\) conduit a

\[
\varepsilon_{\mathrm{eq}}
=\sqrt{\frac{2}{3}\,\boldsymbol e:\boldsymbol e}.
\]

Pour les coques, la grandeur scalaire publiee est la norme maximale des
deformations de face, calculee sur `shell_down` et `shell_up` :

\[
\varepsilon_{\mathrm{face}}
=\sqrt{\varepsilon_{xx}^{2}+\varepsilon_{yy}^{2}
+\frac{1}{2}\gamma_{xy}^{2}}.
\]

Cette norme sert a localiser la deformation; elle ne remplace ni les
composantes locales, ni les resultantes \(N\), \(M\), \(Q\), ni les valeurs
par pli. Pour BEAM2, la carte represente la norme des courbures generalisees
\(\|[\kappa_x,\kappa_y,\kappa_z]\|_2\). Pour la plasticite J2, une carte
separee montre la deformation plastique equivalente cumulee.

Chaque figure est tracee sur la geometrie deformee, avec le maillage initial
en surimpression, une amplification indiquee dans le titre, une barre de
couleur et une palette perceptuellement ordonnee. Les valeurs restent
elementaires ou aux faces; aucune extrapolation nodale lissante n'est utilisee
dans ces cartes documentaires.

## Contrat commun des chargements

Un chargement distribue n'est publiable que si les sept informations suivantes
sont disponibles : support geometrique, repere d'expression, convention de
signe, unite, resultante, moment resultant et test de conservation. Les
conditions de rejet font partie du contrat : groupe physique absent, face ou
arete non conforme, DDL incompatible, normale invalide, valeur non finie ou
materiau sans densite lorsqu'une force d'inertie est demandee.

Les pages `matrices_charges.md` restent la reference par element. Le tableau
regenere ci-dessous donne la couverture transverse et les tests qui la
protegent. Une action mentionnee comme supportee ne signifie pas qu'elle a la
meme maturite pour toutes les geometries.

## Lecture des correlations

Trois niveaux sont distingues :

1. une solution analytique ou un invariant independant du noyau EF ;
2. une correlation reproductible avec Code_Aster ou CalculiX, version et
   environnement traces ;
3. un ecart V&V documente lorsqu'aucun oracle suffisamment proche n'est
   disponible.

Les vues synchronisees utilisent le meme maillage, la meme grille temporelle
ou les memes frequences lorsque la preuve source le permet. Les comparaisons
entre formulations differentes, par exemple MITC3 et DKT, restent qualifiees
de correlations et non d'identites elementaires.

--8<-- "docs/generated/technical_content_coverage.md"

## Interpretation des ecarts maintenus

Les lignes `gap_documented` sont des limites actives. Elles interdisent de
presenter comme valides le materiau non lineaire TET10 sans benchmark dedie,
la dynamique multicouche MITC4 sans campagne propre, et les routes composites
MITC3 au-dela de leurs tests d'execution. Leur fermeture demandera une nouvelle
campagne V&V et une decision Owner distincte; une amelioration de la seule
documentation ne suffira pas.

## Reproduction

```powershell
python .\scripts\build_docs.py --profile engineering --assets-only
python -m pytest tests\documentation\test_docs_fields.py `
  tests\documentation\test_technical_content_closure.py
```

Le manifeste documentaire conserve les empreintes des images et du tableau
regenere. Le registre refuse toute paire element-analyse absente, tout statut
different de la matrice autoritative et tout chemin de preuve orphelin.
