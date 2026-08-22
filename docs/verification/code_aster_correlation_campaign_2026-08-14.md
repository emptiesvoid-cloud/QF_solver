---
doc_id: DOC-VNV-CODEASTER-CAMPAIGN-2026-08-14
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.1-alpha
owner_review: pending
reviewer: ""
approver: ""
---

# Campagne de corrélation Code_Aster du 2026-08-14

**Projet :** QF_solver  
**Type de campagne :** corrélation externe reproductible  
**Statut documentaire :** résultats prêts pour Owner review  
**Maturité :** aucune promotion automatique  
**Oracle :** Code_Aster 18.1.0, image Docker épinglée dans le code

## Objet

Cette campagne reprend les corrélations externes demandées avant la prochaine
Owner review. Chaque cas est exécuté séparément et produit un dossier local
avec le modèle, le jeu de commandes Code_Aster, les résultats normalisés, les
figures, le rapport et le manifeste d'empreintes.

Les dossiers de preuve générés localement se trouvent sous
`tmp/code_aster/`. Ils sont volontairement exclus du dépôt tant que la
politique d'archivage des preuves n'a pas été revue. Cette page ne transforme
donc pas ces résultats en preuve publique ou en qualification.

Le catalogue machine-readable associe est
`qualification/external_reference_digests/code_aster_correlation_campaign_2026-08-14.json`.
Il contient les statuts, la revision source, l'environnement et les
empreintes SHA-256 des fichiers presents localement.

Un paquet de preuve controle a egalement ete genere dans
`qualification/evidence/code_aster_correlation_campaign_2026-08-14/`. Il
contient uniquement les resumes, rapports, manifestes et figures utiles; les
fichiers de travail Code_Aster lourds restent exclus. Son manifeste v2 est
verifie par `verify-evidence` sur `239` fichiers et le gate de release expose
le controle `EVIDENCE-BUNDLE-CODE-ASTER-CORRELATION-2026-08-14=PASS`.
Les chemins du paquet sont relatifs au depot et ne contiennent pas
d'executable Python, de chemin utilisateur ou de metadonnees d'outillage interne.

Le catalogue courant contient `52` dossiers actifs : `36` corrélations externes
réussies, `1` avertissement et `13` échecs numériques explicitement conservés.
Deux dossiers restent indisponibles. Le calcul TET4
dynamique grossier (`h=0,42`) est conservé dans `excluded_directories` comme
étude historique supersédée par le rerun raffiné `h=0,30`; il n'est donc plus
compté comme avertissement actif.
Les treize échecs correspondent principalement aux tentatives MITC4 modal sur
`200 x 50` et à des essais historiques conservés ; ils
ne sont pas comptés comme des corrélations réussies. Les trois runners
historiques auparavant indisponibles ont été reconstruits à partir de leurs
modèles contrôlés et exécutés avec Code_Aster.

## Environnement

| Paramètre | Valeur |
|---|---|
| Solveur externe | Code_Aster |
| Version | 18.1.0 |
| Backend | Docker Desktop / Linux engine |
| Image | `simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435` |
| Date d'exécution | 2026-08-14 |
| Politique | théorie -> Code_Aster -> CalculiX lorsque comparable |

## Résultats

| Famille | Étude | Résultat | Commentaire |
|---|---|---|---|
| TET4 | dynamique modal/Newmark/harmonique `h=0,42` | `SUPERSEDED` | étude historique; remplacée par le protocole raffiné `h=0,30` |
| TET4 | dynamique raffiné `h=0,30` | `PASS_EXTERNAL_CORRELATION` | 313 éléments; incrément modal 0,083 %, statique 4,87 % |
| TET10 | dynamique modal/Newmark/harmonique | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| TET10 J2 | équerre rentrante, deux niveaux de maillage | `PASS_EXTERNAL_CORRELATION` | `457` puis `1 031` éléments; incrément déplacement 0,1885 %, PEEQ 5,13 %, résidu QF 1,97e-9 |
| MITC3 | statique DKT | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC3 | dynamique DKT | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC3 stratifié | dynamique DST | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC3 stratifié courbe | statique DST, orientation projetée | `PASS_EXTERNAL_CORRELATION` | `64 x 32`, `4 096` triangles, écart fin `0,578 %`, incréments finaux sous `5 %` |
| MITC3 | hémisphère pincé DKT | `PASS_EXTERNAL_CORRELATION` | six niveaux, écart QF/Code_Aster final `0,0927 %`, figures de déformée et champ |
| MITC4 | découpe conique DKQ | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC4 stratifié | dynamique DST | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC4 stratifié | orientations de plis DST | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC4 stratifié | modal contrôlé `40 x 10` | `PASS_EXTERNAL_CORRELATION` | écart maximal `0,70194 %`; résidu QF_solver `8,66e-9` |
| MITC4 | modal `32 x 32`, 10 modes | `PASS_EXTERNAL_CORRELATION` | écart QF/Code_Aster maximal `1,872 %`; MAC minimal `0,99999968` |
| MITC4 | Newmark NAFEMS 13H | `PASS_EXTERNAL_CORRELATION` | corrélation UZ `0,954091`; pic UZ `5,211 %`; pic S11 `10,505 %` |
| MITC4 | harmonique NAFEMS 13H | `PASS_EXTERNAL_CORRELATION` | fréquence QF/Code_Aster `3,364 %`; UZ `1,945 %`; S11 `3,245 %` |
| BEAM2 | modal | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| BEAM2 | Newmark | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| BEAM2 | dynamique transverse | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| discret | ressort-masse SDOF | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | cas additionnel | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | surface pliée normale | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | recherche surface pliée | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | TET4 maître | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | frottement | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| J2 | VMIS isotrope linéaire | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| TET10 J2 | cas structurel | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| TET10 J2 | cas complexe | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| RBE2 | bras rigide | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| contact | liaison normale historique | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| TET4 | TL structural avec imperfections | `PASS_EXTERNAL_CORRELATION` | comparaison externe réussie |
| MITC4 stratifié | modal 10k | `QF_NUMERICAL_FAILURE_REFERENCE_AVAILABLE` | référence Code_Aster disponible; `eigsh` et `LOBPCG` QF non convergents |

## Détail TET4 dynamique

Le cas TET4 est conservé en `WARNING` pour une raison de convergence spatiale,
et non pour une différence entre les implémentations. Sur le maillage commun,
les écarts relatifs mesurés sont :

| Vérification | Écart relatif |
|---|---:|
| fréquences modales | `6,53e-13` |
| historique Newmark | `5,93e-13` |
| réponse harmonique | `8,62e-13` |
| raffinement spatial de la première fréquence | `2,49e-1` |

Le dernier indicateur dépasse la limite actuelle de `0,10`. Un maillage plus
fin doit être ajouté avant de conclure sur la convergence spatiale TET4. Le
résultat actuel est donc utile pour la corrélation même-maillage, mais ne doit
pas être présenté comme une convergence finale.

Le rerun `h=0,30` fournit désormais trois niveaux avec `100`, `202` et `313`
éléments. L'incrément modal final vaut `8,27e-4`, l'incrément statique
`4,87e-2`, l'écart Newmark même maillage `1,14e-12` et l'écart harmonique
`2,72e-12`. Ce résultat est prêt pour Owner review; il ne modifie pas seul la
maturité de TET4 dynamique.

## Cas lourds et runners historiques

Le cas MITC4 modal stratifié `200 x 50` a été exécuté. Code_Aster a produit
sa référence et sa figure de comparaison, mais le calcul QF_solver n'a pas
atteint le résidu modal requis de `1e-7`. Le résultat est conservé comme
diagnostic de robustesse du solveur itératif, pas comme corrélation validée.

Une variante `eigsh` avec shift spectral de `1 Hz` et condensation explicite
converge sur le probe `40 x 10` avec un résidu `8,66e-9` et un écart maximal
de `0,70194 %`. Sur `200 x 50`, la condensation explicite dépasse toutefois la
mémoire disponible. Le chemin lazy reste nécessaire pour les gros modèles.

Une seconde tentative `eigsh` avec shift spectral, ILU et préconditionneur
creux approché du complément de Schur a stabilisé la mémoire autour de
`422 Mo`, mais a encore terminé avec `info=500` dans GMRES avant d'atteindre
le résidu modal `1e-7`. Cette tentative est archivée séparément sous
`tmp/code_aster/mitc4_modal_10k_eigsh_lazy_schur/`. Une troisième tentative
`LOBPCG + ILU` avec condensation lazy échoue dès l'itération initiale et
produit un résidu de travail de l'ordre de `7,1e10`; elle est archivée sous
`tmp/code_aster/mitc4_modal_10k_lobpcg_spilu_lazy/`. Le point ouvert est donc
désormais identifié comme une limite de convergence du solveur modal itératif
à environ `10 000` QUAD4, et non comme une divergence de Code_Aster ou une
incohérence de formulation observée sur le cas contrôlé `40 x 10`.

Le correctif appliqué après le premier diagnostic relève le seuil relatif de
détection de fuite de masse du drilling à `1e-10`. Cette fuite provient de la
projection d'un repère nodal moyen sur une coque facettisée courbe; elle ne
correspond pas à une inertie physique et est condensée. Le rerun contrôlé
`tmp/code_aster/mitc4_modal_code_aster_control_400_rerun/` conserve la
corrélation : écart maximal `0,70194 %` et résidu `8,66e-9`.

Les trois runners historiques ont été réparés avec des entrées contrôlées :
`qualification/vnv/external/code_aster_modal/plate_modal.comm.template`,
`qualification/vnv/external/code_aster_newmark/nafems13h_newmark.comm.template`
et `qualification/vnv/external/code_aster_nafems13h/nafems13h_code_aster.comm.template`.
Les sorties ont été exécutées dans Docker puis normalisées avec les mêmes
conventions de nœuds, de blocages et de grandeurs que QF_solver. Les rapports,
figures, résultats bruts et manifestes sont maintenant inclus dans le paquet
de preuve contrôlé. Cela ferme l'indisponibilité de la chaîne, mais ne ferme
pas la revue Owner ni la décision de maturité.

## Décision proposée pour Owner review

1. Prendre acte des corrélations `PASS_EXTERNAL_CORRELATION` sans modifier
   automatiquement la maturité des éléments ou des méthodes.
2. Maintenir TET4 dynamique en `WARNING` jusqu'au raffinement spatial demandé.
3. Vérifier pour chaque étude que le dossier, le modèle public, la figure et
   le manifeste retenus sont présents dans le paquet suivi; les fichiers de
   travail exclus ne doivent pas être réintroduits sans revue de contenu.
4. Statuer séparément sur les domaines `stable`, `experimental` et
   `engineering_internal`.
5. Traiter le cas MITC4 modal `200 x 50` comme un item d'optimisation grand
   modèle : réduire le coût de l'opérateur de shift-invert, mesurer le temps
   et la mémoire, puis relancer la corrélation avant toute promotion.

## Reproduction

Exemple TET4 dynamique :

```powershell
python .\scripts\run_code_aster_tet4_dynamic_vnv.py `
  --output .\tmp\code_aster\tet4_dynamic --mesh-size 0.85
```

Exemple TET10 dynamique :

```powershell
python .\scripts\run_code_aster_tet10_dynamic_vnv.py `
  --output .\tmp\code_aster\tet10_dynamic
```

Les autres commandes sont les scripts `run_code_aster_*_vnv.py` correspondants
dans `scripts/`. La campagne a été exécutée avec Docker actif; sans daemon,
les scripts doivent retourner une erreur d'infrastructure explicite et non un
résultat simulé.

## Owner review

- Décision : à renseigner par Owner.
- Date : à renseigner par Owner.
- Commentaires mécaniques : à renseigner par Owner.
- Promotion de maturité : interdite avant décision explicite.
