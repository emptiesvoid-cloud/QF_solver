# DEVELOPMENT_AUTONOMOUS — mise en service bornée

Date : 2026-10-24
Mandat : `DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1`
Décision : `DEVELOPMENT_AUTONOMOUS_FEM_ENABLED` dans le périmètre enregistré ci-dessous.

## Portée activée

Le lanceur non interactif `scripts/development_autonomous.py` n'accepte que des scopes de tests fixes. La politique versionnée dans `development_autonomous_policy.json` enregistre les worktrees canoniques, branches, commits de référence, racines `src`, nodeids exacts et budgets. Chaque résultat est placé dans un répertoire distinct `worktrees/<id>`; les scopes locaux sont séparés sous `standard/<scope>`.

| WP / mode | Checkout et identité de référence | Allowlist | Budget par tentative |
|---|---|---:|---|
| D01 `fem_exploratory` | `C:\wpc01-frictionless-public-integration-wp-d01-bp-exploratory`, branche `codex/wp-d01-ch-m3-diagnostic-20261023`, baseline `881014d878124e0ca27ce0ddc59ca20c90229c73` | 1 nodeid : diagnostic M3 amortissement projeté/flexibilité résiduelle | 180 s; RSS 2 Gio souple; sorties 64 Mio; temporaires 256 Mio surveillés; 8 processus observés; 3 tentatives/nodeid |
| C01 `fem_exploratory` | `C:\wpc01-frictionless-public-integration`, branche `emptiesvoids-cloud/wp-c01-contact-aware-equilibrium-audit`, baseline `3c0e0492104375fa01ce271896ca3e91c2cc53db` | 18 nodeids A/B legacy, `dimensional_v1` et diagnostics mécaniques | 1200 s; RSS 2 Gio souple; sorties 256 Mio; temporaires 512 Mio surveillés; 16 processus observés; 3 tentatives/nodeid |
| E01 `math_non_fem` | checkout d'intégration `tmp/qf-v0.2.12-integration`, branche `codex/v0.2.12-integration`, baseline `ae429934edc8a18d3febaf85d9b14b21d548eefe` | 15 nodeids de mathématiques constitutives ponctuelles/tangente; assemblage et FEM exclus | 900 s; RSS 2 Gio souple; sorties 64 Mio; temporaires 128 Mio surveillés; 16 processus observés; 3 tentatives/nodeid |

Les 554 empreintes ou identités de campagnes de qualification ne sont pas réutilisées comme autorisations. Les allowlists de développement sont prospectives et indépendantes.

## Contrôles et limites

- Le lanceur refuse un worktree non enregistré, une mauvaise racine Git/branche/histoire, une source `solveur` externe, un nodeid absent de l'allowlist ou une cible E01 évoquant les voies éléments/FEM.
- Les scopes génériques unit/intégration exigent un nodeid de fonction explicite, un à la fois; les répertoires, modules et suites complètes sont refusés afin de ne pas activer implicitement des tests FEM hors liste.
- Le worker enfant est lancé avec stdin fermé, les variables d'autorisation/qualification héritées retirées, les plugins/arguments pytest injectés neutralisés et les sorties séparées par worktree. L'origine de `solveur.__file__` est vérifiée dans l'enfant.
- Le plugin pytest exige la collecte du nodeid exact. Pour le seul nodeid D01 M3, il retire seulement le marqueur existant `NATIVE_AUTH_REQUIRED` après avoir vérifié son motif. Il ne change ni le test, ni le solveur, ni les seuils C4.
- Un verrou OS partagé sérialise les scénarios D01/C01 lancés par ce lanceur. Il ne bloque pas un processus lancé manuellement ou par un autre outil.
- Les sorties stdout/stderr sont plafonnées par le contrôleur applicatif. Timeout, RSS, nombre de processus, tailles d'archives/temporaires et espace disque sont surveillés par échantillonnage; la terminaison de l'arbre de processus est au mieux de l'effort. Ce mécanisme n'est ni un Job Object, ni une limite dure d'engagement mémoire, ni un quota NTFS, ni une sandbox.
- Un registre local persistant borne D01/C01/E01 à trois tentatives par nodeid pour ce mandat, refuse une répétition identique si empreinte source et justification sont inchangées, et conserve les tentatives interrompues comme consommées. C'est un contrôle procédural local, pas une protection contre la modification volontaire du registre par le même utilisateur.
- Les résultats portent `qualification=NOT_APPLICABLE_DEVELOPMENT_ONLY` et `qualification_promotion=PROHIBITED`. Aucun workflow du mode ne peut changer les statuts scientifiques, consommer un manifeste officiel, fusionner ou publier.

## Vérifications effectuées

- Collecte seule des allowlists : D01 `1/1`, C01 `18/18`, E01 `15/15`; aucun corps de test exécuté par ces collectes.
- Import en lecture seule : D01 a résolu `solveur` depuis `C:\wpc01-frictionless-public-integration-wp-d01-bp-exploratory\src\solveur\__init__.py`; C01 depuis `C:\wpc01-frictionless-public-integration\src\solveur\__init__.py`.
- Suite de contrat du dispositif : `21 passed` (refus hors périmètre, identités/imports, séparation qualification, limite d'essais, timeout et descendants synthétiques, plafonnement de capture, suivi des temporaires/RSS, écriture JSON atomique).
- `py_compile`, Ruff et `git diff --check` : réussis.
- Smoke test non-FEM par le lanceur : `test_identity_deformation_has_zero_energy_and_all_stresses` (E01, tentative 2/3) — PASS; 2,745 s, pic RSS observé 88 305 664 octets, un processus observé, sortie 219 octets. Le reçu local déclare explicitement que ce résultat n'est pas une preuve de qualification.
- Smoke test du scope unitaire générique par le lanceur : PASS, 4,31 s, pic RSS observé 86 994 944 octets, sortie capturée 100 octets. Les deux scopes génériques refusent maintenant toute demande de suite complète.
- Le node E01 du smoke math-only a consommé les tentatives 1 et 2 sur 3 : la seconde vérifiait explicitement l'ajout de la provenance runtime au reçu. Une seule tentative reste pour ce nodeid sous ce mandat; les autres allowlists FEM n'ont pas été lancées.
- Espace libre observé sur C: environ 21,6 Go. Aucun processus Python concurrent n'était présent lors de l'instantané de ressources.

Aucun calcul FEM D01 ou C01, aucun assemblage K/M, aucun solveur modal/harmonique, aucun Docker et aucun RUN de qualification n'ont été lancés pour cette mise en service. Le smoke test E01 est le seul test applicatif exécuté via le nouveau lanceur.

## Statuts

`DEVELOPMENT_AUTONOMOUS_FEM_ENABLED` signifie que le mécanisme est prêt à lancer uniquement les opérations enregistrées sans invite de confirmation interne. Les demandes d'approbation éventuelles de Codex, Windows ou de la plateforme restent hors de ce contrôle.

Statuts scientifiques inchangés : D01 diagnostics exploratoires uniquement; C01 benchmark prospectif uniquement; E01 math-only; `C4=NOT_ACQUIRED`; `WP05_FEM_QUALIFICATION=NOT_EVALUATED`; aucune qualification générale, intégration ou publication acquise.
