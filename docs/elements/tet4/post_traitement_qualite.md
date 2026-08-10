---
doc_id: DOC-ELEM-TET4-04
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - Post-traitement et qualite

## Champs elementaires

La deformation et la contrainte sont constantes:

$$
\boldsymbol\varepsilon_e=\mathbf B\mathbf u_e,
\qquad
\boldsymbol\sigma_e=\mathbf D\boldsymbol\varepsilon_e.
$$

QF_solver exporte les tenseurs de contrainte et deformation, leurs valeurs
principales, les traces, la partie deviatorique, la pression hydrostatique et
la contrainte de von Mises.

Les sorties disponibles sont: JSON d'audit, CSV nodal/elementaire et VTU pour
ParaView. Le JSON porte le statut, les unites, les residus et les avertissements;
le CSV sert a la comparaison tabulaire; le VTU porte les champs de visualisation.
Les resultats elementaires sont la reference mecanique; les champs nodaux
lisses sont explicitement des aides de lecture.

## Invariants

Avec $\mathbf s=\boldsymbol\sigma-\tfrac13\operatorname{tr}(\boldsymbol\sigma)\mathbf I$:

$$
p=-\frac13\operatorname{tr}(\boldsymbol\sigma),
\qquad \sigma_{VM}=\sqrt{\frac32\mathbf s:\mathbf s}.
$$

Les cisaillements du vecteur de contrainte sont tensoriels; ceux du vecteur de
deformation sont ingenieur. Cette distinction est appliquee dans les
transformations de Voigt.

## Valeurs nodales

Une moyenne des valeurs des elements incidents est fournie pour la
visualisation. Elle n'augmente pas l'ordre de la solution et ne doit pas etre
utilisee comme preuve d'une contrainte locale. Les valeurs elementaires
restent l'autorite numerique.

## Indicateurs de maillage

Le controle calcule volume signe, volume absolu relatif, longueurs d'aretes,
aspect ratio et indicateur de skew. Un volume trop faible ou negatif produit
`FAIL`; une qualite faible mais admissible produit `WARNING`.

## Limites physiques

- flexion sur-raide sur maillage grossier;
- contraintes discontinues aux interfaces;
- verrouillage volumique pres de l'incompressibilite;
- forte sensibilite aux slivers;
- pas de contact ni grandes transformations dans le perimetre stable.

Code: `solveur/post/stress.py`, `solveur/mesh/quality.py`.
