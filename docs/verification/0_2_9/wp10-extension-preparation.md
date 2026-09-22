---
doc_id: DOC-029-WP10-EXT-PREPARATION
revision: 1.0
status: preparation-only
---

# WP10-EXT — extension par famille d’éléments

## Constat

La qualification WP10 actuelle est limitée à HEX8. Elle valide un couplage
corotationnel-J2 avec contact frictionless penalty à recherche initiale fixe,
mais ne couvre pas TET4, HEX20 ou TET10.

## Stratégie

Les extensions seront conduites séparément et ne modifieront pas les preuves
HEX8 déjà obtenues :

1. TET4 couplé comme première extension ;
2. HEX20 après validation de l’interface haut ordre ;
3. TET10 en dernier, avec contrôle spécifique de l’intégration et du coût.

Chaque famille devra fournir E1/E2/E3 : baseline sérielle, référence
indépendante et replay frais. Une famille qui échoue reste `FAIL_CLOSED` sans
retirer la validité bornée des autres familles.

## Périmètre conservé

- corotationnel-J2 borné ;
- contact frictionless penalty à recherche initiale fixe ;
- petit benchmark avant toute montée en taille ;
- aucune revendication générale, dynamique, frictionnelle ou MPI ;
- aucun changement rétroactif de WP10-HEX8.

## État

```text
WP10_HEX8 = DOSSIER SÉPARÉ, READY_FOR_OWNER_REVIEW
WP10_EXT = PREPARATION_ONLY
FIRST_TARGET = TET4
E1/E2/E3 = NOT_RUN
PRODUCTION_CHANGES = NOT_STARTED
MERGE/PUSH = NOT_PERFORMED
```
