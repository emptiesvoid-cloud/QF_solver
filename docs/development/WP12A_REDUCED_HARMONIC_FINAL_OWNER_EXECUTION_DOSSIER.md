# WP12-A — Harmonique réduit : audit et dossier prospectif

**Statut : `WP12A_REDUCED_HARMONIC_INTEGRATION_REVIEW_REQUIRED`**

Le code proposé enrichit le sidecar et ajoute des indicateurs explicites au
manifeste Dynamics. Il reste à intégrer et à enregistrer sur le worktree
scientifique officiel avant de produire un préflight et un manifeste définitifs.
Aucune exécution scientifique ni réservation n’a été effectuée pour cette
préparation. Le statut `OWNER_EXECUTION_DECISION_READY` ne doit pas être attribué
avant ces étapes et la vérification des identités définitives.

## État actuel vérifié

- Release `emptiesvoids-cloud/0.2.12` : HEAD
  `4bfafe2176f1c05ec3805882759d4bfc1d208fca` lors de l’audit.
- Contrôleur officiellement désigné, checkout propre et détaché : HEAD
  `b206e6f520e9b03c3c925c3bef20883f01aa9800`, tree
  `6f16b0d1d5fe204707e6b784355d34c943f18db5`, fingerprint
  `e48d4e61f04df2819431465130b12c3d36f24f6f92fbdf8221f44190442e1e08`.
- Source scientifique enregistrée : branche `codex/wp12-dynamic-harmonic-verification`,
  HEAD `5f96dd604fe40279ead0186f49be77e7a0bbeac1`, tree
  `bf0b50b95355281f480e7fbab4139bd1cefc1900`; fingerprint actif pour ce
  nodeid `3a8c1324d0563214911e8f9abca87c09ddf98907d5d8ab01c822640c82baa4fe`.
- Nodeid : `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation`.
  Inscription active : 3 DDL libres, 300 s, 10 tentatives au maximum par nodeid.
- Le ledger Dynamics v2 vaut
  `0c519e3cbc4db33b4c520a4bcfa5aec92e7688deb4979449e9394d3f768932c0`;
  le ledger historique lié reste
  `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`.
  Total : 8/130; harmonique réduit : 1/10. La prochaine tentative serait la
  deuxième, sous réserve de revérifier les deux ledgers avant réservation.
- WP07 et Newmark r3 conservent leurs PASS de développement. Le rapport Newmark
  r3 a le SHA-256 `4176d925787d7dafa113b63541b3c2ef22f7d0a32374311bacbb45b115d4503f`.
- Le manifeste `wp12a-harmonic-reduced-b206-20261028-r2`, SHA-256
  `9582fca0ede9dac00edd6a4db40c16c639d38ac3da87abdde16edf4d1d100f7c`, et son
  préflight sont périmés : ils lient le ledger précédant la réservation Newmark.

## Contrat scientifique et limites de l’oracle

Le cas TET4 possède 3 DDL libres; la force est de 1 N sur UX au nœud 1.
L’amortissement est de Rayleigh `C=0,02 M + 0,0001 K` et les phasors suivent
`exp(+i omega t)`. Le balayage comprend zéro, la moitié de la première fréquence
propre et les facteurs 0,98/1,02 autour de la première et de la dernière. Les
paramètres et les fréquences n’ont pas été modifiés.

La voie directe réassemble et résout les équations physiques; la voie modale
projette M, K, C et la charge sur une base complète de trois modes ou tronquée
à deux modes, puis reconstruit la réponse. Les deux voies partagent notamment
l’assembleur, le modèle, les charges et des composants de résolution : leur
accord teste la voie de projection et la résolution, sans constituer un oracle
physique indépendant de l’assemblage. Les matrices, vecteurs, coordonnées et
résidus archivés par la proposition permettent une recomposition hors solveur.

Le test conserve ses assertions : erreurs arrière modale et physique libre de
la base complète et écart relatif vectoriel base complète/directe `<= 1e-8`.
La différence tronquée/directe cumule les effets de sous-espace omis et de
résolution; elle ne démontre pas à elle seule une erreur de troncature pure.
Les résidus modaux sont des forces généralisées et dépendent de la
normalisation. L’indicateur de conditionnement est le minimum du conditionnement
réciproque mis à l’échelle et du plancher singulier mis à l’échelle; il ne doit
pas être présenté comme le conditionnement physique complet.

Le sidecar historique PASS `dev-7b5e16653765`, SHA-256
`93b7fcef37b9d60eb18062509d3b391cda7b177f1f6c520f694564c7b813e6f1`, rapporte
des fréquences propres 1619,555, 1619,555 et 3029,911 Hz. La réponse tronquée à
la sonde était nulle, l’écart relatif tronquée/directe égal à 1, et la phase
tronquée indéfinie. Une ancienne valeur d’écart de phase de pi issue de zéros
signés ne représente pas une phase physique; la proposition enregistre `null`
pour tout écart de phase impliquant un phasor nul. Les preuves historiques ne
sont pas modifiées.

## Modifications prospectives

La proposition archive sous forme JSON réelle/imaginaire avec dimensions les
réponses physiques complètes des trois voies, les coordonnées modales, charges,
différences vectorielles absolues et relatives, résidus physiques libres et
modaux recomposés, ainsi que les différences de reconstruction. Elle conserve
K/M physiques, C Rayleigh recomposée, indices et signatures de DDL, modes,
valeurs propres, nombres de modes, M/K/C projetées et diagnostics de base;
les enregistrements de conditionnement des deux bases sont conservés. Les
diagnostics sont calculés à partir des données déjà produites par le test; ils
ne lancent pas de résolution supplémentaire. Les valeurs non finies sont
signalées par le writer et les rapports relatifs à une référence nulle ou trop
petite sont indéfinis.

Le contrôle d’exécution Dynamics proposé produit des manifestes préparés avec
`execution_authorized=false` et `do_not_execute=true`. Une copie approuvée doit
porter les valeurs inverses et une décision Owner valide; des indicateurs
manquants ou contradictoires sont refusés avant réservation. Les anciens
manifestes et décisions restent archivés et ne sont pas transférables à un
nouveau fingerprint de contrôleur.

Le fingerprint prospectif de la source du test, calculé hors du worktree
officiel sur le candidat, est
`dea993f995b07804b5ca9baf9cccb84615bc14313ccac7934694ca24d3f5e995`.
Le candidat scientifique est sur la branche
`fix/wp12a-harmonic-observability-20261028`, HEAD
`bf88803a8464a805e953013a2593fb06e6ea4659`, tree
`cd75a62d68a95adbbb398ee312fbc8e1fc5fb7cd`. Ces valeurs ne sont pas une
inscription active et devront être recalculées après intégration.

## Vérifications et suite requise

Les contrôles synthétiques ciblés ont réussi (45 tests sur le candidat final);
ils utilisent des tableaux et des doubles
de processus, sans assemblage ni corps du test harmonique. Ils couvrent le
format complexe, les résidus, la reconstruction, zéro/référence proche de zéro,
les valeurs non finies, les chemins et écritures du sidecar, les refus de
manifeste et la réservation simulée sur ledger temporaire. Ruff, compilation et
`git diff --check` sont vérifiés sur la branche candidate; la CI complète de la
PR est à contrôler sur son HEAD final.

La suite synthétique locale complète a également terminé avec 263 réussis,
0 échec, 0 skip et 0 erreur. Elle avait été lancée avant le dernier ajout des
enregistrements de conditionnement au sidecar; la CI doit vérifier le HEAD final.

Après revue et intégration autorisées : actualiser le worktree scientifique
par la procédure Git, inspecter et enregistrer append-only le nodeid et son
nouveau fingerprint, stabiliser la désignation du contrôleur, puis vérifier le
ledger courant. Exécuter un nouveau préflight officiel collect-only et préparer
un manifeste inédit `PREPARED_NOT_AUTHORIZED` lié à ce reçu et ce ledger, avec
les deux indicateurs explicites. Enfin soumettre une décision Owner distincte
pour une seule tentative, 3 DDL, 300 s et sans retry. Tout changement du ledger
après le préflight impose de renouveler le dossier. Aucune qualification globale
ne découle de ces préparatifs ou d’un éventuel PASS de développement.
