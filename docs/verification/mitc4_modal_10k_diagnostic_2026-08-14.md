---
doc_id: DOC-VNV-MITC4-MODAL-10K-DIAGNOSTIC-2026-08-14
revision: 0.1
status: draft
applicable_version: 0.2.1-alpha
reviewer: ""
approver: ""
---

# Diagnostic MITC4 modal 10 000 QUAD4 - 2026-08-14

**Statut :** `QF_NUMERICAL_TIMEOUT_REFERENCE_AVAILABLE`  
**Type :** diagnostic de performance, non corrélation acceptée  
**Référence externe :** Code_Aster 18.1.0, même référence déjà archivée  
**Périmètre :** MITC4 multicouche `[45/-45/-45/45]`, `200 x 50`, soit `10 000` QUAD4

## Configuration

La tentative a utilisé `eigsh` avec un shift de `1 Hz`, une condensation
`drilling` lazy, un préconditionneur `spilu`, `drop_tol=1e-6`,
`fill_factor=20`, `ncv=40`, `maxiter=3000`, et une résolution GMRES interne
avec `rtol=1e-8`, `maxiter=2000`, `restart=100`.

La référence Code_Aster n'a pas été recalculée. Elle a été réutilisée depuis
le dossier déjà contrôlé `mitc4_modal_10k`, afin de ne pas mélanger deux
versions de l'oracle externe.

## Observation

Le calcul QF_solver a atteint la limite de temps de la campagne, fixée à
`900 s`, sans produire d'eigenpaire exploitable ni de `summary.json`. La
mémoire du processus est restée approximativement à `425 MiB` et le processus
est resté actif jusqu'à son arrêt contrôlé. Aucun processus résiduel n'est
laissé après la campagne.

## Interprétation

Cette tentative montre que l'augmentation du redémarrage GMRES ne suffit pas,
à elle seule, à fermer le cas 10k. Elle confirme une limite de convergence et
de temps de l'opérateur modal creux, avec une mémoire maîtrisée sur cette
machine. Elle ne constitue pas une corrélation externe et ne change pas la
maturité MITC4 multicouche.

Le cas contrôlé `40 x 10` reste la preuve positive disponible : écart modal
maximal `0,70194 %` et résidu QF_solver `8,66e-9`. Le cas `10 000` QUAD4
reste ouvert pour un backend distribué ou un préconditionneur AMG/SLEPc.

## Reproduction

```powershell
python .\scripts\run_code_aster_mitc4_modal_10k_vnv.py `
  --output .\tmp\code_aster\mitc4_modal_10k_eigsh_lazy_restart100 `
  --qf-method eigsh `
  --qf-preconditioner spilu `
  --qf-shift-hz 1.0 `
  --qf-drop-tol 1e-6 `
  --qf-fill-factor 20 `
  --qf-maxiter 3000 `
  --qf-ncv 40 `
  --qf-inner-rtol 1e-8 `
  --qf-inner-maxiter 2000 `
  --qf-inner-restart 100 `
  --skip-external
```

La commande ci-dessus doit être exécutée avec une référence Code_Aster
disponible dans le dossier de sortie si `--skip-external` est utilisé.
