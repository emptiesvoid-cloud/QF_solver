# WP12 dynamique — clôture bornée de la sous-campagne

**État de la sous-campagne :** CLOSED_BOUNDED
**Portée :** trois expériences de développement WP06/Newmark, WP05 harmonique direct/réduit et WP07 accélération de base.
**Qualification globale WP12 :** inchangée par ce rapport. Aucun statut général WP05/WP06/WP07 ni aucune qualification physique ou formelle n’est attribué.

## Synthèse pour la matrice WP12

Cette synthèse est destinée aux lignes DYN-05-01, DYN-06-01 et DYN-07-01 de qualification/0_2_12/wp12_preparation/wp12_capability_evidence_matrix.tsv. Elle qualifie uniquement la campagne de développement bornée :

| Ligne | Résultat à reporter pour cette sous-campagne | Limite à conserver |
|---|---|---|
| DYN-05-01 — réponse harmonique réduite | DEVELOPMENT_PASS_BOUNDED : route à base complète équivalente à la route directe à la précision machine sur les six fréquences mesurées. | La base tronquée à deux modes donne une réponse nulle à la sonde UX sur ce fixture; ce résultat ne donne aucune borne générale d’erreur ROM. |
| DYN-06-01 — Newmark modal | DEVELOPMENT_PASS_BOUNDED : ordre fixe-final observé proche de 2 pour u, v et a; les critères existants sur ordre de u, résidu et énergie passent. | Un seul DDL axial libre, fixture BEAM2, réponse libre non amortie; critères d’acceptation v/a absents. |
| DYN-07-01 — accélération uniforme de base | DEVELOPMENT_PASS_BOUNDED : signes, phases, relations cinématiques, repères et round-trip de sérialisation cohérents sur le fixture. | Un axe et une coordonnée libre; à DC, déplacement/vitesse absolus indisponibles; aucun modèle multi-support ou validation physique générale. |

Le statut WP12 global reste hors de cette décision documentaire. Le contenu ci-dessus ne convertit pas ces résultats en points officiels, en qualification formelle ni en validation expérimentale.

## Identités et enveloppe

- Branche scientifique : codex/wp12-dynamic-harmonic-verification
- HEAD scientifique des trois exécutions : d9deddbd6b42467c5fdc9e278bd54e97605f5738
- Empreintes source : Newmark 65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8; harmonique bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c; accélération de base 969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6.
- Contrôleur : HEAD cbdd54aadbb640a96c6b6b5b9726e1247da36012; fingerprint 95d9e4c8ccce76216f7580f6f9e780820772aa0dc4764aaf11a154f270266fb5.
- Une tentative autorisée par cas, 300 s maximum par tentative, un cas FEM par tentative. Les tentatives ci-dessous n’ont pas dépassé 5,75 s.

Les décisions Owner sont enregistrées séparément dans chacun des manifestes autorisés. Le SHA préparé approuvé est suivi du SHA final du JSON après enregistrement de la décision Owner.

| Cas / nodeid exact (DDL) | Manifeste autorisé — SHA préparé → SHA final | Reçu d’exécution — SHA-256 | Sidecar — SHA-256 | Résultat / coût |
|---|---|---|---|---|
| Newmark — tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables (1) | wp12-dyn-newmark-005-d9deddb; 4b90accbe303ba5d2c5480a67866f89105304b708522d66ead06b1b0d292af21 → 374f275f360e41cfe259b8e6d53c35bc33f57f47b329850878ca82dfb860a0d7 | c5cf85dbe107e56d8eb1d404dada0c0ee5c98446b43a895d43fbec8283a26800 | 7155c3a382fbe4edb8a3bb5ec5d3fde07061140c2e52b7654bad10db59a0e1e8 | PASS; 5,744 s; RSS max 162 664 448 octets |
| Harmonique direct/réduit — tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation (3) | wp12-dyn-harmonic-003-d9deddb; 796c6bd8d1a25933046a4b6e392b806681b35b7a294f4e95473624e3afd0aaaa → a3f59422d2c2d18ff79875563c271fc9ec839cd1f95907fbd2af20658d218d8e | 108d546343bbcbf0b8c29a366d5a595f278733669fa4253d69706f5fd9173e47 | 93b7fcef37b9d60eb18062509d3b391cda7b177f1f6c520f694564c7b813e6f1 | PASS; 5,506 s; RSS max 165 998 592 octets |
| Accélération de base — tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization (1) | wp12-dyn-base-003-d9deddb; 57abda38cdfa0fd94d0ab5f4182fa8bf380f5039f1cdb192cb4d5b8d0e32aef9 → 41117c95c613e17c509f32fd08f5a3fa1a025033c16739ebe96f04051e19b87d | a6cb38b8e6161e70d6648d51df31276a78251566715ecb96cfd37fa959c89a73 | 52485089a58d37200630f37b91296c55c1cb0d66f7c9cbbb5cb056d00fe218e2 | PASS; 4,050 s; RSS max 134 672 384 octets |

Le reçu d’exécution est run.json sous le répertoire de tentative. Pour les trois cas, le contrôleur a relu le sidecar et inscrit son nom, sa taille et son SHA-256 dans output_inventory; les valeurs de la table correspondent à cet inventaire. Les manifestes, reçus et sidecars sont dans la racine de preuves locale E:/QFSolverAgents/evidence/dynamics/ :

| Cas | Manifeste Owner | Reçu run.json | Sidecar JSON |
|---|---|---|---|
| Newmark | authorizations/wp12_dynamics/wp12-dyn-newmark-005-d9deddb.json | worktrees/wp12_dynamics/dev-74c6cb1e73a1/attempt-0001/run.json | worktrees/wp12_dynamics/dev-74c6cb1e73a1/attempt-0001/output/wp12-newmark-fixed-time-observables.json |
| Harmonique | authorizations/wp12_dynamics/wp12-dyn-harmonic-003-d9deddb.json | worktrees/wp12_dynamics/dev-7b5e16653765/attempt-0001/run.json | worktrees/wp12_dynamics/dev-7b5e16653765/attempt-0001/output/wp12-harmonic-complex-sweep-observables.json |
| Accélération de base | authorizations/wp12_dynamics/wp12-dyn-base-003-d9deddb.json | worktrees/wp12_dynamics/dev-9a95b817d69d/attempt-0001/run.json | worktrees/wp12_dynamics/dev-9a95b817d69d/attempt-0001/output/wp12-base-acceleration-complex-sweep-observables.json |

## Newmark — erreurs, ordres, résidus et énergie

Le fixture est un BEAM2 rectiligne avec une translation axiale libre. Réponse libre non amortie, u0=0,001 m, v0=0, T=0,08 s, β=0,25 et γ=0,5. L’oracle analytique SDOF est conditionnel aux matrices scalaires K/M assemblées du fixture. Pour chaque pas, les erreurs maximales portent sur tous les échantillons de l’intervalle [0,T]; l’erreur relative est normalisée par le maximum de la solution exacte sur cette même grille. L’ordre est log2(Erel(dt)/Erel(dt/2)).

| dt (s) / pas | Erreur max. u (m) | Erreur relative u | Erreur max. v (m/s) | Erreur relative v | Erreur max. a (m/s²) | Erreur relative a |
|---:|---:|---:|---:|---:|---:|---:|
| 0,002 / 40 | 4,13392259388033e-6 | 4,13392259388033e-3 | 1,7977424513358244e-4 | 3,284482704405264e-3 | 1,2401767781595519e-2 | 4,133922593865172e-3 |
| 0,001 / 80 | 1,035460456880015e-6 | 1,035460456880015e-3 | 4,499724183201076e-5 | 8,216607215987357e-4 | 3,1063813703990917e-3 | 1,035460456799697e-3 |
| 0,0005 / 160 | 2,589890060063194e-7 | 2,589890060063194e-4 | 1,1256015593662932e-5 | 2,0551563096891896e-4 | 7,76967017981689e-4 | 2,589890059938963e-4 |

| Grandeur | Ordre 0,002 → 0,001 | Ordre 0,001 → 0,0005 |
|---|---:|---:|
| u | 1,9972389154632257 | 1,9993096972210767 |
| v | 1,9990514611498051 | 1,999294676685383 |
| a | 1,9972389155698418 | 1,9993096971783733 |

Les ordres de v et a sont des mesures descriptives; aucun seuil d’acceptation v/a n’a été ajouté. Le critère existant sur u, p ≥ 1,8, passe.

| dt (s) | Résidu réduit relatif maximal sur l’historique | Critère | Dérive énergétique relative maximale sur l’historique | Critère | E(T) − E(0) (J) |
|---:|---:|---:|---:|---:|---:|
| 0,002 | 4,855731461966191e-14 | ≤1e-7 | 1,4961989980299958e-14 | ≤1e-10 | +2,168404344971009e-18 |
| 0,001 | 2,266595239942577e-13 | ≤1e-7 | 5,3125906451789705e-14 | ≤1e-10 | −2,656295322589486e-17 |
| 0,0005 | 6,715389929742204e-13 | ≤1e-7 | 3,1810491740724695e-13 | ≤1e-10 | −8,608565249534905e-17 |

L’énergie totale initiale est 5,000000000000001e-4 J. Les valeurs du résidu et de l’énergie à chaque échantillon sont conservées dans le sidecar. Le test rapporte 34 assertions vraies.

## Harmonique direct/réduit — comparaison et troncature

Convention de phase exp(+iωt), sonde au nœud 1, DDL UX global. Les fréquences propres du fixture TET4 sont 1619,5553821068938 Hz, 1619,5553821068938 Hz et 3029,910679374876 Hz.

| Fréquence (Hz) | Amplitude directe (m) | Phase directe (rad) | Amplitude base complète (m) | Amplitude tronquée, 2 modes (m) |
|---:|---:|---:|---:|---:|
| 0 | 2,1224489795918367e-11 | 0 | 2,122448979591837e-11 | 0 |
| 809,7776910534469 | 2,004522938279143e-11 | −0,50125792676733 | 2,0045229382791432e-11 | 0 |
| 1587,1642744647559 | 1,720971111952055e-11 | −0,9417831755952587 | 1,7209711119520547e-11 | 0 |
| 1651,9464897490318 | 1,6932592635877512e-11 | −0,9756400812451841 | 1,6932592635877512e-11 | 0 |
| 2969,3124657873786 | 1,1373743807885823e-11 | −1,5495739525407815 | 1,1373743807885823e-11 | 0 |
| 3090,5088929623735 | 1,0927811139597236e-11 | −1,5915984952540274 | 1,0927811139597237e-11 | 0 |

Sur cette grille, la route à base complète et la route directe concordent à la précision machine : erreur relative maximale d’amplitude 1,8775296373918928e-16, erreur de phase maximale 1,6399613661956332e-16 rad, erreur vectorielle relative maximale 2,27962992322542e-16. Le backward error physique maximal complet est 9,960305612773948e-17; le backward error réduit maximal est 8,620806876426008e-17.

La base tronquée à deux modes donne zéro à la sonde pour les six fréquences, contre une réponse directe non nulle : erreur d’amplitude relative 1 (100 %) à chaque point. Sa phase est indéfinie sur ces réponses nulles. C’est un échec de représentation de cette sonde par cette troncature dans ce fixture; ce n’est pas une borne universelle de précision réduite. Les comparaisons direct/complet partagent les opérateurs assemblés et vérifient la cohérence de route, pas une vérité physique indépendante. Le test rapporte 11 assertions vraies.

## Accélération de base — phases, repères et DC

Convention phasorielle exp(+iωt). Accélération d’entrée Ag = 0,7 − 0,4i m/s², direction globale [1,0,0], sonde nœud 1 UX dans le repère global. Pour chaque réponse complexe, le tableau donne amplitude et phase principale (amplitude ∠ phase). Les relations vérifiées sont Arel = −ω² Urel, Aabs = Arel + Ag, Xg = −Ag/ω², Uabs = Urel + Xg et Vabs = Vrel + iωXg.

| Fréquence (Hz) | Urel (m) | Vrel (m/s) | Arel (m/s²) | Uabs (m) | Aabs (m/s²) |
|---:|---:|---:|---:|---:|---:|
| 4,358637623494104 | 5,374838498865699e-4 ∠ 2,62244653934327 | 1,4719601443879743e-2 ∠ −2,08994244104142 | 0,4031128874149274 ∠ −0,519146114246523 | 0,0016124515496597099 ∠ 2,62244653934327 | 1,2093386622447821 ∠ −0,519146114246523 |
| 8,542929742048445 | 0,010179618369063772 ∠ 2,62244653934327 | 0,5464094475379573 ∠ −2,08994244104142 | 29,329516444946535 ∠ −0,519146114246523 | 0,010459441281332915 ∠ 2,62244653934327 | 30,13574221977639 ∠ −0,519146114246523 |
| 8,891620751927972 | 0,009978041767696354 ∠ −0,519146114246523 | 0,5574502527013935 ∠ 1,051650212548374 | 31,143463965333847 ∠ 2,62244653934327 | 0,009719735419231067 ∠ −0,519146114246523 | 30,337238190503992 ∠ 2,62244653934327 |

La fréquence propre du fixture est 8,717275246988208 Hz. Les écarts absolus recalculés sur les cinq relations cinématiques et de repère ci-dessus sont nuls aux trois fréquences non nulles; le backward error physique maximal est 8,6098176918587e-17 et le backward error réduit est nul.

À DC, l’entrée est exactement nulle; les réponses relatives sont nulles. Le contrat marque le déplacement et la vitesse absolus comme indisponibles, et leurs champs JSON sont null — ils ne doivent pas être interprétés comme des zéros mesurés. Le test rapporte 48 assertions vraies, dont le round-trip de sérialisation des réponses.

## Historique Newmark préservé

Les deux tentatives antérieures restent intactes dans le ledger et dans l’archive. La première a passé pytest en 5,461 s, mais n’a archivé aucun sidecar d’observables. La deuxième est PYTEST_FAILED en 5,152 s, sur l’instrumentation avant toute assertion mécanique : le compteur global du ledger était 2 alors que le répertoire local s’appelait attempt-0001; le helper exigeait à tort que le numéro de répertoire local corresponde au compteur global.

| Tentative globale | Série / reçu | État | SHA-256 du reçu | Observation |
|---:|---|---|---|---|
| 1 | dev-42c3e52f32fc/attempt-0001/run.json | PASS | 2851ca37db2da54cff8b5a701f6d2334dd31afc50f61f298d123f3002e1dc243 | Aucun JSON scientifique dans l’inventaire. SHA stdout 459e2274e262f70cd3e9b6625013c094ddd94f3907c480d4035770f6ac9acaea. |
| 2 | dev-a81c2f0d9e74/attempt-0001/run.json | PYTEST_FAILED | 8a1cb8b493a0769030b77cc9ad6f008b0401b80ebd88d235339dd9b1f38bbeca | Échec d’identité locale/globale de l’instrumentation, pas un défaut mécanique démontré. SHA stdout 036b242bfd8679e1b9af5385fc215df7cbb22b16c65a91c114fc65baa74c7a86. |

La tentative courante Newmark est l’essai global 3 et l’essai local 1 de sa nouvelle série. Son sidecar a été archivé avant les assertions et inventorié; aucun historique n’a été supprimé ou renuméroté.

## Interprétation et limites

- **PASS pytest :** les trois nodeids exacts ont terminé avec le code de retour zéro dans les tentatives identifiées.
- **Vérification numérique bornée :** les erreurs, ordres, résidus, énergie, réponses complexes, phases, repères et sérialisation rapportés s’appliquent aux fixtures et aux oracles énoncés. Newmark compare une intégration temporelle à l’oracle analytique conditionnel aux K/M scalaires du fixture. L’harmonique complet/direct est un contrôle de cohérence partageant les opérateurs. L’accélération de base vérifie les équations de repère sur un modèle à une coordonnée libre.
- **Validation physique :** aucune donnée expérimentale, corrélation externe ou validation indépendante de modèle physique n’a été effectuée.
- **Qualification formelle :** aucune qualification globale WP05/WP06/WP07 ou WP12, aucun point officiel et aucune promotion de maturité ne découlent de cette sous-campagne.

Aucun seuil n’a été créé ou modifié. Aucun solveur, test scientifique, runner ou politique n’a été modifié pour produire ce rapport. Aucun calcul FEM supplémentaire n’a été lancé pendant la clôture documentaire.
