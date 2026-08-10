---
doc_id: DOC-VNV-ELEMENT-ANALYSIS-MATRIX-001
revision: 1.0
status: controlled
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Matrice elements et familles d'analyse

## Regle d'interpretation

Une validation statique ne valide jamais automatiquement le modal, Newmark
ou l'harmonique. La statique controle principalement la rigidite `K`. Le
modal ajoute la masse `M`, ses modes nuls, les residus propres et les
orthogonalites. Newmark ajoute les conditions initiales, l'amortissement,
l'integration temporelle, l'energie et le choix du pas. L'harmonique ajoute
les amplitudes complexes, les phases, les resonances et la condensation des
DDL sans masse.

De meme, une formulation lineaire ne prouve pas une formulation non lineaire.
Le non-lineaire exige une force interne, une tangente consistante, des
variables d'etat, une strategie d'increments et des preuves de convergence.

La source machine-readable de cette page est
`qualification/element_analysis_matrix.json`.
Le registre des decisions Owner encore necessaires est
`qualification/reviews/linear_dynamic_closure_register.json`.

## Bilan synthetique

| Famille | Statique lineaire | Modal | Newmark | Harmonique | Non-lineaire statique |
| --- | --- | --- | --- | --- | --- |
| TET4 | Owner accepte | Owner accepte | Owner accepte | Owner accepte | J2 experimental; total lagrangien accepte avec recommandations |
| TET10 | Owner accepte | Owner accepte | Owner accepte | Owner accepte | J2 petits deplacements verifie en developpement; correlation externe et Owner review ouvertes |
| MITC4 | Owner accepte | Owner accepte avec recommandations | Owner accepte avec recommandations | Owner accepte avec recommandations | non supporte |
| MITC3+ | Owner accepte | Owner accepte avec recommandation | Owner accepte avec recommandation | Owner accepte avec recommandation | non supporte |
| BEAM2 | correle, experimental | Owner accepte borne | Owner accepte borne | Owner accepte borne | non supporte |
| ressorts/masses | statique analytique et Code_Aster | Owner accepte borne | Owner accepte borne | Owner accepte borne | non supporte |
| contact | accepte en statique bornee sans frottement | non supporte | non supporte | non supporte | frottement experimental |

## Ce qui est effectivement ferme

- TET4 statique lineaire isotrope.
- TET10 statique lineaire isotrope, masse coherente et preuve modale bornee.
- MITC4 statique lineaire, modal, Newmark et harmonique, chacun avec une
  decision Owner distincte et des recommandations explicites.
- TET4 et TET10 modal, Newmark et harmonique, acceptes pour le domaine
  engineering borne le 2 aout 2026.
- MITC3+ statique lineaire, accepte le 1er aout 2026; modal, Newmark et
  harmonique acceptes le 2 aout 2026 avec recommandation de raffinement
  maillage-frequence.
- BEAM2 et les ressorts/masses concentres en dynamique lineaire bornee,
  acceptes le 2 aout 2026.
- TET4 total lagrangien statique dans le domaine borne de sa revue.
- Contact sans frottement en statique lineaire bornee.

## Ce qui fonctionne mais n'est pas encore valide uniformement

- Les campagnes `VNV-*-LINEAR-DYNAMICS-001` couvrent maintenant TET4, TET10,
  MITC3+, BEAM2 et ressort/masse. Elles verifient les residus et
  orthogonalites modales, la vibration libre Newmark contre le cosinus du
  premier mode, et l'identite harmonique/statiques a `0 Hz`.
- Les decisions Owner du 2 aout 2026 sont enregistrees dans
  `qualification/reviews/owner_review_linear_dynamics_2026-08-02.json` et
  synchronisees dans le registre de fermeture. Les exclusions de domaine
  restent applicables malgre cette acceptation bornee.
- Les materiaux orthotropes TET4/TET10 ont des tests modal/Newmark, mais leurs
  scopes dynamiques restent en developpement.
- MITC4 multicouche dispose maintenant d'une campagne interne modal, Newmark
  et harmonique sur `[0/90/90/0]`, avec masse coherente, condensation de
  drilling et contraintes par pli. Cette evidence est `verified_development`;
  une correlation dynamique externe et une Owner review restent ouvertes.
- MITC3+ multicouche dispose maintenant d'un patch membranaire analytique et
  d'une campagne interne modal, Newmark et harmonique sur `[0/90/90/0]`.
  Cette evidence est `verified_development`; une correlation externe par pli,
  un cas courbe et une Owner review restent ouverts.

## Domaines non couverts

- dynamique non lineaire pour toutes les familles;
- non-linearite materiau ou geometrique des coques MITC3+/MITC4;
- grandes rotations TET10;
- contact transitoire, impact et contact harmonique;
- dynamique composite qualifiee;
- PSD, vibration aleatoire et excitation de base qualifiees.

## Ordre de fermeture recommande

1. Completer le raffinement maillage-frequence recommande pour MITC3+, sans
   rouvrir les decisions dynamiques deja acceptees.
2. Correl(er) MITC4 et MITC3 multicouches en dynamique avec un oracle externe,
   puis soumettre ces deux perimetres distincts a une Owner review.
3. Conserver la dynamique non lineaire hors V1; elle exige un projet de
   formulation et de V&V distinct.

## Critere futur de couverture uniforme

Pour chaque couple element/analyse revendique, exiger au minimum : un test
analytique, un invariant numerique, une convergence maillage ou temporelle,
un cas structurel, une correlation externe reproductible lorsque possible,
un rapport Markdown/PDF et une decision Owner datee.

## Campagne commune de dynamique lineaire

Les dossiers `qualification/vnv/linear_dynamic_families/` sont generes par :

```powershell
python .\scripts\run_linear_dynamic_vnv.py --family all
```

Pour chaque famille, le premier mode propre calcule est impose comme condition
initiale. La reponse libre attendue est donc la solution analytique reduite
`q(t)=q_0 cos(2 pi f_1 t)`. Cette reduction teste toute la chaine `M`, `K`,
blocages, reduction des DDL, Newmark et post-traitement temporel sans
introduire un second modele discret a etalonner. En harmonique, une force
proportionnelle a `M phi_1` verifie l'identite avec la statique a `0 Hz`, la
finitude de la reponse et le pic amorti autour de `f_1`.
