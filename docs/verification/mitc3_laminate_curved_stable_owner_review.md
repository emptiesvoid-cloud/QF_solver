---
doc_id: DOC-OWNER-MITC3-LAM-CURVED-STABLE-001
revision: 0.1
status: ready_for_owner_review
review_mode: owner_review
promotion_target: stable
scope: mitc3-laminate-static-curved
---

# Owner review — MITC3 multicouche courbe, campagne raffinée

La campagne Code_Aster corrigée comprend trois familles de chargement sur
les niveaux `8x4`, `16x8`, `24x12`, `32x16`, `48x24` et `64x32`. Le modèle
reste un panneau cylindrique facettisé, avec axes matériaux projetés par
facette et empilement `[0/90/90/0]`. Les constantes du deck Code_Aster sont
désormais générées depuis la même table que le modèle QF_solver :
`E1=130 GPa`, `E2=9 GPa`, `nu12=0,28`, `G12=5 GPa`, `G13=4 GPa`,
`G23=3,5 GPa`, `rho=1550 kg/m3`.

| Grandeur | Mixte | Transverse | Axiale | Limite | Verdict |
| --- | ---: | ---: | ---: | --- |
| Écart déplacement QF / Code_Aster à 64x32 | 0,6090 % | 0,5278 % | 0,9066 % | 1 % | PASS |
| Incrément QF 48x24 → 64x32 | 4,3269 % | 4,4486 % | 8,2619 % | 5 % | FAIL axial |
| Incrément Code_Aster 48x24 → 64x32 | 4,6118 % | 4,7110 % | 7,8823 % | 5 % | FAIL axial |
| Résidu libre QF | 4,525e-11 | 2,636e-9 | 4,739e-12 | 1e-7 | PASS |

## Domaine proposé

La cible `stable` est proposée uniquement pour ce domaine : une géométrie
cylindrique facettisée, un empilement symétrique `[0/90/90/0]`, orientation
globale projetée sur les facettes, petits déplacements, trois chargements
documentés et les observables de déplacement de bord. La corrélation primaire
est sous 1 %, mais la convergence spatiale n'est pas encore suffisante car la
famille axiale dépasse 5 % d'incrément final. L'erreur principale de
corrélation reste obligatoirement inférieure à 1 %.

Le raffinement axial ciblé `64x32 -> 96x48 -> 128x64` réduit l’incrément
adjacent à `3,17 %` côté QF_solver et `2,74 %` côté Code_Aster, mais l’écart
externe augmente à `1,336 %` puis `1,570 %`. Ce résultat négatif indique que
le désaccord axial ne peut pas être attribué uniquement au manque de maillage.

## Audit de comparabilité des références axiales

Un audit indépendant a rejoué le même chemin d'entrée QF_solver et comparé les
deux références externes au niveau commun `64x32`. Les résultats sont :

| Comparaison | Ecart relatif vectoriel | Interprétation |
| --- | ---: | --- |
| QF_solver / Code_Aster DST | `0,907 %` | sous la limite de `1 %` |
| QF_solver / CalculiX S6 | `6,420 %` | au-dessus de la limite de `1 %` |
| Code_Aster DST / CalculiX S6 | `7,591 %` | dispersion des formulations externes |

Le dossier `qualification/vnv/external/mitc3_curved_axial_reference_audit_2026-08-21/`
montre que la réponse QF_solver est reproduite entre les deux chemins d'entrée,
mais que Code_Aster DST et CalculiX S6 ne sont pas des opérateurs matriciellement
identiques. Ce diagnostic ne permet donc pas de transformer la comparaison
axiale en preuve de promotion stable générale. Il confirme également qu'un
raffinement temporel n'est pas une explication applicable à ce cas statique.
La promotion reste bloquée tant qu'une référence externe de formulation
comparable, ou une justification mécanique formelle acceptée par Owner, n'est
pas disponible.

Restent exclus : autres géométries courbes, axes obliques non testés,
stratifiés non symétriques, dynamique courbe, contraintes par pli pour
l'acceptation, S13/S23, singularités, dommage, rupture et délamination.

## Questions Owner

### Q1 — Domaine

Le domaine limité au panneau cylindrique facettisé, à l'orientation projetée,
à l'empilement `[0/90/90/0]` et aux trois chargements est-il suffisamment
défini pour une cible `stable` ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Convergence

Les niveaux corrigés et les erreurs externes inférieures à 1 % démontrent-ils
une convergence suffisante malgré l’échec de l’incrément axial à 64x32 et la
remontée au-dessus de 1 % lors du raffinement 128x64 ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Exclusions

Les autres courbures, empilements, dynamique courbe, contraintes interlaminaires,
dommage, rupture et délamination sont-ils correctement exclus ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Décision

Décision proposée : `stable / accepted_with_recommendations /
accepted_for_bounded_engineering_use / more_evidence_required`.

Signature Owner :

Date :

## Artefacts

- `qualification/vnv/external/code_aster_mitc3_curved_laminate_3loads_029/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_3loads_029/reference/vnv_manifest.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_axial_refinement_030/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_axial_refinement_030/reference/vnv_manifest.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_032/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_032/reference/vnv_manifest.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_033/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_033/reference/vnv_manifest.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_034_axial/reference/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_034_axial/reference/vnv_manifest.json`
- `results/VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-029/`
- `output/pdf/mitc3_laminate_curved_stable_owner_review.pdf`
