---
doc_id: DOC-VNV-MITC4-LAMINATE-DYN-001
revision: 0.3
status: controlled
applicable_version: "0.2.0a0"
reviewer: "Quentin Farinazzo"
approver: ""
---

# V&V MITC4 multicouche dynamique

## Resultat de la campagne

`VNV-MITC4-LAMINATE-DYNAMIC-001` execute sur un porte-a-faux MITC4 de `8 x 2`
elements avec stratification symetrique `[0/90/90/0]`. La preuve est interne :
elle verifie la coherence des matrices `K` et `M`, de la condensation des DDL
de drilling, de Newmark et de l'operateur harmonique. Les campagnes externes
Code_Aster repertoriees dans l'Owner review completent cette preuve interne.
Le perimetre reste experimental et borne ; il ne constitue pas une
qualification externe.

Les resultats calcules sont conserves dans
`qualification/vnv/mitc4_laminate_dynamic/reference/summary.json`.

| Controle | Valeur observee | Limite | Verdict |
| --- | ---: | ---: | --- |
| Residus propres relatifs | `3.10e-09` | `1e-07` | PASS |
| Orthogonalite masse | `5.68e-16` | `1e-07` | PASS |
| Orthogonalite raideur | `3.92e-11` | `1e-07` | PASS |
| DDL drilling condenses | `24` | `> 0` | PASS |
| Erreur Newmark T/80 | `2.62e-03` | `1e-02` | PASS |
| Derive energie Newmark | `1.28e-11` | `1e-04` | PASS |
| Erreur harmonique complexe | `2.13e-08` | `1e-06` | PASS |
| Limite statique harmonique | `5.40e-12` | `1e-09` | PASS |
| Post-traitement harmonique | `4` plis | `4` plis | PASS |

## Correlation externe ajoutee

`VNV-MITC4-LAMINATE-DYNAMICS-CODEASTER-DST-018` compare le meme porte-a-faux
`12 x 3` QUAD4 a Code_Aster 18.1 (`DST / DEFI_COMPOSITE`). Les quatre premiers
modes different d'au plus `1,678 %`; l'ecart RMS de l'historique Newmark est
`0,422 %` et celui de la reponse harmonique complexe sous resonance `0,205 %`.
Les seuils respectifs sont `10 %`, `12 %` et `12 %`. La preuve est archivee
dans `qualification/vnv/external/code_aster_mitc4_laminate_dynamic/reference/`.

La convention d'axe materiau projete est en outre correlee sur coque courbe
par `VNV-COMP-CURVED-ORIENTATION-008` contre CalculiX S8R COMPOSITE. C'est une
preuve statique de projection, non une correlation dynamique courbe.

## Extension a trois empilements et Newmark amorti

`VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021` reprend exactement le protocole
externe sur trois bandes planes a quatre plis identiques : `[0/90/90/0]`,
`[45/-45/-45/45]` et `[0/45/45/0]`. Les trois cas conservent le maillage
`12 x 3`, les blocs, les charges, les grilles modales et harmoniques, ainsi que
les proprietes de chaque pli. Seules les orientations changent.

Le dernier empilement introduit un Newmark amorti par Rayleigh massique, cible
sur `3 %` du premier mode. L'enveloppe tardive apres relachement vaut `0,847`,
sous le seuil de decroissance `0,95`.

| Empilement | Ecart modal | Ecart Newmark | Ecart harmonique | Verdict |
| --- | ---: | ---: | ---: | --- |
| `[0/90/90/0]` | `1,678 %` | `0,422 %` | `0,205 %` | PASS |
| `[45/-45/-45/45]` | `5,528 %` | `3,449 %` | `1,842 %` | PASS |
| `[0/45/45/0]`, amorti | `1,823 %` | `0,506 %` | `0,305 %` | PASS |

Cette extension prouve l'invariance du protocole pour trois empilements plans
symetriques. Elle ne valide toujours pas une dynamique de coque courbe, un
couplage `B` non nul, ni une calibration d'amortissement sur essai.

## Raffinement de maillage pour la Owner Review

Une campagne complémentaire est conservée sous
`VNV-MITC4-LAMINATE-MESH-REFINEMENT-022-20260809`. Elle exécute les trois
empilements sur `36`, `72` puis `144` éléments. Le niveau `144` est calculé à
la fois en `48 x 3`, pour mesurer l'effet d'un raffinement directionnel, et en
`24 x 6`, pour mesurer un raffinement équilibré.

| Cas | Indicateur | 36 éléments | 72 éléments | 144 équilibré | 144 directionnel |
| --- | --- | ---: | ---: | ---: | ---: |
| `[0/90/90/0]` | modal | `1,678 %` | `0,389 %` | `0,414 %` | `0,073 %` |
| `[0/90/90/0]` | Newmark | `0,422 %` | `0,125 %` | `0,108 %` | `0,051 %` |
| `[0/90/90/0]` | harmonique | `0,205 %` | `0,061 %` | `0,053 %` | `0,025 %` |
| `[45/-45/-45/45]` | modal | `5,528 %` | `1,585 %` | `1,771 %` | `4,693 %` |
| `[45/-45/-45/45]` | Newmark | `3,449 %` | `3,740 %` | `1,738 %` | `7,115 %` |
| `[45/-45/-45/45]` | harmonique | `1,842 %` | `1,994 %` | `0,964 %` | `3,804 %` |
| `[0/45/45/0]`, amorti | modal | `1,823 %` | `0,703 %` | `0,414 %` | `0,457 %` |
| `[0/45/45/0]`, amorti | Newmark | `0,506 %` | `0,246 %` | `0,147 %` | `0,185 %` |
| `[0/45/45/0]`, amorti | harmonique | `0,305 %` | `0,146 %` | `0,090 %` | `0,107 %` |

Le raffinement équilibré réduit les écarts du cas `+/-45 deg`, mais le modal
reste à `1,771 %`. Le résultat `48 x 3` se dégrade pour ce cas ; il montre
qu'une augmentation du nombre d'éléments dans une seule direction n'est pas
une preuve suffisante de convergence. La campagne confirme une contribution
forte de la discrétisation, sans démontrer que la différence restante est
exclusivement un effet de maillage.

Les trois cas restent dans les seuils de la corrélation externe. La décision
Owner finale est donc laissée ouverte jusqu'à la revue de cette étude, sans
extension de maturité ni revendication de certification.

## Tentative modale a 10 000 QUAD4

La campagne `VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023` traite le cas
`[45/-45/-45/45]` sur un maillage `200 x 50`, soit `10 000` QUAD4 et environ
`51 000` ddl libres. Code_Aster 18.1.0 fournit les frequences de reference
`5.749576`, `35.920088`, `93.708527` et `102.829165 Hz`; son controle a
posteriori signale cependant une alarme sur le mode 3, conservee dans les
logs.

Le chemin QF_solver a ete tente avec `eigh`, `eigsh` et `LOBPCG`. La meilleure
valeur obtenue est un residu modal d'environ `7.383e-6` apres `30 000`
iterations, au-dessus du seuil `1e-7`. La condensation lazy a reduit la
memoire observee, mais la comparaison QF_solver/Code_Aster mode par mode
n'est pas calculable. Cette campagne est donc `more_evidence_required` et ne
constitue pas une conclusion sur la formulation MITC4.

Le rapport Owner lisible est disponible dans
`results/VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023-20260809/owner_review_modal_10k.md`
et en PDF dans
`output/pdf/qf_solver_mitc4_laminate_modal_10k_owner_review.pdf`.

## Decision de maturite

Le couple `MITC4 / laminate_dynamic` est `ready_for_owner_review`. Il reste
hors scope Owner accepte jusqu'a reception :

1. d'une Owner review dediee fixant le domaine d'emploi et les tolerances ;
2. d'une decision explicite sur le fait que la correlation dynamique plane et
   la correlation statique courbe sont suffisantes pour le domaine borne ;
3. si le domaine vise la dynamique courbe, d'une campagne dynamique courbe
   dediee avant toute extension de maturite.

Les images et le manifeste sont generes par le solveur a chaque construction
du site; aucun chiffre n'est recopie manuellement.
