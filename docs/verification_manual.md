---
doc_id: DOC-VV-005
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Manuel de verification du solveur souverain

Ce manuel decrit comment transformer un cas mecanique en preuve exploitable.
Une preuve acceptable doit etre reproductible, auditable et reliee a une
exigence de `docs/qualification_matrix.md`.

## Structure d'un cas de campagne

Chaque entree de `qualification/campaign.json` contient:

- `id`: identifiant stable du cas;
- `requirement`: exigence couverte, par exemple `REQ-SOL-001`;
- `input`: modele JSON a executer;
- `mode`: `solve` ou `check_mesh`;
- `profile`: profil de verification;
- `expected_status`: statut attendu;
- `replacement_candidate`: `true` seulement pour un cas autorise a remplacer
  un calcul externe dans le perimetre courant;
- `accepted_use`: usage industriel borne associe au cas;
- `checks`: criteres numeriques ou structurels obligatoires.

Exemple:

```json
{
  "id": "SOV-TET4-STATIC-001",
  "requirement": "REQ-SOL-001",
  "input": "../examples/tet4_static.json",
  "mode": "solve",
  "profile": "strict",
  "expected_status": "PASS",
  "checks": [
    {
      "path": "result.audit.equilibrium.free_relative_residual",
      "op": "less_equal",
      "expected": 1.0e-9
    }
  ]
}
```

## Operateurs disponibles

| Operateur | Usage |
| --- | --- |
| `exists` | La valeur doit etre presente et non nulle. |
| `equals` | Egalite exacte pour statuts, noms, types ou valeurs fixes. |
| `not_equals` | Difference exacte. |
| `less_equal` | Borne superieure numerique. |
| `greater_equal` | Borne inferieure numerique. |
| `between` | Valeur numerique dans `[min, max]`. |
| `abs_error` | Ecart absolu `abs(actual - expected) <= tolerance`. |
| `relative_error` | Ecart relatif a `expected`, avec `tolerance` obligatoire. |

Le champ `path` descend dans les dictionnaires et listes avec une notation a
points. Exemple: `result.solver.time_history.0.total_energy`.

Un critere peut aussi porter une reference:

```json
{
  "path": "result.max_displacement",
  "op": "relative_error",
  "reference_formula": "tet4_unit_uniaxial_ux_displacement",
  "tolerance": 1.0e-8,
  "reference_type": "analytic",
  "reference": "closed-form constrained unit TET4 uniaxial solution"
}
```

Les types de reference doivent rester explicites:

- `non_regression`: valeur figee par une version du solveur;
- `analytic`: solution analytique documentee;
- `equilibrium_closed_form`: reference deduite d'un equilibre global simple;
- `third_party`: correlation avec un logiciel externe;
- `experimental`: correlation avec mesure physique.

Le statut `non_regression` protege contre les regressions numeriques, mais ne
remplace pas une preuve analytique ou une correlation tiers.

Formules disponibles dans la campagne actuelle:

| Formule | Domaine | Portee |
| --- | --- | --- |
| `tet4_unit_uniaxial_ux_displacement` | TET4 statique | Tetraedre unite contraint, charge UX sur le noeud 1. |
| `tet4_unit_uniaxial_von_mises` | TET4 statique | Etat de contrainte ferme du meme cas. |
| `tet4_unit_first_shear_frequency_hz` | TET4 modal | Premiere frequence de cisaillement du tetraedre unite contraint. |
| `tet4_unit_sdof_free_vibration_initial_energy` | TET4 dynamique | Energie initiale fermee d'un oscillateur TET4 unite a un ddl. |
| `tet4_unit_sdof_free_vibration_frequency_hz` | TET4 dynamique | Frequence naturelle fermee du meme oscillateur 1 ddl. |
| `tet4_unit_sdof_harmonic_static_amplitude` | TET4 harmonique | Amplitude statique fermee du meme oscillateur 1 ddl. |
| `tet4_unit_sdof_harmonic_f1_amplitude` | TET4 harmonique | Amplitude harmonique fermee a la frequence d'index 1. |
| `tet4_unit_sdof_harmonic_f1_phase_degrees` | TET4 harmonique | Phase harmonique fermee a la frequence d'index 1. |
| `tet4_unit_sdof_harmonic_f2_amplitude` | TET4 harmonique | Amplitude harmonique fermee a la frequence d'index 2. |
| `tet4_unit_sdof_harmonic_f2_phase_degrees` | TET4 harmonique | Phase harmonique fermee a la frequence d'index 2. |
| `mitc4_edge_membrane_force_x` | MITC4 statique | Somme des charges UX du bord droit divisee par la longueur du bord. |

Ces formules refusent les modeles hors de leur domaine afin de ne pas donner
une fausse preuve.

Les references statiques TET4 sont implementees dans
`solveur/verification/analytical_references.py`. Cet oracle ne depend ni des
classes d'elements, ni de l'assembleur, ni des solveurs, ni de NumPy/SciPy. Il
calcule directement le module contraint $\lambda+2\mu$, le deplacement, les
contraintes et la charge volumique nodale coherente. Un test d'architecture
controle cette independance et des valeurs calculees a la main protegent les
signes en traction et compression.

## Verification des chargements repartis

Le cas `SOV-TET4-PRESSURE-001` protege `REQ-LOAD-001`. Pour le tetraedre unite
et une pression de `1000 Pa` sur la face opposee a l'origine, l'aire vaut
$\sqrt{3}/2$ et la normale sortante vaut
$(1,1,1)/\sqrt{3}$. La resultante compressive fermee est donc:

$$
\mathbf F=-pA\mathbf n=[-500,-500,-500]^T\ \mathrm{N}.
$$

Sa ligne d'action passe par l'origine, donc $\mathbf M_O=\mathbf0$. La
campagne compare les trois composantes et le moment a ces references
independantes de l'assemblage. Les tests unitaires completent cette preuve par
TET10, MITC4, forces volumiques, pesanteur, bases locales et rotation rigide.

Une nouvelle famille de charge ne doit pas entrer dans la campagne avant de
disposer au minimum de:

- sa definition d'unites et de signe;
- une resultante analytique;
- un premier moment analytique;
- un test de transformation de repere lorsqu'un repere local existe;
- un test de rejet de topologie ou parametre invalide;
- une trace dans `audit.load_assembly`.

## Regles d'acceptation

Un cas de campagne est `PASS` seulement si:

- le statut obtenu egale `expected_status`;
- tous les criteres `checks` sont `PASS`;
- les comparaisons a reference restent dans leur tolerance;
- les fichiers de preuve sont ecrits dans le dossier de sortie.

Une campagne est `PASS` seulement si tous ses cas sont `PASS`.

Pour les cas resolus, la campagne verifie aussi le dossier `evidence` genere:
chaque taille et SHA-256 declare dans `evidence_manifest.json` doit correspondre
au fichier produit. Une incoherence d'artefact rend le cas non passant.
Le resume publie `evidence_bundle_count`, `evidence_verified_count` et
`evidence_manifest_schema_version`. La version courante est v2 et chaque
dossier contient au minimum entree, resultats, audit, rapport maillage,
parametres solveur et verdict de qualification.

## Readiness remplacement

Un cas declare `replacement_candidate: true` est `replacement_ready` seulement
si:

- `expected_status` vaut `PASS`;
- le statut obtenu vaut `PASS`;
- tous les criteres `checks` passent;
- la maturite vaut `stable`;
- le profil est `strict` ou `qualification`.
- au moins une reference independante passe. Les types independants sont
  `analytic`, `equilibrium_closed_form`, `third_party` et `experimental`.

Si une de ces conditions manque, le cas peut rester suivi dans la campagne, mais
il ne doit pas etre utilise comme remplacement logiciel.

Une reference `non_regression` seule ne suffit donc jamais a rendre un cas
`replacement_ready`.

## Monter une nouvelle famille au statut stable

Avant de changer une maturite de `experimental` vers `stable`, ajouter:

- un cas analytique ou une reference logiciel tiers;
- un seuil d'erreur explicite;
- un test API;
- un test CLI;
- un cas de rejet ou de degradation maillage;
- une entree dans la matrice de qualification.

## Commande de reference

```powershell
python .\qf_solver.py qualify --manifest .\qualification\campaign.json --output .\results\qualification_campaign
```
