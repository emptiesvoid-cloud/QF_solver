---
doc_id: VNV-PLAN-MITC3-TET4-TL-ORTHO-001
revision: 0.1
status: technical_evidence_ready_owner_review
date: 2026-08-22
applicable_version: 0.2.1a0
review_mode: owner_review
---

# Plan V&V : MITC3 dynamique, MITC3 courbe, TET4 total-lagrangien et orthotropie statique

## Objet et decision de lecture

Ce dossier rassemble les preuves executees pour quatre perimetres qui etaient
encore a consolider. Il separe volontairement :

1. un sous-perimetre MITC3 dynamique mince et plan ;
2. un sous-perimetre MITC3 courbe limite aux chargements mixte et transverse ;
3. le TET4 total-lagrangien, encore au statut recherche ;
4. les solides orthotropes statiques TET4/TET10, dans leur domaine homogene.

Le resultat global est **PASS avec perimetres bornes**. Les trois premiers
perimetres stables ou promouvables restent des sous-perimetres explicites. Le
TET4 total-lagrangien n'est pas promu stable : les tests sont valides pour une
preuve de recherche, mais l'erreur Euler fine reste a `1,8956 %`, le
post-flambement n'est pas correle a un oracle externe et une revue independante
reste obligatoire.

Le registre machine-readable associe est
`qualification/vnv/vnv_plan_mitc3_tet4_orthotropic_2026-08-22.json`.

## Regles d'acceptation

Les seuils suivants sont utilises pour cette campagne interne :

| Critere | Seuil | Interprétation |
| --- | ---: | --- |
| Observable principal externe | `1 %` | Ecart relatif sur le deplacement, la frequence ou la reponse declaree |
| Incrément de maillage | `5 %` | Indicateur de stabilisation, pas une preuve suffisante seul |
| Résidu statique libre | `1e-8` | Controle d'equilibre normalise |
| Résidu dynamique | `1e-7` | Controle de l'equation dynamique normalisee |
| Revue indépendante | obligatoire pour TET4-TL | Condition de promotion externe ou de revendication de qualification |

Un calcul qui passe un seuil ne peut être extrapolé à une géométrie, un
matériau ou une charge non testés. Les valeurs sont recopiées depuis les
résumés JSON générés par les campagnes, sans saisie manuelle dans les sorties
numériques.

## Execution realisee

Campagne V&V ciblée :

```powershell
python -m pytest -q tests/verification/test_mitc3_laminate_dynamic_vnv.py tests/verification/test_mitc3_dynamic_extended_vnv.py tests/verification/test_mitc3_temporal_refinement.py tests/verification/test_mitc3_external_evidence.py tests/verification/test_tet4_total_lagrangian_assembly_vnv.py tests/verification/test_tet4_total_lagrangian_vnv.py tests/verification/test_orthotropic_completion_vnv.py tests/verification/test_orthotropic_modal_newmark_vnv.py
```

Resultat : `13 passed, 6 skipped` en `168,99 s`.

Les campagnes lourdes ont aussi ete executees :

```powershell
python -m pytest -q tests/verification/test_tet4_tl_buckling_vnv.py -m benchmark
python -m pytest -q tests/verification/test_tet4_tl_postbuckling_vnv.py -m benchmark
```

Resultats : `1 passed` pour le flambement et `1 passed` pour le post-flambement.
La suite complete du projet n'a pas ete relancee dans cette etape.

## 1. MITC3 dynamique mince plan

### Domaine

Le domaine est un stratifié plan symétrique `[0/90/90/0]`, avec `t/L = 0,01`,
petits déplacements, analyses modale, Newmark et harmonique. Les maillages
`12x3`, `16x4` et `24x6` sont conserves dans le rapport, y compris les niveaux
intermédiaires dont l'erreur modale dépasse `1 %`.

### Mesures

| Niveau | Erreur modale | Erreur Newmark | Erreur harmonique |
| ---: | ---: | ---: | ---: |
| `12x3` | `3,1228 %` | `0,2027 %` | `0,0862 %` |
| `16x4` | `1,3705 %` | `0,0813 %` | `0,0168 %` |
| `24x6` | `0,3940 %` | `0,1968 %` | `0,0880 %` |

Le niveau fin passe le seuil de `1 %` pour les trois observables. Le résidu
modal fin est `1,0818e-8`, sous le seuil de campagne `1e-7`, mais légèrement
au-dessus d'un seuil strict `1e-8`. Cette réserve est conservée dans le
dossier au lieu d'être masquée.

La comparaison utilise Code_Aster `18.1.0`, élément `DKT/TRIA3`. DKT est une
référence de limite mince de type Kirchhoff discrète ; ce n'est pas la preuve
que MITC3+ et DKT ont la même matrice. La conclusion est donc :
**stable dans le sous-perimetre mince, plan et symetrique**, sans extrapolation
aux coques épaisses, courbes, amorties ou non symétriques.

Preuves :

- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json` ;
- `docs/verification/mitc3_laminate_dynamic_dkt_thin_owner_review.md` ;
- tests `test_mitc3_laminate_dynamic_vnv.py`, `test_mitc3_dynamic_extended_vnv.py`.

## 2. MITC3 courbe mixte et transverse

### Domaine

Le cas est un panneau cylindrique facettisé de rayon `0,5 m`, ouverture de
`60 degres`, empilement `[0/90/90/0]` et orientation globale projetée sur les
facettes. Les sept niveaux vont de `8x4` à `64x32`. Deux familles sont
acceptées : `mixed` et `transverse`.

### Mesures

| Observable | Mixte | Transverse | Limite |
| --- | ---: | ---: | ---: |
| Ecart QF_solver / Code_Aster | `0,5780 %` | `0,4975 %` | `1 %` |
| Incrément QF final | `4,4755 %` | `4,6023 %` | `5 %` |
| Incrément externe final | `4,7520 %` | `4,8567 %` | `5 %` |
| Résidu libre | `5,22e-11` | `3,03e-9` | `1e-8` |
| Erreur projection orientation | `1,48e-6 deg` | `1,48e-6 deg` | `1e-4 deg` |

Le sous-périmètre passe les deux gates, avec une faible marge sur le dernier
incrément de maillage. Il est donc exploitable comme **stable borné**, avec
recommandation de seconde géométrie et de second empilement.

Le chargement axial n'est pas inclus. La campagne axiale montre un incrément
de `8,47 %` dans une étape et une comparabilité sensible entre formulations
externes ; elle reste `accepted_for_bounded_engineering_use`, pas stable.

Preuves :

- `qualification/vnv/external/code_aster_mitc3_curved_laminate_refinement_027/reference/summary.json` ;
- `docs/verification/mitc3_laminate_curved_mixed_transverse_stable_owner_review.md` ;
- figures `convergence_qf_code_aster.png` et
  `convergence_qf_code_aster_transverse.png`.

## 3. TET4 total-lagrangien

### Ce qui est demontre

La cinématique Green-Lagrange, la loi Saint-Venant-Kirchhoff, les contraintes
PK2, le push-forward Cauchy, le determinant positif et l'arc-length sont
exercés. Le flambement parfait a ete raffine jusqu'à `98 304` TET4 et
`56 355` DDL.

| Mesure h5 | Valeur | Lecture |
| --- | ---: | --- |
| Erreur charge critique Euler | `1,8956 %` | Sous `5 %`, mais au-dessus de `1 %` |
| Ecart QF_solver / CalculiX même maillage | `0,0343 %` | Très bon accord externe |
| Résidu de bracket | `3,32e-4` | Résolution de la charge critique |
| `min det(F)` | `0,999819` | Jacobienne positive |

Le post-flambement a ete relancé sur `1 536` TET4 avec `120` pas et trois
imperfections `0,25 %`, `0,50 %` et `1,00 %`. Le statut est
`PASS_POSTBUCKLING_RESEARCH`, le résidu maximal est `9,52e-9`, le determinant
minimal est `0,9832` et la charge atteint `1,2816 P_Euler` pour l'imperfection
forte. Ces résultats montrent une branche continue et un comportement
post-critique calculable ; ils ne constituent pas encore une corrélation
externe de la branche post-critique.

### Decision

Le périmètre reste **research / more_evidence_required**. Il ne doit pas être
promu stable sur la seule base d'un futur maillage d'environ `1,2 million`
d'éléments. La prochaine campagne doit mesurer le temps, la mémoire, les
résidus, le chemin de charge, la positivité de `F`, l'effet du maillage et une
comparaison indépendante. Une revue indépendante est obligatoire.

Preuves :

- `qualification/vnv/tet4_tl_buckling_h5/reference/summary.json` ;
- `results/VNV-TET4-TL-POSTBUCKLING-007/summary.json` ;
- `docs/verification/revue_tet4_total_lagrangian_structural_v2.md`.

## 4. Orthotropie statique TET4/TET10

### Domaine

Le cas est une console `2,0 x 1,0 x 0,5 m`, traction terminale `TZ=-1 MPa`,
orientation matériau constante à `30 deg` et référence TET10 indépendante.
La campagne TET4 finale emploie `564 525` éléments et la campagne TET10 fine
`2 607` éléments.

| Famille | Erreur déplacement | Erreur énergie | Incrément final | Résidu |
| --- | ---: | ---: | ---: | ---: |
| TET4 | `0,8772 %` | `0,8647 %` | `0,4581 %` | `9,96e-9` |
| TET10 | `0,2918 %` | `0,3027 %` | `0,6358 %` | `7,26e-12` |

Le patch affine TET4 vaut `0`, le patch TET10 vaut `6,06e-17` et l'objectivité
par rotation passe. Le gate sous `1 %` est donc passe pour le domaine statique
homogène documente. La valeur historique `1,3293 %` correspond à une campagne
intermediaire ; la valeur finale de decision est `0,8772 %`.

### Decision

Le scope est **stable dans le domaine statique orthotrope homogène documente**.
Cette decision ne couvre pas l'orientation continue sur une surface courbe,
le composite pli par pli, l'endommagement, la plasticité anisotrope ou les
grandes déformations. Les singularités de contrainte restent hors acceptance.

Preuves :

- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/summary.json` ;
- `docs/verification/orthotropic_static_extended_owner_review.md` ;
- `qualification/maturity_evidence_0_2_1/orthotropic.json`.

## Plan de suite decoupe

| Etape | Action | Gate de sortie | Etat |
| --- | --- | --- | --- |
| P0 | Archiver les résumés, commandes, empreintes et figures | Tous les chemins existent et sont lisibles | Fait |
| P1 | Maintenir MITC3 dynamique mince | Erreurs fines < 1 %, limites publiques | Prêt pour decision Owner |
| P2 | Fermer MITC3 mixte/transverse | Ecart < 1 %, incrément < 5 %, résidus passes | Prêt avec recommandation |
| P3 | Stabiliser l'orthotropie statique documentee | TET4/TET10 < 1 %, patch et rotation passes | Preuve disponible |
| P4 | Raffiner TET4-TL vers ~1,2 M éléments | Erreur, équilibre, mémoire et chemin mesurés | Non exécuté |
| P5 | Revue indépendante TET4-TL | Avis indépendant archivé | Non fait |
| P6 | Etendre MITC3 | Seconde géométrie, second layup, axial requalifié | À planifier |
| P7 | Audit final | Registres cohérents, aucun scope extrapolé | À faire |

## Questions de validation Owner

Ces questions sont prévues pour la revue, sans signature automatique :

1. Le domaine MITC3 dynamique mince plan est-il accepté comme stable uniquement
   dans les limites `[0/90/90/0]`, plan, mince et symétrique ?
2. Le domaine MITC3 courbe mixte/transverse est-il accepté comme stable borné,
   malgré la marge de convergence proche de `5 %` ?
3. Les exclusions axial, courbure dynamique, `S13/S23`, dommage et délamination
   sont-elles maintenues explicitement ?
4. L'orthotropie statique TET4/TET10 est-elle acceptée comme stable uniquement
   pour le matériau homogène et l'orientation constante documentes ?
5. Le TET4 total-lagrangien doit-il rester `more_evidence_required` jusqu'au
   calcul ~1,2 M éléments et à la revue indépendante ?

## Conclusion

Les éléments et méthodes ne sont pas tous au même niveau. MITC3 dynamique
mince, MITC3 courbe mixte/transverse et orthotropie statique disposent d'une
preuve technique exploitable dans un domaine strictement borné. Le TET4
total-lagrangien est fonctionnel et documenté pour la recherche, mais il reste
hors promotion stable. Cette distinction est la conclusion importante de la
campagne.

