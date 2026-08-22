---
doc_id: DOC-AUDIT-MITC4-ORTHO-ONE-PLY-CLOSURE-001
revision: 0.1
status: owner_reviewed
---

# Audit de clôture - MITC4 orthotrope homogène à un pli

Ce document vérifie le paquet de promotion sans attribuer automatiquement le
statut `stable`. Le périmètre proposé est limité à une lamelle orthotrope
homogène, aux petites déformations, aux plaques planes `0°/45°/90°` et aux
panneaux courbes facettisés à orientation axiale `0°`.

## État des exigences

| Exigence | Preuve | État |
|---|---|---|
| Statique linéaire plane | Résidus libres `8,09e-12` à `2,39e-10`, orientations `0°/45°/90°` | PASS |
| Statique courbe axiale | CalculiX S8R, panneau `24×12`, écart UZ `0,012 %` | PASS externe |
| Modal plan | Code_Aster, maillages raffinés, erreurs finales `0,892 %`, `0,884 %`, `0,604 %` | PASS sous 1 % |
| Modal courbe interne | Résidu `1,30e-10`, orthogonalités et condensation vérifiées | PASS interne |
| Modal courbe externe | Code_Aster, `16×8`, écart maximal `2,340 %` | PASS dans seuil externe 5 %, hors critère primaire 1 % |
| Newmark plan | Raffinement temporel et corrélations Code_Aster sous 1 % aux niveaux retenus | PASS |
| Newmark courbe interne | RMS finale `0,2623 %`, résidu `4,80e-10`, dérive énergie `7,66e-12` | PASS interne |
| Newmark courbe externe | Code_Aster, `16×8`, RMS `0,0786 %` | PASS externe |
| Harmonique plan | Limite statique à zéro Hz, résidus et corrélations externes sous 1 % aux niveaux retenus | PASS |
| Harmonique courbe interne | Réponse complexe, limite zéro Hz et pic de résonance vérifiés | PASS interne |
| Harmonique courbe externe | `16×8` aligné : `0,118 %`; diagnostic `32×16` : `16,30 %` | PASS borné / extension ouverte |
| Tests logiciels ciblés | `8 passed, 1 skipped`, Ruff et compilation | PASS |
| Décision Owner signée | `qualification/reviews/mitc4_orthotropic_one_ply_stable_pending.json` | PASS |

## Interprétation de la limite harmonique courbe

L'écart `32×16` ne doit pas être supprimé du dossier. Il apparaît près de la
résonance et reste élevé même lorsque les fréquences sont comparées sur une
grille normalisée par `f1`. Il constitue donc une limite de corrélation entre
MITC4 et DST, et non une preuve suffisante pour extrapoler la formulation à
toute géométrie courbe ou à toute orientation projetée.

Le périmètre stable proposé peut rester borné au protocole courbe axial validé
à `16×8`, avec les observables primaires internes sous `1 %`. Toute extension
vers des maillages plus fins, des orientations courbes non axiales ou une
acceptation harmonique externe générale doit ouvrir une nouvelle campagne.

## Conditions de fermeture

La promotion ne peut être fermée qu'après :

1. réponse Owner aux questions Q1 à Q7 dans `owner_review.md` ;
2. décision explicite `stable` ou décision bornée motivée ;
3. nom, date et signature dans le registre JSON ;
4. vérification que la décision ne couvre pas les exclusions S13/S23, dommage,
   rupture, délamination, grandes déformations et orientation courbe non axiale.

## Conclusion actuelle

**Technique : PASS.**

**Maturité : stable pour le périmètre borné accepté par Owner.**

**Limite conservée : corrélation harmonique courbe au maillage `32×16` hors
acceptance ; cette limite ne couvre pas le périmètre stable signé.**
