# Revue indépendante C03 — 2026-10-24

Auditeur distinct : `<reviewer-workspace>`, configuré GPT-6.1 Sol,
effort high demandé. Mandat en lecture seule, sans sous-délégation. Le présent
compte rendu est transcrit par le manager à partir du retour final de l'auditeur.

**ACCEPTÉ pour examen Owner.** Verdict recommandé :
`C03_PROOF_READY_FOR_OWNER_REVIEW`. Les huit preuves proposées couvrent les
304 contrôles prévus. Aucun défaut mathématique bloquant ne subsiste dans la
version figée examinée. Certificat : `PROPOSED_NOT_PROMOTED`.

## Défauts corrigés avant le gel

- P1 : l'ancien `sum` concaténait des tuples d'intervalles et annulait les
  déformations. Accumulation corrigée par `iadd`, `archive_inputs.py:229`.
- P1 : ordre des points HEX8 corrigé, dernière coordonnée variable le plus vite,
  conforme aux sources historiques; pointeurs élément/point corrigés.
- P1 : extrema décisifs séparés. Une violation intérieure prouvée produit FAIL,
  même si l'image complète de la marge traverse zéro, `rigorous_math.py:286`.
- P2 : l'agrégation HEX8 utilise la branche de chaque point, puis prend la plus
  petite marge stricte. Les extrema et contrôles de racine sont conservés.
- P2 : les statuts finaux respectent les quatre verdicts autorisés par le mandat,
  avec agrégat technique séparé et sans promotion automatique.

## Vérifications mathématiques indépendantes

À géométrie et histoire fixes, la petite déformation est affine en s et la
contrainte trial vaut C[epsilon(s)-epsilon_p,n]. Son déviateur est d0+s d1,
tandis que R=sigma_y0+H alpha_n est constant. Les coefficients sont donc
A=(3/2)d0:d0, B=3d0:d1 et C=(3/2)d1:d1, en Pa², Pa²/m et Pa²/m².

L'auditeur a effectué des calculs autonomes avec la bibliothèque standard,
sans importer les modules candidats ni le solveur :

- Recalcul des coefficients depuis les intervalles de déviateurs des 304 points.
- Contrôle rationnel des extrema aux extrémités et aux sommets intérieurs, avec
  séparation à s=0 pour les enveloppes des coefficients.
- Contrôle des signes par inégalités rationnelles contre R².
- Vérification des 1 216 comparaisons exactes de carrés archivées pour les racines.
- Reconstitution indépendante de G0, du module numérique D, des encadrements de
  production et du budget B.
- Vérification de `base_clearance > B` à chaque point.

Les plus petites marges strictes retrouvées, affichées approximativement en Pa :

| Famille | H [GPa] | Direction faible | Direction mixte |
|---|---:|---:|---:|
| TET4 | 0 | 526964930.480085 | 532345925.312127 |
| TET4 | 1.5 | 526964241.724462 | 532344530.188572 |
| HEX8 | 0 | 17953899.556314 | 21372630.382442 |
| HEX8 | 1.5 | 17953899.556314 | 21372630.382442 |

Les intervalles rationnels exacts des JSON font foi.

## Liaison avec la production

La récupération par division inverse est valide : pour les points plastiques,
le multiplicateur archivé provient de `fl(yield_value/D)`. Ses voisins binary64
et l'encadrement positif de D donnent un encadrement de la valeur avant retour.
Pour les points élastiques, le champ `yield_function` conserve directement cette
valeur. Le bit de branche ne sert pas à fabriquer la marge numérique.

La provenance du multiplicateur a été vérifiée dans les captures historiques :
commit `c1d123d…`, `pytest_capture.py:64` à 81, et commit `b5bda19…`,
`pytest_capture.py:96` à 113. Ces callbacks enregistrent le retour immédiat de
`_prepared_state`. Le test historique assemble la base avec l'histoire acceptée
à la ligne 230, avant les évaluations Decimal du stencil. Le multiplicateur
examiné est donc bien celui de cette évaluation de base.

Le budget maximal proposé est inférieur à 7.52e-7 Pa. C'est une borne certifiée
a posteriori de l'écart à la base, sans garantie numérique de production pour
toutes les perturbations du segment. L'auditeur a retrouvé des bornes légèrement
plus fines par son calcul indépendant; l'arrondi extérieur supplémentaire du
produit dans le candidat est conservateur et valide.

## Provenance et validation finale

- Checkout historique propre, commit
  `87e54913077c7d9fce6f259fb4a4a11f5295e6a5`, tree
  `c42e3c2241af1862d66cab51a38fda74a1167361`.
- 28 fichiers du premier inventaire et 35 fichiers HEX8 rehashés, inchangés.
- Huit histoires entrantes conformes à leurs digests historiques.
- Toutes les empreintes des huit entrées et huit résultats concordent avec le
  résumé final; 304 points PASS.
- Neuf fichiers Python courants identiques à `tested_sources`.
- Validation finale : 44 tests réussis via unittest avec `-I -S -B`.

| Fichier examiné | SHA-256 |
|---|---|
| archive_inputs.py | a1685152da6f45b232206ab7c20455048bd809f8f36bd340d9a05c927029686e |
| rigorous_math.py | 935d7a5c5a05d2007cddbdec9a2ad73051f1f8ca7f569a184bfcd3bcdf679836 |
| production_branch_budget.py | eaba6d150646a1e26faf0ba026ef42dc01dbc52bd6e864ca1bf9b3eef1522a33 |
| integrate_proofs.py | c19ea97206336db293a5810d011ec05f200e901f0f3c33b44c3f5e8d05f50f07 |
| proof_action_summary.json | 6ce32911d1f64a929e11d9ca70982bfcf1728d0779566576db75d3f3e9eb2386 |
| non_fem_verification_record.json | c958b2c43ce9e5c3fd22da7408e5fc22a9316c14661320694de7f18cf231658e |

L'auditeur déclare avoir effectué uniquement lectures, recherches, commandes Git
de consultation et scripts mathématiques autonomes sur stdin, notamment avec
`C:\Python313\python.exe -I -S -B -`. Il n'a effectué aucune écriture, aucun
import scientifique, aucun appel FEM et aucun lancement pytest.

## Écart de procédure et limites

Deux lancements pytest du worker ont contrevenu au mandat de délégation, comme
consigné dans `process_deviations.md`. Leur ensemble exact d'importations n'est
pas établi rétrospectivement. Aucun appel FEM n'est établi par les éléments
disponibles. La validation finale repose sur unittest isolé et les empreintes
vérifiées.

L'acceptation porte sur les huit segments du modèle mathématique explicitement
déclaré, à histoire fixe, et sur la liaison des décisions de production à la base.
Elle ne qualifie pas la tangente globale, les critères C04–C06 ou les décisions
numériques de production sur tout le segment. Les statuts scientifiques globaux
imposés restent inchangés. L'approbation et la promotion appartiennent à l'Owner.
