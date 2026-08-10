---
doc_id: DOC-VV-004
revision: 0.1
status: draft controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Qualification et limites de revendication

Le projet vise un outil qualifiable et verifiable. Seule une autorite ou un
processus externe peut attribuer le statut `qualified` a un scope.

## Profils

| Profil | Usage | Politique |
| --- | --- | --- |
| quick | Developpement | Smoke tests et controles rapides |
| engineering | Usage courant | Campagne complete de developpement |
| strict | Revue technique | Warnings bloquants selon politique |
| qualification | Candidat controle | Revision source, preuves et maturites obligatoires |

Le site `engineering` peut etre construit sur un depot non committe, mais il
affiche `source revision: uncommitted`. Le site `qualification` refuse cet
etat, les pages sans revue, les exigences orphelines et les capacites
experimentales presentees comme acceptables.

Consulter la [matrice de qualification](../qualification_matrix.md), le
[plan V&V](../verification_validation_plan.md), la
[readiness des formules et revues](formules.md) et l'[audit industriel](../audit_qualification_industrielle.md)
pour le processus complet.

## Domaine borne TET4 statique lineaire

Le domaine `tet4-linear-static-v1` est accepte pour l'usage engineering
interne par la [decision du 14 juillet 2026](revue_tet4_lineaire.md). Il reste
`candidate` dans le registre de qualification, car l'auto-revue de l'auteur
n'est pas une qualification externe independante.

Ce domaine est publie dans chaque audit et
dossier de preuve. Il exige des elements TET4 seuls, une loi
`isotropic_3d`, $E>0$ Pa et $0\le\nu\le0.45$. La borne superieure sur $\nu$
ecarte la zone quasi incompressible dans laquelle le TET4 deplacement lineaire
peut verrouiller volumiquement.

Les controles numeriques associes imposent une qualite tetraedrique minimale
de $0.05$, un radius ratio minimal de $0.05$, un aspect ratio maximal de 20 et
un conditionnement estime de la rigidite reduite inferieur ou egal a
$10^{12}$. Un depassement produit un `WARNING`; les profils `strict` et
`qualification` le rendent bloquant. Ces limites delimitent le domaine teste,
elles ne constituent pas une loi universelle de validite mecanique.

## Domaine MITC4 statique lineaire

Le MITC4 isotrope en statique lineaire est accepte avec reservations pour un
usage engineering interne par la [decision du 14 juillet 2026](revue_mitc4_lineaire.md).
Le scope officiel reste `candidate`: l'auto-revue ne constitue pas une
qualification externe independante. Les recommandations Cook et la correlation
Abaqus a maillage identique sont obligatoires avant d'elever ce niveau de preuve.

## Domaine MITC4 harmonique

Le scope `mitc4-harmonic-response` est `candidate` et accepte avec
recommandations pour un usage engineering interne par la
[decision du 15 juillet 2026](revue_mitc4_harmonique.md). La validation couvre
la condensation exacte du drilling, l'excitation large bande, les amplitudes,
les phases et les contraintes complexes locales `S11/S22/S12` par frequence.
La correlation NAFEMS 13H donne sur le pic `S11` un ecart de `1,477 %` avec
Abaqus S4R, `1,412 %` avec Abaqus S4, `2,626 %` avec NAFEMS et `3,730 %` avec
la theorie de Navier. Les courbes complexes completes doivent maintenant etre
produites avec CalculiX puis Code_Aster. Abaqus S4/S4R reste une reference
publiee; aucune licence locale n'est exigee. Une revue independante reste
recommandee.

## Domaine solides orthotropes TET4/TET10

Le scope `orthotropic-solid-tet4-tet10` est
`engineering_internal_validated_with_recommendations` depuis le 22 juillet
2026.

La commande `qualification-readiness` affiche encore `scope status: candidate`.
Ce champ appartient au registre de traçabilite : il signifie que le domaine est
eligible a une progression de qualification et que ses liens exigences/code/
tests existent. Il ne remplace pas la decision mecanique humaine, qui est
enregistree separement dans
`qualification/reviews/orthotropic_solids_2026-07-22.json`.
Les huit specifications automatiques `SPEC-COMP-SOLID-001..008` sont couvertes :
loi 3D, patchs TET4/TET10, objectivite, convergence structurelle, correlation
Code_Aster/CalculiX et non-regression isotrope.

Le TET10 est le chemin recommande pour les structures orthotropes dominees par
flexion ou gradients de contrainte. Le TET4 est convergent, mais reste raide en
flexion sur les maillages courants; son usage doit etre accompagne d'une
recommandation de raffinement ou de bascule TET10. Les orientations constantes
par materiau, region ou element sont acceptees; le champ d'orientation continu
sur geometrie courbe reste un scope distinct. La revue est disponible dans
[la revue des solides orthotropes](revue_solides_orthotropes.md), et le dossier
de passage en revue est [centralise ici](dossier_validation_owner.md).
