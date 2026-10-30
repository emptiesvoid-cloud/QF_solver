# WP12-A — Recommandation de clôture finale

## Verdict

**`WP12A_PARTIALLY_CLOSED`**

Ce verdict est le plus étroit qui corresponde aux critères trouvés dans la roadmap et aux décisions Owner effectivement prises.

| Objet | Décision factuelle |
|---|---|
| Quatre expériences ciblées | **CLOSED documentairement** sous le libellé Owner `WP12A_FOUR_EXPERIMENTS_DOCUMENTARY_CLOSED`. Les quatre tentatives retenues sont PASS de développement et les 31 artefacts cités dans la matrice de preuves ont des SHA-256 concordants. |
| Chantier WP12-A au sens de la roadmap 0.2.12 | **PARTIELLEMENT_CLOSED.** La définition inclut plus que ces quatre tests : projection et amortissement WP04, chemins plein ordre, opérateurs préparés, assemblage partagé, interfaces, et contrats transversaux MPC/RBE. Le registre 62-capacités attribue à WP12-A 11 P0/MUST, 8 P1/SHOULD et une P2/DEFERRED. La décision #65 ne dispose pas de la clôture de ces 20 capacités ni d’une exclusion formelle pour les éléments partiels. |
| Qualification physique générale de la dynamique | **NON ACQUISE.** Aucun niveau D parmi les quatre expériences. Les cas BEAM2 et TET4 sont petits ; plusieurs références utilisent ou partagent `K/M`, l’assemblage, la base ou la voie de calcul. |
| WP12 / release 0.2.12 | **WP12 reste OPEN ; WP13 reste OPEN.** La décision sur la release et la publication reste aux gates WP12/WP13 ; WP12-A seul ne peut la prononcer. |

## Faut-il une nouvelle expérience scientifique ?

- **Pour conserver et clôturer les quatre expériences déjà documentées : non.** Ne pas les relancer ; aucune donnée absente, notamment WP07, ne doit être reconstruite ou présentée comme mesurée.
- **Pour affirmer que le chantier WP12-A complet est terminé : pas encore décidé par les critères seuls.** Une nouvelle campagne n’est pas automatiquement nécessaire : la matrice permet une disposition bornée et des statuts négatifs/inconclusifs conservés. Toutefois, les contrôles de projection WP04 après modification et le plein ordre Newmark ne sont pas démontrés par ces quatre cas. Si l’Owner exige la continuité de non-régression sur le candidat release, une ou plusieurs exécutions nouvelles et ciblées seront nécessaires, sous identités/manifestes/décisions distincts.
- **Pour une qualification physique générale : oui, des preuves supplémentaires seraient nécessaires**, notamment une référence externe ou expérimentale correctement appariée, des cas multi-DDL, plusieurs familles/conditions aux limites, amortissement et excitation étendus. Ce niveau dépasse le besoin de clôturer documentairement les quatre expériences et ne doit pas être ajouté comme gate autonome WP12-E avant 0.2.12 sans décision de gouvernance.

La prochaine action la plus utile n’est pas un rerun des quatre PASS : c’est une décision Owner qui confirme si WP12-A est limité aux quatre expériences de la décision #65 ou couvre encore l’ensemble du chantier roadmap. Si la portée complète est retenue, traiter d’abord `AN-MODAL`/`AN-MODAL-BASIS` post-projection, puis `AN-DIRECT-TRANSIENT` et les contrôles de dispatch/IO dynamiques indispensables aux revendications. Les contrôles MPC/RBE peuvent rester non-bloquants si la route dynamique est explicitement exclue ou refusée ; ne pas les présenter comme pris en charge.

## Limites conservées

1. Les quatre runs utilisent des identités de source scientifique différentes (`630d22b…`, `5f96dd6…`, `bf88803…`, `7406e34…`) et des contrôleurs différents. Ils sont authentiquement liés à leurs preuves respectives, mais ne forment pas une exécution commune sur le HEAD release courant `baf4dc335d61e9a7b6d9289edd280bbb224d84b9`.
2. Le Newmark PASS porte sur un BEAM2 SDOF libre/non amorti ; son résidu est réduit/modal. Le travail extérieur n’est pas une mesure du sidecar pour ce cas.
3. L’harmonique réduit montre qu’un résidu modal nul peut coexister avec un résidu physique `1 N` sur la base tronquée. Aucune borne générale de troncature n’est acquise.
4. L’excitation de base complexe couvre un axe et un DDL libre, incluant DC et des fréquences proches du premier mode ; ce n’est pas une étude de plusieurs supports ou de structures variées.
5. WP07 harmonique est PASS, mais `K`, `M`, réponses et erreurs brutes sont `NOT_EXPOSED`.
6. Deux `PYTEST_FAILED` Newmark demeurent dans l’historique. Le run writer `dev-301ba3b31a43` a consommé une tentative avec verdict mécanique non établi.
7. Les hashes confirment les octets des artefacts locaux contrôlés ; ils ne rendent pas le stockage immuable et ne constituent pas une signature cryptographique.

## Décisions qui restent à prendre

1. **Portée WP12-A :** accepter le libellé `WP12A_FOUR_EXPERIMENTS_DOCUMENTARY_CLOSED` comme la fermeture complète du seul sous-périmètre de quatre expériences, ou maintenir le chantier interne WP12-A complet en cours.
2. **Si scope complet :** approuver une disposition des MUST/PARTIAL/INCONCLUSIVE/NOT_TESTED de la matrice (avec exclusions explicites) et décider si les contrôles post-projection et plein ordre doivent être exécutés sur une identité release gelée.
3. **Release :** décisions indépendantes WP12-F et WP13. Aucun verdict de release, merge supplémentaire ou publication n’est produit par ces documents.

Cette recommandation ne modifie ni les statuts historiques ni leurs critères, ne clôt pas WP12/WP13 et ne qualifie pas globalement QF Solver.
