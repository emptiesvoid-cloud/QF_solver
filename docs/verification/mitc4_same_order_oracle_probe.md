# MITC4 multicouche courbe - sonde oracle de meme ordre

**Document** : `VNV-COMP-CURVED-S4-SAME-ORDER-009`  
**Date** : 2026-08-21  
**Statut** : `NOT_APPLICABLE_EXTERNAL_BACKEND`

## Objet

La campagne MITC4 multicouche courbe reste a `2,043415 %` face a CalculiX
`S8R COMPOSITE` apres six niveaux de maillage. Comme le S8R est quadratique et
geometriquement courbe, une sonde a quatre noeuds a ete tentee afin de separer
la difference de formulation de la difference de geometrie.

## Resultat

CalculiX 2.20 refuse une carte `*SHELL SECTION,COMPOSITE` avec un element `S4`
et indique que l'option composite est disponible pour `S8R` ou `S6`. Le calcul
n'a donc produit ni deplacement ni comparaison exploitable.

Cette sonde est une **preuve negative** : elle ne justifie aucune promotion et
n'est pas comptee comme correlation externe. Le seuil `STABLE-1PCT-POLICY`
reste obligatoire.

## Consequence V&V

Le scope `mitc4-laminate-static` reste `accepted_for_bounded_engineering_use`.
Pour viser `stable`, il faut encore obtenir au moins une des preuves suivantes :

1. une reference analytique de coque courbe multicouche avec observable de
   deplacement defini hors singularite ;
2. un oracle externe composite compatible avec une formulation lineaire a quatre
   noeuds ;
3. une justification mecanique formelle de l'ecart de modele, accompagnee d'une
   decision Owner explicitement datee. Cette voie ne leve pas automatiquement la
   regle d'erreur a `1 %`.

**Artefact brut** : `qualification/vnv/external/calculix_curved_s4_same_order/reference/s4_composite_probe.log`.
