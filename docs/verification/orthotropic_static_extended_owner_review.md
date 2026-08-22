---
doc_id: DOC-OWNER-ORTHO-STATIC-EXTENDED-001
revision: 0.2
status: owner_decision_recorded_pending_audit
review_mode: owner_review
promotion_target: stable
scope: orthotropic-solid-tet4-tet10
---

# Owner review — orthotropie statique TET4/TET10, extension de raffinement

La campagne ajoute un niveau TET4 vectorisé large à `h=0,020 m`, soit onze niveaux TET4 au total. La référence reste le TET10 séparé à `h=0,09 m`. L'objectif d'ingénierie est une erreur principale finale inférieure ou égale à `1 %`.

| Famille | Niveau fin | Éléments | Erreur déplacement | Erreur énergie | Résidu |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | `h=0,020 m` | 564 525 | `0,8772 %` | `0,8647 %` | `9,963e-9` |
| TET10 | `h=0,13 m` | 2 607 | `0,2918 %` | `0,3027 %` | `7,263e-12` |

Le TET4 passe désormais le gate technique `1 %` grâce à l'assemblage vectorisé et au solveur CG/Jacobi : 2 510 itérations, résumé compact et résidu libre inférieur à `1e-8`. Le résultat est une preuve technique du sous-domaine statique orthotrope.

Une ancienne version de cette page mentionnait `1,3293 %` pour le TET4. Cette
valeur correspondait a la campagne intermediaire `extended_005`. La campagne
CG finale `large_cg_006`, utilisee pour la decision Owner, donne `0,8772 %` et
`0,8647 %` d'erreur energie. La valeur historique reste traçable dans le
registre, mais ne doit plus etre presentee comme le resultat final.

Confirmation Owner du 22 aout 2026 : `stable` pour le domaine statique
orthotrope homogene documente, sous reserve de l'audit d'application et sans
extension au composite pli par pli, a l'orientation courbe continue ou au
dommage. Voir `qualification/reviews/owner_review_scope_decisions_2026-08-22.json`.

Cette confirmation est un enregistrement electronique de decision ; elle n'est
pas une signature manuscrite et ne constitue pas une qualification externe.

## Questions Owner

### Q1 — Convergence

Les dix niveaux TET4 et les quatre niveaux TET10 montrent-ils une convergence suffisamment monotone dans le domaine orthotrope statique déclaré ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Seuil d'erreur

Le résultat TET10 sous `1 %` et le TET4 final à `0,8772 %` sont-ils acceptables pour le domaine statique orthotrope homogene documente ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Limites

Les exclusions de l'orientation continue courbe, du composite pli par pli, de l'endommagement, de la plasticité anisotrope et des singularités restent-elles acceptables ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Décision

Décision proposée : `accepted_with_recommendations`, `accepted_for_bounded_engineering_use`, `stable` ou `more_evidence_required`.

Commentaire :

Signature Owner :

Date :

## Artefacts

- `qualification/vnv/orthotropic_solid_convergence_extended_005/reference/summary.json`
- `qualification/vnv/orthotropic_solid_convergence_extended_005/reference/report.md`
- `qualification/vnv/orthotropic_solid_convergence_extended_005/reference/orthotropic_convergence.png`
- `qualification/maturity_evidence_0_2_1/orthotropic.json`
- `output/pdf/orthotropic_static_extended_owner_review.pdf`
- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/summary.json`
- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/tet4_h6.summary.json`
- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/tet4_h6.mesh_summary.json`
- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/orthotropic_convergence.png`
- Commande d'extension : `python scripts/extend_orthotropic_tet4_refinement_vnv.py --campaign qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference --mesh-size 0.020 --solver-method large_cg`
