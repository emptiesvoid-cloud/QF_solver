# Niveaux de detail des audits

Les audits blancs du solveur exposent trois niveaux explicites. Le niveau
choisi ne modifie ni l'assemblage, ni la resolution, ni les resultats
numeriques : il controle uniquement la representation de l'audit et de son
export Markdown.

## API Python

```python
from solveur.api import inspect_model, save_audit_markdown

audit = inspect_model(model, detail="diagnostic")
save_audit_markdown(audit, "audit.md", detail="diagnostic")
```

| Niveau | Usage | Contenu |
| --- | --- | --- |
| `summary` | lecture humaine par defaut | synthese, compteurs PASS/WARNING/FAIL, maillage/DDL/materiaux, matrices globales, equilibre, tous les WARNING/FAIL ; les PASS elementaires sont omis |
| `diagnostic` | analyse recommandee | `summary` plus agregats min/max/moyenne, statistiques par type d'element, matrices, contraintes, resultats/stresses, residus et worst-N |
| `values` | debug/forensic | representation exhaustive historique, incluant DDL locaux, entrees d'assemblage, matrices et controles individuels |

Les objets internes restent reproductibles et les controles WARNING/FAIL ne
sont jamais supprimes par un export compact. En cas de modele invalide, le
detail demande est conserve dans l'audit partiel.

## Export Markdown et protection de taille

`save_audit_markdown()` accepte :

```python
save_audit_markdown(
    result_or_audit,
    "audit.md",
    detail="values",
    max_pass_rows=500,
    values_warning_rows=100_000,
)
```

`max_pass_rows` s'applique uniquement aux lignes PASS de l'export Markdown.
Les WARNING et FAIL restent toujours presents. L'objet `SolverAudit` en
memoire et son export JSON ne sont pas tronques.

Le mode `values` estime le volume de sortie avant rendu. Au-dessus de
`values_warning_rows` (100 000 par defaut), l'export ajoute un avertissement
explicite ; il n'y a pas de troncature silencieuse. La croissance est de
l'ordre de `O(N_elements x controles)` et peut donc produire des centaines de
milliers ou millions de lignes sur un grand maillage.

Le meme seuil est disponible sur `inspect_model(..., detail="values",
values_warning_rows=...)`. Dans ce cas l'estimation et l'avertissement sont
conserves dans `audit.diagnostic` et `audit.notes`; ils ne changent pas les
valeurs internes.

CLI equivalent :

```text
qf-solver inspect --input model.json --detail diagnostic --markdown audit.md
qf-solver inspect --input model.json --detail values \
  --max-pass-rows 500 --values-warning-rows 100000
```

## Exemple grand modele

Pour le cas de reference d'environ 60 000 TET4 et 36 663 DDL, l'ancien
`values` a produit un `result_audit.md` de plus de 2 millions de lignes et
environ 273 Mo. Le nouveau chemin recommande `diagnostic` : il conserve les
compteurs globaux, les deux warnings d'equilibre observes, les agregats de
qualite/matrices/resultats et les worst-N, sans materialiser le dump PASS par
element. Le mode `values` reste disponible pour reproduire le forensic et
emet désormais une alerte de taille avant l'ecriture.

Le gain exact de taille/temps depend de la distribution des post-resultats et
doit etre mesure sur le fichier de reference ; aucune valeur synthetique n'est
presentee comme une mesure de solveur.

Mesure de non-regression de l'export sur une forme synthetique de meme ordre
(`60 000` elements, `240 000` controles, `60 000` post-resultats, sans
resolution) :

| Export | Lignes | Taille | Temps de rendu |
| --- | ---: | ---: | ---: |
| `values` | 360 061 | 23,4 MB | 0,911 s |
| `diagnostic` | 84 | 1 550 octets | 0,002 s |
| `summary` | 54 | 1 029 octets | < 0,001 s |

Cette mesure valide la propriete de croissance de l'export, pas la performance
de l'assemblage FEM. Le chiffre historique de 273 Mo / plus de 2 millions de
lignes reste la reference avant modification pour le cas reel fourni.

## Seuils d'equilibre

Les seuils existants restent inchanges :

```text
relative_error <= 1e-10 : PASS
1e-10 < relative_error <= 1e-8 : WARNING
relative_error > 1e-8 : FAIL
```

Les erreurs de force et de moment sont deja normalisees par une echelle
relative `max(norm(externe), norm(reaction), 1)`. Cette normalisation retire
la dependance directe a l'unite et a l'amplitude du chargement ; elle ne
supprime toutefois pas l'effet de l'accumulation flottante et de l'ordre de
sommation sur les grands systemes. Ainsi, des valeurs de l'ordre de
`1.7e-10` et `1.2e-10` restent correctement classees WARNING dans le cas
60k TET4, sans etre transformees en PASS par le seul fait que le modele est
grand.

Une evolution vers un seuil dimensionnel ou dependante de `N` ne doit pas
etre appliquee sans campagne numerique comparative. Elle devrait comparer
des calculs de reference a plusieurs tailles, ordres d'assemblage et niveaux
de conditionnement, puis conserver un plancher absolu et une borne relative
fail-closed. Cette livraison ne modifie donc pas les criteres de qualification.
