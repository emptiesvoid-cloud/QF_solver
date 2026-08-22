---

doc_id: DOC-OWNER-DECISIONS-2026-08-22
revision: 0.1
status: owner_decisions_recorded_pending_audit
review_mode: owner_declared
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Decisions Owner - 22 aout 2026

Ces decisions sont la transcription de la declaration Owner fournie le 22 aout 2026. Elles ne constituent pas une signature manuscrite, une revue independante ou une certification. Le registre technique ne sera synchronise qu'apres audit.

## Synthese

| Scope | Decision Owner | Etat technique |
| --- | --- | --- |
| mitc3-laminate-static | accepted_for_bounded_engineering_use | PASS_EXTERNAL_CORRELATION |
| mitc3-laminate-dynamic-thin-planar | stable | PASS_EXTERNAL_CORRELATION_DKT |
| mitc3-laminate-static-curved-mixed-transverse | stable | PASS_WITH_AXIAL_EXCLUSION |
| mitc3-laminate-static-curved | accepted_for_bounded_engineering_use | BLOCKED_EXTERNAL_COMPARABILITY |
| tet4-total-lagrangian-structural-v2 | more_evidence_required | PASS_WITH_INDEPENDENT_REVIEW_REQUIRED |
| tet4-material-nonlinear | accepted_for_bounded_engineering_use | PASS_EXTERNAL_STRUCTURAL_BOUNDED |
| tet10-material-nonlinear | accepted_for_bounded_engineering_use | PASS_EXTERNAL_STRUCTURAL_BOUNDED |
| orthotropic-solid-tet4-tet10 | stable | PASS_EXTERNAL_CORRELATION |
| orthotropic-solid-modal | stable | PASS_EXTERNAL_CORRELATION |
| orthotropic-solid-transient-dynamic | stable | PASS_EXTERNAL_CORRELATION |
| contact-v1-linear-static-bounded | accepted_for_bounded_engineering_use | PASS_EXTERNAL_CORRELATION |
| contact-frictional-static | accepted_for_bounded_engineering_use | PASS_EXTERNAL_CORRELATION_SLIP_ONLY |
| large-tet4-linear-static | accepted_for_bounded_engineering_use | PASS_SCALABLE_PIPELINE_WITH_LIMITED_SCALING |
| mitc4-orthotropic-curved-out-of-acceptance | hors acceptance | DIAGNOSTIC_ONLY |

## Observations et actions

### 1. `mitc3-laminate-static`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : Patch plan [0/90/90/0] accepte dans son domaine; pas de promotion stable.
- Action suivante : Ajouter au moins deux layups symetriques : [0/45/45/0] et [45/0/0/45].

### 2. `mitc3-laminate-dynamic-thin-planar`

- Decision : `stable`
- Observation : Stable uniquement pour le sous-perimetre mince, plan, symetrique et sans dommage.
- Action suivante : Conserver les niveaux intermediaires >1 % visibles dans la publication.

### 3. `mitc3-laminate-static-curved-mixed-transverse`

- Decision : `stable`
- Observation : Stable comme sous-perimetre borne mixte/transverse; les increments proches de 5 % restent une recommandation.
- Action suivante : Ajouter une geometrie courbe et un raffinement avant toute extension generale.

### 4. `mitc3-laminate-static-curved`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : Domaine axial complet accepte comme usage borne, sans promotion stable.
- Action suivante : Ajouter des geometries et une reference externe de formulation comparable.

### 5. `tet4-total-lagrangian-structural-v2`

- Decision : `more_evidence_required`
- Observation : Le scope reste research / more_evidence_required. Deux sondes a 1 152 000 TET4 ont ete arretees pour limite de ressources avant production d'un resultat mecanique.
- Action suivante : Implementer une assemblage par blocs, matrix-free ou distribue avant une nouvelle sonde; conserver une revue independante avant toute promotion.

### 6. `tet4-material-nonlinear`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : J2 petites deformations accepte en usage borne.
- Action suivante : Planifier chargement, decharge, rechargement, cyclage et correlation structurelle externe pour une version ulterieure.

### 7. `tet10-material-nonlinear`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : J2 TET10 accepte en usage borne, sans extension rupture/dommage/contact.
- Action suivante : Ajouter des chemins cycliques et une seconde structure avant une cible stable.

### 8. `orthotropic-solid-tet4-tet10`

- Decision : `stable`
- Observation : Stable dans le domaine statique orthotrope homogene documente, apres reconciliation de la valeur historique.
- Action suivante : Corriger le document qui cite 1,3293 % et conserver 0,8772 % comme resultat de la campagne CG finale source.

### 9. `orthotropic-solid-modal`

- Decision : `stable`
- Observation : Stable pour le domaine modal TET4 orthotrope homogene teste.
- Action suivante : Maintenir les exclusions composite pli par pli, orientation courbe continue et dommage.

### 10. `orthotropic-solid-transient-dynamic`

- Decision : `stable`
- Observation : Stable pour le domaine Newmark orthotrope homogene teste.
- Action suivante : Conserver les limites sur amortissement, non-linearite, dommage et orientation variable.

### 11. `contact-v1-linear-static-bounded`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : Contact sans frottement accepte en domaine borne.
- Action suivante : Ajouter des geometries, branches et validations avant toute stabilite generale.

### 12. `contact-frictional-static`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : Frottement accepte en domaine borne, principalement sur la branche slip corrélee.
- Action suivante : Renforcer stick, grand glissement, normales actualisees et seconde correlation externe.

### 13. `large-tet4-linear-static`

- Decision : `accepted_for_bounded_engineering_use`
- Observation : Grand modele TET4 accepte pour la configuration PETSc/MPI mesuree.
- Action suivante : Reporter l'optimisation weak scaling, memoire, partitionnement et plusieurs configurations materielle.

### 14. `mitc4-orthotropic-curved-out-of-acceptance`

- Decision : `hors acceptance / aucune promotion`
- Observation : Hors acceptance; aucune promotion ni decision de maturite.
- Action suivante : Conserver uniquement comme diagnostic experimental interne, non publie comme preuve d'acceptation.

## DKT

DKT signifie *Discrete Kirchhoff Triangle*. C'est un element triangulaire mince de type Kirchhoff-Love qui impose discretement un cisaillement transverse quasi nul. Il sert ici de reference de limite mince; ce n'est pas la meme formulation que MITC3+ Reissner-Mindlin et il ne valide pas les coques epaisses ou courbes en general.

## Actions futures

- MITC3 statique : ajouter les layups symetriques `[0/45/45/0]` et `[45/0/0/45]`.
- TET4 total-lagrangien : preparer une campagne cible autour de 1,2 million d'elements, puis verifier convergence, memoire et independance de revue.
- J2 : planifier chargement/decharge/rechargement, cyclage, multiaxialite et correlation structurelle externe.
- KSP/PC et increments non lineaires : analyser pas de charge, line-search, residus, tangent consistante et choix du sous-solveur avant promotion stable.

## Trace

- Source : `qualification/reviews/owner_review_scope_closure_2026-08-21.json`
- Record : `qualification/reviews/owner_review_scope_decisions_2026-08-22.json`
- Date : `2026-08-22`
