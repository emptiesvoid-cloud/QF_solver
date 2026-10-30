# Dossier Owner prospectif — NON DÉCISIONNEL

Campagne `WP12-VV3D-ADAPTIVE-20261029-R1` ; état `PREPARATION_AUTHORIZED_EXECUTION_NOT_AUTHORIZED`. Ce brouillon n'est ni un manifeste d'exécution, ni un gel de critères, ni une autorisation. Il ne doit pas être signé ou utilisé comme décision finale avant achèvement du code et des contrôles ci-dessous.

## Périmètre scientifique proposé

Douze cas : TET4/TET10/HEX8 standard/HEX20, n=2,4,8 sur Ω=[0,1]³ m. E=10⁶ Pa, ν=0,3, BC u=0 sur les six faces, force volumique analytique `−div σ` associée au déplacement lisse défini dans `oracle.py`. Il s'agit d'un essai de vérification de code 3D, non d'un porte-à-faux ni d'une validation expérimentale. Les douze maillages, DDL, éléments, contraintes et SHA-256 figurent dans `prepared_20261029/MATRIX_NOT_AUTHORIZED.json` ; qualité géométrique dans `MESH_QUALITY_REPORT.json`.

## Budget proposé par le mandat reçu

24 tentatives au total, 28 800 s cumulées, 1 200 s maximum/tentative, RSS surveillée 4 096 MiB/processus, maximum 30 000 DDL, concurrence 1 et aucun retry implicite. À 1 200 s chacune, douze tentatives initiales représentent au plus 14 400 s et 24 au plus 28 800 s, sans prédiction de durée réelle. Les événements d'échec, interruption et dépassement, la méthode de mesure cumulée, l'imputation après crash et les conditions d'adaptation doivent être fixés avec la suite du mandat, qui a été reçue tronquée. Les vérifications de `budget.py` n'effectuent aucune réservation et ne sont pas le ledger du contrôleur.

## Avant décision finale

1. Compléter et revoir l'adaptateur de charge variable, son raccordement au solveur et les contrôles de quadrature ; son entrée actuelle refuse l'exécution et le noyau privé n'a pas été exécuté.
2. Définir et implémenter les 12 nodeids exacts avec observables et archive create-only avant assertions ; figer les normes, unités, seuils et critères d'arrêt. Aucun seuil n'est ici approuvé.
3. Créer un mandat et un ledger globaux, séparés des campagnes historiques, avec réservation atomique et budget commun pour initial/adaptatif ; intégrer le contrôleur conformément à AGENTS.md et tester les refus sur fichiers synthétiques.
4. Figer HEAD/tree/fingerprint des sources et du runner, Python et bibliothèques, mesh et oracle ; enregistrer les cas, émettre et valider les préflights officiels collect-only et les manifestes non autorisés, puis établir leurs empreintes finales.
5. Présenter à l'Owner le contrat exact et ses SHA, la méthode de sélection adaptative et les limites ; aucune autorisation n'est implicite. Les modèles incomplets ne doivent jamais être exécutés comme modèles à charge nulle.

Les contraintes et décisions des campagnes R1/R2 HEX20 et HEX8-SRI sont indépendantes et ne confèrent aucune tentative à VV3D.
