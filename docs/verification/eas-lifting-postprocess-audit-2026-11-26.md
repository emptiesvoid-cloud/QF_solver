# EAS : post-traitement et relèvement externe

La route EAS ne possède pas d'entrée de relèvement volumique. Dans les
campagnes, le worker construit g, assemble K, applique la charge modifiée
f−Kg au modèle avec appuis nuls, résout pour w, puis calcule séparément
u=g+w et son post-traitement. L'API n'est pas informée de g. Elle retourne
et exporte donc le résultat du modèle transformé w. Un appelant qui traite
ce résultat comme u obtient des déplacements et contraintes incorrects.
Cette confusion est possible avec ce montage externe ; l'API ne peut pas
déduire un relèvement d'une charge nodale ordinaire.

Le solveur statique construit normalement un déplacement par
ConstraintReduction.expand, puis transmet ce même vecteur à l'audit,
aux résultats élémentaires et nodaux et à SolveResult.displacements. La
réduction générale peut inclure un offset de contrainte multipoint.
L'élément EAS refuse toutefois les MPC, RBE et autres options indiquées
dans son contrôle de portée. Ses fixed_dofs représentent des valeurs
nulles. Une valeur non nulle sur fixed_dofs dans un document JSON est
refusée par le schéma. Avant ce correctif, FiniteElementModel.from_raw
ignorait silencieusement un champ value pour une entrée EAS. Il refuse
désormais tout champ supplémentaire dans une condition EAS, avec un
message indiquant que les appuis imposent uniquement zéro. Le traitement
des autres familles n'est pas modifié.

Il n'existe pas d'argument displacement_lift dans from_raw ou dans le
schéma JSON. Les deux interfaces refusent cette clé lorsqu'elle leur est
soumise directement. Le dictionnaire libre de paramètres d'analyse ne
constitue pas une API de relèvement et aucun nom arbitraire n'est
interprété comme tel. Pour prendre en charge officiellement un
relèvement, il faudrait une API et un contrat définissant notamment
le champ, les charges, les réactions et le déplacement physique à
exporter. Ce travail dépasse le présent correctif.

## Rejeu hors ligne

Les NPZ de la campagne QR 16×4×4 ont été vérifiés par SHA-256.
Sur le premier élément des deux archives, u=g+w est vérifié et la
récupération de u reproduit exactement les contraintes archivées.
Avec w seul, les écarts suivants apparaissent :

| ν | Norme de l'écart de contrainte aux huit points (Pa) | Écart des six amplitudes | Énergie u / w (J) | Écart de force interne (N) |
|---|---:|---:|---:|---:|
| 0,3 | 4,2855 | 8,1565e-7 | 7,5855e-10 / 6,8632e-13 | 2,6601e-3 |
| 0,4999 | 4,2832 | 8,7343e-7 | 7,4916e-10 / 4,4398e-13 | 2,6599e-3 |

Ce contrôle utilise l'élément réel et les coefficients archivés. Il
partage le noyau de récupération avec la campagne et ne résout aucun
système. Les réactions physiques doivent utiliser Ku−f. Pour le montage
du worker, si la charge effective complète f−Kg est bien appliquée sur
tous les DDL, Kw−(f−Kg) est algébriquement égal à Ku−f. Cette identité
a été testée élémentairement et ne transforme pas les contraintes ou
les déplacements w en champs physiques. L'API calcule les réactions
pour les entrées réellement reçues. Les exports VTU et CSV utilisent
les déplacements du résultat ; le VTU utilise aussi les résultats
élémentaires fournis. Un résultat w exporté donne donc w et ses champs.

## Tests et décision

Les tests sans FEM vérifient le refus de fixed_dofs avec value via le
constructeur Python EAS et via le lecteur JSON, le refus de MPC dans la
portée EAS, le refus d'une clé explicite de relèvement inconnu, les
appuis nuls et le maintien du comportement du constructeur HEX8. Pour un
déplacement synthétique non nul, StressPostProcessor et le noyau
élémentaire réels distinguent u et w. La récupération des contraintes,
des amplitudes, des forces et de l'énergie est vérifiée, ainsi que le
contenu VTU par lecture XML pour EAS et HEX8. Le test du chemin accepté
de LinearStaticSolver utilise des doubles pour l'assemblage et la
résolution et vérifie que le vecteur retourné est transmis au
post-traitement. Le test de réduction MPC général est algébrique.

Le cas transformé reste un montage externe à traiter explicitement par
l'appelant. La documentation décrit sa portée et le refus de saisie
ambiguë. Aucun FEM n'a été lancé. Les seuils et verdicts historiques
PYTEST_FAILED, J7 FAIL et J14 PASS de développement sont préservés.
