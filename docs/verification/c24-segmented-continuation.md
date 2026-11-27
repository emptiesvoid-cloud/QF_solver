# Continuation segmentée expérimentale de Newton TET10

Sur la route publique de statique géométrique TET10 à pas fixes, sans contact,
`experimental_newton_exact_residual=true` reste une option explicite. Le budget
`experimental_newton_exact_residual_max_checks` vaut huit par défaut et accepte
un entier de 1 à 48 avec cette option. Le garde linéaire historique est évalué
en premier. Son verdict et le résultat complémentaire restent distincts.
Un résultat absent, non concluant ou invalide ne permet pas d’appliquer la
correction. Le contrôle exact requiert la dépendance optionnelle `psutil`,
fournie par l’extra existant `eas-diagnostic`.

Pour arrêter un appel à une frontière acceptée, fournir
`experimental_pause_after_accepted_increments` et un `checkpoint_path`
NPZ, avec `checkpoint_interval=1` et `checkpoint_keep_steps=true`. Le nombre
d’incréments à accepter dans l’appel doit être un entier positif et rester
dans la portion restante du chemin. L’option nécessite le contrôle exact
expérimental et est limitée à cette route. Le solveur écrit l’état accepté
avec son facteur global, sa signature de modèle et ses empreintes.

Pour reprendre, transmettre le checkpoint via `restart_from` et conserver
les charges **absolues de la cible complète**, le nombre total
`load_increments`, la géométrie, les appuis, les matériaux et les paramètres
de calcul liés à la signature. Le premier facteur repris est celui de
l’incrément global suivant. Une pause retourne `status="PAUSED"` et
`solver["converged"]=False` avec les champs de départ et d’arrivée du
segment. À la cible complète, le résultat retourne `status="success"` et
`solver["continuation_status"]="CONVERGED"`.

Le compteur exact du solveur est propre à un **appel Newton**. Un nouvel
appel, y compris après reprise, crée un nouveau compteur. Un plafond sur
plusieurs appels requiert un contrôleur externe qui réserve et consigne
les contrôles de chaque appel. Le contrôleur de campagne C24, ses scopes,
ses ledgers et ses captures restent des instruments de recherche.

## Preuve et portée

La campagne C24 a exercé le solveur avec l’instrumentation `aaeb0578`
et le contrôleur `1d558ea7`. Elle a couvert 192 incréments et 16 segments
jusqu’à `p = 0,05`, avec 576 contrôles exacts exécutés, dont 72 pendant
le pilote. Les pauses intermédiaires et la convergence terminale ont des
statuts distincts. Le bilan final a été réévalué avec le même opérateur
produit et la comparaison à l’élastique J33 est descriptive. Ce résultat
porte sur le témoin et le chemin figés. La stabilité générale et l’atteinte
de `p = 1,5` restent ouvertes. Les tests synthétiques du port exercent
la route publique et la reprise sans campagne FEM.
