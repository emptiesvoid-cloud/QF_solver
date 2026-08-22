---
doc_id: DOC-UNREGISTERED-VERIFICATION-TET4-ERROR-CAUSAL-AUDIT-2026-08-21
revision: 0.1
status: draft
applicable_version: 0.2.1a0
reviewer: ''
approver: ''
---

# Audit causal TET4 : origine des ecarts

| Champ | Valeur |
| --- | --- |
| Document | `VNV-TET4-ERROR-CAUSAL-AUDIT-001` |
| Date | `2026-08-21` |
| Domaine | TET4 isotrope lineaire, statique, modal, Newmark et harmonique |
| Statut | `PASS_DIAGNOSTIC` |
| Promotion | Aucune promotion automatique |

## Reponse directe

Le pas de temps n'est pas la cause de l'ecart TET4 observe dans le domaine
teste. Le cas statique n'a pas de pas de temps et le cas dynamique conserve
des erreurs externes inferieures a `1 %` sur les observables comparees.

La cause principale du deficit de precision statique en flexion est spatiale :
le TET4 utilise une interpolation lineaire et une matrice `B` constante dans
chaque element. Une courbure est donc representee par morceaux constants et
demande un raffinement important.

Le solveur lineaire n'est pas incrimine : le cas structure fin a un residu
relatif de `2,088e-16` apres `252` iterations. La correlation QF_solver / Code_Aster
`TETRA4` sur maillage identique est de `8,051e-13`, ce qui exclut une
divergence d'implementation comme cause de l'ecart avec la reference de poutre.

## Valeurs de decision

| Controle | Valeur | Limite | Verdict |
| --- | ---: | ---: | --- |
| TET4 statique, porte-a-faux structure fin | `0,818328 %` | `1 %` | `PASS` |
| QF_solver / Code_Aster TETRA4, meme maillage | `8,051e-11 %` | `1 %` | `PASS` |
| Incrementation finale de maillage externe | `4,643 %` | `1 %` | `WARNING` |
| TET4 modal / Code_Aster | `7,891e-11 %` | `1 %` | `PASS` |
| TET4 Newmark / Code_Aster | `8,159e-09 %` | `1 %` | `PASS` |
| TET4 harmonique / Code_Aster | `5,329e-10 %` | `1 %` | `PASS` |

Les valeurs dynamiques ne doivent pas etre lues comme une precision
universelle : elles concernent le modele, la grille temporelle et la grille
frequentielle declares dans les preuves sources.

## Interpretation mecanique

Le raffinement permet bien de passer sous `1 %` pour le porte-a-faux structure
documente. Cela ne prouve pas que tout TET4 sera sous `1 %`. Le dernier
increment de maillage disponible dans la correlation externe reste de `4,643 %`;
la valeur finale est donc acceptable pour le sous-perimetre, mais la stabilite
asymptotique generale n'est pas encore demontree.

Le comparatif TET10 est un diagnostic d'ordre d'interpolation. Il confirme que
le TET4 est l'approximation limitante en flexion, mais ne remplace pas une
reference tridimensionnelle d'ordre identique pour toutes les geometries.

## Actions restantes avant une promotion generale

1. Ajouter un niveau de raffinement apres l'increment de `4,643 %`.
2. Refaire le gate sous `1 %` sur une geometrie TET4 non rectangulaire ou avec
   une seconde famille de chargement.
3. Conserver la correlation TET4/TETRA4 comme controle d'implementation.
4. Ne pas extrapoler cette preuve aux grandes deformations, au contact, a
   l'orthotropie ou au materiau non lineaire.

## Artefacts et reproductibilite

Le rapport machine-readable et la figure sont generes par :

```powershell
python .\scripts\run_tet4_error_audit.py
```

Artefacts :

- [`summary.json`](../../qualification/vnv/tet4_error_audit_2026-08-21/summary.json)
- [`report.md`](../../qualification/vnv/tet4_error_audit_2026-08-21/report.md)
- [`tet4_error_convergence.png`](../../qualification/vnv/tet4_error_audit_2026-08-21/tet4_error_convergence.png)
- [`vnv_manifest.json`](../../qualification/vnv/tet4_error_audit_2026-08-21/vnv_manifest.json)

L'audit ne signe pas une Owner Review et ne change pas seul la maturite du
scope.
