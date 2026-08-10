---
doc_id: DOC-VV-008
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Etudes V&V comparees

## Objectif

Chaque nouvel element ou solveur doit etre associe a une etude V&V avant son
integration dans un perimetre candidat. Une etude compare QF_solver a une
solution analytique, a une publication primaire ou a un solveur de reference.
Les solveurs libres CalculiX et Code_Aster sont prioritaires lorsqu'une
licence commerciale n'est pas disponible; Abaqus et Ansys peuvent rester des
references publiees clairement identifiees. Elle produit obligatoirement un rapport Markdown, des
resultats machine-readable, des empreintes SHA-256 et les deformees utilisees
pour la revue.

Le format v1 compare des grandeurs scalaires choisies aux memes points et avec
les memes conventions : deplacements, energies, reactions, contraintes ou
frequences. La comparaison champ a champ avec projection entre maillages
dissemblables n'est pas encore implementee. Les PNG et VTU permettent donc la
revue visuelle, tandis que les criteres automatiques portent sur les grandeurs
normalisees declarees.

## Organisation d'une etude

```text
VNV-TET4-CANTILEVER-001/
  study.json
  results/
    h1_qf.json
    h1_qf_deformation.png
    h1_qf_deformation.vtu
    h2_qf.json
    h3_qf.json
  references/
    h1_abaqus.json
    h1_abaqus.inp
    h1_abaqus_deformation.png
    h1_abaqus_deformation.vtu
    h2_abaqus.json
    h3_abaqus.json
```

Les modeles controles sont disponibles dans
`qualification/vnv/templates/`. Les schemas documentaires se trouvent dans
`qualification/vnv/schema/`.

## Definition `study.json`

Le fichier d'etude est l'autorite pour le cas, les maillages et les seuils.
Les niveaux sont ranges du plus grossier au plus fin avec une taille
caracteristique strictement decroissante.

| Groupe | Role |
| --- | --- |
| `study_id`, `title`, `scope` | Identite stable et perimetre de qualification |
| `subject` | Element ou methode evaluee et maturite revendiquee |
| `author`, `validation` | Responsabilites, decision et nature de la revue |
| `reference` | Solveur, version, manuel, revision et cas de reference |
| `quantities` | Grandeurs, metrique d'erreur, unite implicite interdite et seuil |
| `levels` | Taille `h` et paire de resultats normalises par maillage |
| `convergence` | Monotonie, ordre minimal et erreur finale admissible |
| `acceptance` | Exigence de deformees sur aucun, le dernier ou tous les maillages |

Pour une grandeur $q$, l'erreur absolue et l'erreur relative sont

$$
e_a = |q_{QF}-q_{ref}|,
\qquad
e_r = \frac{|q_{QF}-q_{ref}|}
{\max(|q_{ref}|,q_{floor})}.
$$

L'ordre observe est estime par regression lineaire de
$\log(e)$ sur $\log(h)$. Au moins trois niveaux sont imposes lorsqu'un critere
de convergence est declare.

## Resultat normalise

QF_solver et le solveur de reference utilisent le meme contrat :

```json
{
  "schema_version": 1,
  "case_id": "VNV-TET4-CANTILEVER-001",
  "producer": {
    "name": "Abaqus",
    "version": "2024",
    "run_id": "ABAQUS-H1-20260713"
  },
  "units_system": "SI",
  "mesh": {
    "nodes": 1000,
    "elements": 4200,
    "dofs": 3000,
    "characteristic_size": 0.2
  },
  "quantities": {
    "tip_uz": {"value": -0.00125, "unit": "m"},
    "strain_energy": {"value": 12.4, "unit": "J"},
    "max_von_mises": {"value": 205000000.0, "unit": "Pa"}
  },
  "diagnostics": {"source_job_status": "COMPLETED"},
  "visualization": {
    "deformation_scale": 100.0,
    "field": "displacement_magnitude",
    "view": "isometric_xyz",
    "undeformed_overlay": true
  },
  "artifacts": {
    "deformation_png": "h1_abaqus_deformation.png",
    "deformation_vtu": "h1_abaqus_deformation.vtu",
    "source_input": "h1_abaqus.inp"
  }
}
```

Les identifiants de grandeur et les unites doivent etre strictement identiques
dans les deux sorties. Une conversion d'unites manuelle non tracee est
interdite. Le `run_id`, la version du solveur et le fichier source commercial
doivent permettre de retrouver le calcul d'origine.

## Correlation avec un solveur externe

1. Utiliser exactement la meme geometrie, le meme maillage ou une serie de
   maillages dont la difference est expliquee.
2. Verifier la famille elementaire, l'integration, les materiaux, les charges,
   les blocages et le systeme d'unites.
3. Extraire les valeurs avec un script reproductible depuis les resultats
   CalculiX, Code_Aster, Abaqus ou Ansys; ne pas recopier une valeur lue a
   l'ecran.
4. Enregistrer le fichier d'entree, la version du solveur, le statut du job,
   les criteres de convergence et les points d'extraction.
5. Exporter une vue de la deformee avec facteur d'amplification, legende,
   chargements et conditions aux limites, puis un champ VTU lorsque possible.
6. Remplir un `normalized_reference_result.json` par niveau de maillage.

Le dossier doit distinguer un resultat effectivement calcule d'une valeur
publiee. Une table Abaqus ou NAFEMS peut constituer une reference primaire,
mais ne doit jamais etre etiquetee comme une execution locale. Les manuels
commerciaux sont soumis a licence; le rapport cite leur version et leur
section sans recopier de contenu protege dans le depot.

### Chaine de preuve recommandee

Pour les elements et solveurs critiques, la cible est :

```text
QF_solver <-> solution analytique <-> benchmark publie <-> solveur libre independant
```

Lorsque les outils le permettent, CalculiX et Code_Aster sont tous deux
executes. Ils ne sont pas fusionnes en une reference unique : chaque solveur
possede son entree, sa version, ses conventions, ses resultats normalises et
son verdict. Une divergence entre les deux fait l'objet d'une analyse avant
acceptation du scope.

Le cas `VNV-MITC4-HARMONIC-CODEASTER13H-DKQ-007` applique cette regle au
benchmark NAFEMS 13H. Code_Aster `18.1.0` est execute localement sur le meme
maillage `8x8`. Les ecarts Code_Aster/QF_solver restent inferieurs a `5 %`
sur la frequence de pic, le deplacement central et `S11` de face. La
formulation DKQ Kirchhoff et la reconstruction de contrainte depuis les
rotations complexes sont explicitement distinguees du MITC4 Reissner-Mindlin.

## Execution

```powershell
qf-solver vnv-compare `
  --study .\VNV-TET4-CANTILEVER-001\study.json `
  --output .\results\VNV-TET4-CANTILEVER-001
```

## Etude pre-remplie depuis le benchmark TET4

Le benchmark controle `BM-SOL-CANTILEVER-001` contient deja six maillages
TET4, les VTU et la reference analytique de Timoshenko. La commande suivante
creee une etude complete sans recopier les grands resultats JSON bruts :

```powershell
qf-solver vnv-import-benchmark `
  --case BM-SOL-CANTILEVER-001 `
  --output .\VNV-TET4-CANTILEVER-ANALYTIC-001
```

Elle genere six PNG QF_solver et une PNG de la ligne moyenne analytique,
avec le meme facteur d'amplification. La reference analytique est explicitement
identifiee; elle ne remplace ni une comparaison Abaqus/Ansys, ni un champ 3D
de contraintes de reference. Un dossier de sortie deja existant est refuse
par securite; `--overwrite` doit etre demande explicitement.

## Etude de torsion TET4 et sonde fine de contrainte

La commande suivante construit et execute l'etude controlee de torsion
circulaire :

```powershell
qf-solver vnv-import-benchmark `
  --case BM-SOL-TET4-TORSION-001 `
  --output .\VNV-TET4-TORSION-ANALYTIC-001

qf-solver vnv-compare `
  --study .\VNV-TET4-TORSION-ANALYTIC-001\study.json `
  --output .\results\VNV-TET4-TORSION-ANALYTIC-001 `
  --require-approval
```

Les huit niveaux utilisent le meme maillage pour le champ QF_solver et le
champ analytique de Saint-Venant. Chaque niveau contient deux PNG comparables
et deux VTU. La rotation terminale converge de `34,50 %` d'erreur a `3,07 %`,
avec un ordre observe de `1,499`. Le couple resultant est reproduit a l'arrondi
pres et le verdict automatique est `PASS`.

Sur h8, l'erreur L2 de contrainte vaut `29,06 %`. Une sonde supplementaire
utilise ensuite `105 529` TET4, soit `4,007` fois plus d'elements, et ramene
l'erreur de rotation a `1,242 %` et l'erreur globale L2 de contrainte a
`18,891 %`. Les six controles de la sonde sont en PASS.

La decision Owner est donc `accepted` pour l'usage engineering interne dans
le domaine borne de l'etude. Le seuil de contrainte est `20 %` sur une norme
L2 globale d'un arbre circulaire lisse; il ne qualifie pas un pic ponctuel,
une singularite ou une autre geometrie. Le dossier controle est
`VNV-TET4-TORSION-ANALYTIC-001/`; `STUDY.md` et
`stress_probe_h9/STRESS_PROBE.md` permettent une lecture directe.

La sonde est reproductible sans audit JSON monolithique :

```powershell
python .\scripts\run_torsion_stress_probe.py `
  --output .\VNV-TET4-TORSION-ANALYTIC-001\stress_probe_h9 `
  --overwrite
```

Le sous-dossier `commercial_reference/` explique les entrees Abaqus ou Ansys
encore attendues. Aucun resultat commercial n'est simule ou remplace par la
reference analytique.

Pour rendre la decision Owner obligatoire dans une campagne de livraison :

```powershell
qf-solver vnv-compare --study study.json --output results --require-approval
```

La commande produit :

| Fichier | Contenu |
| --- | --- |
| `comparison.json` | Ecarts, convergence, checks et statut de revue |
| `study_report.md` | Etude complete lisible et checklist humaine |
| `convergence.png` | Courbes d'erreur pour les grandeurs declarees |
| `inputs/` | Copie autonome du protocole et des resultats normalises |
| `artifacts/` | Copies autonomes des PNG, VTU et sources declarees |
| `vnv_manifest.json` | Empreintes d'entrees, environnement et revision source |

## Revue de Quentin Farinazzo

Dans la baseline actuelle, Quentin Farinazzo est a la fois auteur et
validateur mecanique. Le champ `mode` doit donc rester `self_review` et le
rapport indique `independence: not_independent`. Apres lecture complete, la
decision passe de `pending` a `accepted`, `accepted_with_reservations` ou
`rejected`, avec une date et des commentaires.

Cette auto-revue est recevable comme decision interne engineering. Elle ne
doit pas etre presentee comme une revue independante, une certification ou une
qualification attribuee par une autorite externe. Toute modification d'une
entree ou d'un resultat change son empreinte et impose une nouvelle revue.

## Regle d'integration

Une fonctionnalite ne peut pas monter en maturite si :

- un critere automatique est en `FAIL`;
- la convergence demandee n'est pas monotone ou reste sous l'ordre minimal;
- les deformees requises ne sont pas disponibles;
- la decision Owner est `pending` ou `rejected` pour une livraison;
- les ecarts, points d'extraction, versions ou unites ne sont pas explicables;
- une anomalie bloquante reste ouverte.
