---
doc_id: DOC-UNREGISTERED-VERIFICATION-MITC3-DYNAMIC-CAUSAL-AUDIT-2026-08-21
revision: 0.1
status: draft
applicable_version: 0.2.1a0
reviewer: ''
approver: ''
---

# Audit causal de la dynamique MITC3+

| Champ | Valeur |
| --- | --- |
| Identifiant | `DOC-AUDIT-MITC3-DYN-001` |
| Revision | `0.1` |
| Date | `2026-08-21` |
| Objet | Newmark et reponse harmonique du MITC3+ multicouche |
| Statut | audit technique, protocole V&V corrige, formulation MITC3+ inchangée |
| Decision de maturite | maintien du perimetre courant jusqu'a nouvelle campagne V&V |

## 1. Question examinee

La campagne externe MITC3+ multicouche ne descend pas sous 1 % lorsque le
maillage est raffine. Cet audit cherche a determiner si cette limite vient du
schema Newmark, du solveur harmonique, de la formulation MITC3+, du maillage,
du modele Code_Aster utilise comme reference ou des indicateurs V&V.

Le present travail ne modifie ni la formulation MITC3+, ni les solveurs
generiques, ni les criteres de promotion. Il consolide les observations
locales, des calculs legers et des references publiees afin de corriger le
protocole de campagne V&V.

Le runner de correlation a ensuite ete corrige : la grille temporelle utilise
desormais 80 pas par periode par defaut et une reference CLT/Euler independante
de la frequence QF_solver. Les erreurs Newmark forcee et libre sont publiees
separement. Les anciennes preuves restent archivees et ne sont pas reecrites.

Une execution Code_Aster de controle a ete relancee avec ce protocole corrige
sur le maillage de reference `12x3` (`72` triangles). Elle est archivee dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic/reference/`.

## 2. Conclusion executive

**Oui, une preuve MITC3+ Newmark et harmonique sous 1 % est techniquement
atteignable.** Les resultats locaux montrent deja :

- `0.0415 %` d'erreur sur la premiere frequence face a une reference
  analytique CLT/Euler-Bernoulli ;
- `0.897 %` d'ecart modal maximal MITC3+/MITC4 sur quatre modes ;
- `0.0407 %` d'ecart Newmark MITC3+/MITC4 sur un historique commun ;
- `0.0186 %` d'ecart harmonique MITC3+/MITC4 en RMS complexe ;
- `0.262 %` d'erreur temporelle Newmark interne avec 80 pas par periode ;
- moins de `1e-8` d'erreur harmonique interne face a la superposition modale.

En revanche, **raffiner uniquement le maillage ne peut pas faire passer la
campagne Code_Aster DST actuelle sous 1 %**. Entre `8x2` et `64x16`, les ecarts
Newmark et harmoniques augmentent. Les deux codes convergent vers des
operateurs discrets differents : MITC3+ dans QF_solver, DST dans Code_Aster,
avec des interpolations et des matrices de masse non identiques.

Le protocole corrige abaisse nettement les indicateurs sur le cas `12x3` :

| Controle corrige | Valeur | Ancienne valeur archivee |
| --- | ---: | ---: |
| Frequences modales, maximum | `3.957 %` | `3.957 %` |
| Newmark, RMS complet | `2.323 %` | `2.318 %` |
| Newmark, RMS force | `0.289 %` | non separe |
| Newmark, RMS libre | `2.677 %` | non separe |
| Harmonique, RMS complexe | `1.341 %` | `1.345 %` |

La correction confirme qu'un pas temporel et une grille de frequences mal
calibres ajoutaient un biais de protocole, mais elle ne suffit pas a faire
passer les trois observables sous `1 %`. La formulation n'est donc pas
declaree corrigee sur la seule base de cette relance.

Le probleme principal n'est donc pas une incapacite du MITC3+ a traiter la
dynamique, ni un pas temporel insuffisant sur le cas controle. Il s'agit d'un
**probleme de hierarchie des references et de metrique V&V**, auquel s'ajoute
une difference d'operateurs spatiaux et de masse entre MITC3+ et DST.

## 3. Campagne de raffinement existante

| Maillage quadrilateral equivalent | Triangles | Ecart modal | Ecart Newmark RMS | Ecart harmonique RMS |
| ---: | ---: | ---: | ---: | ---: |
| `8x2` | 32 | 7.5201 % | 1.7119 % | 0.9406 % |
| `12x3` | 72 | 3.9573 % | 2.3179 % | 1.3449 % |
| `16x4` | 128 | 2.5016 % | 3.4004 % | 1.9957 % |
| `24x6` | 288 | 1.7784 % | 5.5578 % | 3.2746 % |
| `32x8` | 512 | 2.0355 % | 7.2337 % | 4.2565 % |
| `48x12` | 1152 | 2.4476 % | 9.3150 % | 5.4589 % |
| `64x16` | 2048 | 2.6867 % | 10.4121 % | 6.0831 % |

Les resultats sont archives dans :

`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037/`

Une erreur de discretisation classique doit, a formulation et reference
compatibles, decroitre vers une asymptote. Ici l'ecart modal atteint un minimum
puis remonte, tandis que Newmark et l'harmonique se degradent. Cette signature
exclut une correction par simple augmentation du nombre d'elements. Elle
indique des limites discretes differentes et une accumulation de phase.

## 4. Audit des solveurs

### 4.1 Newmark

Le solveur `src/solveur/core/dynamic.py` emploie le schema implicite de Newmark
avec `beta=0.25` et `gamma=0.5`. Les tests cibles de conservation d'energie,
residu, valeurs finies et solution modale passent.

| Pas par periode | Erreur temporelle interne |
| ---: | ---: |
| 20 | 4.1620 % |
| 40 | 1.0476 % |
| 80 | 0.2623 % |

La campagne externe utilise 40 pas par periode. Ce choix convient a un seuil
engineering de 5 %, mais pas a une preuve dure de 1 %. Une nouvelle preuve
devra utiliser au moins 80 pas par periode, puis 160 et 320 pour etablir la
convergence temporelle.

**Verdict : algorithme Newmark non mis en cause ; parametrage V&V insuffisant
pour garantir 1 %.**

Une campagne dediee a ensuite ete executee avec le meme modele MITC3+ et `80`,
`160` puis `320` pas par periode. Elle est archivee dans
`qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/`.

| Pas par periode | Pas de temps (s) | Erreur RMS interne |
| ---: | ---: | ---: |
| 80 | `8.970e-4` | `0.2623 %` |
| 160 | `4.485e-4` | `0.0656 %` |
| 320 | `2.243e-4` | `0.0164 %` |

La decroissance est monotone et l'erreur fine est inferieure a 1 %. Cela
ferme la question de la discretisation temporelle pour ce cas interne. Cela ne
ferme pas la correlation externe : l'ecart restant avec Code_Aster DST vient
principalement des operateurs `K/M` et de la derive de phase entre frequences
propres differentes.

Une verification externe complementaire a ete executee sur le maillage fixe
`12x3`, avec Code_Aster relance a `80`, `160` et `320` pas par periode :

| Pas par periode | Ecart modal | Ecart Newmark RMS | Ecart harmonique |
| ---: | ---: | ---: | ---: |
| 80 | `3,9573 %` | `2,3231 %` | `1,3410 %` |
| 160 | `3,9573 %` | `2,3243 %` | `1,3410 %` |
| 320 | `3,9573 %` | `2,3247 %` | `1,3410 %` |

L'ecart Newmark varie de seulement `0,00155 %` entre les trois niveaux et
l'ecart harmonique est invariant a l'affichage numerique pres. Cette preuve
externe confirme que raffiner `dt` ne suffit pas : la cause dominante est la
difference entre les matrices `K/M` et les interpolations MITC3+/DST. Le gate
`stable` reste donc **BLOQUE** et cette campagne est classee comme diagnostic,
pas comme resultat de promotion.

Les artefacts sont archives dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_temporal_refinement_2026-08-21/reference/`.

### 4.2 Harmonique

Le solveur `src/solveur/core/harmonic.py` resout directement :

`(K + i*omega*C - omega^2*M) u = f`.

Les controles locaux donnent :

- limite statique a 0 Hz : erreur relative `7.48e-14` ;
- residu harmonique maximal : `5.40e-11` ;
- accord avec superposition modale interne : environ `6.3e-9`.

**Verdict : solveur harmonique non mis en cause.** L'ecart externe vient de la
difference des operateurs `K/M` et de la position des excitations par rapport
aux poles modaux.

## 5. Audit de la formulation MITC3+

### 5.1 Conformite observee

Le module `src/solveur/elements/shell/mitc3.py` contient les caracteristiques
majeures de la formulation MITC3+ publiee :

- rotations enrichies par une bulle cubique ;
- distance de tying `d=1e-4` ;
- cisaillement transverse suppose MITC ;
- integration triangulaire a sept points ;
- condensation statique des deux rotations internes ;
- separation membrane, flexion, cisaillement et drilling.

Les tests unitaires verifient la symetrie, les six modes rigides, les mouvements
rigides, la condensation stationnaire, la masse totale, la positivite
semi-definie et l'invariance en energie de la rigidite sous rotation.

La publication modale MITC3+ etudie explicitement une masse coherente et montre
de bonnes convergences sur plaque libre et hyperboloide. La dynamique modale
n'est donc pas une extrapolation interdite par la formulation.

### 5.2 Point restant sur la masse condensee

QF_solver construit une masse coherente avec interpolation lineaire des
translations, interpolation enrichie des rotations, inerties surfacique et
rotatoire, puis la projette avec la transformation de condensation deduite de
la rigidite.

Les controles donnent :

- masse translationnelle totale : `3.1 kg`, exactement la masse analytique ;
- symetrie relative : environ `1.2e-21` ;
- positivite semi-definie verifiee ;
- aucune inertie artificielle sur la rotation de drilling nodale.

Ces invariants sont sains. Une verification elementaire independante a ensuite
recalcule la masse avec une quadrature Duffy tensorielle de Gauss-Legendre
d'ordre 12 :

| Controle | Valeur |
| --- | ---: |
| Difference masse developpee | `1,1783e-7` |
| Difference masse condensee | `1,1803e-5` |
| Erreur bilan translationnel | `1,8623e-15` |
| Valeur minimale propre condensee | `0` |
| Bloc drilling nodal | `0` |

La masse condensee est donc coherente avec l'integration independante dans la
limite du schema de quadrature utilise, et la difference mesuree est tres
inferieure aux ecarts externes de `1,3 %` a `4,0 %`. Cette preuve exclut la
quadrature de masse comme cause dominante, mais ne compare pas encore la
formulation MITC3+ a un element externe de meme ordre.

### 5.3 Audit algébrique de la condensation K/M

Une seconde campagne elementaire a compare directement les matrices
developpees `20x20` et les matrices publiques `18x18` :

| Controle | Valeur | Limite |
| --- | ---: | ---: |
| Projection de `K` par `T.T @ K @ T` | `1,1058e-18` | `1e-12` |
| Additivite des composantes de `K` | `0` | `1e-12` |
| Projection de `M` par `T.T @ M @ T` | `0` | `1e-12` |
| Residu de stationnarite interne | `1,1303e-19` | `1e-10` |

Le verdict est `PASS_ALGEBRAIC_CONDENSATION`. Cette preuve ferme la coherence
de la chaine logicielle `K/M -> condensation -> matrices publiques`, mais elle
ne vaut pas une implementation independante de la formulation MITC3 et ne
ferme donc pas la correlation externe DST. Le rapport complet est archive dans
`qualification/vnv/mitc3_matrix_condensation_audit_2026-08-21/`.

### 5.4 Audit indépendant de quadrature de rigidité

La même vérification a été appliquée à la rigidité `K` avec une intégration
Duffy Gauss-Legendre d'ordre 12, indépendante de la règle Dunavant à sept
points utilisée par l'élément :

| Contrôle | Valeur | Limite |
| --- | ---: | ---: |
| `K` développé total | `1,9817e-15` | `2e-7` |
| Maximum par composante | `4,2790e-15` | `2e-7` |
| `K` condensé | `1,9831e-15` | `2e-7` |
| Symétrie développée et indépendante | `0` | `1e-14` |

Le verdict `PASS_INDEPENDENT_QUADRATURE` écarte donc une erreur dominante de
quadrature de rigidité sur le triangle testé. Comme pour la masse, les
opérateurs de déformation MITC3+ et les lois constitutives sont réutilisés par
les deux intégrations : cette preuve ne constitue pas une formulation shell
indépendante et ne ferme pas la corrélation DST. Le dossier est archivé dans
`qualification/vnv/mitc3_stiffness_quadrature_audit_2026-08-21/`.

Un audit complémentaire `MITC3-LAM-DYN-C12` compare la chaîne constitutive à
une quadrature Gauss-Legendre indépendante dans l'épaisseur. Les matrices
`A/B/D`, la masse surfacique, l'inertie de rotation et l'orientation projetée
passent les contrôles à `1e-12`, avec `1e-9` absolu pour le couplage `B` nul
par annulation symétrique. Le verdict est `PASS_INDEPENDENT_ABD`. Cette
preuve écarte une incohérence démontrée dans la construction du stratifié,
mais ne crée pas une formulation shell externe MITC3+ de comparaison.
Le dossier est dans
`qualification/vnv/mitc3_laminate_abd_audit_2026-08-21/`.

**Verdict formulation : aucune anomalie de masse ou de condensation demontree. La formulation
MITC3+ reste ouverte pour une comparaison externe de meme ordre avant
promotion stable.** La preuve est archivee dans
`qualification/vnv/mitc3_mass_quadrature_audit_2026-08-21/`.

## 6. Limite de l'oracle Code_Aster DST

La documentation officielle Code_Aster indique que les familles DKT/DST
emploient en dynamique une matrice de masse amelioree fondee sur une
interpolation cubique du deplacement transverse. QF_solver MITC3+ utilise une
autre interpolation et une autre condensation interne.

Les modeles partagent le maillage geometrique, le materiau, l'empilement, les
conditions limites, les charges et les instants. Ils ne partagent pas
exactement l'operateur de flexion, l'operateur de cisaillement, la construction
de masse ni les degres internes. Un meme maillage ne produit donc pas la meme
approximation numerique.

Code_Aster DST est une triangulation externe utile, mais ne doit pas etre
l'unique reference primaire d'un critere de 1 % au meme maillage.

Pour distinguer la dependance au modele de coque, une campagne Code_Aster `DKT`
a ete executee sur le meme stratifie plan mince, avec trois maillages :

| Maillage | Ecart modal | Ecart Newmark | Ecart harmonique |
| --- | ---: | ---: | ---: |
| `12x3` | `3,1228 %` | `0,2027 %` | `0,0862 %` |
| `16x4` | `1,3705 %` | `0,0813 %` | `0,0168 %` |
| `24x6` | `0,3940 %` | `0,1968 %` | `0,0880 %` |

Le dernier niveau est sous `1 %` pour les trois observables, avec des residus
QF_solver inferieurs a `1,1e-8` en modal et `5,2e-11` en dynamique. Cette
preuve ouvre un sous-perimetre potentiellement stable : stratifies plans,
minces, symetriques, petits deplacements, sans dommage ni delamination. Elle
ne permet pas de promouvoir le scope DST general : DKT est une reference de
limite mince differente et les niveaux intermediaires sont conserves dans le
rapport.

Les artefacts DKT sont archives dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/`.

Une reserve documentaire demeure : la campagne execute Code_Aster 18.1 alors
que les manuels analyses sont anterieurs. La prochaine campagne doit tracer le
manuel ou le code source correspondant exactement a la version executee et
confirmer le chemin `MASS_MECA`.

## 7. Reference analytique independante

Pour le cantilever `[0/90/90/0]`, la theorie classique des stratifies donne,
en N.m :

```text
D = [[9625.1591,  211.1460,    0.0000],
     [ 211.1460, 2021.3881,    0.0000],
     [   0.0000,    0.0000,  416.6667]]
```

La rigidite equivalente est :

`D_eff = D11 - D12^2 / D22 = 9603.1036 N.m`.

Avec une masse surfacique de `15.5 kg/m2`, la premiere frequence analytique
vaut `13.928708 Hz`.

| Resultat fin `64x16` | Frequence | Ecart analytique |
| --- | ---: | ---: |
| QF_solver MITC3+ | 13.922925 Hz | 0.0415 % |
| Code_Aster DST | 13.576242 Hz | 2.5305 % |

La compliance statique analytique sous 1 N vaut `1.735550e-4 m`. Le deplacement
moyen de bord QF_solver vaut `1.736250e-4 m`, soit environ `0.0404 %` d'ecart.

Cette preuve ne qualifie pas toutes les coques multicouches. Elle montre que,
pour la flexion de cette geometrie, QF_solver est plus proche de la theorie que
le DST utilise comme comparaison.

## 8. Origine de l'ecart Newmark

Au maillage `64x16` :

- RMS brut complet : `10.4121 %` ;
- RMS pendant les 20 echantillons forces : `1.4098 %` ;
- RMS pendant la vibration libre : `11.9954 %` ;
- meilleur recalage retard/amplitude : `4.7883 %` ;
- ecart de premiere frequence QF/DST : `2.5536 %` ;
- derive de phase estimee : `0.313 rad`, soit `17.9 deg`.

La metrique RMS brute compare les signaux echantillon par echantillon. Une
petite difference de frequence propre accumule une difference de phase. La
norme augmente alors meme si chaque integrateur calcule correctement son propre
modele semi-discret.

La prochaine preuve doit separer amplitude, periode, phase, phase forcee,
vibration libre, energie, residu et erreur propre au pas de temps.

## 9. Origine de l'ecart harmonique

Les frequences externes sont `0.1`, `0.25`, `0.5` et `0.75` fois la premiere
frequence QF_solver. La grille depend donc d'un solveur. A `0.75 f1`, une petite
difference de pole modal genere deja une difference d'amplitude, surtout sans
amortissement.

Sur une grille absolue commune, QF_solver MITC3+/MITC4 ne differe que de
`0.0186 %` en RMS complexe. L'ecart QF/DST de `6.08 %` est donc compatible avec
la difference de `K/M`, et non avec une mauvaise resolution harmonique.

## 10. Classement causal

| Hypothese | Verdict | Confiance | Justification |
| --- | --- | --- | --- |
| Maillage seul insuffisant | Rejete comme cause unique | Haute | L'ecart augmente de `8x2` a `64x16`. |
| Defaut Newmark | Rejete | Haute | Convergence temporelle et energie internes. |
| Defaut harmonique | Rejete | Haute | Limite statique, residu et superposition passent. |
| Solveur lineaire non converge | Rejete | Haute | Residus faibles et solutions finies. |
| Drilling | Rejete | Haute | Variation de `1e-8` a `1` sans effet significatif. |
| Facteur de cisaillement | Secondaire negligeable | Haute | `0.5` a `1.0` change `f1` d'environ `0.06 %`. |
| Mauvaise masse totale | Rejete | Haute | Masse assemblee exactement `3.1 kg`. |
| Difference MITC3+/DST | Cause principale | Haute | Frequences limites et masses distinctes. |
| RMS Newmark sensible a la phase | Cause principale | Haute | Derive mesuree de `17.9 deg`. |
| Grille harmonique liee a QF | Cause aggravante | Haute | Frequences proches du pole QF. |
| Masse MITC3+ condensee erronee | Non demontre | Moyenne | Invariants sains, matrice de reference absente. |

## 11. Verification croisee MITC3+ / MITC4

Sur le meme modele et le maillage `24x6` :

| Mode | MITC3+ | MITC4 | Ecart |
| ---: | ---: | ---: | ---: |
| 1 | 13.924530 Hz | 13.925839 Hz | 0.0094 % |
| 2 | 52.636555 Hz | 52.340038 Hz | 0.5665 % |
| 3 | 87.156430 Hz | 87.238062 Hz | 0.0936 % |
| 4 | 175.796166 Hz | 174.233729 Hz | 0.8967 % |

Avec une grille physique absolue et 80 pas par periode :

- Newmark, RMS normalise : `0.0407 %` ;
- harmonique, RMS complexe : `0.0186 %`.

Cette comparaison confirme la capacite dynamique du MITC3+. Elle reste une
preuve secondaire car les deux elements partagent l'infrastructure QF_solver.

## 12. Roadmap apres correction du protocole

### A. Figer le diagnostic actuel

- Archiver `8x2` a `64x16` comme preuve que le raffinement seul ne ferme pas
  l'ecart.
- Classer Code_Aster DST comme reference externe secondaire.
- Conserver la maturite actuelle ; aucune promotion automatique.

### B. Verifier les operateurs elementaires

- Exporter `K` et `M` MITC3+ completes `20x20` et condensees `18x18`.
- Recalculer independamment chaque bloc d'integration.
- Ajouter invariance de masse sous rotation, inertie rotatoire, positivite et
  modes rigides.
- Comparer la condensation de masse a une implementation independante.

Critere : ecart coefficient ou energie inferieur a `1e-10` sur les cas
analytiques.

### C. Reproduire les benchmarks modaux MITC3+ publies

- Reproduire la plaque carree libre et l'hyperboloide libre de la publication
  de 2015.
- Utiliser `N=5,10,15,20`, `d=1e-4`, plusieurs rapports d'epaisseur, maillages
  reguliers et distordus.
- Comparer frequences, modes rigides, MAC et ordres de convergence.

Critere : erreurs primaires inferieures a `1 %`.

### D. Etablir les references analytiques CLT

- Couvrir au moins trois empilements, trois geometries ou elancements, et deux
  familles de chargement.
- Comparer compliance, frequences, resultantes `N/M/Q` et energies.
- Utiliser Richardson lorsque le regime asymptotique est observable.

Critere : dernier maillage et extrapolation sous `1 %`.

### E. Refaire Newmark

- Utiliser `80`, `160` et `320` pas par periode.
- Comparer chaque solveur a sa solution modale propre.
- Fixer un temps physique et une charge absolus pour la correlation externe.
- Publier amplitude, periode, phase, RMS forcee, RMS libre, energie et residu.

Critere : chaque erreur engineering primaire sous `1 %`.

### F. Refaire l'harmonique

- Verifier la limite statique a `0 Hz`.
- Employer une grille absolue commune en Hz.
- Comparer receptance complexe, amplitude et phase.
- Ajouter un cas amorti autour de la resonance.
- Utiliser la superposition modale analytique/CLT comme reference primaire.

Critere : moins de `1 %` hors voisinage de pole explicitement defini.

### G. Repositionner Code_Aster

- Confirmer la formulation et `MASS_MECA` de Code_Aster 18.1.
- Comparer les limites extrapolees `h -> 0`, pas seulement le meme maillage.
- Ajouter une reference coque d'ordre superieur ou solide 3D convergee.
- N'exiger l'identite sous 1 % avec DST que si l'equivalence des operateurs est
  etablie.

### H. Gate de promotion stable

La promotion exige simultanement :

- toutes les erreurs engineering primaires inferieures ou egales a `1 %` ;
- au moins trois niveaux spatiaux et trois niveaux temporels ;
- plusieurs geometries, empilements et chargements ;
- references analytiques ou publiees primaires ;
- correlation externe reproductible comme preuve complementaire ;
- matrices, residus, energies, figures et manifestes archives ;
- Owner Review apres revue des resultats.

## 13. Decision recommandee

1. Ne pas modifier MITC3+ sur la seule base de l'ecart DST.
2. Ne pas lancer un maillage plus gros avec le protocole actuel.
3. Conserver le scope actuel sans promotion stable.
4. Refaire la hierarchie V&V : publication MITC3+, analytique CLT, convergence
   propre, puis Code_Aster en preuve secondaire.
5. Employer au moins 80 pas par periode pour la future preuve Newmark sous 1 %.

## 14. References

1. Jeon, Lee et Bathe, *The MITC3+ shell element and its performance*, 2014,
   <https://doi.org/10.1016/j.compstruc.2014.02.005>.
2. Jeon, Lee et Bathe, *The modal behavior of the MITC3+ triangular shell
   element*, 2015, <https://doi.org/10.1016/j.compstruc.2015.02.033>.
3. MIT, copies auteurs des publications MITC,
   <https://web.mit.edu/kjb/www/Principal_Publications/>.
4. Code_Aster, formulation DKT/DST,
   <https://www.code-aster.org/V2/doc/v12/en/man_r/r3/r3.07.03.pdf>.
5. Code_Aster, commande `DYNA_VIBRA`,
   <https://www.code-aster.org/V2/doc/v14/en/man_u/u4/u4.53.03.pdf>.
6. Newmark, *A Method of Computation for Structural Dynamics*, 1959,
   <https://doi.org/10.1061/JMCEA3.0000098>.

## 15. Verification executee

```powershell
python -m pytest `
  tests\verification\test_mitc3_laminate_dynamic_vnv.py `
  tests\unit\test_analysis_features.py::test_transient_dynamic_newmark_conserves_energy_without_damping `
  tests\unit\test_analysis_features.py::test_harmonic_response_zero_frequency_matches_static_solution `
  -q
```

Resultat : `9 passed` pour le lot cible, puis campagne Code_Aster
`PASS_EXTERNAL_CORRELATION` avec les valeurs corrigees reportees ci-dessus.

Des diagnostics legers ont ensuite mesure le drilling, le facteur de
cisaillement, la masse, la reference CLT et la correlation MITC3+/MITC4. Le
code de formulation MITC3+ n'a pas ete modifie ; seul le runner de V&V et ses
tests de protocole ont ete ajustes.
