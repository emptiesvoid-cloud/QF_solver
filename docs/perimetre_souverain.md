---
doc_id: DOC-GOV-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Perimetre souverain du solveur mecanique

## Objectif

Construire un solveur EF souverain, transparent, robuste et qualifiable sur un
perimetre mecanique precis, puis elargir ce perimetre par campagnes de preuves.

Le solveur ne cherche pas a cloner tous les logiciels industriels existants. Il
vise d'abord le remplacement de cas bornes, repetables et auditables:

- statique lineaire de composants simples;
- coques MITC4 pour plaques et panneaux;
- solides TET4/TET10 pour pieces 3D tetraedriques;
- modal et dynamique lineaire;
- reponse harmonique lineaire;
- premiers cas non-lineaires petits deplacements sous statut experimental.

## Perimetre v1 qualifiable

| Domaine | Statut vise | Condition de confiance |
| --- | --- | --- |
| TET4 statique lineaire | stable | Equilibre, energie, contraintes et evidence. |
| MITC4 statique lineaire | stable | Verification MITC4 et benchmarks conserves. |
| Validation maillage | stable | Rejet des elements invalides et warnings qualite. |
| Audit boite blanche | stable | Matrices, vecteurs, ddl, residus et checks. |
| TET10 lineaire isotrope | stable apres tests renforces | Revue interne acceptee avec recommandations; campagne finale complexe requise avant acceptation totale. |
| Modal | experimental vers stable | Residus propres et orthogonalites a renforcer. |
| Newmark | experimental vers stable | Energie et cas analytiques a renforcer. |
| Harmonique | experimental vers stable | Coherence 0 Hz/statique et resonance a renforcer. |
| Non-lineaire | experimental | Rester hors profil `qualification` tant que les preuves sont incompletes. |
| BEAM2, ressorts et masses | planifie V1 | Formulations analytiques, energie, masse et dynamique verifiees. |
| MPC et RBE | planifie V1 | Conservation cinematique, forces, moments et absence de rigidite parasite. |
| Contact sans frottement | planifie V1 experimental | Petites transformations, complementarite et convergence controlees. |
| Contact avec frottement | planifie V1 experimental | Coulomb regularise, dissipation et transitions adhesion/glissement verifiees. |

## Frontiere produit V1 / V2

La fermeture fonctionnelle de la V1 est limitee a `BEAM2`, ressorts, masses
concentrees, MPC/RBE et contact mecanique. Le contact est introduit sans
frottement avant l'extension au frottement de Coulomb.

HEX8, WEDGE, PYRAMID, thermique, thermoelasticite, integration temporelle
`generalized-alpha`, spectres, PSD, hyperelasticite, dommage, delaminage,
raffinement adaptatif et reduction de modele avancee sont reportes en V2.
Cette separation permet de publier le socle existant et de recueillir des
retours sans presenter les extensions futures comme disponibles.

## Definition du remplacement acceptable

Un cas peut remplacer un calcul logiciel externe seulement si:

- il appartient au perimetre declare;
- le maillage passe sans `FAIL`;
- le dossier `evidence` est genere;
- le resume qualification est `PASS`;
- les criteres numeriques du manifest de campagne sont tous `PASS`;
- le cas est declare `replacement_candidate` et ressort `replacement_ready`;
- les grandeurs cles sont comparees a une reference explicite avec tolerance;
- au moins une reference independante passe pour ce cas;
- les limites connues ne touchent pas le cas;
- une reference analytique, experimentale ou logiciel tiers existe pour la
  famille de cas;
- l'ecart attendu est documente avant usage projet.

## Campagne executable

Le manifest `qualification/campaign.json` liste les cas souverains minimaux.
La commande:

```powershell
python .\qf_solver.py qualify --manifest .\qualification\campaign.json --output .\results\qualification_campaign
```

genere:

- un dossier de preuve par cas resolu;
- un rapport maillage pour les cas de rejet;
- un manifeste `evidence_manifest.json` avec empreintes SHA-256 par artefact;
- une verification automatique du manifeste pour chaque dossier de preuve;
- `qualification_campaign_summary.json`;
- `qualification_campaign_summary.md`.

Chaque cas contient des criteres executables (`checks`) qui valident les
grandeurs importantes: residus, energie, maturite, score de confiance, presence
des sorties attendues ou rejet maillage.

Le resume de campagne distingue:

- les cas suivis pour elargir le perimetre;
- les cas candidats remplacement;
- les cas effectivement `replacement_ready`.

La campagne actuelle utilise des references `non_regression` pour figer les
valeurs numeriques du solveur. Ces references securisent les evolutions du code,
mais les familles candidates devront progressivement recevoir des references
`analytic`, `third_party` ou `experimental` pour augmenter le niveau de
confiance.

Regle de garde-fou: une non-regression seule ne rend jamais un cas
`replacement_ready`. Il faut au moins une reference independante:
`analytic`, `equilibrium_closed_form`, `third_party` ou `experimental`.

Etat courant des candidats remplacement:

- `SOV-TET4-STATIC-001`: reference analytique fermee pour le deplacement UX et
  le von Mises du tetraedre unite contraint.
- `SOV-MITC4-STATIC-001`: reference d'equilibre fermee pour l'effort membrane
  `Nxx`; le deplacement reste suivi en non-regression.
- `SOV-MODAL-TET4-001`: reference analytique de premiere frequence de
  cisaillement; le modal reste suivi avant passage candidat remplacement.
- `SOV-DYN-SDOF-001`: reference analytique d'energie initiale sur vibration
  libre Newmark 1 ddl; la dynamique reste suivie avant passage candidat
  remplacement.
- `SOV-HAR-SDOF-001`: reference analytique amplitude/phase sur reponse
  harmonique 1 ddl; l'harmonique reste suivi avant passage candidat
  remplacement.

## Prochain elargissement

Avant de declarer une famille `stable`, ajouter au moins:

- un cas analytique;
- un cas de non-regression;
- un cas maillage degrade;
- un cas CLI;
- un cas API;
- un seuil d'acceptation numerique documente.
