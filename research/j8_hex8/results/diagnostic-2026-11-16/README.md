# J8 HEX8-SRI diagnostic artifacts

Ces fichiers documentent trois diagnostics de développement décrits dans
[`0.3.0-j8-resultats.md`](../../../../docs/planning/0.3.0-j8-resultats.md).
Ils ne remplacent pas les FAIL J7 et ne constituent pas une qualification.

## Contenu

- `regular/` : vecteurs de méthodes du run J8 régulier, snapshot de diagnostic
  assaini, métriques indépendamment recalculées, contrat et manifeste gelés
  du run d’origine, enregistrement runner sans chemins locaux.
- `near_degenerate/` : mêmes artefacts pour le cas quasi dégénéré, avec les
  huit méthodes et le solveur mpmath à 80 chiffres.
- `geometry_contrast/` : résultat du contrôle géométrique, matrices et état
  réassemblés, contrat et enregistrement runner assaini.
- `regular/posthoc_rigid_mode_audit.json` et
  `near_degenerate/posthoc_rigid_mode_audit.json` : post-traitement descriptif
  ultérieur des modes rigides sur les matrices archivées, sans nouveau solve
  ni seuil d’acceptation.
- `sha256_manifest.json` : taille et SHA-256 de chaque fichier listé ici.

Les copies J7 de K, f, déplacements, masque et coordonnées sont dans
`research/j8_hex8/inputs/`, liées aux empreintes de leur manifeste. Les
fichiers de runner bruts restent dans le stockage local ignoré et peuvent
contenir des chemins Windows. Les snapshots suivis retirent uniquement les
chemins des DLL numériques ; les hashes bruts sont conservés dans le champ
`provenance` ou dans l’enregistrement runner correspondant.

## Recalculer les métriques récupérées

Depuis la racine du dépôt, les métriques sont recalculables sans solveur FEM
et sans résolution de système à partir du snapshot, du fichier des vecteurs,
du manifeste et du contrat conservés :

```python
from pathlib import Path
from research.j8_hex8.recovery import recover_method_archive

root = Path("research/j8_hex8/results/diagnostic-2026-11-16")
case = "regular"  # ou "near_degenerate"
folder = root / case
recover_method_archive(
    case,
    folder / "original_diagnostic_snapshot.json",
    folder / "method_solutions.npz",
    folder / "frozen_execution_manifest.json",
    folder / "frozen_contract.json",
    folder / "recovered_method_metrics.rebuilt.json",
)
```

Cette récupération exploite les vecteurs enregistrés pendant l’exécution
J8. Les temps individuels absents du checkpoint régulier restent absents.
