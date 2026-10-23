# WP-E01-AY — Audit d’équilibre et agrégation fail-closed

Date : 2026-10-23  
Périmètre : analyse hors ligne des preuves WP-E01-AX, correction ciblée du worker/superviseur et tests unitaires de contrat.  
Exécution FEM/Docker pendant AY : **aucune**.

## Identité et preuves préservées

- HEAD de référence AX : `c54f12c3ebd1275ca8cc644fc54c5086a5b7acb6`
- Tree de référence AX : `5cb5912e4afb25bd9f413d249b674744b14a8729`
- Reçu RUN examiné : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ax-evidence\WP-E01-AX-COLLECT-20261023-CBF0182360954A3E8C631B2B4E2319C8\RUN\run_receipt.json`
- Rapport AX : `qualification/0_2_12/wp_e01_ax_docker_native_fem_vnv_report.md`
- Le verdict historique AX, les deux replays, journaux et reçus n’ont pas été modifiés.

Le RUN AX a convergé au facteur de charge 1 dans deux replays identiques. Son résidu libre relatif archivé est `2.182020284783493e-12`. Le contrôle historique de bilan global donne `FAIL` pour les deux replays : erreur relative de force `0.6657242842315055` et erreur relative de moment `0.507475126989006`. Chaque verdict de replay est `FAIL`, alors que l’ancien agrégat du worker déclarait incorrectement `PASS`. Ces résultats restent les résultats historiques ; le présent audit ne les requalifie pas.

## Reconstitution mécanique à partir du reçu AX

Le modèle archivé est un TET4 GF4 avec 12 DDL, dont 6 prescrits et 6 libres, trois points de quadrature de contact, et un maître rigide externe au sous-système déformable. Le reçu identifie la convention `residual = internal_force - external_force`, les réactions comme résidus sur les DDL prescrits et les moments en `REFERENCE_COORDINATES`.

Les forces extérieures archivées sont trois charges nodales `UZ=-0.5 N`, appliquées aux nœuds 0, 1 et 2 :

\[
E=(0,0,-1.5)\;\mathrm N,\qquad M_E^{ref}=(-0.5,0.5,0)\;\mathrm{N\,m}.
\]

La résultante des réactions d’appui archivée est

\[
R=(-0.04630120354435955,-0.054915536897736185,0.5040003347176439)\;\mathrm N,
\]

avec

\[
M_R^{ref}=(0.14117500925783807,-0.14116639492448468,-0.003751586318383675)\;\mathrm{N\,m}.
\]

Les trois contributions de contact contiennent les positions de référence des points esclaves et les forces physiques exercées sur le sous-système esclave. Leur somme indépendante est

\[
C_s=(0.046301203547404,0.054915536897467684,0.9959996652823566)\;\mathrm N.
\]

En réutilisant les points et forces du reçu, sans appeler le code de production, le moment discret généralisé en référence vaut

\[
M_C^{ref}=\sum_q X_q\times C_q
=(0.3588249907421624,-0.35883360507551243,0.003751586317045979)\;\mathrm{N\,m}.
\]

Le bilan complet du **sous-système déformable**, contact compris, est donc :

| Contribution | Force résultante (N) | Moment de référence (N·m) |
|---|---:|---:|
| Charge extérieure `E` | `(0, 0, -1.5)` | `(-0.5, 0.5, 0)` |
| Réactions `R` | `(-0.04630120354436, -0.05491553689774, 0.50400033471764)` | `(0.14117500925784, -0.14116639492448, -0.00375158631838)` |
| Contact sur l’esclave `C_s` | `(0.04630120354740, 0.05491553689747, 0.99599966528236)` | `(0.35882499074216, -0.35883360507551, 0.00375158631705)` |
| **Somme** | **`(3.0445e-12, -2.6850e-13, 5.55e-16)`** | **`(5.00e-16, 2.89e-15, -1.3377e-12)`** |

Les normes des écarts sont `3.0562706712284904e-12 N` et `1.337698787036916e-12 N·m`. Avec l’échelle de référence effectivement utilisée pour cette reconstruction (`1.5 N` pour les forces et plancher `1 N·m` pour les moments), les écarts relatifs valent respectivement `2.0375137808189935e-12` et `1.337698787036916e-12`. Ce sont des recalculs hors ligne à partir des données numériques du reçu, pas une nouvelle exécution.

L’ancien contrôle contact-blind additionne uniquement `E+R`. Il obtient une norme de force `0.9985864263473851 N`, relative `0.6657242842315055`, et une norme de moment d’environ `0.507475126989006 N·m`, relative identique. Il omet donc une contribution qui est extérieure au sous-système esclave lorsque le maître rigide n’est pas inclus dans le domaine audité.

Le résidu libre (`2.1820e-12` relatif) mesure l’équilibre des équations sur les DDL libres. Il n’est pas le bilan vectoriel de corps entier : les DDL prescrits portent les réactions et le contact agit comme une charge sur le sous-système déformable. Les deux diagnostics sont compatibles, mais répondent à des questions différentes.

### Référentiel et limites

Le bilan ci-dessus est celui des efforts généralisés discrets dans la configuration de référence, cohérent avec le contrat de petites déformations et la distribution nodale des forces de contact. Le moment de contact est obtenu par `Σ X_q × C_q`, équivalent au moment des forces nodales distribuées par les fonctions de forme au point de quadrature. Il ne faut pas mélanger ce moment avec un bilan spatial en coordonnées courantes.

À titre de contrôle distinct, la reconstruction courante à partir des coordonnées déplacées donne un moment total `([1.0270569e-4, -9.9562199e-5, 8.3158010e-7]) N·m`, norme `1.430446831528931e-4 N·m`. Ce nombre appartient à un autre référentiel et n’est pas comparé au seuil historique en référence.

Le maître reçoit la force opposée. Le reçu montre un couple géométrique de paire d’environ `(9.3543e-6, -7.8869e-6, 0) N·m`, mais ne fournit pas une mesure indépendante complète de la réaction de son montage. L’équilibre du système combiné esclave + maître + montage n’est donc **pas certifié**. L’équilibre démontré ici est borné au sous-système déformable, avec les forces de contact comme contribution extérieure.

## Diagnostic de l’audit historique

La cause la mieux étayée est **l’omission des forces de contact esclaves dans le bilan global du sous-système déformable**. Les données de contact nécessaires sont présentes dans le reçu, et leur ajout ferme les bilans de force et de moment de référence à l’échelle des résidus numériques observés.

| Hypothèse | Conclusion |
|---|---|
| Contribution physique omise | **Oui : contact sur l’esclave absent de `E+R`** |
| Double comptage des forces de contact | Non observé dans les contributions archivées utilisées ici |
| Convention de signe incohérente | Non : la convention résidu/réaction du reçu et le signe du contact ferment le bilan lorsqu’ils sont appliqués au même sous-système |
| Périmètre audité différent du système résolu | **Oui : audit `E+R` contact-blind contre équilibre du sous-système esclave avec contact** |
| Défaut mécanique de production démontré | Non |
| Équilibre complet incluant maître et montage établi | Non, données de réaction du montage insuffisantes |

La classification est donc : **cause de l’échec historique d’audit identifiée pour le sous-système déformable, bilan du système total incomplet**. Aucun seuil historique n’a été changé et aucun verdict historique n’a été réécrit. Le code de production d’audit n’a pas été corrigé : une modification de ce contrat scientifique nécessiterait une campagne dédiée et une nouvelle identité de test.

## Correction du P1 d’agrégation

Le worker `experiments/wp_e01ag_docker_worker.py` classifie maintenant chaque replay avant agrégation. L’agrégat est `PASS` uniquement si exactement deux replays sont individuellement `PASS`, contiennent les preuves d’acceptation/audit requises, satisfont les métriques et seuils déclarés, et ont la même signature scientifique. Toute classification `FAIL` produit un agrégat `FAIL`; tout `ERROR`, preuve manquante ou malformée produit `ERROR`. Les codes de sortie sont distincts : `0` PASS, `1` FAIL, `2` ERROR.

La validation d’un contrôle d’équilibre exige maintenant une valeur numérique finie, égale à la métrique sérialisée correspondante, un libellé de limite analysable et cohérent, et un statut compatible avec cette limite. Les limites analysées sont les limites déjà émises par la source d’audit gelée ; aucune valeur de seuil n’a été modifiée.

Le superviseur `experiments/wp_e01ag_docker_host.ps1` vérifie le nombre et les classes de replays, les deux signatures hexadécimales, compare réellement les signatures, et s’assure que le booléen de déterminisme et le résultat agrégé reflètent ces preuves. Il transmet PASS/FAIL/ERROR par des codes de sortie cohérents.

Les tests `tests/unit/test_wp_e01ag_worker_state_capture.py` couvrent : deux PASS, PASS+FAIL, deux FAIL, deux ERROR, PASS+ERROR, preuves absentes, désaccord valeur/métrique, limite invalide et valeur au-dessus du seuil déclarée à tort PASS. Ils exercent les décisions de reçu avec des objets synthétiques sans solveur ni processus FEM.

### Limite résiduelle

Le superviseur hôte valide les signatures et les classifications déclarées par le worker hash-pinné, mais ne recalcule pas lui-même chaque classification à partir des objets détaillés de chaque replay. La revue indépendante classe ce point P2 : pas de faux PASS démontré, mais une vérification hôte indépendante supplémentaire serait utile avant une future qualification. Cette limite n’empêche pas de corriger le P1 historique (l’agrégat du worker ne peut plus ignorer un replay FAIL), mais elle doit rester visible dans toute préparation d’exécution.

## Revue et vérifications

Revue indépendante en lecture seule effectuée par un reviewer distinct de l’implémenteur. Conclusion : aucun finding P0/P1 restant sur le correctif ou la séparation référence/courant ; P2 résiduel décrit ci-dessus. Le reviewer n’a ni modifié les sources, ni lancé Docker/FEM, ni exécuté les tests.

Vérifications exécutées dans AY :

- `python -m pytest -q -rs tests/unit/test_wp_e01ag_worker_state_capture.py` : **19 passed**.
- `python -m ruff check experiments/wp_e01ag_docker_worker.py tests/unit/test_wp_e01ag_worker_state_capture.py tests/conftest.py` : **All checks passed**.
- `python -m py_compile experiments/wp_e01ag_docker_worker.py tests/unit/test_wp_e01ag_worker_state_capture.py tests/conftest.py` : réussi.
- Analyse AST PowerShell de `experiments/wp_e01ag_docker_host.ps1` : **PowerShell AST OK** (analyse uniquement, script non exécuté).
- `git diff --check` : réussi.
- Aucun pytest scientifique, Docker, worker, solveur Newton ou calcul FEM n’a été lancé.

Un premier appel de pytest avant la mise à jour du pin de test a été bloqué par le registre de sécurité et a rapporté `17 skipped` (hash inconnu, aucun corps exécuté). Le pin a ensuite été mis à jour avec le SHA-256 exact du test ; l’exécution ciblée finale a réussi avec 19 tests.

## Identités modifiées et suites

Fichiers de code/test modifiés :

- `experiments/wp_e01ag_docker_worker.py`
- `experiments/wp_e01ag_docker_host.ps1`
- `tests/unit/test_wp_e01ag_worker_state_capture.py`
- `tests/conftest.py` (mise à jour du hash, classification toujours `CONTRACT`)
- `qualification/0_2_12/wp_e01_ay_balance_aggregation_audit.md` (présent rapport)

Hashes SHA-256 des fichiers exécutables modifiés :

| Fichier | SHA-256 |
|---|---|
| `experiments/wp_e01ag_docker_worker.py` | `3b53c9757db89ebc2de1eb6b704de757a5d71d7fb48e7b9074596aa71469b835` |
| `experiments/wp_e01ag_docker_host.ps1` | `1445df14f92bc75435e46554732d70fa7b4f25c166a7037366616d457b74aca3` |
| `tests/unit/test_wp_e01ag_worker_state_capture.py` | `b502b138b8a7d4bcf2465efe06113ef1c0111aa56f27b2dd68962414c4a7b2c9` |
| `tests/conftest.py` | `21ad2a17a00dd5f15cf8dfc1c84b04b3122d6b69439929895a3fef460f21c403` |

Commit de code/test : `0d07842c9391d69ca9e61b048d143bbd07d1bb31`  
Tree à ce commit : `cc07e934a9eca47dfd920eb39011f9772f9cc4e7`

Les sources scientifiques de production, seuils Newton/Armijo et sources du scénario n’ont pas été modifiés. Le commit de rapport, HEAD/tree final et son propre SHA-256 sont consignés dans le résumé de clôture (un fichier ne peut pas contenir de façon stable son propre hash ni le hash du commit qui le contient).

La modification invalide l’ancienne identité exécutable AX pour toute réutilisation comme gel courant. Avant toute future collecte/RUN, il faudra recalculer la carte source complète, actualiser les pins/manifeste, reconstruire l’image si son contexte inclut ces fichiers et obtenir les autorisations correspondantes. Ce rapport ne constitue ni GO-COLLECT ni GO-RUN.

## Statuts AY

| Domaine | Statut |
|---|---|
| Verdict WP-E01-AX | `FAIL_PRESERVED` |
| Cause du bilan de force/moment AX | `CONTACT_OMITTED_FROM_DEFORMABLE_SUBSYSTEM_AUDIT` |
| Bilan de référence du sous-système déformable | `RECONSTRUCTED_BOUNDED` |
| Équilibre maître + montage complet | `INCOMPLETE_EVIDENCE` |
| Agrégation worker fail-closed | `FIXED_BY_SOURCE` |
| Tests unitaires ciblés | `19_PASS` |
| Docker / nouveau RUN FEM | `NOT_RUN` |
| Certificat de production Armijo | `NOT_VERIFIED` |
| Qualification scientifique générale | `NOT_ACQUIRED` |
