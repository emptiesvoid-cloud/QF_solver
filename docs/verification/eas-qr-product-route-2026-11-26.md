# Raccordement local de la tangente QR HEX8 EAS

Le type expérimental HEX8_EAS_EXPERIMENTAL utilise désormais la tangente
et la récupération à facteurs de déformation pondérés. La sélection du type,
les restrictions de matériau et d'analyse, le diagnostic et la politique
d'acceptation exacte restent ceux du lot de consolidation. Le code testé
est 5a5c8412fbf21c818db04b3ede39aa58ec0b9dc8, sur la branche locale
emptiesvoids-cloud/eas-qr-product-route-20261126, issue de
3d2cde2b06a913ac9e0c2e56cb5d7198d7eccb01. La tête distante 0.3.0 a été
vérifiée à c4de3ff6bf4549bf68d34652bcf6fb05e36f43c4.

## Opérateurs

Pour les huit points de Gauss, la racine déviatorique L vérifie
LᵀL = C_dev avec deux lignes normales sans trace et trois lignes de
cisaillement ingénieur. A empile √w L B et H empile √w L M, où B
est la matrice de déformation et M les six modes enrichis centrés en
moyenne. Pour H = QR, l'élimination locale donne
T = −R⁻¹QᵀA et α = T u. La partie déviatorique condensée est
F_d = A + H T. La ligne volumique est
F_v = √(K V) div_moy et la tangente FᵀF, F = [F_d ; F_v].
La force récupérée est FᵀF u, évaluée comme Fᵀ(F u). Les contraintes
emploient ε_q = B_q u + M_q α et
σ_q = LᵀL ε_q + K div_moy(u) I. L'énergie est ||F u||²/2 et la
pression reste moyenne, positive en traction.

Le calcul centre les coordonnées par le premier nœud avant de former les
jacobiens, comme le prototype. La base transversale est reconstruite à
partir des tangentes au centre et six amplitudes sont exprimées dans
cette base. Une rotation ou un changement de cette base exige la
transformation inverse des coefficients pour préserver Mα. L'égalité
des coefficients entre bases locales différentes n'est pas une condition
d'égalité des déformations ou contraintes. Le contrôle de conditionnement
du bloc condensé est conservé. Les échecs QR et les coefficients non finis
produisent une erreur explicite.

Le noyau élémentaire est appelé par GlobalAssembler et par
StressPostProcessor. L'assembleur global garde sa sommation de production.
Le prototype de campagne utilisait un assemblage distinct avec math.fsum.
Les matrices globales et les solutions ne sont donc pas réputées identiques
bit à bit sur cette seule comparaison élémentaire.

## Vérifications

Sur l'élément régulier et l'élément distordu du test produit, à E=1e6 Pa
et ν=0,3 et 0,4999, le script de comparaison a chargé le prototype QR
de la source 16cad564. Les quatre matrices sont identiques en binary64.
Pour le déplacement sinusoïdal testé, l'écart maximal de déformation est
5,43e-20, celui de contrainte 2,85e-14 Pa, et les écarts de force et
d'énergie arrondis sont nuls. Le prototype et le port partagent les
opérateurs géométriques de l'élément ; cette comparaison ne constitue pas
une vérification indépendante complète de la formulation.

Les tests élémentaires vérifient les six mouvements rigides, les patchs
affines réguliers et distordus, la symétrie, les modes projetés et le
résidu du vecteur propre le plus faible. Un témoin utilise un calcul par
moindres carrés indépendant de la factorisation QR du port pour comparer
facteurs, tangente, déformations et énergie. La dérivée directionnelle
est vérifiée par différence centrée. Un test injecte un échec QR. Les
tests de récupération, routage, condensation invalide, refus et assemblage
produit passent sur les cas couverts. Les tests du garde, du diagnostic,
du défaut d'archive, du timeout, de l'interruption, de l'absence de psutil
et de l'acceptation expérimentale passent aussi. Une régression HEX8
standard passe. Ruff et git diff --check passent.

Les empreintes des six archives de comparaison transverse ont été
vérifiées. Les cas quasi incompressibles 8×4×4 et 8×4×6 conservent
PYTEST_FAILED. Les campagnes de recherche ont utilisé l'assemblage et la
récupération injectés du prototype et ne sont pas des résolutions de
cette route intégrée.

## Suite

Une comparaison FEM future requiert un contrat neuf fixant notamment les
deux cas plans 16×4×4 à ν=0,3 et 0,4999, les charges et le relèvement
existants, les critères de bilan préalables, la capture de la matrice
effectivement assemblée, les décisions distinctes du garde et du contrôle
exact ainsi que les champs physiques. Deux scopes, préflights et ledgers
neufs et l'autorisation Owner correspondante seraient nécessaires.
Les écarts de sommation globale, les réactions, le moment et le
post-traitement de u=g+w devront être mesurés. Les éléments minces,
distordus, autres chargements et la stabilité globale restent à étudier.
Le plateau de contrainte associé à la pression moyenne reste présent.

Aucun nouveau FEM ni test CI n'a été exécuté. Les seuils, PYTEST_FAILED,
J7 FAIL et J14 PASS de développement sont préservés.

La wheel construite depuis le commit code 5a5c8412 a pour SHA-256
9a46f13485ed5666ab7cc66698b23e27fddb846839fc1c034070eead80329e6c.
Sous Windows et Python 3.13.1, elle a été installée hors checkout dans
deux environnements isolés. Cinq tests passent avec l'extra eas-diagnostic,
dont le lancement réel d'un enfant spawn et les contrôles d'identité.
Le test d'absence de psutil passe dans l'environnement sans extra. Les
modules sont importés depuis site-packages et research est inaccessible.
Les tests de différentiation supplémentaires utilisent deux directions et
trois tailles de perturbation avec les tolérances antérieures inchangées.
Le commit de rapport et ces tests n'apportent aucun changement au code de
la wheel.

Le commit code final 74a3068609ce73035836bb96bce8b37e0f7e8502 préserve
en outre les coordonnées physiques retournées par recover, après centrage
interne des opérateurs. Un test vérifie ces coordonnées et l'invariance
par translation. La wheel reconstruite depuis ce commit a pour SHA-256
7edabbd757f5d0a952882cca33d77ada39cfe85b0dac116e9bc0bb914881c9b5.
Après installation dans les deux environnements isolés, quatre tests
passent avec l'extra et un sans psutil. Le contrôle des forces par
intégration des contraintes récupérées a également été ajouté au test
élémentaire, sur les deux géométries et valeurs de ν.
