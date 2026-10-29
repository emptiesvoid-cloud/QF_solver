# Proposition de décision Owner — diagnostic H1 après clôture VV3D R1

**Statut : proposition uniquement — aucune autorisation d'exécution.**

## Décisions proposées

1. Confirmer pour la campagne `WP12-VV3D-ADAPTIVE-20261029-R1` que toute issue non PASS arrête la campagne. Une `SCIENTIFIC_DEVIATION`, un `PYTEST_FAILED` ou un `INCONCLUSIVE` ne peut jamais autoriser une transition adaptative de R1.
2. Ne pas autoriser le candidat H1 actuellement catalogué comme continuation de R1. Son seuil de déclenchement est le même ordre observé qui fait échouer un `CAMPAIGN_GATE`; son éligibilité exigerait alors simultanément le PASS et l'échec de ce gate.
3. Autoriser, si souhaité, la préparation d'un **nouveau diagnostic H1 indépendant** après la clôture documentée de R1. Cette décision de préparation n'autoriserait pas son exécution.

## Contrat requis pour un diagnostic indépendant

Avant toute exécution, un dossier distinct devra fixer et faire approuver :

- un nouvel identifiant de campagne et un scope contrôleur dédié ;
- un nodeid exact et un catalogue fermé ;
- un ledger neuf, à chemin physique distinct du ledger R1, avec un lien documentaire/hashé vers le reçu de clôture R1 ;
- un modèle H1, son maillage, les observables et les critères inchangés ou explicitement révisés par décision scientifique ;
- les fingerprints science, contrôleur et runtime, ainsi que le préflight collect-only et le manifeste exacts ;
- un budget autonome (tentatives, temps par tentative et total, RSS, archives, DDL), sans consommation ni transfert du budget R1 ;
- une décision Owner d'exécution séparée, liée au manifeste et aux empreintes finales ;
- des conditions d'arrêt couvrant échec scientifique, données incomplètes, provenance et ledger.

Le déclencheur proposé est uniquement la présence d'un reçu terminal immuable de R1 indiquant `SCIENTIFIC_DEVIATION`, avec aucun run ou réservation R1 en cours. Le diagnostic lira les preuves R1 sans les modifier. Son résultat sera un résultat diagnostic du nouveau scope : il ne pourra ni remplacer le FAIL de R1, ni reprendre R1, ni autoriser automatiquement une autre campagne.

## Table de transitions R1

La transition `SCIENTIFIC_DEVIATION` de R1 doit rester `STOP`. Un H1 post-échec n'est donc pas une exception à cette transition : c'est une nouvelle campagne et une nouvelle décision. Le validateur R1 doit refuser une table qui associerait un échec scientifique à un nodeid adaptatif.

QLOAD et QPOST restent soumis aux gates de R1 : QLOAD exige le PASS vérifié du cas L3 et de l'évaluation de campagne ; QPOST exige également ce PASS exact et son archive hashée. Leur mesure diagnostique ne modifie pas le verdict ni les critères de R1.

## Limites de la présente proposition

Cette proposition ne fixe aucun nouveau seuil et ne fournit aucun budget numérique pour H1. Ces paramètres doivent être soumis à l'Owner dans le dossier de la nouvelle campagne, avec justification et empreintes. Elle n'autorise aucune réservation, aucun assemblage, aucune résolution FEM, aucun QPOST et aucune reprise de R1.
