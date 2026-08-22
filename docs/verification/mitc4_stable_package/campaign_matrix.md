---

doc_id: DOC-VNV-MITC4-STABLE-MATRIX-001
revision: 0.1
status: owner_reviewed
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Matrice de campagne MITC4

| Sous-scope | Statut de départ | Campagne obligatoire | Référence principale | Critère de sortie |
|---|---|---|---|---|
| MITC4 isotrope | stable | non-régression statique/modal/Newmark/harmonique | théorie + Code_Aster | aucune régression, résidus conformes |
| MITC4 multicouche | stable borné statique et dynamique sur trois layups | trois layups, ABD, contraintes par pli, dynamique | NAFEMS R0031 + Code_Aster | observables primaires <= 1 % au niveau final |
| MITC4 orthotrope 1 pli | stable borné | axes 0/45/90, rotation, statique et dynamique; courbe axiale 0° | théorie orthotrope + Code_Aster + CalculiX | observables internes <= 1 %, exclusions et limite harmonique courbe conservées |

## Contrôles communs

Les trois sous-scopes utilisent la même liste de contrôles :

- connectivité et qualité du maillage ;
- repère local de chaque facette ;
- orientation matériau et projection sur la facette ;
- matrice de rigidité symétrique ;
- masse cohérente symétrique et positive sur les sous-espaces utiles ;
- résidu statique, modal et dynamique ;
- bilan énergie/travail en statique et dérive énergétique en Newmark ;
- amplitude, phase et limite à fréquence nulle en harmonique ;
- figure de maillage, déformée et champ mécanique ;
- traçabilité des versions et des fichiers d'entrée.

## Règle de maturité

Un résultat `PASS` technique ne suffit pas à lui seul pour la promotion. Le
statut `stable` est attribué seulement après la fermeture des preuves et la
signature de la décision Owner correspondant exactement au sous-scope testé.
Pour l'orthotrope mono-pli, l'orientation projetée non axiale sur une surface
courbe reste explicitement hors du périmètre stable tant qu'une corrélation
externe avec la même convention locale n'est pas disponible.
