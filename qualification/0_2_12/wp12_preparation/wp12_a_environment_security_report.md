# WP12-A — État de sécurité de l'environnement

PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN

## Résumé

L'environnement observé ne satisfait pas le profil d'exécution scientifique isolé. L'attestation [wp12_a_isolation_attestation.json](wp12_a_isolation_attestation.json) reste NOT_VERIFIED. Le compte est non-administrateur mais n'est pas un compte runner dédié. Le compte courant peut écrire dans les checkouts, sources/tests et archives de qualification; cela interdit de protéger les preuves historiques contre le processus lancé sous ce compte.

L'identité du compte a été vérifiée localement et est volontairement expurgée des documents suivis. Aucune clé Owner réelle n'a été demandée, générée ou installée. Aucun registre HKLM, ACL système ou paramètre GitHub n'a été modifié.

## Contrôles observés

| Contrôle | Observation | Garantie disponible | Verdict |
|---|---|---|---|
| Compte Windows | Identité contrôlée; non administrateur; pas dédié | Contrôle d'identité local, sans séparation de compte | Insuffisant |
| Python | CPython 3.13.1 x64, système C:/Python313/python.exe; pas de venv dédié | Binaire et SHA statiques consignés au manifeste | Insuffisant pour une exécution isolée |
| Dépendances | qf-solver 0.2.10, NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1, plus bibliothèques natives hashées | Métadonnées et fichiers présents inspectés sans import du solveur | Ne prouve pas l'origine réellement importée ni les DLL chargées |
| Origine du solveur | Aucun import du package effectué | Aucune | NOT_VERIFIED; blocker |
| Checkout scientifique et checkout runner | ACL effectives autorisent l'écriture depuis le contexte actuel | Aucune protection lecture seule pour un enfant | Échec |
| Archives de qualification historiques | ACL effectives autorisent également l'écriture | Aucune protection lecture seule | Échec bloquant |
| Trust store et pin machine | Non configurés | Pas de racine de confiance Owner | Échec bloquant |
| Terminaison des descendants | Job Object exercé sur enfants factices | Kill-on-close/descendants vérifiés synthétiquement sous Windows | Pas de preuve sur campagne scientifique |
| Mémoire et nombre de processus | Job Object exercé avec limites synthétiques | Mécanismes durs disponibles sur Windows dans le test factice | Pas de preuve d'application à un processus QF |
| Temps wall et journaux | Timeout et plafonds stdout/stderr testés sur enfants factices | Supervision du runner | Uniquement synthétique |
| Temps CPU | Le plafond CPU dur n'est pas démontré | Observation/arrêt wall seulement | Soft; ne pas appeler cela un quota |
| Threads | Valeurs de profil "1" proposées, mais non appliquées par un exécuteur scientifique | Pas de plafond dur | Soft |
| Stockage | Destination non créée; aucun quota | Contrôles de chemin/collision seulement | Soft; pas une garantie contre l'épuisement disque |
| Ancrage indépendant des preuves | Non configuré | Hash-chain locale seulement, modifiable par un acteur ayant accès en écriture | Échec si l'ancrage indépendant est exigé |

Un Windows Job Object ne sandboxe pas l'accès aux fichiers. Le polling de RSS ne constitue pas un plafond mémoire, et un contrôle de chemin n'est pas une ACL. Le profil mémoire/processus testé synthétiquement n'isole pas les archives auxquelles le même compte a accès.

## Mesures nécessaires avant réexamen

1. Utiliser un compte Windows standard dédié ou une VM isolée dont l'administrateur/propriétaire est distinct du compte d'exécution.
2. Placer les checkouts scientifiques et runner en lecture seule pour ce compte, avec une vérification des ACL effectives sur fichiers et dossiers; placer les archives historiques sur un volume ou sous une ACL qu'il ne peut pas modifier.
3. Autoriser l'écriture uniquement dans un répertoire de preuve neuf et un temporaire dédié; vérifier l'absence de collision, lien symbolique/junction et chemin traversant. Si un quota stockage dur est requis, employer un volume/quota qui l'applique réellement.
4. Provisionner le trust store public hors checkout, protéger fichier, répertoire et pin HKLM contre l'écriture du compte runner; faire vérifier les ACL et le hash par un administrateur indépendant. La clé privée demeure sous contrôle Owner et hors du dépôt.
5. Figer l'environnement enfant : python exact, environnement de packages, profil de threads réellement appliqué, origine d'import du solveur et bibliothèques chargées. L'inspection actuelle a volontairement évité l'import QF.
6. Vérifier les limites du Job Object dans le compte/environnement retenu, puis effectuer les tests de terminaison et dépassement uniquement avec enfants factices. Une limite non garantie entraîne un refus ou le choix d'une VM/solution de confinement adaptée.
7. Définir un ancrage indépendant pour recevoir les empreintes/reçus si la politique Owner requiert une résistance à la modification après campagne.

Ces étapes demandent des interventions et décisions Owner. Aucune n'a été effectuée. Le runner ne doit pas réduire les exigences ou convertir un contrôle soft en garantie dure pour obtenir un lancement.
