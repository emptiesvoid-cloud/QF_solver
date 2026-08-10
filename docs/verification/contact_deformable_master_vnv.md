---
doc_id: DOC-VNV-CONTACT-DEFORMABLE-MASTER-003
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# V&V contact avec maitre elastique

## Objet

`VNV-CONTACT-DEFORMABLE-MASTER-003` verifie que le gap normal integre le
deplacement barycentrique des trois noeuds maitres. Le triangle maitre est
porte par trois ressorts isotropes de `600 N/m`; l'esclave est porte par un
ressort de `1000 N/m`, place a `0.1 m` au-dessus de la face et charge par
`200 N` suivant la normale.

Les poids barycentriques de la projection sont `[0.5, 0.25, 0.25]`. Le gap
ferme est donc :

$$
g = g_0 + u_s - \sum_i b_i u_i = 0.
$$

La pression analytique est obtenue avec la compliance serie :

$$
p = \frac{F/k_s-g_0}{1/k_s+\sum_i b_i^2/k_m}.
$$

Elle vaut `61.5384615385 N`. La campagne exige un gap sous `1e-12 m`, un
ecart de pression sous `1e-10 N` et les deplacements esclave/maitres sous
`1e-12 m` de la solution fermee.

## Interpretation

Le resultat prouve l'assemblage du terme de contact sur les noeuds maitres
mobiles et la repartition barycentrique de la force. Il ne prouve pas une
surface EF deformable generalisee : la face n'a ni element de coque/solide,
ni recherche geometrique mise a jour, ni changement de normale. La maturite
reste donc `experimental`.

```powershell
python .\qf_solver.py verify-contact --output .\results\VNV-CONTACT-V1
```

Le sous-dossier `elastic_master` contient `summary.json`, `report.md` et le
manifeste SHA-256 de l'etude.
