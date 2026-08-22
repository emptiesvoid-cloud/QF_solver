---

doc_id: DOC-VNV-MITC4-STABLE-PACKAGE-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
applicable_version: 0.2.1-alpha
reviewer: ""
approver: ""
---

# Étude MITC4 : isotrope, multicouche et orthotrope

Cette étude regroupe trois sous-périmètres MITC4. La décision Owner du
21 août 2026 clôt la promotion `stable` bornée de l'isotrope, du multicouche
plan et de l'orthotrope homogène mono-pli. Les exclusions et les diagnostics
restent contraignants : cette clôture ne vaut pas qualification générale.

Le registre machine-readable est
`qualification/studies/mitc4_stable_package_2026-08-21/study.json`.
Les premiers résultats exécutés sont synthétisés dans
`orthotropic_one_ply_results_2026-08-21.md`.
Le formulaire PDF signable est généré dans
`output/pdf/mitc4_orthotropic_one_ply_stable_owner_review.pdf`.

## 1. Décision attendue

Le paquet est organisé autour de quatre méthodes : statique linéaire, modal,
Newmark linéaire et réponse harmonique. Une promotion `stable` exige que les
observables primaires soient sous 1 % lorsque la référence est définie, que les
résidus soient acceptables, que la convergence soit visible et qu'une Owner
Review séparée soit signée pour chaque sous-périmètre.

La décision de l'un des sous-périmètres ne doit pas être propagée aux deux
autres. En particulier, la preuve des solides orthotropes TET4/TET10 ne vaut pas
preuve d'une coque MITC4 orthotrope.

## 2. Sous-périmètre isotrope

Le MITC4 isotrope est déjà enregistré `stable` dans la baseline actuelle. Cette
partie sert de témoin de non-régression : patch membrane, flexion, cisaillement,
shear locking, modal, Newmark et harmonique doivent continuer à passer.

Les comparaisons Code_Aster et CalculiX restent des corrélations de formulations
distinctes. Elles ne doivent pas être présentées comme une identité entre les
éléments.

## 3. Sous-périmètre multicouche

Le matériau `shell_laminate` calcule les matrices `A`, `B` et `D`, projette les
axes de chaque pli dans le repère de la facette et récupère les contraintes
membranaires dans les axes matériau. Les empilements actuellement documentés
sont `[0/90/90/0]`, `[45/-45/-45/45]` et `[0/45/45/0]`.

La preuve statique plane et la preuve dynamique sont maintenant promues en
`stable` dans un domaine borné. La dynamique reste limitée aux trois
empilements, à la masse, à l'amortissement et aux géométries réellement
calculés. S13/S23, dommage, rupture et délamination sont exclus des critères
d'acceptation.

La décision Owner du 21 août 2026 est enregistrée dans
`qualification/reviews/mitc4_laminate_dynamic_refined_three_layups_stable_owner_review_pending.json`.
Elle utilise `accepted_with_recommendations` comme décision machine-readable et
`stable` comme cible de promotion.

## 4. Sous-périmètre orthotrope

Le cas orthotrope proposé est une lamelle unique dans `shell_laminate`. Cette
construction est utile pour tester l'anisotropie membrane/flexion d'une coque,
mais elle ne constitue pas encore un matériau coque orthotrope autonome.

Les essais obligatoires sont :

1. patch affine selon les axes 0°, 45° et 90° ;
2. invariance par rotation du repère global ;
3. flexion et cisaillement transverse ;
4. fréquences propres et orthogonalité de masse ;
5. Newmark avec raffinement temporel ;
6. réponse harmonique et limite statique à fréquence nulle ;
7. corrélation Code_Aster sur plaque plane ;
8. répétition sur panneau courbe facettisé.

La campagne interne et les corrélations planes sont maintenant exécutées sur
les trois orientations. Après raffinement, le modal `45°` atteint `0,884 %`
sur `56 x 14`, le modal `90°` `0,604 %` sur `48 x 12`, et les observables
Newmark/harmoniques restent sous `1 %`. Une corrélation CalculiX complémentaire
sur panneau courbe facettisé à orientation axiale `0°` atteint `0,012 %` sur
`UZ` au maillage fin.

Le même panneau possède maintenant une campagne dynamique interne dédiée
(modal, Newmark et harmonique) et une corrélation externe Code_Aster au
maillage `16 x 8`. Le premier maillage `8 x 4` reste publié comme diagnostic
de raffinement modal, avec son écart non masqué. Le diagnostic `32 x 16`
montre que la fréquence converge sous 1 %, mais que l'amplitude harmonique
ponctuelle près de la résonance reste sensible au décalage de fréquence entre
MITC4 et DST ; il n'est donc pas utilisé pour une promotion automatique.

Le paquet est donc promu `stable` pour le périmètre borné accepté par Owner.
Le cas courbe non axial à `45°` reste ouvert, car l'orientation projetée par
facette de QF_solver n'est pas encore représentée par le deck CalculiX avec
la même loi locale. Il ne doit pas être extrapolé au périmètre stable.

## 5. Observables et figures

Chaque campagne doit publier :

- le maillage initial et déformé avec une légende lisible ;
- les blocages, charges et repère matériau ;
- les déplacements, contraintes locales et contraintes dans les axes matériau ;
- les fréquences, formes propres, amplitude et phase ;
- les résidus, bilans d'énergie et incréments de raffinement ;
- le tableau QF_solver / théorie / Code_Aster / CalculiX lorsque disponible ;
- le manifeste des entrées, versions, unités et empreintes.

Les cartes de contraintes ponctuelles aux singularités restent informatives et
ne doivent pas être utilisées comme observable primaire d'acceptation.

## 6. Questions Owner Review

**Q1.** Les trois sous-périmètres sont-ils séparés correctement, sans
extrapolation entre isotrope, multicouche et orthotrope ?

**Q2.** Les méthodes statique, modal, Newmark et harmonique sont-elles
couvertes par des preuves et des figures suffisantes dans le domaine annoncé ?

**Q3.** Les limites, notamment les exclusions S13/S23, dommage, délamination,
grandes déformations et orientation continue courbe, sont-elles acceptables ?

**Q4.** Le seuil de 1 % sur les observables primaires est-il accepté lorsque
la référence est suffisamment définie ?

**Q5.** Décision par sous-scope : `stable`, `accepted_with_recommendations`,
`accepted_for_bounded_engineering_use` ou `more_evidence_required`.

| Sous-périmètre | Décision enregistrée | Cible |
|---|---|---|
| `mitc4-isotropic` | `stable` | stable borné |
| `mitc4-laminate` | `stable` pour la statique plane et les trois layups dynamiques | stable borné |
| `mitc4-orthotropic-homogeneous-ply` | `stable` dans le périmètre documenté | stable borné |

**Owner :** Quentin Farinazzo (déclaration électronique)

**Date :** 2026-08-21

## 7. Références de preuve existantes

- `docs/verification/mitc4_classic_stable_owner_review.md`
- `docs/verification/mitc4_laminate_static_planar_stable_owner_review.md`
- `docs/verification/mitc4_laminate_dynamic_refined_three_layups_stable_owner_review.md`
- `qualification/vnv/external/code_aster_composite_nafems/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/summary.json`
- `results/mitc4_orthotropic_modal_codeaster_20260821_56x14/summary.json`
- `results/mitc4_orthotropic_curved_axial_one_ply_calculix_20260821/summary.json`
