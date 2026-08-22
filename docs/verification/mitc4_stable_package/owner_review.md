---

doc_id: DOC-OWNER-MITC4-STABLE-PACKAGE-001
revision: 0.1
status: owner_reviewed
review_mode: owner_review
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner Review - paquet MITC4 vers stable

Répondre séparément pour chacun des trois sous-scopes :
`mitc4-isotropic`, `mitc4-laminate` et `mitc4-orthotropic-homogeneous-ply`.

## Questions

**Q1.** La géométrie, les DDL, les repères locaux, les signes et la projection
des axes matériau sont-ils correctement décrits ?

**Q2.** La formulation, l'intégration, la masse cohérente, la condensation du
drilling et les algorithmes statique/modal/Newmark/harmonique sont-ils
suffisamment justifiés ?

**Q3.** Les maillages, chargements, blocages et conditions de comparaison sont-ils
reproductibles et visibles dans les figures et tableaux ?

**Q4.** Les erreurs primaires, résidus, invariants, bilans d'énergie et courbes
de convergence satisfont-ils le seuil applicable de 1 % ?

**Q5.** Les corrélations théorie, Code_Aster et CalculiX sont-elles clairement
identifiées comme corrélations de formulation, avec leurs versions et limites ?

**Q6.** Les exclusions S13/S23, dommage, rupture, délamination, grandes
déformations et orientation continue courbe sont-elles explicites et
acceptables ?

**Q7.** Décision pour le sous-scope : `stable`, `accepted_with_recommendations`,
`accepted_for_bounded_engineering_use` ou `more_evidence_required` ?

## Données de décision pour l'orthotrope mono-pli

Le sous-scope `mitc4-orthotropic-homogeneous-ply` a reçu une décision Owner
électronique. Les résultats techniques disponibles sont :

| Domaine | Résultat principal | Verdict technique |
|---|---:|---|
| Statique interne, 0°/45°/90° | résidus libres `8,09e-12` à `2,39e-10` | PASS |
| Modal plan, 0° | écart Code_Aster `0,892 %` à `16 x 4` | PASS sous 1 % |
| Modal plan, 45° | écart Code_Aster `0,884 %` à `56 x 14` | PASS sous 1 % |
| Modal plan, 90° | écart Code_Aster `0,604 %` à `48 x 12` | PASS sous 1 % |
| Newmark plan, 45° | écart final `0,413 %` | PASS sous 1 % |
| Harmonique plan, 45° | écart final `0,251 %` | PASS sous 1 % |
| Courbe facettisée, 0° axial | écart UZ final `0,012 %` avec CalculiX | PASS sous 1 % |
| Courbe dynamique axiale, 16 x 8 | modal `2,340 %`, Newmark `0,0786 %`, harmonique aligné `0,118 %` avec Code_Aster | PASS externe, seuils documentés |
| Diagnostic courbe dynamique 32 x 16 | modal `0,933 %`, Newmark `1,51 %`, harmonique aligné `16,30 %` | non-acceptance, limite de formulation |

Le périmètre stable proposé est strictement borné aux plaques planes avec les
orientations testées `0°/45°/90°` et aux panneaux courbes facettisés à
orientation axiale `0°`. Le cas courbe non axial à `45°` est conservé comme
preuve interne de projection, mais reste ouvert en corrélation externe : QF_solver
projette la direction de référence sur chaque facette alors que le deck
CalculiX utilisé applique une orientation globale unique. Cette différence ne
doit pas être masquée par le verdict.

### Références de preuve

- `docs/verification/mitc4_stable_package/orthotropic_one_ply_results_2026-08-21.md`
- `results/mitc4_orthotropic_one_ply_static_20260821/summary.json`
- `results/mitc4_orthotropic_one_ply_internal_20260821/summary.json`
- `results/mitc4_orthotropic_one_ply_codeaster_20260821/summary.json`
- `results/mitc4_orthotropic_modal_codeaster_20260821_56x14/summary.json`
- `results/mitc4_orthotropic_curved_axial_one_ply_calculix_20260821/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_20260821/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_codeaster_20260821_16x8_aligned/summary.json`
- `results/mitc4_orthotropic_curved_dynamic_codeaster_20260821_32x16_aligned/summary.json` (diagnostic)
- `output/pdf/mitc4_orthotropic_one_ply_stable_owner_review.pdf`

## Réponse Owner

| Sous-scope | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 |
|---|---|---|---|---|---|---|---|
| `mitc4-isotropic` |  |  |  |  |  |  |  |
| `mitc4-laminate` |  |  |  |  |  |  |  |
| `mitc4-orthotropic-homogeneous-ply` | OUI | OUI | OUI | OUI | OUI | OUI, exclusions maintenues | stable |

**Commentaires et recommandations :**

Owner accepte la géométrie et les aires de référence, la masse cohérente, les
invariants et la corrélation Code_Aster. Les exclusions rupture, dommage,
délamination et orientation courbe non axiale sont maintenues. La décision est
stable pour le périmètre borné documenté.

**Nom Owner :** Quentin Farinazzo

**Signature :** Déclaration Owner électronique enregistrée

**Date :** 2026-08-21

