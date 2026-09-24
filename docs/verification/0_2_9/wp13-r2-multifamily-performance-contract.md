# WP13 R2 — extension de caractérisation J2 à quatre familles

## Objet

Cette révision ajoute **HEX8 et HEX20** à la caractérisation de coût non linéaire J2 qui ne couvrait jusque-là que TET4 et TET10. Elle ne remplace pas WP13 R1 : contrat, exécution et preuves R1 restent dans leurs chemins historiques et ne sont pas réécrits.

Le nouveau contrat gelé est [`wp13_r2_execution_contract.json`](../../../qualification/0_2_9/wp13_r2_multifamily/wp13_r2_execution_contract.json). Il lie l’exécution aux SHA-256 du runner, du générateur de maillages, des tests et du `.gitignore`, puis exige une exécution séquentielle depuis le commit qui ajoute ce contrat.

## Cas commun

Les quatre cas utilisent la même barre `1.0 × 0.2 × 0.2 m`, le même matériau de von Mises J2 isotrope (`E=210 GPa`, `ν=0.3`, limite d’élasticité `250 MPa`, écrouissage `50 GPa`), les mêmes appuis, la traction `300 MPa` sur `x_max` et le même chemin cyclique de 24 facteurs. Le solveur est exécuté une famille à la fois.

| Famille | Maillage gelé | Éléments attendus | But de comparaison |
|---|---|---:|---|
| TET4 | Gmsh tétra, taille `0.18 m`, ordre 1 | issu du générateur existant | référence basse résolution |
| TET10 | Gmsh tétra, taille `0.18 m`, ordre 2 | issu du générateur existant | référence quadratique |
| HEX8 | structuré `6×2×2`, ordre 1 | 24 | nouvelle famille hexa linéaire |
| HEX20 | structuré `6×2×2`, ordre 2 incomplet | 24 | nouvelle famille hexa quadratique |

Les résolutions et ordres d’interpolation ne sont pas strictement équivalents. Les temps sont descriptifs pour cette machine ; ils ne démontrent ni efficacité intrinsèque relative des éléments, ni convergence, ni performance générale.

## Exécution et preuves

Le préflight doit confirmer branche `codex/wp13-r2-multifamily`, arbre propre, contrat gelé, parent d’exécution exact, policy digest inchangé et hashes sources conformes. Le runner refuse un autre dossier de sortie ou un dossier brut déjà rempli. Il vérifie le type exact de chaque élément, l’intégrité finie du résultat complet et les 24 incréments.

Les résultats complets (`result.json`), maillages et rapports d’import restent sous `qualification/0_2_9/wp13_r2_multifamily/raw/`, ignoré par Git pour éviter de gonfler le dépôt. Le manifeste versionné doit fournir les tailles et SHA-256 de chaque fichier brut. Le rapport compact, l’enregistrement d’exécution et le manifeste restent versionnés. Un hash de manifeste ne remplace pas une archive externe.

Les seuls avertissements d’import autorisés pour les maillages tétra sont les groupes physiques `y_min` et `z_min` inutilisés, hérités du générateur générique et consignés. Le statut géométrique du maillage doit rester `PASS`. Les imports HEX8/HEX20 doivent être sans avertissement.

## Vérification ciblée

Après gel du contrat, exécuter la commande exacte de tests dans le contrat. Elle couvre les contrats API/diagnostics/harness précédents et les tests du générateur hexa et du setup commun. Puis lancer une fois la commande campagne gelée. Ne pas lancer la suite complète du dépôt.

## Gouvernance et limites

- Aucun noyau ou comportement numérique du solveur ne doit changer.
- Aucun seuil de temps, mémoire, vitesse, convergence de maillage ou classement des familles n’est introduit.
- Aucun point WP13 n’est attribué par cette révision.
- Aucune mise à jour du ledger, exécution WP14, fusion ou publication n’est autorisée par ce contrat.
- Cette caractérisation ne vaut pas corrélation externe, validation de précision ni qualification de tous les éléments ou méthodes.

Le statut après exécution devra être communiqué comme candidat technique avec limites et soumis à revue Owner ; R1 et toute preuve d’échec historique restent intacts.
