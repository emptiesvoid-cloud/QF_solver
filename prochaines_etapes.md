# Prochaines etapes du solveur EF

## Lecture prioritaire - prepublication 0.2.1 alpha - 22 aout 2026

L'etat courant est defini par
`qualification/reviews/owner_review_scope_decisions_2026-08-22.json`,
`qualification/element_analysis_matrix.json` et le paquet detaille
`docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md` et
`docs/verification/owner_final_release_decision_0_2_1a0.md`. Les
paragraphes historiques ci-dessous sont conserves pour la tracabilite; ils ne
doivent pas ecraser une decision plus recente du registre Owner.

Le preflight de publication est techniquement propre : l'audit du lot public
est `PASS` (`1550` fichiers analyses, `0` finding) et l'architecture respecte
les regles de couches et de taille. La release n'est toutefois pas gelable :
`release-vv` controle les `28` scopes `stable`. Les `8` scopes bornes,
experimentaux ou `research` sont exclus du gate de stabilite, tout en restant
visibles dans le registre de maturite et la decision finale. La campagne de
release, la revalidation Owner finale et un checkout Git propre restent des
gates bloquants.

Avant tout tag ou push, suivre cet ordre strict :

1. ne modifier que les documents et correctifs necessaires au perimetre 0.2.1a0 ;
2. executer la campagne de release sur un checkout propre ;
3. reexecuter `release-vv`, les audits publics et le test d'installation ;
4. relire le paquet de cloture et enregistrer la decision Owner finale ;
5. aligner `CHANGELOG.md` et `CITATION.cff` sur le commit, le tag et la date
   de publication effectivement retenus ;
6. faire une revue manuelle de `git archive`, puis seulement creer commit et tag.

La dette structurelle non bloquante est suivie apres l'alpha : decoupage
progressif de `scripts/` et `solveur.verification`, retrait eventuel de la
facade interne `src/solveur/compat/mitc4` en 0.3.0, et refactoring preventif
des fichiers proches de 700 lignes. Aucun nouvel element ou solveur n'est
ajoute pour fermer cette alpha.

### Plan de nettoyage du worktree avant gel

Le worktree contient de nombreuses modifications historiques et artefacts de
campagnes. Avant le gel, sans suppression automatique :

1. inventorier chaque modification par lot fonctionnel (`runtime`, `tests`,
   `preuves`, `documentation`, `artefacts generes`) ;
2. faire relire les fichiers ambigus par l'Owner et isoler les artefacts hors
   depot lorsque leur conservation Git n'est pas justifiee ;
3. preparer un checkout propre sur une branche de release, puis y reappliquer
   uniquement les lots acceptes ;
4. rejouer package, campagne, release-VV et audit public sur ce checkout ;
5. ne creer commit et tag qu'apres la decision finale Owner.

## Pack de cloture 0.2.1 alpha avant audit Owner - 22 aout 2026

Le bilan de cloture et la liste des points restant a traiter sont regroupes
dans `docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md`.
La derniere tentative TET4 total-lagrangien a environ `1 152 000` elements est
archivee comme `RESOURCE_LIMIT_ABORTED`; elle ne donne ni PASS ni FAIL
mecanique. La fiche Owner a remplir est
`docs/verification/tet4_total_lagrangian_phase2_owner_review_2026-08-22.md`.

Avant tout push, il reste a :

1. revalider cette fiche en `research / more_evidence_required` ;
2. relire les 14 decisions Owner du 2026-08-22 sans modifier les preuves
   historiques ;
3. nettoyer le registre de maturite et les fiches `pending` ou `superseded` ;
4. relancer la suite complete, `release-vv` et l'audit de publication sur une
   revision Git propre ;
5. faire l'audit final du grand modele et de l'arbre public, puis seulement
   creer le commit, le tag et le push.

## Etat de la baseline

La prochaine alpha ciblee est `0.2.1a0`. Elle est consacree a la fermeture
progressive V&V, a la consolidation d'architecture et a l'audit de publication.
Elle ne modifie pas la baseline `0.2.0a0` deja publiee et n'ajoute aucun nouvel
element fini, solveur ou capacite mecanique.

### Regle d'acceptation prioritaire - toutes les erreurs d'ingenierie <= 1 %

**Objectif obligatoire pour la prochaine maturite : chaque erreur d'ingenierie
applicable doit etre inferieure ou egale a `1 %`.** Cette exigence s'applique
desormais a chaque element, methode, solveur et scope V&V avant toute promotion
vers `stable`. Elle ne constitue pas une moyenne de campagne : un seul
observable primaire au-dessus de `1 %` suffit a maintenir le scope ouvert.

A partir de cette etape, chaque scope doit respecter une limite d'erreur
relative inferieure ou egale a `1 %` pour **toutes ses grandeurs primaires
d'ingenierie** comparees a une reference definie. Cela couvre notamment le
deplacement, la frequence propre, la reponse harmonique, le RMS Newmark, les
reactions ou resultantes, l'energie, ainsi que les contraintes et deformations
evaluees hors singularite. Il ne suffit pas qu'une seule grandeur soit sous
le seuil : aucune grandeur primaire applicable au scope ne doit depasser
`1 %`. Toute valeur strictement superieure a `1 %` bloque la promotion vers
`stable` et laisse le scope ouvert.

Une exception ne peut etre examinee qu'avec une justification mecanique
formelle, un raffinement complementaire reproductible et une decision Owner
explicitement datee. Les residus, increments de maillage, erreurs de
quadrature et diagnostics de modele-forme restent suivis par leurs propres
seuils et ne doivent pas etre confondus avec cette erreur d'observable
principale.

En pratique, chaque nouvelle campagne devra donc fournir un tableau indiquant
pour chaque observable : la valeur QF_solver, la reference, l'erreur relative,
la limite `1 %` et le verdict. Les valeurs intermediaires superieures a `1 %`
restent archivees et signalees; elles ne peuvent pas etre masquees par le seul
resultat du maillage final. Les pics de contrainte situes exactement sur une
singularite restent hors de cette regle d'acceptation et doivent etre marques
comme informatifs, avec une observable de contrainte choisie hors singularite.

La promotion stable est donc conditionnee par un verdict conjoint : toutes
les erreurs primaires applicables sont `<= 1 %`, les criteres numeriques et de
convergence sont satisfaits, et la revue Owner est signee. Un statut `PASS`
sur un seul indicateur, ou un statut `PASS` technique obtenu avec une autre
limite, ne permet pas a lui seul de fermer le scope.

### Etat de durcissement au 21 aout 2026

### Decisions Owner enregistrees - promotion `stable`

La revue Owner du `2026-08-21` enregistre la promotion `stable` de `23`
sous-perimetres lineaires ou bornes dans leurs domaines explicitement documentes :
BEAM2 statique
et dynamique, systeme discret statique et dynamique, MITC3 isotrope classique,
MITC4 isotrope et stratifie plan regulier, TET4 isotrope et TET10 isotrope pour
les routes statique, modale, Newmark et harmonique applicables. La decision est
tracee dans `qualification/reviews/owner_stable_promotion_2026-08-21.json` et
dans le PDF `output/pdf/qf_solver_owner_decision_register_stable_0_2_1_20260821.pdf`.

La promotion est strictement bornee aux geometries, observables, maillages et
exclusions declares dans chaque dossier. Elle ne constitue ni une certification
externe ni une validation generale de l'element hors de ce domaine. Le TET4
statique est accepte sur le cas raffine sous `1 %`; son increment final de
maillage reste une recommandation de suivi non bloquante. Les ecarts spatiaux
externes conserves pour MITC4 Newmark et harmonique restent des diagnostics de
formulation, distincts des observables primaires d'acceptation temporelle.

Les paragraphes plus bas qui reprennent un statut experimental ou un gate
ouvert pour le MITC4 multicouche dynamique sont des traces historiques
anterieures a la decision du `2026-08-21`. L'etat courant est celui du registre
Owner et du dossier PDF de cloture.

Le paquet `mitc4-laminate-dynamic-refined-three-layups` est maintenant
enregistre `stable` pour les trois layups plans raffines, avec ses exclusions
associees. Les decisions du 22 aout ont aussi synchronise les sous-perimetres
suivants : `mitc3-laminate-dynamic-thin-planar`,
`mitc3-laminate-static-curved-mixed-transverse`,
`orthotropic-solid-tet4-tet10`, `orthotropic-solid-modal` et
`orthotropic-solid-transient-dynamic` sont `stable` dans leur domaine borne.

Les decisions appliquees mais non promues vers `stable` sont :
`mitc3-laminate-static`, `mitc3-laminate-dynamic`,
`mitc3-laminate-static-curved`, `tet4-material-nonlinear`,
`tet10-material-nonlinear`, `contact-v1-linear-static-bounded`,
`contact-frictional-static` et `large-tet4-linear-static`, tous en usage
engineering borne. `tet4-total-lagrangian-structural-v2` reste
`research / more_evidence_required`. MITC4 orthotrope courbe reste hors
acceptance et ne porte aucune decision de promotion.

La source de verite courante est le registre
`qualification/reviews/owner_review_scope_decisions_2026-08-22.json` et son
PDF detaille
`output/pdf/qf_solver_0_2_1_alpha_closure_owner_review_2026-08-22.pdf`.
Le registre detaille du 21 aout et les tableaux qui suivent conservent une
photographie historique de la campagne precedente; ils ne doivent pas etre
lus comme l'etat courant lorsqu'une decision du 22 aout la remplace.

La matrice `qualification/maturity_criteria_0_2_1.json` applique maintenant
la limite de `1 %` aux erreurs et differences relatives utilisees comme
criteres de promotion. L'instantane d'audit v14 ci-dessous a ete produit avant
la cloture Owner MITC4 multicouche dynamique et conserve une valeur historique.
Il est conserve pour la tracabilite et ne constitue pas le registre courant.
L'audit v14 couvre `37` scopes : `23` ont une cible
`stable`, les chemins sont valides `37/37`, `2` scopes restent bloques par des
criteres techniques et `4` attendent une decision ou une relecture Owner.
Les deux sous-perimetres supplementaires sont techniquement prets mais
attendent encore une Owner Review datee : MITC3 dynamique mince plan et MITC3
courbe sous chargements mixte/transverse.

| Scope | Motif principal | Action avant `stable` |
| --- | --- | --- |
| `mitc3-laminate-dynamic` | diagnostic 64x16 : 2,687 % modal / 10,412 % Newmark / 6,083 % harmonique | qualifier la différence de formulation DST/MITC3 ou définir un domaine analytique comparable |
| `mitc3-laminate-static-curved` | contrat matériau corrigé; corrélations à 64x32 sous 1 %, mais l'axial remonte à 1,570 % à 128x64 | analyser le désaccord axial de formulation et obtenir la décision Owner |
| `tet4-total-lagrangian-structural-v2` | revue independante non signee | obtenir la revue avant fermeture du gate |

Les sous-perimetres encore prets pour decision sont suivis separement :

| Sous-perimetre | Resultat technique | Action |
| --- | --- | --- |
| `mitc3-laminate-dynamic-thin-planar` | modal `0,3940 %`, Newmark `0,1968 %`, harmonique `0,0880 %` | Owner Review cible `stable` |
| `mitc3-laminate-static-curved-mixed-transverse` | mixte `0,5780 %`, transverse `0,4975 %`, increments sous `5 %` | Owner Review cible `stable` |

Le sous-perimetre MITC4 multicouche statique plan regulier est maintenant
techniquement PASS : membrane, flexion et chargement combine disposent de
trois niveaux de maillage et d'erreurs principales inferieures a `1 %`, avec
correlations NAFEMS/Code_Aster egalement inferieures a `1 %`. Le dossier
`docs/verification/mitc4_laminate_static_planar_stable_owner_review.md` porte
maintenant la decision Owner `stable` pour ce sous-perimetre. Le probe courbe oblique a `2,043 %` reste
documente comme optionnel et ne bloque plus ce sous-perimetre explicitement
  borne.

### Etude groupee MITC4 vers `stable` - isotrope, multicouche et orthotrope

Une etude consolidee est maintenant ouverte dans
`qualification/studies/mitc4_stable_package_2026-08-21/study.json`, avec sa page
de lecture dans `docs/verification/mitc4_stable_package/README.md` et sa
matrice dans `docs/verification/mitc4_stable_package/campaign_matrix.md`.
L'objectif est de traiter MITC4 comme une famille coherente tout en gardant
trois decisions de maturite independantes :

| Sous-scope | Etat actuel | Cible | Action principale |
| --- | --- | --- | --- |
| `mitc4-isotropic` | `stable` | `stable` | conserver les campagnes comme non-regression |
| `mitc4-laminate` | stable borne statique et dynamique sur trois layups | `stable` | conserver les exclusions S13/S23, dommage, rupture et delamination |
| `mitc4-orthotropic-homogeneous-ply` | `stable` | `stable` | conserver les exclusions et traiter la corrélation harmonique courbe 32x16 dans une campagne ultérieure |

Le terme orthotrope est volontairement borne : le noyau actuel le represente
par une lamelle unique dans `shell_laminate`. Cette etude ne revendique pas
encore un type `shell_orthotropic` autonome, ni une qualification de composite
pli par pli. Les solides orthotropes TET4/TET10 ne peuvent pas servir de preuve
directe pour MITC4.

Les quatre methodes obligatoires pour le paquet sont la statique lineaire, le
modal, Newmark et l'harmonique. Chaque sous-scope doit publier les memes
observables : maillage et deforme, axes materiau, deplacements, contraintes,
frequences, amplitude/phase, residus, energie et convergence. La promotion
stable exige une erreur primaire `<= 1 %` lorsque la reference est definie,
les seuils numeriques applicables, une correlation externe tracee et une
Owner Review distincte. Aucune promotion de groupe ne sera automatique.

#### Decoupage d'execution

1. Rejouer l'isotrope et figer le paquet de non-regression.
2. Fermer la campagne multicouche sur les trois layups documentes et verifier
   ABD, contraintes par pli, masse et reponses dynamiques.
3. Creer les cas orthotropes a un pli pour 0, 45 et 90 degres, puis verifier
   l'invariance par rotation du repere global.
4. Ajouter la plaque plane puis le panneau courbe facettise pour l'orthotrope.
5. Comparer chaque cas a la theorie applicable et a Code_Aster; utiliser
   CalculiX comme correlation secondaire lorsqu'un element comparable est
   disponible.
6. Generer les rapports, figures, tableaux et manifestes, puis soumettre les
   trois sous-scopes a une Owner Review separee.

Les exclusions restent explicites : S13/S23 comme observables primaires,
dommage, rupture, delamination, grandes deformations et orientation continue
de fibres dans une surface courbe. Tant que la campagne orthotrope n'est pas
executee, son statut reste `candidate`; aucune reutilisation automatique de la
decision orthotrope solide n'est permise.

La question du pas de temps MITC3+ est maintenant isolee : la campagne interne
`VNV-MITC3-LAMINATE-TEMPORAL-REFINEMENT-001` utilise `80`, `160` et `320` pas
par periode. L'erreur RMS passe de `0,2623 %` a `0,0164 %`, avec un ordre
observe proche de deux, une derive energetique inferieure a `2,3e-12` et des
residus inferieurs a `2,3e-12`. Le pas de temps n'est donc plus une cause
credible de l'ecart externe; la comparaison DST/MITC3 reste ouverte comme
probleme d'operateur et de reference, sans promotion stable automatique.

Une campagne Code_Aster complementaire a ete executee sur un maillage spatial
fixe `12x3` a `80`, `160` et `320` pas par periode. Les ecarts restent
`3,9573 %` en modal, `2,3231--2,3247 %` en Newmark et `1,3410 %` en harmonique.
Le diagnostic externe est donc **PASS_DIAGNOSTIC**, mais son gate `stable` reste
**BLOQUE_OVER_1_PERCENT** : le raffinement temporel ne resout pas l'ecart de
formulation DST/MITC3. Les artefacts sont dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_temporal_refinement_2026-08-21/reference/`.

Un audit elementaire de masse a egalement ete ferme par quadrature Duffy
independante : difference condensee `1,1803e-5`, bilan translationnel
`1,8623e-15`, masse semi-definie positive et drilling nodal nul. Cette preuve
ecarte une erreur dominante de quadrature de masse, mais ne constitue pas une
identite de formulation avec DST. Le dossier est dans
`qualification/vnv/mitc3_mass_quadrature_audit_2026-08-21/`.

La chaine algébrique de condensation a ensuite été vérifiée séparément sur un
triangle stratifié : les opérateurs `K` et `M` développés `20x20` reproduisent
les matrices publiques condensées `18x18` à `1,11e-18` et `0` d'écart relatif,
avec résidu de stationnarité `1,13e-19`, symétrie et masse sans drilling. Cette
preuve ferme la cohérence interne `K/M -> condensation`; elle ne ferme pas la
différence de formulation externe MITC3/DST. Les artefacts sont dans
`qualification/vnv/mitc3_matrix_condensation_audit_2026-08-21/`.

La quadrature de rigidité a également été recalculée par Duffy
Gauss-Legendre d'ordre 12. L'écart relatif maximal entre la règle Dunavant à
sept points et l'intégration indépendante est `4,28e-15` par composante et
`1,98e-15` sur l'opérateur total, y compris après condensation. Le critère
`MITC3-LAM-DYN-C11` est PASS dans l'audit v14. Cette preuve ferme l'intégration
numérique de `K`, mais ne remplace pas une référence externe de même ordre.
Les artefacts sont dans
`qualification/vnv/mitc3_stiffness_quadrature_audit_2026-08-21/`.

La chaîne matériau stratifiée a ensuite été comparée à une intégration
indépendante de Gauss-Legendre dans l'épaisseur. Les matrices `A`, `B` et `D`,
la masse surfacique, l'inertie de rotation et la projection d'orientation
passent à mieux que `1e-12`, avec une tolérance absolue `1e-9` pour le
couplage `B` nul par annulation symétrique. Le critère
`MITC3-LAM-DYN-C12` est PASS dans l'audit v14. Cette preuve ferme la chaîne
constitutive mais ne remplace pas une corrélation externe de même formulation.
Les artefacts sont dans
`qualification/vnv/mitc3_laminate_abd_audit_2026-08-21/`.

Une reference Code_Aster `DKT` a ensuite ete ajoutee pour le sous-perimetre des
stratifies plans minces. Sur `12x3`, `16x4` et `24x6`, le dernier niveau atteint
`0,3940 %` modal, `0,1968 %` Newmark et `0,0880 %` harmonique. Ce sous-perimetre
est candidat au passage vers `stable`, mais demande encore une Owner Review
dediee et ne doit pas etre extrapole aux coques epaisses ou courbes. Les preuves
sont dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/`.

Le scope machine-readable est
`mitc3-laminate-dynamic-thin-planar`. Son gate est
`BLOCKED_OWNER_REVIEW`, sans échec technique. Le dossier de décision est
`docs/verification/mitc3_laminate_dynamic_dkt_thin_owner_review.md` et le
registre est `qualification/reviews/mitc3_laminate_dynamic_dkt_thin_owner_review_pending.json`.

Le chargement axial de la coque courbe reste volontairement séparé. Les
chargements mixte et transverse satisfont le seuil de `1 %` et l'incrément de
maillage de `5 %`; ils sont suivis sous
`mitc3-laminate-static-curved-mixed-transverse`. Le chargement axial reste
exclu car son désaccord augmente au raffinement et les deux références
externes ne sont pas comparables. Le dossier de décision est
`docs/verification/mitc3_laminate_curved_mixed_transverse_stable_owner_review.md`.

### ST-02 - Diagnostic TET4 statique et objectif de 1 %

- [x] Corréler QF_solver et Code_Aster `TETRA4` sur le même maillage : l'écart
  maximal est `2,08e-10 %`, ce qui écarte une divergence d'implémentation.
  La preuve est archivée sous
  `qualification/vnv/external/code_aster_tet4_static/reference/`.
- [x] Mesurer une convergence structurée TET4 en flexion : avec le motif
  centré et le chargement de face cohérent, l'erreur de flèche décroît de
  `11,711981 %` à `1,217644 %` entre `24 576` et `3 072 000` éléments, avec
  un résidu PETSc relatif de `1,37e-16` au dernier niveau.
- [x] Auditer puis corriger la sensibilité du cas à la topologie et au
  chargement de maillage : le runner accepte le motif historique à six TET4
  et le motif centré à douze TET4 par cellule. `surface_consistent` intègre
  désormais la traction avec les fonctions de forme bilinéaires de la face,
  sans biais de diagonale. La preuve corrigée est archivée sous
  `qualification/vnv/tet4_structured_petsc_corrected_002/reference/`.
- [x] Poursuivre le raffinement et ajouter une corrélation 3D de même ordre
  pour fermer le seuil `<= 1 %`. Le niveau Docker factor `80` atteint
  `0,818328 %` sur `24 576 000` TET4 et `12 462 243` DDL, avec un résidu
  `2,09e-16`. Le motif centré reste un outil de diagnostic et ne constitue
  pas une nouvelle formulation ni une promotion automatique du TET4.
- [x] Construire la fabrique et le runner de maillages TET4 imbriqués :
  `generate_large_tet4_cantilever` et
  `scripts/run_tet4_structured_convergence.py` produisent les niveaux
  `1, 2, 4, 8` avec charge transverse tributaire et métriques d'ordre h.
- [x] Exécuter une preuve grand modèle PETSc/MPI avec `CG+GAMG` et télémétrie.
  Le niveau reproductible contient `3 072 000` TET4, `1 579 923` DDL, `219`
  itérations et un résidu relatif de `1,37e-16`; l'écart de flèche par
  rapport à la référence de poutre est `1,217644 %`. Le niveau est archivé
  sous `qualification/vnv/tet4_structured_petsc_refined_003/` avec manifeste.
- [x] Comparer la séquence à une référence 3D interne TET10 conforme. À
  `12 288` TET4, le TET10 atteint `0,8277 %` face à la référence poutre, avec
  un résidu `1,19e-10`. Les artefacts sont archivés sous
  `qualification/vnv/tet4_tet10_3d_reference_001/`.
- [x] Refaire le probe 3D avec le motif centré et le chargement
  `surface_consistent` identiques à la campagne corrigée. À `24 576` TET4,
  l'écart TET4/TET10 est `11,009264 %`, tandis que TET10 est à `0,789652 %`
  de la référence poutre. Le probe confirme que l'écart est d'interpolation
  TET4 en flexion ; il reste interne et ne remplace pas Code_Aster TETRA10.
  Artefacts : `qualification/vnv/tet4_tet10_corrected_reference_002/`.
- [x] Structurer l'audit causal TET4 dans
  `qualification/vnv/tet4_static_causal_audit_2026-08-21.json`, avec le gate
  `STABLE-1PCT-POLICY`, les causes établies et les preuves associées.
- [x] Rejouer la preuve dans l'image Docker large épinglée : `h5py 3.13.0`,
  `petsc4py 3.25.1` et `mpi4py 4.1.2` sont tracés dans le manifeste, avec
  l'image `qf-solver-large:vnv-20260821` et son digest.
- [x] Ajouter un niveau PETSc au-delà de `3 072 000` TET4 et vérifier le seuil
  avec le runtime Docker épinglé. Le niveau `24 576 000` atteint `0,818328 %`,
  `252` itérations et `2,09e-16` de résidu. L'exécution a duré `830,82 s`
  avec environ `986 MiB` d'opérateur ; cette preuve est destinée à la revue,
  pas à la CI courante.
- [x] Executer une première correlation Code_Aster `TETRA10` sur maillage
  identique au niveau intermediaire. Elle est archivee sous
  `qualification/vnv/external/code_aster_tet10_static_reference_001/` :
  QF_solver TET10/TETRA10 `3,87208e-09 %`, mais TET4/TETRA10 `32,296413 %`
  au niveau `3 072` TET4.
- [x] Étendre la comparaison au niveau final avec Code_Aster `TETRA4` sur
  maillage identique : l'écart de déplacement fin est `8,05e-13`, et les
  résultats restent finis. Cette corrélation de même ordre est l'oracle
  primaire de l'opérateur TET4 ; le TET10/TETRA10 reste un diagnostic
  d'interpolation et ne doit pas être utilisé comme critère de rejet du TET4.
- [ ] Obtenir la décision Owner pour le scope TET4 statique. Les critères
  techniques sont maintenant `PASS` et le gate est `READY_FOR_OWNER_REVIEW`,
  mais aucune promotion `stable` n'est automatique.

**Conclusion causale TET4.** Le cas est statique : il n'y a ni pas de temps ni
intégrateur Newmark. L'écart initial provenait principalement de la
discrétisation de la flexion et de la distribution discrète de la charge sur
la face terminale. Le motif centré et le chargement `surface_consistent`
réduisent l'écart de `11,711981 %` à `0,818328 %`. Le résidu PETSc étant déjà
de l'ordre de `10^-16`, augmenter les itérations ne corrigerait pas la flèche.
La preuve sous `1 %` est donc une preuve de raffinement spatial et de
cohérence de chargement, non une preuve temporelle. Le scope reste limité aux
cas statiques linéaires et attend la revue Owner avant une maturité `stable`.

Un audit causal multi-scope a ete ajoute dans
`qualification/vnv/tet4_error_audit_2026-08-21/`. Il confirme que le deficit
statique vient principalement de l'interpolation lineaire a deformation
constante du TET4 : ni le pas de temps, ni le solveur lineaire, ni une
divergence QF_solver/Code_Aster TETRA4 n'expliquent l'ecart. Le porte-a-faux
fin atteint `0,818328 %`; les comparaisons TET4 dynamiques restent aussi sous
`1 %`. L'increment final de maillage externe reste toutefois `4,643 %`, donc
la preuve est suffisante pour le sous-perimetre documente mais pas pour une
promotion generale sans une geometrie ou un chargement supplementaire.

Le rapport lisible est
`docs/verification/tet4_error_causal_audit_2026-08-21.md`; la generation est
reproductible avec `python .\\scripts\\run_tet4_error_audit.py`. Le critere
machine-readable associe est `TET4-LS-C10`.

### ST-03 - Préparation de promotion TET4 modal/Newmark/harmonique

- [x] Vérifier les invariants analytiques internes : résidu modal
  `1,78e-16`, orthogonalités masse/raideur nulles, dérive énergétique Newmark
  `1,41e-13` et limite statique harmonique nulle.
- [x] Corréler les trois routes sur un même maillage Code_Aster TETRA4 :
  erreurs maximales `2,74e-11` en modal, `6,38e-13` en Newmark et
  `6,98e-13` en harmonique.
- [x] Ajouter une géométrie rectangulaire épaisse et une géométrie circulaire.
  Les erreurs externes maximales restent respectivement de l'ordre de
  `1e-13` et `1e-12` pour les trois routes.
- [ ] Obtenir la décision Owner datée sur le domaine strictement déclaré :
  isotrope, petits déplacements, sans amortissement calibré, sans contact et
  sans non-linéarité. Les preuves techniques sont prêtes, mais la maturité
  ne change pas automatiquement.

### ST-04 - Préparation de promotion TET10 isotrope

- [x] Vérifier la formulation et la géométrie : quadrature Hammer sur les
  tétraèdres droits, quadrature Duffy positive sur les géométries courbes,
  contrôle du Jacobien et rejet des éléments inversés.
- [x] Vérifier les familles statiques traction, flexion et torsion. Le niveau
  TET10 fin documente `0,9927 %` en flexion et `0,9908 %` sur la contrainte de
  torsion, avec résidus libres sous `1,1e-10`.
- [x] Corréler un maillage courbe identique avec CalculiX C3D10 : écarts de
  déplacement `6,84e-5` et de torsion `6,45e-5`.
- [x] Corréler modal, Newmark et harmonique avec Code_Aster TETRA10 sur même
  maillage, mêmes pas de temps et mêmes fréquences. Les écarts maximaux sont
  `7,60e-12` en modal, `5,78e-12` en Newmark et `6,19e-12` en harmonique.
- [x] Vérifier le raffinement temporel Newmark sur quatre niveaux (`T/30` à
  `T/240`) ; l'incrément final est `0,4721 %`.
- [ ] Obtenir la décision Owner sur le domaine borné : élasticité isotrope,
  petites déformations, géométries droites ou courbes admissibles, masse
  cohérente et amortissement de Rayleigh déclaré. Les grandes transformations,
  plasticité courbe, contact et singularités de contrainte restent exclues.

Le diagnostic complet est disponible dans
`docs/verification/tet4_static_causal_audit_2026-08-21.md`. Il conclut que le
TET4 à déformation constante converge lentement en flexion ; le TET10 reste
le choix recommandé pour les modèles dominés par la flexion tant que le seuil
physique TET4 `< 1 %` n'est pas démontré.

Le raffinement MITC3 avec contrat matériau unique réduit les écarts externes
à `0,609 %` (mixte), `0,528 %` (transverse) et `0,907 %` (axiale) à `64x32`.
Les deux premières familles respectent l'incrément de `5 %`; l'axial reste
au-dessus avec `8,262 %`. La corrélation principale est donc sous `1 %`, sans
fermer le critère de convergence requis pour `stable`.

La campagne corrigée est archivée dans
`qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_033`
et le raffinement axial dans `...material_fix_034_axial`. Celui-ci réduit les
incréments à `3,17 %` côté QF_solver et `2,74 %` côté Code_Aster, mais l'écart
externe remonte à `1,336 %` puis `1,570 %` sur `96x48` et `128x64`. Cette preuve
négative confirme que le désaccord axial n'est pas un simple effet de maillage;
le scope reste bloqué par la règle d'erreur à `1 %`.

La campagne dynamique MITC3 étendue jusqu'au niveau `48x12` ne confirme pas
cette tendance : les écarts fins atteignent `2,4476 %` en modal, `9,3150 %`
en Newmark et `5,4589 %` en harmonique, malgré des résidus internes faibles
(`3,205e-8` modal et `4,025e-10` dynamique). Le résultat est conservé comme
preuve négative utile : augmenter le maillage seul ne suffit pas et la
différence DST/MITC3 doit être traitée avant `stable`.

Deux contrôles de protocole ont ensuite été fermés. Le deck Code_Aster fixe
explicitement `A_CIS=5/6`, puis applique la même distribution trapézoïdale des
forces de pointe que QF_solver sur les groupes `TIP_####`. Sur `8x2`, `12x3`
et `16x4`, les écarts fins restent `2,5016 %` en modal, `3,4004 %` en Newmark
et `1,9957 %` en harmonique. Ces campagnes négatives excluent donc le facteur
de cisaillement implicite et la distribution nodale comme causes suffisantes;
elles renforcent le diagnostic d'une différence de formulation ou de
référence. Les preuves sont archivées dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_a_cis_035` et
`...code_aster_mitc3_laminate_dynamic_load_fix_036`.

Un diagnostic de raffinement massif `64x16` (`2048` triangles) a ensuite été
exécuté. Les erreurs maximales obtenues sont `2,687 %` en modal, `10,412 %`
en Newmark et `6,083 %` en harmonique, avec des résidus QF de `4,883e-8` et
`8,021e-10`. Le résultat répond à la question du raffinement : multiplier
fortement le maillage ne garantit pas un passage sous `1 %` et ne constitue
pas une correction de formulation. Le dossier est archivé dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037`;
le scope reste bloqué jusqu'à une comparaison de formulation/matrice de masse
ou à une définition plus étroite et justifiée de l'observable dynamique.

La campagne MITC4 multicouche dynamique a été étendue aux trois empilements
sur `24x6`, `36x9` et `48x12`. Au niveau final, les erreurs maximales sont
`0,379 %` en modal, `0,484 %` en Newmark et `0,261 %` en harmonique, avec un
résidu modal maximal de `7,409e-8`. Le niveau intermédiaire reste conservé :
l'angle-ply atteint `2,938 %` en Newmark et `1,606 %` en harmonique à `36x9`.
Le critère technique à `1 %` est maintenant PASS, sans effacer les niveaux
qui dépassent le seuil. Le scope est prêt pour une Owner Review ciblant
`stable`; la preuve complète est dans
`docs/verification/mitc4_laminate_dynamic_extended_owner_review.md`.

Le raffinement MITC4 multicouche statique courbe atteint six niveaux, mais
conserve un écart de forme de `2,043 %` alors que les increments de maillage
sont déjà inférieurs à `1 %`. Ce plateau est traité comme une différence de
modèle entre la coque facettisée bilinéaire et l'oracle courbe quadratique,
pas comme un simple manque de mailles. Une promotion stable exige donc un
oracle courbe de même ordre, une référence analytique adaptée ou une
séparation explicite du sous-périmètre plan et du sous-périmètre courbe.

Le TET10 J2 structurel dispose maintenant d'une campagne de raffinement dédiée
sur l'equerre re-entrante : trois niveaux identiques `457 -> 911 -> 2217`
elements, avec un PEEQ RMS final de `0,8867 %` et un residu maximal de
`4,666e-11`. Le gate technique `<= 1 %` est donc PASS pour ce cas. Le scope
reste toutefois soumis a une Owner Review dédiée avant toute promotion vers
`stable`; les limites de la plasticite J2 a petites deformations restent
inchangées.

L'orthotropie statique dispose désormais d'une preuve TET4 vectorisée large
sur onze niveaux, jusqu'à `564 525` éléments (`h=0,020 m`). Le dernier niveau
atteint `0,8772 %` d'erreur de déplacement et `0,8647 %` d'énergie, avec un
résidu libre `9,96e-9`; le gate technique `<= 1 %` est PASS. Le backend,
les `2 510` itérations CG, le résumé compact, le maillage et le manifeste
sont archivés dans
`qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/`.
Les anciennes campagnes à `1,329 %` / `1,448 %` restent conservées comme
preuves historiques de progression. La promotion du scope attend encore une
Owner review explicite et ne vaut pas validation dynamique ou composite.

## P-VV-021 - Consolidation V&V de QF_solver 0.2.1a0

Objectif : ne pas publier `0.2.1a0` tant que chaque combinaison element /
methode incluse dans la matrice de qualification ne dispose pas d'une preuve
complete, reproductible et relue par Owner.

- [x] creer `qualification/release_vv_0_2_1.json` avec baseline, scopes,
  exclusions et politique de verdict ;
- [x] ajouter l'API `run_release_vv()` et la commande `release-vv` ;
- [x] produire un resume JSON, un rapport Markdown et un manifeste SHA-256 ;
- [x] controler que le tag `v0.2.0-alpha` pointe toujours vers le commit de
  baseline immuable ;
- [x] separer `PASS`, `WARNING` et `FAIL` pour ne pas confondre calcul passe
  et preuve de qualification ;
- [x] appliquer la regle commune `STABLE-1PCT-POLICY` : aucune promotion
  `stable` sans **toutes** les erreurs d'observables primaires applicables
  `<= 1 %` ;
- [ ] completer les preuves de chaque ligne de `qualification/element_analysis_matrix.json` ;
- [ ] executer la campagne complete, y compris les campagnes Docker externes, et analyser chaque cas ;
- [ ] remplir l'Owner review du registre, fermer les anomalies et lancer le gate final ;
- [ ] geler `v0.2.1a0` seulement apres un gate `PASS`, une revue Owner finale
  et un audit de l'archive ;
- [ ] pousser uniquement apres accord explicite du proprietaire.

Etat technique ajoute le 2026-08-14 :

- [x] la campagne interne `linear_dynamic_families` passe pour `TET4`, `TET10`,
  `MITC3`, `BEAM2` et `SPRING_MASS` ; chaque famille produit un resume, un
  rapport Markdown et un manifeste V&V ;
- [x] le rapport `release-vv` distingue maintenant les causes d'ouverture :
  `maturity_not_stable`, `evidence_missing`, `external_reference_missing`,
  `campaign_not_green`, `owner_review_pending` et `source_dirty` ;
- [x] les cas de campagne dont les calculs et controles numeriques passent,
  mais dont le statut de qualification reste `WARNING`, sont identifies comme
  `calculation_checks_passed_but_qualification_policy_blocks` ;
- [x] executer les correlations Code_Aster avec l'image epinglee lorsque le
  daemon Docker est disponible ; le lot du 2026-08-14 est archive dans
  `docs/verification/code_aster_correlation_campaign_2026-08-14.md` et les
  preuves locales sont sous `tmp/code_aster/` ;
- [x] generer un index suivi des preuves et de leurs SHA-256 dans
  `qualification/external_reference_digests/code_aster_correlation_campaign_2026-08-14.json` ;
- [x] empaqueter les preuves Code_Aster dans
  `qualification/evidence/code_aster_correlation_campaign_2026-08-14/` en
  excluant les fichiers de travail lourds : le manifeste v2 contient `234`
  fichiers controles, et `verify-evidence` retourne `PASS` ;
- [x] raccorder ce bundle au registre `release_vv_0_2_1.json` : le controle
  `EVIDENCE-BUNDLE-CODE-ASTER-CORRELATION-2026-08-14` est `PASS` avec `0`
  erreur d'integrite. Le controle ne prejuge ni de la maturite mecanique ni
  de la decision Owner ;
- [x] archiver aussi la campagne interne par familles dans
  `qualification/evidence/linear_dynamic_families_2026-08-14/` : les cinq
  familles `TET4`, `TET10`, `MITC3`, `BEAM2` et `SPRING_MASS` sont `PASS`, le
  bundle contient `11` fichiers controles et son controle d'integrite est
  `PASS`. Les manifestes bruts contenant des chemins de poste ne sont pas
  recopies ; la maturite et la decision Owner restent distinctes ;
- [x] corriger la fuite numerique d'inertie du drilling sur les coques
  facettisees courbes : le seuil relatif par defaut est `1e-10`, la masse
  elementaire reste sans inertie de drilling et la condensation est tracee
  dans les diagnostics ;
- [x] relancer TET4 dynamique avec `h=0,30` : la frequence modale passe a un
  increment final de `0,083 %`, le critere statique a `4,87 %` et la
  correlation meme-maillage reste sous `3e-12` ;
- [ ] faire relire par Owner les ecarts et les limites de chaque correlation
  avant toute promotion de maturite ; le resultat Code_Aster ne vaut pas, a
  lui seul, une qualification ;
- [x] archiver les artefacts V&V controles dans un paquet de preuve suivi :
  le bundle Code_Aster est verifie et preserve ; les dossiers de travail
  `qualification/vnv`, `results` et `tmp` restent ignores par Git et ne
  ferment pas la tracabilite a eux seuls ;
- [x] effectuer le lot de verification interne par familles : `TET4`, `TET10`,
  `MITC3`, `BEAM2` et `SPRING_MASS` retournent `PASS` avec
  `run_linear_dynamic_vnv.py --family all`; chaque famille produit son resume,
  son rapport Markdown et son manifeste V&V ;
- [ ] apres revue des rapports et des ecarts, relancer la campagne complete ;
- [ ] renseigner une decision Owner datee et laisser la gate finale echouer
  tant que cette decision n'est pas fournie.

Commande de preparation :

```powershell
python .\qf_solver.py release-vv --output .\results\release_vv_0_2_1
```

Le statut attendu pendant le developpement est `FAIL` ou `WARNING`. Le statut
`PASS` est reserve au moment ou toutes les lignes incluses de la matrice sont
`stable`, toutes les preuves requises sont presentes, les campagnes externes
sont executees et la revue Owner est enregistree.

Le gate applique une politique exhaustive aux lignes incluses : elles sont
ajoutees au pack meme si elles ne sont pas encore declarees dans le registre.
Les lignes `unsupported` sont ignorees uniquement parce que le registre de
release les declare explicitement hors perimetre. Toute ligne incluse
`experimental`, `research`, `verified_development` ou
`owner_accepted_experimental` ne peut pas satisfaire la cible `stable`. Une
fonctionnalite non implementee reste `unsupported` et doit rester declaree
hors perimetre avant le gel.

## P-REL-021 - Stabilisation 0.2.1a0 sans nouvelle fonctionnalite

Objectif : etendre les preuves des domaines deja implementes, rendre leur
statut de maturite lisible et remettre l'arborescence en ordre avant toute
nouvelle famille d'elements. Cette phase ne cree ni nouvel element, ni nouveau
solveur, ni nouveau format de modele.

### P-REL-021.1 - Rapatriement controle de MITC4 dans les coques

Constat : le paquet historique `src/solveur/compat/mitc4/` coexiste avec
`src/solveur/elements/shell/mitc4.py`. Cette double localisation rend
l'architecture et les responsabilites moins lisibles.

- [x] etablir l'inventaire des imports, commandes, benchmarks, tests et
  documents qui dependent encore de `src/solveur/compat/mitc4/` ; il est trace dans
  `docs/verification/mitc4_migration_inventory.md` ;
- [x] figer une baseline numerique MITC4 avant migration dans
  `qualification/baselines/mitc4_migration_baseline_2026-08-14.json` et le
  test associe. Le lot cible de `61` tests et la verification rapide sont
  `PASS` ; les campagnes longues Cook, Scordelis-Lo, cisaillement, modal,
  Newmark et harmonique restent des gates obligatoires de fin de migration ;
- [x] definir `src/solveur/elements/shell/mitc4/` comme localisation canonique
  de la formulation MITC4, de ses reperes, de son maillage et de son modele.
  Le post-traitement, les benchmarks et les outils de verification sont dans
  `solveur.post` et `solveur.verification`, conformement a leurs
  responsabilites ;
- [x] decouper proprement le fichier historique `shell/mitc4.py` en modules courts
  sous ce paquet, sans depasser 700 lignes et sans melanger CLI, I/O ou V&V ;
- [x] migrer le code historique par etapes et conserver `src/solveur/compat/mitc4/` comme
  facade de compatibilite depreciee pendant toute la serie `0.2.x` ;
- [x] ajouter des tests d'equivalence d'import et de resultat entre les anciens
  chemins et les chemins canoniques ; la campagne cible a valide `107` tests,
  avec `12` exclusions explicites pour dependances/campagnes non actives ;
- [x] migrer les helpers de maillage, modele, visualisation, benchmarks,
  convergence, locking et verification vers leurs modules canoniques ; les
  modules `src/solveur/compat/mitc4/` correspondants sont des facades de compatibilite ;
- [ ] ne retirer la facade historique qu'apres une release majeure, une fois la
  compatibilite publique explicitement terminee.

Critere de sortie atteint pour la migration de noyau : un seul noyau MITC4 fait
autorite sous `solveur.elements.shell`, les anciens imports restent
fonctionnels avec un avertissement de depreciation, et les campagnes MITC4
selectionnees ne changent pas. Le retrait de la facade reste volontairement
hors de la serie `0.2.x`.

### P-REL-021.2 - Extension des domaines deja bornes

La cible de `0.2.1a0` est de transformer les preuves ponctuelles en domaines
mieux caracterises, sans reetiqueter une fonctionnalite par simple intention.
Le vocabulaire de maturite est fige ainsi :

| Statut | Sens | Passage au statut suivant |
| --- | --- | --- |
| `experimental` | comportement implemente et explore, sans acceptation de domaine | campagne V&V dediee et limites explicites |
| `owner_accepted_experimental_bounded_use` | domaine etroit accepte par Owner, avec exclusions | extension de geometries, maillages, chargements et oracle externe |
| `owner_accepted` | domaine accepte par Owner, avec limites normales documentees | preuves completes de release et absence de reserve bloquante dans ce domaine |
| `stable` | domaine eligible au gate de release | maintien des non-regressions et audit de release |

- [x] produire, pour chaque statut borne, une fiche de promotion reliee a la
  ligne de `qualification/element_analysis_matrix.json` ; le registre
  `qualification/maturity_promotion_0_2_1.json` interdit les scopes oublies
  ou les promotions par simple libelle ;
- [x] ajouter l'audit executable `qf_solver.py maturity-promotion` avec un
  rapport JSON/Markdown, un controle d'integrite des chemins et une gate qui
  interdit toute promotion automatique ;
- [ ] etendre chaque campagne bornee avec au moins trois familles de geometrie
  ou chargement, trois niveaux de maillage, un indicateur de convergence et
  une zone de mesure non singuliere ;
- [ ] confronter les cas comparables a Code_Aster ou CalculiX sur maillage et
  conventions documentes, sans presenter un oracle externe comme une preuve de
  validite generale ;
- [ ] couvrir residues, bilan d'energie, reactions, modes rigides et valeurs
  finies selon le type d'analyse ;
- [ ] faire intervenir une `owner_review` ou un `external_audit` apres les
  preuves automatiques, puis seulement mettre a jour le statut de la matrice ;
- [ ] prioriser les domaines actuellement `owner_accepted_experimental_bounded_use` :
  MITC4 multicouche dynamique, MITC3 multicouche courbe, TET10 J2, contact
  borne, orthotropie structurelle et grand modele ;
- [ ] conserver `research` lorsque la convergence, la physique ou le domaine
  restent insuffisamment etablis, notamment le total-lagrangien structurel.

Critere de sortie : chaque promotion de maturite est accompagnee d'une preuve
reproductible, d'une justification de domaine, d'une mise a jour de matrice et
d'une decision Owner ou d'un audit externe trace.

### P-REL-021.3 - Audit de publication et retrait de la livraison web

Un site Internet n'est pas necessaire a une bibliotheque Python. Pour
`0.2.1a0`, la documentation publiee peut rester composee de Markdown, PDF,
README, exemples et artefacts V&V versionnes. Aucune livraison web ne sera
maintenue par defaut.

- [x] inventorier tous les documents suivis par Git : README, `docs/`, PDF,
  HTML, rapports V&V, images, manifests et liens externes ; le resultat est
  trace dans `qualification/publication_audit_0_2_1.json` ;
- [x] classer chaque artefact en `public`, `internal`, `archive_immutable` ou
  `generated_not_published` ;
- [x] rechercher les donnees personnelles, chemins locaux, traces d'outillage
  interne, regles internes, secrets, anciennes marques et references non
  publiables ;
- [ ] verifier licences, droits de redistribution et provenance des figures,
  references, images Docker et resultats externes par `external_audit` avant
  le tag public ;
- [x] retirer du depot public le repertoire genere `site/`, la publication web
  et les tests de navigateur associes apres migration des liens utiles vers
  Markdown ou PDF ;
- [x] conserver les sources Markdown et le generateur PDF lorsque leurs
  contenus sont necessaires a la revue Owner ;
- [x] verifier les liens Markdown/PDF apres retrait du site et mettre a jour
  README, `pyproject.toml`, CI, `.gitignore` et le guide de contribution ;
- [x] ne planifier aucun site futur dans cette feuille de route : cette phase
  se limite a une publication propre de la librairie et de ses documents.

Critere de sortie : aucun site genere ou pipeline web ne bloque la release,
les documents publics sont inventories et les artefacts internes ne sont pas
publies par erreur.

### P-REL-021.4 - Terminologie de revue et audit documentaire

Les sources maintenues ne doivent pas utiliser de vocabulaire generique pour
une decision de maturite. Les termes controles sont :

- `owner_review` : decision du proprietaire du projet, tracee et non
  independante ;
- `external_audit` : controle ou revue independante, avec auteur, version,
  perimetre et artefacts identifies ;
- `automated_verification` : controle reproductible execute par les tests ou
  une campagne, sans decision de maturite implicite.

- [x] auditer les sources publiees, metadonnees, schemas JSON, messages CLI,
  README, documentation et CI pour chaque ancien libelle de revue ou de
  blocage non attribue ;
- [x] remplacer les termes publies par `owner_review` ou `external_audit`
  selon la responsabilite effective ; le schema V&V de sortie passe a `2` et
  publie `owner_decision` ;
- [x] conserver les archives de preuves immuables sans reecriture, mais
  documenter leur terminologie historique lorsqu'elle est encore visible ;
- [x] ajouter un test de vocabulaire avec une liste d'exceptions limitee aux
  archives immuables ;
- [x] appliquer la meme regle aux nouveaux documents et enregistrements de
  qualification ; la politique est tracee dans
  `docs/reference/review_terminology.md`.

Critere de sortie : les sources publiques maintenues emploient une terminologie
coherente, et la trace distingue clairement verification automatique,
`owner_review` et `external_audit`.

## Matrice de preuves obligatoire

Pour chaque element et methode inclus, le dossier doit contenir une reference
analytique ou un invariant, plusieurs maillages et une courbe de convergence,
plusieurs chargements et une geometrie non triviale, une correlation
Code_Aster ou CalculiX lorsque comparable, des controles de residu, reactions,
energie, modes et valeurs finies, les sorties JSON/Markdown/PNG/VTU et une
`owner_review` datee.

Les familles ciblees sont TET4, TET10, MITC4, MITC3, BEAM2, ressorts/masses/
MPC/RBE, solides orthotropes, stratifies, J2, contact borne et grand modele.
Le contact dynamique, le dommage, la delamination et la dynamique non lineaire
restent hors scope tant qu'ils ne sont pas implementes et prouves.

## Robustesse a fermer

- maillages inverses, degeneres, aplatis et distordus ;
- conditions limites insuffisantes et matrices singulieres ;
- materiaux, unites, orientations et DDL invalides ;
- non-convergence, residus anormaux et valeurs non finies ;
- pas de temps, frequences et amortissements invalides ;
- contact actif/inactif, ouverture, fermeture et glissement ;
- reprise checkpoint, memoire, gros modele et comparaison direct/iteratif ;
- erreurs explicites classees et couvertes par des tests.

## Commandes de pilotage V&V

```powershell
python .\qf_solver.py release-vv --output .\results\release_vv_0_2_1
python .\qf_solver.py release-vv --output .\results\release_vv_0_2_1 --execute-campaign
python -m pytest tests/unit tests/integration
python -m pytest tests/verification -m benchmark
python -m ruff check src tests scripts
```

Lots rapides recommandes avant une campagne complete :

```powershell
python .\scripts\run_linear_dynamic_vnv.py --family all --output .\qualification\vnv\linear_dynamic_families
python -m pytest tests/verification -q -k "not code_aster and not benchmark and not meshed"
python .\qf_solver.py release-vv --output .\tmp\release_vv --execute-campaign
```

Le premier lot est actuellement `PASS` pour les cinq familles internes. Le
second lot ne remplace pas les correlations externes ; il sert a isoler les
regressions de formulation sans attendre Docker. La commande `release-vv`
reste l'autorite pour la decision de release et retourne le code `4` tant que
les preuves, la maturite ou la revue Owner sont incompletes.

## Etat mesure de l'iteration P-VV-021

La campagne de qualification du `2026-08-14` a ete executee avec
`python .\\qf_solver.py qualify --manifest .\\qualification\\campaign.json`
et retourne `PASS` pour `13/13` cas, dont `12` bundles verifies. Le gate
`release-vv` reste toutefois en `FAIL` lorsque les conditions de maturite,
de revue ou de proprete du checkout ne sont pas satisfaites : ce verdict ne
contredit pas la campagne de calcul et ne doit pas etre resume comme un echec
des 13 cas.

Le dernier controle automatise mesure `825 passed, 24 skipped` pour
`tests/unit`; la derniere passe complete d'integration reste `115 passed, 13
skipped`. Les tests Code_Aster/evidence cibles passent avec `7 passed, 4
skipped`, les tests du runner TET10 J2 et du paquet interne avec `5 passed`, et
le gate release avec `10 passed` sur sa selection. `ruff`, `compileall` et
`git diff --check` passent. Le lot complet
`tests/verification` n'est pas declare vert : il depasse le delai
d'execution local lorsqu'il melange toutes les campagnes lourdes et doit etre
decoupe par campagne avant le gel.

Apres l'integration du bundle Code_Aster, les deux bundles de preuves sont
desormais controles par `release-vv` avec `0` erreur d'integrite. Le nouveau
paquet interne contient `11` fichiers, le paquet Code_Aster `234` fichiers; le
runner TET10 J2 complexe a produit deux niveaux de maillage et un rapport de
raffinement. Les resultats numeriques et les maturites restent separes de la
decision Owner.

Les blocages restants ne sont pas transformes en succes artificiels :

- plusieurs scopes portent encore `owner_accepted`, `verified_development` ou
  `experimental`, alors que la cible release exige `stable` ;
- plusieurs artefacts V&V references par les registres ne sont pas presents
  dans le checkout controle, notamment des campagnes `qualification/vnv` ;
- la campagne officielle contient six cas dont les calculs et controles
  numeriques passent, mais dont la politique de qualification maintient le
  verdict `WARNING` ou `FAIL` ; le rapport les classe comme
  `calculation_checks_passed_but_qualification_policy_blocks` ;
- la revue Owner de `0.2.1a0` reste `pending` ;
- l'arbre source est volontairement non propre tant que les changements de
  cette iteration n'ont pas ete revus et commites.

Le prochain travail automatisable est donc de regenerer ou d'archiver les
artefacts V&V manquants, puis d'executer chaque campagne lourde separement
avec son rapport et son manifeste. Une promotion vers `stable`, une fermeture
d'anomalie ou une decision Owner restent des actions de revue et ne doivent
pas etre pre-remplies par l'outil.

### Correlations Code_Aster executees le 2026-08-14

Le daemon Docker a ete demarre avec Docker Desktop et l'image Code_Aster
epinglee `18.1.0` a ete utilisee. Le catalogue courant recense 51 dossiers
actifs : 35 sont termines avec `PASS_EXTERNAL_CORRELATION`, 1 est en `WARNING`,
13 sont des echecs numeriques conserves et 2 restent indisponibles ;
echecs numeriques explicites. Le calcul TET4 dynamique grossier `h=0,42` est
conserve dans `excluded_directories` comme etude historique supersedee par le
rerun `h=0,30`; il n'est donc plus compte comme avertissement actif. Les
deux niveaux TET10 J2 complexes sont regroupes dans l'etude de raffinement
`VNV-TET10-J2-CODEASTER-COMPLEX-REFINEMENT-027`; les dossiers individuels sont
exclus du comptage pour eviter une double comptabilisation. Les trois runners historiques
`modal_reference`, `newmark_reference` et `nafems13h` ont ete reconstruits avec
des templates controles, executes dans Docker et normalises.
Les autres campagnes actives listees dans le catalogue disposent bien d'un
resume Code_Aster, d'une figure et d'empreintes. Les rapports individuels,
figures et empreintes sont conserves dans `tmp/code_aster/` pour audit local.

Le paquet suivi
`qualification/evidence/code_aster_correlation_campaign_2026-08-14/` contient
les fichiers de preuve retenus, `234` empreintes verifiees et aucun chemin
absolu de poste de travail. Le gate release le voit comme
`EVIDENCE-BUNDLE-CODE-ASTER-CORRELATION-2026-08-14: PASS`.

Le premier calcul TET4 dynamique (`h=0,42`) etait `WARNING`, non pas pour une divergence entre les
solveurs : les ecarts sur le meme maillage sont `6,5e-13` en modal,
`5,9e-13` sur l'historique Newmark et `8,6e-13` en harmonique. Le warning
vient du raffinement spatial encore insuffisant : l'increment final de la
premiere frequence vaut `24,9 %`, au-dessus du seuil de `10 %`. Le cas doit
donc rester ouvert jusqu'a un raffinement supplementaire; il ne faut pas le
promouvoir automatiquement.

Le rerun `h=0,30` est `PASS_EXTERNAL_CORRELATION` : `313` TET4, ecart modal
de `0,083 %`, ecart statique de `4,87 %`, ecart Newmark de `1,14e-12` et
ecart harmonique de `2,72e-12`. Le warning de convergence spatiale est leve
pour le protocole retenu; le calcul grossier reste preserve comme historique
et ne doit pas etre requalifie comme un echec actif. La revue Owner et
l'archivage de la preuve correspondante restent obligatoires.

La nouvelle etude TET10 J2 complexe `VNV-TET10-J2-CODEASTER-COMPLEX-REFINEMENT-027`
compare `457` puis `1 031` elements TET10 sur une equerre rentrante sous
chargement combine. Les deux niveaux passent Code_Aster; l'increment relatif
QF du deplacement combine est `0,1885 %`, celui de la PEEQ moyenne `5,13 %`,
et le residu maximal est `1,97e-9`. Deux niveaux ne suffisent pas a demontrer
une convergence asymptotique; le statut experimental et l'exclusion des pics
ponctuels a l'angle rentrant sont maintenus.

Le lot historique complementaire ajoute aussi les resultats suivants :
contact liaison normal, contact normal historique et TET4 TL structural
passent `PASS_EXTERNAL_CORRELATION`. Les runners historiques `modal_reference`,
`newmark_reference` et `nafems13h` passent maintenant eux aussi
`PASS_EXTERNAL_CORRELATION` apres reconstruction de leurs templates et
execution Code_Aster. Le cas
MITC4 modal 10k a produit une reference Code_Aster, mais QF_solver n'a pas
atteint le residu modal `1e-7`; il reste donc
`QF_NUMERICAL_FAILURE_REFERENCE_AVAILABLE` et ne peut pas etre compte comme
correlation externe reussie.

Les trois nouvelles corrélations MITC4 sont documentées dans le paquet :
modal `32x32` sur dix modes avec ecart maximal QF/Code_Aster de `1,872 %` et
MAC minimal `0,99999968`; Newmark NAFEMS 13H avec correlations `0,954091` en
deplacement et `0,955821` en contrainte, pics `5,211 %` et `10,505 %`; et
harmonique NAFEMS 13H avec ecarts de pic `3,364 %` en frequence, `1,945 %`
en deplacement et `3,245 %` en `S11`. Ces resultats restent soumis a Owner
review et ne changent pas automatiquement la maturite.

Le probe controle `40 x 10`, execute directement avec Code_Aster, passe avec
un ecart modal maximal de `0,70194 %` et un residu QF_solver de `8,66e-9`.
Une tentative `200 x 50` avec `eigsh`, shift-invert, ILU et un complement de
Schur creux approche reste en echec GMRES (`info=500`) malgre une memoire
stabilisee autour de `422 Mo`. Une tentative `LOBPCG + ILU` avec condensation
lazy echoue des l'iteration initiale avec un residu de travail de l'ordre de
`7,1e10`; elle reste elle aussi un diagnostic, pas une correlation validee.

Le diagnostic modal 10k a ensuite teste `eigsh` avec shift `1 Hz` et
condensation explicite. Cette variante passe sur `400` elements avec un
residu `8,66e-9` et un ecart maximal de `0,70194 %`, mais la condensation
explicite depasse la memoire disponible a `10 000` elements. Le chemin
`LOBPCG + condensation lazy` et la variante `eigsh` restent donc des voies
scalables en memoire, mais leur convergence modale est encore insuffisante
pour fermer le cas 10k. Les controles de methode,
preconditionneur ILU, shift et reutilisation de reference sont maintenant
tracables dans le runner; aucune promotion de maturite n'est faite.

Une tentative supplementaire `eigsh + spilu` avec `ncv=40`, GMRES interne
`maxiter=2000` et `restart=100` a atteint le timeout controle de `900 s` avec
environ `425 MiB` de memoire, sans eigenpaire. Elle est tracee comme diagnostic
separe dans `docs/verification/mitc4_modal_10k_diagnostic_2026-08-14.md` et ne
rejoint pas le catalogue des correlations. Le prochain levier reste un
backend distribue ou un preconditionneur AMG/SLEPc, pas une hausse artificielle
du statut.

La campagne ne ferme pas le gate de release : les maturites, la presence des
preuves dans l'archive suivie et la revue Owner restent obligatoires. Les
resultats externes sont des preuves de correlation, pas une signature de
qualification.

Le socle fonctionnel couvre TET4, TET10, MITC4, statique lineaire, modal,
Newmark, harmonique, non-lineaire experimental et grand modele. La
documentation technique Markdown/PDF est regeneree hors ligne et ses resultats
sont recalcules par l'API publique.

Le tableau de bord genere est la source autoritative pour le nombre de tests,
les verdicts et la revision source. Le projet n'est pas certifie : il vise une
qualification progressive sur des perimetres bornes.

La version 0.2.0 ajoute l'identite QF_solver, l'import Gmsh MSH 4.1 et dix
benchmarks mailles reproductibles. Les criteres mecaniques de ces dix cas
passent; TET10 courbe et J2 restent volontairement en `WARNING` experimental.

La structure de publication alpha est figee autour de `src/solveur` et
`src/solveur/compat/mitc4`. Docker est conserve uniquement sous `tools/containers/large`
pour reproduire PETSc/MPI; il n'est ni requis par la V1 standard ni embarque
sur PyPI. Le manuel et les preuves restent publics dans GitHub, tandis que la
wheel ne contient que le runtime et ses petites ressources d'execution.

## Regles de lecture de la feuille de route

Les cases cochees constituent des constats dates et des preuves historiques;
elles ne remplacent ni le registre de maturite ni une decision Owner par
perimetre. Les nombres de tests, d'artefacts et les performances chiffres ici
sont des instantanes de campagne : le tableau de bord genere reste la source
active.

La politique d'oracle externe active est exclusivement
`theorie -> Code_Aster -> CalculiX`, telle que figee dans
`qualification/external_oracle_policy.json`. Les resultats issus de logiciels
commerciaux ou de tables publiees peuvent etre archives comme contexte
historique, mais ils ne constituent ni une dependance, ni un critere bloquant
de la feuille de route.

## Frontiere de publication V1 / V2

Decision de produit : fermer une premiere version publique utile et
decouvrable avant d'elargir davantage la mecanique.

La V1 ajoute uniquement les trois blocs fonctionnels suivants au socle actuel :

1. elements d'assemblage : `BEAM2`, ressorts, masses concentrees, contraintes
   multipoints et liaisons de type RBE ;
2. contact mecanique : sans frottement en premier, puis frottement de Coulomb
   regularise ;
3. coque triangulaire `MITC3+` a trois noeuds, necessaire pour les maillages
   surfaciques qui ne peuvent pas etre constitues uniquement de quadrangles.
   Son objectif fonctionnel est d'offrir, a terme, les memes familles
   d'analyse et de materiaux que `MITC4`, sans supposer que leurs precisions
   ou leurs domaines de validation sont identiques.

Les autres familles proposees, notamment HEX8, WEDGE, PYRAMID, thermique,
thermoelasticite, `generalized-alpha`, spectres, PSD, hyperelasticite,
endommagement, raffinement adaptatif et sous-structuration avancee, sont
reportees en V2. Elles ne bloquent pas la publication de la V1.

La V1 pourra publier des fonctions de maturites differentes. Une fonction
`experimental` restera accessible si son statut, ses limites et ses preuves
sont visibles; elle ne sera pas presentee comme qualifiee.

## P-OSS - Transition vers une bibliotheque Python open source

Objectif final : publier QF_solver comme bibliotheque Python FEM boite blanche,
installable, documentee et reproductible. La traduction anglaise du site et
des interfaces est reportee apres stabilisation technique; elle ne doit pas
dupliquer les sources de verite francaises avant la mise en place d'une chaine
de traduction controlee.

- [x] figer l'identite publique `qf-solver`, la facade `solveur.api`, les URLs
  de distribution et les regles de version de l'API ;
- [x] preparer contribution, support, securite, conduite, citation et
  formulaires distincts pour defauts et V&V ;
- [x] documenter une checklist de publication et figer la politique de licence
  `Apache-2.0` pour le code et `CC BY 4.0` pour la documentation et les
  exemples originaux ;
- [x] supprimer les references publiques au mode de travail interne, remplacer
  les instructions de developpement par un guide neutre et ajouter un audit
  bloquant de confidentialite avant archive publique ;
- [x] exclure des archives Git les resultats locaux, sites generes, dossiers
  temporaires et etudes V&V de travail; les preuves publiees seront choisies
  explicitement lors de la release ;
- [x] formaliser la frontiere public/prive : une archive `export-ignore` ne
  rend pas prive un fichier commite; les donnees locales, notes de travail,
  configurations de machine et contenus non publics restent hors de
  l'historique du depot public ;
- [ ] realiser un `external_audit` de l'historique Git, des fichiers suivis et des
  changements indexes; si necessaire, creer un depot public a historique
  propre avant la premiere publication ;
- [ ] definir et revoir les URLs publiques (depot, documentation, paquets,
  releases) avant toute mise en ligne; aucune URL locale ou interne ne doit
  etre publiee ;
- [ ] separer durablement les preuves V&V publiees des etudes de travail
  privees : publier uniquement des paquets relus, compacts et reproductibles ;
- [x] choisir les licences avec revue initiale des dependances et ajouter
  `LICENSE`, `LICENSE-DOCS`, `NOTICE` et `THIRD_PARTY_LICENSES.md` ; la
  verification finale des artefacts publics reste une action Owner ;
- [ ] analyser et purger les donnees, chemins locaux, preuves et modeles qui
  ne peuvent pas etre rendus publics ;
- [ ] publier une premiere release taggee avec archives, notes de version,
  hashes et politique de support explicite ;
- [ ] etablir un processus de revue externe des pull requests et des etudes
  V&V avant toute hausse de maturite ;
- [ ] concevoir la traduction anglaise a partir d'identifiants documentaires
  stables, avec controle des formules, tableaux et verdicts dans les deux
  langues.

## P0 - Fermer la baseline documentaire

Statut : **baseline technique et Owner review documentaire fermees;
revue independante et qualification externe volontairement BLOCKED**. Le dossier de cloture est
`docs/verification/baseline_documentaire_p0.md`.

- [x] definir un contrat V&V generique `study.json` + sorties normalisees,
  comparaison automatique et rapport Markdown obligatoire ;
- [x] declarer Quentin Farinazzo comme auteur et validateur mecanique en
  `self_review`, sans revendiquer une independence inexistante ;
- [x] retirer les logiciels commerciaux des dependances actives : la politique
  `theorie -> Code_Aster -> CalculiX` est acceptee le `2026-07-26` dans
  `qualification/external_oracle_policy.json`; les valeurs publiees restent
  des references historiques non bloquantes ;
- [x] relire le dossier technique consolidant TET4, TET10, MITC4, MITC3+,
  BEAM2, composite borne et methodes : owner review finale enregistree le
  `2026-08-01`, decision `accepted_with_recommendations` ;
- [ ] renseigner les champs `reviewer` et `approver` apres `external_audit` :
  action Owner, volontairement non pre-remplie ;
- [x] approuver une premiere revision Git, figer les dependances et enregistrer
  la baseline engineering `0.2.0` dans `qualification/baselines/` ;
- [x] classer 61 formules critiques par `REQ-*`, code, fonction, test et
  reference dans `qualification/formulas.json` ;
- [x] traiter toute anomalie de lien, formule, figure ou resultat comme une
  anomalie de configuration ;
- [x] conserver `qualification` bloquant tant que la baseline n'est pas propre et
  approuvee.

Le rapport genere `docs/generated/review_readiness.json` separe couverture
automatique, Owner review et baseline Git. Aucun champ de signature n'est
pre-rempli par le solveur.

Critere de sortie : generation d'artefacts documentaires, tests documentaires
et `owner_review` sont verts sur Windows et Linux.

## P-DOC - Demonstrations documentees et accessibles par la librairie

Objectif : rendre chaque capacite mecanique demonstrable de deux manieres
coherentes : par une page technique lisible par un ingenieur et par une entree
reproductible de la librairie Python. Le catalogue ne doit pas etre une simple
liste de figures : chaque demonstration doit relier formulation,
implementation, test, resultat et reference bibliographique.

- [x] conserver un catalogue de benchmarks machine-readable avec identifiant,
  famille d'element, analyse, maturite, criteres, exigences et reference HTTPS
  dans `qualification/benchmarks.json` ;
- [x] creer `qualification/demonstrations.json` comme registre transverse de
  vingt-huit demonstrations : onze benchmarks mailles, dix cas V&V executes
  par `QualificationCampaignRunner.run_case()`, six exemples JSON avec dossier
  de preuve v2 et un plan PETSc/MPI 1M DDL sans allocation. Le catalogue couvre
  deja TET4/TET10/MITC4 statique, modal, Newmark, harmonique, J2, orthotropie,
  multicouche et la preparation grand modele; l'execution massive reste une
  campagne d'infrastructure separee ;
- [x] imposer pour chaque entree : `demo_id`, element ou methode, hypotheses,
  modele d'exemple, runner, page documentaire, tests, exigences, maturite,
  references `REF-*`, DOI ou URL, sorties attendues et limites. Le controle
  `DemonstrationCatalog.validate_integrity()` refuse un benchmark, modele,
  page, runner, test, exigence, reference ou sortie minimale orphelin ;
- [x] ajouter dans `solveur.api` `list_demonstrations()`, `run_demonstration()`
  et `run_qualification_case()` avec filtrage par famille, methode et maturite.
  Les fonctions retournent le descripteur, les references et les artefacts de
  preuve; les cas V&V conservent obligatoirement le profil fige du manifeste ;
  des sorties sans dependre du site web ;
- [x] conserver `list_benchmarks()` et `run_benchmark()` comme interface
  retrocompatible pour les onze benchmarks mailles existants ;
- [x] produire une page Markdown par element et par methode comprenant :
  geometrie, ddl, formulation mathematique, integration, algorithme, exemple
  executable, maillage, chargement, conditions limites, tableau de resultats,
  figure de deformee, invariants, convergence, limites et references ; les
  23 pages controlees de `qualification/documentation_review_pages.json`
  couvrent les elements, entites, contacts et methodes disponibles ;
- [x] relier chaque formule importante a un identifiant `FORM-*` ou `REQ-*`,
  une fonction de code, un test et une entree de `docs/reference/references.md`;
  les 44 formules critiques sont controlees par `qualification/formulas.json`
  et le rapport de readiness documentaire ;
- [x] couvrir au minimum les demonstrations TET4 traction/compression,
  membrane et torsion; TET10 patch, flexion et courbe; MITC4 membrane,
  flexion, cisaillement, locking, modal et Newmark; puis les variantes
  orthotropes, multicouches, harmoniques, J2 et grand modele. Le registre
  public contient 28 demonstrations controlees ;
- [x] faire regenerer par l'API les PNG, tableaux, JSON/VTU, rapports Markdown
  et empreintes SHA-256. Aucune valeur numerique ne doit etre recopiee
  manuellement dans la documentation. La campagne engineering du
  `2026-07-29` a regenere 625 artefacts avec manifeste `PASS` ;
- [x] ajouter un test de completude refusant une demonstration orpheline :
  `DemonstrationCatalog.validate_integrity()` controle le benchmark, le modele
  JSON ou generateur explicite, la page, le runner, les exigences, les
  references, les tests et les sorties minimales; les cas negatifs sont dans
  `tests/unit/test_demonstration_registry.py` ;
- [x] publier le catalogue dans le site hors ligne et dans le paquet Python,
  sans inclure de chemins locaux, donnees privees ou contexte d'execution.
  `docs/generated/demonstration_registry.md` est derive du registre
  machine-readable et `list_demonstrations()` expose la meme source ;
- [x] faire realiser une Owner review de chaque page avant de changer sa
  maturite. Les 23 pages ont une decision `accepted_with_recommendations`
  enregistree; une demonstration documentee ne vaut pas, a elle seule,
  qualification.

Critere de sortie : un ingenieur peut partir d'un identifiant de demonstration,
lancer le cas via l'API, lire la formulation et retrouver la reference
bibliographique, les tests et les artefacts correspondants sans chercher dans
des scripts internes.

## P1 - Qualification TET4 statique lineaire

Objectif : obtenir le premier perimetre candidat a une qualification interne.

- [x] completer traction, compression, pression et patch contrainte constante ;
- [x] enregistrer le 14 juillet 2026 l'acceptation engineering interne du
  TET4 lineaire isotrope par Quentin Farinazzo, en auto-revue non independante
  et sans revendication de certification externe ;
- [x] ajouter un panneau mince TET4 sollicite dans son plan, avec champ affine,
  resultante membranaire, cinq maillages en traction et cinq en compression,
  VTU et PNG regeneres ;
- [x] ajouter un arbre circulaire TET4 en torsion de Saint-Venant, avec huit
  maillages, traction terminale coherente, couple, rotation, contraintes, VTU
  et PNG regeneres ;
- [x] produire l'etude `VNV-TET4-TORSION-ANALYTIC-001`, avec huit paires de
  deformees QF_solver/Saint-Venant, resultats normalises, empreintes et rapport
  Markdown ;
- [x] ajouter la sonde `VNV-TET4-TORSION-STRESS-H9-001` a `105 529` TET4,
  soit `4,007` fois h8, et accepter le champ global L2 de contrainte a
  `18,891 %` sous le seuil engineering borne de `20 %` ;
- [x] retirer les etudes externes non reproductibles du plan actif ; la
  comparaison retenue est `theorie -> Code_Aster -> CalculiX`, selon
  `qualification/external_oracle_policy.json` ;
- [x] statuer sur le perimetre TET4 lineaire isotrope; accepter la contrainte
  globale L2 du cas de torsion lisse et conserver hors acceptation les pics
  ponctuels, singularites et extrapolations a d'autres geometries ;
- faire relire independamment le patch TET4 Gmsh et sa reference analytique ;
- [x] ajouter une convergence h quantitative avec ordre observe sur six
  maillages Gmsh, seuil executable et courbe regeneree ;
- [x] qualifier les cas canoniques de pression, force volumique et reactions
  globales; etendre ensuite cette preuve aux maillages multi-elements ;
- [x] borner conditionnement, qualite de maillage et domaine materiau TET4
  dans `tet4-linear-static-v1`, avec politique executable par profil ;
- [x] produire et verifier un dossier de preuve v2 reproductible pour chaque
  cas resolu de la campagne ;
- [x] ajouter un oracle analytique TET4 independant du noyau EF pour traction,
  compression et force volumique, puis le relier a la campagne ;
- mettre en place couverture MC/DC ou justification adaptee uniquement si le
  niveau d'assurance retenu l'exige.

Critere de sortie : aucune exigence orpheline dans le scope
`tet4-linear-static`, aucune anomalie ouverte de severite bloquante, dossier de
preuve relu independamment.

## P2 - Coques MITC4

- [x] figer conventions de repere local et signes faces superieure/inferieure ;
- [x] renforcer patchs membrane, flexion et cisaillement ;
- [x] automatiser une matrice de shear locking de 160 calculs croisant cinq
  maillages, quatre epaisseurs, quatre distorsions et un Q4 temoin ;
- [x] ajouter une courbe de convergence publiee sur six maillages pour Cook et
  cinq maillages pour Scordelis-Lo et le cylindre pince ;
- [x] archiver une table publiee de cylindre pince comme repere historique
  non bloquant (`4,87 %`) ;
- [x] executer le point Cook `64x64` puis `200x200` (40 000 elements) pour
  ecarter une divergence numerique ;
- [ ] auditer independamment la reference et les conditions aux limites Cook:
  la fleche converge vers environ `0,2515`, pas vers la reference `0,2396` ;
- [x] executer CalculiX ou Code_Aster sur un maillage strictement identique
  pour fermer la correlation externe statique : `VNV-MITC4-CONICAL-CUTOUT-
  CODEASTER-DKQ-014` reprend les trois maillages QUAD4, le vecteur de pression
  coherent et les appuis; l'ecart fin vaut `0,3436 %` a la sonde, `1,7565 %`
  sur le vecteur et `2,26e-11 %` sur la resultante de reaction ;
- [x] verifier la distorsion jusqu'a 30 %, le warping par le gate maillage et
  l'energie de rotation de percage ;
- [x] ajouter `VNV-MITC4-CONICAL-CUTOUT-STATIC-012` : panneau annulaire
  conique facettise, ouverture centrale libre, pression normale coherente,
  trois maillages et export PNG/VTU. Cette preuve geometrie complexe est
  supplementaire; elle ne modifie pas l'acceptation statique existante ;
- [x] correler cinematiquement le panneau conique ajoure sur les memes maillages
  avec CalculiX 2.20 S4 (`VNV-MITC4-CONICAL-CUTOUT-CALCULIX-S4-013`) : ecart
  sonde fin `0,0249 %`, ecart vectoriel fin `0,629 %`. Les pics de contrainte
  au bord libre restent publies mais ne sont pas utilises seuls comme critere ;
- [x] fermer la correlation de resultante du panneau conique : la sortie
  CalculiX `RF` reste un diagnostic ambigu avec `CLOAD`, mais Code_Aster
  `REAC_NODA` sur les translations du bord encastre ferme la comparaison de
  resultante au meme maillage (`2,26e-11 %` au niveau fin). Les energies et
  contraintes de faces restent des comparaisons distinctes ;
- comparer resultantes, contraintes de faces et energies a une reference
  independante.

Le perimetre `mitc4-linear-static` est valide pour `engineering_internal` avec
recommandations, tout en restant `candidate` dans le registre de qualification.
Sa matrice locking fine presente une erreur maximale de `2,08 %` face a
Timoshenko et un ratio limite mince de `0,979`. La correlation publiee du
cylindre pince est `PARTIAL_PASS`; une correlation reproductible Code_Aster ou
CalculiX sur maillage identique reste necessaire pour une decision au-dela de
`engineering_internal`.

Critere de sortie : domaine d'emploi MITC4 borne et justifie, avec tendances de
convergence et limites explicitement publiees.

## P2B - Coque triangulaire MITC3+

Objectif V1 : ajouter un element coque triangulaire a trois noeuds pour traiter
les maillages non structures, les raccords topologiques et les surfaces pour
lesquelles un remailleur ne peut pas garantir des quadrangles. Le nom public
sera `MITC3`; la formulation implementee sera documentee comme `MITC3+`.

Le plan de conception et de V&V autoritatif est
`docs/elements/mitc3_plan_implementation.md`.

- [x] figer la formulation `MITC3+` lineaire : triangle a trois noeuds,
  cinematique Reissner-Mindlin, six DDL par noeud, enrichissement interne des
  rotations par bulle cubique et condensation statique locale ;
- [x] conserver 18 DDL assembles et ne jamais exposer les deux parametres
  internes de bulle dans le format JSON, l'API ou les resultats nodaux ;
- [x] definir le repere local, l'ordre nodal, la normale, les signes de
  courbure, les faces `z=+t/2` et `z=-t/2`, ainsi que la compatibilite de bord
  avec MITC4 ;
- [x] implementer rigidite, masse coherente, charges nodales, pression,
  traction surfacique, traction de bord, gravite et force volumique ;
- [x] supporter `shell_isotropic`, puis `shell_laminate` avec matrices
  `A/B/D`, cisaillement transverse, orientation projetee des plis et resultats
  par pli. Le composite reste `experimental` jusqu'a sa campagne dediee ;
- [x] integrer `MITC3` au registre d'elements, au schema JSON, a l'import Gmsh
  TRI3, au controle maillage, aux exports JSON/CSV/VTU et au post-traitement ;
- [x] ajouter les scopes separes `mitc3-linear-static`, `mitc3-modal`,
  `mitc3-transient-dynamic`, `mitc3-harmonic-response` et
  `mitc3-laminate-static` ;
- [x] enregistrer la decision finale Owner sur la statique lineaire isotrope
  le `2026-08-01`, puis accepter modal, Newmark et harmonique le
  `2026-08-02` apres verification de la masse et de la condensation des
  directions sans inertie ;
- [x] completer le patch de flexion explicite et la correlation externe sur
  coque doublement courbe. Le patch de cisaillement constant atteint
  `1,81e-16`; les modes rigides, l'isotropie, l'objectivite, le patch
  membrane, le shear locking, la distorsion, la convergence h et le melange
  `MITC3`/`MITC4` sont couverts par la campagne raffinee `PASS` ;
- [x] comparer le meme maillage de 512 triangles a Code_Aster 18.1.0 DKT :
  ecart membrane `5,96e-8` et flexion `0,007116 %`, verdict
  `PASS_EXTERNAL_CORRELATION` ;
- [x] executer CalculiX 2.20 S3 comme temoin : membrane `0,0086 %`, mais
  flexion trop raide avec `113,086 %` d'ecart; conserver ce resultat en
  `WARNING` et ne pas utiliser S3 comme oracle positif de flexion ;
- [x] raffiner Scordelis-Lo a `20 000` triangles et le cylindre pince a
  `19 600` triangles : erreurs finales `0,4044 %` et `2,0899 %`, avec
  courbes, champs, manifestes et dossier PDF de revue ;
- [x] ajouter l'hemisphere pince a quatre quadrants sur six raffinements et le
  comparer sur les memes maillages a Code_Aster 18.1.0 DKT : au niveau fin,
  ecart a la reference publiee `0,5912 %`, ecart sonde QF/Aster `0,0927 %`,
  ecart de champ nodal `0,1536 %` et increment final `0,2605 %` ;
- [ ] ajouter une reference NAFEMS triangulaire supplementaire comme oracle
  secondaire trace; cette action est recommandee mais non bloquante ;
- [x] publier les formulations forte et faible, les matrices, les points de
  tying, la condensation, les demonstrations, les limites et les preuves en
  Markdown et PDF ;
- [x] maintenir le statut `experimental` jusqu'a Owner review de la statique
  isotrope, puis faire evoluer chaque scope independamment.

Critere de sortie V1 : `MITC3` statique lineaire isotrope utilisable via JSON,
API, CLI et Gmsh, sans mode parasite, avec patch tests, campagne mince,
convergence h, correlation externe et dossier de preuve reproductible. La
parite complete avec MITC4 est un objectif progressif, pas un prerequis masque
pour publier le premier scope MITC3.

## P3 - Dynamique lineaire

La couverture element/analyse est suivie dans
`qualification/element_analysis_matrix.json` et
`docs/verification/matrice_elements_analyses.md`. La priorite n'est plus
seulement de verifier les algorithmes generiques, mais de fermer chaque couple
element/analyse avec sa propre convergence, son oracle et sa decision Owner.

- [x] ajouter les campagnes internes modales, Newmark et harmoniques
  `VNV-*-LINEAR-DYNAMICS-001` pour TET4, TET10, MITC3+, BEAM2 et
  ressort/masse : residus/orthogonalites, vibration libre du premier mode,
  energie et limite statique a `0 Hz`;
- [x] executer `VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020` : correlation
  Code_Aster `3D/TETRA4` sur 135 TET4, avec six modes, Newmark et harmonique
  sur les memes grilles; les ecarts externes sont inferieurs a `1e-9 %` et
  les scopes sont acceptes par l'Owner le `2026-08-02`;
- [x] fermer TET4 modal, Newmark et harmonique dans trois scopes Owner
  separes; conserver le raffinement structurel recommande ;
- [x] executer `VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018` : correlation
  Code_Aster `3D/TETRA10` sur 135 TET10, avec six modes, Newmark et
  harmonique sur les memes grilles; les ecarts sont inferieurs a `1e-9 %` et
  les convergences maillage/pas de temps passent;
- [x] fermer TET10 modal, Newmark et harmonique avec les Owner reviews
  distinctes; le raffinement Newmark maillage/pas de temps est enregistre ;
- [x] ajouter une preuve TET10 amortie sur geometrie cylindrique avec
  amortissement de Rayleigh massique cible a `2 %` du premier mode :
  `VNV-TET10-DYNAMICS-DAMPED-CODEASTER-TETRA10-CYLINDER-024` passe Code_Aster
  sur les memes maillages, grilles temporelles et frequences; ecarts maximaux
  `0,0701 %` modal, `0,0889 %` Newmark et `0,0610 %` harmonique ;
- [x] ajouter un chemin de charge non cantilever sur bloc 3D a face inferieure
  bloquee et face superieure chargee :
  `VNV-TET10-DYNAMICS-CODEASTER-TETRA10-BLOCK-025` passe Code_Aster sur quatre
  niveaux spatiaux et quatre niveaux temporels; ecarts maximaux `3,24e-10 %`
  modal, `8,86e-13 %` Newmark et `1,14e-13 %` harmonique ;
- [x] ajouter une sonde de contraintes interieures TET10 sur `35` elements
  eloignes de `20 %` des faces singulieres : correlation Code_Aster PASS avec
  ecart L2 `2,1316e-13 %` sous la limite `10 %`, dans
  `VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-BLOCK-026` ;
- [x] etendre cette sonde au cantilever rectangulaire avec `13` elements
  interieurs : correlation Code_Aster PASS, ecart L2 `5,9227e-10 %`, dans
  `VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-CANTILEVER-027` ;
- [x] etendre la sonde au cylindre TET10 facettise avec `30` elements
  interieurs : correlation Code_Aster PASS, ecart L2 `0,43619 %`, dans
  `VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-CYLINDER-028` ;
- [ ] soumettre cette preuve amortie a l'Owner review et distinguer
  explicitement amortissement proportionnel demontre, amortissement
  non-proportionnel et calage experimental encore hors scope ;
- [ ] soumettre aussi le chemin non cantilever a l'Owner review ;
- [x] formaliser la politique machine-readable des observables de contrainte
  dans `qualification/stress_observable_policy_0_2_1.json` : marge interieure
  `20 %`, au moins trois sondes, seuil de correlation `10 %`, et pics
  ponctuels aux singularites informatifs seulement ;
- [x] documenter separement les pics ponctuels aux singularites, qui restent
  hors acceptance, dans la fiche Owner et le rapport ST-02 ;
- [x] executer `VNV-MITC3-DYNAMICS-CODEASTER-DKT-017` : correlation externe
  meme maillage DKT sur six modes (`1,7367 %`), historique Newmark (`0,5496 %`
  RMS) et harmonique (`0,2998 %` RMS), sous le seuil declare de `10 %`;
- [x] fermer MITC3+ modal, Newmark et harmonique par trois Owner reviews
  distinctes; les preuves internes coque courbe, libre-libre, dix modes,
  raffinement temporel et correlation DKT sont disponibles. Le raffinement
  maillage-frequence reste une recommandation ;
- [x] executer `VNV-MITC3-DYNAMIC-EXTENDED-001` : structure libre-libre,
  six modes rigides analytiques, coque cylindrique raffinee et tournee,
  controle `eigh/eigsh` a 2 560 DDL retenus, Newmark et harmonique courbes;
- [x] ajouter `VNV-MITC3-LAMINATE-DYNAMIC-001` : patch membranaire
  analytique, masse coherente, condensation drilling, modal, Newmark et
  harmonique pour le stratifie plan symetrique `[0/90/90/0]`;
- [x] correl(er) les reponses globales MITC3+ multicouches modal, Newmark et
  harmonique sur le meme maillage avec Code_Aster DST dans
  `VNV-MITC3-LAMINATE-DYNAMICS-CODEASTER-DST-019` : ecarts maximaux de
  `3,957 %`, `2,318 %` et `1,345 %`, sous les seuils traces ;
- [x] isoler l'erreur de pas de temps MITC3+ avec `80`, `160` et `320` pas par
  periode dans `VNV-MITC3-LAMINATE-TEMPORAL-REFINEMENT-001` : erreur RMS finale
  `0,0164 %`, ordre observe `2,00`, energie et residu sous `2,3e-12` ; cette
  preuve interne ne remplace pas une correlation externe de formulation ;
- [x] correl(er) les contraintes planes `S11`, `S22`, `S12` de chaque pli
  MITC3+ avec CalculiX `2.20` `S6 COMPOSITE` dans
  `VNV-MITC3-LAMINATE-PLY-STRESS-CALCULIX-S6-020` : ecart L2 fin `0,09625 %`,
  increment CalculiX final `0,07313 %` sous `0,2 %` ;
- [x] executer la correlation MITC3+ multicouche courbe a orientation projetee
  `VNV-MITC3-LAMINATE-CURVED-PROJECTED-CALCULIX-S6-024` : panneau cylindrique
  facettise, empilement `[0/90/90/0]`, projection de la direction globale dans
  chaque facette et comparaison CalculiX `S6 COMPOSITE`. Les raffinements
  `96x48` puis `128x64` abaissent l'ecart vectoriel `UX/UZ` a `3,4437 %` puis
  `2,0738 %`, avec un increment QF final de `1,2273 %` et un residu libre de
  `3,2487e-10` ;
- [x] fermer le MITC3+ multicouche courbe par une Owner review dediee. Quentin
  Farinazzo accepte le perimetre au statut experimental pour la V0.2.0-alpha le
  `2026-08-09`. Les contraintes par pli, les quantites interlaminaires et les
  cas courbes dynamiques restent hors de cette preuve et sont recommandes pour
  une version ulterieure ;
- [x] fermer BEAM2 modal, Newmark et harmonique par correlations Code_Aster
  axiale et transverse elancee sur les memes grilles :
  `VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019` passe sous `1 %`;
  Owner accepte le domaine borne; la dynamique de poutre epaisse est exclue;
- [x] fermer les preuves externes ressort/masse Newmark et harmonique avec
  Code_Aster `18.1.0` `DIS_T` sur les memes grilles temporelles et
  frequentielles declarees (`VNV-DISCRETE-CODEASTER-SDOF-001`) : ecarts
  statique/modal/Newmark/harmonique de `1,39e-16`, `0`, `3,05e-11` et
  `1,87e-15`; Owner accepte le domaine SDOF translationnel sans amortissement
  ni couplage multi-DDL le `2026-08-02`;
- [ ] conserver la dynamique non lineaire hors V1 et la traiter dans un projet
  de formulation/V&V distinct.

- [x] ajouter la masse coherente MITC4 avec inerties translationnelles et
  rotatoires physiques, sans inertie artificielle de drilling ;
- [x] condenser les directions de drilling effectivement sans masse et
  reconstruire les six ddl nodaux ;
- [x] permettre MITC4 modal et Newmark via API, CLI et exemples JSON ;
- [x] modal : ajouter la convergence de frequence et MAC sur porte-a-faux
  mince (`VNV-MITC4-MODAL-CANTILEVER-002`) ;
- [x] modal : verifier une plaque simplement appuyee et les quatre premiers
  modes de Navier, dont la paire propre double (`VNV-MITC4-MODAL-PLATE-003`) ;
- [x] modal : executer Code_Aster `18.1.0` DKQ sur le meme maillage `32x32` et
  comparer dix modes; ecart maximal `1,609 %`, MAC minimal `0,999998493`
  (`VNV-MITC4-MODAL-CODEASTER-DKQ-004`) ;
- [x] modal : verifier une structure assemblee libre-libre, exactement six
  modes rigides et leur sous-espace analytique ;
- [x] modal : verifier une coque courbe, une distorsion de `20 %`, la
  convergence et l'objectivite par rotation ;
- [x] modal : comparer `eigh/eigsh`, puis executer dix modes sur `2304`
  elements et `7011` DDL actifs sans conversion dense ;
- [x] modal : tentative de validation interne enregistree le `2026-07-16`,
  decision `accepted_with_recommendations`, masse coherente uniquement; la grille est disponible
  en Markdown et PDF dans `docs/verification/revue_mitc4_modale.md` et
  `docs/assets/reviews/revue_mitc4_modale.pdf` ;
- modal : faire remplir la revue independante par une personne autre que
  l'auteur avant toute qualification externe ; modele dans
  `qualification/reviews/mitc4_modal_independent_review_template.md` ;
- [x] Newmark : verifier l'historique signe et la convergence d'ordre deux
  de `T/20` a `T/160` (`VNV-MITC4-NEWMARK-FREE-002`) ;
- [x] Newmark : verifier amortissement analytique et chargement modal force
  (`VNV-MITC4-NEWMARK-DAMPED-FORCED-003`) ;
- [x] Newmark : ajouter impulsion demi-sinus, chirp lineaire et table arbitraire,
  avec convergence temporelle et contraintes de face
  (`VNV-MITC4-NEWMARK-BROADBAND-004`) ;
- [x] Newmark : comparer sur le meme maillage `8x8` avec Code_Aster `18.1.0`
  DKQ; correlations `0,9543` en `UZ` et `0,9560` en `S11`, ecarts de pic
  `5,20 %` et `10,51 %` (`VNV-MITC4-NEWMARK-CODEASTER-DKQ-005`) ;
- [x] Newmark : revue mecanique enregistree par Quentin Farinazzo le
  `2026-07-16`, decision `accepted_with_recommendations` pour l'usage
  engineering interne; registre
  `qualification/reviews/mitc4_transient_dynamic_2026-07-16.json`, Markdown et
  PDF controles ;
- [x] harmonique MITC4 : limite statique, amplitude, phase, resonance amortie
  et sensibilite a l'amortissement (`VNV-MITC4-HARMONIC-MODAL-001`) ;
- [x] demontrer la condensation harmonique exacte avec
  $C=\alpha M+\beta K$, charge directe de drilling et comparaison au systeme
  complexe complet (`VNV-MITC4-HARMONIC-CONDENSATION-002`) ;
- [x] harmonique MITC4 : excitation large bande sur quatre resonances avec
  accord direct/superposition modale complete
  (`VNV-MITC4-HARMONIC-BROADBAND-003`) ;
- [x] harmonique MITC4 : reference publiee NAFEMS 13H et correlations
  reproductibles Code_Aster/CalculiX sur maillage `8x8`, amplitude, frequence
  et `S11` (`VNV-MITC4-HARMONIC-NAFEMS13H-004`) ;
- [x] harmonique MITC4 : exporter les contraintes complexes `S11/S22/S12`
  par face et frequence, puis comparer `S11` a Navier, NAFEMS, Code_Aster et
  CalculiX ;
- [x] harmonique MITC4 : revue mecanique `accepted_with_recommendations` par
  Quentin Farinazzo le `2026-07-15` ;
- [x] harmonique MITC4 : adopter le processus de validation
  `QF_solver <-> Navier <-> NAFEMS publie <-> CalculiX/Code_Aster` ;
- [x] harmonique MITC4 : executer CalculiX S4/S8R sur le cas 13H; retenir S8R
  pour la sensibilite et tracer le `WARNING` `S11/NAFEMS=5,168 %` ;
- [x] harmonique MITC4 : executer Code_Aster `18.1.0` avec DKQ sur le cas
  13H; ecarts QF_solver de `3,364 %` en frequence, `1,900 %` en deplacement
  et `3,272 %` en `S11`, tous sous `5 %` ;
- [ ] harmonique MITC4 : obtenir une revue independante des correlations
  Navier, NAFEMS, Code_Aster et CalculiX avant toute hausse de maturite ;
- [x] ajouter chargements multi-composantes, calage de Rayleigh sur deux cibles
  modales et reprise de calcul; campagne
  `VNV-MITC4-NEWMARK-OPERATIONAL-006` `PASS`, addendum mecanique a revoir ;
- [x] documenter la masse coherente comme seule formulation acceptee et garder
  les matrices concentrees hors scope.

Critere de sortie : chaque methode possede reference analytique, invariant,
test de non-regression et exemple CLI/API.

## P4 - Grands modeles

- [x] ajouter l'orchestrateur `large-campaign`, son mode plan sans allocation,
  l'agregation JSON/Markdown et la telemetrie RSS processus ;
- [x] installer et figer le runtime Docker PETSc `3.25.1`, puis executer
  `P4-PETSC-100K-001` et `P4-PETSC-1M-001` sur deux rangs MPI ;
- [x] distribuer la matrice AIJ, le vecteur, les elements et les ddl entre
  rangs; accord mono/deux-rangs `2,92e-16` sur le petit cas ;
- [x] vectoriser par lots gradients, matrices `B` et rigidites TET4 : gain
  assemblage `x10,36` a 100k et `x2,88` a 1M, sans ecart numerique ;
- [x] assembler en blocs BAIJ `3x3`, convertir en AIJ avant GAMG et executer
  le niveau `3M`: `3 000 000` DDL, `5 821 794` TET4, `88,68 s`, `PASS` ;
- [x] mesurer la scalabilite forte 1/2/4 rangs sur 1M; accelerations `1,45`
  et `1,65`, efficacite quatre rangs limitee a `41,18 %` ;
- [x] supprimer la replication globale des noeuds/connectivites par rang avec
  lecture HDF5 par hyperslabs et tables de noeuds compactes locales ;
- [x] eliminer le rassemblement global des deplacements par une sortie MPI-IO
  collective `float64`, accompagnee de metadonnees et verifiee par empreinte ;
- [x] distribuer aussi les tableaux de blocages et charges en lecture HDF5
  chunkee: charges possedees par plage de DDL, blocages gardes pour le halo
  elementaire ou la ligne PETSc possedee; smoke MPI `PASS` avec norme de charge
  conservee ;
- [x] mettre en place la reprise PETSc depuis une solution terminee avec
  empreinte de modele, ainsi que le post-traitement TET4 HDF5 par blocs avec
  checkpoint atomique; preuve sur `477 042` TET4, reprise apres `131 072`,
  energie a `4,14e-13` du solveur et restart KSP en zero iteration ;
- [x] publier memoire pic, temps, iterations et versions MPI/PETSc ;
- [x] comparer GAMG et Hypre/BoomerAMG sur 1M/4 rangs : accord deplacement
  `3,40e-12`; GAMG reste le defaut (`24,41 s`, `0,759 GB/rang`) devant Hypre
  (`52,30 s`, `2,47 GB/rang`) malgre `18` iterations contre `53` ;
- [x] activer et tracer le repartitionnement des grilles grossieres GAMG a
  partir de quatre rangs; gain KSP mesure de `12,66` a `12,20 s` ;
- [x] mesurer la scalabilite faible a charge locale constante sur 1/2/4 rangs:
  efficacites `100/72,6/41,6 %`, verdict `WARNING` sous le seuil `60 %` ;
- [x] implementer un partitionnement de graphe PETSc/PT-Scotch avec
  redistribution reelle des elements; petit cas MPI verifie avec accord
  deplacement `3,06e-16` face au partitionnement contigu ;
- [x] corriger le proprietaire MPI des lignes du graphe pour les nombres
  d'elements non divisibles par le nombre de rangs, ajouter le trace
  `QF_SOLVER_MPI_TRACE=1` et la lecture HDF5 par plages contigues ;
- [x] stabiliser le partitionnement graphe sur `264 600` DDL et `1 029 000`
  DDL en quatre rangs: `PASS`, ecart graphe/contigu `2,24e-13` sur 1M,
  cut-face ratio `0,514 %`, imbalance `1,009` ;
- [ ] conserver le graphe en option experimentale tant qu'il n'a pas demontre
  un gain net de temps total et de memoire sur plusieurs topologies; le
  partitionnement contigu reste le defaut ;
- [x] tracer les tailles de halo nodal par rang dans `audit_large.json`
  (`local_owned_node_counts`, `local_halo_node_counts`,
  `halo_node_ratio_max`) ;
- [x] tracer les communications MPI estimees et niveaux multigrilles PETSc:
  `mpi_communication` dans `audit_large.json` et
  `preconditioner_diagnostics` dans `summary.json` avec `pc_mg_levels`,
  tailles matricielles et `matrix_info` ;
- [x] ajouter le profilage PETSc detaille `-log_view`, son parseur sans
  execution de contenu, les rapports JSON/Markdown et une campagne quatre
  rangs sur bloc, poutre et plaque pour expliquer quantitativement
  l'efficacite au-dela de deux rangs; a environ `254k` DDL, le bloc demande
  `49` iterations contre `161` pour la poutre et `136` pour la plaque, tandis
  que `PCSetUp` reste entre `0,546` et `0,613 s` ;
- [x] tester cinq reglages GAMG/Hypre sur bloc, poutre et plaque, soit quinze
  calculs quatre rangs; tous `PASS`, ecart deplacement maximal `1,96e-11`;
  GAMG seuil `0.01` gagne `18,0/5,3/7,3 %`, insuffisant pour changer le defaut
  selon la regle de gain minimal `10 %` sur chaque topologie.

Critere de sortie : cas 1M+ reproductible sur infrastructure identifiee, sans
conversion dense ni JSON monolithique.

## P4B - Politique de choix du solveur lineaire

Constat : la factorisation directe LU est une reference numerique utile pour
les V&V et les petits/moyens modeles. Elle reste correcte sur le cas Newmark
TET10 raffine a `50 112` DDL, mais une factorisation a demande environ
`4,5 Go` de memoire virtuelle. Ce cout interdit d'en faire le choix implicite
pour les calculs de grande taille : il s'agit d'une limite de ressources, pas
d'une invalidation de la solution LU.

- [x] definir une politique de selection explicite, exposee par l'API, les
  resultats et l'audit, sans basculement silencieux de methode ;
- [x] reserver LU/direct aux V&V, diagnostics, petits/moyens modeles et cas a
  plusieurs seconds membres lorsque le budget memoire estime est acceptable :
  les routes statique, Newmark et harmonique publient l'estimation et refusent
  le direct lorsque `enforce_direct_memory_budget` est active ;
- [x] choisir `CG` avec preconditionneur seulement pour un systeme reduit
  symetrique defini positif, et verifier cette hypothese dans l'audit : une
  Cholesky bornee prouve les petits systemes et `assume_spd` reste une
  declaration explicite et tracee pour les grands systemes, jamais deduite de
  la seule diagonale positive ;
- [x] choisir `MINRES` pour les systemes symetriques indefinis et
  `GMRES`/`BiCGSTAB` uniquement lorsqu'une non-symetrie est documentee : la
  politique lineaire refuse CG sans preuve SPD bornee ou declaration explicite
  `assume_spd`, et recommande MINRES pour un systeme symetrique non prouve SPD ;
- [x] imposer `PETSc KSP + GAMG` comme trajectoire par defaut pour le TET4
  statique distribue : `LargeLinearStaticSolver` utilise `KSP CG + GAMG` par
  defaut; la comparaison Hypre/BoomerAMG reste une optimisation conditionnelle,
  a ne mener que si une topologie ou un conditionnement la justifie ;
- [x] estimer avant calcul le nombre de coefficients et la memoire de
  factorisation directe. Emettre un avertissement ou refuser LU au-dela d'un
  budget configure ; la memoire d'assemblage et le cout de sortie grand modele
  restent traites par le chemin HDF5/PETSc ;
- [x] enregistrer pour la statique lineaire standard le solveur demande et
  finalement utilise, sa justification, preconditionneur, tolerances,
  iterations, residu, absence de repli, temps et estimation memoire dans les
  sorties JSON et l'audit ; les diagnostics PETSc restent portes par le mode
  grand modele et les routes Newmark/harmonique seront alignees avant de
  revendiquer une dynamique grand modele ;
- [x] comparer LU, CG, MINRES, GMRES et BiCGSTAB a la voie directe sur quatre
  systemes controles (`VNV-LINEAR-SOLVERS-001`), dont deux matrices de `32` DDL
  de type chaine; publier ecart de solution, residu relatif, iterations,
  conditionnement 2-norme diagnostique, temps indicatif et manifeste V&V.
  Le benchmark poutre confirme separement l'accord sur un systeme EF
  symetrique; le conditionnement et le temps ne sont pas des criteres de
  qualification ;
- [x] aligner les diagnostics des matrices effectives Newmark et harmoniques :
  contrat reel/complexe, symetrie, estimation LU, budget optionnel, methode
  effectivement utilisee, reutilisation Newmark et temps par frequence sont
  exposes dans le resultat JSON et l'audit. La dynamique grand modele reste un
  chantier distinct, sans promesse implicite de passage a l'echelle ;
- [x] comparer PETSc aux voies SciPy sur les modeles TET4 distribues, avec
  accord de solution et residu avant toute conclusion de performance :
  `VNV-LARGE-PETSC-SCIPY-001` resout le meme bloc HDF5 par SciPy et PETSc/GAMG
  sur deux rangs Docker, avec un ecart de deplacement `1,02e-12` et des residus
  sous `1e-7`. Cette preuve ne se substitue pas aux campagnes de performance 1M+ ;
- [ ] etendre cette politique aux matrices effectives Newmark et harmonique
  distribuees, avec post-traitement resume ou chunke avant de revendiquer une
  dynamique grand modele.

Critere de sortie : aucun calcul ne selectionne LU par defaut sans estimation
de ressources et toute selection automatique reste explicable, reproductible
et visible dans le dossier de preuve.

## P5 - Non-lineaire et TET10

### P5.1 - Loi J2 en petites deformations

- [x] conserver les tests unitaires de tangente algorithmique par differences
  finies en regime plastique, y compris depuis un etat commite ;
- [x] creer `VNV-J2-MATERIAL-CYCLIC-001` avec rapport JSON/Markdown et chemins
  proportionnels, non proportionnels, decharge et recharge ;
- [x] verifier plusieurs directions de chargement elastiques et plastiques avec
  une erreur relative de tangente inferieure a `1e-6` ;
- [x] verifier la condition de plasticite, la croissance monotone de la
  deformation plastique cumulee et une dissipation plastique non negative ;
- [x] couvrir plasticite parfaite (`H=0`) et ecrouissage isotrope (`H>0`) ;
- [x] ajouter un essai uniaxial material-point compare a la loi bilineaire et
  publier les courbes contrainte-deformation et variable interne ;
- [x] comparer les quatre increments monotones a une reference publiee de
  plaque elastoplastique sous charge uniforme; conserver les increments
  inverses hors comparaison car la reference utilise un ecrouissage
  cinematique ;
- [x] executer la meme histoire monotone avec CalculiX `2.20` isotrope sur un
  C3D8 homogene; accord exact en `S11/PEEQ`, ecart de deformation `1,76e-7`
  relatif et ecart d'energie `0,1317 %` sous la limite `0,5 %`
  (`VNV-J2-CALCULIX-ISOTROPIC-002`) ;
- [x] ajouter Code_Aster `18.1.0` `VMIS_ISOT_LINE` comme seconde
  implementation externe dans `VNV-J2-CODEASTER-VMIS-ISOT-LINE-004` :
  contrainte axiale, deformation plastique equivalente, contraintes
  laterales et homogeneite du patch affine passent a mieux que `4,34e-16`
  relatif. La conversion entre module d'ecrouissage plastique QF_solver et
  pente totale `D_SIGM_EPSI=E H/(E+H)` est explicite et testee ;
- [x] renforcer la campagne TET4 multi-elements monotone avec equilibre,
  deformation plastique analytique et independance sur `3/6/12` increments ;
- [x] ajouter `VNV-J2-TET4-CYCLIC-003` sur `140` TET4 avec cycle d'amplitude
  croissante `+300/-360/+420 MPa`; ecart oracle `5,02e-11`, croissance
  plastique prouvee aux deux inversions et residu maximal `2,41e-8`.
- [x] ajouter `VNV-J2-TET10-CYCLIC-001` sur `140` TET10 droits, quatre points
  de Hammer et un cycle commite charge/decharge/recharge; l'erreur de chemin
  plastique est `8,73e-10`, l'erreur de contrainte `5,96e-11` et le residu
  maximal `4,14e-9`.
- [x] executer `VNV-TET10-J2-CODEASTER-STRUCTURAL-025` sur le meme maillage
  TET10/TETRA10 avec six facteurs monotones : ecart UX final `0,03175 %`,
  PEEQ RMS `0,55084 %` et residu QF maximal `7,40079e-11`.
- [x] enregistrer l'Owner review du `2026-08-09` : acceptation bornee pour
  usage interne experimental, sans hausse de maturite generale.
- [x] lancer `VNV-TET10-J2-CODEASTER-COMPLEX-026` sur un support en L :
  `1 039` noeuds, `457` TET10, charges combinees `FX=3 MN` et `FY=-6 MN`,
  ecart RMS deplacement `0,01245 %`, ecart final `0,00227 %`, PEEQ RMS
  `1,84443 %`, ratio petites deformations `1,95357 %` et residu maximal
  `1,97226e-9` ; la campagne est `PASS_EXTERNAL_CORRELATION`, Owner review
  a faire. Le raffinement dédié `0,32 -> 0,24 -> 0,16` ramène le PEEQ RMS
  à `0,8867 %` au niveau fin, ce qui ferme le gate technique à 1 % pour ce
  cas sans promotion automatique du scope.

### P5.2 - Robustesse du solveur non lineaire

- [x] prouver que les etats internes ne sont commites qu'apres convergence et
  qu'un increment rejete restaure exactement le dernier etat accepte ;
- [x] tester reduction et croissance adaptatives du pas, nombre maximal de
  coupures et diagnostic explicite de non-convergence; les rejets sont exposes
  dans `solver.rejection_log` et les parametres incoherents sont refuses ;
- [x] comparer Newton complet, Newton modifie et line-search sur le meme cycle
  `VNV-J2-NONLINEAR-METHODS-004`: Newton complet et Armijo convergent en `33`
  iterations et concordent sur la reponse axiale; le champ transverse faiblement
  retenu reste sensible a la methode. Newton modifie ne converge pas au premier
  dechargement et reste non recommande pour les inversions plastiques ;
- [x] corriger la line-search sur inversion plastique multi-elements : le
  residu des passages par charge nulle est normalise par la charge de reference;
  la campagne `VNV-J2-TET4-CYCLIC-003` passe avec Armijo (erreur chemin
  plastique `3,70e-13`, residu relatif maximal `1,60e-12`) ;
- [x] ajouter checkpoint/reprise NPZ atomique des deplacements, du facteur de
  charge et des variables internes avec empreinte du modele; identite calcul
  continu/reprise prouvee sur un cycle J2. Adaptatif et arc-length restent
  explicitement hors de ce premier contrat ;
- [x] tracer par increment iterations, norme du residu, corrections, travaux
  interne/externe trapezoidaux, desequilibre de travail, coupures de pas et
  statut de commit; ne pas assimiler ce diagnostic a une decomposition exacte
  energie elastique/dissipation plastique ;
- [x] verifier la reproductibilite sur `12/24/48` increments du meme cycle
  dans `VNV-J2-STEP-SENSITIVITY-005`, avec comparaison aux retournements,
  reponse finale, travaux et courbe PNG; sensibilite d'etat `9,49e-11` et
  convergence du travail `24 -> 48` increments inferieure a `2 %`.

### P5.3 - Non-linearite geometrique

- [x] figer une formulation totale lagrangienne TET4 avec Green-Lagrange,
  Piola-Kirchhoff 2 et Saint-Venant-Kirchhoff, distincte du J2 petites
  deformations; domaine et limites documentes ;
- [x] implementer le noyau de verification objectif, sa force interne, son
  energie et sa tangente geometrique/materielle consistante sans modifier le
  chemin petites deformations qualifie ;
- [x] verifier l'assemblage sur `192/648/1536/5184/12288/24000` TET4 : patch affine,
  rotation rigide, Newton, jacobien courant et grande fleche; invariants
  `PASS`, variation de fleche reduite de `19,09 %` a `3,81 %` ;
- [x] enregistrer la validation mecanique interne de Quentin Farinazzo en
  `self_review`, avec statut `engineering_internal_validated_with_recommendations`;
  le perimetre reste `research` et ne constitue pas une revue independante ;
- [x] integrer un premier chemin public `geometric_nonlinear_static` au routeur,
  aux sorties JSON et a l'API/CLI, borne a TET4 homogene, charges nodales mortes,
  Newton complet, minimum `6` et defaut `10` increments; maturite `research` ;
- [x] verifier rotation rigide sans contrainte, traction avec grande rotation,
  poutre en grand deplacement et flambement d'Euler ; les preuves sont reunies
  dans les campagnes `001` a `010` et la revue structurelle V2 ;
- [x] ajouter une reference d'elastica d'Euler sous charge morte; fleche
  `-0,60013`, ecart fin `6,91 %`, reference informative hors effets 3D ;
- [x] demontrer par `3/6/10/12/24` increments que `6/10/12/24` donnent le meme
  equilibre a `8,10e-16` relatif; minimum technique `6`, recommandation et
  valeur par defaut `10` increments ;
- [x] correler les six maillages avec CalculiX `2.20` C3D4 dans Docker;
  ecart maximal de fleche `1,86e-7` relatif ;
- [x] mettre en cache les gradients/volumes et vectoriser force et tangente;
  les trois anciens niveaux passent d'environ `198,7 s` a `6,90 s` ;
- [x] executer `VNV-TET4-TL-STRESS-005` : patch affine fini PK2/Cauchy/energie
  sur quatre maillages, erreur maximale inferieure a `1e-11` ;
- [x] executer `VNV-TET4-TL-BUCKLING-EULER-006` : tangente precontrainte et
  charge critique analytique d'Euler; ecart fin `5,87 %`, variation finale
  `3,31 %`; correlation externe encore recommandee ;
- [x] executer le point d'acceptation `64x16x16`, soit `98 304` TET4 et
  `56 355` DDL : erreur Euler reduite a `1,896 %`, charge QF `818,415`,
  CalculiX `818,696` et ecart meme maillage `0,0343 %` ;
- [x] executer `VNV-TET4-TL-POSTBUCKLING-007` : trois colonnes imparfaites,
  `120` pas arc-length creux par chemin, residu maximal `9,53e-9` et
  `det(F)` minimal `0,9832` ;
- [x] produire pour ces trois benchmarks les rapports Markdown, courbes,
  deformees PNG, resultats normalises et manifestes SHA-256 avant la nouvelle
  revue mecanique ;
- [x] correler contrainte finie et flambement propre sur maillage identique avec
  CalculiX `2.20` C3D4: erreur Cauchy `1,17e-7`, ecart Pcr fin `0,035 %` ;
- [x] correler avec Code_Aster `18.1.0` TETRA4: erreur PK2 `8,54e-5` et
  ecart maximal de branche imparfaite jusqu'a `0,8 Pcr` de `1,69e-9`; documenter
  `RIGI_GEOM` solide 3D comme non applicable au flambement propre meme formulation ;
- [x] revue structurelle V2 acceptee avec recommandations par Quentin Farinazzo
  le `2026-07-18`: push-forward Cauchy, erreur Euler h5, trois amplitudes
  d'imperfection, arc-length et correlations CalculiX/Code_Aster ;
- [x] borner la validation interne aux charges nodales mortes et au domaine
  documente ; pression suiveuse, contact, plasticite en deformation finie,
  endommagement et qualification externe restent explicitement hors scope.

### P5.4 - Consolidation TET10

- [x] qualifier au niveau elementaire les Jacobiennes variables et les
  quadratures sur elements droits, courbes, distordus et proches des limites
  de qualite dans `VNV-TET10-GEOMETRY-QUADRATURE-011`; regle automatique
  Hammer-4/Duffy-64, erreur courbe `7,51e-7` et rejet du Jacobien negatif ;
- [x] completer le patch affine et la convergence structurelle en `h` dans
  `VNV-TET10-STRUCTURAL-CONVERGENCE-012`, avec quatre maillages TET4/TET10 par
  probleme : erreur TET10 `5,76e-15` en traction, `1,179 %` en flexion et
  `0,00250 %` sur la rotation de torsion; erreur de contrainte de torsion
  `0,991 %` et equilibre de charge `2,27e-16` ;
- [x] verifier masse, modal, chargements de face quadratiques et recuperation
  nodale dans `VNV-TET10-MASS-MODAL-LOADS-013` : masse courbe a `3,57e-16`,
  resultante/moment de pression a `9,10e-18`/`4,71e-16`, contrainte recuperee
  a `8,72e-16` et premiere paire modale a `0,434 %` de la theorie ;
- [x] correler le cas de torsion courbe sur le meme maillage avec CalculiX
  `2.20` C3D10 dans `VNV-TET10-CALCULIX-C3D10-014` : ecart relatif du champ
  complet `6,84e-5` et de la rotation terminale `6,45e-5`, sous `1e-4` ;
- [x] caracteriser la flexion quasi-incompressible dans
  `VNV-TET10-NEAR-INCOMPRESSIBLE-015` sur trois maillages et quatre valeurs de
  `nu` : a `nu=0,499`, compliance TET10 `94,83 %` contre `8,48 %` pour le
  temoin TET4; conserver l'incompressibilite exacte hors scope ;
- [x] revue mecanique TET10 lineaire acceptee avec recommandations par Quentin
  Farinazzo le `2026-07-18`, en `self_review`, pour le domaine borne ;
- [x] conserver J2, grandes transformations, incompressibilite exacte et TET10
  avance hors du scope accepte jusqu'a campagnes reproductibles dediees ;
- [x] executer `REC-TET10-001` sur une piece a geometrie rentrante TET10 avec
  chargements combines et correlation Code_Aster : deux niveaux `h=0,32` et
  `h=0,22`, soit `457` puis `1 031` elements, passent avec un increment de
  deplacement de `0,1885 %` et de PEEQ de `5,13 %`. L'etude
  `VNV-TET10-J2-CODEASTER-COMPLEX-REFINEMENT-027` est archivee; le statut
  reste `experimental` jusqu'a Owner review et deux niveaux ne constituent
  pas encore une convergence asymptotique.
- [ ] en toute fin du developpement, executer `REC-TET10-002` sur des pieces et
  assemblages beaucoup plus complexes, des maillages importants, des charges
  combinees et plusieurs codes de reference, notamment Conastin, CalculiX et
  Code_Aster, avant acceptation totale ou qualification externe.

Critere de sortie : loi J2 material-point et structure multi-elements prouvees,
gestion transactionnelle des etats internes testee, puis TET10 consolide. La
non-linearite geometrique constitue un scope distinct et ne peut pas etre
deduite de la seule convergence du solveur petites deformations.

## P6 - Composites et stratifies (socle constitutif demarre)

### P6.1 - Conventions et materiaux orthotropes

- [x] figer les axes materiau `1-2-3`, les angles de pli, le sens positif et la
  transformation entre repere materiau, repere element et repere global ;
- [x] implementer une couche orthotrope elastique avec constantes reciproques,
  controles de positivite et matrice reduite en contraintes planes ;
- [x] verifier analytiquement les matrices `Q` et `Qbar` pour `0`, `90` et
  `+/-45 deg`, ainsi que l'invariance par rotation.

### P6.2 - Theorie classique des stratifies

- [x] definir la sequence d'empilement, les interfaces en epaisseur, les
  matrices `A/B/D`, les resultantes membrane/flexion et les couplages ;
- [x] prendre en charge stratifies symetriques, equilibres et non symetriques,
  puis les chargements thermiques seulement dans un scope ulterieur ;
- [x] comparer `A/B/D` a des solutions analytiques et imposer `B=0` pour les
  empilements symetriques dans les tests de verification.

### P6.3 - MITC4 multicouche

- [x] integrer les contributions pli par pli sans modifier le MITC4 isotrope
  qualifie, avec resultats contraintes/deformations aux faces de chaque pli ;
- [x] verifier le cisaillement transverse, l'orientation sur coques courbes,
  le couplage membrane-flexion et la sensibilite au shear locking ;
- [x] conserver l'element composite au statut `experimental` jusqu'aux patch
  tests, etudes de convergence et correlations externes.

### P6.4 - Criteres et V&V composites

- [x] introduire d'abord contrainte/deformation maximale, Tsai-Hill et Tsai-Wu;
  garder Hashin, Puck et l'endommagement progressif hors premier perimetre ;
- [x] construire des cas analytiques `[0]`, `[0/90]s`, `[+45/-45]s`, traction
  hors axe et plaque stratifiee en flexion ;
- [x] publier la convergence structurelle MITC4 multicouche sur membrane,
  flexion croisee et flexion angle-ply dans `VNV-COMP-STRUCTURAL-CONVERGENCE-002`;
- [x] correler le panneau `[0/90]s` avec CalculiX `2.20` S8R composite dans
  `VNV-COMP-CALCULIX-S8R-003`: ecart fin de fleche `0,0310 %`;
- [x] completer par le benchmark NAFEMS R0031/1 et une correlation Code_Aster
  `18.1.0` DST/DSQ dans `VNV-COMP-NAFEMS-R0031-CODEASTER-004`: ecart fin
  QF/NAFEMS `0,458 %`, Code_Aster/NAFEMS `0,710 %`, QF/Code_Aster `0,251 %`;
  cinq maillages jusqu'a `160x32`, increments finaux `0,0967 %` et `0,0920 %`;
- [x] realiser la revue mecanique composite distincte; Quentin Farinazzo a
  enregistre le `2026-07-26` une acceptation engineering interne avec
  recommandations, en mode `self_review` et sans certification revendiquee ;
- [x] traiter la recommandation sur les contraintes par pli hors singularites
  dans `VNV-COMP-PLY-STRESS-005` : erreurs L2 fines de `0,00389 %` en
  membrane, `0,254 %` en flexion, `0,0379 %` en charge combinee et `1,056 %`
  sur le maillage interieur distordu de `15 %`.
- [x] implementer `reference_direction` projete sur chaque facette et executer
  `VNV-COMP-CURVED-ASSEMBLY-006` : erreur angulaire `1,4e-14 deg`, increments
  finaux `1,063 %` sur cylindre et `0,875 %` sur assemblage plie; le cas a
  facettes gauches reste correctement refuse par le profil qualifiable.
- [x] correler la coque cylindrique `[0/90]s` avec CalculiX `2.20` S8R dans
  `VNV-COMP-CURVED-CALCULIX-S8R-007` : ecart vectoriel fin `0,225 %`,
  increment final QF `0,245 %` et CalculiX `0,0376 %`.
- [x] fermer `ANOM-COMP-CURVED-ORIENTATION-001` dans
  `VNV-COMP-CURVED-ORIENTATION-008` : orientations CalculiX tangentielles par
  rangee et par pli, empilement `[0/+45/-45/90]`, cinq maillages jusqu'a
  `96x48`; ecart vectoriel fin `1,839 %` sous le seuil externe borne de `3 %`.
- [x] ajouter `VNV-COMP-CONICAL-CUTOUT-009` : panneau annulaire conique
  stratifie `[0/+45/-45/90]`, ouverture centrale libre, projection locale des
  axes par facette, resultats par pli, VTU/PNG et convergence sur trois
  maillages. La fleche sonde se stabilise a `0,0588 %`; cette evidence reste
  interne et `experimental` jusqu'a correlation externe dediee ;
- [x] correler les deplacements du panneau composite conique ajoure avec
  CalculiX S8R COMPOSITE; la comparaison de contraintes par pli hors bord
  libre reste une etape distincte ouverte ;
- [x] executer l'essai exploratoire
  `VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-010` avec une charge nodale de bord
  identique : statut `WARNING`, ecart vectoriel `29,17 % -> 10,10 %` mais
  sonde encore trop sensible au bord libre. Ne pas utiliser ce resultat comme
  validation; remplacer la charge par une sollicitation reguliere et comparer
  les contraintes par pli sur un chemin a distance fixee ;
- [x] executer `VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-011` avec le vecteur de
  pression coherent QF transfere aux noeuds de coin communs : ecart de sonde
  fin `0,728 %`, ecart vectoriel fin `1,608 %`, increments QF/CalculiX
  `0,0588 %`/`0,260 %`. Cette correlation cinematique reguliere passe sous le
  seuil borne de `3 %`; elle ne valide ni la quadrature de pression native
  CalculiX ni les contraintes par pli au bord libre ;
- [x] ajouter `VNV-COMP-CONICAL-CUTOUT-PLY-STRESS-CALCULIX-S8R-012` :
  extraction des contraintes tangentielles par pli sur la couronne
  `0,38 <= eta <= 0,62`, a distance normalisee de l'ouverture, avec
  comparaison CalculiX S8R dans les axes materiau. L'ecart L2 fin est
  `0,298 %`, et les increments finaux QF/CalculiX sont `0,611 %`/`0,480 %` ;
  les pics de bord libre et `S13` restent hors critere ;
- [ ] traiter `REC-COMP-CURVED-MODELFORM-001` avec un oracle coque de meme
  ordre ou une reference analytique de stratifie courbe; ne pas generaliser
  le seuil croise MITC4/S8R de `3 %`.

La campagne `VNV-COMP-ANALYTIC-001` passe six controles sous `1e-12`, la
campagne structurelle `002` passe, et les correlations CalculiX `003` et
NAFEMS/Code_Aster `004` passent. La campagne de contraintes par pli `005`
passe egalement. La correlation externe courbe `007` passe dans son domaine
axial borne. La campagne `008` ferme aussi l'anomalie d'orientation oblique,
avec une recommandation sur l'ecart de formulation MITC4/S8R. Le scope reste
`experimental` jusqu'a l'ajout d'assemblages industriels complexes;
`S13` interlaminaire reste hors acceptation.

### P6.5 - Solides orthotropes TET4 et TET10

- [x] rediger la specification `orthotropic_3d`, ses constantes reciproques,
  les orientations materiau, sorties et limites de premiere version ;
- [x] implementer la loi 3D et sa transformation globale sans modifier le
  chemin isotrope qualifie ;
- [x] integrer la loi au TET4 puis au TET10, avec resultats dans les axes
  globaux et materiau ;
- [x] executer les huit preuves `SPEC-COMP-SOLID-001..008`: les preuves
  `001..005` passent dans `VNV-ORTHOTROPIC-SOLID-KERNEL-001`; la correlation
  externe `007` passe sur une eprouvette trouee et une equerre dans
  `VNV-ORTHOTROPIC-SOLID-EXTERNAL-002`; la convergence `006` passe dans la
  campagne `003` avec reserve de precision TET4; la non-regression isotrope
  `008` passe dans la campagne `004` ;
- [x] preparer puis signer la revue mecanique des solides orthotropes le
  `2026-07-22` : `docs/verification/revue_solides_orthotropes.md` et
  `qualification/reviews/orthotropic_solids_2026-07-22.json` ;
- [x] etendre la convergence TET4 a `4 951` et `9 820` elements : l'ecart de
  fleche descend monotoniquement a `16,83 %` puis `11,75 %` ;
- [x] accepter les conventions d'orientation, les contraintes en axes
  materiau/global, les patchs affines, l'objectivite et les correlations
  externes pour le domaine statique lineaire borne ;
- [x] enregistrer le statut
  `engineering_internal_validated_with_recommendations`, sans revendication de
  certification externe ;
- [x] implementer le champ `cylindrical_tangent` pour TET4/TET10 standard :
  repere circonferentiel/axial/radial evalue au centroide, valide par tests de
  rotation de repere et d'assemblage global ;
- [ ] qualifier ce champ sur une structure cylindrique ou conique avec
  raffinement et oracle externe; les fibres a courbure arbitraire, les champs
  interpoles aux points de Gauss et le grand modele restent hors scope ;
- [x] implementer la campagne reelle de contraintes proches des singularites avec
  raffinement, chemins a distance controlee, moyennes regularisees et
  correlations Code_Aster ;
- [x] executer la campagne controlee avec deux raffinements supplementaires et
  ajouter la seconde correlation CalculiX sur les memes chemins et moyennes de
  bande ; QF_solver/Code_Aster est a la precision machine et l'ecart maximal
  QF_solver/CalculiX vaut `0,000193 %`.
- [x] poursuivre `VNV-ORTHOTROPIC-SINGULAR-STRESS-005` avec deux maillages
  encore plus fins et une recuperation compacte quadratique ponderee par les
  volumes : les huit niveaux atteignent `86 469` TET4 pour le trou et
  `237 358` TET4 pour l'equerre. Les increments finaux chemin/bande valent
  `1,342 % / 0,125 %` et `1,625 % / 3,420 %`, sous le seuil `5 %`.
  Code_Aster sur maillage identique passe a mieux que `5,4e-9 %`. La bande
  nodale CalculiX de l'equerre differe encore de `6,357 %` car son extrapolation
  n'utilise pas le meme operateur de recuperation; elle reste un diagnostic
  `WARNING` non bloquant, trace dans le digest controle.
- [x] traiter la demande Owner de deux pieces supplementaires avec
  `VNV-ORTHOTROPIC-ADDITIONAL-STRESS-006` : encoche arrondie et double trou
  sur cinq raffinements, jusqu'a `55 935` TET4. Les increments finaux
  chemin/bande valent `0,611 % / 0,868 %` et `4,404 % / 0,556 %`;
  les cartes `S11` QF_solver/Code_Aster sont publiees. Quentin Farinazzo a
  enregistre `accepted_with_recommendations` le `2026-07-29`, avec maintien
  des chemins, bandes et exclusions des pics ponctuels singuliers ;
- [x] definir le protocole de surete `VNV-ORTHOTROPIC-SINGULAR-STRESS-005` :
  classification des pics finis ou singuliers, chemins a distance fixe,
  moyennes de bande, quatre maillages et correlation analytique/Code_Aster/
  CalculiX ;
- [x] brancher l'orthotropie lineaire sur le modal TET4/TET10 et verifier
  frequences, residus propres et orthogonalite par la limite isotrope ;
- [x] brancher l'orthotropie lineaire sur Newmark TET4/TET10 et verifier
  champs, residus et energie par la limite isotrope ;
- [x] etendre le grand modele statique TET4 aux materiaux `orthotropic_3d` et
  `composite_orthotropic_3d` dans les backends SciPy, PETSc et matrix-free,
  ainsi que dans l'audit et le post-traitement ;
- [x] conserver hors scope dommage, delaminage, plasticite anisotrope et
  grandes deformations ;
  - [x] executer un benchmark modal orthotrope avec convergence de `24` a
    `96` TET4 et correlation Code_Aster `18.1.0` `3D/TETRA4` sur meme
    maillage : erreur theorique fine `0,0309 %`, ecart modal externe
    `2,00e-12 %` (`VNV-ORTHOTROPIC-MODAL-NEWMARK-010`) ;
  - [x] executer une convergence temporelle Newmark orthotrope de `2 ms` a
    `62,5 us` et une correlation transitoire Code_Aster sur `0,25 ms` : RMS
    normalise `9,00e-13 %`, ecart entre les deux pas QF_solver les plus fins
    `2,89 %` sous le seuil de stabilisation `5 %`
    (`VNV-ORTHOTROPIC-MODAL-NEWMARK-010`) ;
- [x] executer PETSc/MPI sur le modele TET4 isotrope de qualification grand
  modele : `1 029 000` DDL, audit large et verification file-backed `PASS`;
  cette preuve ne doit pas etre attribuee a l'orthotropie.
- [x] produire la preuve orthotrope grand-modele bornee
  `VNV-ORTHOTROPIC-LARGE-STATIC-008` : `576` TET4, `540` DDL, ecart de
  deplacement `1,06e-11` entre chemin large SciPy et solveur standard, ecart
  `1,38e-12` entre matrix-free et assemble, et erreur energie/travail
  `4,59e-15`. Le statut reste `experimental` et la preuve ne remplace pas
  une correlation Code_Aster.

La specification controlee est dans
`qualification/specifications/composite_solids.json`; le statut est
`engineering_internal_validated_with_recommendations`. Le dossier de passage en revue est
centralise dans `docs/verification/dossier_validation_owner.md`.

Critere d'entree : ne commencer P6 qu'apres stabilisation de P5.2. Critere de
sortie initial : calcul elastique lineaire multicouche reproductible, conventions
figees, resultats par pli et preuves analytiques; aucune revendication de rupture
ou de dommage qualifiee a ce stade.

## P7 - Fermeture fonctionnelle de la V1

### P7.1 - BEAM2

- [x] definir un element poutre 3D de Timoshenko a deux noeuds et six DDL par
  noeud : `UX`, `UY`, `UZ`, `RX`, `RY`, `RZ` ;
- [x] figer le repere local, l'orientation de section et les signes de
  `N`, `Vy`, `Vz`, `T`, `My`, `Mz` ;
- [x] accepter les proprietes `A`, `Iy`, `Iz`, `J`, `E`, `G`, densite et
  facteurs de correction de cisaillement ;
- [x] implementer rigidite, masse coherente, chargements nodaux et repartis ;
  la masse concentree est traitee separement en P7.2 ;
- [x] ajouter traction, torsion, flexion dans les deux plans, poutre epaisse,
  modes rigides, modal et convergence vers Euler-Bernoulli ;
- [x] comparer aux solutions analytiques et a Code_Aster `18.1.0` Docker sur
  une section generale identique : axial, torsion et flexion elancee passent
  sous `1 %` dans `VNV-BEAM2-CODEASTER-POUDE-001`; le cisaillement epais et la
  dynamique externe restent ouverts ;
- [x] corriger puis verifier la masse BEAM2 par correlation modale externe :
  la masse Hermite transverse avec inertie rotatoire Timoshenko est comparee a
  Code_Aster `18.1.0` `POU_D_E` dans
  `VNV-BEAM2-MODAL-CODEASTER-POUDE-002`; les six modes du porte-a-faux elance
  passent sous `1 %`, avec un ecart maximal observe de `0,0265 %`. La
  dynamique de poutre epaisse, l'amortissement et les assemblages restent
  ouverts ;
- [x] documenter formulation, limites, demonstrations et references dans le
  catalogue public de la librairie.

### P7.2 - Ressorts et masses concentrees

- [x] ajouter des ressorts translationnels et rotationnels entre un noeud et
  le sol ou entre deux noeuds ;
- [x] autoriser une raideur scalaire par direction et une matrice locale
  symetrique validee ;
- [x] ajouter des masses nodales avec masse translationnelle, centre de masse
  documente et tenseur d'inertie symetrique positif ;
- [x] verifier energie elastique, forces opposees, masse totale, invariance par
  rotation et frequences analytiques masse-ressort ;
- [x] correler le SDOF ressort-masse au sol avec Code_Aster `18.1.0` `DIS_T`
  dans `VNV-DISCRETE-CODEASTER-SDOF-001` : la fleche statique passe a
  `1,39e-14 %` et la premiere frequence est identique a la precision machine.
  Les inerties excentrees, rotations et assemblages restent ouverts ;
- [x] refuser les raideurs negatives non explicitement classees comme
  experimentales et les inerties non physiques.

### P7.3 - MPC et RBE

- [x] definir une contrainte lineaire generale
  `sum(a_i * q_i) = b` avec validation des DDL et detection des conflits ;
- [x] appliquer les MPC par elimination creuse comme voie normale et conserver
  une formulation multiplicateurs de Lagrange pour verification ;
- [x] ajouter une liaison `RBE2` rigide avec translations et rotations du
  noeud maitre, offsets compris ;
- [x] ajouter une liaison de distribution `RBE3` sans rigidite artificielle,
  avec projection rigide ponderee, conservation du torseur et mode scalaire
  `weighted` explicitement limite ;
- [x] detecter contraintes redondantes, cycles et conflits ; les mecanismes
  restent signales par les diagnostics de rang existants ;
- [x] verifier mouvement de corps rigide, reactions, energie et comparaison
  matrice complete/systeme condense ; le patch sur structure EF assemblee est
  couvert par la future campagne externe P7.6 ;
- [x] garder les noms RBE comme analogies fonctionnelles documentees, sans
  revendiquer une compatibilite implicite avec un format proprietaire.

### P7.4 - Contact sans frottement

- [x] limiter le premier scope aux petites transformations, `linear_static`
  et au contact unilateral noeud-triangle a normale initiale figee ;
- [x] definir gap, normale, signe de pression et convention maitre/esclave ;
- [x] implementer le contact noeud-surface par active-set avec multiplicateurs
  de Lagrange exacts, sans penalite cachee ;
- [x] verifier les conditions de Kuhn-Tucker : gap positif, pression
  compressive et complementarite, ainsi que l'equilibre global ;
- [x] ajouter les tests de separation sans traction, fermeture sous
  compression et rejet des DDL tangents non stabilises par la matrice ;
- [x] refuser projection hors triangle, triangle degenere, methode iterative,
  MPC/RBE, normale invalide et non-convergence de l'active-set ;
- [x] verifier la convergence structurelle TET4 de la reaction normale sur
  quatre maillages (`VNV-CONTACT-TET4-STRUCTURAL-001`) ;
- [x] correler ouverture/fermeture normale avec Code_Aster `18.1.0` dans
  Docker epingle (`VNV-CONTACT-CODEASTER-LIAISON-UNIL-001`) ;
- [x] classer le contact sans frottement borne `engineering_ready_bounded`
  apres Owner review et demonstration de robustesse de l'active-set sur des
  faces EF deformables. Les trois
  orientations orthogonales d'un triangle maitre, un coin a deux contacts
  actifs et un triangle a trois noeuds maitres elastiques sont maintenant
  couverts. `VNV-CONTACT-DEFORMABLE-MASTER-003` confirme le transfert
  barycentrique vers des maitres mobiles. `VNV-CONTACT-TET4-MASTER-FACE-004`
  ajoute une face frontiere TET4 deformable et confronte la reponse couplee a
  une compliance EF obtenue independamment. Les extensions surface-surface,
  grand glissement et changement topologique restent `experimental`.
- [x] accepter une liste `master_faces` de triangles explicites et selectionner
  une seule facette compatible dans la geometrie initiale
  (`VNV-CONTACT-MASTER-SURFACE-005`). Cette extension reste bornee : aucun
  changement de facette, de normale ou recherche apres deformation n'est
  revendique ;
- [x] ajouter `contact_search_mode="updated"` pour une iteration bornee sans
  frottement qui relocalise la facette et la normale en petites translations ;
  `VNV-CONTACT-MASTER-SURFACE-005` verifie une commutation de la face 0 a la
  face 1, d'abord sur plan puis sur deux facettes pliees avec normale
  analytique. Un patch esclave discret a trois noeuds commute aussi
  coheremment vers la facette pliee, base de comparaison surface Code_Aster.
  Grand glissement et contact surface-surface restent ouverts ;
- [x] rendre les caps d'iterations et la tolerance de recherche strictement
  verifiables par `check-mesh` et a l'execution : les valeurs non finies,
  non entieres ou non positives sont refusees, sans troncature silencieuse ;
- [x] correler l'etat actif de cette face TET4 avec Code_Aster `18.1.0`
  `3D/TETRA4` et `LIAISON_DDL` (`VNV-CONTACT-CODEASTER-TET4-MASTER-004`),
  en distinguant cette cinematique active de la detection `LIAISON_UNIL` deja
  correlee ;
- [x] correler la normale finale d'une facette pliee avec Code_Aster `18.1.0`
  Docker et `LIAISON_DDL` (`VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006`) : les
  trois deplacements sont a la precision machine. Cette preuve impose la
  facette finale et ne revendique pas la detection externe de commutation ;
- [x] comparer la commutation de facette a Code_Aster `18.1.0` sans ensemble
  actif impose : `VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007` utilise
  `DEFI_CONTACT/CONTINUE` autonome sur une surface pliee et retrouve le
  deplacement moyen du patch QF_solver a `0,1157 %` (seuil `1 %`). La
  correspondance paire-a-paire des deux discretisations reste explicitement
  hors preuve ;
- [x] preparer l'Owner review sans la signer :
  `qualification/reviews/contact_v1_linear_static_bounded_pending.json`
  porte les preuves, limites et recommandations; la decision et la signature
  restent volontairement `pending` et `null` ;
- [x] traiter la demande Owner review `more_evidence_required` du `2026-07-29`
  avec `VNV-CONTACT-ADDITIONAL-MODELS-008` : coin a deux normales, rampe
  facettisee a trois esclaves et bloc deformable de `576` TET4 a deux contacts
  passent ;
- [x] comparer ces trois modeles sur dix paliers avec Code_Aster 18.1.0 :
  coin et rampe sont confondus, la branche fermee du bloc TET4 est confondue
  a partir de `0,2`, et CalculiX confirme QF_solver avant contact a
  `4,78e-5 %`. Le raffinement a `768` TET4 abaisse l'ecart de transition
  QF_solver/Code_Aster de `5,2565 %` a `4,3400 %`, sous le seuil `5 %` ;
- [x] confirmer ce passage avec un calcul proche de 10 000 elements :
  `VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010` contient `9 984` TET4 et
  donne un ecart maximal QF_solver/Code_Aster de `3,3029e-12 %` sur toute
  la courbe, avec un jeu final inferieur a `1e-15 m` ;
- [x] enregistrer l'Owner review du scope
  `contact-v1-linear-static-bounded` en
  `accepted_for_bounded_engineering_use`, datee et signee le `2026-07-29`
  dans `qualification/reviews/contact_v1_linear_static_bounded_2026-07-29.json` ;
- [ ] demontrer une surface EF generalisee au-dela du patch borne et etendre
  la recherche mise a jour au grand glissement sans frottement.

### P7.5 - Contact avec frottement

- [x] etendre le contact normal par une loi de Coulomb regularisee, limitee
  aux petites transformations et au contact noeud-triangle ;
- [x] distinguer clairement adhesion, glissement et retour sur le cone de
  frottement `||t_t|| <= mu p` ;
- [x] ajouter l'historique d'iteration local et les diagnostics de changement
  d'etat ; la tangente de stick est exposee, la tangente Newton complete
  reste a faire ;
- [x] verifier le bloc glissant analytique, la borne de Coulomb, la
  dissipation locale, l'inversion de charge et la sensibilite de la force
  saturee a la regularisation ;
- [x] ajouter une boucle adhesion-glissement a memoire et verifier le
  changement de sens ainsi que la dissipation incrementale ;
- [x] verifier l'independance au pas pour une rampe tangentielle a pression
  normale constante ;
- [x] ajouter un repli structurel TET4 : apres echec du point fixe, les deux
  efforts de glissement actifs sont resolus avec la contrainte normale exacte;
  la campagne `VNV-CONTACT-FRICTION-TET4-STRUCTURAL-002` verifie quatre
  maillages, gap, cone de Coulomb et branches `stick`/`slip` ;
- [x] ajouter une globalisation de secours : si la racine hybride de
  glissement echoue, une region de confiance sur le meme residu actif est
  tentee et tracee comme `active_slip_least_squares` ;
- [x] intercaler une Newton de branche active consistante : reponses unitaires
  exactes du systeme selle, derivee analytique de Coulomb et recherche
  lineaire d'Armijo, tracee comme `active_slip_consistent_newton`; les echos
  hybrides et Newton sont testes separement avant le repli par region de
  confiance ;
- [x] obtenir une correlation externe en glissement sature avec Code_Aster
  `18.1.0` Docker epingle : `VNV-CONTACT-FRICTION-CODEASTER-CONTINUE-003`
  donne `0,6070 %` d'ecart en `UX`; l'adhérence reste explicitement hors
  correlation car les regularisations tangentielles different ;
- [x] executer l'essai exploratoire Code_Aster en adhesion nominale : l'etat
  `stick` est bien retrouve dans QF_solver, mais `UX` differe de `396,20 %`
  faute de compliance tangentielle equivalente. Le resultat est classe
  `non_comparable`, sans masquer l'ecart ni le presenter comme echec mecanique ;
- [x] rejeter la calibration scalaire de penalite Code_Aster : deux charges
  d'adhesion de controle donnent respectivement `107,16 %` et `167,32 %`
  d'ecart avec un decalage de branche. L'adhesion externe reste ouverte et ne
  sera pas forcee par ajustement de parametre ;
- [ ] lineariser les changements d'ensemble actif et de normale pour les cas
  fortement non lineaires, puis etendre la correlation externe aux structures
  deformables et a l'adhérence comparable ;
- [ ] garder hors V1 qualifiable le grand glissement, l'usure, la cohesion,
  le contact thermique et les lois dependantes de la vitesse.

### P7.6 - Publication V1

- [x] exposer les preuves internes de contact par API
  `run_contact_verification(...)` et CLI `verify-contact`, avec dossier de
  resultats, rapports et manifestes regroupes ;
- [x] integrer `BEAM2`, ressorts/masses, MPC/RBE et contact dans l'API, le
  schema JSON, la CLI generique, les audits, les exports et le catalogue des
  demonstrations. La non-regression `rbe2_rigid_arm.json` couvre desormais le
  chemin API -> audit -> JSON/VTU -> CLI et verifie le transport du moment de
  liaison vers la reaction imposee ;
- [x] fournir au moins une demonstration analytique, une V&V externe, un cas
  d'erreur et un test d'integration par nouvelle famille : BEAM2 est correle
  en statique et modal, ressorts/masses en SDOF et RBE2 par
  `VNV-RBE2-CODEASTER-RIGID-ARM-001` avec Code_Aster epingle, et les deux
  contacts ont leurs campagnes bornees. Les extensions non couvertes restent
  explicitement experimentales ;
- [x] publier la matrice de maturite dans `docs/etat/capacites.md` et les
  exclusions dans `docs/etat/limites.md` : assemblage lineaire borne,
  BEAM2/ressorts/MPC-RBE experimentaux et contacts explicitement limites. La
  branche de glissement sature est correlee; l'adhesion reste
  `non_comparable` avec l'oracle externe ;
- [x] executer la campagne complete Windows et construire le site hors ligne :
  le `2026-07-29`, `pytest` donne `926 passed, 12 skipped`, le profil
  `verify-all engineering` donne `886 passed, 9 skipped, 23 deselected`,
  Ruff, `compileall`, MITC4 quick, TET10 et la campagne documentaire de
  `625` artefacts sont PASS ;
- [x] verifier l'archive prospective locale : `407` fichiers exportes,
  `0` constat, avec exclusion explicite des instructions de travail internes,
  des resultats, du site genere, des repertoires temporaires et des etudes
  V&V de travail ;
- [ ] confirmer la meme baseline dans la matrice CI Linux et inspecter
  manuellement le contenu de l'archive publique finale ;
- [x] fermer l'audit technique de confidentialite et choisir les licences de
  la V0.2.0-alpha. Au `2026-08-10`, la source publique compte `992` fichiers
  inspectes sans constat, l'archive propre `1102` fichiers sans constat et la
  nouvelle histoire publique un seul commit sans constat historique. Les
  licences retenues sont Apache-2.0 pour le code et CC BY 4.0 pour la
  documentation originale. La publication distante reste une action Owner
  distincte et n'est pas executee automatiquement ;
- [x] ajouter un prefiltre de chemins dans l'historique atteignable avec
  `scripts/audit_git_history.py`; tout constat impose une revue de contenu ou
  la creation d'un historique public propre, sans pretendre remplacer cette
  Owner review. Le passage du `2026-07-29` trouve `145` chemins d'etudes
  historiques dans `13` commits : aucun secret n'est etabli, mais la revue
  manuelle ou un historique public neuf reste obligatoire ;
- [x] formaliser la politique de controles proportionnes dans
  `docs/controle_qualite.md` : tests unitaires et V&V cibles pendant une
  iteration locale, integration seulement aux frontieres touchees, baseline
  complete reservee aux releases, refactorings transverses, dependances et
  regenerations controlees. La CI conserve la campagne exhaustive apres push.

Critere de sortie V1 : les assemblages lineaires sont reproductibles et
documentes; le contact sans frottement possede une campagne V&V complete; le
contact avec frottement est au minimum demonstrable, borne et explicitement
classe selon ses preuves. Aucun element reporte en V2 ne bloque ce jalon.

### Gel technique V0.2.0-alpha du 10 aout 2026

- [x] suite complete Windows : `1091 passed`, `17 skipped`, aucun echec ;
- [x] site hors ligne strict : `711` artefacts, aucune ressource locale
  manquante ;
- [x] MITC4 multicouche dynamique accepte par l'Owner pour un usage
  engineering experimental borne, avec reserve modale 10 000 QUAD4 ;
- [x] histoire publique neuve creee dans un depot local separe, avec identite
  Git `noreply`, sans les 12,2 Go de preuves V&V de travail ;
- [ ] confirmer la matrice CI Linux/Windows sur le commit public ;
- [ ] realiser l'audit Owner du grand modele et autoriser explicitement le
  push public.

## Post V0.2.0-alpha - preparation V0.2.1

Cette section regroupe les approfondissements reportes apres la fermeture de
l'alpha. Ils ne bloquent pas l'acceptation experimentale bornee du cas TET10
J2, mais ils bloquent toute hausse de maturite generale.

- [ ] refaire `VNV-TET10-J2-CODEASTER-COMPLEX-026` sur au moins deux niveaux
  de maillage et publier la convergence des deplacements, de la PEEQ moyenne
  et des energies ;
- [ ] comparer les champs de contraintes et de deformations hors de l'angle
  rentrant, avec une bande d'exclusion et une regle de moyenne documentees ;
- [ ] controler les rotations, les deformations locales maximales et le
  critere petites deformations, au-dela du seul ratio deplacement/longueur ;
- [ ] ajouter un chemin charge/decharge/recharge sur une geometrie complexe et
  verifier le stockage et la restauration des variables internes ;
- [ ] completer la correlation externe TET10 J2 avec Code_Aster et CalculiX
  sur une geometrie complexe, avec versions et decks traces ;
- [ ] soumettre le dossier complexe a une nouvelle Owner review avant toute
  evolution de `experimental` vers une maturite superieure ;
- [ ] ne pas presenter les pics de contrainte aux angles rentrants comme des
  valeurs acceptables sans etude de convergence et regularisation explicite.

## Gel V0.2.0-alpha avant publication

Date de l'etat : **2026-08-10**. Le perimetre V0.2.0-alpha est gele par Owner,
mais le push public n'est pas encore autorise. Le dossier de reference est
`docs/verification/release_v020_alpha_freeze.md` et son PDF de
relecture est `output/pdf/qf_solver_v020_alpha_freeze_owner_review.pdf`.

Etat technique consolide :

- TET4, TET10 et MITC3 modal/Newmark/harmonique, BEAM2 dynamique et entites
  discretes : decisions Owner `accepted_for_bounded_engineering_use` du
  2026-08-02, avec leurs recommandations de raffinement ;
- TET10 J2 structurel / Code_Aster : correlation technique `PASS`, maturite
  `experimental` bornee, decision Owner enregistree ;
- MITC4 multicouche dynamique plan : trois empilements testes en modal,
  Newmark et harmonique, correlation technique `PASS`, statut `experimental`
  conserve et reserve modale 10 000 QUAD4 ;
- MITC3 multicouche courbe a orientation projetee : preuve disponible,
  statut `experimental` borne ;
- licences, audit public, archive, artefacts documentaires, Ruff et
  compilation : `PASS` au dernier controle ;
- suite pytest complete : execution interrompue apres plus de dix minutes,
  sans verdict final ; ce point doit etre rejoue par lots puis en campagne
  complete avant le tag ;
- le tag local `v0.2.0-alpha` est cree apres le gate pytest ; aucun push public
  ne doit etre realise avant l'audit Owner du grand modele.

Les travaux post-alpha ne sont pas detailles dans le dossier de release ; ils
seront definis apres la publication et apres l'audit Owner du grand modele.
Le gel signifie que le perimetre et les limites de la V0.2.0-alpha ne changent
plus.

Checklist de fermeture avant publication :

- [x] enregistrer la decision Owner du gel V0.2.0-alpha ;
- [x] integrer les decisions dynamiques du 2026-08-02 et les validations
  recentes MITC3+/TET10 J2 ;
- [ ] relancer les tests longs par lots, puis executer une campagne complete
  avec resultat archive et sans timeout ;
- [ ] realiser un `external_audit` de l'historique Git et du contenu exact de l'archive ;
- [ ] confirmer les URLs publiques et l'absence de donnees ou modeles prives ;
- [x] creer le tag local `v0.2.0-alpha` apres le gate pytest ;
- [ ] pousser uniquement apres l'audit Owner du grand modele et accord
  explicite.

## Commandes de pilotage

## Pages techniques et Owner review

### P-DOC-R2 - Refonte de lisibilite avant Owner review

Statut : **revision 0.2 acceptee; revision 0.3 acceptee documentairement avec
recommandations et ecarts V&V ouverts**. La decision 0.2 reste valide et
immuable. La revision 0.3 ne remplace pas les decisions mecaniques par
perimetre et ne vaut pas revue independante.

- [x] reorganiser le manuel dans l'ordre `element -> demonstration ->
  resultats et post-traitement -> limites -> references`, puis `methodes`,
  puis annexes communes uniquees en fin de volume ;
- [x] remplacer le rendu PDF Markdown par une source LaTeX controlee, avec
  equations vectorielles, matrices et fractions rendues nativement; ne pas
  publier de notation de secours telle que `frac`, `^` ou matrices texte ;
- [x] limiter taille, largeur et nombre des equations affichees dans le flux
  principal; les derivations longues et matrices completes vont en annexes
  referencees ;
- [x] relier chaque convention de Jacobien, interpolation et quadrature a son
  point de depart, une reference bibliographique, une formule `FORM-*`, le
  code et le test associes ;
- [x] expliciter pour chaque element le chargement: support, repere, signe,
  unite, resultant, moment, conservation, conditions de rejet et test ;
- [x] ajouter sur les demonstrations controlees les deformations
  initiale/deformee clairement
  distinguables, le champ de contrainte, les deformations, les invariants et
  les valeurs aux points d'integration lorsqu'elles sont pertinentes ;
- [x] corriger et publier les comparaisons QF/reference MITC4 disponibles;
  les figures TET10, courbes de residu logarithmiques et tableaux matriciels
  sont egalement corriges ;
- [x] relancer les cas Newmark a maillage structurel raffine avant toute
  conclusion sur une correlation externe : TET4 a `9 893` elements et TET10
  a `9 893` elements / `50 112` DDL avec etude maillage/pas de temps, ecart
  RMS final TET10 de `1,2403 %` ;
- [x] verifier visuellement chaque page PDF en rendu raster A4,
  puis enregistrer la revue Owner sans remplir aucune decision a l'avance.

Etat consolide du 2026-08-01 : TET10 flexion, residus logarithmiques, tableaux
matriciels et comparaisons QF/reference MITC4 disponibles sont integres. Le
PDF natif comporte TET4, TET10, MITC4, MITC3, BEAM2, les entites discretes,
les liaisons, le contact et les methodes de resolution.

La cloture automatique 0.3 couvre `33` couples element-analyse, `7` contrats
de chargement et `12` familles de methodes. Les cartes de contraintes et
deformations ainsi que les vues externes disponibles sont publiees. Quatre
absences d'oracle restent classees `gap_documented`; elles sont des actions
V&V et non des passes mecaniques.

Owner review du 2026-08-01 : decision
`accepted_with_recommendations`, tracee dans
`qualification/reviews/technical_manual_owner_review_2026-08-01.json`, puis
validation finale du PDF regenere tracee dans
`qualification/reviews/technical_manual_owner_review_final_2026-08-01.json`.
La relecture documentaire est fermee. Les
actions ouvertes sont la generalisation des champs de contraintes et
deformations, davantage de courbes de convergence, une correlation externe
par element et methode lorsque realisable, et les vues QF/reference
synchronisees. Le composite statique borne est integre a la V1; ses extensions
dynamiques, dommage et delaminage restent hors de cette acceptation.

- [x] convertir les equations de ressorts et masses concentrees en LaTeX natif ;
- [x] ajouter en annexe les liens de publications primaires, dont
  Hammer-Stroud pour la quadrature des simplexes ;
- [x] publier la convention d'epaisseur `shell_down`, `shell_middle`,
  `shell_up` et conserver les deux limites lorsque le plan moyen est une
  interface composite ;
- [x] integrer les pages composites au dossier technique principal V1 avec
  leur maturite explicite ;
- [x] publier des cartes colorees de contrainte/deformation pour chaque cas
  ou ces champs pilotent la conclusion mecanique ;
- [x] ajouter une correlation analytique ou Code_Aster/CalculiX pour chaque
  couple element-methode revendique, ou documenter explicitement l'absence
  d'oracle reproductible.

Critere technique atteint le `2026-08-01` : le PDF 0.3 de `277` pages est
genere depuis LaTeX, les equations sont lisibles, chaque element contient son
exemple et ses sorties, et les annexes ne rompent plus le fil de lecture. Le
PDF corrige porte l'empreinte
`ec06c572e27c45d2d1159c3eef2a0ed84eadda4adfc3a28e009c3eb7b36d1708`.
La decision Owner du `2026-08-01` est `accepted_with_recommendations`, tracee
dans `qualification/reviews/technical_manual_owner_review_0_3_2026-08-01.json`.
Elle ferme la qualite documentaire mais laisse ouverts les ecarts V&V
`PAIR-MITC3-LAMINATE` et `PAIR-MITC3-LAMINATE-DYN`. Les campagnes dediees
TET10 J2 et MITC4 multicouche dynamique ont depuis apporte une evidence
`verified_development_external_correlation`; la correlation structurelle TET10
J2 avec Code_Aster est tracee, mais la maturite `experimental` et la Owner
review restent ouvertes. Ces lignes interdisent toute extrapolation de maturite hors campagne
dediee et decision Owner.

- [x] executer `VNV-MITC4-LAMINATE-DYNAMIC-001` : modal, Newmark et
  harmonique sur `[0/90/90/0]`, masse coherente, condensation de drilling et
  post-traitement par pli ;
- [x] correl(er) ce cas avec Code_Aster sur meme maillage dans
  `VNV-MITC4-LAMINATE-DYNAMICS-CODEASTER-DST-018` : les ecarts maximaux sont
  `1,678 %` (modes), `0,422 %` (Newmark) et `0,205 %` (harmonique), tous sous
  les seuils traces. Le cas multicouche courbe a axe materiau projete est
  couvert separement par `VNV-COMP-CURVED-ORIENTATION-008` contre CalculiX;
  il valide la projection en statique, non la dynamique courbe complete ;
- [x] soumettre le perimetre MITC4 multicouche dynamique a une Owner review
  : Quentin Farinazzo l'accepte le `2026-08-10` pour un usage engineering
  experimental borne. La dynamique courbe, les stratifies non symetriques,
  le dommage, la rupture et la delamination restent exclus ;
  distincte. Le statut actuel est `verified_development`, pas Owner accepte.
- [x] executer la tentative de reference Code_Aster sur `10 000` QUAD4 pour
  `[45/-45/-45/45]` dans `VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023` ; les
  quatre frequences sont archivees, mais le controle a posteriori Code_Aster
  signale une alarme sur le mode 3 ;
- [ ] fermer la preuve modale MITC4 multicouche a `10 000` QUAD4 : le chemin
  QF_solver SciPy atteint environ `7,383e-6` de residu apres `30 000`
  iterations, au-dessus de `1e-7`. La prochaine action est un backend
  PETSc/SLEPc ou AMG avant toute correlation mode par mode.

Controles de cloture automatique du `2026-08-01` : `1022 passed`,
`13 skipped`; Ruff, `compileall`, generation documentaire, QF_solver quick et
MITC4 quick sont `PASS`. L'audit de publication analyse `649` fichiers avec
`0` constat. La baseline documentaire inclut desormais `pypdf==6.10.0` et
la decouverte Pandoc/MiKTeX n'embarque plus aucun chemin de poste.

- [x] produire une page Markdown par element et par methode avec geometrie,
  DDL, formulation, integration, algorithme, cas executable, maillage,
  chargement, conditions limites, resultats, deformee, invariants,
  convergence, limites et references ;
- [x] separer les pages des solveurs direct, CG, MINRES, GMRES, BiCGSTAB et
  arc-length ;
- [x] creer le registre controle
  `qualification/documentation_review_pages.json` sans decision pre-remplie ;
- [x] ajouter les formulations fortes et faibles detaillees TET4, TET10,
  MITC4 et BEAM2, avec au moins dix tests/invariants documentes par famille ;
- [x] composer les equations LaTeX dans le PDF et verifier automatiquement le
  minimum de dix pages par formulation principale : la premiere version
  affichait encore des equations trop grandes ou degradees; la refonte
  `P-DOC-R2` doit remplacer ce rendu avant Owner review ;
- [x] effectuer l'Owner review du dossier consolide couvrant chaque page avec
  `docs/verification/owner_review_pages_techniques.md`; decision finale
  `accepted_with_recommendations` du `2026-08-01` ;
- [x] enregistrer la decision Owner sur la revision complementaire 0.3 apres
  confirmation explicite du PDF de 277 pages et de son empreinte SHA-256 ;
- [ ] ne changer une maturite qu'apres Owner review enregistree et preuves
  V&V suffisantes. Une demonstration documentee ne vaut pas qualification.

```powershell
python -m pytest
python -m ruff check solveur mitc4 scripts tests
python .\qf_solver.py verify-all --profile engineering --json-report .\results\verification\verify_all_engineering.json
python .\scripts\build_docs.py --profile engineering
python .\qf_solver.py qualification-readiness --scope tet4-linear-static
python .\qf_solver.py qualification-readiness --scope mitc4-linear-static
python .\scripts\run_mitc4_vnv.py --output .\results\VNV-MITC4-LINEAR-V1
python .\scripts\run_mitc4_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CANTILEVER-002
python .\scripts\run_mitc4_modal_plate_vnv.py --output .\results\VNV-MITC4-MODAL-PLATE-003
python .\scripts\run_code_aster_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CODEASTER-DKQ-004 --mesh-size 32
python .\scripts\run_mitc4_modal_extended_vnv.py --output .\results\VNV-MITC4-MODAL-EXTENDED-005
python .\scripts\run_mitc4_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-FREE-002
python .\scripts\run_mitc4_newmark_extended_vnv.py --output .\results\VNV-MITC4-NEWMARK-DAMPED-FORCED-003
python .\scripts\run_mitc4_newmark_broadband_vnv.py --output .\results\VNV-MITC4-NEWMARK-BROADBAND-004
python .\scripts\run_code_aster_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-CODEASTER-DKQ-005
python .\scripts\run_mitc4_newmark_operational_vnv.py --output .\results\VNV-MITC4-NEWMARK-OPERATIONAL-006
python .\scripts\run_mitc4_harmonic_vnv.py --output .\results\VNV-MITC4-HARMONIC-MODAL-001
python .\scripts\run_mitc4_harmonic_condensation_vnv.py --output .\results\VNV-MITC4-HARMONIC-CONDENSATION-002
python .\scripts\run_mitc4_harmonic_broadband_vnv.py --output .\results\VNV-MITC4-HARMONIC-BROADBAND-003
python .\scripts\run_mitc4_nafems13h_vnv.py --output .\results\VNV-MITC4-HARMONIC-NAFEMS13H-004
python .\scripts\run_code_aster_nafems13h_vnv.py --output .\results\VNV-MITC4-HARMONIC-CODEASTER13H-DKQ-007
python .\scripts\run_j2_material_vnv.py --output .\results\VNV-J2-MATERIAL-CYCLIC-001
python .\scripts\run_calculix_j2_vnv.py --output .\results\VNV-J2-CALCULIX-ISOTROPIC-002
python .\scripts\run_j2_structural_vnv.py --output .\results\VNV-J2-TET4-CYCLIC-003
python .\scripts\run_j2_methods_vnv.py --output .\results\VNV-J2-NONLINEAR-METHODS-004
python .\scripts\run_j2_step_sensitivity_vnv.py --output .\results\VNV-J2-STEP-SENSITIVITY-005
python .\scripts\run_composite_analytic_vnv.py --output .\results\VNV-COMP-ANALYTIC-001
python .\scripts\run_composite_structural_vnv.py --output .\results\VNV-COMP-STRUCTURAL-CONVERGENCE-002
python .\scripts\run_calculix_composite_vnv.py --output .\results\VNV-COMP-CALCULIX-S8R-003
python .\scripts\run_composite_nafems_code_aster_vnv.py --output .\results\VNV-COMP-NAFEMS-R0031-CODEASTER-004
python .\qf_solver.py large-campaign --output .\results_large\P4-CAMPAIGN-PLAN-001 --targets 100000 1000000 3000000 --solver-backend petsc
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action weak
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action preconditioners -Execute
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action profile -Execute
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action tuning -Execute
python .\qf_solver.py postprocess-large --input .\model.h5 --displacements .\benchmark\displacements.bin --output .\post --chunk-size 65536
```

Le scope harmonique MITC4 est accepte avec recommandations pour l'usage
engineering interne. Le scope Newmark MITC4 est valide avec recommandations
pour l'usage engineering interne depuis le `2026-07-16`; une revue independante
et une baseline Git propre restent requises avant toute qualification externe.

## Execution V&V et correlations Code_Aster - 2026-08-14

Cette mise a jour reprend les executions demandees avec Code_Aster dans Docker
et distingue les resultats numeriquement passes des decisions de maturite.

- [x] Executer la campagne composite interne : analytique, convergence
  structurelle, contraintes par pli, assemblage courbe et decoupe conique.
  Les cinq rapports retournent `PASS_TECHNICAL_VERIFICATION`.
- [x] Executer la correlation Code_Aster du benchmark composite NAFEMS
  R0031/1. Le verdict est `PASS_EXTERNAL_CORRELATION`; le deplacement fin QF
  est a `0,4576 %` de la reference NAFEMS, Code_Aster a `0,7103 %`, et
  l'ecart QF/Code_Aster est a `0,2509 %`. La limitation interlaminaire `S13`
  reste explicitement ouverte.
- [x] Executer TET4 total-lagrangien : noyau, assemblage, sensibilite au
  nombre d'increments, contrainte/energie, flambement d'Euler,
  post-flambement et sonde `98 304` elements. Les verdicts automatiques sont
  positifs, mais la maturite reste `research`.
- [x] Executer les solides orthotropes TET4/TET10 : noyau, convergence,
  non-regression isotrope, contraintes singulieres, contraintes additionnelles,
  correlation structurelle externe et modal/Newmark. Les campagnes retournent
  `PASS_TECHNICAL_VERIFICATION`, `PASS_STRESS_ACCEPTANCE` ou
  `PASS_EXTERNAL_CORRELATION` selon le cas. La sonde grand modele orthotrope
  est maintenant disponible et retournee dans `VNV-ORTHOTROPIC-LARGE-STATIC-008`.
- [x] Remplacer les anciens chemins de preuve absents du contact, du composite
  et du total-lagrangien par les resumes Code_Aster et les artefacts internes
  controles effectivement presents.
- [x] Produire l'archive de release
  `qualification/evidence/release_vv_artifacts_2026-08-14-r14/`. Elle contient
  la preuve MITC3 courbe Code_Aster ajoutee apres l'archive r10; r10, r11, r12
  et r13 restent immuables comme photographies precedentes. Le bundle r14 est
  verifie par `verify-evidence` avec un verdict `PASS`.
- [x] Faire la revue Owner des ecarts Code_Aster et des figures sans promotion
  automatique de maturite. La decision `accepted_with_recommendations` du
  `2026-08-14` est enregistree dans
  `qualification/reviews/code_aster_correlation_owner_review_2026-08-14.json`.
  Q6 (orthotropie) et Q8 (MITC3 courbe) conservent leurs recommandations;
  le gate `release-vv` reste distinct et ouvert.
- [x] Ajouter la correlation Code_Aster de l'hemisphere pince MITC3 au
  catalogue et au bundle actif. `VNV-MITC3-PINCHED-HEMISPHERE-CODEASTER-015`
  comporte six niveaux, des figures de maillage/deformee/champ et une erreur
  QF/Code_Aster finale de `0,0927 %`. Le statut reste `experimental` jusqu'a
  la revue Owner.
- [x] Construire la correlation Code_Aster du MITC3 multicouche courbe a
  orientation projetee. `VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025`
  compare les memes facettes `TRIA3`, le meme empilement `[0/90/90/0]` et le
  meme vecteur global projete par QF_solver et Code_Aster `VECTEUR`. Avec
  `8x4`, `16x8`, `24x12`, `32x16`, `48x24` et `64x32` (jusqu'a `4 096`
  triangles), l'ecart vectoriel fin vaut `0,578 %`, les increments finaux
  valent `4,48 %` et `4,75 %`, et le residu libre maximal vaut
  `5,22e-11`; le verdict technique est `PASS_EXTERNAL_CORRELATION`. Le suivi
  `96x48` a ensuite ramene les increments a `3,381 %` et `3,818 %`, avec un
  ecart vectoriel de `0,996 %`. La revue Owner l'accepte avec recommandation;
  contraintes par pli, `S13`, dommage, delaminage et dynamique courbe restent
  hors du scope accepte.
- [x] Produire la preuve du grand modele orthotrope borne et archiver la
  correlation MPC/RBE2 Code_Aster; le chemin file-backed PETSc reste couvert
  par la campagne 1M TET4 isotrope.
- [x] Executer la campagne release complete avec `--execute-campaign` : les
  `13/13` cas passent, sans echec numerique ou infrastructure. Les cas
  `WARNING` ou `FAIL` attendus restent acceptes par leur propre contrat de
  campagne et ne sont pas confondus avec un calcul non conforme.
- [x] Fermer les preuves manquantes de la matrice d'analyse : les chemins
  obsoletes ont ete remplaces par les artefacts controles actifs du bundle
  2026-08-14 ; l'audit `maturity-promotion` confirme `0` chemin manquant.
- [x] Executer le premier lot de promotion atomique pour `tet4-linear-static` :
  la campagne officielle archivee sous
  `qualification/evidence/maturity_promotion_0_2_1/tet4_linear_static_campaign/`
  passe `13/13`, avec `12` bundles verifies et des resultats relisables.
- [x] Structurer les criteres machine-readable du TET4 statique dans
  `qualification/maturity_criteria_0_2_1.json` : convergence multi-niveaux,
  familles de chargement, equilibre, energie, matrices, exports et regle
  d'oracle externe. Le rapport les classe `PASS`, mais la promotion reste
  volontairement en attente d'une owner review ciblee.
- [x] Structurer les criteres TET4 modal, Newmark et harmonique dans le meme
  registre. Le registre dynamique compact rassemble les preuves internes et la
  correlation Code_Aster : ecart modal maximal `7,89e-13`, erreur d'historique
  Newmark maximale `8,16e-11` et ecart harmonique maximal `5,33e-12`. Les trois
  scopes sont `READY_FOR_OWNER_REVIEW`; aucune maturite n'est modifiee.
- [x] Structurer le scope `tet10-linear-static` : quatre niveaux traction,
  flexion et torsion, audit d'equilibre/energie, masse et charges T6, puis
  correlation CalculiX C3D10 sur maillage identique. Les ecarts deplacement et
  rotation sont respectivement `6,84e-5` et `6,45e-5`; le scope est
  `READY_FOR_OWNER_REVIEW` avec la recommandation Owner sur les pieces et
  assemblages complexes.
- [x] Structurer les preuves internes TET10 modal, Newmark et harmonique, puis
  archiver `VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018`. La campagne externe
  couvre six frequences, quatre niveaux temporels et trois niveaux spatiaux;
  les ecarts maximums sont `3,225e-11`, `5,779e-12` et `6,190e-12` pour modal,
  Newmark et harmonique. Les trois scopes sont maintenant `READY_FOR_OWNER_REVIEW`;
  aucune maturite n'est promue automatiquement.
- [x] Structurer les criteres MITC4 isotropes dans
  `qualification/maturity_criteria_0_2_1.json` et le registre
  `qualification/maturity_evidence_0_2_1/mitc4_isotropic_linear.json`. Modal,
  Newmark et harmonique passent les criteres internes et les correlations
  externes complementaires Code_Aster/NAFEMS; ils sont prets pour une nouvelle
  owner review. La statique est maintenant corrélée à Code_Aster DKQ sur trois
  maillages QUAD4 identiques; l'écart vectoriel fin vaut `1,7565 %` et la
  différence de résultante de réaction `2,26e-13`. Les quatre scopes restent
  soumis à une Owner review avant toute promotion automatique.
- [x] Realiser le premier plan de promotion P2 sur
  `mitc4-laminate-dynamic`. Le ledger
  `qualification/maturity_evidence_0_2_1/mitc4_laminate_dynamic.json` couvre
  trois empilements plans, trois niveaux de maillage, modal/Newmark/harmonique,
  Newmark amorti et la corrélation Code_Aster. Les critères
  `MITC4-LAM-C01` à `MITC4-LAM-C03` passent; la réserve 10 000 QUAD4 est
  explicitement hors domaine via `MITC4-LAM-C04`. Le scope est
  `READY_FOR_OWNER_REVIEW` pour une cible `owner_accepted`, sans modification
  automatique de la matrice.
- [x] Structurer le lot MITC3 multicouche dans
  `qualification/maturity_evidence_0_2_1/mitc3_laminate.json`. La preuve
  courbe statique dispose maintenant de deux familles de chargement et trois
  niveaux fins `4096/9216/16384` triangles; ses criteres techniques passent et
  le gate reste `BLOCKED_OWNER_REVIEW`, avec une seconde geometrie courbe encore
  recommandee. La preuve dynamique
  plane reste bloquee par
  `MITC3-LAM-DYN-C03` (un seul maillage) et `MITC3-LAM-DYN-C04` (owner review
  dediee absente). Les calculs et chemins d'artefacts sont passes, mais aucune
  promotion n'est automatique.
- [x] Structurer le plan de promotion TET10 J2 dans
  `qualification/maturity_evidence_0_2_1/tet10_j2.json`. La barre monotone
  et l'equerre re-entrante a charges combinees passent les correlations
  Code_Aster sur maillages identiques, avec residus et PEEQ traces. Le critere
  `TET10-J2-C04` bloque encore la promotion car le cas complexe n'a pas de
  decision Owner dediee; la famille reste experimentalement bornee.
- [x] Aligner le critere constitutif TET4 J2 sur l'oracle externe reellement
  disponible : Code_Aster `18.1.0` `VMIS_ISOT_LINE`, image Docker epinglee,
  empreinte de preuve et six checks PASS. Ce critere couvre le material-point;
  il ne remplace pas une correlation structurelle et ne ferme pas la decision
  Owner `TET4-J2-C04`.
- [x] Structurer les plans P1 `beam2-linear-static` et `discrete-linear` dans
  `qualification/maturity_evidence_0_2_1/beam2_discrete_static.json`. BEAM2
  dispose maintenant d'une correlation statique Code_Aster `POU_D_E` sur les
  memes maillages `4/8/16` : ecart fin `0,002808 %`, increments finaux
  inferieurs a `2,1e-12`, image Docker epinglee et artefacts archives dans
  `beam2_static_code_aster`. Le scope BEAM2 reste bloque uniquement par sa
  Owner review; le discret reste bloque par sa revue dediee.
- [ ] Aligner chaque ligne sur une maturite stable uniquement apres campagne
  complete, criteres atomiques et decision Owner ; l'audit actuel reste
  `WARNING` et ne promeut aucune ligne automatiquement.
- [ ] Refaire le gate sur un checkout Git propre. Tant que le depot est dirty,
  la release ne doit pas etre taguee ni publiee comme baseline qualifiee.

### Lot de promotion de maturite - solides orthotropes

- [x] Ajouter le ledger controle
  `qualification/maturity_evidence_0_2_1/orthotropic.json` pour separer les
  preuves statiques, modales et transitoires des decisions de maturite.
- [x] Ajouter les criteres machine-readable `ORTHO-STAT-C01` a
  `ORTHO-STAT-C02` pour les TET4/TET10 orthotropes statiques. Les deux cas
  Code_Aster/CalculiX, les patchs affines, l'objectivite par rotation et les
  niveaux de convergence sont controles; le scope est pret pour une revue
  Owner ciblee.
- [x] Ajouter les criteres `ORTHO-MOD-C01` a `ORTHO-MOD-C04` et
  `ORTHO-NEW-C01` a `ORTHO-NEW-C04`. Les preuves internes et les correlations
  Code_Aster passent ; les campagnes raffinees respectent maintenant la regle
  principale `<= 1 %` : erreur modale fine `0,00772 %` et increment Newmark
  final `0,1119 %`.
- [x] Corriger l'auditeur de promotion afin qu'un critere obligatoire en echec
  bloque tous les niveaux de cible, et pas seulement la cible `stable`.
- [ ] Faire signer la revue Owner cible `stable` du modal orthotrope, avec
  quatre niveaux de maillage, correlation Code_Aster `1,20e-13` et exclusions
  explicites.
- [ ] Faire signer la revue Owner cible `stable` du Newmark orthotrope, avec
  huit niveaux de pas, correlation d'histoire `6,25e-14` et residu maximal
  `2,23e-10`.
- [ ] Ne promouvoir la dynamique orthotrope qu'apres ces deux decisions et un
  audit reproductible sur checkout Git propre.

Campagne raffinee executee le `2026-08-21` : le modal TET4 orthotrope atteint
`0,00772 %` d'erreur theorique sur quatre niveaux, et la campagne Newmark
atteint `0,1119 %` d'increment adjacent final sur huit niveaux (`2e-4` a
`1,5625e-6 s`). La correlation Code_Aster sur maillage et grille identiques
est de `1,205e-13` en frequence, `6,254e-14` en RMS d'histoire et
`6,295e-15` sur le pic. Les rapports, PNG, manifeste et PDF sont controles
dans `qualification/vnv/orthotropic_modal_newmark/reference/` et
`output/pdf/orthotropic_modal_newmark_stable_owner_review.pdf`. Les deux
scopes sont donc techniquement prets pour Owner Review cible `stable`, mais
aucune maturite n'est modifiee automatiquement.

### Lot de promotion de maturite - contact avec frottement

- [x] Ajouter le ledger
  `qualification/maturity_evidence_0_2_1/contact_frictional_static.json`.
  Il distingue le cas de glissement Code_Aster deja execute des extensions
  encore non demontrees.
- [x] Ajouter les criteres `CONTACT-FRIC-C01` a `CONTACT-FRIC-C04` dans le
  registre machine-readable. Le cas de glissement, la limite de Coulomb, les
  residus, les fichiers et les figures passent.
- [x] Corriger la gate et distinguer la preuve externe unique de la campagne
  interne par familles; le ledger suit maintenant trois geometries et trois
  niveaux par famille.
- [x] Executer au moins trois familles de contact avec frottement : glissement
  d'un bloc, contact sur surface facettee et contact deformable multi-esclave.
- [x] Ajouter au moins trois niveaux de maillage par famille et mesurer
  penetration, pression normale, force tangentielle, branche stick/slip,
  equilibre et sensibilite aux penalisations; la campagne est archivee dans
  `qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/`.
- [x] Correl(er) les cas mecaniquement comparables a Code_Aster en conservant
  les differences de regularisation et de formulation dans le rapport. La
  branche glissante est maintenant comparee sur trois niveaux de charge
  (`200/250/300 N`) dans
  `contact_friction_code_aster_three_loads/`; les ecarts UX sont
  `0,607 %`, `0,456 %` et `0,365 %`, tous sous `2 %`.
- [ ] Enregistrer une `owner_review` dediee au frottement; la revue du contact
  sans frottement ne vaut pas decision pour Coulomb.
- [ ] Ne pas promouvoir `contact-frictional-static` avant la levee de
  `CONTACT-FRIC-C04`; `CONTACT-FRIC-C03` est maintenant satisfait par la
  campagne interne a trois familles et trois niveaux.

### Lot de promotion de maturite - grand modele PETSc/MPI

- [x] Ajouter le template `large_static` et le scope supplementaire
  `large-tet4-linear-static` au plan de promotion.
- [x] Archiver les preuves 100 k, 1 M et 3 M DDL dans
  `qualification/maturity_evidence_0_2_1/large_tet4_linear_static.json`, avec
  les empreintes et l'environnement PETSc/MPI epingle.
- [x] Formaliser les criteres `LARGE-TET4-C01` a `LARGE-TET4-C05` : residus,
  equivalence inter-rangs, assemblage par blocs, MPI-IO, memoire,
  preconditionneur, scaling et dossier reproductible.
- [x] Conserver le weak scaling a `41,6 %` comme `WARNING`; il ne doit pas
  etre transforme en succes par le seul fait que le solveur converge.
- [ ] Executer la campagne sur une seconde configuration materielle ou
  documenter explicitement pourquoi la comparaison reste mono-machine.
- [ ] Mesurer une campagne de scaling plus large et ameliorer la partition
  avant de relever le seuil d'efficacite.
- [ ] Enregistrer une `owner_review` dediee au grand modele, en acceptant ou
  refusant explicitement le perimetre TET4 isotrope lineaire et ses limites.
- [ ] Ne pas extrapoler cette preuve aux elements, analyses ou materiaux non
  mesures dans l'environnement PETSc/MPI.

### Lot de promotion P1 - MITC3, BEAM2 et entites discretes dynamiques

- [x] Structurer les criteres `MITC3-STAT-C01` et `MITC3-STAT-C02` a partir de
  la revue Owner statique, des campagnes courbes et des archives Code_Aster.
  Le scope `mitc3-linear-static` est maintenant pret pour Owner.
- [x] Structurer les scopes `mitc3-modal`, `mitc3-transient-dynamic` et
  `mitc3-harmonic-response` avec invariants internes, correlations DKT,
  artefacts et decision Owner dynamique.
- [x] Conserver les trois demandes de raffinement frequence-maillage comme
  criteres obligatoires `MITC3-MOD-C04`, `MITC3-NEW-C04` et `MITC3-HAR-C04`.
  Elles sont maintenant satisfaites par un ledger dedie, sans promotion
  automatique de maturite.
- [x] Structurer `beam2-linear-dynamics` et `discrete-linear-dynamics` avec
  leurs campagnes analytiques, correlations Code_Aster et revue Owner.
  Les deux scopes sont prets pour une nouvelle decision Owner dans leur
  domaine borne.
- [x] Executer le raffinement MITC3 dynamique commun aux trois methodes sur
  les niveaux 8x2, 16x4 et 24x6 avec Code_Aster et archiver le ledger dedie
  `qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json`.
- [ ] Faire relire par Owner le nouveau ledger MITC3 dynamique et enregistrer
  une decision datee dans `qualification/reviews/` avant toute cible `stable`.
- [x] Regrouper les gates restantes dans
  `docs/verification/maturity_promotion_owner_review_0_2_1.md` afin de
  preparer une revue Owner scope par scope sans modifier les decisions.
- [ ] Faire relire les six scopes P1 et enregistrer les decisions Owner
  specifiques; aucune promotion vers `stable` ne doit etre automatique. Les
  preuves de raffinement MITC3 multicouche statique et dynamique sont
  maintenant presentes, mais leurs decisions Owner restent ouvertes.

### Lot de promotion de maturite - MITC4 stratifie statique

- [x] Rattacher le scope `mitc4-laminate-static` au suivi de recommandations
  du 2026-07-26 et au benchmark NAFEMS R0031 execute avec Code_Aster.
- [x] Ajouter les criteres `MITC4-LAM-STAT-C01` a `MITC4-LAM-STAT-C03` pour
  ABD, contraintes par pli, orientation courbe, convergence, correlation et
  artefacts de test.
- [x] Verifier les chemins du dossier : les trois criteres passent et la gate
  est `READY_FOR_OWNER_REVIEW`.
- [ ] Enregistrer une decision Owner ciblee pour la ligne statique stratifiee
  avant de discuter du passage a `stable`.
- [ ] Maintenir explicitement hors scope `S13`, la delamination, le dommage,
  la rupture progressive et l'extrapolation aux assemblages non couverts.

### Lot de promotion - TET4 total-lagrangien

- [x] Structurer `tet4-total-lagrangian-structural-v2` avec les criteres
  `TET4-TL-C01` a `TET4-TL-C04`.
- [x] Verifier la formulation Green-Lagrange/PK2, la politique minimum de six
  increments avec recommandation et defaut a dix, la correlation Code_Aster
  et les campagnes de flambement/post-flambement deja archivees.
- [x] Conserver le statut `BLOCKED_CRITERIA_FAILED` tant que la revue
  independante demandee par la self-review Owner n'est pas disponible.
- [ ] Obtenir un audit externe independant avant toute revendication de
  qualification ou extension du domaine total-lagrangien.
- [ ] Ne pas inclure pression suiveuse, contact, plasticite finie, dommage,
  rupture ou contraintes singulieres dans cette promotion.

### Lot de promotion - TET4 J2 materiau

- [x] Executer et archiver la campagne structurelle cyclique TET4 J2 : 140
  elements, 24 points de chemin, inversion et rechargement.
- [x] Ajouter les criteres `TET4-J2-C01` a `TET4-J2-C04` et rattacher le
  rapport, la figure, le VTU et les tests au registre de preuves.
- [x] Ajouter les criteres `TET4-J2-C03B` et `TET4-J2-C03B-FILES` pour la
  correlation structurelle externe monotone TET4/Code_Aster. La campagne
  `VNV-TET4-J2-CODEASTER-COMPLEX-027` utilise 244 TETRA4 sur maillage commun,
  avec erreurs deplacement et PEEQ inferieures a `1e-12` et residu `1,36e-12`.
- [x] Retirer du runner la dependance obligatoire a la reference Abaqus absente
  `qualification/vnv/references/abaqus_j2_uniaxial_2024.json`. Le rapport
  signale maintenant `NOT_AVAILABLE` et ne reconstruit aucune valeur publiee.
- [x] Conserver la preuve reproductible sur la theorie et Code_Aster dans
  `qualification/external_reference_digests/code_aster_j2.json`; Abaqus reste
  une reference historique optionnelle et non executee localement.
- [ ] Ajouter une correlation structurelle externe TET4 avec inversion,
  decharge et rechargement, puis enregistrer une decision Owner dediee avant
  passage de `experimental` a `owner_accepted` et, plus tard, a `stable`.

### Lot de promotion - contact statique borne et MITC3 multicouche statique

- [x] Structurer `contact-v1-linear-static-bounded` dans le registre de
  criteres sans modifier sa decision existante `accepted_for_bounded_engineering_use`.
- [x] Verifier la condition de raffinement a 9 984 elements et les empreintes
  Code_Aster associees; la gate reste `NO_PROMOTION_REQUIRED`.
- [x] Distinguer explicitement le contact sans frottement accepte du lot
  `contact-frictional-static`, encore bloque par son evidence gap.
- [x] Structurer `mitc3-laminate-static` sans reutiliser la correlation
  dynamique comme preuve statique.
- [x] Enregistrer `MITC3-LAM-STAT-C01` et `MITC3-LAM-STAT-C03` comme
  criteres bloquants tant que le ledger statique et la decision Owner dediee
  ne sont pas disponibles.
- [x] Executer un cas statique MITC3 multicouche avec trois niveaux de
  maillage, resultats par pli, patch affine et oracle CalculiX S6 trace.
- [x] Archiver le ledger statique, la figure, le manifeste et le rapport
  Markdown dans `qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/`.
- [ ] Faire enregistrer une decision Owner specifique au scope statique
  multicouche; aucune promotion ne doit etre deduite d'une preuve dynamique.

Etat machine-readable au 2026-08-14 : le contact statique borne est structure
et ne demande pas de promotion supplementaire; le MITC3 multicouche statique
etait alors `BLOCKED_CRITERIA_FAILED` par `MITC3-LAM-STAT-C01` et
`MITC3-LAM-STAT-C03`.

Mise a jour du registre au 2026-08-15 : `MITC3-LAM-STAT-C01` et
`MITC3-LAM-STAT-C02` sont `PASS`; seul `MITC3-LAM-STAT-C03` reste
`owner_decision_pending`, avec son dossier Owner dedie.

Etat machine-readable au 2026-08-14 : la campagne interne retourne
`PASS (13/13)` et le bundle Code_Aster actif est verifie `PASS` avec `52`
etudes cataloguees, dont `36` correlations externes positives. Les archives
de release r10 a r14 restent immuables comme photographies precedentes.
Le gate global reste `FAIL` avec `30` maturites hors cible stable, `13` scopes
dont la readiness reste a traiter, une revue Owner en attente et un checkout
Git modifie. Les calculs passes sont archives et relisables, mais aucun calcul
orthotrope ne doit etre presente comme qualifie par la seule preuve interne.

### Mise a jour de promotion au 2026-08-15

- [x] Executer l'audit `maturity-promotion` apres les dernieres preuves :
  `34` scopes inspectes et `34/34` chemins d'artefacts integres.
- [x] Fermer techniquement les trois criteres de raffinement MITC3
  `MITC3-MOD-C04`, `MITC3-NEW-C04` et `MITC3-HAR-C04` avec le ledger
  `qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json`.
- [x] Archiver la campagne Code_Aster DKT MITC3 sur `8x2`, `16x4` et `24x6`.
  Les ecarts finaux sont `0,673 %` modal, `0,174 %` Newmark et `0,097 %`
  harmonique; la variation de frequence QF entre les deux derniers niveaux
  est `0,129 %`.
- [x] Creer le dossier sans decision
  `qualification/reviews/mitc3_dynamic_refinement_owner_review_pending.json`.
- [x] Corriger l'audit pour qu'une revue `pending` plus recente ne soit pas
  masquee par une ancienne revue acceptee; les trois scopes MITC3 sont
  maintenant `READY_FOR_OWNER_REVIEW` avec `owner_review: PENDING`.
- [x] Regrouper les douze gates de decision restantes dans
  `docs/verification/maturity_promotion_owner_review_0_2_1.md`.
- [x] Regenerer les dossiers PDF Owner existants dans
  `output/pdf/owner_review_code_aster_correlations_2026-08-14_decision_record.pdf`
  et `output/pdf/owner_review_status_2026-08-14_decision_record.pdf`.
- [x] Generer un paquet Owner machine-readable et Markdown depuis l'audit :
  `results/maturity_promotion_0_2_1/owner_review_packet.json` et
  `results/maturity_promotion_0_2_1/owner_review_packet.md`. Le paquet
  contient `33` scopes, dont `22` techniquement prets et `11` gates limitees
  a une decision Owner; aucune decision ni signature n'est pre-remplie.
- [x] Rattacher les `11` criteres `pending` a des fiches de revue dediees,
  sans decision pre-remplie. Les nouveaux dossiers couvrent discrete lineaire,
  TET10 J2, orthotrope modal, orthotrope Newmark et grand modele TET4.
- [x] Verifier que l'audit reste a `34/34` chemins presents; le seul gate
  supplementaire est la revue Owner du scope courbe MITC3, qui reste distincte
  des criteres techniques `PASS`.
- [x] Ajouter la classification machine-readable `owner_decision_pending`
  pour distinguer les onze decisions Owner manquantes d'un echec technique.
- [x] Nettoyer le runner J2 : l'absence de la reference Abaqus locale produit
  maintenant `NOT_AVAILABLE` sans reconstruire de valeurs; la campagne
  `VNV-J2-MATERIAL-CYCLIC-001` reste `PASS_INTERNAL` sur theorie et invariants.
- [x] Relancer les tests cibles des domaines en promotion : `6 passed` et
  `8 skipped`; les skips sont explicitement lies au corpus orthotrope
  optionnel ou a l'execution Docker externe non activee dans cette passe.
- [x] Ajouter `owner-review-check` avec `--require-decision` pour controler la
  structure, le scope, la decision autorisee et la signature d'une fiche avant
  le gate de release; la commande ne modifie jamais la matrice.
- [x] Executer avec Docker actif les six correlations externes encore
  conditionnees par `QF_SOLVER_RUN_EXTERNAL=1` : BEAM2 statique/modal/Newmark/
  transverse, discret et contact frictionnel retournent `6 passed`.
- [ ] Faire la revue Owner scope par scope; aucune matrice de maturite ne doit
  etre modifiee automatiquement.
- [ ] Relancer `release-vv` uniquement apres ces decisions et apres un
  checkout Git propre. Dans cette archive historique, le gate etait
  volontairement `FAIL` avec `30` scopes hors cible `stable`; ce chiffre ne
   doit pas etre utilise pour l'etat courant v14.

### Archive historique du dossier Owner consolide au 2026-08-15

Cette section conserve les artefacts de la campagne du 15 aout. Elle n'est
plus le decompte courant : le registre machine-readable de reference est
desormais l'audit v14 decrit en tete du document.

- [x] Generer un dossier PDF de 22 scopes techniquement prets, sans decision
  ni signature pre-remplie :
  `output/pdf/qf_solver_owner_review_stable_promotions_0_2_1.pdf`.
- [x] Generer un dossier PDF separe pour les 11 criteres bloques par une
  decision Owner ou une relecture independante :
  `output/pdf/qf_solver_owner_review_open_gates_0_2_1.pdf`.
- [x] Inclure le scope `mitc3-laminate-static-curved` dans le dossier archive
  des promotions techniquement pretes; sa decision reste distincte des gates
  Owner de cette campagne historique.
- [x] Produire l'audit structure, scripts, confidentialite et manques dans
  `docs/verification/project_hygiene_architecture_audit_0_2_1.md` et
  `output/pdf/qf_solver_project_hygiene_architecture_audit_0_2_1.pdf`.
- [x] Scanner le lot publiable courant : plus de `1400` fichiers controles, aucun
  chemin de poste, email prive, secret courant, ancienne marque ou vocabulaire
  d'assistance interne detecte.
- [x] Verifier que les configurations locales et caches de graphe ne sont pas
  suivis par Git.
- [ ] Reorganiser les `102` runners V&V actuellement places a plat dans
  `scripts/`, avec wrappers temporaires et tests de compatibilite.
- [ ] Decouper progressivement `src/solveur/verification` par familles; ce
  repertoire contient `135` modules et concentre la plus forte dette de
  navigation du projet.
- [ ] Reduire les modules situes entre 600 et 700 lignes avant d'ajouter de
  nouvelles responsabilites; aucun fichier ne depasse encore la limite.
- [ ] Enregistrer les decisions Owner scope par scope, obtenir la relecture
  independante du total-lagrangien ou conserver `research`, puis relancer le
  gate complet sur un checkout propre.

## Phase suivante - passer de Owner accepted a stable par preuves V&V

### Objectif de maturite

Cette phase ne cree pas de nouveaux elements. Elle augmente la profondeur des
preuves des elements et methodes deja presentes afin de distinguer clairement :

`owner_accepted` = utilisable dans le domaine declare apres decision Owner ;

`accepted_with_recommendations` = utilisable, mais avec actions de preuve encore
ouvertes ;

`accepted_for_bounded_engineering_use` = utilisable uniquement dans un domaine
etroitement borne ;

`stable` = domaine suffisamment demontre pour que les recommandations critiques
soient fermees, avec une preuve repetable, plusieurs cas independants et aucune
extrapolation non documentee.

Le passage vers `stable` ne sera jamais declenche par une seule Owner review,
un seul benchmark ou un seul calcul Code_Aster/CalculiX. La decision devra etre
prise scope par scope et conserver les limites qui restent hors domaine.

### Critere commun de passage vers stable

Un scope pourra proposer `stable` uniquement si les neuf conditions suivantes
sont satisfaites :

1. la formulation, les hypotheses, les unites, les signes et les conventions
   sont figes dans une page technique versionnee ;
2. un test analytique ou un invariant mecanique est PASS ;
3. une etude de convergence comporte au moins quatre niveaux de maillage ou
   de pas de temps, avec une asymptote interpretable ;
4. au moins trois geometries ou trois cas de chargement representatifs sont
   passes, dont au moins un cas qui n'est pas le cas de developpement ;
5. une correlation externe, une reference publiee ou une solution fermee est
   disponible lorsque le domaine le permet ;
6. les quantites acceptees sont definies : deplacements, reactions, energie,
   contraintes, frequences, residus ou historique temporel ;
7. les cas singuliers, les limites de maillage et les modes d'echec sont
   affiches dans le rapport ;
8. les recommandations critiques de la derniere Owner review sont fermees ou
   transformees en limites explicites ;
9. une nouvelle Owner review datee confirme la promotion, sans modifier
   automatiquement la matrice de maturite.

Un scope qui echoue a une seule condition reste `owner_accepted`,
`accepted_with_recommendations` ou `accepted_for_bounded_engineering_use` selon
le risque. Un resultat PASS numerique ne compense pas une preuve V&V absente.

### Etape ST-00 - figer le protocole de promotion

Registre cree le 2026-08-16 :
`qualification/stable_promotion_criteria_0_2_1.json`. Il definit les neuf
conditions communes et les regles de decision sans modifier les maturites.

- [x] Creer `qualification/stable_promotion_criteria_0_2_1.json` avec les neuf
  conditions communes, les seuils par famille et les artefacts obligatoires.
- [ ] Ajouter a chaque scope un identifiant `ST-*`, un domaine accepte, un
  domaine exclu, une reference et une liste de recommandations ouvertes.
- [x] Separarer dans les rapports `technical_status`, `owner_decision`,
  `maturity_target` et `release_readiness`, en conservant `criteria_status`
  pour compatibilite avec les anciens consommateurs.
- [ ] Refuser une promotion si une recommandation critique n'a ni preuve de
  fermeture ni limite explicite.
- [x] Ajouter un test qui verifie qu'un scope ne peut pas passer a `stable`
  uniquement parce que sa decision Owner est acceptee ; les blocages
  techniques restent `NOT_READY_TECHNICAL` dans le rapport.

### Etape ST-01 - fermer les recommandations des scopes deja proches de stable

Ledger cree le 2026-08-16 :
`qualification/stable_recommendation_ledger_0_2_1.json`. Il contient les
recommandations, leur criticite, les preuves de fermeture et le premier lot
TET4 a traiter.

- [x] Reprendre le dossier signe
  `qualification/reviews/owner_review_maturity_promotion_0_2_1_2026-08-15.json`
  comme point de depart, sans reecrire les anciennes preuves.
- [x] Pour chaque scope, creer une fiche de suivi avec `recommendation_id`,
  action, preuve attendue, responsable de revue, statut et date de fermeture.
- [x] Executer la reconduction ciblee ST-01-A sur les quatre scopes TET4 :
  `34 passed`, `3 skipped`, `0 failed`. Le rapport est archive dans
  `qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/`.
- [x] Passer `REC-ST-013` a `REC-ST-016` en `in_progress` avec un artefact de
  progression, sans les fermer : la seconde geometrie reste necessaire.
- [ ] Transformer les recommandations non bloquantes en limites utilisateur
  lorsqu'une nouvelle campagne n'est pas necessaire.
- [ ] Relancer l'audit de maturite et verifier qu'aucun scope n'est promu par
  effet de bord.
- [ ] Produire un rapport de delta Owner review -> stable candidate.

### Etape ST-02 - TET4 et TET10 lineaires

- [x] TET4 statique : le lot ST-01-A confirme les bilans internes et ajoute
  une convergence structurelle complementaire.
- [x] TET4 statique : une correlation structurelle meme-maillage QF_solver /
  Code_Aster TETRA4 a ete ajoutee sur quatre niveaux. L'ecart de deplacement
  externe est de `8,05e-11 %` au niveau fin, mais l'increment h reste a
  `4,64 %` avec des maillages Gmsh non imbriques.
- [ ] TET4 statique : produire une vraie convergence h imbriquee ou une
  extrapolation de Richardson avant promotion `stable`; la correlation
  externe seule ne ferme pas `REC-ST-013`.
- [x] TET4 dynamique : trois geometries 3D sont correlees a Code_Aster pour
  modal, Newmark et harmonique; la geometrie epaisse atteint `4,972 %` sur le
  dernier increment statique apres cinq niveaux.
- [ ] TET4 statique : ajouter une geometrie de piece differente du tetraedre
  elementaire, avec traction, flexion, torsion et pression.
- [x] TET10 dynamique : modal, Newmark et harmonique sont correles a Code_Aster
  TETRA10 sur le meme maillage, avec trois niveaux spatiaux et quatre niveaux
  temporels.
- [ ] TET10 statique : refaire la convergence sur une geometrie courbe puis
  comparer les champs de contraintes hors singularites avec TET4 affine.
- [x] TET10 modal/Newmark/harmonique : ajouter un arbre cylindrique dynamique
  avec quatre niveaux spatiaux externes; les ecarts Code_Aster restent sous
  `0,1 %` pour les trois observables.
- [ ] TET10 dynamique : ajouter amortissement et un chemin de charge non
  cantilever avant promotion stable.
- [ ] Fermer uniquement les ecarts qui restent sous les seuils definis dans le
  protocole ST-00 sur au moins trois geometries ou familles de chargement
  independantes.
- [ ] Soumettre separement les quatre scopes TET4 et les quatre scopes TET10
  a une Owner review de promotion.

Les dossiers de preuve TET10 sont
`qualification/maturity_evidence_0_2_1/tet10_stable_batch_01/summary.json` et
`qualification/maturity_evidence_0_2_1/tet10_stable_batch_01/report.md`. La fiche
Owner est `docs/verification/tet10_stable_promotion_owner_review_0_2_1.md`.

### Etape ST-03 - MITC3 et MITC4 isotropes

- [ ] MITC3 statique : completer la preuve sur une plaque, une coque courbe
  facettisee et une geometrie distordue.
- [x] MITC3 modal/Newmark/harmonique : verifier les invariants internes de la
  masse coherente : masse translationnelle, absence d'inertie nodale de
  drilling et invariance par rotation. Les tests ciblés passent (`25 passed`).
- [x] MITC3 modal/Newmark/harmonique : vérifier algébriquement les matrices
  élémentaires `K/M` avant et après condensation. La projection `20x20 -> 18x18`,
  l'additivité des composantes, la stationnarité, la symétrie et la masse sans
  drilling passent dans `VNV-MITC3-MATRIX-CONDENSATION-AUDIT-001`, archivé dans
  `qualification/vnv/mitc3_matrix_condensation_audit_2026-08-21/`.
- [x] MITC3 modal/Newmark/harmonique : recalculer la rigidité par quadrature
  Duffy indépendante. L'écart maximal est `4,28e-15` par composante et le
  critère `MITC3-LAM-DYN-C11` est PASS dans
  `qualification/vnv/mitc3_stiffness_quadrature_audit_2026-08-21/`.
- [x] MITC3 multicouche : comparer indépendamment les opérateurs `A/B/D`, la
  masse surfacique, l'inertie de rotation et la projection d'orientation par
  quadrature Gauss-Legendre dans l'épaisseur. Le critère
  `MITC3-LAM-DYN-C12` est PASS dans
  `qualification/vnv/mitc3_laminate_abd_audit_2026-08-21/`.
- [ ] MITC3 modal/Newmark/harmonique : comparer maintenant ces matrices à une
  implémentation indépendante de formulation et reproduire les benchmarks
  modaux MITC3+ publiés. Cette étape reste ouverte : les audits algébriques
  et matériaux ne valent pas une corrélation externe de même formulation.
- [x] MITC3 multicouche dynamique : corriger le protocole V&V pour imposer au
  moins `80` pas par periode et une grille harmonique independante de la
  frequence QF_solver. Le diagnostic et les limites sont dans
  `docs/verification/mitc3_dynamic_causal_audit_2026-08-21.md`.
- [x] Relancer la correlation Code_Aster avec le protocole corrige sur `12x3`.
  Le lot est `PASS_EXTERNAL_CORRELATION` ; les erreurs sont `3,957 %` modal,
  `2,323 %` Newmark complet (`0,289 %` force, `2,677 %` libre) et `1,341 %`
  harmonique. Cette baisse confirme un biais de protocole, mais ne ferme pas
  le critere global `<= 1 %`.
- [ ] Ne pas promouvoir MITC3 multicouche dynamique a `stable` sur cette seule
  relance. Completer la comparaison `K/M` elementaire, une reference primaire
  CLT/analytique et une seconde geometrie avant toute correction de formulation.
- [ ] MITC4 statique : conserver les preuves deja acceptees et fermer chaque
  recommandation par une campagne ciblee, sans refaire inutilement les tests
  deja immuables.
- [ ] MITC4 modal/Newmark/harmonique : ajouter un cas courbe ou distordu,
  un cas avec amortissement et une comparaison externe reproductible.
- [ ] Pour chaque coque, separer clairement membrane, flexion, cisaillement,
  drilling et contraintes aux faces superieure/inferieure.
- [ ] Recalculer les etudes de shear locking avec quatre niveaux de maillage,
  trois elancements et au moins deux distorsions.
- [ ] Ne fermer la recommandation shear locking que si le plateau mince, le
  ratio d'energie et la comparaison de reference sont simultanement PASS.

### Etape ST-04 - MITC3/MITC4 stratifies et composites bornes

- [ ] MITC3 stratifie statique : ajouter au moins une seconde geometrie et une
  seconde sequence de plis, puis comparer les contraintes par pli hors zones
  singulieres.
- [ ] MITC4 stratifie statique : verifier ABD, couplage B, resultantes, faces
  superieure/inferieure et convergence sur deux empilements supplementaires.
- [ ] MITC4 stratifie dynamique : ajouter amortissement, modal, Newmark et
  harmonique pour au moins deux empilements differents.
- [ ] MITC3 stratifie dynamique : reproduire le meme protocole sans reutiliser
  automatiquement une preuve MITC4.
- [ ] Maintenir hors scope delamination, S13/S23 non verifies, dommage, rupture
  progressive et grandes deformations tant qu'une campagne dediee n'existe pas.
- [ ] Les scopes stratifies ne pourront devenir `stable` qu'apres fermeture des
  recommandations par pli et des geometries courbes associees.

### Etape ST-05 - BEAM2, discret et choix des solveurs

- [ ] BEAM2 : completer statique, modal, Newmark et harmonique sur une poutre
  multi-elements, puis sur une poutre avec changement de section ou d'axe.
- [x] Discret : ajouter un systeme multi-DDL couple et une comparaison de
  conservation d'energie avec le cas analytique masse-ressort. La campagne
  `VNV-DISCRETE-MULTIDOF-ANALYTIC-001` couvre six DDL translationnels libres,
  statique, modal, Newmark et harmonique avec erreurs relatives sous `1e-10`.
  Elle renforce le domaine technique, mais ne remplace pas la correlation
  externe Code_Aster mono-DDL et ne signe pas la promotion Owner.
- [ ] Discret : ajouter une correlation externe Code_Aster d'un assemblage
  multi-DDL avant toute promotion `stable` generale des ressorts et masses.
- [ ] Tester le choix direct, CG, MINRES, GMRES et BiCGSTAB sur les memes
  matrices, avec residu final, iterations, conditionnement et temps.
- [ ] Definir quand un solveur iteratif est recommande, refuse ou remplace par
  un fallback direct trace.
- [ ] Fermer la recommandation uniquement lorsque les erreurs de convergence et
  les diagnostics sont reproductibles sur deux tailles de modele.

### Etape ST-06 - Orthotropie et non-lineaire

- [x] Solides orthotropes TET4/TET10 : ajouter rotation d'axes, traction
  biaxiale, cisaillement combine et champ de deformation mixte. La campagne
  `VNV-ORTHOTROPIC-SOLID-LOAD-CASES-007` couvre cinq angles et trois etats de
  charge sur TET4/TET10, avec erreurs de projection et d'energie inferieures a
  `1e-12`. Cette preuve constitutive ne ferme pas la convergence structurale
  TET4 en flexion.
- [ ] Modal/Newmark orthotrope : verifier invariance par rotation, masse,
  energie et comparaison a une solution de reference.
- [ ] TET4/TET10 J2 : completer chargement, decharge, rechargement, ecrouissage
  et comparaison structurelle Code_Aster. La branche monotone structurelle TET4
  est maintenant PASS ; la branche cyclique externe reste ouverte.
- [x] TET4 J2 : tangent algorithmique, chargement/decharge/rechargement,
  plasticite parfaite et cycle structurel interne passes dans
  `qualification/maturity_evidence_0_2_1/tet4_j2.json`. La correlation Code_Aster
  material-point et la correlation structurelle monotone TET4 sont archivees;
  elles ne ferment pas encore le cyclique externe ni la promotion `stable`.
- [x] TET10 J2 : correlation structurelle Code_Aster sur eprouvette droite et
  equerre a chargements combines, puis raffinement `0,32 -> 0,24 -> 0,16 m`.
  Le cas fin respecte le gate primaire `<= 1 %` avec erreur de fleche
  `0,0123 %` et PEEQ RMS `0,8867 %`; la decision Owner stable reste a enregistrer.
- [ ] Total-lagrangien : obtenir la relecture independante requise avant toute
  promotion; conserver `research` si elle reste absente.
- [ ] Ne pas promouvoir plasticite finie, dommage, rupture ou grandes
  deformations sur la seule base des campagnes petites deformations.

### Etape ST-07 - Contact et grand modele

- [ ] Contact frottant : traiter d'abord l'ecart de 4,5 %, puis ajouter une
  seconde geometrie, une transition stick/slip et une correlation externe.
- [ ] Contact sans frottement : verifier une seconde topologie et les bilans
  de reactions avant toute extension du domaine.
- [ ] Grand TET4 : mesurer weak scaling et strong scaling sur au moins deux
  configurations PETSc/MPI, avec memoire, repartition, iterations et residu.
- [ ] Ajouter une reprise checkpoint et verifier qu'un calcul interrompu puis
  repris donne le meme resultat dans la tolerance definie.
- [ ] Maintenir les autres elements hors du perimetre grand modele tant qu'un
  chemin distribue dedie n'est pas prouve.

### Etape ST-08 - dossier V&V et seconde Owner review

- [ ] Generer une page Markdown par scope avec formulation, cas, maillage,
  chargement, figures, tableaux, convergence, limites et references.
- [ ] Ajouter au rapport une table `critere / valeur / seuil / verdict / source`.
- [ ] Fournir au minimum une figure de geometrie/maillage, une deformee, un
  champ mecanique, une courbe de convergence et une comparaison de reference.
- [ ] Verifier les PNG, VTU, JSON, empreintes, commandes et versions avant la
  revue.
- [ ] Creer un PDF de promotion par famille, puis un PDF de synthese sans
  decision pre-remplie.
- [ ] Faire une Owner review distincte pour chaque promotion; la signature doit
  citer le domaine accepte et les exclusions restantes.

### Etape ST-09 - fermeture des accepted bounded

- [ ] Lister tous les scopes `accepted_for_bounded_engineering_use` et les
  classer : promotion vers `owner_accepted`, maintien borne ou retrait.
- [ ] Pour chaque scope, choisir une seule voie : nouvelle preuve, limite
  definitive ou maintien experimental.
- [ ] Interdire la disparition silencieuse d'une recommandation : toute action
  fermee doit pointer vers un artefact et une date.
- [ ] Mettre a jour la matrice de maturite uniquement apres la decision Owner
  correspondante.
- [ ] Relancer `release-vv` et `qualification-readiness` apres chaque lot,
  jamais avant l'enregistrement des preuves.

### Etape ST-10 - release de maturite

- [ ] Executer les tests cibles de la famille modifiee apres chaque campagne.
- [ ] Executer la campagne complete uniquement apres fermeture d'un lot de
  promotions ou avant une release.
- [ ] Construire la distribution dans un checkout Git propre et verifier les
  artefacts en environnement Python neuf.
- [ ] Controler qu'aucun PDF, Markdown ou JSON public ne revendique une
  certification externe ou une capacite hors domaine.
- [ ] Produire `stable_promotion_summary.json`, les manifestes et le changelog.
- [ ] Marquer chaque scope comme `stable`, `owner_accepted`, `experimental` ou
  `research` avec une justification lisible et une preuve correspondante.

### Ordre recommande des prochains petits lots

1. ST-00 : figer les criteres et le schema de promotion.
2. ST-01 : fermer les recommandations et mettre a jour le ledger.
3. ST-02 : TET4/TET10 lineaires et dynamiques.
4. ST-03 : MITC3/MITC4 isotropes, shear locking et coques courbes.
5. ST-05 : BEAM2, discret et choix des solveurs.
6. ST-04 : composites et stratifies.
7. ST-06 : orthotropie et non-lineaire.
8. ST-07 : contact et grand modele.
9. ST-08 : dossiers V&V et seconde Owner review.
10. ST-09/ST-10 : fermeture des bounded et release de maturite.

Etat au 2026-08-20 : les decisions Owner du paquet 0.2.1 sont enregistrees
dans `qualification/reviews/owner_review_maturity_promotion_0_2_1_2026-08-20.json`.
Elles constituent un jalon de gouvernance et non une promotion automatique vers
`stable`. ST-00 est en place et le lot ST-01-A TET4 a ete reconduit.

### Avancement ST-01-A - correlation TET4 dynamique

- [x] Executer la correlation externe Code_Aster `18.1.0` dans Docker avec
  image epinglee par digest.
- [x] Comparer le meme maillage, la meme grille temporelle et la meme grille
  frequentielle sur le cantilever de reference : modal `2.738e-11`, Newmark
  `6.509e-13`, harmonique `6.970e-13` d'ecart relatif maximal.
- [x] Archiver le resultat dans
  `qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/code_aster_tet4_dynamic_final/`.
- [x] Remplacer le controle Euler non comparable par une reference 3D
  Code_Aster dans le rapport de preuve.
- [x] Ajouter une geometrie rectangulaire plus courte et plus epaisse : modal
  `2.345e-12`, Newmark `2.455e-13`, harmonique `2.280e-13`.
- [x] Ajouter une geometrie cylindrique : modal `5.668e-12`, Newmark
  `6.850e-13`, harmonique `1.309e-13`, avec increments modal et statique
  respectivement `3.720 %` et `5.188 %`.
- [x] Reprendre le controle statique de la geometrie rectangulaire epaisse avec
  cinq niveaux, jusqu'a `25 766` TET4 : increment final `4,972 %`, sous le
  seuil de `10 %`, sans relacher la tolerance.
- [ ] Faire la nouvelle Owner review et fermer formellement `REC-ST-013` a
  `REC-ST-016` avec les trois artefacts Code_Aster et leurs empreintes.

La fiche prete a completer est
`docs/verification/tet4_stable_promotion_owner_review_0_2_1.md`; son registre
machine-readable est `qualification/reviews/tet4_stable_promotion_owner_review_pending.json`.

## Plan de promotion vers `stable` - mise a jour Owner du 2026-08-20

Cette section devient la feuille de route active pour faire progresser les
scopes actuellement acceptes, sans transformer une decision Owner en
promotion automatique. Chaque promotion devra produire une preuve
reproductible, une fiche de decision signee et une mise a jour explicite de la
matrice de maturite.

### Regle commune de passage

Un scope ne peut passer a `stable` que si toutes les conditions suivantes sont
remplies :

1. Le domaine revendique est ecrit en termes de geometrie, materiau,
   chargement, conditions aux limites et route d'analyse.
2. Au moins trois familles de cas sont executees, avec au moins trois niveaux
   de maillage ou de pas pertinent.
3. Une grandeur principale converge et une grandeur secondaire est controlee
   hors singularite.
4. Les invariants numeriques, les residus, les bilans d'energie et les
   symetries attendues sont controles.
5. Une correlation analytique ou externe reproductible est disponible lorsque
   le modele de reference est applicable.
6. Les limites et exclusions sont presentes dans la documentation publique et
   dans le rapport de preuve.
7. La campagne complete est reproductible depuis une commande versionnee,
   avec manifeste, empreintes, versions et profil de verification.
8. Une Owner review repond a chaque question technique et contient un
   `promotion_target` explicite. Pour une cible `stable`, la decision ne peut
   pas etre `more_evidence_required`.
9. Chaque observable primaire applicable respecte la limite d'erreur relative
   `<= 1 %`. Aucun depassement ne peut etre ignore, compense par un autre
   indicateur ou converti en `PASS` sans justification mecanique formelle,
   campagne reproductible et decision Owner datee.

Le statut `accepted_with_recommendations` indique que le domaine est
acceptable mais que la promotion vers `stable` reste a instruire. Le statut
`accepted_for_bounded_engineering_use` autorise uniquement le domaine borne
ecrit dans la fiche ; il ne doit pas etre presente comme stable.

### ST-11 - Promotions techniques deja pretes

- [ ] Corriger les fiches Owner afin que la decision soit toujours placee sur
  la question `Q5` ou `Q6` qui la demande, et non sur une question technique.
- [x] Pour `beam2-linear-static`, preuve sur poutre elancee relue, exclusion
  des poutres epaisses conservee et cible `owner_accepted` enregistree.
- [x] Pour `discrete-linear`, cible `owner_accepted` enregistree ; les
  systemes multi-DDL couples et non lineaires restent exclus.
- [x] Remplacer le seuil historique de `tet4_final_deflection_error` par une
  campagne dynamique dediee aux observables modales/Newmark ; le seuil de
  promotion applicable est desormais `<= 1 %` sur la grandeur principale.
- [x] Enregistrer pour ces deux scopes la decision Owner
  `accepted_with_recommendations` et la cible intermediaire `owner_accepted`.
- [ ] Pour `large-tet4-linear-static`, conserver `accepted_for_bounded_engineering_use`
  jusqu'a la campagne de seconde configuration materielle et ne pas generaliser
  le resultat au HPC.

### ST-12 - Contact et discretisation non lineaire

- [ ] Contact frottant : ajouter la branche `stick` et une seconde geometrie
  externe de contact ; conserver les trois niveaux Code_Aster `200/250/300 N`
  comme preuve de la branche `slip`. Trois geometries internes sont maintenant
  executees dans `VNV-CONTACT-ADDITIONAL-MODELS-008`.
- [ ] Contact frottant : verifier les seuils de force tangentielle, pression
  normale, complementarity et energie de contact ; exclure grand glissement,
  impact et usure tant qu'ils ne sont pas prouves.
- [x] TET4 J2 : ajouter une correlation structurelle externe monotone au-dela du
  material-point, sur maillage TET4/TETRA4 identique et charges combinees.
- [ ] TET4 et TET10 J2 : etendre cette preuve a la decharge, l'inversion et le
  rechargement structurels externes.
- [ ] Comparer contrainte, deformation, force globale et energie plastique sur
  au moins deux geometries ; maintenir le statut borne tant que la preuve
  structurelle n'est pas complete.
- [x] Archiver les decisions Owner bornees pour contact, TET4 J2 et TET10 J2 ;
  elles n'autorisent pas encore la cible `stable`.

### ST-13 - MITC3 et MITC4 stratifies

- [ ] MITC3 stratifie dynamique : ajouter au moins un layup non symetrique,
  une geometrie courbe et un cas avec amortissement ; maintenir les exclusions
  du couplage B, des contraintes par pli dynamiques et de la delamination.
- [ ] MITC3 stratifie statique : ajouter une seconde geometrie courbe et un
  second chargement ; documenter la normalisation exacte du residu `1e-7`.
- [ ] MITC4 stratifie dynamique : conserver
  `accepted_for_bounded_engineering_use` ; ajouter amortissement, geometrie
  courbe et une campagne de raffinement temporel avant toute cible stable.
- [ ] Comparer les resultantes globales, les energies membrane/flexion/
  cisaillement et les contraintes par pli hors singularite.
- [x] Archiver les decisions Owner bornees MITC3 statique et dynamique ; les
  extensions de geometries, layups et amortissement restent requises.
- [x] Archiver la decision Owner MITC3 courbe en usage borne ; la seconde
  geometrie et la normalisation du residu restent des actions avant stable.

### ST-14 - TET4 Total Lagrangian : gate independant

- [ ] Maintenir `tet4-total-lagrangian-structural-v2` en
  `experimental/research` avec `more_evidence_required`.
- [ ] Organiser une revue independante de la formulation, de la mesure de
  convergence, des imperfection initiales et du post-flambement.
- [x] Generer le dossier de revue independante Markdown
  `docs/verification/tet4_total_lagrangian_independent_review_pack.md` et son
  PDF `output/pdf/qf_solver_tet4_total_lagrangian_independent_review_0_2_1.pdf`.
- [x] Actualiser le paquet le 21/08/2026 avec les valeurs quantitatives :
  erreur constitutive `0,008544 %`, ecart de chemin Code_Aster `1,7e-7 %`,
  ecart QF/CalculiX `0,034274 %`, mais erreur Euler au point raffine
  `1,895558 %`. Cette derniere grandeur reste diagnostique et empeche toute
  promotion stable sur cette preuve seule.
- [ ] Ajouter un cas de flambement lineaire, un cas post-flambement avec
  plusieurs imperfections et une comparaison externe reproductible.
- [ ] Ne pas fermer ce gate par une seule decision Owner ; archiver le rapport
  independant avant toute nouvelle proposition de maturite.

### ST-15 - Dossiers et decision de promotion

- [ ] Generer un dossier Markdown et PDF par scope avec : questions, reponses
  numeriques, figures maillage/deformee/champ, convergence, limites et
  references.
- [ ] Ajouter au manifeste la revision source, le profil, les versions des
  oracles, les empreintes et la liste des exigences couvertes.
- [ ] Faire controler chaque dossier par `maturity-promotion` puis executer les
  tests cibles de la famille modifiee.
- [ ] Enregistrer la fiche Owner datee avec `promotion_target` explicite.
- [ ] Modifier la matrice de maturite uniquement apres validation du dossier ;
  relancer `release-vv` et `qualification-readiness` ensuite.

### Ordre des promotions

1. `beam2-linear-static` et `discrete-linear` vers `owner_accepted`.
2. Orthotropie modal/transitoire vers `owner_accepted` apres clarification du
   seuil `0.11752`.
3. Contact, TET4 J2 et TET10 J2 en usage borne avec preuves structurelles.
4. MITC3 et MITC4 stratifies avec nouvelles geometries, layups et amortissement.
5. Grand modele apres seconde configuration de scaling.
6. TET4 Total Lagrangian uniquement apres revue independante.
7. Promotion vers `stable` scope par scope lorsque les huit regles communes
   sont satisfaites, jamais par lot aveugle.

### ST-16 - Première vague de promotion stable prête pour Owner

- [x] Vérifier techniquement `beam2-linear-dynamics` : résidu modal
  `1,175e-12`, erreur modale Code_Aster maximale `0,02649 %`, erreur RMS
  Newmark `0,01437 %`, incrément temporel final `0,47210 %` et harmonique à
  `0 Hz` exacte.
- [x] Vérifier techniquement `discrete-linear-dynamics` : résidu modal
  `1,798e-16`, erreur RMS Newmark `0,01437 %`, dérive énergétique `3,800e-13`
  et corrélation Code_Aster `DIS_T` PASS.
- [x] Conserver les versions et digests Code_Aster dans les preuves externes.
- [x] Créer le dossier de décision ciblé
  `docs/verification/beam2_discrete_dynamics_stable_owner_review.md` et son
  registre `qualification/reviews/beam2_discrete_dynamics_stable_owner_review_pending.json`.
- [ ] Faire répondre l'Owner aux cinq questions du dossier, séparément pour
  BEAM2 et le système discret.
- [ ] Enregistrer `promotion_target: stable` et la décision datée uniquement
  après la revue; relancer ensuite `maturity-promotion` et `release-vv`.

Cette première vague est volontairement limitée aux domaines linéaires décrits.
Elle ne transforme pas les résultats en validation générale des poutres,
systèmes multi-DDL ou dynamiques amorties.

### ST-17 - Dossiers Owner déjà prêts pour les solides et extensions

- [x] Rattacher `tet10_stable_promotion_owner_review_pending.json` à la matrice
  de couverture. Les scopes TET10 statique, modal, Newmark et harmonique sont
  techniquement PASS et attendent une décision Owner ciblée `stable`.
- [x] Rattacher `tet4_stable_promotion_owner_review_pending.json` au suivi
  TET4. Les scopes TET4 modal, Newmark et harmonique sont techniquement PASS;
  le TET4 statique reste séparément bloqué par l'erreur de flexion à `1,217644 %`.
- [x] Ouvrir une Owner review dédiée au sous-périmètre `mitc4-laminate-static`
  plan régulier : trois chargements, corrélation NAFEMS/Code_Aster et
  observables principales sous `1 %`. Le dossier reste en attente de décision
  et ne promeut pas automatiquement le scope.
- [x] Conserver `tet4-total-lagrangian-structural-v2` en attente de revue
  indépendante; sa promotion ne peut pas être déduite des résultats linéaires.
- [x] Conserver les dossiers orthotropes modal et transitoire avec leur cible
  stable et leurs fiches Owner séparées; aucune extrapolation au composite
  pli-par-pli n'est autorisée.
- [ ] Faire signer les dossiers TET10, TET4 dynamique et orthotrope scope par
  scope; une signature doit contenir la décision, la date et le
  `promotion_target` correspondant.
- [ ] Relancer le readiness global après chaque décision et vérifier qu'aucun
  chemin de preuve n'est manquant.

### ST-18 - MITC3 isotrope classique séparé du stratifié

- [x] Vérifier la campagne `8x2 -> 16x4 -> 24x6` : erreurs finales `0,673329 %`
  modal, `0,174158 %` Newmark et `0,096638 %` harmonique.
- [x] Vérifier les invariants internes : résidu modal `4,391e-9`, dérive
  énergétique `6,877e-13`, résidu dynamique `6,556e-14` et limite harmonique
  à `0 Hz` de `1,521e-13`.
- [x] Créer le dossier
  `docs/verification/mitc3_classic_stable_owner_review.md` et le registre
  `qualification/reviews/mitc3_classic_stable_owner_review_pending.json`.
- [x] Rattacher le dossier à la matrice de couverture; le readiness indique
  maintenant `READY_FOR_OWNER_REVIEW` pour les trois scopes isotropes.
- [ ] Faire statuer séparément le modal, Newmark et harmonique.
- [ ] Ne pas utiliser cette preuve pour le MITC3 stratifié ou courbe, dont les
  gates restent indépendants et potentiellement bloqués.

### Commandes de controle

```powershell
python .\qf_solver.py maturity-promotion --output .\results\maturity_promotion_0_2_1
python .\qf_solver.py qualification-readiness --scope <scope>
python -m pytest tests\unit tests\verification -k "<scope>" -q
python .\qf_solver.py release-vv --profile engineering
```

Etat de depart : les decisions Owner du 2026-08-20 sont archivees, mais les
promotions techniques restent bloquees tant que les fiches individuelles et
leurs `promotion_target` ne sont pas enregistres. Le scope MITC4 multicouche
dynamique a maintenant un gate technique PASS et attend sa Owner Review. Les
trois blocages techniques restants sont MITC3 multicouche dynamique, MITC3
multicouche courbe statique et TET4 Total Lagrangian. Le prochain lot est donc
la clarification de la formulation MITC3 dynamique, puis la revue independante
TET4 Total Lagrangian ; aucune promotion n'est automatique.

### Tableau global de readiness stable

Le script ci-dessous genere un tableau machine-readable et un resume Markdown
avant toute nouvelle Owner Review :

```powershell
python .\scripts\build_stable_scope_readiness.py
```

Artefacts generes :

- `results/stable_promotion_readiness_0_2_1/stable_scope_readiness.json`
- `results/stable_promotion_readiness_0_2_1/stable_scope_readiness.md`

La regle commune de promotion est desormais une erreur relative maximale de
`1 %` pour les observables principaux : deplacement, frequence, reponse
harmonique, RMS Newmark, reaction/resultante, energie et contrainte ou
deformation hors singularite. Une valeur superieure a `1 %` bloque la
promotion stable, sauf justification mecanique formelle accompagnee d'un
raffinement supplementaire et d'une decision Owner explicite.

Cette limite devient egalement la regle de fermeture des campagnes V&V : a
partir de cette baseline, toute comparaison primaire publiee pour un element,
une methode ou un scope doit rester inferieure ou egale a `1 %`. Une campagne
qui depasse `1 %` reste ouverte, meme si elle passe un ancien seuil
engineering; elle doit recevoir un raffinement, une justification mecanique
formelle et une decision Owner explicite avant toute promotion. Cette regle ne
remplace pas les seuils specifiques des residus, de la convergence iterative,
des increments de maillage ou des erreurs de quadrature, qui restent controles
separement.

Le readiness courant identifie encore des depassements de ce seuil dans
plusieurs campagnes MITC4 et dans quelques resultats TET10. Ces points ne sont
pas declares stables : ils doivent d'abord faire l'objet d'un raffinement de
maillage ou de temps, d'une verification de l'observable et, si necessaire,
d'une correlation externe. Le tableau est un indicateur de preparation et ne
realise aucune promotion automatique. Il liste l'ensemble des scopes audites,
y compris ceux qui ont encore une cible intermediaire ou un statut borne; aucun
scope ne doit disparaitre du suivi parce qu'il n'est pas encore candidat a
`stable`.

### Blocages techniques actuels a traiter

Le garde-fou machine `STABLE-1PCT-POLICY` surveille les scopes suivants. Les
lignes sous `1 %` sont techniquement conformes et attendent seulement la
revue Owner; les lignes au-dessus de `1 %` restent bloquees.

| Scope | Observable depassant 1 % | Valeur observee | Action avant Owner Review stable |
| --- | --- | ---: | --- |
| `mitc4-linear-static` | ferme par raffinement : 0,726108 % | 0,726108 % | Owner Review cible `stable` encore requise |
| `mitc4-modal` | ferme par raffinement Code_Aster : 0,782014 % | 0,782014 % | Owner Review cible `stable` encore requise |
| `mitc4-transient-dynamic` | ferme techniquement par oracle temporel : RMS 0,09867227 % | 0,09867227 % primaire ; 5,2114 % / 10,5047 % model-form secondaire | Owner Review cible `stable`; conserver les ecarts Code_Aster comme diagnostics spatiaux |
| `mitc4-harmonic-response` | candidate par raffinement theorie : 0,547102 % au niveau final | 0,547102 % final ; 3,730001 % / 2,635265 % intermediaires | Owner Review cible `stable`, avec depassements intermediaires conserves |
| `mitc4-laminate-static` | difference de vecteur fine | 2,043415 % | Promotion `stable` bloquee : difference de forme MITC4 facettise / CalculiX S8R apres six niveaux ; oracle de meme ordre ou justification mecanique formelle requis |
| `tet10-linear-static` | ferme par raffinement : 0,992738 % | 0,992738 % | Owner Review cible `stable` encore requise |

Le statut technique `PASS` historique de ces campagnes est conserve comme
preuve de verification, mais il ne suffit plus pour `stable` depuis l'adoption
de la limite a 1 %. Une Owner Review ne peut justifier une exception que si une
analyse mecanique formelle, une convergence supplementaire et la decision
explicite sont archivees.

Le TET10 statique est le premier scope dont la campagne supplementaire respecte
la limite : six niveaux, erreur de flexion finale `0,992738 %` et residu libre
maximal `1,05e-10`. Cette campagne est maintenant la preuve de reference pour la
prochaine Owner Review ; elle ne modifie pas encore la matrice de maturite.

La correlation MITC4 statique est egalement sous la limite : cinq niveaux
Code_Aster, ecart vecteur deplacement final `0,726108 %`, ecart de sonde
`0,144620 %` et ecart de resultante `5,55e-13`. Elle est prete pour une Owner
Review technique ; aucun changement de maturite n'est applique automatiquement.

La correlation MITC4 modale est maintenant egalement sous la limite : campagne
Code_Aster sur plaque `48x48`, dix modes, ecart maximal de frequence
`0,782014 %`, MAC minimal `0,99999981`, residu modal maximal `1,10e-8`.
Le dossier est pret pour une Owner Review visant `stable`; la matrice reste
inchangée jusqu'a cette decision datee.

La campagne MITC4 harmonique comporte trois niveaux `8x8`, `12x12` et `16x16`.
Les erreurs maximales primaires sont respectivement `3,730001 %`, `2,635265 %`
et `0,547102 %`; les depassements des niveaux intermediaires restent archives.
Le niveau final passe sous 1 % pour le deplacement, la frequence et la
contrainte hors singularite. Le scope devient candidat a Owner Review, sans
promotion automatique et sans effacer l'historique des niveaux precedents.

Le MITC4 transitoire est maintenant traite avec une separation explicite des
observables. La grandeur primaire de Newmark est l'erreur RMS face a la
propagation modale exacte independante, `0,09867227 %`, avec energie et residu
controles. Les ecarts Code_Aster de pics `5,2114 %` en deplacement et
`10,5047 %` en contrainte sont conserves comme diagnostics de difference de
formulation spatiale MITC4/DKQ; ils ne sont pas presentes comme une erreur de
l'integration temporelle. Cette distinction est tracee dans les criteres
machine et devra etre relue avant la promotion stable.

Le TET10 transitoire a egalement ete renforce par une campagne temporelle
independante `T/30`, `T/60`, `T/120` et `T/240`. L'erreur RMS finale face a la
propagation modale vaut `0,014369 %` et l'increment adjacent final vaut
`0,472096 %`, avec une derive energetique de `4,73e-11 %` et un residu maximal
de `3,67e-8`. Le maximum des niveaux grossiers (`3,759715 %`) reste publie
comme diagnostic de demarrage et ne remplace pas le critere de stabilisation
final. Le dossier est techniquement pret pour une Owner Review cible `stable`;
aucune maturite n'est modifiee automatiquement.

La campagne MITC4 multicouche courbe oblique a ete raffinee jusqu'a `192x96`
(`18 432` elements). L'ecart vectoriel final QF_solver/CalculiX reste de
`2,043415 %` et l'ecart de la sonde `UZ` de `2,047208 %`, alors que les
increments de maillage fin sont respectivement `0,220046 %` et `0,019243 %`.
Le raffinement montre donc une stabilisation numerique, mais pas une
convergence vers la meme formulation : MITC4 lineaire facettise et CalculiX
S8R quadratique courbe constituent des modeles differents. Le resultat est
archive comme preuve negative utile et le scope reste
`accepted_for_bounded_engineering_use`; il ne peut pas etre promu `stable` tant
que l'observable primaire depasse `1 %`.

Une sonde d'oracle de meme ordre a ete tentee le 21/08/2026 avec CalculiX
`S4 COMPOSITE` sur la meme surface facettisee. CalculiX 2.20 refuse cette
combinaison et limite la carte composite aux elements `S8R` ou `S6`. Aucun
resultat n'a donc ete utilise pour l'acceptation. Cette impossibilite est
tracee dans `docs/verification/mitc4_same_order_oracle_probe.md`; elle confirme
que l'ecart de `2,043415 %` ne doit pas etre transforme en promotion artificielle.

## MITC3 courbe axial : diagnostic de comparabilite externe (21/08/2026)

Une reference CalculiX `S6 COMPOSITE` a ete executee sur le cas axial courbe,
avec le meme maillage `64x32`, les memes resultantes et le meme modele QF_solver.
La reproductibilite de la reponse QF entre les deux chemins vaut `1,37e-16`.
Les ecarts observes sont :

| Comparaison | Ecart vectoriel UX/UZ |
| --- | ---: |
| QF_solver / Code_Aster DST | `0,9066 %` |
| QF_solver / CalculiX S6 | `6,4197 %` |
| Code_Aster DST / CalculiX S6 | `7,5910 %` |

Conclusion : le cas axial est sensible a la formulation de coque externe et
ne peut pas etre explique par un pas de temps, puisqu'il est statique. Le
raffinement seul ne justifie pas une promotion `stable` generale. Le scope
reste bloque, tandis que le diagnostic est conserve comme preuve de
comparabilite et comme base pour une reference de meme ordre ou une seconde
geometrie courbe.

Artefacts :

- `qualification/vnv/external/calculix_mitc3_curved_laminate_axial_2026-08-21/reference/` ;
- `qualification/vnv/external/mitc3_curved_axial_reference_audit_2026-08-21/` ;
- `docs/verification/mitc3_laminate_curved_code_aster.md`.

## MITC4 orthotrope homogène mono-pli : paquet de promotion stable (21/08/2026)

Le paquet `VNV-MITC4-STABLE-PACKAGE-001` est maintenant prêt pour une Owner
Review dédiée. Il couvre une lamelle orthotrope homogène dans `shell_laminate`,
les calculs statique, modal, Newmark et harmonique, ainsi qu'une plaque plane
et un panneau courbe facettisé.

Les observables primaires des plaques planes sont sous `1 %` pour les axes
`0°`, `45°` et `90°`. Le cas modal `45°` a été raffiné à `56 x 14` et atteint
`0,884 %`; le cas `90°` atteint `0,604 %` à `48 x 12`. Les réponses Newmark et
harmoniques restent sous `1 %` sur les niveaux finaux retenus.

Une corrélation CalculiX externe du panneau courbe axial mono-pli `0°` atteint
`0,012 %` sur `UZ` au maillage `24 x 12`. L'orientation non axiale projetée
`45°` sur une surface courbe reste ouverte : le deck externe ne reproduit pas
encore la même loi locale d'orientation par facette. Cette exclusion est
obligatoire dans la décision stable proposée.

Artefacts de la campagne :

- `qualification/studies/mitc4_stable_package_2026-08-21/study.json` ;
- `docs/verification/mitc4_stable_package/README.md` ;
- `docs/verification/mitc4_stable_package/campaign_matrix.md` ;
- `docs/verification/mitc4_stable_package/orthotropic_one_ply_results_2026-08-21.md` ;
- `docs/verification/mitc4_stable_package/owner_review.md` ;
- `results/mitc4_orthotropic_modal_codeaster_20260821_56x14/` ;
- `results/mitc4_orthotropic_curved_axial_one_ply_calculix_20260821/`.

Action restante : faire relire et signer `owner_review.md`. La signature ne
doit couvrir que le périmètre borné documenté; elle ne doit pas promouvoir
l'orientation continue non axiale sur surface courbe, le dommage, la rupture,
la délamination ou les contraintes interlaminaires.

## Dossiers Owner Review a valider avant audit final - 2026-08-21

Un paquet de preparation consolide les preuves deja disponibles pour les
perimetres qui ne sont pas encore stables ou qui restent bornes :

- Markdown : `docs/verification/owner_review_scope_closure_2026-08-21.md` ;
- JSON machine-readable :
  `qualification/reviews/owner_review_scope_closure_2026-08-21.json` ;
- PDF lisible :
  `output/pdf/qf_solver_owner_review_scope_closure_2026-08-21.pdf` ;
- generateur reproductible :
  `scripts/build_scope_closure_owner_review_pack.py`.

Le paquet contient quatorze sections, avec mesures, limites, references,
figures disponibles et questions a repondre. Il a ete produit a partir des
archives existantes et n'a lance aucun calcul. Aucune maturite n'a ete
modifiee et aucune signature n'a ete ajoutee.

| Famille | Perimetre prepare | Etat de preparation | Decision a fournir |
| --- | --- | --- | --- |
| MITC3 multicouche | statique plane, dynamique mince plane | preuves disponibles; sous-perimetre dynamique candidat | Owner Review par sous-perimetre |
| MITC3 courbe | mixte/transverse, axial complet | mixte/transverse candidat borne; axial bloque | accepter le sous-perimetre ou demander plus d'evidence |
| TET4 non-lineaire | total-lagrangien et J2 | experimental/recherche, gates independants | maintenir borne ou demander plus d'evidence |
| TET10 non-lineaire | J2 petites deformations | experimental borne | decision d'usage borne |
| Solides orthotropes | statique, modal, Newmark | pret pour Owner Review | owner_accepted ou recommandations |
| Contact | sans frottement, frottement | sans frottement borne; frottement experimental | maintenir les exclusions |
| Grand modele | TET4 PETSc/MPI | PASS avec scaling limite | accepter le domaine machine borne |
| MITC4 orthotrope courbe | orientation courbe non axiale | hors acceptance | aucune promotion |

### Regles de decision

1. Repondre a chaque question dans le PDF et reporter la meme decision dans le
   JSON associe.
2. Ne pas transformer un `PASS` technique en `stable` sans verifier le domaine
   exact, les observables primaires et la limite d'erreur applicable.
3. Conserver `more_evidence_required` lorsqu'une preuve independante, une
   seconde geometrie ou une comparabilite externe manque.
4. Garder MITC4 orthotrope courbe hors acceptance; les preuves MITC4 planes ou
   les solides orthotropes ne peuvent pas etre reutilises pour ce cas.
5. Apres la relecture, seulement mettre a jour les registres de maturite,
   regenerer l'audit et preparer la release. Aucun changement automatique ne
   doit etre deduit du PDF.

### Ordre recommande pour la revue

1. MITC3 dynamique mince plane et MITC3 courbe mixte/transverse.
2. Solides orthotropes statiques, modal et Newmark.
3. TET4/TET10 J2 et TET4 total-lagrangien.
4. Contact sans frottement puis contact avec frottement.
5. Grand modele PETSc/MPI.
6. Confirmer explicitement l'exclusion MITC4 orthotrope courbe.

Le prochain travail apres les reponses Owner est l'audit global : coherence
des registres, absence de doublons documentaires, verification des artefacts et
controle final de publication. Aucun calcul lourd n'est necessaire pour cette
phase de lecture.

## Decisions Owner declarees le 22 aout 2026 - application apres audit

La declaration Owner du 22 aout 2026 est archivee dans :

- `qualification/reviews/owner_review_scope_decisions_2026-08-22.json` ;
- `docs/verification/owner_review_scope_decisions_2026-08-22.md` ;
- `output/pdf/qf_solver_owner_review_scope_decisions_2026-08-22.pdf`.

Elle comprend les orientations suivantes, sans modifier automatiquement les
registres de maturite :

| Perimetre | Decision Owner declaree | Limite de lecture |
| --- | --- | --- |
| MITC3 multicouche statique plane | `accepted_for_bounded_engineering_use` | Ajouter deux layups avant toute stabilite |
| MITC3 multicouche dynamique mince plane | `stable` | Sous-perimetre mince, plan et symetrique uniquement |
| MITC3 courbe mixte/transverse | `stable` | Sous-perimetre borne; axial exclu |
| MITC3 courbe axial complet | `accepted_for_bounded_engineering_use` | Comparabilite externe encore ouverte |
| TET4 total-lagrangien | `more_evidence_required` | Cas 1,2 M d'elements a etudier; revue independante requise |
| TET4/TET10 J2 | `accepted_for_bounded_engineering_use` | Plan J2 enrichi reporte a une etape ulterieure |
| Solides orthotropes statique/modal/Newmark | `stable` | Homogene, domaine documente; courbe continue exclue |
| Contact sans frottement / frottement | `accepted_for_bounded_engineering_use` | Pas de contact general, impact ou usure |
| Grand modele TET4 | `accepted_for_bounded_engineering_use` | Configuration PETSc/MPI mesuree; scaling a renforcer |
| MITC4 orthotrope courbe | aucune decision | Hors acceptance, diagnostic uniquement |

### Travaux ajoutes pour la prochaine etape

#### MITC3 multicouche statique : deux layups supplementaires

Ajouter au minimum les deux empilements symetriques suivants, avec le meme
patch, les memes observables et les memes niveaux de maillage :

1. `[0/45/45/0]` ;
2. `[45/0/0/45]`.

Les contraintes par pli resteront limitees a `S11`, `S22` et `S12` hors bords
libres. `S13`, `S23`, dommage et delamination restent exclus.

#### TET4 total-lagrangien : campagne de raffinement ciblee

Un calcul cible d'environ `1 200 000` TET4 pourra mesurer la tendance de la
charge critique, de la fleche, du residu, de la memoire et du temps. Ce calcul
ne sera pas lance dans cette etape documentaire et ne garantit pas une erreur
inferieure a `1 %`. La promotion stable exigera aussi la revue independante,
la verification de la branche post-critique et la confirmation que le critere
choisi est bien la grandeur d'acceptation.

#### J2 et robustesse des increments non lineaires

Pour la prochaine version, preparer une matrice de preuves comprenant
chargement, decharge, rechargement, cyclage, plasticite parfaite, ecrouissage,
chargement multiaxial et une seconde structure. Les sous-resolutions KSP/PC,
les tangentes, la line-search, les residus et le nombre d'increments devront
etre traces. La recommandation reste `10` increments par defaut avec `6` comme
minimum, mais la convergence devra etre justifiee par le residu et non par un
nombre fixe de pas.

#### Interpretation de « KRM SPIC »

Le terme est conserve comme point a clarifier. Pour la feuille de route, il est
interprete provisoirement comme le choix et le diagnostic des solveurs KSP/PC
et de la robustesse des sous-iterations dans les calculs non lineaires. Cette
interpretation devra etre confirmee avant de modifier le code.

## Plan V&V execute : MITC3, TET4 total-lagrangien et orthotropie - 22 aout 2026

Le plan et les preuves de cette etape sont maintenant regroupes dans :

- `docs/verification/vnv_plan_mitc3_tet4_orthotropic_2026-08-22.md` ;
- `qualification/vnv/vnv_plan_mitc3_tet4_orthotropic_2026-08-22.json` ;
- `output/pdf/qf_solver_vnv_mitc3_tet4_orthotropic_2026-08-22.pdf` ;
- `scripts/build_vnv_mitc3_tet4_orthotropic_pdf.py`.

### Resultat de la campagne

| Perimetre | Resultat mesure | Decision de travail |
| --- | --- | --- |
| MITC3 dynamique mince plan | modal `0,3940 %`, Newmark `0,1968 %`, harmonique `0,0880 %` | `stable` borne au plan mince symetrique |
| MITC3 courbe mixte/transverse | `0,5780 %` et `0,4975 %`, increments proches de `5 %` | `stable` borne avec recommandation |
| Orthotropie statique TET4/TET10 | TET4 `0,8772 %`, TET10 `0,2918 %` | `stable` homogene statique documente |
| TET4 total-lagrangien | Euler h5 `1,8956 %`, CalculiX `0,0343 %`, post-flambement PASS recherche | `more_evidence_required`, reste `research` |

La campagne ciblee a donne `13 passed, 6 skipped`. Le flambement TET4-TL a
donne `1 passed` et le post-flambement `1 passed`. La suite complete du projet
n'a pas ete relancee dans cette etape.

### Fermetures et actions restantes

1. Conserver les trois decisions stables uniquement dans leurs sous-perimetres
   et ne pas les extrapoler aux cas courbes continus, non symetriques,
   interlaminaires ou endommages.
2. Pour MITC3 courbe, ajouter une seconde geometrie et un second layup ; le
   chargement axial reste hors stable tant que l'increment et la comparabilite
   externe ne sont pas fermes.
3. Pour TET4 total-lagrangien, lancer plus tard la campagne d'environ `1,2 M`
   d'elements avec mesure des ressources, du chemin de charge, de `det(F)`, des
   residus et de l'erreur ; un resultat sous `1 %` ne suffira pas seul.
4. Obtenir une revue independante du TET4-TL avant toute qualification externe.
5. Apres les revues Owner, synchroniser les registres de maturite, puis faire
   l'audit final des chemins, empreintes, limites et documents actifs.

## Confirmation Owner et tickets TET4 total-lagrangien phase 2 - 22 aout 2026

Les trois decisions suivantes sont maintenant confirmees dans un addendum
Owner, sans extension de leur domaine :

- MITC3 dynamique mince plan : `stable` dans le sous-perimetre `[0/90/90/0]`,
  plan, mince, symetrique ;
- MITC3 courbe mixte/transverse : `stable_bounded` sur le panneau facettise et
  les deux chargements testes ;
- orthotropie statique TET4/TET10 : `stable` pour le solide homogene a
  orientation constante documente.

Documents de trace :

- `docs/verification/owner_validation_addendum_mitc3_orthotropic_2026-08-22.md` ;
- `qualification/reviews/owner_validation_addendum_mitc3_orthotropic_2026-08-22.json`.

Le lot suivant est ouvert pour le TET4 total-lagrangien :

- plan : `docs/verification/tet4_total_lagrangian_phase2_roadmap_2026-08-22.md` ;
- tickets : `qualification/tickets/tet4_total_lagrangian_phase2_2026-08-22.json`.

Le lot comprend la definition de l'observable, le raffinement vers environ
`1,2 M` d'elements, les diagnostics tangent/residu/determinant, la mesure des
ressources, la robustesse des imperfections et des increments, une correlation
de la branche effectivement revendiquee et une revue independante. Le TET4-TL
reste `research / more_evidence_required` jusqu'a fermeture de ces gates.
