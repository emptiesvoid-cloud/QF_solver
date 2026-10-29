# WP12-VV3D-ADAPTIVE-20261029-R1 — préparation prospective

**Statut : PREPARATION_AUTHORIZED_EXECUTION_NOT_AUTHORIZED.** Cette préparation ne constitue ni une qualification, ni un manifeste officiel, ni une inscription de nodeid. Aucun solveur, assemblage de charges, eigensolve ou calcul FEM n'a été lancé. Le texte du mandat reçu s'interrompt dans la section budget : sa suite doit être examinée avant tout contrat définitif.

## Proposition de problème indépendant

Sur Ω=[0,1]³ m, E=10⁶ Pa, ν=0,3, petites déformations et élasticité isotrope. Les déplacements des six faces sont imposés à zéro. Pour k=π/m et A=10⁻⁴ m, le champ proposé est u*=(0,0,w), w=A sin(kx) sin(ky) sin(kz). Il est régulier, non affine et nul sur tout le bord. Pour λ=Eν/((1+ν)(1−2ν)) et μ=E/(2(1+ν)), on définit f=−div σ(u*) en N/m³ dans `oracle.py`, indépendamment des éléments QF Solver. Les contraintes, l'énergie analytique ½∫ε:C:ε, la résultante et le moment externes sont fournis par le même fichier. Le signe et la divergence sont vérifiés par différences finies synthétiques ; une quadrature produit indépendante vérifie l'énergie et la résultante.

C'est un problème 3D manufacturé **proposé**, non un porte-à-faux. Il couvre la convergence en volume et les réactions globales, mais pas une application réelle de traction de face ni la flexion d'une poutre. Les quatre formulations et tous les niveaux doivent recevoir exactement la même fonction f, les mêmes BC et les mêmes unités. Un patch affine et un cas de traction de face sont des compléments distincts à inscrire et autoriser séparément. La référence Timoshenko est un indicateur 1D, pas une solution exacte du présent problème ni d'une poutre solide 3D.

Les solutions manufacturées servent à vérifier le calcul des équations et les erreurs de discrétisation ; elles ne sont pas, à elles seules, une validation physique expérimentale ([Sandia, SAND2000-1444](https://www.sandia.gov/research/publications/details/code-verification-by-the-method-of-manufactured-solutions-2000-06-01/), [Aycock et al., 2020](https://doi.org/10.1016/j.compstruc.2019.106175)).

## Matrice préparée

`prepared_20261029/MATRIX_NOT_AUTHORIZED.json` répertorie douze maillages JSON et leurs SHA-256. Coordonnées entières divisées par 2n, connectivité 0-based, arêtes quadratiques partagées. Géométrie affine pour les quatre familles ; les tétraèdres sont six partitions conformes de chaque cube. Les indices d'arêtes HEX20 et TET10 suivent les sources du dépôt. Les déterminants affichés sont les valeurs analytiques de géométries affines droites, pas des résultats d'un audit FEM ni une preuve sur des géométries déformées. Ces empreintes identifient les fichiers préparés, mais ne constituent pas un gel Owner des sources ou de la campagne.

| Élément | L1 éléments / DDL | L2 éléments / DDL | L3 éléments / DDL |
|---|---:|---:|---:|
| TET4 | 48 / 81 | 384 / 375 | 3 072 / 2 187 |
| TET10 | 48 / 375 | 384 / 2 187 | 3 072 / 14 739 |
| HEX8 standard | 8 / 81 | 64 / 375 | 512 / 2 187 |
| HEX20 | 8 / 243 | 64 / 1 275 | 512 / 8 019 |

Les trois niveaux correspondent à n=2,4,8 dans chaque direction et ont tous des DDL libres. La numérotation et les DDL contraints précis sont enregistrés dans chaque fichier. HEX8 est à intégration complète, sans substitution SRI. Géométrie, f et BC sont communs ; la discrétisation nodale de f dépendra de l'interpolation mais doit converger vers le même chargement continu.

`MESH_QUALITY_REPORT.json` relie chaque mesure au SHA du maillage : ratio moyen tétraédrique minimal 0,75595 et rapport d'aspect inverse des briques égal à 1 pour cette famille régulière. Les Jacobiennes affines sont positives. L'outil refuse notamment les milieux d'arête déplacés plutôt que d'étiqueter une géométrie quadratique déformée comme affine. Ces contrôles ne caractérisent pas les maillages courbes ou distordus.

## Observables et critères à geler

Par cas : déplacement intégral L², erreur en norme d'énergie (intégration indépendante convergée), déformations et contraintes comparées au champ exact, énergie, travail, résidu libre, réactions, fermeture de résultante et de moment, origine du solveur, temps et RSS. Les dénominateurs des erreurs relatives doivent être explicites et non nuls. Conserver les valeurs brutes et les unités ; ne pas utiliser le résidu comme oracle de précision. Les ordres observés nécessitent les trois niveaux et un régime asymptotique ; les normes, quadratures d'évaluation, incertitudes de référence et seuils bloquants doivent être définis et approuvés avant calcul. Les maxima de contrainte ne suffisent pas à caractériser la convergence.

## État opérationnel et blocages avant exécution

`load_assembly_draft.py` contient l'intégration cohérente candidate `∫Nᵀ f dV` pour TET4, TET10, HEX8 et HEX20 sur les géométries affines préparées. Son entrée publique exige un validateur de permis fourni par le contexte du runner; le cas préparé appelle cette entrée après validation du reçu. Aucune intégration FEM réelle n'a été lancée sous cette préparation, et cette voie n'a donc pas encore été validée par une résolution du solveur. Les quadratures de chargement d'ordre 8 et 12 restent des observables comparatives à mesurer, pas une exactitude présumée. `model_draft.py` reste un générateur de gabarit documentaire incomplet; le cas d'exécution construit séparément un `FiniteElementModel` après contrôle du runner et de la charge intégrée.

Le contrôleur VV3D canonique et son scope sont intégrés et désignés par l'`AGENTS.md` de la branche `emptiesvoids-cloud/0.2.12`. Les inscriptions exactes couvrent les 12 nodeids initiaux, huit candidats FEM adaptatifs fermés et quatre nodeids QPOST. Le ledger/runner applique le plafond prospectif global et les préconditions de provenance, mais aucune décision globale Owner, aucun préflight pour les nouvelles identités scientifiques, aucun manifeste final ni aucune réservation n'existe. Les modifications d'une source scientifique ou du catalogue invalident les artefacts source-liés antérieurs. Les 24 tentatives/28 800 s restent un plafond de préparation partagé, non une autorisation.

Le postprocesseur `field_error_draft.py` calcule les normes de champ avec des fonctions de forme, mappings et règles de Gauss propres; il ne réutilise pas `basis.py`, `sampling.py` ou `quadrature.py`. Il prend comme référence le champ analytique de `oracle.py`, donc l'indépendance est vis-à-vis de l'opérateur discret et des outils candidats du solveur, pas une seconde implémentation externe de l'oracle. Le résidu relatif du sidecar reprend exactement la valeur `free_relative_residual` produite par l'audit statique du solveur, avec son dénominateur réduit et son plancher de 1 N; la norme absolue est aussi conservée. Les tests synthétiques vérifient des champs fabriqués et ne constituent pas un test d'assemblage réel.

## Revue indépendante du snapshot b4ac817

- TET4 : P1 à gradient constant ; le test cité par une inscription historique est absent dans ce checkout. La raideur en flexion et le verrouillage sont à caractériser, non à présumer.
- TET10 : arêtes globalement partagées, Hammer 4 points pour géométrie droite ; l'ancien convertisseur conserve des charges nodales de coin mais ne crée pas une traction quadratique cohérente.
- HEX8 standard : 2×2×2 complet ; contrôle de Jacobien aux points d'intégration seulement pour les géométries générales. Descripteur et registre ne sont pas équivalents pour toutes les familles de matériaux.
- HEX20 : 3×3×3 volumique ; QUAD8 surfacique corrigé. Le diagnostic R2-CORE et son autorisation éventuelle sont indépendants de cette campagne. L'exactitude des faces courbes reste non établie.
- Auditeur : le patch affine ne prouve pas la convergence ; égalité des résultantes ne prouve pas une distribution de charge équivalente ; norme de champ et intégration indépendante sont nécessaires. Une autre solution manufacturée polynomiale peut servir de patch mais sera exactement représentable par les éléments quadratiques sur géométrie affine, et donc insuffisante seule pour établir leurs pentes.

Les audits portaient sur l'instantané `b4ac817cdb565c45f8f8d92a9c10bbb609f6df37`, pas sur un solveur exécuté. Les outils de délégation ont sélectionné le modèle `gpt-6-luna` demandé ; l'identité effective des runtimes des sous-agents n'a pas été attestée indépendamment.
