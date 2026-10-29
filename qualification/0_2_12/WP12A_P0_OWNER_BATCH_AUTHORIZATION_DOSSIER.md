# WP12-A — Dossier Owner groupé, non prêt à autorisation

**Statut : `NOT_READY`.** Ne pas approuver d’exécution à partir de ce dossier. Aucun SHA-256 de manifeste ou de préflight nouveau n’est disponible ; les identités proposées sont décrites dans le [plan](WP12A_P0_BATCH_EXECUTION_PLAN.md).

Le contrôleur désigné ne peut pas actuellement offrir une revue groupée exécutable pour les six candidats : cinq ne sont pas allowlistés, le préflight est limité aux quatre anciens cas et l’état partagé du ledger invalidera les manifestes des cas suivants après la première réservation. Les décisions Owner sont actuellement attachées à chaque manifeste et à son SHA exact. Une autorisation de principe ou une décision groupée fictive ne peut pas être substituée à ces champs.

## Contenu requis avant de soumettre le dossier final

Pour chaque nodeid retenu : source propre HEAD/tree, fingerprint officiel et dépendances, inscription active et justification des DDL, budget 300 s maximum, identifiant et SHA du préflight `PREFLIGHT_PASS` (collecte unique, zéro skip/corps/réservation/mutation), manifeste `PREPARED_NOT_AUTHORIZED` et SHA brut, oracle, assertions et seuils existants, sorties et durée, historique de tentatives et conditions d’arrêt. Le contrôleur final doit être propre, officiellement désigné et identifié par HEAD/tree/fingerprint.

Le dossier commun devra préciser l’état du ledger et sa chaîne historique, l’ordre, les règles de consommation, l’arrêt sur toute divergence de provenance, et le maintien d’une tentative par cas sans retry. Les échecs scientifiques ne doivent pas interrompre un cas indépendant sauf si une condition globale de fiabilité ou d’intégrité est atteinte.

Une seule décision Owner groupée ne peut être proposée qu’après implémentation et revue d’un contrat officiel qui valide sans ambiguïté les décisions et les transitions de ledger pour chaque cas. Sous le contrat actuel, une décision distincte est nécessaire pour chaque manifeste courant et le manifeste du cas suivant ne peut être créé qu’après la tentative précédente. Les décisions ne sont pas transférables à des manifests régénérés.

**Blocages restants :** mise en œuvre et tests d’un contrat de campagne sûr ; inscription exacte des nodeids et actualisation des inventaires ; intégration et désignation du contrôleur selon les autorisations Git applicables ; démonstration des préflights officiels et de l’observabilité. Aucun hash définitif ou projet de décision d’exécution ne doit être inventé avant ces étapes.
