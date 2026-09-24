# WP13 R2.1 — contrat d’exécution multi-familles

Le contrat R2 initial (`QF-029-WP13-EXEC-002`) est conservé sans modification. Sa première invocation du runner s’est arrêtée avant la campagne avec `ModuleNotFoundError: solveur`, car le lancement direct ne plaçait pas le répertoire `src/` dans le chemin Python. **Aucun maillage de campagne, solve, ou résultat brut n’a été créé.** Le répertoire de sortie R2 était absent après cet arrêt.

R2.1 corrige uniquement l’amorçage `src/` du script et rebinde les hashes de provenance. Il garde exactement le même contrat physique et numérique, le même ordre et les mêmes seuils/paramètres : TET4, TET10, HEX8 et HEX20, un par un. Le parent d’implémentation lié est `77a640b438b495603670a756b1ff2548b7a75ec3`; le contrat R2.1 doit être le commit suivant avant de pouvoir exécuter la campagne.

Le contrat machine complet est [`wp13_r2_1_execution_contract.json`](../../../qualification/0_2_9/wp13_r2_multifamily/wp13_r2_1_execution_contract.json). Le runner vérifie lui-même branche, arbre propre, parent, digest de politique, hashes sources et chemin brut avant de commencer.

Les sorties brutes intégrales restent locales dans `qualification/0_2_9/wp13_r2_multifamily/raw/` (ignoré par Git). Le rapport compact et le manifeste hashé seront versionnés après exécution. R1 demeure intact ; WP14, le ledger, points officiels, merge et push restent hors périmètre.

La caractérisation reste expérimentale et descriptive sur une machine. Les maillages ne sont pas d’une résolution strictement équivalente : aucun classement d’efficacité, résultat de convergence, claim de performance générale ou point WP13 n’en découle.
