# WP11-B — Évaluation du gate de clôture

Date : 2026-10-23
Branche : `codex/v0.2.12-integration`
Baseline : `a0846af0249ac3f3a37ec4e9c4900f1311c86238` / `b3b9886b7aa96874e5dfade5ea0e1c22c3b137ca`

## Statut proposé

**Statut officiel : `WP11=OPEN`.**
**Description de décision proposée : C — `OPEN_WITH_INTEGRATION_READY`.** Cette description n’est pas ajoutée comme nouveau statut normatif. Elle indique que la consolidation API/résultats et la traçabilité sont prêtes pour l’examen Owner, mais que le gate de clôture complet n’est pas encore démontré ou accepté comme clos.

La roadmap opérationnelle indique WP11 « intégration, résultats, API et sérialisation », `OPEN`, avec « gate d’intégration complet à démontrer ». Elle ne donne pas de liste détaillée d’essais, seuils ou format universel de résultat. Aucun critère de release nouveau n’est créé dans cette évaluation.

## État des critères existants

| Gate / contrat existant | État | Preuve et limite |
|---|---|---|
| Identité de la branche commune | **Satisfait pour la baseline auditée** | HEAD/tree et origin vérifiés avant changement; HEAD/tree après commit doivent être lus dans le rapport final. |
| Inventaire des modules et branches | **Satisfait pour WP11-A** | Inventaire de 1 688 fichiers Python et comparaison des arbres C02/D01/E01 préservés. Cette différence d’arbres ne prouve pas à elle seule une dépendance. |
| Façade et classification API | **Satisfait dans le périmètre testé** | Tests contrôlent 77 exports (30 STABLE / 47 PROVISIONAL), signatures critiques et compatibilité de façade. Les docs courantes indiquent maintenant 0.2.12. |
| Entrée modèle | **Satisfait au niveau de contrat inventorié** | JSON schema v1 documenté; v2 n’est pas annoncé. `read_inp` garde son périmètre partiel. |
| Résultats, sérialisation et provenance | **Partiellement satisfait; limite explicite** | DTO standards `to_dict()` sans identifiant commun versionné ni lecteur générique; Modal-Newmark et Reduced-Harmonic ont leurs contrats v1; HDF5 mixte version 1.0; D02 a son schéma v1. Le paquet prouve ces différences et teste des round-trips DTO synthétiques sans solveur. La roadmap ne dit pas si un schéma universel est exigé : l’Owner doit décider si l’inventaire contractuel actuel suffit. |
| Maturité et refus expérimentaux | **Satisfait pour les capacités retenues** | D02 demeure `CLOSED_BOUNDED`; E01 demeure `OPEN_WITH_BOUNDED_CERTIFICATES`; restrictions et champs NOT_ASSESSED sont reportés dans la matrice et les références. |
| Statuts scientifiques et preuves historiques | **Satisfait comme préservation, non comme nouveau run** | Certificat GF4 reste borné au sous-système esclave exact; raw BA `FAIL`; maître `NOT_VERIFIED`; qualification générale `NOT_ACQUIRED`; tangente J2 globale `UNRESOLVED`. |
| Démonstration du « gate d’intégration complet » | **Ouvert** | La matrice et les tests non qualifiants démontrent le contrat documenté, pas une définition Owner plus détaillée ou une acceptation formelle de clôture. Aucun nouveau RUN FEM n’était autorisé. |
| Dépendance à C02 | **Pas de dépendance directe démontrée** | La comparaison WP11-A relève des chemins divergents/risques de réconciliation; aucun code C02 n’a été intégré. Un contrat Owner explicite reste prioritaire s’il existe. |
| Dépendance à D01 | **Pas de dépendance directe démontrée** | D01 reste hors de ce candidat. L’ordre historique de la roadmap est conservé; l’audit n’a pas trouvé d’API/source consommée nécessitant le code D01. Si un gate contractuel explicite exige D01, il reste ouvert. |
| WP12 / WP13 | **Restent ouverts séparément** | WP11-B ne les clôture pas. WP12 peut consommer des contrats explicitement identifiés; son besoin d’un schéma ou d’une capacité supplémentaire dépend de son scope approuvé. |

## Risques et findings résiduels

- **P2 — contrat commun des résultats :** les résultats ordinaires sont hétérogènes et n’ont pas de lecteur générique. C’est un fait API/documentaire; aucun défaut de lecture/écriture des formats couverts par les tests exécutés n’a été démontré. Ne pas inventer une obligation de schéma universel si elle n’est pas dans le contrat WP11 approuvé.
- **P2 — limites de tests :** les contrôles ont exclu les workflows de solveur, l’assemblage multifamille et les tests D02 qui construisent des opérateurs/évaluent une réponse dynamique. Les résultats historiques exacts restent la preuve pour les scopes fermés/bornés.
- **P1 scientifique non résolu hors du gate général d’intégration API :** la tangente J2 globale n’est pas résolue et le maître GF4 n’est pas vérifié. Cela interdit ces revendications, mais ne change pas la portée limitée des capacités E01 intégrées.
- **Séquençage :** aucun code de C02 ou D01 n’est intégré. Si une exigence propriétaire approuvée fait explicitement de leur clôture un gate WP11, cette exigence prévaut sur l’absence de dépendance technique constatée.

## Recommandation de clôture

Ne pas choisir A (`CLOSED_BOUNDED`) dans ce paquet : le critère roadmap de gate complet reste général et son acceptation de clôture n’a pas été établie indépendamment. Choisir **B (`OPEN`)** comme statut officiel, et **C** comme description si l’Owner souhaite signaler que l’intégration contractuelle est prête pour décision. Cela n’empêche pas la préparation ciblée de WP12 lorsque ses contrats consommés sont établis; cela ne ferme pas WP12/13 ni n’ajoute un gate à leur plan.

La décision Owner restant à obtenir est : (1) si les contrats de résultats hétérogènes mais documentés suffisent pour le gate WP11 actuel; (2) si un contrat explicite impose C02 ou D01 comme dépendance de séquencement; (3) si la preuve consolidée et sa revue sont acceptées comme démonstration du gate d’intégration. Jusqu’à cette décision, maintenir `WP11=OPEN`.

## Activités hors périmètre

Aucun solveur FEM public ou privé, assemblage global, Newton/Armijo, Docker, calcul FEM qualifiant, merge vers `main`, tag ou publication n’a été exécuté ou demandé.
