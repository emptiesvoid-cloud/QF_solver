# WP12-A — Résultats et disposition P0 du lot

**Campagne P0 supplémentaire : `NOT_RUN`.** Aucun FEM, eigensolve, harmonique, Newmark scientifique ou réservation réelle n’a été lancé dans cette préparation. Les quatre PASS scientifiques antérieurs sont conservés avec leurs identités et limites de la PR #64/#65 ; ils ne sont pas rejoués ici.

| Capacité MUST | Disposition au terme de cette préparation | Preuve / limite |
|---|---|---|
| `AN-MODAL` | `PARTIAL` | Historique borné ; le contrôle post-projection proposé est `NOT_RUN`. |
| `AN-MODAL-BASIS` | `PARTIAL` | Orthogonalité, dégénérescence et Rayleigh proposés ; aucun corps de test exécuté. |
| `AN-DIRECT-TRANSIENT` | `PARTIAL` | Le Newmark modal historique PASS ne couvre pas le plein ordre ; SDOF direct proposé, non enregistré. |
| `AN-DIRECT-HARMONIC` | `PARTIAL` | Comparaison direct/base complète PASS pour son cas historique ; SDOF direct analytique proposé, non enregistré. |
| `AN-PREPARED` | `PARTIAL` | Contrat d’identité et assemblage proposé, non enregistré. |
| `AN-EXCITATION` | `PARTIAL` | Base complexe historique PASS borné ; interactions de charge et opérateurs préparés pas encore reprises dans le lot. |
| `AN-REDUCED-HARMONIC` | `PASS` borné / `PARTIAL` général | Run historique `dev-0dd64d435dd1` ; résidu modal nul de la base tronquée et résidu physique libre `1 N`, pas de borne générale. |
| `AN-MODAL-NEWMARK` | `PASS` borné / `PARTIAL` général | Run historique r3 `dev-b81ed5a46142` ; un DDL, libre non amorti, résidu modal, pas de mesure du travail extérieur. |
| `ASM-STATIC` | `PARTIAL` | Résidus et assemblages de fixtures historiques ; aucune preuve exhaustive actuelle pour toutes les réactions/routes. |
| `API-IO` | `PARTIAL` | Quatre tests DTO synthétiques PASS sur la base inspectée ; aucun oracle mécanique ni couverture de tous les formats. |
| `API-CLI` | `PARTIAL` | Inventaire public synthétique PASS ; le dispatch CLI qui appelle un solveur reste non exécuté dans cette mission. |

Les 12 cas synthétiques de refus MPC/RBE ont passé sur la base inspectée ; cela rectifie la formulation plus ancienne qui indiquait une absence de tests spécifiques, mais ne prouve pas le support dynamique des contraintes. Les huit SHOULD et le DEFERRED restent dans la [matrice des 20 capacités](WP12A_REQUIREMENT_TO_EVIDENCE_MATRIX.md), avec D01 `INCONCLUSIVE`, D02 borné et limites RBE conservées.

Les ledgers totalisent 10/130 tentatives : 8 PASS et 2 `PYTEST_FAILED` historiques. Le FAIL Newmark du writer reste une tentative consommée avec verdict mécanique non établi. Aucun PASS de sentinelle n’acquiert la qualification physique générale. WP12 reste OPEN ; aucune décision de release ou de clôture générale n’est prise.
