# Dossier de revue Owner - promotion de maturite 0.2.1 alpha

**Document ID** : DOC-MATURITY-OWNER-REVIEW-021  
**Revision** : 0.1  
**Statut** : pret pour lecture Owner  
**Decision** : non renseignee

Cette page ne promeut aucun scope. Elle regroupe les decisions encore
necessaires apres l'audit automatise du registre
`results/maturity_promotion_final_20260821_v14/maturity_promotion_audit.json`.

Le paquet machine-readable complet est disponible dans
`results/maturity_promotion_final_20260821_v14/owner_review_packet.json`, avec
sa version lisible dans
`results/maturity_promotion_final_20260821_v14/owner_review_packet.md`.

## Nouveau dossier MITC3 dynamique

Le raffinement technique demande pour les trois scopes isotropes MITC3 est
maintenant archive dans :

`qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json`

La campagne utilise trois niveaux du meme modele : `8x2`, `16x4` et `24x6`.
Les ecarts finaux QF_solver / Code_Aster DKT sont les suivants :

| Scope | Ecart au niveau `24x6` | Variation entre les deux derniers niveaux | Statut technique |
| --- | ---: | ---: | --- |
| MITC3 modal | 0,673 % | frequence QF : 0,129 % | PASS |
| MITC3 Newmark | 0,174 % | protocole identique par niveau | PASS |
| MITC3 harmonique | 0,097 % | grille frequencielle identique par niveau | PASS |

Le dossier de questions sans decision est
`qualification/reviews/mitc3_dynamic_refinement_owner_review_pending.json`.

Les controles internes complementaires `MITC3-LAM-DYN-C10` (projection
algebrique `K/M` avec condensation) et `MITC3-LAM-DYN-C11` (quadrature Duffy
independante de la rigidite) et `MITC3-LAM-DYN-C12` (A/B/D et orientation)
sont PASS dans le registre v14. Ils renforcent la
coherence elementaire sans fermer la correlation externe generale au-dessus
de `1 %`.

## Dossiers historiques de revue Owner

Le tableau ci-dessous conserve la liste de travail historique des revues
identifiees pendant les campagnes precedentes. Il sert a retrouver les
artefacts et les limites, mais **ne constitue pas le decompte courant** et ne
doit pas etre additionne. Pour la decision actuelle, seul
`results/maturity_promotion_final_20260821_v14/maturity_promotion_audit.json`
fait foi : il identifie quatre gates Owner/relecture encore bloques, en plus
des deux blocages techniques MITC3 generaux.

| Scope | Gate | Motif de l'ouverture | Action attendue |
| --- | --- | --- | --- |
| `beam2-linear-static` | `BEAM2-LS-C04` | decision Owner dediee absente | Lire la correlation Code_Aster et statuer sur le domaine POU_D_E borne |
| `contact-frictional-static` | `CONTACT-FRIC-C04` | la revue sans frottement ne couvre pas Coulomb | Lire les trois geometries et statuer separement |
| `discrete-linear` | `DISCRETE-LS-C03` | decision Owner discrete absente | Statuer sur le systeme ressort-masse mono-DDL documente |
| `mitc3-laminate-dynamic` | `MITC3-LAM-DYN-C04` | decision Owner multicouche dynamique en attente | Lire la campagne plane [0/90/90/0] et maintenir les exclusions |
| `mitc3-laminate-dynamic-thin-planar` | `MITC3-LAM-DYN-THIN-C03` | preuve technique DKT sous 1 %; Owner Review manquante | Statuer uniquement sur le sous-périmètre mince plan |
| `mitc3-laminate-static` | `MITC3-LAM-STAT-C03` | decision Owner multicouche statique en attente | Statuer sur ABD, orientations et contraintes par pli hors singularite |
| `mitc3-laminate-static-curved` | revue Owner courbe absente | les criteres techniques passent | Relire les deux chargements et le raffinement courbe |
| `mitc3-laminate-static-curved-mixed-transverse` | `MITC3-LAM-STAT-CURVE-MT-C03` | preuve technique sous 1 %; axial explicitement exclu | Statuer uniquement sur les chargements mixte et transverse |
| `mitc4-laminate-dynamic-refined-three-layups` | `MITC4-LAM-DYN-REF-C03` | preuve technique sous 1 % sur trois layups | Statuer avec la réserve 10000 QUAD4 explicitement maintenue |
| `tet10-material-nonlinear` | `TET10-J2-C04` | cas structurel complexe sans decision dediee | Statuer sur le perimetre J2 experimental borne |
| `tet4-material-nonlinear` | `TET4-J2-C04` | decision Owner J2 TET4 absente | Statuer sur la reference constitutive Code_Aster |
| `tet4-total-lagrangian-structural-v2` | `TET4-TL-C04` | revue independante recommandee | Maintenir `research` tant que cette revue n'est pas obtenue |
| `orthotropic-solid-modal` | `ORTHO-MOD-C04` | revue statique ne couvre pas le modal; fiche creee | Statuer sur le perimetre modal et ses limites |
| `orthotropic-solid-transient-dynamic` | `ORTHO-NEW-C04` | revue statique ne couvre pas Newmark; fiche creee | Statuer sur le perimetre transitoire et ses limites |
| `large-tet4-linear-static` | `LARGE-TET4-C05` | weak scaling et materiel mesure; fiche creee | Accepter ou refuser explicitement le perimetre PETSc/MPI |

## Questions communes

1. Les preuves et les seuils sont-ils suffisants pour le domaine exact du
   scope lu ?
2. Les exclusions affichees sont-elles acceptables pour un usage engineering
   interne borne ?
3. La maturite ciblee est-elle appropriee, sans extrapolation vers les cas
   non testes ?
4. La decision est-elle `accepted_with_recommendations`,
   `accepted_for_bounded_engineering_use` ou `more_evidence_required` ?

Une decision doit etre datee, signee et enregistree dans un fichier de revue
dedie. L'audit automatise ne transforme jamais une preuve technique en
decision de maturite.

## Dossiers PDF disponibles

Les dossiers PDF actuels generes a partir des preuves controlees sont :

- `output/pdf/qf_solver_owner_review_stable_promotions_0_2_1.pdf`
  (dossier historique des promotions techniquement pretes ; verifier le
  registre v6 avant toute signature) ;
- `output/pdf/qf_solver_owner_review_open_gates_0_2_1.pdf`
  (dossier historique des gates Owner ; le decompte courant est celui du
  registre v6) ;
- `output/pdf/qf_solver_project_hygiene_architecture_audit_0_2_1.pdf`
  (audit structure, scripts, confidentialite et manques futurs) ;

- `output/pdf/owner_review_code_aster_correlations_2026-08-14_decision_record.pdf`
  (archive de la decision de correlation du 14 aout 2026) ;
- `output/pdf/owner_review_status_2026-08-14_decision_record.pdf`
  (archive de l'etat des revues au 14 aout 2026).

Les sources Markdown des nouveaux dossiers sont
`docs/verification/owner_review_stable_promotions_0_2_1.md`,
`docs/verification/owner_review_open_gates_0_2_1.md` et
`docs/verification/project_hygiene_architecture_audit_0_2_1.md`.

## Etat automatise actuel

La derniere execution de l'audit v14 donne :

```text
scopes: 37
criteria/path checks: 37/37
target stable: 23
blocked scopes: 6 (2 techniques, 4 Owner/relecture)
```

Le blocage technique concerne uniquement les scopes generaux
`mitc3-laminate-dynamic` et `mitc3-laminate-static-curved`. Le sous-scope
MITC3 dynamique mince plan, le sous-scope courbe mixte/transverse et le
sous-scope MITC4 dynamique a trois layups ont leurs criteres techniques en
`PASS`, mais attendent encore une decision Owner. Le TET4 Total Lagrangian
attend une relecture independante ; il ne doit pas etre promu par une simple
self-review.

Les criteres pending sont maintenant rattaches a une fiche de revue dediee dans
`qualification/reviews/`. Ces fiches restent sans decision ni signature. Les
fiches ajoutees pour cette passe concernent discrete lineaire, TET10 J2,
orthotrope modal, orthotrope Newmark et grand modele TET4.

Le champ machine-readable `blocking_classification` distingue desormais
`owner_decision_pending` d'un echec technique reel. L'audit v13 contient
`4` scopes bloques par une decision ou une relecture Owner et `2` scopes dont
les criteres techniques restent a corriger. Les autres lignes du tableau
precedent constituent le registre historique des revues a enregistrer; elles
ne doivent pas etre additionnees au decompte v5.

Avant d'enregistrer une decision, la fiche peut etre controlee avec :

```powershell
python .\qf_solver.py owner-review-check --input .\qualification\reviews\beam2_linear_static_owner_review_pending.json --scope beam2-linear-static --require-decision
```

Le code de sortie `4` est attendu pour une fiche encore pending. La commande
ne modifie ni la fiche, ni la matrice de maturite.

Les six correlations externes relancees avec Docker actif retournent `6 passed`
(BEAM2 statique/modal/Newmark/transverse, discret et contact frictionnel).
Cette execution confirme les preuves techniques disponibles, mais ne remplace
pas les decisions Owner du paquet.
