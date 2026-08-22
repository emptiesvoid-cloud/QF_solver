---

doc_id: DOC-OWNER-BEAM2-DISCRETE-DYN-STABLE-001
revision: 0.1
status: ready_for_owner_review
review_mode: owner_review
promotion_target: stable
scope: beam2-linear-dynamics, discrete-linear-dynamics
date: 2026-08-21
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner review — BEAM2 et système discret, dynamique linéaire

Ce dossier prépare une promotion vers `stable` pour deux périmètres séparés.
La décision n'est pas automatique. Les limites et exclusions restent attachées
à chaque scope; cette revue ne couvre ni dynamique non linéaire, ni contact,
ni amortissement non proportionnel.

## 1. BEAM2 dynamique linéaire

Le cas interne est une poutre droite linéaire avec masse cohérente, modal,
Newmark et réponse harmonique. La corrélation externe utilise Code_Aster
18.1.0, image épinglée par digest, sur le même maillage et les mêmes grilles
temporelle et fréquentielle.

| Observable | QF_solver / résultat | Référence ou limite | Statut |
| --- | ---: | ---: | --- |
| Résidu modal maximal | `1,175e-12` | `1e-8` | PASS |
| Erreur orthogonalité masse | `8,187e-17` | `1e-8` | PASS |
| Erreur orthogonalité raideur | `5,506e-14` | `1e-8` | PASS |
| Erreur RMS Newmark | `0,01437 %` | `1 %` | PASS |
| Dérive énergétique Newmark | `2,363e-13` | `1e-4` | PASS |
| Incrément temporel final | `0,47210 %` | `1 %` | PASS |
| Erreur modale Code_Aster maximale | `0,02649 %` | `1 %` | PASS |
| Erreur de corrélation transitoire Code_Aster | conforme | même grille | PASS |
| Erreur harmonique à 0 Hz | `0` | `1e-8` | PASS |

### Domaine proposé

Poutres BEAM2 droites, linéaires, petits déplacements, masse cohérente,
modalité sans amortissement calibré, intégration Newmark moyenne accélération
(`beta=0,25`, `gamma=0,5`) et harmonique linéaire. Les poutres épaisses,
grandes rotations, non-linéarités, amortissement non proportionnel et contact
restent exclus.

## 2. Système discret linéaire

Le cas est un oscillateur masse-ressort translationnel à un degré de liberté,
avec `k=1000 N/m`, `m=10 kg` et charge `25 N`. Il est comparé à la solution
fermée et à Code_Aster `DIS_T`.

| Observable | Résultat | Référence ou limite | Statut |
| --- | ---: | ---: | --- |
| Fréquence propre | `1,59154943 Hz` | analytique | PASS |
| Résidu modal | `1,798e-16` | `1e-8` | PASS |
| Erreur RMS Newmark | `0,01437 %` | `1 %` | PASS |
| Dérive énergétique | `3,800e-13` | `1e-4` | PASS |
| Incrément temporel final | `0,47210 %` | `1 %` | PASS |
| Erreur harmonique à 0 Hz | `0` | `1e-8` | PASS |
| Corrélation Code_Aster | PASS externe | même cas | PASS |

### Domaine proposé

Systèmes discrets linéaires SDOF translationnels, raideur et masse constantes,
sans amortissement calibré, sans non-linéarité et sans extrapolation aux
systèmes multi-DDL couplés.

## Questions Owner

### Q1 — Couverture BEAM2

Les preuves modales, Newmark, harmoniques et Code_Aster couvrent-elles le
domaine BEAM2 droit, linéaire et borné décrit ci-dessus ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q2 — Couverture discret

Le cas analytique et la corrélation Code_Aster suffisent-ils pour le périmètre
SDOF translationnel déclaré, sans extrapolation aux systèmes multi-DDL ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q3 — Critères numériques

Les résidus, orthogonalités, dérives énergétiques et erreurs principales
inférieures ou égales à `1 %` sont-ils acceptables pour une promotion stable
dans ces périmètres stricts ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q4 — Exclusions

Les exclusions concernant grandes rotations, non-linéarité, amortissement non
proportionnel, contact et systèmes multi-DDL sont-elles suffisamment explicites
et acceptables ?

Réponse : `OUI / NON / PARTIELLEMENT`

### Q5 — Décision

Décision proposée séparément pour `beam2-linear-dynamics` et
`discrete-linear-dynamics` : `stable / accepted_with_recommendations /
accepted_for_bounded_engineering_use / more_evidence_required`.

Décision BEAM2 :

Décision discret :

Signature Owner :

Date :

## Traçabilité

- Résultats analytiques : `qualification/vnv/linear_dynamic_families/beam2/summary.json`
  et `qualification/vnv/linear_dynamic_families/spring_mass/summary.json`.
- Corrélations externes : `qualification/vnv/external/code_aster_beam2_transverse/reference/summary.json`
  et `qualification/vnv/external/code_aster_discrete/reference/summary.json`.
- Registre de fermeture : `qualification/reviews/linear_dynamic_closure_register.json`.
- PDF dynamique : `output/pdf/owner_review_dynamique_lineaire.pdf`.

Une réponse Owner favorable ne modifie la matrice de maturité qu'après
enregistrement d'une décision datée et relance du gate `maturity-promotion`.
