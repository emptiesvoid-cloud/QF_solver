---
doc_id: DOC-VNV-022-MULTI-MILLION-001
revision: 0.1
status: draft
applicable_version: 0.2.2a0
---

# Campagne multi-million DDL : execution Docker

Statut technique : **PASS_BOUNDED_DOCKER**. Le statut de maturite reste **development** jusqu'a la revue Owner.

Image : `qf-solver-large:0.2.0@sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8` ; image de base : `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`.
Backend PETSc avec CG + GAMG et matrice BAIJ. Budget RSS cumule maximal accepte : `32 GiB`.

## Cas executes

| Cas | DDL | Rangs | Elements | Assemblage (s) | Resolution (s) | Pipeline (s) | Iterations | Residu | RSS cumule |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2m_r2` | 2,044,416 | 2 | 3,951,018 | 19.921 | 27.161 | 48.238 | 54 | 8.801e-19 | 4.70 GiB |
| `2m_r4` | 2,044,416 | 4 | 3,951,018 | 12.585 | 23.530 | 37.029 | 55 | 5.477e-19 | 5.10 GiB |
| `4m_r2` | 4,102,893 | 2 | 7,986,000 | 61.328 | 57.781 | 121.394 | 57 | 7.552e-19 | 9.14 GiB |
| `4m_r4` | 4,102,893 | 4 | 7,986,000 | 47.227 | 49.624 | 98.690 | 57 | 1.041e-18 | 9.59 GiB |

## Scaling fort

| Taille | Speedup 2 -> 4 rangs | Efficacite | Seuil | Statut |
| ---: | ---: | ---: | ---: | --- |
| 2,000,000 DDL | 1.303 | 0.651 | 0.60 | PASS |
| 4,000,000 DDL | 1.230 | 0.615 | 0.60 | PASS |

## Criteres verifies

Chaque cas a ete verifie par son `evidence_manifest.json`, son audit grand modele, son empreinte d'entree et ses metriques runtime.
Les quatre cas passent le residu relatif `1e-8`, la convergence CG, le couple GAMG/BAIJ, la sortie file-backed et le budget RSS.

## Limites

- Une seule image Docker et une seule machine ont ete mesurees.
- La campagne couvre le statique lineaire TET4, pas le modal ou le dynamique multi-million.
- Le partitionnement execute est contiguous; la variante graphe reste a mesurer.
- Matrix-free et SLEPc ne sont pas des resultats de cette campagne.
- Le statut de traceabilite reste development jusqu'a la revue Owner.
