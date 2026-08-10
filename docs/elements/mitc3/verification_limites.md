---
doc_id: DOC-ELEM-MITC3-06
revision: 0.2
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Verification, shear locking et limites

## Matrice de preuves

| Etude | Objet | Critere principal |
| --- | --- | --- |
| `VNV-MITC3-PATCH-001` | champs membrane et cisaillement constants | erreur d'interpolation |
| `VNV-MITC3-SHEAR-LOCKING-002` | plaque mince | absence d'effondrement de fleche |
| `VNV-MITC3-DISTORTION-003` | noeuds perturbes | sensibilite bornee |
| `VNV-MITC3-COOK-004` | membrane biaisee | convergence de la fleche |
| `VNV-MITC3-SCORDELIS-005` | coque cylindrique | valeur et symetrie |
| `VNV-MITC3-PINCHED-006` | cylindre pince | convergence |
| `VNV-MITC3-MIXED-MESH-007` | interface TRI3/QUAD4 | patch affine |
| `VNV-MITC3-LOADS-008` | charges coherentes | forces et moments |
| `VNV-MITC3-MODAL-009` | masse coherente | residus et orthogonalite |
| `VNV-MITC3-NEWMARK-010` | vibration libre | derive d'energie |
| `VNV-MITC3-HARMONIC-011` | balayage | limite statique et phase |
| `VNV-MITC3-LAMINATE-012` | stratifies | ABD et contraintes par pli |
| `VNV-MITC3-LAMINATE-DYNAMIC-001` | stratifies, statique/modal/Newmark/harmonique | patch affine, masse coherente et invariants dynamiques |

La commande de developpement est:

```powershell
python .\scripts\run_mitc3_vnv.py --quick
```

La campagne rapide passe les invariants de formulation et laisse en
`WARNING` les benchmarks structurels volontairement grossiers. La campagne
complete doit etre executee, comparee a Code_Aster/CalculiX et relue avant
toute elevation de maturite.

La baseline V2 corrigee atteint une erreur de cisaillement constant de
`1,81e-16` et un ratio de fleche mince de `0,97951`. Les raffinements
Scordelis-Lo et cylindre pince atteignent respectivement `0,4044 %` et
`2,0899 %` d'ecart autour de 20 000 triangles.

## Shear locking

Le temoin important est le ratio entre la fleche EF et la reference
Timoshenko lorsque $t/L$ tend vers zero. Une formulation verrouillee fait
tendre ce ratio vers zero. MITC3+ conserve une reponse finie et convergente,
mais les triangles P1 peuvent demander un raffinement plus important que
MITC4 en flexion. Cette difference de vitesse de convergence n'est pas
confondue avec du locking.

## Domaine actuel

Inclus: facettes planes, petits deplacements, isotrope et stratifies
lineaires, statique, modal, Newmark et harmonique. Pour le MITC3+
multicouche, la preuve interne dynamique est limitee au stratifie plan
symetrique `[0/90/90/0]`; la correlation externe et l'Owner review restent
ouvertes.

Exclus: grandes rotations, flambement, post-flambement, contact entre plis,
delaminage, dommage progressif et certification externe. Le statut reste
`experimental` jusqu'a la campagne complete et a l'owner review.

\enlargethispage{4\baselineskip}

## Reference primaire

Lee, P.-S., Lee, Y. et Bathe, K.-J., *The MITC3+ shell element and its
performance*, Computers & Structures 138 (2014), 12-23,
DOI: 10.1016/j.compstruc.2014.02.005.
