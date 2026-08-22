---
doc_id: DOC-PUB-AUD-021-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.1a0
owner_review: pending
reviewer: ""
approver: ""
---

# Audit documentaire de publication 0.2.1a0

## Objet

Cet audit verifie que les documents et preuves destines au depot public sont
classes, que les chemins de poste et informations internes sont absents, et
que la livraison documentaire ne depend plus d'un runtime web.

Il ne prononce aucune acceptation mecanique. Les decisions de maturite restent
dans les enregistrements `owner_review` et les `external_audit` associes aux
perimetres mecaniques.

## Commande reproductible

```powershell
python .\scripts\audit_public_documents.py
python .\scripts\audit_public_release.py
```

Le resultat machine-readable est
`qualification/publication_audit_0_2_1.json`. Il est mis a jour avant un tag
de release, apres toute modification des documents versionnes.

## Classement

| Classe | Contenu | Politique |
| --- | --- | --- |
| `public` | README, sources Markdown/PDF, figures et preuves sous `docs/` | versionne et audite |
| `public_historical` | baseline 0.2.0 immuable | conservee sans reecriture |
| `internal` | configurations locales, graphes de travail et corpus de preuves locaux | ignore et absent de l'archive publique |
| `generated_not_published` | sorties de calcul, livraison web retiree et repertoires de travail | ignore et absent de l'archive publique |

Les artefacts sous `docs/generated/` et `docs/assets/generated/` restent
publics lorsqu'ils sont suivis par Git : ce sont des resultats, tableaux ou
figures references par la documentation. Ils sont donc inclus dans l'audit de
confidentialite, contrairement aux repertoires de travail ignores.

## Controles

Le script execute quatre controles bloquants :

1. hygiene des sources et documents publics ;
2. vocabulaire controle `automated_verification`, `owner_review` et
   `external_audit` ;
3. absence de runtime et de dependances de livraison web ;
4. absence de chemins internes ou de corpus de travail dans les fichiers suivis.

Les droits de redistribution des publications, valeurs de benchmark et sorties
externes restent soumis a `THIRD_PARTY_LICENSES.md` et a la politique des
oracles externes. L'audit automatise ne remplace pas cette verification de
provenance.

## Statut

Le resultat courant est `PASS`. La verification de provenance des artefacts
tiers reste une action de release distincte avant tout tag public.
