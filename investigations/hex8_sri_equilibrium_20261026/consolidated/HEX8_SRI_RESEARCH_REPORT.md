# HEX8-SRI — rapport scientifique de recherche

**État : `EXPERIMENTAL_GLOBAL_PASS_BOUNDED`**

**Convergence spatiale actuelle : `SPATIAL_CONVERGENCE_NOT_ASSESSED`**

**Recommandation : `RESEARCH_ONLY`**

## 1. Résumé exécutif

Le défaut historique est une omission exacte du poids `8` pour l’intégration volumique au point central de `[-1,1]³`. Sur un cube affine et un champ de déformation constant, ce défaut divise exactement l’énergie volumique par huit. Le correctif applique ce poids explicitement; le test analytique échoue sur le source historique et passe sur le source corrigé. L’opérateur déviatorique ne change pas.

Les six calculs globaux archivés et vérifiés sont PASS selon leurs critères gelés, sur un seul maillage `4×2×2`. À `ν=.4999`, le HEX8 standard est environ 7,2 fois plus raide en déplacement moyen que les SRI sur ce cantilever; cela suggère un verrouillage volumétrique du standard dans ce cas. Le conditionnement du SRI corrigé atteint `8,59e8`. Aucun de ces chiffres ne qualifie la précision générale. Le maillage grossier donne environ 3 mm de déplacement SRI, loin de l’ordre de grandeur Timoshenko 32 mm.

## 2. Problème initial et historique

HEX8-SRI sépare intégration déviatorique complète `2×2×2` et intégration volumique au centre. L’expression source initiale omettait le poids du point central. Le correctif scientifique est conservé dans `research/hex8-sri-equilibrium`; la branche release v0.2.12, le registre public et le solveur public n’ont pas été modifiés. Une reproduction historique, locale et explicitement figée du terme sans poids sert uniquement de contrôle comparatif.

## 3. Formulation théorique

Pour `m=(1,1,1,0,0,0)ᵀ`, `κ=E/[3(1−2ν)]`, `Cvol=κmmᵀ` et `Cdev=C−Cvol`, le code utilise `Kdev=Σ₈ detJ BᵀCdevB` et `Kvol=8detJ₀B₀ᵀCvolB₀`. L’audit des opérateurs et transformations est dans [THEORY_AND_FORMULATION_AUDIT.md](THEORY_AND_FORMULATION_AUDIT.md).

## 4. Défaut du facteur 8

La règle de Gauss produit-tensorielle a huit poids unitaires; le volume de référence vaut 8. Le point centre requiert le poids produit `2³=8`. Pour le cube unité physique, `detJ=1/8`, `u=x`, `ε=I`, la référence indépendante est `Uvol=9κ/2`; l’ancien opérateur donne `9κ/16`; le corrigé donne `9κ/2`. Les énergies `468.75` et `3750 J` au cas `E=1000 Pa,ν=.3` sont archivées. Ni `detJ`, ni `B`, ni `Cvol` ne contiennent un facteur compensatoire.

## 5. Correctif

`Hex8SRIElement.volumetric_integration_weight=8.0`; `volumetric_stiffness()` multiplie explicitement le terme central par ce poids. À l’échelle locale contrôlée, `Kvol,corr=8Kvol,hist`, `ΔKdev=0`, `ΔKtotal=ΔKvol`. Le SRI corrigé n’est pas identique à HEX8 complet, qui évalue aussi `Cvol` aux huit points.

## 6. Protocole expérimental

Le cas autorisé était apparié : poutre `20×1×1 m`, maillage régulier affine `4×2×2`, 16 éléments, 45 nœuds, 135 DDL dont 27 bloqués, `E=1 MPa`, trois formulations, deux `ν`, charge résultante `(0,0,−1) N`. Les mêmes solveur, conditions aux limites et répartition cohérente de charge ont été utilisés. Les six identifiants et les hashes de tous les manifests/reçus sont dans l’index et le CSV.

## 7. Résultats historiques conservés

Les six `run.json` sont PASS, code retour zéro, tentative 1. Les hashes des six NPZ et sidecars correspondent. Les reçus de préflight sont liés depuis les runs. Les sources et origines de solveur concordent avec le fingerprint. Aucun artefact ne manque dans les 12 fichiers de l’archive de calcul. L’index global comprend aussi les scripts et traces de preuve analytique.

## 8. Analyse comparative

Le déplacement signé moyen (`mm`) est : à `ν=.3`, standard `−2.991477`, historique `−3.161814`, corrigé `−3.036130`; à `ν=.4999`, `−0.474211`, `−3.411156`, `−3.410621`. À `.3`, le correctif change le déplacement corrigé de `−3.98 %` versus historique; à `.4999`, de `−0.0157 %`. Les différences de `K` et `u` globaux archivés sont données par paires dans `FORMULATION_PAIRWISE_DIFFERENCES.csv`; les valeurs élémentaires de `Kdev/Kvol/Ktotal` sont au §4 et dans la preuve JSON indexée.

## 9. Sensibilité à `ν`

`κ/μ` passe de `2.1667` à `.3` à `4999.6667` à `.4999`. Le déplacement HEX8 standard chute tandis que les deux SRI restent proches dans ce cas. C’est compatible avec une contrainte volumique excessive du standard, mais une référence 3D indépendante et un raffinement apparié sont nécessaires pour conclure à un verrouillage/précision comparée.

## 10. Conditionnement et stabilité

`cond₂(Kff)` à `.4999` vaut `1.15e8` (standard), `1.08e8` (historique) et `8.59e8` (corrigé); à `.3`, les valeurs sont `6.33e5`, `3.11e5`, `6.01e5`. Les matrices restent finies et symétriques à la précision observée. Les résultats historiques de modes sur l’élément affine sont référencés séparément; aucune stabilité spectrale sur distorsion n’est démontrée ici. Une analyse de modes future est différée et requiert autorisation distincte.

## 11. Équilibre, résidus et énergie

Résidus libres relatifs : `3.18e−12` à `4.65e−9`. La fermeture de force maximale est `1.75e−8`, de moment `1.24e−8`. Les énergies et travaux ont été recalculés des matrices archivées et concordent aux valeurs enregistrées. La mesure sans dimension correcte est `|2U−W|/|W|`, maximum `3.13e−9`. Le champ sidecar `energy_defect_normalized` n’est pas une mesure normalisée (dénominateur minimal 1 J); les preuves historiques ne sont pas modifiées. La campagne n’avait pas de seuil additionnel énergie/équilibre.

## 12. Limites de validité

Un seul maillage, un cas global, un matériau isotrope élastique linéaire, deux valeurs de `ν`, géométrie affine, aucune validation non linéaire/dynamique/contact, aucune convergence globale et aucun corrélation industrielle. Le contrôle Jacobien est échantillonné, pas certifié en tout point pour une géométrie distordue. Le run ne lie pas cryptographiquement les hashes du sidecar/NPZ directement dans `run.json`. Tous ces points sont détaillés dans [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## 13. Plan de convergence spatiale

Quatre niveaux all-axis `4×2×2`, `8×4×4`, `16×8×8`, `32×16×16`; trois formulations × cinq `ν` donnent 60 cas préparés. Le premier lot réduit de convergence comprend 24 cas : les trois formulations pour `ν=.3` et `.4999`, aux quatre niveaux. Le pilote creux et les nodeids sont préparés, mais ils ne sont pas inscrits au contrôleur courant; aucun de ces cas n’a été préflighté ou exécuté. Le budget maximal proposé est 8,3 h séquentielles, une tentative par cas, jusqu’à 3 600 s et 16 GiB RSS souple au niveau fin. Voir [le protocole du premier lot](FIRST_CONVERGENCE_CAMPAIGN.md). La matrice complète demeure dans `../NEXT_CAMPAIGN_MATRIX.csv`; la matrice complémentaire prépare 115 contrôles analytiques, de géométrie, distorsion et stabilité (`../SUPPLEMENTAL_VALIDATION_MATRIX.csv`). Rien de nouveau n’est inscrit ou autorisé.

## 14. Vérification indépendante nécessaire

Pour la section carrée `1×1 m`, le chargement uniforme de face donne le même résultant centroidal de `1 N`, et l’observable de face QF est une moyenne Q1 de `UZ` correspondant au déplacement d’axe dans l’hypothèse de poutre à sections planes. Timoshenko prédit `32,0624 mm` à `ν=.3` et `32,0720 mm` à `ν=.4999` avec `k=5/6`; le facteur rectangulaire de Cowper change ces totaux de moins de `0,002 mm`. Le rapport `h/L=1/20` rend la théorie utile pour l’échelle et la tendance, mais les effets de bout 3D et le maillage grossier empêchent d’en faire un seuil d’erreur serré. Les `3–3,4 mm` archivés imposent une étude de convergence; ils ne justifient pas de considérer la formulation la plus souple exacte. La référence de précision recommandée reste un calcul 3D mixte indépendant, à qualifier sous raffinement; son backend n’est pas encore installé ou fingerprinté.

## 15. Risques d’intégration

Verrouillage standard, stabilité/heureglass sous distorsion, conditionnement près de `ν=.5`, erreur quadrature pour géométrie non affine, cancellation dans `C−Cvol`, unités/normalisation d’énergie, régressions API et élargissement implicite de portée sont suivis dans `INTEGRATION_RISK_MATRIX.csv`. Une intégration demanderait une campagne indépendante, all-axis, patch/énergie, distorsion certifiée, comparaisons avec référence, spectre avant/après, contrôles logiciels et gate Owner/qualification séparés.

## 16. Recommandation scientifique

Garder le correctif au statut `RESEARCH_ONLY`. Le facteur 8 est démontré et les six observations structurelles sont reproductibles/bornées; aucune maturité générale ni intégration v0.2.12 n’est recommandée. Voir Q1–Q5 ci-dessous.

## 17. Statuts des cinq questions

| Question | Statut | Conclusion bornée |
|---|---|---|
| Q1 énergie volumique corrigée | `PARTIALLY_SUPPORTED` | Exacte sur le cube affine à déformation constante; géométrie non affine pas généralement exacte au centre unique. |
| Q2 réponse quasi incompressible et stabilité | `PARTIALLY_SUPPORTED` | Changement cohérent avec le relâchement du verrouillage sur un cantilever; conditionnement élevé, étude de modes/distorsion incomplète. |
| Q3 convergence spatiale | `PARTIALLY_SUPPORTED` | WP10 historique rapporte une tendance 4/8/16; six cas présents `NOT_ASSESSED_SINGLE_MESH`, pas de convergence 3D indépendante. |
| Q4 maillages déformés/aniso/non structurés | `INCONCLUSIVE` | Quelques mesures historiques bornées; famille `stretched` dupliquée et Jacobien non certifié partout. |
| Q5 conditions d’intégration | `PARTIALLY_SUPPORTED` | Les portes minimales sont spécifiées; leurs preuves n’existent pas et la décision reste `RESEARCH_ONLY`. |

Statut transversal : `EXPERIMENTAL_GLOBAL_PASS_BOUNDED`; convergence spatiale de la campagne actuelle : `SPATIAL_CONVERGENCE_NOT_ASSESSED`.

## 18. Bibliographie et références internes

Références techniques : Sandia [Sierra/SD Theory Manual](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf), [Sierra/SM User Manual](https://www.sandia.gov/files/sierra/SM_Users_5_30/user_manual/elements/sections.html), Hughes (1980) [doi](https://doi.org/10.1002/nme.1620150914), Belytschko & Bindeman (1993) [doi](https://doi.org/10.1016/0045-7825(93)90124-G). Références internes : [audit théorique](THEORY_AND_FORMULATION_AUDIT.md), [rapport de l’incident et preuve analytique](../report.md), [rapport WP10](../../../docs/verification/0_2_8/wp10_hex8_sri_vnv.md), protocole WP13-12 et runner historique indexés dans la provenance.

## 19. Index des preuves et empreintes

Les 71 pièces sources sont indexées dans `EVIDENCE_INDEX.json`, y compris six manifests, six préflights, reçus calcul, logs, six sidecars, six NPZ, scripts et résultats du test analytique. Les SHA-256 sources sont dans `SHA256SUMS.txt`; les SHA des sidecars/NPZ sont en colonnes de `SIX_CASES_RESULTS.csv`. Les figures SVG sont reproductibles avec `tools/hex8_sri_research/build_consolidated.py` à partir des NPZ contrôlés.

## 20. Poursuite de recherche — vérification au 2026-10-27

Les anciennes 71 pièces et les douze fichiers des six runs restent intactes; les preuves gardent leurs identités et statuts d’origine. Un pilote sparse gardé et un oracle analytique Timoshenko/Cowper ont été ajoutés, ainsi qu’un post-traitement indépendant des solveurs pour les sidecars futurs. Dix-huit nodeids unitaires ciblés, exécutés individuellement, passent (26 tests avec paramètres ou cas directs), y compris les cinq contrôles géométriques purs. Sept géométries ont aussi été inspectées à neuf points d’intégration/contrôle par élément; elles sont toutes échantillonnées positives, sans certificat volumique continu ni résultat mécanique. Ruff, le contrôle de format et l’analyse AST passent. Aucun test FEM de convergence, assemblage global, solve ou eigensolve nouveau n’a été lancé.

Le contrôleur officiel `0d6286ec…` n’inscrit actuellement que les six nodeids de la campagne structurelle précédente, avec 180 s / 1 024 MiB par cas; ses validations exigent exactement six manifestes et ce module de test. Il faut une extension de configuration dédiée, préservant les autres scopes, avant de produire des préflights valides pour les 24 nouveaux nodeids. La demande est préparée dans `../campaign_preparation/first_convergence_24/CONTROLLER_EXTENSION_REQUEST.md`; le chemin du manifeste doit être passé au child exclusivement depuis le binding contrôleur.

Un oracle numérique 3D mixte indépendant manque encore : aucun backend n’est installé ou fingerprinté dans l’environnement vérifié. Les comparaisons à Timoshenko resteront des écarts de tendance, et la précision en continuum ne pourra être qualifiée avant la vérification indépendante de cette référence. Le statut scientifique demeure `EXPERIMENTAL_GLOBAL_PASS_BOUNDED`, la convergence actuelle `SPATIAL_CONVERGENCE_NOT_ASSESSED`, et la recommandation `RESEARCH_ONLY`.

Les outils de préparation sont maintenant commités à `7ff2809a854e1434619c261195e78b901be0ea78`, fingerprint `1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555`. Vingt-quatre manifests brouillons sont calculés et leurs SHA vérifiés; tous restent non autorisés. La demande d’extension contrôleur et de décision Owner est indexée dans `../campaign_preparation/first_convergence_24/drafts/OWNER_DECISION_REQUEST.md`. Aucun préflight ou calcul nouveau n’a été lancé.
