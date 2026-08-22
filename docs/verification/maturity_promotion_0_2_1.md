---
doc_id: DOC-MATURITY-PROMOTION-021-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.1a0
owner_review: pending
reviewer: ""
approver: ""
---

# Plan de promotion des maturites 0.2.1a0

## Objet

Cette alpha ne cree aucun nouvel element, solveur ou format de modele. Son but
est d'etendre les preuves des fonctions deja implementees, sans transformer un
statut par simple renommage.

Le registre machine-readable est
`qualification/maturity_promotion_0_2_1.json`. Il couvre chaque scope pris en
charge par `qualification/element_analysis_matrix.json`, ainsi que les scopes
materiaux orthotropes suivis dans les exigences.

## Regle de promotion

Une extension du domaine experimental ne supprime pas les limites existantes.
Une promotion vers `owner_accepted` exige les preuves du domaine elargi et une
`owner_review` datee. Le statut `stable` exige en plus une preuve analytique ou
un invariant, une convergence, une correlation externe lorsque comparable,
des diagnostics numeriques, des non-regressions et une evidence
reproductible.

## Politique renforcee des erreurs

Depuis le 21 aout 2026, toute erreur relative principale d'ingenierie doit
etre inferieure ou egale a `1 %` pour autoriser une promotion vers `stable`.
Cette regle couvre les deplacements, frequences, reponses harmoniques,
historiques Newmark, reactions ou resultantes, energies et champs de
contraintes ou deformations lorsqu'ils sont compares hors singularite. Une
valeur superieure a `1 %` bloque automatiquement le scope. Une exception
exige une justification mecanique formelle, un raffinement reproductible
supplementaire et une decision Owner datee; elle ne transforme pas
automatiquement le scope en `stable`.

Les increments de maillage, residus et diagnostics de stabilisation restent
des criteres distincts, mais sont egalement controles par la matrice lorsqu'ils
sont utilises pour justifier la convergence.

### Instantane de l'audit renforce

L'audit avec la matrice a 1 % couvre 34 scopes et laisse 4 scopes bloques :
`mitc3-laminate-dynamic`, `mitc3-laminate-static-curved`,
`mitc4-laminate-dynamic` et `tet4-total-lagrangian-structural-v2`. Le
sous-perimetre MITC4 multicouche statique
plan regulier est techniquement pret pour une Owner review cible `stable`;
le probe courbe oblique reste optionnel et hors de ce sous-perimetre.
Ce bilan est plus strict que les anciennes campagnes a 2 %, 5 % ou 10 %;
les anciennes valeurs restent historiques et ne constituent pas une
autorisation de promotion.

## Lots prioritaires

| Priorite | Cible | Scopes |
| --- | --- | --- |
| P1 | `stable` | TET4/TET10 isotropes lineaire, modal, Newmark et harmonique; MITC3/MITC4 isotropes; BEAM2 et discret deja acceptes |
| P1 | `owner_accepted` | BEAM2 statique et discret statique |
| P2 | `owner_accepted` | MITC3 et MITC4 stratifies, TET10 J2, TET4 J2, orthotropie solide et contact statique |
| P3 | `owner_accepted` ou maintien experimental | contact avec frottement et total-lagrangien TET4 |

Le total-lagrangien TET4 reste volontairement `experimental` tant que les
preuves de flambement, post-flambement et sensibilite au chemin de charge ne
sont pas completes. Cette prudence est une limitation explicite, pas une
regression du code.

## Evidence commune

Chaque fiche de scope choisit un gabarit d'evidence : statique, modal,
Newmark, harmonique, stratifie, non lineaire, contact ou discret. Les gabarits
imposent notamment :

1. une reference analytique ou un invariant mecanique ;
2. au moins trois maillages ou pas de temps avec un indicateur de convergence ;
3. au moins trois geometries ou familles de chargement representatifs ;
4. residus, reactions, energies, modes rigides ou observables dynamiques ;
5. une correlation Code_Aster ou CalculiX lorsque l'observable est comparable ;
6. une `owner_review`, puis seulement une mise a jour de la matrice.

Les exclusions restent affichees dans la documentation et les resultats :
dommage, delaminage, rupture, dynamique non lineaire et extrapolation hors du
domaine effectivement verifie ne sont pas inclus par cette alpha.

## Controle

Le test `tests/unit/test_maturity_promotion_plan.py` interdit une fiche
manquante, dupliquee ou incoherente avec la matrice element/analyse. Toute
nouvelle ligne implementee devra donc recevoir une intention de preuve avant
une revendication de maturite.

## Audit executable

Le premier lot de realisation est l'audit des preuves existantes et de leurs
chemins controles. Il ne modifie pas automatiquement la matrice de maturite :

```powershell
python .\qf_solver.py maturity-promotion --output .\results\maturity_promotion_0_2_1
```

Le rapport produit distingue les chemins d'evidence presents, les decisions
`owner_review` detectees et les criteres du gabarit qui ne sont pas encore
decomposes en controles machine-readables. La commande peut devenir bloquante
avec `--fail-on-blocking`, mais le comportement par defaut permet de construire
le dossier sans masquer les travaux restants.

## Premier lot executable : TET4 statique

Le registre atomique `qualification/maturity_criteria_0_2_1.json` complete le
plan general. Il ne change pas la maturite de la matrice. Il permet de verifier
separement :

1. la campagne analytique executee et ses bundles verifies ;
2. les niveaux de convergence flexion, traction, compression et torsion ;
3. les familles de chargement traction, compression, pression et force volumique ;
4. l'equilibre libre, les reactions, l'identite energie-travail et la symetrie
   de la raideur reduite ;
5. la presence des sorties JSON, audit, mesh report, VTU, manifeste et tests
   API/CLI/export ;
6. la regle d'oracle externe, declaree non applicable pour le cas ferme
   analytique et a completer sur les structures multi-elements.

La campagne de preuve correspondante est archivee sous
`qualification/evidence/maturity_promotion_0_2_1/tet4_linear_static_campaign/`.
Elle passe `13/13`, avec `12` bundles verifies. Le resultat de l'audit est
`READY_FOR_OWNER_REVIEW` pour `tet4-linear-static` : les criteres sont
structures et passes, mais aucune promotion vers `stable` n'est automatique.
Une nouvelle owner review ciblee reste obligatoire.

## Extension TET4 dynamique

Le registre compact
`qualification/maturity_evidence_0_2_1/tet4_linear_dynamics.json` rassemble les
preuves de la meme campagne pour les trois scopes dynamiques :

| Scope | Preuve interne | Preuve Code_Aster | Gate |
| --- | --- | --- | --- |
| `tet4-modal` | residu propre, orthogonalites masse/raideur | six frequences sur maillage identique, trois niveaux spatiaux | `READY_FOR_OWNER_REVIEW` |
| `tet4-transient-dynamic` | vibration libre, energie et residu dynamique | quatre niveaux temporels et historique de deplacement | `READY_FOR_OWNER_REVIEW` |
| `tet4-harmonic-response` | limite statique a zero Hz, balayage et finitude | quatre frequences communes et reponse finie | `READY_FOR_OWNER_REVIEW` |

Les ecarts externes mesures restent tres inferieurs aux seuils du registre :
`7,89e-13` au maximum pour les frequences modales, `8,16e-11` pour
l'historique Newmark et `5,33e-12` pour la reponse harmonique. Ces chiffres
ferment le lot automatique de preuve, pas la decision de maturite. Les trois
scopes necessitent encore une owner review datee avant toute modification de
`qualification/element_analysis_matrix.json`.

## Extension TET10 statique

Le registre `qualification/maturity_evidence_0_2_1/tet10_linear_static.json`
structure egalement le scope `tet10-linear-static`. Les quatre controles
atomiques passent : convergence traction/flexion/torsion, equilibre et energie,
masse et charges de face, puis correlation CalculiX C3D10. La correlation sur
maillage identique donne `6,84e-5` sur le champ de deplacement et `6,45e-5`
sur la rotation terminale.

Le gate reste `READY_FOR_OWNER_REVIEW`, car la decision existante est une
acceptation avec recommandations et demande encore une campagne finale sur
pieces et assemblages complexes. La preuve ne permet donc pas de changer seule
la ligne vers `stable`.

Le lot TET10 dynamique est également décrit dans
`qualification/maturity_evidence_0_2_1/tet10_linear_dynamics.json`. Les
invariants internes modal, Newmark et harmonique passent. La campagne externe
`VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018` est maintenant archivée avec six
fréquences, quatre niveaux temporels et trois niveaux spatiaux; les écarts
maximums sont `3,225e-11` en modal, `5,779e-12` sur l'historique Newmark et
`6,190e-12` en harmonique. Les trois scopes passent leurs critères techniques
et sont `READY_FOR_OWNER_REVIEW`; aucune maturité n'est modifiée
automatiquement.

Une campagne temporelle complémentaire est archivée dans
`qualification/maturity_evidence_0_2_1/tet10_dynamic_refinement_001.json`.
Elle ajoute les niveaux `T/30`, `T/60`, `T/120` et `T/240` : l'erreur RMS
finale vaut `0,014369 %`, l'incrément adjacent final `0,472096 %`, la dérive
énergétique `4,73e-11 %` et le résidu `3,67e-8`. Le maximum des niveaux
grossiers (`3,759715 %`) reste un diagnostic publié, tandis que l'incrément
final est le critère de stabilisation. Le dossier PDF et la figure sont
disponibles sous `output/pdf/tet10_dynamic_refinement_owner_review.pdf` et
`qualification/vnv/external/tet10_dynamic_refinement_001/reference/`.

## Extension MITC4 isotrope

Le registre compact `qualification/maturity_evidence_0_2_1/mitc4_isotropic_linear.json`
consolide les preuves MITC4 isotropes déjà présentes sans changer la matrice
de maturité. Les critères atomiques sont ajoutés à
`qualification/maturity_criteria_0_2_1.json`.

| Scope | Vérifications internes | Corrélation externe | Gate actuel |
| --- | --- | --- | --- |
| `mitc4-linear-static` | patchs, statique, shear-locking, résidu `1,217e-16` | Code_Aster DKQ sur trois maillages QUAD4, écart vectoriel fin `1,7565 %` | `READY_FOR_OWNER_REVIEW` |
| `mitc4-modal` | cinq niveaux, MAC minimal `0,99999983`, résidu `2,409e-9` | Code_Aster DKQ, dix modes, erreur fréquence max `1,872 %` | `READY_FOR_OWNER_REVIEW` |
| `mitc4-transient-dynamic` | quatre pas `T/20` à `T/160`, RMS primaire `0,0987 %`, énergie et résidu contrôlés | Code_Aster, pics déplacement `5,21 %`, contrainte `10,50 %` conservés comme différence de modèle spatial, corrélations `0,954` et `0,956` | `READY_FOR_OWNER_REVIEW` |
| `mitc4-harmonic-response` | limite statique `4,519e-11`, réponse complexe `1,254e-7`, résidu `1,748e-9` | NAFEMS 13H/Code_Aster, écart maximal `3,245 %` | `READY_FOR_OWNER_REVIEW` |

Les comparaisons Code_Aster sont des preuves externes complémentaires. Les
formulations DKQ et MITC4 ne sont pas identiques et les contraintes complexes
Code_Aster peuvent être reconstruites hors de son post-traitement coque natif.
Ces limites sont conservées dans le registre plutôt que masquées derrière un
verdict global.

### Règle d'erreur d'ingénieur pour la promotion stable

À partir de cette baseline, toute erreur relative sur un observable primaire
d'ingénieur doit être inférieure ou égale à `1 %` pour qu'un scope puisse être
promu `stable` : déplacement, fréquence propre, réponse harmonique, RMS
Newmark, réaction ou résultante, énergie globale, ainsi que contrainte ou
déformation mesurée hors singularité. Une valeur supérieure à `1 %` bloque la
promotion, même si un ancien seuil `engineering` est respecté. Une exception
nécessite simultanément une justification mécanique formelle, une étude de
convergence complémentaire et une décision Owner explicite. Les résidus, les
incréments de maillage, les erreurs de quadrature et les critères itératifs
restent suivis par leurs propres seuils et ne sont pas assimilés à une erreur
d'observable primaire.

Pour Newmark, l'observable primaire de fermeture est l'erreur RMS face à la
propagation modale exacte indépendante (`0,0987 %`, donc sous `1 %`). Les pics
Code_Aster de `5,21 %` et `10,50 %` restent publiés comme diagnostics de la
différence spatiale MITC4/DKQ; ils ne sont pas interprétés comme une erreur de
l'intégrateur temporel.

La statique MITC4 ne peut donc pas être promue sur la seule base de ce lot :
il faut archiver une exécution externe locale comparable, avec géométrie,
maillage, chargement, blocages, version du code et résultats normalisés. Les
trois scopes dynamiques sont prêts pour une nouvelle owner review, mais aucune
ligne de la matrice n'est modifiée automatiquement.

## Promotion MITC4 multicouche dynamique

Le premier scope P2 borné traité par le registre est
`mitc4-laminate-dynamic`. Le ledger
`qualification/maturity_evidence_0_2_1/mitc4_laminate_dynamic.json` rassemble
les trois empilements plans symétriques, les trois niveaux de maillage, la
campagne modale/Newmark/harmonique et la corrélation Code_Aster.

| Contrôle | Résultat | Limite ou interprétation |
| --- | ---: | --- |
| Empilements étudiés | 3 | `[0/90/90/0]`, `[45/-45/-45/45]`, `[0/45/45/0]` |
| Niveaux de maillage | 36, 72, 144 éléments | raffinement équilibré et directionnel |
| Erreur modale externe maximale | `1,678 %` | limite `10 %` |
| Erreur historique Newmark | `0,422 %` | limite `12 %` |
| Erreur harmonique | `0,205 %` | limite `12 %` |
| Résidu modal QF_solver | `3,609e-9` | limite `1e-7` |
| Résidu dynamique QF_solver | `1,495e-11` | limite `1e-7` |
| Enveloppe tardive du cas amorti | `0,847` | seuil `0,95` |

Les critères `MITC4-LAM-C01` à `MITC4-LAM-C03` passent. Le cas 10 000 QUAD4
`[45/-45/-45/45]` est conservé comme `NOT_APPLICABLE` optionnel dans
`MITC4-LAM-C04` : son résidu modal d'environ `7,383e-6` ne permet pas une
comparaison mode par mode au seuil `1e-7`. Il ne bloque pas l'usage borné
actuel, mais interdit toute extension implicite vers les grands maillages ou
une maturité stable.

Le gate est donc `READY_FOR_OWNER_REVIEW`, avec une décision Owner existante
`accepted_for_bounded_engineering_use`. Cette étape ne change pas la matrice :
la prochaine action Owner est de relire le domaine exact et de décider si
la ligne peut passer de `owner_accepted_experimental_bounded_use` à
`owner_accepted`. Les domaines courbes dynamiques, non symétriques, dommage,
rupture et délaminage restent exclus.
## Promotion MITC3 multicouche

Le lot MITC3 est structure dans
`qualification/maturity_evidence_0_2_1/mitc3_laminate.json`. Il distingue le
panneau courbe statique a orientation projetee du porte-a-faux dynamique plan.

| Scope | Preuves disponibles | Blocage de promotion |
| --- | --- | --- |
| `mitc3-laminate-static-curved` | trois niveaux fins `4096/9216/16384` triangles, deux familles de chargement, CalculiX S6, Code_Aster DST, projection d'orientation; ecarts fins `1,220 %` et `1,073 %` | `BLOCKED_OWNER_REVIEW` : la preuve technique passe; une decision Owner pour la cible suivante reste necessaire |
| `mitc3-laminate-dynamic` | patch, modal, Newmark, harmonique, Code_Aster DST; erreurs `3,957 %`, `2,318 %`, `1,345 %` | `MITC3-LAM-DYN-C03` : un seul maillage dynamique; `MITC3-LAM-DYN-C04` : owner review dediee absente |

Les criteres de calcul et les chemins d'artefacts du statique courbe passent.
Le scope dynamique reste `BLOCKED_CRITERIA_FAILED` par sa revue Owner dediee.
La correlation externe ne change aucune maturite automatiquement.

Cette distinction est importante : une preuve externe positive confirme les
observables du cas execute, mais ne suffit pas a elargir le domaine a d'autres
geometries, charges, maillages ou regimes dynamiques. Les contraintes par pli,
les quantites interlaminaires, le dommage et la delamination restent exclus.

## Promotion TET10 J2

Le scope `tet10-material-nonlinear` est maintenant structure dans
`qualification/maturity_evidence_0_2_1/tet10_j2.json`. Le dossier contient la
correlation de reference sur barre droite et le cas structural complexe a
charges combinees.

| Cas | Resultat | Observables |
| --- | --- | --- |
| Barre droite monotone | `PASS_EXTERNAL_CORRELATION` | erreur deplacement finale `0,0318 %`, PEEQ RMS `0,551 %`, six niveaux de charge |
| Equerre re-entrante historique | `PASS_EXTERNAL_CORRELATION` | deplacement RMS `0,0125 %`, PEEQ RMS `1,844 %`, residu max `1,972e-9` |
| Equerre re-entrante raffinee | `PASS_EXTERNAL_CORRELATION` | deplacement RMS `0,0090 %`, PEEQ RMS `0,8867 %`, residu max `4,666e-11` |

Les deux cas utilisent TET10/TETRA10 et Code_Aster `VMIS_ISOT_LINE` sur des
maillages identiques. Les contraintes ponctuelles singulieres, la rupture,
le contact, les grandes deformations et les chargements cycliques restent
exclus.

Le critere `TET10-J2-C04` bloque encore la promotion : le cas complexe est
techniquement passe, mais la decision Owner dediee n'est pas archivee. La
revue existante demande explicitement cette etape avant de sortir la famille
J2 de sa maturite experimentale. Le gate reste donc
`BLOCKED_CRITERIA_FAILED`; aucune ligne de matrice n'est modifiee.

## Promotions P1 BEAM2 et discret

Les premiers scopes P1 statiques sont maintenant decrits par
`qualification/maturity_evidence_0_2_1/beam2_discrete_static.json`.

| Scope | Preuve technique | Blocage |
| --- | --- | --- |
| `beam2-linear-static` | reference analytique sur cinq niveaux, puis correlation Code_Aster `POU_D_E` sur les memes maillages `4, 8, 16`; ecart fin `0,002808 %`, increments finaux `< 2,1e-12` | `BEAM2-LS-C04` : Owner review absente |
| `discrete-linear` | Code_Aster DIS_T, erreur statique `1,388e-16`, frequence exacte, Newmark et harmonique finis | `DISCRETE-LS-C03` : owner review dediee absente |

Les controles BEAM2 sont maintenant passes et la correlation externe est
archivee avec l'image Code_Aster epinglee. Le scope reste bloque uniquement par
la decision Owner. La correlation externe ne change pas automatiquement la
maturite et ne vaut pas validation de poutres epaisses ou de non-linearites.
Le scope discret reste bloque par sa revue dediee.

## Promotions des solides orthotropes

Le registre `qualification/maturity_evidence_0_2_1/orthotropic.json` rassemble
les preuves statiques et dynamiques disponibles pour les materiaux orthotropes
3D. Cette etape ne change pas la matrice de maturite : elle rend les preuves
lisibles par l'audit et identifie les decisions encore necessaires.

| Scope | Preuves disponibles | Etat de la promotion |
| --- | --- | --- |
| `orthotropic-solid-tet4-tet10` | Deux cas externes Code_Aster/CalculiX sur maillages identiques, patch TET4/TET10, objectivite par rotation, convergence et grand modele interne | `READY_FOR_OWNER_REVIEW` |
| `orthotropic-solid-modal` | Quatre niveaux spatiaux, erreur theorique fine `0,00772 %`, residu `2,625e-12`, orthogonalite de masse `1,122e-16`, correlation Code_Aster `1,205e-13` | `READY_FOR_OWNER_REVIEW` cible `stable` |
| `orthotropic-solid-transient-dynamic` | Huit niveaux temporels, increment final `0,1119 %`, residu `2,228e-10`, derive energetique nulle, correlation Newmark Code_Aster `6,25e-14` | `READY_FOR_OWNER_REVIEW` cible `stable` |

Le dossier PDF cible est `output/pdf/orthotropic_modal_newmark_stable_owner_review.pdf`.
Les deux fiches Owner associees restent en attente de signature :
`qualification/reviews/orthotropic_modal_owner_review_pending.json` et
`qualification/reviews/orthotropic_transient_dynamic_owner_review_pending.json`.
La campagne technique respecte la regle commune d'erreur principale `<= 1 %`,
mais cette preuve ne vaut pas decision de maturite.

La statique orthotrope dispose deja d'une revue Owner acceptee avec
recommandations. Elle reste borne par l'orientation constante par materiau,
region ou element; le suivi continu de fibres courbes, le composite pli par
pli, le dommage, la plasticite anisotrope et les grandes deformations sont
exclus.

Les preuves modales et Newmark sont techniquement positives et corrélées a
Code_Aster, mais la revue statique du 2026-07-22 exclut explicitement la
dynamique. Une decision Owner dediee est donc obligatoire avant toute promotion
vers `owner_accepted`. La promotion automatique reste interdite, meme lorsque
tous les calculs numeriques passent.

## Promotion du contact statique avec frottement

Le lot est maintenant suivi par
`qualification/maturity_evidence_0_2_1/contact_frictional_static.json`. La
preuve disponible est positive mais volontairement etroite : un cas de
glissement avec loi de Coulomb regularisee, compare a Code_Aster CONTINUE sur
les memes charges et les memes unites.

| Critere | Resultat | Interpretation |
| --- | --- | --- |
| Branche de glissement et limite de Coulomb | `PASS` | force tangentielle QF `50 N`, limite `50 N`, branche `slip` |
| Correlation deplacement Code_Aster | `PASS` | ecart tangentiel `0,607 %`, ecart normal `0,0500 %` |
| Residus et reponse finie | `PASS` | residu relatif nul dans le cas archive |
| Artefacts et tests | `PASS` | rapport, figure, manifeste, documentation et test presents |
| Diversite geometrique | `PASS_INTERNAL` | trois familles sont executees : double butee, rampe facettisee et deux esclaves TET4 |
| Trois niveaux par famille | `PASS_INTERNAL` | trois niveaux sont executes pour chaque famille; le resultat reste une preuve interne |
| Decision Owner specifique au frottement | `PENDING` | la revue existante concerne le contact sans frottement |

La campagne de diversite est maintenant archivee dans
`qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/`.
Les trois familles retournent une reponse finie, un gap maximal de
`9,159e-16 m`, un depassement maximal du cone de Coulomb de
`1,421e-14 N` et une branche
`slip` activee sur les familles a butee/rampe. Cette preuve elargit la
diversite geometrique et couvre trois niveaux par famille, mais elle ne
remplace pas une correlation externe de chaque famille.

La promotion `experimental` vers `owner_accepted` est donc
`BLOCKED_CRITERIA_FAILED` uniquement par `CONTACT-FRIC-C04`. Le
resultat est exploitable comme preuve de fonctionnement de la branche de
glissement, mais il ne doit pas etre extrapole au collage, au grand glissement,
au contact dynamique, a l'usure ou a la branche stick non correlee.

## Promotion du grand modele TET4 PETSc/MPI

Le perimetre `large-tet4-linear-static` est suivi par
`qualification/maturity_evidence_0_2_1/large_tet4_linear_static.json`. Il est
separe du chemin standard SciPy afin de conserver les exigences d'environnement,
de memoire, de partitionnement et de reproductibilite propres au calcul
distribue.

| Controle | Resultat | Limite ou decision |
| --- | --- | --- |
| Execution 100 k DDL | `PASS` | residu `1,824e-15` |
| Execution 1 M DDL | `PASS` | residu `5,220e-15`, environ `7,13 GB` cumules sur deux rangs |
| Execution 3 M DDL avec BAIJ | `PASS` | residu `8,997e-19` |
| Assemblage par blocs et MPI-IO | `PASS` | erreurs inter-rangs et A IJ/BAIJ sous `1e-10` |
| Comparaison GAMG / Hypre | `PASS` | GAMG conserve comme defaut mesure |
| Weak scaling a quatre rangs | `WARNING` | efficacite `41,6 %`, seuil provisoire `60 %` |
| Decision Owner grand modele | `PENDING` | aucune decision dediee archivee |

La gate est `BLOCKED_CRITERIA_FAILED` par `LARGE-TET4-C05`. Le scope peut
servir de preuve de capacite technique pour TET4 isotrope lineaire statique
dans l'environnement epingle, mais il ne constitue pas une garantie generale
de performance. Les resultats ne couvrent ni TET10, ni MITC4, ni le modal, ni
le transitoire, ni le non-lineaire en mode distribue.

## Promotions P1 restantes : MITC3, BEAM2 et discret

Les scopes P1 qui avaient des preuves dans le catalogue mais pas de criteres
atomiques sont maintenant rattaches a leurs sources actives.

| Scope | Criteres | Gate | Point restant |
| --- | --- | --- | --- |
| `mitc3-linear-static` | campagne, coques courbes, patch, Code_Aster et dossier : `PASS` | `READY_FOR_OWNER_REVIEW` | aucune anomalie bloquante dans le dossier actuel |
| `mitc3-modal` | invariants internes, six frequences Code_Aster et raffinement 8x2/16x4/24x6 : `PASS` | `READY_FOR_OWNER_REVIEW` | relire la preuve dediee avant toute promotion |
| `mitc3-transient-dynamic` | Newmark, energie, historique Code_Aster et raffinement 8x2/16x4/24x6 : `PASS` | `READY_FOR_OWNER_REVIEW` | relire la preuve dediee avant toute promotion |
| `mitc3-harmonic-response` | limite statique, reponse finie, sweep Code_Aster et raffinement 8x2/16x4/24x6 : `PASS` | `READY_FOR_OWNER_REVIEW` | relire la preuve dediee avant toute promotion |
| `mitc3-laminate-dynamic` | trois maillages Code_Aster, modal/Newmark/harmonique et residus : `PASS` | `BLOCKED_CRITERIA_FAILED` | `MITC3-LAM-DYN-C04`, decision Owner dediee |
| `beam2-linear-dynamics` | modal, Newmark, harmonique et correlation transverse : `PASS` | `READY_FOR_OWNER_REVIEW` | domaine borne sans dynamique non lineaire ni amortissement non proportionnel |
| `discrete-linear-dynamics` | oscillateur analytique et correlation DIS_T : `PASS` | `READY_FOR_OWNER_REVIEW` | domaine borne a un systeme spring-mass translationnel mono-DDL |

La demande technique de raffinement MITC3 est maintenant couverte par
`qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json`.
Les ecarts finaux sont de `0,673 %` en modal, `0,174 %` en Newmark et
`0,097 %` en harmonique, avec une variation de la premiere frequence QF de
`0,129 %` entre les deux derniers niveaux. La gate devient
`READY_FOR_OWNER_REVIEW`, car aucune preuve numerique ne doit promouvoir
automatiquement un scope vers `stable`.

## Promotion MITC4 stratifie statique

Le scope `mitc4-laminate-static` est maintenant rattache au suivi
`qualification/reviews/mitc4_laminate_static_followup_2026-07-26.json` et au
benchmark NAFEMS R0031/Code_Aster. Les recommandations de comparaison par pli,
d'orientation sur coque courbe et de correlation externe ont des artefacts
associes.

| Controle | Resultat |
| --- | --- |
| ABD, contraintes par pli et recommandations suivies | `PASS` |
| NAFEMS R0031 deplacement fin | `PASS`, erreur `0,458 %` |
| Increment de maillage QF / Code_Aster | `PASS`, `0,0967 %` / `0,0920 %` |
| Correlation Code_Aster et residu libre | `PASS`, residu maximal `1,013e-9` |
| Dossier, documentation et tests | `PASS` |

La promotion est `READY_FOR_OWNER_REVIEW`. La preuve ne couvre toujours pas
`S13` interlaminaire, delamination, dommage ou rupture progressive; elle ne
constitue pas non plus une qualification pli par pli generale pour des
assemblages non symetriques ou des directions obliques hors des cas archives.

## Promotion TET4 total-lagrangien

Le scope `tet4-total-lagrangian-structural-v2` est maintenant controle par
les criteres `TET4-TL-C01` a `TET4-TL-C04`. Les invariants de formulation, la
politique d'increments, la correlation Code_Aster, le flambement/post-flambement
et les tests sont presents.

| Controle | Resultat |
| --- | --- |
| Green-Lagrange, PK2, tangente et convergence | `PASS` |
| Politique d'increments | minimum `6`, recommande et defaut `10` |
| Patch PK2 Code_Aster | `PASS`, erreur `8,544e-5` |
| Branche imparfaite jusqu'a `0,8 Pcr` | `PASS`, ecart maximal `1,693e-9` |
| Revue independante avant qualification externe | `PENDING` |

La gate reste `BLOCKED_OWNER_REVIEW` par `TET4-TL-C04`. Le resultat est
compatible avec un usage interne de recherche borne, mais la self-review Owner
ne doit pas etre presentee comme une revue independante; pression suiveuse,
contact, plasticite en deformation finie, dommage et extrapolation des
contraintes aux singularites restent exclus.

## Promotion TET4 J2 materiau

La campagne structurelle TET4 J2 a ete executee et archivee dans
`qualification/maturity_evidence_0_2_1/tet4_j2_structural_campaign/`. Elle
contient 140 elements, 24 points de chemin de charge, inversion de chargement,
rechargement et controles de retour d'etat.

| Controle | Resultat |
| --- | --- |
| Chemin structurel cyclique | `PASS_INTERNAL` |
| Erreur de chemin constitutif | `5,020e-11` |
| Residu maximal par increment | `5,231e-10` |
| Retour plastique inverse et rechargement | `PASS` |
| Reference constitutive Code_Aster 18.1.0, image epinglee et manifeste | `PASS_EXTERNAL_CORRELATION` |
| Decision Owner TET4 J2 | `PENDING` |

La gate est `BLOCKED_CRITERIA_FAILED` avec la classification
`owner_decision_pending`, uniquement par `TET4-J2-C04`. La comparaison
Code_Aster est une preuve constitutive material-point reproductible; elle ne
constitue pas une correlation structurelle externe. Les grandes deformations,
le dommage, la plasticite anisotrope et le contact restent exclus.

## Promotion du contact statique borne

Le scope `contact-v1-linear-static-bounded` est maintenant structure dans le
registre de criteres. Cette structuration ne change pas son statut : la
decision existante reste `accepted_for_bounded_engineering_use` et la cible
est identique au statut courant.

| Controle | Resultat |
| --- | --- |
| Decision et condition de raffinement | `PASS`, 9 984 elements de confirmation, ecart Code_Aster sous 5 % |
| Dossier, empreintes et tests | `PASS` |
| Gate de promotion | `NO_PROMOTION_REQUIRED` |

Ce scope concerne le contact unilateral statique sans frottement, a petites
transformations, avec la topologie et la recherche de contact documentees. Il
ne couvre pas le frottement, le grand glissement, l'impact, l'usure ni un
contact surface-surface general. Le lot `contact-frictional-static` reste
separe et bloque par son manque de familles de cas et de decision Owner.

## Promotion MITC3 multicouche statique

Le scope `mitc3-laminate-static` est desormais visible dans l'audit, mais il
ne doit pas etre confondu avec le scope courbe deja accepte experimentalement
ni avec la campagne dynamique plane. Les briques CLT, contraintes par pli et
dynamique sont presentes; le ledger statique MITC3 dedie relie maintenant un
meme cas, trois maillages, quatre contraintes par pli et un oracle CalculiX.

| Critere | Etat | Action requise |
| --- | --- | --- |
| `MITC3-LAM-STAT-C01` | `PASS` | Ledger statique archive avec trois maillages, contraintes par pli et CalculiX S6 |
| `MITC3-LAM-STAT-C02` | `PASS` | Conserver le dossier analytique, ply-stress, documentation et tests existants |
| `MITC3-LAM-STAT-C03` | `PASS` | Deux familles de chargement archivees sur le panneau courbe; une seconde geometrie reste recommandee |

La preuve technique est complete, mais le gate reste `BLOCKED_OWNER_REVIEW`;
aucune maturite n'est modifiee automatiquement.
Cette sortie est une amélioration de traçabilité, pas une régression
numérique : le ledger statique est maintenant isolé et passe, mais la décision
Owner dédiée doit encore être enregistrée. Les exclusions restent `S13`,
délamination, dommage, rupture progressive et extrapolation aux stratifiés
non couverts.

## Etat de l'audit de promotion

La commande suivante régénère le rapport sans modifier la matrice de maturité :

```powershell
python .\qf_solver.py maturity-promotion --output .\results\maturity_promotion_0_2_1
```

Au 14 août 2026, le rapport compte 34 scopes, 34 chemins d'artefacts
intègres et 19 gates bloquées. Les blocages restants sont donc visibles et
actionnables : décisions Owner dédiées, raffinements MITC3 dynamiques,
seconde configuration grand modèle, audit indépendant TL, ledger MITC3
multicouche statique et référence constitutive J2 publiée. Aucune promotion
de maturité n'est automatique.
