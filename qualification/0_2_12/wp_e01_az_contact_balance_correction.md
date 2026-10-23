# WP-E01-AZ — Correction du bilan de contact et agrégation fail-closed

Date : 2026-10-23

Branche : `codex/wp-e01-ax-registry-packaging-20261023`

HEAD initial : `ce2d233aab2fa3e0acd5297274b2a261ee99997a`
Tree initial : `0d5983073c7f25efa49b84da7944f2f1cc97e387`

## Décision et portée

Le diagnostic hors ligne, le correctif ciblé, les tests et la revue indépendante ont été effectués. L’audit GF4 du sous-système déformable est maintenant construit à partir des forces physiques réellement émises aux points de quadrature. L’agrégation du worker exige des preuves de contact directes et cohérentes avec les métriques publiées.

La campagne Docker n’est **pas prête à être gelée ni exécutée** : le contrôle de provenance du montage rigide reste volontairement `WARNING`, tandis que le worker exige que tous les contrôles soient `PASS`. Le finding P1 de compatibilité entre le périmètre audité et le verdict global reste ouvert. Aucun seuil ni cet avertissement n’a été supprimé. Aucun BUILD, PREFLIGHT, COLLECT, RUN, worker scientifique ou calcul FEM n’a été lancé sous AZ.

## Preuves AX/AY préservées

Le verdict historique AX reste `FAIL` pour chacun des deux replays, avec le verdict agrégé `PASS` erroné de l’ancien worker. Les deux replays et leurs reçus n’ont pas été réécrits. Les données de contact et la reconstruction hors ligne consignées dans le rapport AY restent inchangées.

La reconstruction indépendante AY du sous-système déformable donne :

| Contribution en référence | Force (N) | Moment autour de l’origine (N·m) |
|---|---|---|
| Charges extérieures `E` | `(0, 0, -1.5)` | `(-0.5, 0.5, 0)` |
| Réactions directes aux appuis `R` | `(-0.04630120354435955, -0.054915536897736185, 0.5040003347176439)` | `(0.14117500925783807, -0.14116639492448468, -0.003751586318383675)` |
| Contact physique sur l’esclave `C_s` | `(0.046301203547404, 0.054915536897467684, 0.9959996652823566)` | `(0.3588249907421624, -0.35883360507551243, 0.003751586317045979)` |
| Somme `E + R + C_s` | norme `3.0562706712284904e-12` | norme `1.337698787036916e-12` |

Les erreurs relatives reconstruites sont `2.0375137808189935e-12` pour la force et `1.337698787036916e-12` pour le moment selon les échelles documentées dans AY. Ce sont des recalculs hors ligne des données AX, et non un nouveau RUN.

Le contrôle historique contact-blind `E+R` reste inchangé : erreur relative de force `0.6657242842315055`, de moment `0.507475126989006`. Le résidu libre relatif `2.182020284783493e-12` établit l’équilibre des équations sur les DDL libres; il ne remplace pas le bilan des forces et moments du corps entier.

Le maître rigide externe et son montage n’ont pas de réaction d’appui mesurée indépendamment dans le reçu AX. Aucun bilan maître/montage n’est déduit des valeurs esclave. L’équilibre global du maître et du montage demeure `NOT_VERIFIED`.

## Cause et correction d’audit

### Cause démontrée

Le chemin final du solveur appelait auparavant le helper de contact hérité, qui attendait une liste `contacts`. L’assembleur GF4 fournit des contributions intégrées sous forme de lignes `points`, accompagnées d’un `gf_trial_contact_state`. Le schéma n’était donc pas compatible et le bilan GF4 pouvait être déclaré incomplet malgré les données de quadrature disponibles.

Le calcul historique du moment de contact utilisait en outre une position nodale comme bras de levier. Pour des forces intégrées aux points de quadrature, le moment discret correct est calculé point par point avec les positions correspondantes : `sum_q X_q × f_q` en référence, et séparément `sum_q x_q × f_q` dans le diagnostic courant.

### Changements

- Ajout de `gf_contact_aware_equilibrium`, dédié au schéma de quadrature GF4. Il vérifie l’identité de configuration, le facteur de charge, le déplacement accepté, la complétude exacte des états et des points, l’unicité des identifiants de quadrature, les identités et positions géométriques, les forces d’action-réaction et la somme des contributions.
- Le bilan audité du corps déformable additionne exactement une fois les charges extérieures, les réactions directes aux DDL prescrits et le contact physique sur l’esclave. Les moments utilisent les positions de quadrature du même référentiel.
- Le solveur réutilise le même facteur de charge pour son assemblage diagnostique final et ses charges finales. Le nouvel assemblage est utilisé pour l’audit post-solve seulement; Newton, Armijo, les décisions de contact, les tangentes et les critères d’acceptation ne sont pas modifiés.
- Le montage rigide sans réaction directement observée reste explicitement `NOT_INDEPENDENTLY_MEASURED`; le système complet reste `NOT_EVALUATED`. Le contrôle de provenance émet un avertissement bloquant, sans inventer de réaction.
- Le worker refuse un replay sans bilan imbriqué direct complet, avec statut autre que `PASS`, avec vecteurs incomplets/non finis, avec métrique imbriquée incohérente avec la métrique d’audit ou avec une somme vectorielle non fermée. Toute classification non-`PASS` interdit l’agrégat `PASS`.
- La sérialisation compacte conserve le champ `verification` nécessaire au worker.

Les équations de production, la loi de contact, les tolérances Newton–Armijo, les normalisations et les seuils historiques n’ont pas été modifiés.

## Tests et vérifications

Commande ciblée exécutée :

```text
python -m pytest -q -rs tests/unit/test_contact_aware_equilibrium_audit.py tests/unit/test_wp_e01az_nonlinear_contact_audit.py tests/unit/test_wp_e01ag_worker_state_capture.py
```

Résultat final : **47 passed in 2.07s**. Les cas couvrent le bilan sans contact existant, les contrats de contact externe/interne, l’action-réaction, le mauvais signe, les contributions manquantes, les bras de levier, l’inventaire de points, l’état d’essai, les cas PASS/FAIL/ERROR par replay, les signatures incohérentes et le refus lorsque la provenance du montage rigide n’est pas vérifiée.

Chronologie de développement conservée : un lancement intermédiaire a donné `2 failed, 45 passed` à cause de deux déstructurations de tuple de fixture devenues obsolètes après l’ajout d’un huitième champ. Ces assertions de test ont été corrigées; aucune production n’a été changée en réponse à une défaillance numérique. Le lancement final ciblé a ensuite donné 47/47.

Autres contrôles finaux :

- `python -m ruff check` sur les fichiers Python touchés : **All checks passed**.
- `python -m py_compile` sur les fichiers Python touchés : **réussi**.
- `git diff --check` : **réussi**.
- Vérification statique par AST du registre `REVIEWED_TEST_TIERS` : les SHA-256 de chaque module ciblé correspondent aux entrées enregistrées; les classifications restent `NUMERICAL_UNIT` ou `CONTRACT` selon leur portée.
- Les tests n’appellent ni solveur global, ni Docker, ni worker, ni backend natif, ni réseau.

## Revue indépendante

Un reviewer distinct a effectué une revue en lecture seule; il n’a modifié aucun fichier et n’a exécuté ni test, ni Docker, ni calcul FEM.

- **Aucun P0**.
- Les problèmes de schéma GF4 (`points` contre `contacts`) et de bras de levier sont corrigés par source et couverts par les tests ciblés.
- **P1 ouvert :** le bilan direct du sous-système déformable peut passer, mais la réaction du montage rigide reste non mesurée et donne un `WARNING`. Le classificateur du worker traite tout avertissement comme non-`PASS`; par conséquent, l’agrégat et le certificat ne peuvent pas être positifs sous le contrat courant, même si le sous-système esclave est équilibré.
- **P2 :** le worker lie les erreurs imbriquées aux métriques de haut niveau mais ne recalcule pas leur normalisation à partir des échelles sérialisées et ne vérifie pas séparément le compteur d’ownership dans le reçu. L’auditeur épinglé vérifie toutefois l’inventaire complet des points; le reviewer n’a pas démontré de faux `PASS`. La remarque selon laquelle les vecteurs accepteraient des booléens n’a pas été reproduite : `_finite_number` les rejette explicitement.

La revue indépendante ne valide pas les mesures produites par un nouveau solveur; aucune telle exécution n’a eu lieu.

## Empreintes et Git

| Fichier | SHA-256 |
|---|---|
| `src/solveur/core/contact_equilibrium.py` | `3b03c3ea17482142bf6af72190abc8b502b52fa8e9b19eddbcd4e68afb277e4e` |
| `src/solveur/core/nonlinear/solver.py` | `d553077b4d9f502d9fa25c136873b6ba3b8dc3e0d2841ca90f5e8c48d946263c` |
| `src/solveur/core/audit_checks.py` | `614f21963fe7678f2afb1ad8dd72345b01f8afaa2b5b924b9065ae0d33498714` |
| `src/solveur/core/audit.py` | `1050d0271af48991611a6f51499dc144b65dcb43693aa254befb4cc51bac9996` |
| `experiments/wp_e01ag_docker_worker.py` | `ebaf6f80cbf489ff937871a930148d82606bbf22a69ca9cc1ba02022831db9b2` |
| `tests/unit/test_wp_e01az_nonlinear_contact_audit.py` | `0e2dd8d876aa9fad6465b1e7bfaa84da14cb83080b17855ab2f7eb1354c73b5a` |
| `tests/unit/test_wp_e01ag_worker_state_capture.py` | `dbf3f6e5f4f1e7a41805921a1457f5a9143b6bf9bfec675e9f4780f97409d32a` |
| `tests/unit/test_contact_aware_equilibrium_audit.py` | `e4b6dd60fcb70dff696cb8c142d03b84ebff3817da0ed4f3904acc22e2b40894` |
| `tests/conftest.py` | `418f95753fd4d45ba0cf3ba2217d613c411d383ed6d27770706491a1320b0a74` |

Commit code/tests : `9e5d9a3a177722f87732e49ad019f39b1d332d27`

Tree après commit code/tests : `69817e0173ea9ecfd1bdfb588cd91e60e4306c34`.

Les sources d’AX/AY restent préservées. Ces nouveaux changements créent une nouvelle identité source; les 533 pins historiques ne sont donc pas présentées comme un gel exécutable actuel. Aucun nouveau manifeste, BUILD Docker ou préflight n’a été créé. Le commit documentaire du présent rapport est le commit final contenant ce fichier; son HEAD et son tree sont indiqués dans le message final afin d’éviter une auto-référence au commit.

## Conclusion et décision Owner requise

| Élément | Statut |
|---|---|
| Cause de l’échec d’audit AX | `CONTACT_OMITTED_FROM_DEFORMABLE_SUBSYSTEM_AUDIT` |
| Audit GF4 du sous-système déformable | `CORRECTED_BY_SOURCE; VERIFIED_BY_TARGETED_TESTS` |
| Agrégation worker | `FAIL_CLOSED` |
| Revue indépendante | `NO_P0; P1_OPEN; P2_NONBLOCKING` |
| Équilibre complet maître + montage | `NOT_VERIFIED` |
| Nouveau gel / BUILD | `NOT_PREPARED` |
| PREFLIGHT / COLLECT / RUN | `NOT_RUN` |
| Certificat Armijo de production | `NOT_VERIFIED` |
| Qualification scientifique générale | `NOT_ACQUIRED` |

Avant toute nouvelle campagne, l’Owner doit choisir entre :

1. fournir/autoriser une source indépendante de réaction du montage rigide, afin de satisfaire le contrat global actuel; ou
2. définir et approuver explicitement une portée limitée au sous-système déformable, en précisant que cette portée ne certifie pas l’équilibre maître/montage ni la qualification globale et comment le verdict du worker doit représenter cette limite.

Aucune option n’est appliquée automatiquement. Une nouvelle campagne nécessitera ensuite un gel complet, une revue favorable sans P1 bloquant, et la reconnaissance explicite des autorisations par le superviseur. Aucun merge ou publication n’a été effectué.
