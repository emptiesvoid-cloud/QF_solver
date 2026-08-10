---
doc_id: DOC-VNV-MITC4-01
revision: 0.1
status: verification interne en cours
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Perimetre de validation MITC4

## Separation des decisions

La validation est divisee en quatre scopes independants:

| Scope | Contenu | Statut courant |
| --- | --- | --- |
| `mitc4-linear-static` | rigidite, charges, resultantes, contraintes et locking | valide engineering interne avec recommandations |
| `mitc4-modal` | masse coherente, condensation et modes propres | candidate, revue mecanique en attente |
| `mitc4-transient-dynamic` | Newmark lineaire apres validation modale | valide avec recommandations, engineering interne |
| `mitc4-harmonic-response` | reponse frequentielle apres validation modale | valide engineering interne avec recommandations |
| `mitc4-harmonic-condensation` | identite de Schur et implementation Rayleigh | candidate technique |

Une reussite Newmark ou harmonique ne peut pas masquer un echec modal. Les
grandes rotations, le flambement, les composites et les offsets sont hors
perimetre.

## Domaine geometrique et materiau

Le domaine accepte utilise un materiau isotrope homogene, une epaisseur
constante par element et des facettes a quatre noeuds en petits deplacements.
Les limites de maillage sont: aspect ratio 10, warpage 5 degres, angles entre
30 et 150 degres et planarity ratio $10^{-3}$. Un profil `qualification`
transforme tout depassement en refus.

## Condensation du drilling dynamique

Dans un repere directeur nodal, les coordonnees libres sont partitionnees en
coordonnees physiques $p$ et rotations de drilling sans masse $d$:

$$
\begin{bmatrix}K_{pp}&K_{pd}\\K_{dp}&K_{dd}\end{bmatrix}
\begin{bmatrix}q_p\\q_d\end{bmatrix}=
\begin{bmatrix}f_p\\f_d\end{bmatrix}.
$$

L'equilibre algebrique donne

$$
q_d=K_{dd}^{-1}(f_d-K_{dp}q_p),
$$

et le systeme dynamique conserve uniquement

$$
K_c=K_{pp}-K_{pd}K_{dd}^{-1}K_{dp},\qquad M_c=M_{pp}.
$$

La direction n'est condensee que si sa ligne de masse assemblee est nulle sous
la tolerance tracee. Cette verification preserve l'objectivite des plaques
inclinees et ne retire pas une rotation devenue inertielle dans un assemblage
facettise courbe. Les blocages `RX/RY/RZ` doivent etre tous libres ou tous
bloques a un noeud dynamique. Tant qu'un drilling est condense, le premier
scope Newmark autorise seulement l'amortissement proportionnel a la masse
(`rayleigh_beta=0`).

## Shear locking

La campagne `VNV-MITC4-SHEAR-LOCKING-001` utilise les maillages `4x1`, `8x2`,
`16x4`, `24x6`, `32x8`, les rapports $t/L$ de $10^{-1}$ a $10^{-4}$ et des
distorsions de 0 a 30 %. Les grandeurs acceptees sont la fleche de Timoshenko,
les energies flexion/cisaillement/drilling, l'erreur arriere, le conditionnement
diagonal et l'increment du dernier maillage.

Le Q4 a cisaillement complet est uniquement un temoin negatif. Il doit
verrouiller dans la limite mince; il ne constitue jamais une formulation
alternative utilisable.

La sensibilite `VNV-MITC4-DRILLING-001` balaie `drilling_scale` de `1e-6` a
`1e-2` sur Cook `16x16`. Entre `1e-5` et `1e-3`, la variation maximale de
deplacement vaut `9,50e-6`, tres inferieure a la limite de plateau de 1 %.
La valeur par defaut `1e-4` est donc conservee dans ce domaine borne.

## Verification statique

Les patchs couvrent membrane, flexion, cisaillement, champs mixtes, distorsion
et rotation globale. Les benchmarks structuraux sont Cook, Scordelis-Lo et le
cylindre pince. Les contraintes sont relues sur les faces $z=+t/2$ et
$z=-t/2$, avec la normale locale publiee dans le resultat.

Les convergences structurelles executees utilisent cinq niveaux pour
Scordelis-Lo et le cylindre pince, six niveaux jusqu'a `64x64` pour Cook. Un
point isole `200x200` a ensuite ete execute pour examiner la tendance Cook:

| Etude | Maillage fin | Erreur fine | Limite |
| --- | --- | ---: | ---: |
| Cook | `64x64` | 4,52 % | 5 % |
| Scordelis-Lo | `32x32` | 0,31 % | 2 % |
| Cylindre pince | `32x64` | 7,26 % | 10 % |

Les courbes et valeurs de chaque niveau sont regenerees par
`scripts/run_mitc4_vnv.py`; elles ne sont pas recopies manuellement dans les
dossiers de preuve.

Le point Cook `200x200` contient 40 000 elements et 242 406 DDL. Il est resolu
par CG mis a l'echelle, avec 3 259 iterations et un residu relatif de
`1,12e-8`. Sa fleche vaut `0,251503`, soit `4,968 %` par rapport a la reference
actuelle `0,2396`. La fleche augmente encore de `0,250433` a `64x64` vers
`0,251503` a `200x200`; elle ne montre donc pas une divergence numerique, mais
elle ne converge pas vers cette reference. Le statut Cook est
`WITHIN_CURRENT_THRESHOLD_REVIEW_REQUIRED`: l'audit de la reference et des
conditions aux limites est obligatoire avant de revendiquer une acceptation
complete de ce benchmark.

Le point se regenere par:

```powershell
python .\scripts\run_mitc4_cook_large.py --mesh 200
```

## Verification modale et Newmark

La masse est controlee analytiquement avant tout calcul propre. Le modal exige
des residus et erreurs d'orthogonalite sous $10^{-8}$. Newmark utilise
$\beta=1/4$, $\gamma=1/2$, quatre pas temporels de $T_1/20$ a $T_1/160$ et
une vibration libre dominee par le premier mode. La derive energetique admise
est $10^{-4}$ et le residu dynamique relatif $10^{-7}$.

La premiere preuve analytique modale est
`VNV-MITC4-MODAL-CANTILEVER-002`. Elle compare le premier mode de flexion
hors-plan d'un porte-a-faux mince ($t/L=0,01$) a Euler-Bernoulli, sur les
maillages `4x1`, `8x2`, `12x3`, `16x4` et `24x6`. Les criteres sont une erreur
de frequence finale inferieure a 5 %, un MAC de forme superieur ou egal a
0,995, et des residus/erreurs d'orthogonalite inferieurs ou egaux a $10^{-7}$.
La campagne s'execute sans service externe :

```powershell
python .\scripts\run_mitc4_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CANTILEVER-002
```

La seconde preuve `VNV-MITC4-MODAL-PLATE-003` traite une plaque carree
simplement appuyee avec les modes de Navier `(1,1)`, `(1,2)`, `(2,1)` et
`(2,2)`. Sur le maillage `16x16`, les erreurs de frequence sont respectivement
`0,318 %`, `1,434 %`, `1,434 %` et `1,513 %`. Les MAC sont superieurs a
`0,9999998`; la paire double `(1,2)/(2,1)` est comparee comme un sous-espace.

```powershell
python .\scripts\run_mitc4_modal_plate_vnv.py --output .\results\VNV-MITC4-MODAL-PLATE-003
```

La correlation `VNV-MITC4-MODAL-CODEASTER-DKQ-004` complete ces deux preuves
sur un maillage `32x32` identique et les dix premiers modes. L'ecart maximal
QF_solver/Code_Aster vaut `1,609 %`; le MAC minimal des modes ou sous-espaces
correspondants vaut `0,999998493`. Le residu QF_solver maximal vaut `7,99e-11`.

```powershell
python .\scripts\run_code_aster_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CODEASTER-DKQ-004 --mesh-size 32
```

La campagne `VNV-MITC4-MODAL-EXTENDED-005` ajoute une structure assemblee
libre-libre, une coque cylindrique distordue et un calcul `eigsh` `48x48` a
`7011` DDL actifs. Les trois etudes sont `PASS`.

```powershell
python .\scripts\run_mitc4_modal_extended_vnv.py --output .\results\VNV-MITC4-MODAL-EXTENDED-005
```

Le scope `mitc4-modal` porte une tentative de validation interne enregistree
le `2026-07-16`, decision `accepted_with_recommendations`, pour l'usage
`engineering_internal_provisional`. Le registre est
`qualification/reviews/mitc4_modal_2026-07-16.json`.
Le perimetre couvre exclusivement la masse coherente MITC4. Les formulations
de masse concentree restent hors scope et sont refusees si elles sont demandees
explicitement dans l'analyse.
Une grille independante distincte est preparee dans
`qualification/reviews/mitc4_modal_independent_review_template.md`; elle ne
peut etre signee par l'auteur du solveur.

La campagne transitoire `VNV-MITC4-NEWMARK-FREE-002` propage le premier mode
du porte-a-faux pendant trois periodes. L'erreur RMS normalisee diminue de
`6,258 %` pour `T/20` a `0,099 %` pour `T/160`; les ordres observes restent
proches de deux. L'erreur de retour finale vaut `2,93e-6` et la derive
energetique maximale reste inferieure a `6,3e-11`.

```powershell
python .\scripts\run_mitc4_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-FREE-002
```

Cette premiere campagne est completee par les cas amorti, force et large bande
ci-dessous. Elle ne constitue pas seule une validation du perimetre.

Les cas amorti et force sont maintenant couverts par
`VNV-MITC4-NEWMARK-DAMPED-FORCED-003`. A `T/160`, les erreurs RMS valent
`0,0748 %` en vibration libre amortie et `0,0576 %` sous force modale
sinusoidale. Les ordres observes sont compris entre `1,998` et `2,047`.
L'energie amortie decroit, la puissance dissipative reste non negative et les
residus absolus maximaux restent inferieurs a `3,1e-10`.

```powershell
python .\scripts\run_mitc4_newmark_extended_vnv.py --output .\results\VNV-MITC4-NEWMARK-DAMPED-FORCED-003
```

La campagne `VNV-MITC4-NEWMARK-BROADBAND-004` ajoute une impulsion demi-sinus,
un chirp lineaire et une table multi-sinus. Une propagation modale exacte par
exponentielle de matrice sert d'oracle temporel independant de Newmark. Au pas
`T/160`, les erreurs RMS `UZ/S11` valent `0,298 %/1,390 %` pour l'impulsion,
`0,077 %/0,119 %` pour le chirp et `0,037 %/0,033 %` pour la table. Les
charges lisses retrouvent l'ordre deux; l'impulsion courte passe d'un ordre
`0,85` a `1,69` parce qu'elle excite davantage les hautes frequences.

```powershell
python .\scripts\run_mitc4_newmark_broadband_vnv.py --output .\results\VNV-MITC4-NEWMARK-BROADBAND-004
```

L'extension `VNV-MITC4-NEWMARK-OPERATIONAL-006` verifie ensuite deux histoires
de charge independantes, un calage de Rayleigh sur deux frequences modales et
la reprise au pas 40. L'erreur de superposition maximale vaut `2,337e-8` sur
l'acceleration, l'erreur RMS de decroissance libre `0,300 %`, et les trois
etats finaux repris sont identiques au calcul continu a la precision stockee.

```powershell
python .\scripts\run_mitc4_newmark_operational_vnv.py --output .\results\VNV-MITC4-NEWMARK-OPERATIONAL-006
```

Cette preuve est un addendum interne post-revue. Elle ne qualifie pas encore
l'excitation de base, la PSD ni des taux d'amortissement arbitraires mode par
mode.

Le meme chirp est execute avec Code_Aster `18.1.0` DKQ sur le maillage `8x8`
identique. Les correlations temporelles sont `0,9543` en deplacement et
`0,9560` en contrainte; les ecarts de pic sont `5,20 %` et `10,51 %`.

```powershell
python .\scripts\run_code_aster_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-CODEASTER-DKQ-005
```

Le scope transitoire est accepte avec recommandations par Quentin Farinazzo le
`2026-07-16` pour l'usage engineering interne. La decision est tracee dans
`qualification/reviews/mitc4_transient_dynamic_2026-07-16.json`. Le scope
reste `candidate` pour la qualification, car l'auto-revue n'est pas
independante et la baseline code n'est pas encore un commit propre.

## Verification harmonique

`VNV-MITC4-HARMONIC-MODAL-001` excite le premier mode massiquement normalise
d'un porte-a-faux `8x2` par $\mathbf f=\mathbf M\boldsymbol\phi_1$. Le balayage
contient 81 frequences de 0 a $2f_1$ et compare la reponse complexe a

$$
\hat u_{tip}(\Omega)=
\frac{\phi_{1,tip}}
{\omega_1^2-\Omega^2+i\alpha\Omega}.
$$

| Grandeur | Valeur | Limite | Verdict |
| --- | ---: | ---: | --- |
| erreur a 0 Hz par rapport a la statique | `4,50e-11` | `1e-9` | PASS |
| erreur complexe maximale | `1,90e-7` | `1e-6` | PASS |
| frequence du pic / $f_1$ | `1,000` | `[0,95 ; 1,05]` | PASS |
| residu harmonique maximal | `1,49e-9` | `1e-7` | PASS |

Le seuil complexe de $10^{-6}$ est plus large que la limite statique car le
residu de la paire propre numerique est amplifie au voisinage exact de la
resonance. Les amplitudes a $f_1$ decroissent strictement lorsque
l'amortissement passe de 1 a 2 puis 5 %, et la phase traverse -90 degres.

```powershell
python .\scripts\run_mitc4_harmonic_vnv.py --output .\results\VNV-MITC4-HARMONIC-MODAL-001
```

Cette preuve monomodale est completee ci-dessous par une excitation large
bande et une correlation externe. Le scope harmonique est `candidate` et
accepte avec recommandations en usage engineering interne depuis la revue
mecanique du `2026-07-15`.

La condensation harmonique fait l'objet d'une preuve separee,
`VNV-MITC4-HARMONIC-CONDENSATION-002`. Le complement de Schur exact est
compare au systeme complexe complet pour quatre coefficients $\beta_R$ et
cinq frequences, avec une force `UZ` et un moment `RZ`:

| Controle | Erreur maximale | Limite |
| --- | ---: | ---: |
| complement de Schur | `9,62e-17` | `1e-11` |
| charge condensee | `1,40e-16` | `1e-11` |
| reponse condensee / systeme complet | `4,12e-11` | `1e-9` |
| equilibre complexe complet | `7,81e-11` | `1e-8` |

Cette preuve autorise `rayleigh_beta >= 0` pour la reponse harmonique MITC4.
Elle est classee `candidate technique`; elle ne change pas seule la maturite
du scope harmonique complet.

### Excitation large bande multimodale

`VNV-MITC4-HARMONIC-BROADBAND-003` applique une force `UZ` decentree sur la
plaque `8x8` afin d'activer plusieurs familles modales. Le balayage contient
`600` points de `0,1` a `16 Hz`. La solution directe est comparee a une
superposition complete des `175` modes du systeme reduit:

| Famille | Frequence modale | Pic direct | Ecart |
| ---: | ---: | ---: | ---: |
| 1 | `2,41789 Hz` | `2,40935 Hz` | `0,353 %` |
| 2 | `6,33209 Hz` | `6,33790 Hz` | `0,092 %` |
| 3 | `10,19214 Hz` | `10,26644 Hz` | `0,729 %` |
| 4 | `13,99118 Hz` | `14,03573 Hz` | `0,318 %` |

L'erreur complexe plein champ maximale est `2,411e-7`, sous `1e-6`, et le
residu relatif maximal `8,251e-11`, sous `1e-8`. Cette comparaison verifie deux
algorithmes, mais partage les memes matrices elementaires; elle est donc une
preuve numerique interne, pas une correlation physique externe.

```powershell
python .\scripts\run_mitc4_harmonic_broadband_vnv.py --output .\results\VNV-MITC4-HARMONIC-BROADBAND-003
```

### Correlation harmonique externe NAFEMS/Abaqus

`VNV-MITC4-HARMONIC-NAFEMS13H-004` reprend le Test 13H NAFEMS publie par
Abaqus/Standard, y compris le maillage `8x8`, les conditions aux limites, la
pression, l'amortissement et les `200` frequences:

| Indicateur | QF_solver | Abaqus S4R | Abaqus S4 | NAFEMS | Ecart QF/S4R |
| --- | ---: | ---: | ---: | ---: | ---: |
| pic de deplacement | `44,2719 mm` | `45,38 mm` | `44,93 mm` | `45,42 mm` | `2,442 %` |
| pic `S11` face | `30,8186 MPa` | `30,37 MPa` | `31,26 MPa` | `30,03 MPa` | `1,477 %` |
| frequence du pic | `2,42583 Hz` | `2,405 Hz` | `2,420 Hz` | `2,377 Hz` | `0,866 %` |

Le residu relatif maximal vaut `3,881e-10`. Tous les criteres programmes sont
`PASS`. La theorie de Navier donne `32,0127 MPa` pour `S11` en face au centre;
l'ecart QF_solver vaut `3,730 %`. Le champ complexe `S11/S22/S12` est exporte
par element, face et frequence.

```powershell
python .\scripts\run_mitc4_nafems13h_vnv.py --output .\results\VNV-MITC4-HARMONIC-NAFEMS13H-004
```

Le scope est accepte avec recommandations par Quentin Farinazzo le
`2026-07-15`, en mode `self_review`, pour un usage `engineering_internal`.
La decision controlee est dans
`qualification/reviews/mitc4_harmonic_response_2026-07-15.json`.

## Correlation externe statique et decision

Abaqus `S4R` est le comparateur principal et `S4` l'etude de sensibilite. Une
premiere correlation externe est maintenant controlee pour le cylindre pince.
La documentation officielle SIMULIA 2025 publie les resultats S4R suivants:

| Abaqus/Standard S4R | DDL publies | Deplacement radial | Ecart publie a Lindberg |
| --- | ---: | ---: | ---: |
| `5x5` | 216 | `1,089e-5` | `-40,3 %` |
| `10x10` | 726 | `1,591e-5` | `-12,8 %` |
| `20x20` | 2646 | `1,779e-5` | `-2,5 %` |

Le MITC4 QF_solver `32x64` donne `1,69234e-5`. L'ecart relatif au resultat
Abaqus S4R fin publie est `4,87 %`, sous la limite de correlation de support de
`10 %`. Le statut externe devient donc `PARTIAL_PASS`.

Source primaire: [SIMULIA, The pinched cylinder problem, Abaqus 2025](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEBMKRefMap/simabmk-c-pinchcyl.htm).
Les trois fichiers d'entree S4R officiels sont references dans
`qualification/vnv/references/abaqus_mitc4_static.json`.

Cette preuve reste partielle: QF_solver utilise le cylindre complet tandis que
la publication Abaqus utilise les symetries; les maillages et nombres de DDL ne
sont donc pas identiques. Abaqus n'a pas ete execute localement. La page Abaqus
nommee Cook traite un materiau hyperelastique quasi incompressible et ne peut
pas etre employee comme reference du cas de coque lineaire actuel. Aucune table
officielle S4R numerique a maillage identique n'a ete identifiee pour
Scordelis-Lo.

Une signature interne du scope statique peut s'appuyer sur cette correlation
comme preuve externe complementaire. Une correlation Abaqus a maillage
strictement identique reste necessaire pour elever le niveau de preuve au-dela
de `engineering_internal`.

La revue est signee par Quentin Farinazzo en mode `self_review`, avec la
decision `accepted_with_reservations`. Elle constitue une validation mecanique
interne non independante et ne porte aucune revendication de certification.
Le detail est publie dans [la decision MITC4](revue_mitc4_lineaire.md).
