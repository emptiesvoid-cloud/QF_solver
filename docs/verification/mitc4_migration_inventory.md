---
doc_id: DOC-ARCH-MITC4-MIGRATION-001
revision: 0.2
status: controlled
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Inventaire de migration MITC4

## Objet

Ce document prepare le rapatriement progressif du noyau historique `mitc4`
dans l'arborescence canonique `solveur.elements.shell`. Il ne modifie ni la
formulation MITC4, ni ses resultats mecaniques, ni les interfaces de
compatibilite de la serie `0.2.x`.

## Etat de migration controle

| Zone | Localisation actuelle | Responsabilite |
| --- | --- | --- |
| Formulation | `src/solveur/elements/shell/mitc4/element.py` | MITC4, Q4 temoin, matrices, masse et drilling |
| Conventions elementaires | `src/solveur/elements/shell/mitc4/constants.py`, `geometry.py`, `material.py` | DDL, reperes, materiau isotrope coque |
| Maillage et modele | `src/solveur/elements/shell/mitc4/mesh.py`, `model.py` | maillage quadrangulaire et assemblage de coque |
| V&V et benchmarks | `src/solveur/verification/mitc4_benchmarks.py`, `mitc4_locking.py`, `mitc4_convergence.py`, `mitc4_mechanical.py` | patchs, locking, Cook, Scordelis et cylindre pince |
| Visualisation | `src/solveur/post/mitc4_visualization.py` | figures de maillage et deforme |
| CLI specialisee | `src/solveur/compat/mitc4/cli.py` | compatibilite de `mitc4-solver` |
| Adaptateur commun | `src/solveur/elements/shell/mitc4/adapter.py` | integration du MITC4 dans le registre general |

Les dependants directs incluent le registre d'elements, la validation de
maillage, les chargements, le post-traitement, les analyses dynamique et
harmonique, les campagnes V&V, les scripts et les tests de packaging.

## Cible d'architecture

```text
src/solveur/
  elements/
    shell/
      mitc4/
        __init__.py
        element.py
        geometry.py
        constants.py
        material.py
  materials/
    shell.py              # facade materiau publique, si necessaire
  verification/
    mitc4_*.py            # campagnes et oracles, separes de la formulation
  cli/
    ...                   # commandes generales et compatibilite
src/solveur/compat/mitc4/
  ...                     # facades deprecation 0.2.x seulement
```

La migration couvre maintenant le noyau de formulation, le maillage, le modele,
la visualisation et les helpers de verification. Les anciens modules restent
des facades minces qui reexportent les objets canoniques. Aucun calcul MITC4
ne doit etre reimplemente dans `src/solveur/compat/mitc4/`.

## Contrat de compatibilite

Pendant `0.2.x` :

- `import mitc4` et ses sous-modules restent utilisables ;
- la commande `mitc4-solver` reste disponible ;
- les nouveaux imports internes utilisent progressivement
  `solveur.elements.shell.mitc4` ;
- les resultats sont compares a
  `qualification/baselines/mitc4_migration_baseline_2026-08-14.json` ;
- une suppression du paquet de compatibilite exige une release majeure et une
  note de migration publique.

## Baseline de migration

La baseline enregistree le `2026-08-14` couvre une facette MITC4 non plane,
sa matrice de rigidite, sa masse coherente et la verification mecanique rapide.
Apres migration, la baseline locale de `64` tests est passee, puis la campagne
MITC4 elargie a valide `107` tests avec `12` exclusions explicites pour des
dependances ou campagnes non actives. `python -m solveur.compat.mitc4.cli verify --quick`
reste `PASS`. La commande specialisee ecrit un avis de depreciation sur
`stderr`; elle reste fonctionnelle pendant toute la serie `0.2.x`.

## Exclusions de cette migration

- aucune modification de formulation, quadrature, tying, drilling ou masse ;
- aucune promotion de maturite mecanique ;
- aucune modification de format JSON, API publique ou contrat CLI ;
- aucun retrait du package `mitc4` avant la fin annoncee de sa compatibilite.
