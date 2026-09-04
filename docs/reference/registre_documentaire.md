---
doc_id: DOC-REF-002
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Documentation registry

Le fichier `docs/document_registry.json` est la source machine-readable des
identifiants, chemins, statuts et exigences documentees. La table ci-dessous
est regeneree et controlee lors du build.

--8<-- "docs/generated/document_registry.md"

## Regle de revue

Une page reste `draft` tant que les champs de revue correspondants ne sont pas
approuves dans un registre `owner_review` ou `external_audit` hors du generateur.
Le code ne remplit jamais automatiquement une signature de revue.
