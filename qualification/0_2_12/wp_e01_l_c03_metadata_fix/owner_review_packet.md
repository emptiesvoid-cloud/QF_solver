# WP-E01-L-C03-PROOF — dossier de décision Owner

Date : 2026-10-24. Verdict de préparation : **C03_PROOF_READY_FOR_OWNER_REVIEW**.
Agrégat technique : **PASS**. Certificat : **PROPOSED_NOT_PROMOTED**.

Les huit preuves individuelles établissent les signes stricts requis sur les
segments mathématiques gelés et relient ces signes à la classification de
production effectivement archivée à la base. La promotion du certificat
demeure une décision Owner distincte. Aucun résultat C04, C05 ou C06 n'est acquis
par cette preuve.

## Tableau des huit actions

Pour chaque point plastique, la quantité décisive est le minimum de g sur le
segment; pour chaque point élastique, c'est l'opposé du maximum de g. La colonne
m est une borne inférieure de la plus petite de ces distances strictes à zéro
sur tous les points de l'action. Les affichages de m sont arrondis vers le bas;
ceux de B vers le haut. Les rationnels et intervalles complets sont conservés
dans les fichiers `*.proof_input.json` et `*.proof_result.json`.

| Famille | H [GPa] | Direction gelée | Points P / E | m certifié [MPa] | B maximal à la base [Pa] | Preuve individuelle |
|---|---:|---|---:|---:|---:|---|
| TET4 | 0 | historique faible projetée | 12 / 0 | ≥ 526.964930 | ≤ 0.000000465746 | PASS, proposé |
| TET4 | 0 | mixte projetée | 12 / 0 | ≥ 532.345925 | ≤ 0.000000465746 | PASS, proposé |
| TET4 | 1.5 | historique faible projetée | 12 / 0 | ≥ 526.964241 | ≤ 0.000000455277 | PASS, proposé |
| TET4 | 1.5 | mixte projetée | 12 / 0 | ≥ 532.344530 | ≤ 0.000000455277 | PASS, proposé |
| HEX8 | 0 | historique faible projetée | 56 / 8 | ≥ 17.953899 | ≤ 0.000000751619 | PASS, proposé |
| HEX8 | 0 | mixte projetée | 56 / 8 | ≥ 21.372630 | ≤ 0.000000751619 | PASS, proposé |
| HEX8 | 1.5 | historique faible projetée | 56 / 8 | ≥ 17.953899 | ≤ 0.000000705168 | PASS, proposé |
| HEX8 | 1.5 | mixte projetée | 56 / 8 | ≥ 21.372630 | ≤ 0.000000705168 | PASS, proposé |

Cela représente 304 contrôles point × action et quatre états de base sondés dans
deux directions, avec 152 points de base distincts. Les histoires sont identiques
entre les deux directions d'un même état de base; les huit actions ne constituent
pas huit histoires indépendantes. Les 272 décisions plastiques utilisent la
récupération par intervalle ci-dessous; les 32 décisions élastiques disposent
directement de la marge numérique avant retour.

## Cible mathématique et preuve du segment

Le domaine est exactement s ∈ [-1/10000, +1/10000] m. Les données binary64
archivées sont prises comme les nombres rationnels exacts qu'elles représentent.
La fonction `_d` du test historique utilise `Decimal.from_float`, ce qui confirme
cette convention pour les entrées du modèle de référence. Aucune valeur arrondie
d'un rapport, aucune marge observée, aucune force et aucun plateau exploratoire
ne sert à construire les coefficients ou à choisir une tolérance.

Les gradients de référence sont fixes et la cinématique est en petites
déformations. À histoire entrante fixe :

```
epsilon(s) = epsilon_0 + s epsilon_1
sigma_trial(s) = 2 mu [epsilon(s)-epsilon_p,n]
                 + lambda tr[epsilon(s)-epsilon_p,n] I
dev(s) = d0 + s d1
R = sigma_y0 + H alpha_n
A = (3/2) d0:d0                       [Pa²]
B = 3 d0:d1                           [Pa²/m]
C = (3/2) d1:d1                       [Pa²/m²]
q(s)² = A + B s + C s²
g(s) = sqrt(q(s)²) - R                [Pa]
```

La conversion des cisaillements d'ingénieur de l'histoire vers le tenseur est
explicite. Les produits de Frobenius comptent les deux positions de chaque
composante hors diagonale. Les gradients TET4 sont calculés par algèbre rationnelle.
Les cellules HEX8 de 0.5 m et leur ordre local sont vérifiés; les abscisses
mathématiques ±1/sqrt(3) sont encadrées par des rationnels dyadiques de 192 bits.
L'ordre des points correspond aux boucles du code gelé, dernière coordonnée
variant le plus vite.

Les coefficients HEX8 sont des intervalles. L'évaluateur construit leurs
enveloppes polynomiales inférieure et supérieure, coupe le segment à zéro pour
le terme B s, et traite exactement les extrémités et le sommet éventuel
-B/(2C). C=0 est traité séparément. Il produit des intervalles du minimum et du
maximum, ainsi que l'image de g sur le segment. Ainsi un changement de signe
prouvé au minimum intérieur donne FAIL, même si les extrémités sont plastiques.
Un extremum décisif contenant zéro donne INCONCLUSIVE.

Tous les calculs polynomiaux utilisent `Fraction`. Les racines sont encadrées
avec `isqrt` et des inégalités exactes sur les carrés; ces contrôles sont aussi
enregistrés dans les preuves. Les décimales affichées sont arrondies vers
l'extérieur par division entière. La précision Decimal des anciennes sorties
n'est pas utilisée comme garantie d'arrondi dirigé.

## Lien avec la décision numérique de production à la base

Le code gelé branche sur `yield_value <= 0`. Pour les points élastiques, le champ
archivé `yield_function` est ce scalaire avant retour; sa valeur binary64 est
restaurée exactement. Pour les points plastiques, le champ homonyme est le zéro
après retour : il n'est jamais utilisé comme marge trial.

Le code plastique archive en revanche le résultat de :

```
shear = fl(E / fl(2 * fl(1 + nu)))
D = fl(fl(3 * shear) + H)
delta_gamma = fl(yield_value / D)
```

Chaque opération du dénominateur est encadrée par les binary64 inférieur et
supérieur du résultat rationnel exact. Cela couvre les modes d'arrondi IEEE
standards, avec refus conservateur des cas non finis, sous-normaux non pris en
charge ou des dénominateurs non strictement positifs. Le runtime binary64 et
les relations d'adjacence sont vérifiés, ainsi que chaque inégalité rationnelle
d'encadrement.

Si delta64 est le multiplicateur archivé, son quotient exact avant arrondi est
compris entre son prédécesseur et son successeur. Par conséquent :

```
Yprod = [prev(delta64), next(delta64)] * intervalle(D)  [Pa]
Ebase = Yprod - G0                                    [Pa]
Bbase = max(abs(Ebase.lo), abs(Ebase.hi))              [Pa]
```

G0 est l'encadrement du modèle mathématique à s=0. La preuve exige le bon signe
strict de Yprod, le bon signe de G0, la concordance du bit de branche archivé et
la domination stricte de Bbase par la distance certifiée de G0 à zéro. Ces
conditions sont satisfaites aux 304 contrôles.

**Bbase est une borne a posteriori de l'écart numérique de la tentative archivée
à la base.** Ce n'est ni un budget d'arrondi a priori, ni une garantie sur les
calculs de production à chaque déplacement du segment. La valeur exacte du
scalaire trial plastique reste UNAVAILABLE; son encadrement récupéré est certifié.
L'identité de la branche n'est pas utilisée pour fabriquer cet encadrement : le
témoin numérique est le multiplicateur réellement archivé et l'équation source.

## Provenance et reproductibilité

- Snapshot : `87e54913077c7d9fce6f259fb4a4a11f5295e6a5`.
- Tree : `c42e3c2241af1862d66cab51a38fda74a1167361`.
- Checkout historique vérifié propre; 29 pins historiques conformes, sans nouvel
  audit de compatibilité avec la branche d'intégration.
- Première archive : 28 fichiers vérifiés; quatre actions TET4 complètes dans une
  campagne globalement INCOMPLETE après le premier timeout HEX8.
- Archive complémentaire HEX8 : 35 fichiers vérifiés; quatre actions complètes.
- Capture : commits `c1d123d7ac785473cd26b6593caf78563c3b0fdc` et
  `b5bda19f7c6c4dab97c0105b4374f247bcce81a8`, trees et blobs vérifiés contre
  les données de campagne.
- Les huit histoires entrantes concordent avec leurs digests avant/après;
  quatre digests distincts. La conversion exacte des données suit le sérialiseur
  archivé : floats conservés, tableaux via `tolist`, JSON permettant le retour
  exact au binary64. Les anciennes sorties Decimal calculées ne sont pas prises
  comme des entrées exactes.

Les fichiers `archive_inventory.json` et `proof_action_summary.json` lient les
archives, sources, entrées et résultats par SHA-256. `artifact_manifest.json`
donne les empreintes de l'ensemble du nouveau dossier de preuve, hors manifeste
lui-même. Les nouveaux artefacts sont dans le worktree de préparation, non
commités; leurs identités sont donc leurs empreintes, sans nouveau commit inventé.

Reproduction du post-traitement, avec les chemins gelés par défaut documentés
dans `archive_inputs.py` :

```powershell
C:\Python313\python.exe -I -S -B integrate_proofs.py
C:\Python313\python.exe -I -S -B verify_non_fem.py
```

Ces commandes s'exécutent depuis ce dossier. La première revérifie les archives
et sources avant de régénérer les entrées et résultats. Elle échoue si une
identité indispensable diverge. Les fichiers d'une ancienne invocation restent
liés à leurs propres empreintes; un code retour non nul ne constitue jamais une
nouvelle preuve positive.

## Tests et revue indépendante

La validation finale isolée a exécuté **44 tests non FEM**, tous réussis sous
`C:\Python313\python.exe`, avec `-I -S -B`. Le fichier
`non_fem_verification_record.json` conserve la version, l'empreinte de
l'interpréteur, les empreintes des neuf sources Python testées, la commande, le
code retour, la durée et les empreintes de stdout/stderr. Les tests sont des
contrôles analytiques et de provenance synthétiques; ils restent distincts des
observations scientifiques historiques et des preuves calculées sur les archives.

La revue distincte Sol 6.1 est consignée dans `independent_review.md`. Elle
comprend des calculs critiques indépendants sur les 304 points et les vérifications
de provenance des données de production. Les défauts détectés pendant la
construction ont été corrigés avant le gel final : accumulation des intervalles,
ordre HEX8, classification des extrema et agrégation des branches mixtes.

Deux lancements pytest antérieurs par un worker ont enfreint l'instruction de
délégation; le détail et les limites de la trace sont conservés dans
`process_deviations.md`. La validation finale utilise uniquement unittest en
mode isolé avec initialisation `site` désactivée.

Coordination : deux workers configurés GPT-6 Luna et un auditeur distinct
configuré GPT-6.1 Sol, effort high demandé. Le routeur du tour confirme GPT-6.1
Sol pour le manager; aucun relevé supplémentaire du modèle/effort effectivement
exécuté dans les workers n'est exposé. La consommation de tokens n'est pas mesurée.

## Décision proposée et limites

La décision proposée est l'approbation distincte d'un certificat C03 limité à la
stabilité du signe du modèle trial exact sur les huit segments gelés, à histoire
entrante fixe, avec concordance démontrée de la décision numérique archivée à
chaque état de base. La validité de la génération de l'histoire n'est pas qualifiée.
Le calcul Decimal arrondi complet n'est pas certifié par cette preuve.

Les deux directions par état ne qualifient pas toute la matrice J2. Aucun autre
maillage, chargement, historique, segment ou runtime de production futur n'est
couvert. Aucun calcul de forces, d'assemblage, de résolution ou d'évaluation du
noyau scientifique n'entre dans les évaluateurs de preuve. Les archives
exploratoires et leurs FAIL/INCOMPLETE historiques restent inchangés.

L'Owner doit accepter ou refuser ce périmètre de certificat et sa promotion.
Cette décision ne vaut approbation de C04–C06, autorisation de RUN, merge ou release.

```text
C03_PROOF=C03_PROOF_READY_FOR_OWNER_REVIEW
C03_CERTIFICATE=PROPOSED_NOT_PROMOTED
WP_E01_STATUS=OPEN_WITH_BOUNDED_CERTIFICATES
GLOBAL_J2_TANGENT_QUALIFICATION=NOT_ACQUIRED
CRITERIA_GLOBAL=NOT_APPROVED
BA_GLOBAL_VERDICT=FAIL
RUN=NOT_RUN_BLOCKED
```
