---
doc_id: DOC-VNV-026-G07-OWNER-001
revision: 0.1
status: owner_closeout
applicable_version: 0.2.6a0
gate: 026-G07
closeout_start_sha: c55f768d570905869904e08042180f2b515f26c4
---

# 026-G07 — Owner disposition and conditional closeout

## Décision

L’Owner clôt `026-G07` comme **PASS_WITH_LIMITATIONS** dans un périmètre
explicitement borné. La décision est enregistrée dans
[`g07_owner_closeout.json`](../../../qualification/0_2_6/g07_owner_closeout.json).

Les preuves ne promeuvent pas toutes les familles ni tous les chemins
nonlinéaires. Elles autorisent uniquement les claims détaillés ci-dessous ; une
absence de comparaison ou une limitation de route reste une exclusion explicite,
jamais un PASS implicite.

| Capability / family | Owner status | Disposition |
| --- | --- | --- |
| TL TET4 | `OWNER_PASS_WITH_LIMITATIONS` | Corrélation externe bornée, 16/16 points, déplacements/réactions concordants ; contraintes de mesure pour les contraintes/déformations |
| TL HEX8 | `OWNER_NOT_QUALIFIED` | L’histoire QF s’arrête déterministiquement à `lambda = 0.375` malgré les subdivisions et cutbacks existants |
| Arc-Length global | `OWNER_PASS_WITH_LIMITATIONS` | Preuve de recherche interne bornée sur le benchmark TET4 ; aucune qualification de production |
| ARC-002 refined mesh | `OWNER_DEFERRED` | Pas de turning point comparable dans la fenêtre raffinée ; probe plus fin arrêté sur `det(F) < 0` |
| ARC-003 restart/rollback | `OWNER_APPROVED_BOUNDED` | Reprise, rollback et déterminisme démontrés sur le cas déclaré |

## Périmètre qualifié

Le périmètre G07 fermé est limité à :

- l’élasticité Total-Lagrangian existante sur `TET4`, dans le domaine fini,
  positif en `det(F)` et couvert par les preuves internes et B2/B3 ;
- la corrélation Code_Aster compatible sur les 16 points TET4 déclarés, pour les
  déplacements et réactions ;
- le benchmark Arc-Length TET4 coarse déclaré, avec suivi de branche,
  turning-point et restart/rollback bornés au corpus existant.

Il ne s’agit pas d’une qualification générale TL/Arc-Length, d’une garantie
industrielle ou d’une qualification de toutes les combinaisons éléments,
matériaux, maillages, chargements et contrôles.

## Exclusions et gaps acceptés

`TL HEX8 complete-history` est `OWNER_NOT_QUALIFIED`, non `PASS` : la
limitation algorithmique est conservée telle quelle et aucune corrélation
complète n’est revendiquée. `ARC-002` reste `OWNER_DEFERRED` : la preuve coarse
reste utile mais la comparabilité refined n’est pas déclarée satisfaite.

Ces deux points ne bloquent pas le périmètre TET4 borné retenu : aucun bug réel,
aucune corruption d’état, aucune valeur non finie et aucune revendication
publique ambiguë n’a été observée. Les exigences hors périmètre sont listées
dans l’artefact machine-readable et devront faire l’objet d’une nouvelle preuve
et d’une nouvelle revue Owner avant toute extension.

## Régression de clôture

La commande complète unique exécutée pour cette décision était exactement
`python -m pytest -q` sur le SHA de départ propre `c55f768d570905869904e08042180f2b515f26c4` :

| Résultat | Valeur |
| --- | ---: |
| Passed | 1876 |
| Skipped | 184 |
| Failed | 2 |
| `NEW_FIX_ONLY_FAILURES` | 0 |

Les deux failures sont préexistantes à ce closeout et hors comportement
fonctionnel G07 :

1. la règle de taille de source signale le runner B1 existant
   `scripts/run_g07_b1_arc_length.py` à 762 lignes ;
2. l’audit documentaire contrôlé conserve un décompte 456 alors que l’arbre
   courant pré-closeout en compte 460.

Elles restent des blockers de release globaux séparés ; aucune correction n’a
été introduite dans cette revue.

## Gouvernance

Le contrat G07 et le manifeste global des gates n’ont pas été modifiés. Ce
closeout local enregistre la décision Owner et laisse la consolidation globale
à l’intégration multi-agent. Aucun code fonctionnel, formulation, tangent,
Newton, politique de cutback ou route TL/Arc-Length n’a été changé.
