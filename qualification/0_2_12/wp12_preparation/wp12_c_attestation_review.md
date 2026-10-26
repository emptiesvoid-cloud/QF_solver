# WP12-C — Attestation synthétique du processus enfant

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Date : 2026-10-26. Base de travail vérifiée : `fd560aeb737ee5b7fc122a9ae0cb15eeed35421c`, arbre `0e16f41a46e52b58e954c56e887f44701e462a9b`. La branche distante était au même commit avant intervention. Le checkout scientifique `00428adf38e9397340ac136f6f503a268eb671da` / `df4ec667bf746b042c900fad1f86bf542e1a437b` et le checkout runner historique `782820fe31fa8b69223bd368e39949fca325ba3e` / `100d7b3ca869cad267666337947f204c9c8bf31e` étaient séparés et propres.

## Résultat

Une chaîne de supervision **synthétique uniquement** a été ajoutée dans `scripts/wp12_runner/process_attestation.py`. Elle utilise une décision Ed25519 éphémère fournie par les tests, n'accepte que des labels factices codés en dur et construit elle-même la commande vers `tests/fixtures/wp12_runner/attestation_fake_child.py`. Aucun argument, interpréteur, chemin de travail ou sélecteur pytest arbitraire n'est fourni par l'appelant.

Sur Windows, le faux enfant est créé suspendu, affecté au Job Object sans reprise, puis contrôlé par PID, PID parent, chemin/hash d'image, ligne de commande et SID du token. Le superviseur le reprend une seule fois après ces contrôles. Le Job Object impose les limites synthétiques de nombre de processus, mémoire et temps CPU configurées dans le test. En cas d'erreur d'affectation, d'interruption ou d'exception, le superviseur termine le Job et le handle exact de l'enfant, puis vérifie que le processus est terminé. Hors Windows, le lancement est refusé avant réservation.

Le résultat ne devient `PASS` que si l'enfant factice termine avec le code attendu, si le JUnit contient un seul testcase au label synthétique exact et si ses compteurs concordent. Une sélection manquante ou contradictoire produit `INFRA_ERROR`; un testcase explicitement en échec produit `FAIL`. Le reçu inclut les identités observées, les hashes des sorties, le statut et la chaîne du ledger. L'archive est créée sans écrasement après la terminaison du processus.

## Limites de preuve

Cette chaîne ne constitue **pas** encore un superviseur SYSTEM indépendant : le processus qui lance l'enfant, le contrôle et écrit l'archive tourne sous le compte courant. Le SID dédié `QF_WP12_RUNNER` n'est pas configuré et aucun broker privilégié ne fournit un token runner. Le trust store HKLM et sa clé Owner réelle ne sont pas configurés; les tests injectent des clés éphémères. Le reçu et le ledger restent accessibles au même compte dans le test synthétique. Le chemin d'image est observé puis hashé par chemin, sans verrouillage de handle de fichier contre une substitution concurrente; les contrôles de chemins n'éliminent pas les courses TOCTOU. Le plafond d'octets stdout/stderr du harness est contrôlé après capture, et ne constitue pas un plafond mémoire dur pour un enfant arbitraire.

Le JUnit du test factice est une sortie produite par ce faux enfant; aucun pytest QF Solver n'a été lancé. Le statut du processus, le statut JUnit, un verdict d'oracle scientifique et une qualification Owner demeurent quatre affirmations distinctes. La nouvelle suite n'apporte aucune preuve mécanique.

Les entrées `EXECUTE` existantes restent inchangées et bloquées par `SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED`, par le refus bas niveau et par les contrôles d'archive. La démonstration synthétique ne retire aucune de ces barrières.

## Manifeste pilote révisé

Le runner synthétique est maintenant identifié par le commit `f9707fdcab3fad2104345085c22db7f7c007567b` / tree `d813ecef91a2299d5fd5f99538ce1323ec7512a7`. Une nouvelle révision [v4](wp12_c_pilot_manifest_v4.json) préserve le manifeste v3 et lie séparément le code scientifique gelé et ce runner. Elle reste `FROZEN_NOT_AUTHORIZED`; son SHA-256 est `09ae6021f1248f4210ede7e42446fc44c7e5c048233239e91c06064e2c7f6c27`. Le schéma et les 144 empreintes de fichiers ont été vérifiés statiquement contre les checkouts référencés. Le détail des chemins et de la validation figure dans la [revue du manifeste v4](wp12_c_pilot_manifest_review.md). Cette révision ne peut pas autoriser le pilote : trust store, décision Owner, compte isolé, isolation vérifiée, revue du chemin scientifique et archivage protégé restent absents.

## Revue indépendante

Une revue indépendante en lecture seule a d'abord relevé que le faux enfant était repris avant l'inspection de son identité. Le code a été corrigé : affectation au Job avec `resume=False`, vérification de l'identité, puis reprise unique. La seconde revue a relevé le lancement non suspendu hors Windows et le risque qu'un enfant reste hors Job si l'affectation échoue. Le code refuse maintenant les plateformes non Windows et termine directement le handle du processus en plus du Job. La revue finale a confirmé l'ordre suspendre → affecter → observer → reprendre, ainsi que les chemins de terminaison. Elle confirme également que ces contrôles ne prouvent ni l'isolation des fichiers ni la protection d'une archive réelle.

## Vérifications exécutées

- `python -m pytest --noconftest -p no:cacheprovider -q tests/unit/test_wp12_process_attestation.py` — **18 passed**. Suite propre au superviseur; uniquement enfants factices, clés éphémères et répertoires temporaires.
- Six tests de régression ciblés de `tests/unit/test_wp12_qualification_runner.py` — **6 passed** : refus bas niveau, refus des flags pytest arbitraires, terminaison d'un descendant, limites Job Object mémoire et CPU sur enfants factices, et refus inconditionnel du point d'entrée pilote.
- Ruff ciblé — réussi.
- `py_compile` des deux nouveaux modules/tests et de `windows_job.py` — réussi.
- `git diff --check` — réussi au contrôle courant.
- Aucun test scientifique, pytest QF Solver, solveur, QEP, calcul FEM, benchmark ou campagne WP12 n'a été lancé.

## Windows 10 et profil alternatif

Lecture seule du registre sur l'hôte le 2026-10-26 : Windows 10 Enterprise 22H2 x64, build `19045.6456`. `Set-WP12LocalIsolation.ps1` exige explicitement `19045.7807` ou plus. Cette valeur est un **seuil de politique d'isolation configuré dans le script**, et non une dépendance technique démontrée par le code du Job Object ou par les appels Win32 utilisés. Elle reste inchangée et bloquante jusqu'à décision Owner; aucune mise à jour n'a été installée.

Profil alternatif à soumettre à une nouvelle revue : Windows 11 Enterprise x64 sur un canal et une build encore supportés à la date du provisionnement, avec le même compte non administrateur dédié, les mêmes protections NTFS, le même trust pin et les mêmes contrôles de Job Object. Au 2026-10-26, les informations Microsoft indiquent Windows 11 26H2 en disponibilité générale; le script actuel n'accepte pas ce profil. Il faudrait donc une décision Owner explicite, une modification séparée de la politique, une validation de compatibilité et une nouvelle revue de sécurité avant tout provisionnement. La version de Windows seule ne fournit ni sandbox de fichiers ni protection des preuves.

Références de fraîcheur : [Windows 10 release information](https://learn.microsoft.com/en-us/windows/release-health/release-information), [Windows 11 release information](https://learn.microsoft.com/en-us/windows/release-health/windows11-release-information), [CreateProcessAsUserW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Écarts et décisions Owner restants

1. Choisir le maintien du profil Windows 10 avec build minimale `19045.7807` ou demander une revue du profil Windows 11; aucune dérogation n'est appliquée.
2. Provisionner, par action administrateur contrôlée, le compte runner standard, ses ACL NTFS et les destinations protégées. Le compte d'exécution ne doit pas écrire dans le trust store, les décisions ou les archives historiques.
3. Implémenter et installer un broker SYSTEM audité qui authentifie une décision depuis une racine de confiance indépendante, obtient/vérifie le token du compte runner, crée l'enfant suspendu sous ce SID, observe le processus et ses descendants, puis archive par handles/destinations protégés.
4. Provisionner le trust store public, son pin et ses ACL hors checkout; ne pas envoyer de clé privée dans le dépôt ou le chat.
5. Faire signer une nouvelle décision Owner pour un manifeste pilote distinct, après recalcul de l'identité runner. Le manifeste v3 et toute signature qui le cible ne couvrent pas le nouveau code runner.
6. Faire relire indépendamment l'implémentation de production et vérifier le broker, le compte, les ACL, les limites du Job Object, le ledger et l'ancrage externe avant d'envisager l'unique pilote.

**État du runner :** l'attestation factice est démontrée; l'attestation privilégiée de processus scientifique et l'archivage protégé restent absents. `WP12_C_VERIFIED_WITH_LIMITATIONS`. WP11 reste `CLOSED`; WP12 et WP13 restent `OPEN`.
