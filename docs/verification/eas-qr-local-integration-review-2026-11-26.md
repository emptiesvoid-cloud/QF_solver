# Revue d'intégration locale HEX8 EAS–QR

Décision A. Le lot est intégré dans une branche locale isolée à titre
expérimental, avec sélection explicite de l'élément et options exactes
désactivées par défaut. La comparaison contrôlée couvre deux cas plans
et ne constitue pas une qualification générale.

## Identité du lot

La tête distante refs/heads/0.3.0, vérifiée directement, est
c4de3ff6bf4549bf68d34652bcf6fb05e36f43c4. La référence de suivi locale
origin/0.3.0 pointait vers c16d8f1d et n'a pas été modifiée. La branche
produit locale est emptiesvoids-cloud/0.3.0-eas-qr-review-20261126.
Le SHA de code vérifié est 75d3607156334c92cdf5c43f972406aa48b5b2a6,
atteint par avance rapide depuis la tête distante.

L'élément et le diagnostic proviennent de 00195b8b, l'acceptation
expérimentale de 0ee6fead, la tangente QR de 5a5c8412 et le maintien
des coordonnées physiques de 74a30686. Les tests additionnels de
force–contrainte sont dans 75d36071. Le lot inclut NumPy et SciPy déjà
requis par le projet, avec psutil optionnel via eas-diagnostic.

La source des deux calculs contrôlés est
3b27f67203bc465885def2e563e5cf412f2fffcd. Son unique différence sous src
par rapport à 75d36071 est l'ajout du validateur de l'archive d'étude.
Les contrats, workers, contrôleurs, ledgers et archives brutes de cette
campagne restent dans leurs espaces de recherche. Ils ne sont pas
importés dans le lot produit.

## Vérification des preuves et portée

Les deux contrats, préflights, ledgers, captures de garde et archives
mécaniques ont été validés depuis leurs chemins locaux. Chaque ledger
contient une tentative et les deux runners sont PASS. Les empreintes des
archives NPZ sont :

- ν=0,3 : e976658f0f9a3bf264e91b1f34c86498bb9da203272112d6dbdcca35b9a9b231.
- ν=0,4999 : a79f76a6f2f620b9c8541e301effb9cde69bfc302f1b3c120efde0907c9c334d.

Le préflight est pf-20261126c001 pour le premier et pf-20261126c002
pour le second. Leurs empreintes et les SHA des ledgers figurent dans le
rapport de campagne. Le garde a accepté le premier candidat. Pour le
second, il a rejeté le candidat initial et l'option explicitement activée
a accepté un candidat après une correction LU et un PASS exact.
Le verdict historique du garde reste REJECTED. Les deux archives
présentent des erreurs L2 de contrainte analytiques de 15,515 % et
16,361 %. Le contrôle exact concerne le système binary64 stocké.

La pression récupérée est K fois la divergence moyenne. Le noyau récupère
les six variables enrichies et utilise les facteurs condensés dans la
rigidité, les forces et l'énergie. Les limites de pression constante dans
l'épaisseur et de sensibilité près de ν=0,5 demeurent. Le traitement de
l'essai à relèvement récupère séparément le champ physique u=g+w.
L'API y post-traite automatiquement la variable w. Les archives de
campagne ne prouvent pas que toutes les configurations d'appuis et de
relèvement sont prises en charge de manière équivalente.

L'option de diagnostic exact conserve le rejet historique. L'option
distincte d'acceptation expérimentale peut utiliser un candidat vérifié
si elle est explicitement sélectionnée et conserve séparément les deux
décisions. FAIL, INCONCLUSIVE et les erreurs des moyens de supervision
conservent le rejet. La surveillance RSS est échantillonnée et le
watchdog commence après le démarrage synchrone de l'enfant. Aucun quota
OS strict ni garantie de nettoyage de descendants arbitraires n'est
établi.

## Tests et installation

Le lot code a été rejoué avec les tests ciblés d'activation, de
condensation, des mouvements rigides et patchs, de cohérence
force–tangente, du post-traitement et des refus de portée. Les tests des
garde, diagnostic, acceptation, échecs et régressions HEX8 et SRI
sélectionnés passent. Les tests de route statique utilisent des doubles
pour certaines phases d'assemblage et de résolution. Les tests
élémentaires et le lancement spawn du vérificateur utilisent les
composants réels. Ruff et git diff --check passent.

La wheel construite depuis 75d36071 a le SHA-256
2422d84846f9c279defea8c265ca058f4e21ba5ec6eb0f4e1c947e19c24f54f9.
Son contenu décompressé est identique à la wheel précédemment construite
depuis 74a30686, dont le SHA-256 de conteneur diffère.

Sous Windows/Python 3.13.1, la wheel a été installée dans deux
environnements isolés hors checkout. Neuf tests passent avec l'extra,
dont le lancement réel d'un enfant spawn, l'archive altérée, les
interruptions et le rejet conservé après PASS exact. Un test passe sans
psutil et vérifie la conservation du rejet. Les imports proviennent de
site-packages et research est inaccessible.

Les objets du lot ont été examinés dans le diff produit. Aucun import
research, chemin personnel ou archive brute n'a été trouvé. Les
contrôles de contenu concernent les fichiers ajoutés ou modifiés par
rapport à la base, et les archives restent locales dans les contrôleurs.

Aucun nouveau FEM, test CI, push, fusion vers main, tag, release ou
publication n'a été réalisé. Les verdicts PYTEST_FAILED, J7 FAIL et
J14 PASS de développement restent attachés à leurs archives. Une
validation sur d'autres distorsions, chargements, élancements et niveaux
de raffinement reste nécessaire avant toute conclusion générale.
