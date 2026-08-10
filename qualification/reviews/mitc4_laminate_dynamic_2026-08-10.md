---
review_id: OWNER-REVIEW-MITC4-LAMINATE-DYNAMIC-2026-08-10
scope: mitc4-laminate-dynamic
status: owner_accepted_experimental_bounded_use
decision: accepted_for_bounded_engineering_use
review_mode: owner_review
certification_claim: none
owner_response_recorded: 2026-08-10
---

# Owner review - MITC4 multicouche dynamique lineaire

## Evidence disponible

- `VNV-MITC4-LAMINATE-DYNAMIC-001` : invariants internes modal, Newmark et harmonique ;
- `VNV-MITC4-LAMINATE-DYNAMICS-CODEASTER-DST-018` : meme QUAD4, empilement,
  masse, blocage, grille temporelle et frequences contre Code_Aster DST ;
- `VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021` : trois empilements
  symetriques sur le meme QUAD4 et contre le meme Code_Aster DST :
  `[0/90/90/0]`, `[45/-45/-45/45]` et `[0/45/45/0]`. Le dernier cas utilise
  Newmark avec `3 %` d'amortissement modal cible par Rayleigh massique ;
- `VNV-MITC4-LAMINATE-MESH-REFINEMENT-022` : raffinement `36 -> 72 -> 144`
  elements et comparaison d'un raffinement directionnel `48 x 3` avec un
  raffinement equilibre `24 x 6` ;
- `VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023` : tentative de fermeture sur
  `10 000` QUAD4 pour `[45/-45/-45/45]`. Code_Aster fournit quatre frequences,
  mais le backend modal QF_solver reste non convergent au seuil `1e-7` ; la
  correlation mode par mode est donc explicitement ouverte.
- `VNV-COMP-CURVED-ORIENTATION-008` : axe materiau oblique projete sur coque
  cylindrique, correle statique contre CalculiX S8R.

| Empilement | Modal | Newmark | Harmonique | Controle amorti |
| --- | ---: | ---: | ---: | ---: |
| `[0/90/90/0]` | `1,678 %` | `0,422 %` | `0,205 %` | non applicable |
| `[45/-45/-45/45]` | `5,528 %` | `3,449 %` | `1,842 %` | non applicable |
| `[0/45/45/0]` | `1,823 %` | `0,506 %` | `0,305 %` | enveloppe finale `0,847 < 0,95` |

## Suivi de convergence demande par l'Owner

Le maillage de reference `12 x 3` contient `36` elements. Le premier
doublement `24 x 3` contient `72` elements. Un second doublement a ete execute
de deux manieres, afin de ne pas confondre raffinement et anisotropie de grille
: `48 x 3` directionnel et `24 x 6` equilibre, tous deux a `144` elements.

| Cas | Indicateur | H1 36 | H2 72 | H4 equilibre 144 | H4 directionnel 144 |
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

La conclusion technique est que le raffinement equilibre reduit nettement les
ecarts, notamment pour le cas `+/-45 deg`. Le modal de ce cas reste toutefois
a `1,771 %`. Le maillage directionnel `48 x 3` degrade ce cas ; il ne peut
donc pas servir seul de preuve de convergence monotone. Les seuils de
correlation externe restent respectes, mais l'hypothese d'un ecart
exclusivement imputable au maillage reste ouverte pour ce cas modal.

Le detail machine-readable est conserve dans
`results/VNV-MITC4-LAMINATE-MESH-REFINEMENT-022-20260809/mesh_refinement_summary.json`
et le rapport lisible dans
`results/VNV-MITC4-LAMINATE-MESH-REFINEMENT-022-20260809/mesh_refinement_report.md`.

## Suivi modal 10 000 elements

La campagne `VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023` a ete executee sur
`200 x 50 = 10 000` QUAD4. La reference Code_Aster 18.1.0 donne les quatre
frequences `5.749576`, `35.920088`, `93.708527` et `102.829165 Hz`. Son
controle a posteriori emet toutefois une alarme sur le mode 3 ; la sortie
complete est conservee et la reference reste classee `reference_only`.

Le chemin QF_solver a ete tente avec `eigh`, `eigsh` et `LOBPCG`. La
condensation lazy a reduit la memoire observee, mais le meilleur residu modal
reste environ `7.383e-6` apres `30 000` iterations, au-dessus du seuil `1e-7`.
Le resultat ne permet donc pas de calculer un ecart QF_solver/Code_Aster sur
ce maillage. Cette limite est numerique et ne constitue pas une conclusion
sur la formulation MITC4.

Le dossier de revue est disponible dans
`results/VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023-20260809/owner_review_modal_10k.md`
et en PDF dans
`output/pdf/qf_solver_mitc4_laminate_modal_10k_owner_review.pdf`.

## Questions Owner

| ID | Question | Reponse | Commentaire |
| --- | --- | --- | --- |
| Q1 | Le domaine plan a quatre plis symetriques, petits deplacements, masse coherente et drilling condense est-il accepte pour les trois empilements testes ? | `OUI` | Domaine accepte par l'Owner pour la suite de l'etude. |
| Q2 | Les ecarts Code_Aster pour les trois empilements, dont le Newmark amorti `[0/45/45/0]`, sont-ils acceptables ? | `OUI` | Acceptes dans les bornes de correlation, avec le suivi de convergence annexe. |
| Q3 | La preuve statique d'axe projete sur coque courbe est-elle suffisante pour ce domaine dynamique plan borne ? | `OUI` | Acceptation limitee au domaine dynamique plan borne. |
| Q4 | Les exclusions dynamique courbe, `B` non nul, amortissement calibre, dommage et delaminage sont-elles explicites et acceptables ? | `OUI` | Pas de delaminage, pas de rupture et pas de calibration sur essais a ce stade. |
| Q5 | Decision | `ACCEPTE POUR USAGE ENGINEERING BORNE` | La reserve modale a 10 000 QUAD4 reste ouverte et bloque une maturite plus large, sans bloquer le domaine plan teste. |

## Signature

| Champ | Valeur |
| --- | --- |
| Owner | `Quentin Farinazzo` |
| Date | `2026-08-10` |
| Signature / decision | `declared_owner_review - accepted_for_bounded_engineering_use` |

Cette revue ne constitue pas une certification externe et ne valide pas une
dynamique de coque courbe ou un comportement de rupture composite.
