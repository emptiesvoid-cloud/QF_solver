# Revue de la tolérance de Coulomb sur R10 M4

## Règle numérique

`contact_friction_tolerance` est une tolérance relative dans le critère de variation de force de la route directe et dans les résidus normalisés des replis. Pour une capacité `c = μ max(p, 0) > 0`, le résidu hors du disque au point d'essai vaut `max(||f_trial|| − c, 0) / max(c, 1)` si la force retournée est la force d'essai. La classification utilise donc la bande `b = ε max(c, 1)` dans l'unité de force du modèle. La valeur du paramètre reste `ε = 1e-9` pour les deux contrats M4. L'ancienne règle ajoutait au rayon un nombre tiré de la tolérance de jeu en mètres.

La route directe peut retenir l'adhérence avec un dépassement physique d'au plus `b`. À la même distance sous la frontière, elle peut conserver un état de glissement déjà engagé. Le contrôle de variation de force entre itérations n'impose pas à lui seul le respect du disque exact. La classification post-racine partage cette hystérésis et la validation de la force en adhérence utilise la même bande. La projection couplée garde le disque exact dans son équation de projection, à l'erreur du solveur près. Son étiquette finale utilise la bande, sans état antérieur. Dans cette bande, la projection peut donc être à la limite alors que l'étiquette est `stick`.

À `ε = 1e-9`, la bande vaut `1e-9 N` pour `c = 0,2 N` et `5e-8 N` pour `c = 50 N`. Pour une très faible capacité positive, le dépassement absolu reste borné mais peut dépasser la capacité en valeur relative. Quand `0 < c ≤ b`, l'hystérésis peut conserver l'étiquette de glissement avec une force d'essai nulle. Le retour sans direction donne alors une force nulle. La candidate impose également une force tangentielle nulle à capacité exactement nulle dans la route directe. Un opérateur `μ = 0` demeure sans frottement. Le calcul de la bande refuse un débordement numérique et la mise à jour directe refuse une réaction non finie, y compris `−∞` qui aurait pu être écrêtée à zéro.

La référence vaut numériquement 1 dans l'unité de force des données, donc 1 N en SI. Le lecteur conserve les unités déclarées comme métadonnées. La conversion de longueur m vers mm à unité de force fixe conserve le classement si le déplacement et la raideur sont convertis ensemble. Une conversion N vers mN peut modifier la classification aux alentours du plancher. Par exemple, une capacité de 0,1 N et une marge de 0,5 nN donnent un état d'adhérence en N et un état de glissement avec les valeurs correspondantes en mN. Une bande proportionnelle à `c` seule supprimerait cette dépendance, mais ne suivrait plus le résidu actuel près de zéro. Un plancher paramétré dans une unité de force physique demanderait une convention commune à la classification et à tous les résidus.

Les seuils d'acceptation des rampes et la limite d'énumération restent ceux des contrats précédents. Le seuil normal historique de certains replis réutilise encore numériquement `gap_tolerance` comme seuil de réaction de fermeture. C'est une question distincte de la bande tangentielle. Le correctif remplace aussi les anciennes comparaisons tangentielles en force avec le jeu dans la validation post-racine. Les anciens critères par pas d'ouverture et d'état sont rejoués hors ligne, avec leur valeur historique.

## Sources et périmètre des contrôles

- Produit de référence vérifié sur le distant `57e04bf3e80e2846cb0f8d45a7dde40de917d2cf`. Port examiné `3886017246d358f10968a490feb006ce797e2243`. Code de la candidate exécutée `0ef2c9f6675af6f97465499b13ff5d5d03566774`, arbre `src` `38c8401ac42a9a61d455a6e9b9d6350ca17dbd35`. Tête des deux préflights et processus enfants `1a98cd5afe43e63191f0c013e7b09bdca8eb107d`.
- Les cinq fichiers de sortie, les deux reçus et les deux ledgers des variantes slip précédentes concordent avec leurs empreintes. Le contrat slip a le SHA-256 `304fdeeb3fec3c655b1e9578f01401cd9d721fefdfad3f2876c5b4ed966150c1`. Les arbres des variantes référence et mise à l'échelle concordent à `7d6d5da910dc5387eb554c00dcbb3f5ae5f0ddf5` et `e29d5e2d2c2a972c63fdff786337168f64715e2c`. Le contrat stick précédent, ses cinq sorties principales, son reçu et son ledger ont aussi été vérifiés.
- Le slip antérieur avec mise à l'échelle et le produit `57e04bf3` ont le même constructeur et le même générateur M4. Leur code de production diffère par le garde de récupération de réaction en cas de débordement. La comparaison slip inclut donc ce garde et la correction de tolérance. La capture ajoute des observables et le rejeu distingue les contrôles historiques de ceux du harnais courant.
- Les 82 tests du port ont passé, puis 88 sur la candidate avant exécution. La sélection finale compte 101 tests passés, dont les routes directe, post-racine et projection couplée près de la frontière, la transition vers l'ouverture, le cas sans frottement, les réactions non finies, les paramètres de tolérance invalides et les changements d'échelle. Windows, Python 3.13.1, pytest 8.4.1.

## Rejeu indépendant

Le rejeu valide le manifeste et l'empreinte, reconstruit les forces internes par contraintes TET4 à partir du maillage et des déplacements archivés, puis recalcule les gaps à partir du plan maître fixe. Il reconstruit les forces d'essai à partir du déplacement local, des références d'entrée et des raideurs archivées. Il vérifie la projection de Coulomb, les anciens critères par état et l'équilibre du solide. Les bases tangentes, les efforts de contact retournés et les déplacements proviennent de la capture. Les bases sont contrôlées comme orthonormales et tangentes au plan. Cette vérification n'appelle ni le solveur mécanique ni le constructeur des opérateurs de contact.

## Exécution

Les deux contrats bornent chacun une seule tentative et utilisent le même code produit, via `solve_model`, sans cache LU de harnais ni reprise de checkpoint. Le contrôleur a d'abord refusé un format d'identifiant de préflight puis un format d'identifiant de série. Ces refus sont antérieurs à toute réservation. Les deux préflights réussis collectent chacun le seul nodeid lié au contrat et vérifient la provenance du solveur importé. Le runner applique 480 s, 768 Mio de RSS surveillée, 32 Mio d'archive et de sorties cumulées, et 8 processus au maximum par tentative. Les mesures de mémoire et d'espace disque sont échantillonnées.

| Rampe | Scope | Préflight collect-only | Tentative | Runner / solveur / archive | Mural / solveur | RSS pic | Sorties |
|---|---|---|---:|---|---:|---:|---:|
| Stick | `m4_coulomb_stick` | `pf-9974abcd4a6d` | 1 | `PASS` / `RAMP_DIAGNOSTIC_PASS` / valide | 32,91 / 28,27 s | 487,7 Mio | 5,72 Mo |
| Slip | `m4_coulomb_slip` | `pf-b8bbf1480903` | 1 | `PASS` / `RAMP_DIAGNOSTIC_PASS` / valide | 341,93 / 337,65 s | 487,0 Mio | 10,13 Mo |

Les deux ledgers sont distincts et comptent une entrée chacun. Le SHA-256 stick est `d3fa4d62b7b0f812ea796d3a9d68fb9c59fe1815f71f7b867946cfeb9e18abf7`, celui du slip `882d6387d4352bff786bd4dff4ff8ce3955e1ceebaf22cf66d9717b2fb9a59f8`. Le fichier de résultats compact associe à chaque résultat le contrat, le reçu, l'archive et les empreintes des pièces. Les données brutes restent dans le magasin local des tentatives.

Les triplets donnent les nombres de contacts ouverts, en adhérence et en glissement. Tous les pas du tableau ont passé les contrôles. Les résidus d'équilibre libre et de Coulomb sont normalisés et sans dimension.

| Pas | États stick | Résidu libre stick | Coulomb stick | États slip | Résidu libre slip | Coulomb slip |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 / 75 / 6 | 4,21e-11 | 1,39e-17 | 0 / 75 / 6 | 4,21e-11 | 1,39e-17 |
| 2 | 0 / 81 / 0 | 3,68e-14 | 0 | 0 / 81 / 0 | 3,68e-14 | 0 |
| 3 | 0 / 81 / 0 | 2,45e-14 | 0 | 0 / 81 / 0 | 2,45e-14 | 0 |
| 4 | 0 / 81 / 0 | 1,84e-14 | 0 | 0 / 81 / 0 | 1,84e-14 | 0 |
| 5 | 0 / 81 / 0 | 1,69e-14 | 0 | 0 / 81 / 0 | 1,70e-14 | 0 |
| 6 | 0 / 81 / 0 | 1,69e-14 | 0 | 0 / 81 / 0 | 1,73e-14 | 0 |
| 7 | 0 / 81 / 0 | 1,70e-14 | 0 | 0 / 0 / 81 | 6,81e-14 | 1,87e-11 |
| 8 | 0 / 81 / 0 | 1,67e-14 | 0 | 18 / 0 / 63 | 1,49e-13 | 5,19e-11 |

Les six opérateurs initiaux 0, 8, 9, 63, 72 et 80 restent en glissement dans les deux rampes sous 250 N de compression et 0 N de charge tangentielle appliquée. Leurs marges, comprises entre `1,1538e-3` et `3,2878e-2 N`, sont identiques à celles de la capture précédente. La bande vaut `1e-9 N` pour chacun. Aucun contact en adhérence sur les seize pas n'a présenté de dépassement positif observé du disque.

Les seize pas reproduisent les chargements, états, ensembles actifs et empreintes des références de glissement d'entrée et de sortie de leurs comparateurs respectifs. L'archive de champs stick est identique par SHA-256 à la précédente. Le slip retrouve la transition de 45 à 81 contacts en projection couplée au pas 7 et de 36 à 72 puis 63 par la racine de glissement au pas 8. Le comparateur slip disponible inclut la mise à l'échelle normale, tandis que la variante de référence s'arrête au pas 7. Le verdict historique `FAIL_CLOSED` demeure distinct de ces essais. Le stick local v2 conserve huit pas et contrôles locaux réussis, avec préflight officiel et reconstruction indépendante `NOT_RUN`.

Le rejeu retrouve chaque gap et force d'essai archivés à la précision des données et satisfait les anciens contrôles par état sur les seize pas. L'écart maximal des multiplicateurs normaux est `4,89e-14 N` en stick et `3,91e-13 N` en slip. La pénétration maximale vaut respectivement `3,20e-16 m` et `1,36e-15 m`. Les maxima relatifs reconstruits de résultante et de moment, communs aux deux rampes au premier pas, valent `7,48e-12` et `6,53e-12`.

## Intégration

Le lot local est fondé sur le SHA produit vérifié et conserve l'arbre `src` exécuté. Ruff, la compilation Python, `git diff --check` et le contrôle de confidentialité des nouveaux objets Git passent. La suite complète et la CI protégée n'ont pas été exécutées. La branche distante reste à `57e04bf3`. Ces résultats couvrent les deux rampes exploratoires R10 M4. La séparation entre seuil de jeu et réaction près de l'ouverture dans les replis reste à étudier avant d'étendre les conclusions à d'autres routes.
