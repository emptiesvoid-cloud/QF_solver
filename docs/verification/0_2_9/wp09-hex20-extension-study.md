# WP09 — étude d’extension HEX20

## Verdict

`HEX20_EXTENSION_DIAGNOSTIC_ONLY_NOT_FORMALLY_QUALIFIED`

L’extension HEX20 fonctionne dans une fenêtre de charge plus faible, mais elle
ne satisfait pas le contrat initial WP09 à charge finale `0,25` et sa
convergence de maillage n’est pas suffisante dans la fenêtre diagnostique
`0,20`. Aucun point officiel WP09 n’est ajouté et la validation HEX8 `8/8`
reste inchangée.

## Provenance

| Champ | Valeur |
|---|---|
| Branche | `codex/wp09-hex20-extension` |
| Base autorisée | `3e4f79161c0484563387a55d3de9c19c5389f9b3` |
| Exécution initiale | `681b1e131143e54c960e96aa0020f99144aca558` |
| Diagnostic charge 0,20 | `69b082d3330e76b14d850035535d97537f2de86b` |
| Tête locale après correctifs outillage | `1e0d4f58ee7dcc1bb512a7d2540e8ad452b208d5` |
| Contrat SHA-256 | `8a694acbab56c711c6b9961e57efb0fce4841b847e2dc7cf9ee28ee7f02eb0c9` |
| Policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Push / merge | non effectués |

La mécanique de production, les seuils et la validation HEX8 n’ont pas été
modifiés.

## Contrat initial — charge finale 0,25

| Niveau | Éléments | Nœuds | DDL | Statut | Observation |
|---|---:|---:|---:|---|---|
| H1 | 1 | 20 | 60 | PASS | `max ||U-I||F = 0,04202` |
| H2 | 2 | 32 | 96 | FAIL_CLOSED | `0,0508986 > 0,05` |
| H3 | 3 | 44 | 132 | non exécuté | dépendance H2 échouée |

H1 atteint 4/4 incréments, sans rejet ni fallback. H2 échoue sur la borne
locale corotationnelle pendant une itération d’essai. Les essais à 8 et 16
incréments reproduisent le même dépassement (`0,0508994` et `0,0508823`) :
le simple sous-incrémentage ne résout pas la cause.

## Sensibilité — charge finale 0,20

Cette campagne est une expérience séparée ; elle ne rebinde pas le contrat
initial.

| Niveau | Nœuds | DDL | Statut | max `||U-I||F` |
|---|---:|---:|---|---:|
| H1 | 20 | 60 | PASS | `0,0330084` |
| H2 | 32 | 96 | PASS | `0,0403291` |
| H3 | 44 | 132 | PASS | `0,0474037` |

Les équilibres et `det(F)` restent propres. Toutefois, H2→H3 donne :

- déplacement : `10,8736 %` — seuil `5 %`, échec ;
- énergie : `8,7672 %` — seuil `5 %`, échec ;
- réaction : `≈ 0 %` — passe ;
- von Mises : `3,7628 %` — passe.

La fenêtre `0,20` est donc numériquement exploitable comme résultat
expérimental borné, mais elle ne constitue pas encore une convergence de
maillage formelle.

## Référence et replay

La recomputation indépendante H1 revalidée passe avec des écarts nuls sur les
observables sérialisées. Elle reste une recomputation d’observables à partir
des données brutes, pas un second solve global FEM/Newton. Le dossier initial
reste `FAIL_CLOSED` au niveau H2 et aucun replay complet H1→H3 n’est revendiqué.

## Conclusion et suite possible

La cause immédiate est la combinaison du chemin HEX20 raffiné et de la borne
corotationnelle `0,05` à la charge `0,25`; augmenter le nombre d’incréments ne
suffit pas. Une suite légitime serait un nouveau contrat HEX20 prospectif,
explicitement borné à une charge plus faible, avec une hiérarchie plus riche et
un gate de maillage satisfaisant. Il ne faut ni modifier rétroactivement le
contrat R1, ni attribuer de points WP09 sur cette étude.

`WP09 HEX8 = 8/8 officiel inchangé`  
`WP09 HEX20 = 0 / extension en attente de revue Owner`  
`FULL_TEST_SUITE = NOT_RUN`
