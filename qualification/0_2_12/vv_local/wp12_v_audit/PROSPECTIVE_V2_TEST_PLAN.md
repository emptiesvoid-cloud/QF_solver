# WP12-V2 — Expérience minimale proposée

**État :** PROPOSED_NOT_AUTHORIZED. **Exécution :** NOT_RUN. **WP12 :** OPEN.

Ce document propose une seule expérience prospective, si l'Owner souhaite lever les limites laissées par les archives U3. Aucun nouveau test exécutable, manifeste figé ou décision Owner n'est créé ici. U3 n'est ni modifié ni relancé.

## Pourquoi une expérience supplémentaire peut être utile

L'archive suffit à identifier le critère exact non garanti et à quantifier la dissymétrie, les écarts de matrices, les deux solutions et leurs résidus. Elle ne conserve pas les contributions flottantes individuelles des douze éléments ni leur réduction effective; elle ne conserve pas non plus toutes les colonnes de l'opérateur matrix-free. Trois vecteurs de comparaison et un seul chargement ne démontrent pas l'équivalence complète des opérateurs.

La nouvelle expérience ne servirait donc pas à effacer le FAIL. Elle fournirait les données manquantes pour (a) tester une borne d'arrondi définie avant observation, (b) localiser le bit produit par la réduction et (c) vérifier tout le bloc libre et les contrôles que pytest n'a pas atteints dans U3. Aucun raffinement H2/H3, changement de chargement ou benchmark n'est requis pour cette question étroite.

## Identité proposée et gel préalable

Identifiant proposé : TET4-H1-OPERATOR-AUDIT-002. Le futur nodeid doit être une fonction unique nouvelle, définie, relue et hashée avant autorisation; le nom proposé n'est pas un nodeid déjà présent.

| Entrée | Exigence avant lancement |
|---|---|
| Modèle H1 | Même fichier, SHA-256 `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`, 12 TET4/12 nœuds/36 DDL |
| Science | Commit `00428adf38e9397340ac136f6f503a268eb671da` et tree `df4ec667bf746b042c900fad1f86bf542e1a437b` inchangés |
| Tests / instrumentation | Nouvelle identité distincte; lecture seule des sources gelées, pas de monkeypatch de leurs calculs |
| Runner | Identité exacte à geler; ne pas hériter silencieusement de l'autorisation U |
| Environnement | Python/packages/import/threads relevés et approuvés dans le nouveau manifeste |
| Critères | Règles de [NUMERICAL_CRITERION_PROPOSAL.md](NUMERICAL_CRITERION_PROPOSAL.md) relues et approuvées, plus oracles/critères U conservés explicitement |
| Destination | Nouveau namespace exclusif, distinct de WP12-U; chemin final à approuver |
| Budget | Une tentative et 300 s proposés, PROPOSED_OWNER_APPROVAL_REQUIRED; aucune reprise automatique |
| Ressources | Journaux 16 MiB/flux proposés sous contrôle logiciel; limites locales réacceptées ou isolation effective à documenter dans la décision |

La décision doit lier le SHA-256 final du nouveau manifeste, le nodeid réel, toutes les identités, les entrées, l'environnement, les critères, la tentative et la destination. Le manifeste U et ses décisions ne s'appliquent pas à V2.

## Observations minimales à capturer

1. Charger exactement la fixture H1; vérifier unités, E/ν, coordonnées, connectivité, DDL, force, contraintes et toutes les empreintes.
2. Avant agrégation, conserver les douze matrices élémentaires binary64 du kernel batch et leurs équivalents scalaires, les cartes de DDL, l'ordre d'émission COO et les contributions affectant chaque paire. La paire (14,22)/(22,14) doit conserver les éléments 0, 8 et 9 et leurs mots binary64.
3. Capturer les matrices globales batch et scalaire 36×36 et la référence rationnelle; conserver à la fois les entrées fractionnaires et binary64. Enregistrer chaque somme absolue S et un majorant du nombre d'additions, par paire. Documenter SciPy/version/réduction et toute instrumentation : sa propre réduction ne doit pas se substituer silencieusement à celle de production.
4. Pour le bloc libre 24×24, appliquer l'opérateur matrix-free aux 24 vecteurs canoniques, avec le même mapping et les mêmes contraintes. Ce contrôle identifie toutes les colonnes du bloc linéaire effectivement résolu; il ne prétend pas couvrir les DDL contraints ou d'autres modèles. Le résultat par colonne doit rester traité comme une évaluation flottante, comparée à l'oracle avec un budget d'arrondi justifié pour local-matvec/scatter.
5. Réemployer les trois vecteurs déterministes et les deux champs de solution U3 comme entrées archivées vérifiées, puis recalculer les résidus/critères sur les opérateurs capturés. Réexaminer les contrôles force/moment/énergie et les assertions non atteintes dans U3. Les deux résolutions linéaires n'ont pas à être relancées pour cette question; tout rejeu de solve doit être motivé et ajouté explicitement au futur manifeste, pas inclus par défaut.
6. Produire un enregistrement structuré de chaque contrôle, y compris ceux qui échouent, avant l'assertion finale agrégée. Cela évite que l'arrêt de pytest rende invisibles les autres observations; cela ne permet pas de changer un FAIL en PASS.

Il n'est pas nécessaire d'appeler une seconde fois le kernel pour identifier l'ordre de la réduction : le test peut capturer les entrées réellement remises au constructeur sparse puis examiner cette réduction sous le profil SciPy identifié. Si l'instrumentation modifie l'ordre ou le chemin de production, le rapport doit le déclarer et la preuve causale rester INCONCLUSIVE.

## Critères prospectifs

- Structure : mêmes ensembles de contributions des deux orientations; mappage, multiplicité, unités, fixtures et contraintes vérifiés, pas de NaN/Inf ni d'hypothèse arithmétique non satisfaite.
- Symétrie locale : égalité miroir des valeurs locales là où le kernel la construit explicitement.
- Symétrie globale : borne composante par composante fondée sur L et les sommes absolues S, avec γ pour la réduction documentée. Une borne impossible à évaluer produit INCONCLUSIVE, pas un atol de secours. L'ordre précis n'est pas nécessaire à la borne worst-case; il l'est pour attribuer le résultat exact d'un ULP.
- Exactitude des valeurs : comparaison séparée des matrices/produits à l'oracle rationnel; une matrice parfaitement symétrique peut néanmoins être fausse. Le budget de chaque opération doit être dérivé et gelé; ne pas recopier un multiplicateur arbitraire de epsilon.
- Résolution : reprendre explicitement les critères gelés de résidus et la borne de différence de solution issue de l'inverse/résidu exact de U3. Les dénominateurs et unités doivent être enregistrés, sans modification après observation.
- Mécanique : réactions/bilans et identité 2U−W = u_freeᵀr_free; les identités seules ne démontrent ni petit résidu ni précision du continuum.
- Sortie : tous les contrôles requis doivent être évalués et réussir pour le résultat prospectif du nouveau cas. Toute failure conserve son archive; U3 conserve toujours son FAIL historique.

## Contrôles négatifs

Les contrôles du prédicat doivent utiliser des copies synthétiques des données capturées, sans modifier la résolution physique ni ses sources : contribution miroir perturbée au-delà de la borne; paire near-zero avec cancellation; indice/DDL déplacé ou contribution omise; matrice fausse mais exactement symétrique; NaN/Inf; hypothèse du modèle d'arrondi indisponible. Une mise à l'échelle par puissance de deux doit faire varier la borne avec S. Ces contrôles testent le prédicat et sa sensibilité, pas la mécanique du solveur.

## Sortie et décision

Si le nouveau contrôle accepte l'assemblage sous sa borne et que toutes les colonnes libres, solutions et bilans concordent avec leurs oracles, il pourra établir une non-régression bornée H1. Il ne résoudra pas l'écart de 66,69 % au diagnostic poutre sur H3 et n'accordera aucune qualification générale TET4. Un écart de colonne, un dépassement de borne ou un défaut de mapping orientera une investigation de production distincte; aucune correction automatique du solveur n'est proposée.

La prochaine action est une revue Owner de ce protocole et des critères, suivie seulement si approuvée de l'implémentation, du gel du nouveau manifeste et d'une décision d'exécution distincte. Aucune action WP12-V2 n'est engagée par ce rapport.
