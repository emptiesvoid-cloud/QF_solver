# WP-D01 — Intégration prospective de la projection Rayleigh structurée

## Verdict borné

`D01_STABLE_PROJECTION_MERGE_CANDIDATE`

Ce changement ajoute au chemin harmonique réduit une sélection explicite de projection Rayleigh structurée. La voie historique reste la valeur par défaut. Le correctif est vérifié sur les opérandes M3 archivés et sur des tests algébriques non FEM ; il ne constitue pas une nouvelle exécution FEM ni une qualification. La fusion reste conditionnée à la revue indépendante et à l’intégration propre dans le worktree de destination.

Statuts conservés : `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED`, `WP05_FEM_QUALIFICATION=NOT_EVALUATED`, `WP11=PAUSED_BY_OWNER`.

## Identités et préservation

- Prototype de référence : commit `e6b63dfe7c1c3a00fd897c107a2322a3172ff96f`, tree `28f3160aedacc166bcc158e1fb473ef1d5c53295`.
- Base d’intégration : `codex/v0.2.12-integration`, HEAD initial `9035adff88b42e2ed8172260ead7c74485494d88`, tree `4eededfe7e9e589769f0d7b885f213945c9f807e`.
- Branche isolée de travail : `codex/wp-d01-stable-projection-20261024`.
- Les changements locaux C01/E01/AGENTS du worktree d’intégration d’origine n’ont pas été touchés.
- Les quatre artefacts non suivis de récupération M3 dans le worktree D01 d’origine ont été laissés intacts.
- Archive M3 lue sans modification : `attempt3_recovered.json`, SHA-256 `fbc7ed535fe6f32582aca03439e55c1584c57b6eaddc1ce7d73880796485332e`.

Le commit prototype n’est pas ancêtre de la branche d’intégration ; ses changements divergents n’ont donc pas été fusionnés. Seule la méthode pertinente a été portée dans une branche neuve dérivée du HEAD d’intégration indiqué ci-dessus.

## Méthode retenue : B, exclusivement pour le Rayleigh déclaré

Pour un amortissement Rayleigh vérifié `C = αM + βK`, le nouveau choix explicite `reduced_damping_projection="rayleigh_structured"` calcule `Cᵣ = α Mᵣ + β Kᵣ`, avec `Mᵣ` et `Kᵣ` déjà projetés et validés par la base modale. Il ne moyenne pas les triangles et ne modifie aucun opérateur source. La matrice construite repasse le contrôle existant de symétrie relative `1e-12`. Une contraction directe indépendante est encore calculée ; elle doit être finie et cohérente avec la forme structurée sous la borne interne existante `_MODAL_RESIDUAL_MAX` (`1e-8`). Cette borne n’a pas été modifiée.

La sélection est disponible dans le résolveur réduit harmonique WP05 et validée par le schéma. Elle est interdite pour l’amortissement modal prescrit et les définitions non Rayleigh.

La sélection par défaut reste `legacy_direct` : `Φᵀ(CΦ)`, avec le même ordre de contrôle et le même payload de provenance historiques. Le nouveau comportement n’est donc jamais implicite. Les amortissements génériques non Rayleigh ne sont pas redirigés vers B ; aucune route publique de matrice C arbitraire n’a été introduite.

## Comparaison A/B/C sur les opérandes M3 conservés

L’archive a été relue après vérification de son SHA-256 et des hashes intégrés des CSR et tableaux binary64. Les imports du solveur pendant la replay provenaient du worktree isolé. Aucun `PreparedDynamicSystem.prepare`, assemblage K/M, extraction modale ou solveur FEM n’a été exécuté.

| Méthode | Définition et statut | M3, 2 modes | M3, 4 modes |
|---|---|---:|---:|
| A — historique | `Φᵀ(CΦ)` ; conservée, verdict historique intact | résidu `2.2293825935426e-12`, refus au seuil inchangé `1e-12` | résidu `7.0416551142576e-13`, sous le seuil |
| B — Rayleigh structuré | `αMᵣ+βKᵣ`, uniquement si Rayleigh déclaré | symétrie exacte des opérandes projetés archivés ; écart relatif à A `3.5487638618593e-11` | symétrie exacte ; écart relatif à A `2.9904661692244e-12` |
| C — contraction rationnelle exacte | oracle diagnostique hors ligne sur les binary64 d’entrée ; non intégré en production | symétrie exacte après arrondi final | symétrie exacte après arrondi final |

La replay du chemin de production retrouve A refusé à deux modes et accepté à quatre modes ; B passe le garde inchangé pour les deux comptes. Le contrôle de cohérence direct/structuré vaut respectivement `3.5487638618593e-11` et `2.9904661692244e-12`, sous la borne existante `1e-8`. C diffère de A de `7.5143798886e-12` et `7.4580829301e-13`. Ces valeurs distinguent la contraction du C binary64 stocké de la projection structurée de la définition Rayleigh ; elles ne changent pas les critères de qualification.

L’archive confirme que `C = 0.2 M + 2e-5 K` est exactement reproduit en binary64 pour les opérateurs stockés. Aucune conclusion ne s’étend à un amortissement non Rayleigh, à d’autres BLAS, bases ou maillages.

### Réponses réduites archivées

Les six points M3 déjà analysés sont `0 Hz` puis `4.5270493671`, `9.0540987342`, `18.0176564810`, `18.1081974683` et `18.1987384557 Hz`. Les mesures ci-dessous proviennent du post-traitement hors FEM antérieur de ces mêmes opérandes ; elles ne sont pas de nouveaux calculs de cette campagne :

- Différence maximale de déplacement reconstruit A/B : `3.89e-13` à 2 modes ; `3.64e-13` à 4 modes.
- Différence maximale A/C : `4.15e-14` et `3.05e-14` ; B/C : `3.51e-13` et `3.35e-13`.
- Erreur d’amplitude maximale de troncature historique : `2.94e-2` (2 modes) et `4.62e-3` (4 modes) ; erreur de phase maximale `2.07e-4 rad` et `3.16e-5 rad`.
- Aucune amélioration physique mesurable n’est attribuable à A/B/C dans ces réponses ; l’effet dominant documenté provient de la troncature et de la flexibilité résiduelle.

Les matrices exactes M1/M2 ne sont pas disponibles pour comparer A/B/C ; aucun opérateur n’a été reconstruit par un nouvel assemblage.

## Changements ciblés

- `src/solveur/core/analyses/modal_basis.py` : sélection explicite de méthode ; conservation de la voie directe ; ajout de B avec contrôles inchangés.
- `src/solveur/core/analyses/reduced_harmonic.py` : transmission du choix configuré et refus des valeurs inconnues ou de son emploi avec `prescribed_modal`.
- `src/solveur/core/analyses/settings.py` : contrat partagé validant le choix sur l’objet settings programmatique avant préparation ; valeurs autorisées et conditions Rayleigh explicites.
- `src/solveur/io/schema_analysis.py` : réutilise le même contrat et le valide avec la méthode effective, y compris la méthode par défaut.
- `tests/unit/test_modal_rayleigh_projection.py` : tests purement algébriques du dispatch, de l’équivalence, des refus et de la configuration.

Aucune équation physique, valeur de `α/β`, tolérance, oracle, réponse ou archive historique n’a été modifiée.

## Vérifications

- `python -m pytest -q tests/unit/test_modal_rayleigh_projection.py` : **21 PASS**.
- Tests algébriques existants (problème 2-DOF, coupure de cluster, covariance rotation/signe) : **3 PASS**.
- Replay M3 2/4 modes sur l’archive : A/B et seuil inchangé reproduits ; aucune FEM.
- Ruff ciblé : PASS.
- Compilation Python ciblée : PASS.
- `git diff --check` : PASS.
- Les comparaisons de réponse A/B/C sont des valeurs historiques archivées et post-traitées hors FEM, pas des sorties nouvelles du patch.

## Revue indépendante

La première revue read-only n’a trouvé aucun P0/P1, mais a relevé un P2 : le schéma laissait spécifier l’option hors `modal_superposition` ou avec `prescribed_modal`, ce qui pouvait produire une option ignorée ou un refus tardif. Correction appliquée : le validateur reçoit maintenant la méthode effective (y compris le défaut `direct_frequency`) et refuse l’option hors du chemin modal Rayleigh avant toute préparation. Des tests ciblent les méthodes directes, le défaut de méthode, `prescribed_modal`, ratios prescrits, modèle non-Rayleigh et valeurs mal formées. Une seconde revue indépendante du snapshot corrigé est requise avant commit/merge.

La seconde revue a confirmé la fermeture du cas JSON, puis relevé que les objets `FiniteElementModel` construits en Python peuvent contourner le schéma JSON. Correction appliquée : le contrat de sélection est centralisé dans `reduced_damping_projection_errors()` et appelé par `AnalysisSettings.validate()`, qui s’exécute lors de la construction du modèle et au début du solveur, avant préparation/assemblage. Le schéma JSON appelle la même fonction avec sa méthode effective. Les tests programment directement ces modèles/configurations sans préparer ni assembler de système. Une revue finale du snapshot consolidé reste requise avant commit/merge.

## Limites et étape suivante

1. La voie B n’est justifiée que si le modèle réellement sélectionné est Rayleigh ; une cohérence numérique seule ne prouve pas l’origine Rayleigh.
2. C reste un oracle de contraction hors ligne ; il n’est pas déployé.
3. La symétrie projetée obtenue par B n’acquiert ni C4 ni qualification FEM ; une validation FEM prospective reste nécessaire.
4. WP05 FEM M1/M2/M3 n’est pas promu ; M1/M2 n’ont pas d’opérandes archivés pour comparer A/B/C.
5. La revue indépendante finale du diff consolidé, puis un fast-forward sans conflit dans la branche d’intégration en préservant les changements C01/E01/AGENTS, restent requis avant `D01_STABLE_PROJECTION_MERGED`.

```text
WP_D01_STATUS=INCONCLUSIVE
C4=NOT_ACQUIRED
WP05_FEM_QUALIFICATION=NOT_EVALUATED
WP11=PAUSED_BY_OWNER
NEW_FEM_RUN=NOT_RUN
```
