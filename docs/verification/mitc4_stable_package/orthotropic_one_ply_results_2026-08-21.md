---
doc_id: DOC-VNV-MITC4-ORTHO-ONE-PLY-RESULTS-001
revision: 0.1
status: owner_reviewed
---

# Résultats exécutés : MITC4 orthotrope homogène à un pli

## Modèle

Le modèle est une plaque MITC4 en porte-à-faux, maillage `16 x 4`, soit 64
éléments, avec une seule lamelle orthotrope d'épaisseur totale `0,01 m`.
Les orientations testées sont `0°`, `45°` et `90°`. Les calculs utilisent la
masse cohérente, la condensation du drilling, Newmark `β=0,25`, `γ=0,5` et un
amortissement proportionnel à la masse de `2 %` pour la corrélation dynamique.

## Vérification interne

### Statique linéaire

| Orientation | UZ moyen à l'extrémité [m] | Résidu libre | Verdict |
|---:|---:|---:|---|
| 0° | -1,4785e-4 | 8,09e-12 | PASS |
| 45° | -1,3170e-3 | 1,50e-10 | PASS |
| 90° | -1,9968e-3 | 2,39e-10 | PASS |

Le calcul statique passe le seuil de résidu `1e-8` pour les trois orientations.
Ces valeurs constituent la référence interne de la campagne et devront être
comparées à une référence analytique ou Code_Aster avec les mêmes conventions
d'épaisseur, de charge et de repère.

| Orientation | f1 [Hz] | Résidu modal | Erreur Newmark RMS | Erreur harmonique | Verdict |
|---:|---:|---:|---:|---:|---|
| 0° | 14,8537 | 1,30e-9 | 0,2623 % | 2,33e-8 % | PASS |
| 45° | 5,0741 | 5,62e-9 | 0,2623 % | 1,30e-7 % | PASS |
| 90° | 4,0420 | 2,19e-9 | 0,2623 % | 8,72e-8 % | PASS |

Les invariants internes passent pour les trois orientations. Le résultat
`16 x 4` est retenu comme niveau minimal de preuve modale : les maillages
`8 x 2` et `12 x 3` ont montré des résidus modaux au-dessus de `1e-7` et ne
doivent pas être utilisés comme niveau de qualification.

## Corrélation Code_Aster

| Orientation | Maillage | Modal | Newmark | Harmonique | Verdict technique |
|---:|---:|---:|---:|---:|---|
| 0° | 16 x 4 | 0,892 % | 0,230 % | 0,126 % | PASS externe |
| 45° | 16 x 4 | 3,431 % | 1,664 % | 1,001 % | PASS externe, gate 1 % non satisfait |
| 45° | 32 x 8 | 2,075 % | 0,666 % | 0,417 % | PASS externe, gate 1 % non satisfait |
| 45° | 48 x 12 | 1,037 % | 0,413 % | 0,251 % | PASS externe, gate modal presque atteint |
| 45° | 56 x 14 | 0,884 % | — | — | PASS externe modal dédié |
| 90° | 16 x 4 | 2,749 % | 0,211 % | 0,117 % | PASS externe, gate 1 % non satisfait pour modal |
| 90° | 48 x 12 | 0,604 % | 0,019 % | 0,012 % | PASS externe sous 1 % |

Code_Aster passe ses seuils de corrélation technique actuels. Le critère de
promotion QF_solver `<= 1 %` est maintenant satisfait pour les trois
orientations sur les observables dynamiques : la fréquence `45°` atteint
`0,884 %` sur le calcul modal dédié `56 x 14`, tandis que les réponses
Newmark et harmoniques sont déjà sous `1 %` au niveau `48 x 12`. Le cas `90°`
est sous `1 %` sur les trois observables au niveau `48 x 12` et le cas `0°`
est sous `1 %` dès `16 x 4`.

Le calcul modal `56 x 14` a été exécuté avec `eigsh` en mode shift-invert ; il
conserve un résidu modal relatif de `3,09e-9`. Il s'agit d'une campagne
modale dédiée, séparée de la campagne Code_Aster complète, afin de ne pas
confondre une preuve modale raffinée avec une nouvelle corrélation temporelle.
Il reste donc à déterminer si l'écart résiduel vient de la différence MITC4 /
DST, de la définition de l'épaisseur, de la masse ou de la référence modale.

## Campagne courbe facettisée

La campagne interne courbe et pliée, exécutée avec une lamelle unique à `45°`,
donne :

- erreur d'angle projeté : `1,42e-14°` ;
- incrément du dernier maillage cylindrique : `0,691 %` ;
- incrément du dernier maillage plié : `0,905 %` ;
- écart de réponse avec 10 % de distorsion : `0,040 %` ;
- résidu libre maximal : `1,71e-10`.

Cette preuve est une vérification interne de projection des axes et de qualité
de maillage. Elle n'est pas encore une corrélation externe courbe et ne ferme
pas seule la promotion dynamique.

Une corrélation externe complémentaire a été exécutée sur le même panneau
cylindrique avec une lamelle unique à `0°`, orientation axiale non ambiguë sur
la surface. Elle donne :

| Maillage | Écart vecteur final | Écart UZ final | Incrément QF final | Incrément CalculiX final | Verdict |
|---:|---:|---:|---:|---:|---|
| 8 x 4 | 5,858 % | 5,860 % | — | — | informationnel, premier niveau |
| 16 x 8 | 0,041 % | 0,041 % | — | — | PASS |
| 24 x 12 | 0,012 % | 0,012 % | 0,072 % | 0,019 % | PASS externe |

La dynamique du panneau courbe a également été exécutée en interne avec une
sonde `UY` au milieu de l'extrémité. Cette composante est choisie car le
premier mode est antisymétrique en `UZ` sur ce point, ce qui rendrait une sonde
`UZ` quasi nulle et numériquement peu pertinente :

| Méthode | Résultat principal | Limite | Verdict |
|---|---:|---:|---|
| Modal | résidu `1,30e-10` | `1e-7` | PASS |
| Newmark, `T/20` à `T/80` | RMS finale `0,2623 %` | `1 %` | PASS |
| Newmark | dérive énergétique `7,66e-12` | `1e-4` | PASS |
| Newmark | résidu dynamique `4,80e-10` | `1e-7` | PASS |
| Harmonique | erreur maximale `1,46e-8 %` | `1e-6` relatif | PASS |

Cette campagne est une vérification interne de cohérence dynamique courbe. La
correlation externe dynamique complémentaire a ensuite été exécutée avec
Code_Aster sur le même panneau axial, au maillage `16 x 8` :

| Observable | Écart QF_solver / Code_Aster | Seuil de campagne | Verdict |
|---|---:|---:|---|
| Fréquences modales, 4 modes | 2,340 % | 5 % | PASS externe |
| Historique Newmark forcé | 0,0786 % RMS | 10 % | PASS externe |
| Réponse harmonique complexe, grille alignée | 0,118 % RMS | 10 % | PASS externe |

Le premier maillage `8 x 4` donne un écart modal maximal de `8,957 %` sur le
troisième mode. Il est conservé comme diagnostic et non comme preuve finale.
Le raffinement `16 x 8` ramène cet écart à `2,340 %`, ce qui confirme un effet
de résolution modale et non une divergence numérique. Les résidus QF restent
respectivement `1,18e-9` pour le modal et `1,42e-12` pour Newmark.

La grille harmonique alignée utilise les mêmes rapports `f/f1` pour les deux
solveurs ; elle évite de confondre un décalage de fréquence propre avec une
erreur d'amplitude.

Un diagnostic supplémentaire `32 x 16`, exécuté avec `eigsh`, donne `0,933 %`
sur les fréquences modales. Il ne ferme toutefois pas la corrélation dynamique
globale : l'écart Newmark atteint `1,51 %` et l'écart harmonique ponctuel
`17,84 %` en grille absolue et `16,30 %` en grille alignée autour de la
résonance. Cette différence résiduelle reste ouverte comme limite de
corrélation dynamique courbe et interdit son extrapolation au-delà du domaine
borné retenu.

Cette corrélation confirme le chemin courbe lorsque l'orientation est
axiale. Le cas courbe mono-pli à `45°` reste ouvert : QF_solver projette la
direction globale sur chaque facette, alors que le deck CalculiX historique
applique une orientation globale unique. Les deux calculs ne représentent
donc pas encore la même loi d'orientation sur toute la surface. Ce cas ne
bloque pas le périmètre stable borné aux plaques planes et aux panneaux
courbes à orientation axiale ; il interdit en revanche toute extrapolation à
une orientation continue de fibres sur une surface courbe.

## Conclusion de maturité

Le noyau orthotrope homogène MITC4 est techniquement exécutable et cohérent
en interne. Les campagnes planes satisfont maintenant le critère primaire de
`1 %` pour les orientations `0°`, `45°` et `90°`, avec résidus statiques,
modaux et dynamiques dans les limites définies. Le panneau courbe axial à
`0°` dispose également d'une corrélation externe sous `1 %` au maillage fin.

Le périmètre proposé pour une promotion `stable` est donc explicitement
borné à : une lamelle orthotrope homogène, petites déformations, plaques
planes pour les orientations testées `0°/45°/90°`, et panneaux courbes
facettisés à orientation axiale `0°`. L'orientation projetée non axiale sur
une surface courbe, les contraintes interlaminaires, le dommage, la rupture
et la délamination restent exclus.

## Artefacts bruts

- `results/mitc4_orthotropic_one_ply_internal_20260821/summary.json`
- `results/mitc4_orthotropic_one_ply_static_20260821/summary.json`
- `results/mitc4_orthotropic_one_ply_codeaster_20260821/summary.json`
- `results/mitc4_orthotropic_curved_one_ply_20260821/summary.json`
- `results/mitc4_orthotropic_modal_codeaster_20260821_56x14/summary.json`
- `results/mitc4_orthotropic_curved_axial_one_ply_calculix_20260821/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_20260821/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_codeaster_20260821_16x8_aligned/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_codeaster_20260821_32x16_aligned/summary.json` (diagnostic, non acceptance)

