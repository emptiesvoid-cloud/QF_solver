# WP12-A P0 — Résultats et disposition

## Résultats de cette préparation

**Aucun résultat scientifique nouveau.** Les six corps de test, assemblages, eigensolves, calculs transitoires ou harmoniques n’ont pas été exécutés. Aucun préflight officiel, manifeste d’exécution, décision Owner d’exécution ou tentative n’a été enregistré. Les six cas restent `NOT_RUN` et `PROPOSED_NOT_AUTHORIZED`.

Les tests exécutés pour le prototype sont des tests synthétiques temporaires : ils utilisent fichiers de test, faux contrôleur et JUnit simulé, sans import ou exécution des fonctions scientifiques ciblées. Leur réussite démontre seulement le comportement de routage, de refus, de verrou et d’archivage du prototype.

## Disposition par capacité P0 proposée

| Capacité | Cas proposé | Statut du nouveau contrôle | Portée de preuve en cas de succès futur |
|---|---|---|---|
| `AN-MODAL` | Modal couplé à deux DDL | `NOT_RUN` | Sentinelle analytique de petite taille ; pas de validation physique de modèles généraux. |
| `AN-MODAL-BASIS` | Sous-espace dégénéré et Rayleigh | `NOT_RUN` | Rotation/signe de petite base et projection/damping ; oracle partiellement interne. |
| `AN-DIRECT-TRANSIENT` | SDOF direct transitoire | `NOT_RUN` | Vérification fermée de la fixture SDOF, sans convergence maillée générale. |
| `AN-DIRECT-HARMONIC` | SDOF direct harmonique | `NOT_RUN` | Réponse amplitude/phase et résidu sur les fréquences du test, pas une campagne de résonance générale. |
| `AN-PREPARED` | Opérateurs préparés | `NOT_RUN` | Identité/count d’assemblage pour le contrat ciblé, pas justesse exhaustive des matrices. |
| `AN-EXCITATION` | Variation d’excitation préparée | `NOT_RUN` | Conservation des opérateurs lors du changement ciblé ; pas couverture complète de toutes excitations. |

Le résultat archivé précédent de WP12-A et les deux tentatives `PYTEST_FAILED` de l’historique Dynamics sont conservés sans réécriture. Le ledger observé avant cette mission reste SHA `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88` pour v2, avec chaîne vers le ledger générique immuable SHA `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`. Aucun ledger n’a été écrit.

## Portée des tests synthétiques

Les scénarios couvrent l’ordre six cas A→F, préflight juste-à-temps, décision liée aux six cas, budget complet qui ne tient pas, épuisement par nodeid, mutation étrangère du ledger, mutation entre préflight et réservation, changement source/controller/critère/DDL, assertion scientifique isolée continuable, erreur JUnit/infra qui arrête, interruption entre cas, interruption `RESERVED` non rejouable, reprise explicite sans doublon, et altération du JUnit, reçu, préflight, manifeste préparé, manifeste autorisé ou checkpoint. Ils n’établissent aucune valeur numérique de QF Solver.

## Recommandation

Garder les six contrôles comme sentinelles de développement. Après activation officielle et une campagne Owner autorisée, rapporter chacun individuellement comme `PASS_BOUNDED`, `FAIL`, `EXECUTION_INFRASTRUCTURE_FAILURE` ou `PRE_RESERVATION_REFUSAL`, en distinguant les assertions réelles et les refus du contrôleur. Ne promouvoir aucune maturité WP12-A sur la seule base d’un PASS de sentinelle ; ne pas qualifier MPC/RBE ou les modèles de grande taille sans contrôles indépendants dédiés.
