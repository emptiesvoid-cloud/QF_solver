# WP13 — dossier Owner final des smoke tests du candidat v7

**État : `PREPARED_NOT_AUTHORIZED`**  
**Portée de la décision : six calculs installés maximum; aucune qualification globale**  
**PR : #114 · branche `codex/wp13-release-engineering-20261031`**

## Identités exactes proposées

| Élément contrôlé | Identité |
| --- | --- |
| Source package v7 | `7a78cc673da2abb7c3d0afd6cabd378aa327f424` |
| Contrat de build | `QF-0212-WP13-SELECTED-CANDIDATE-20261101-07`; SHA-256 `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43` |
| Smoke controller | `scripts/wp13_package_smoke.py`; SHA-256 `cba01759b5b3b1cc41cfcc23c405adef55a6cccdaffcec85ac4a057b8b7e2ed7`; commit `c3c10f2f30c82550261eeb436df8468614c742e6` |
| Manifeste v7 externe | SHA-256 `e1e86a8c5aae20b687469886f0efa4434769c84d5770538cec93f4a9123a8bd8` |
| Préflight principal | `PASS_NO_FEM_PREFLIGHT`; SHA-256 `a7c2b1f52a8998ce4a45d54a27bacea38b8f86b957d75c5bde5740d0024425e6` |
| Préflight synthétique requis par le runner | `NOT_RUN`; hash `NOT_ACQUIRED` dans ce mandat |
| Wheel installé | 1 690 080 octets; SHA-256 `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518` |
| Sdist normalisée installée | 1 295 214 octets; SHA-256 `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174` |
| Runtime visé | Windows · Python 3.13.1 · QF Solver 0.2.12 |
| HEAD vérifié lors du préflight | `c3c10f2f30c82550261eeb436df8468614c742e6`; branche propre |

Les chemins du manifeste, des environnements et des sorties sont maintenus hors dépôt; ils ne sont pas recopiés dans ce dossier. Les rapports d’installation séparés sont liés par hashes `12c6d1a755d19a53f0418f73b3beda2e15f413716b70d0085c01723c4086ee91` (wheel) et `fb2c839745bcc98f0ab439bd2c07243f4a4b25cf5cdd88df94b758930ee25755` (sdist normalisée).

## Entrées et oracles gelés

Chaque paquet installé contient les mêmes entrées que les blobs source v7. Le préflight principal a vérifié leurs hashes dans les deux environnements.

| Cas | Entrée | SHA-256 |
| --- | --- | --- |
| STATIC-01 | `tet4_static.json` | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` |
| MODAL-01 | `tet4_modal_unit.json` | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` |
| DYNAMIC-01 | `tet4_dynamic_sdof_free_vibration.json` | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` |

Sources d’oracles vérifiées pour la source v7 :

| Source | SHA-256 |
| --- | --- |
| `src/solveur/verification/analytical_references.py` | `38ae37e1ff40844eedf7c2ca5b95d9d03f3fe660670036b05895c5043c96fb6c` |
| `src/solveur/verification/campaign.py` | `ea06968dc65927791549d698d19eeae33b6a3ad3e466ed2da0b87ae45e8952f1` |
| `qualification/campaign.json` | `8750d29a9d52498ec5051f4850c600232b0e7a4515905a8354f4a34771fd92cf` |

Les oracles et tolérances sont ceux du dossier historique [`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md) et des constantes source du controller. Aucun nombre, signe, seuil ou résultat attendu n’a été changé :

- **STATIC-01** : `ux = 2.1224489795918369e-8 m` et contrainte de von Mises `3428.5714285714284 Pa`, tolérances relatives `1e-12`; résidu libre `≤1e-9`; résultante de réaction `−1000 N`, tolérance absolue `1e-10 N`; erreur d’équilibre `≤1e-12`; identité d’énergie linéaire `≤1e-9`.
- **MODAL-01** : première fréquence `1619.5553821068941 Hz`, tolérance relative `1e-12`; résidu propre, orthogonalité de masse et erreur diagonale de raideur `≤1e-10`.
- **DYNAMIC-01** : `k=200 N/m`, `m=1/6 kg`, déplacement initial `0.001 m`, vitesse initiale `0`; énergie attendue `0.0001 J`, tolérance relative `1e-10`; temps d’enregistrement initial `0.001 s`, indice d’historique `39` / pas `40`, durée `0.04 s`; cohérence énergétique absolue `1e-14 J`, dérive énergétique `≤1e-10`, résidu dynamique et résidu libre `≤1e-10`.

## Ordre et limites d’exécution proposées

| Ordre | Couple artifact/cas | Tentatives autorisées |
| ---: | --- | ---: |
| 1 | wheel / STATIC-01 | 1 |
| 2 | wheel / MODAL-01 | 1 |
| 3 | wheel / DYNAMIC-01 | 1 |
| 4 | sdist normalisée / STATIC-01 | 1 |
| 5 | sdist normalisée / MODAL-01 | 1 |
| 6 | sdist normalisée / DYNAMIC-01 | 1 |

- Maximum six tentatives, une par couple; séquentiel et arrêt au premier échec.
- Timeout de 30 s par tentative; stdout et stderr limités chacun à 1 Mio.
- RSS échantillonné avec limite souple à 512 Mio; modèle limité à quatre nœuds et trois DDL libres.
- Aucun retry automatique. Ledger d’essais append-only et outputs persistants hors dépôt.
- Import depuis le package installé seulement; les entrées sont relues depuis les données de chaque installation et leurs hashes revalidés.
- Variables numériques mono-thread contrôlées par le controller. Les checks de préparation n’exécutent ni `solve`, ni assemblage.

Le préflight principal a réussi : les deux paquets sont trouvés dans leur venv Windows/Python 3.13.1; versions et entrées installées concordent; les SHA du manifeste sont valides. Son rapport affirme `execution_authorized=false`, `actual_attempt_reservations=0` et `fem_executed=false`. Le ledger réel n’existe pas et le répertoire d’evidence est vide. Aucun calcul smoke n’a été lancé.

## Approbation Owner encore requise

L’accord de principe précédent ne constitue pas l’autorisation d’exécuter le nouveau candidat v7. Le contrôleur exige également un `synthetic-preflight` no-FEM qui crée un ledger synthétique distinct; ce contrôle n’a pas été lancé sans décision sur cette réservation synthétique. Son hash exact n’est donc pas disponible. Le controller `run-all` n’acceptera qu’une décision Owner explicite liée aux hashes du manifeste, du préflight principal et de ce rapport synthétique.

Pour permettre la progression, l’Owner doit autoriser explicitement le périmètre : **le contrôle synthétique sans FEM décrit ci-dessus, puis, seulement si celui-ci passe et si les identités restent inchangées, les six tentatives exactes de la table**. Le fichier de décision lié au hash synthétique sera préparé à partir de cette autorisation avant toute réservation réelle. En cas de changement d’identité, aucune ancienne autorisation ne s’applique.

Cette autorisation ne vaudrait que pour `EXECUTION_PASS` et `NUMERICAL_ORACLE_PASS` dans les six cas bornés. Elle ne conférerait ni qualification scientifique, ni clôture WP12, ni promotion de maturité, ni autorisation de release, tag, merge ou publication. L’état courant reste `PREPARED_NOT_AUTHORIZED`.
