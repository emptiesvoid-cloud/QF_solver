# Revue de consolidation de la route HEX8 EAS

La branche de revue est construite depuis la tête distante 0.3.0 vérifiée
directement à c4de3ff6bf4549bf68d34652bcf6fb05e36f43c4. Le lot de code
testé est 0ee6feadcbedd3ae0e6aeab1e31ab5db73e4c0ed, descendant direct
des commits 00195b8b et b3accf58. La branche locale de recherche 0.3.0 a
un historique distinct. La référence de suivi locale origin/0.3.0 était
c16d8f1d2228d901e9eefee2b0706ce9155d36a5 lors de la revue.

| Composant | Source | Preuve et portée | Décision |
|---|---|---|---|
| HEX8_EAS_EXPERIMENTAL, six modes, divergence moyenne, récupération | 00195b8b | Patchs élémentaires, rigidité, condensation et post-traitement ; cas global ν=0,3 exécuté dans la route produit avec source 5c6ab3f24192a0bbd277f95249168c1539728260, à rapprocher des rapports de route et de reprise | Inclus, explicite et expérimental |
| Diagnostic exact | 00195b8b | Tests synthétiques du garde et de l'enfant réel, wheel isolée | Inclus, désactivé par défaut |
| Acceptation exacte expérimentale | 0ee6fead | Rejeu du système capturé et résolution contrôlée source ae147db6 ; rejet historique et verdict complémentaire distincts | Inclus pour revue séparée de sa politique, désactivé par défaut |
| Facteurs QR et assemblage à sommes compensées | research/hex8_eas_experimental/coherent_operator.py, source 16cad564 | Campagnes planes par injection dans le worker, évaluateur et tangente cohérents ; moment amélioré sur certains cas, deux échecs historiques | Maintenu en recherche, l'injection remplace l'assemblage et la récupération produit, son port nécessite intégration et essais propres |
| Pression moyenne | 00195b8b | Formulation K V div_moy²/2 et récupération cohérente, étude hors ligne cf76dc01 | Incluse avec limite de précision documentée |
| Pression ponctuelle alternative | étude cf76dc01 | Améliore certains cas ν=0,3, dégrade très fortement ν=0,4999 et change les forces et l'énergie | Maintenue en recherche, hors lot |
| Contrôleurs et archives | sources des campagnes | Contrats, préflights et ledgers dans leurs espaces locaux, essais exploratoires et historiques | Hors lot produit |

La source ae147db6 capture une route d'acceptation exacte distincte de la
tangente QR. Les essais à tangente QR les plus récents utilisent les sources
1573ef4 et 16cad564 et un remplacement explicite de l'assemblage et de la
récupération par le worker. Leur preuve mécanique ne qualifie pas l'opérateur
de production de 0ee6fead. Le calcul de pression ponctuelle de cf76dc01
utilise des champs archivés et ne lance pas de nouvelle résolution.

L'élément est sélectionné par HEX8_EAS_EXPERIMENTAL et les analyses admises
sont linéaires statiques directes, petites déformations, matériau isotrope
et maillage EAS homogène. Le critère historique de reproduction directe des coefficients EAS à ν=0,3 reste NOT_MET car les bases locales diffèrent. Les champs physiques concordent dans les tolérances de cet essai. Dans le worker à relèvement, le post-traitement automatique porte sur la variable à conditions homogènes w. Le champ physique u=g+w nécessite une récupération distincte. Les autres routes conservent leur sélection
existante. La récupération emploie les variables condensées et une pression
K fois la divergence moyenne, positive en traction, en pascals.

Les options experimental_eas_exact_residual_diagnostic et
experimental_eas_exact_residual_acceptance sont distinctes et désactivées
par défaut. La première conserve le rejet historique même si le contrôle
exact réussit. La seconde peut, lorsqu'elle est explicitement activée,
retourner un candidat raffiné vérifié tout en conservant le verdict
historique REJECTED et son résultat supplémentaire. Le critère exact porte
sur les valeurs binaires stockées, sans garantie sur la mécanique.

Le témoin plan à pression moyenne présente une limite de trace liée au
nombre de couches. Les erreurs de contrainte restent significatives et
les bilans de moment deviennent sensibles à ν proche de 0,5. Les géométries,
chargements et modes faibles déjà explorés ne démontrent pas une stabilité
générale. Les ressources du superviseur sont bornées en taille d'entrée
et surveillées en temps et RSS. Le démarrage synchrone de l'enfant, la
RSS échantillonnée et le nettoyage de descendants ne constituent pas des
quotas OS stricts.

Décision B. Le lot est préparé pour une revue locale de son caractère
expérimental. Avant une intégration qui associerait les résultats récents
à la route produit, il faut porter et vérifier la tangente QR et sa
récupération dans l'assembleur réel, puis définir une campagne contrôlée
avec les critères de bilan et les conditions de garde explicites. Les
verdicts historiques PYTEST_FAILED, J7 FAIL et J14 PASS de développement
restent attachés à leurs archives.

## Vérification du lot code

La wheel construite depuis 0ee6fead a pour SHA-256
a6adcae5be3d63f71c041612eebca1bbadf05ee1d6c3a7bc7d234c9245c7c12e.
Sous Windows et Python 3.13.1, deux environnements isolés hors checkout ont
installé la wheel avec et sans l'extra eas-diagnostic. Les imports
proviennent de site-packages et research est absent. Les tests isolés
donnent 21 succès avec l'extra et deux sans psutil. Ils incluent un enfant
réel en mode spawn, timeout, interruption, archive altérée, garde rejeté
avec PASS exact et refus conservé, et acceptation expérimentale après
raffinement. Les tests de la route statique utilisent des doubles pour les
systèmes, l'assemblage et la réduction. Ils ne sont pas des calculs FEM.

Les tests ciblés dans le checkout couvrent les cinq tests de l'élément,
les routes et matériaux refusés, la cohérence force-tangente, la récupération
et l'écriture du résultat, les garde/diagnostic/acceptation et leurs échecs.
Quatre régressions élémentaires HEX8 et SRI passent. Ruff et git diff
--check passent. Aucun nouveau FEM ni test CI n'a été exécuté dans cette revue.
Les objets du lot ont été examinés pour les archives brutes, chemins
personnels et imports research dans les composants distribués.
