---

doc_id: DOC-OWNER-MITC4-LAM-DYN-EXTENDED-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
promotion_target: stable
scope: mitc4-laminate-dynamic
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner review — MITC4 multicouche dynamique, trois empilements

La campagne compare trois empilements symétriques MITC4 et Code_Aster DST sur le même protocole modal, Newmark et harmonique. Les niveaux `24x6`, `36x9` et `48x12` sont conservés. Le tableau ci-dessous donne le niveau final `48x12` :

| Empilement | Modal | Newmark | Harmonique | Résidu modal |
| --- | ---: | ---: | ---: | ---: |
| `[0/90/90/0]` | 0,1303 % | 0,0272 % | 0,0144 % | 9,642e-09 |
| `[45/-45/-45/45]` | 0,3792 % | 0,4841 % | 0,2613 % | 7,409e-08 |
| `[0/45/45/0]` avec amortissement | 0,1281 % | 0,0669 % | 0,0349 % | 2,163e-09 |

Les trois layups respectent maintenant la règle d'ingénierie `≤ 1 %` au niveau final, et le résidu modal maximal vaut `7,409e-08`. Le niveau `36x9` reste publié comme niveau intermédiaire : l'angle-ply y atteint `2,938 %` en Newmark et `1,606 %` en harmonique. Le raffinement `48x12` est donc nécessaire et ne doit pas être omis dans une reproduction. La preuve technique est favorable. La décision Owner du 21 août 2026 promeut ce sous-périmètre en `stable` dans les limites déclarées.

## Questions Owner

### Q1 — Domaine

Les trois empilements, dont un cas amorti, couvrent-ils suffisamment le domaine dynamique plan déclaré ?

Réponse Owner : `OUI`.

### Q2 — Gate d'erreur

Les trois empilements sont-ils acceptables au niveau final `48x12` malgré les dépassements observés au niveau intermédiaire `36x9` ?

Réponse Owner : `OUI`.

### Q3 — Limites

Les exclusions courbure, couplage B non nul, calibration expérimentale de l'amortissement, dommage, rupture et délamination sont-elles acceptables ?

Réponse Owner : `OUI`.

### Q4 — Décision

Décision Owner : `stable` pour le sous-périmètre déclaré ; décision machine-readable `accepted_with_recommendations`, cible `stable`.

Owner : Quentin Farinazzo (déclaration électronique)

Date : 2026-08-21

## Artefacts

- `results/VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-023/summary.json`
- `results/VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-023/report.md`
- `results/VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-023/mitc4_laminate_layups_comparison.png`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/layup_0090/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/layup_4545/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/layup_0045/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/mesh_36x9_0090/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/mesh_36x9_4545/summary.json`
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/mesh_36x9_0045/summary.json`
- `output/pdf/mitc4_laminate_dynamic_extended_owner_review.pdf`
- Commande : `python scripts/run_code_aster_mitc4_laminate_layups_vnv.py --output results/VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-023 --nx 24 --ny 6`
