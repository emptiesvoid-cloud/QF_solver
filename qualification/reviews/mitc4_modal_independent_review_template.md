# Revue independante du scope MITC4 modal

## Regle d'independance

Ce formulaire doit etre rempli par une personne qui n'a ni implemente les
fonctions modales examinees, ni produit les resultats de reference. Quentin
Farinazzo peut realiser la validation mecanique interne, mais ne peut pas
signer cette revue comme independante puisqu'il est l'auteur du solveur.

Une execution Code_Aster constitue une correlation logicielle externe. Elle
ne remplace pas une Owner review independante.

## Dossier a examiner

- `docs/verification/revue_mitc4_modale.md`
- `qualification/vnv/external/code_aster_modal/reference/summary.json`
- `results/VNV-MITC4-MODAL-EXTENDED-005/summary.json`
- `results/VNV-MITC4-MODAL-EXTENDED-005/vnv_manifest.json`
- `qualification/reviews/mitc4_modal_pending.json`

## Controles demandes

- [ ] J'ai verifie la formulation de la masse coherente et la gestion du drilling.
- [ ] J'ai verifie les dix frequences contre Navier et Code_Aster.
- [ ] J'ai verifie les comparaisons de sous-espaces pour les modes multiples.
- [ ] J'ai verifie les six modes rigides de la structure libre-libre.
- [ ] J'ai verifie la coque courbe, sa distorsion et son objectivite.
- [ ] J'ai verifie la concordance `eigh/eigsh` et l'absence de conversion dense.
- [ ] J'ai examine les scripts, criteres, resultats bruts et manifestes.
- [ ] J'ai consigne toute anomalie ou reserve ci-dessous.

## Decision

Cocher une seule decision:

- [ ] `accepted`
- [ ] `accepted_with_recommendations`
- [ ] `rework_required`
- [ ] `rejected`

Commentaires et anomalies:

..............................................................................

..............................................................................

| Signature | Valeur a renseigner |
| --- | --- |
| Nom |  |
| Organisation |  |
| Competence/referentiel |  |
| Declaration d'independance |  |
| Date |  |
| Decision |  |
| Revision Git examinee |  |
| Empreinte du manifeste examine |  |

Sans identite, declaration d'independance, revision et signature, cette revue
reste `pending` et ne permet aucune revendication de qualification externe.
