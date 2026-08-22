---

doc_id: DOC-OWNER-MITC3-LAM-DYN-EXTENDED-001
revision: 0.1
status: ready_for_owner_review
review_mode: owner_review
promotion_target: stable
scope: mitc3-laminate-dynamic
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner review — MITC3 multicouche dynamique, raffinement étendu

> **Règle de promotion QF_solver 0.2.1a0 :** toute erreur primaire de comparaison
> (fréquence, historique Newmark ou réponse harmonique) doit être inférieure ou
> égale à **1 %** pour une promotion `stable`. Un résidu interne faible ne
> compense pas une corrélation externe hors seuil.

La campagne compare le MITC3+ QF_solver et Code_Aster DST/TRIA3 sur un stratifié plan `[0/90/90/0]`. Les niveaux historiques `8x2`, `12x3`, `16x4`, `24x6` et `32x8` sont complétés par les diagnostics `48x12` et `64x16`.

| Maillage | Triangles | Modal | Newmark | Harmonique |
| ---: | ---: | ---: | ---: | ---: |
| 8x2 | 32 | 7,5201 % | 1,7119 % | 0,9406 % |
| 12x3 | 72 | 3,9573 % | 2,3179 % | 1,3449 % |
| 16x4 | 128 | 2,5016 % | 3,4004 % | 1,9957 % |
| 24x6 | 288 | 1,7784 % | 5,5578 % | 3,2746 % |
| 32x8 | 512 | 2,0355 % | 7,2337 % | 4,2565 % |
| 48x12 | 1152 | 2,4476 % | 9,3150 % | 5,4589 % |
| 64x16 | 2048 | 2,6867 % | 10,4121 % | 6,0831 % |

Les niveaux supplémentaires ne confirment pas une convergence monotone vers 1 %. Le niveau `64x16` contient `2048` triangles mais conserve un maximum modal de `2,6867 %`, une erreur Newmark de `10,4121 %` et une erreur harmonique de `6,0831 %`. Les résidus QF restent faibles (`4,883e-08` modal et `8,021e-10` dynamique), mais les écarts externes ne sont donc pas expliqués par le seul manque de mailles. Cette distinction est importante : les résidus attestent la résolution du système QF_solver, tandis que les trois écarts ci-dessus restent les observables primaires de corrélation et bloquent la stabilité.

Un diagnostic séparé a rendu explicite le coefficient de correction du cisaillement
dans le deck Code_Aster (`A_CIS=5/6`) sur les niveaux `8x2`, `12x3` et `16x4`.
Les erreurs fines restent respectivement `2,5016 %` en modal, `3,4004 %` en
Newmark et `1,9957 %` en harmonique. Cette campagne négative exclut donc une
ambiguïté liée à la valeur par défaut de la correction de cisaillement; elle ne
ferme pas le blocage de formulation.

Un second diagnostic a également aligné la distribution de force sur le bord
chargé : les poids trapézoïdaux QF_solver sont appliqués aux mêmes groupes
`TIP_####` dans Code_Aster, avec une résultante totale `FZ=-1`. Les écarts fins
restent inchangés à `2,5016 %`, `3,4004 %` et `1,9957 %`; la distribution nodale
ne suffit donc pas à expliquer le désaccord modal et dynamique.

## Questions Owner

### Q1 — Domaine

Les cinq niveaux et le protocole modal/Newmark/harmonique couvrent-ils le domaine du stratifié plan `[0/90/90/0]` revendiqué ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Critère à 1 %

Les valeurs fines `2,0355 %`, `7,2337 %` et `4,2565 %` doivent-elles maintenir le scope hors stable malgré les résidus internes faibles ? La règle de promotion impose-t-elle bien de traiter chacune de ces valeurs comme une erreur primaire indépendante ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Limites

Les exclusions des coques courbes, du couplage B non nul, de l'amortissement calibré, des contraintes dynamiques par pli, du dommage et de la délamination sont-elles acceptables ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Décision

Décision proposée : `accepted_with_recommendations`, `accepted_for_bounded_engineering_use`, `stable` ou `more_evidence_required`. En l'état des chiffres publiés, `stable` n'est pas recevable. Une décision plus mature devra être accompagnée d'une campagne reproductible ramenant **chaque** erreur primaire à `<= 1 %`, ou d'une justification mécanique formelle et d'une nouvelle décision Owner datée.

Signature Owner :

Date :

## Artefacts

- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_extended_021/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_extended_021/reference/report.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_extended_021/reference/mitc3_laminate_dynamic_refinement.png`
- `output/pdf/mitc3_laminate_dynamic_extended_owner_review.pdf`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_a_cis_035/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_a_cis_035/reference/report.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_a_cis_035/reference/mitc3_laminate_dynamic_refinement.png`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_load_fix_036/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_load_fix_036/reference/report.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_load_fix_036/reference/mitc3_laminate_dynamic_refinement.png`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037/reference/report.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037/reference/mitc3_laminate_code_aster_comparison.png`
- Commande diagnostic : `python scripts/run_code_aster_mitc3_laminate_dynamic_vnv.py --output results/VNV-MITC3-LAMINATE-DYNAMICS-64x16-037 --nx 64 --ny 16`
- Commande : `python scripts/run_code_aster_mitc3_laminate_dynamic_refinement_vnv.py --output results/VNV-MITC3-LAMINATE-DYNAMICS-REFINEMENT-CODEASTER-DST-021 --levels 8x2 12x3 16x4 24x6 32x8`

## Référence de formulation externe

Le choix `DST` et la prise en compte du cisaillement transverse sont documentés
dans le manuel théorique Code_Aster R3.07.03. Cette référence est utilisée pour
interpréter l'écart de modèle; elle ne transforme pas Code_Aster en preuve de
qualification automatique :

- https://code-aster.org/doc/v11/fr/man_r/r3/r3.07.03.pdf
- https://code-aster.org/V2/doc/v11/fr/man_u/u4/u4.42.03.pdf
