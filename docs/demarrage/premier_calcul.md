---
doc_id: DOC-START-002
revision: 0.1
status: draft technique
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Premier calcul controle

Le premier calcul doit enchainer validation, resolution et preuve. Le cas
TET4 officiel fournit une reference analytique simple.

```powershell
python .\qf_solver.py check-mesh --input .\examples\tet4_static.json --json-report .\results\first_mesh.json
python .\qf_solver.py solve --input .\examples\tet4_static.json --output .\results\first_result.json --audit-md .\results\first_audit.md --audit-gate fail
python .\qf_solver.py evidence --input .\examples\tet4_static.json --output .\results\first_evidence
python .\qf_solver.py verify-evidence --input .\results\first_evidence
```

## Points a relire

| Controle | Attendu |
| --- | --- |
| `mesh_report.status` | `PASS` |
| `run_verdict` | `PASS` ou avertissement explicitement accepte |
| Residu relatif libre | Inferieur au seuil du profil |
| Equilibre | Charges et reactions compatibles |
| Energie lineaire | $u^TKu\simeq u^Tf$ |
| Empreintes | Tous les fichiers du manifeste verifies |

Un deplacement plausible ne suffit pas: le maillage, les unites, les
conditions limites et les bilans doivent etre plausibles simultanement.
