# WP12-A — Accélération de base complexe : préparation prospective

**Statut : WP12A_BASE_MOTION_INTEGRATION_REVIEW_REQUIRED**

Cette proposition améliore l'observabilité du dernier cas WP12-A. Elle ne constitue ni un préflight officiel pour la source modifiée, ni un manifeste autorisé. Aucun corps scientifique ni réservation n'a été lancé pour cette préparation.

## Contrat scientifique inspecté

Nodeid : `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization`. Le cas est un BEAM2 à un DDL libre UX, sans amortissement Rayleigh ; le mouvement de support est homogène et co-mobile. L'excitation complexe vaut `0,7 - 0,4i m/s²` aux fréquences non nulles et zéro au point DC. La convention est `exp(+i omega t)`. Le balayage est DC, 0,5, 0,98 et 1,02 fois la première fréquence propre. La fréquence propre est calculée à partir des opérateurs assemblés.

La référence scalaire résout `(K_ff - omega² M_ff) U_rel = -(M r)_f A_g` à partir des matrices assemblées et du vecteur d'influence. Les vitesses et accélérations suivent `i omega U` et `-omega² U`. Pour les fréquences non nulles, le déplacement du support vaut `-A_g / omega²` et s'ajoute au déplacement relatif ; l'accélération absolue ajoute `A_g` à l'accélération relative. À DC, les déplacements et vitesses absolus restent indisponibles ; l'accélération imposée est nulle. Les assertions existantes utilisent `rel=1e-11, abs=1e-13` et vérifient aussi la sérialisation des six champs et de la clé d'exécution.

La référence est une équation scalaire formulée séparément de la voie modale mais réutilise les matrices assemblées, la masse et les conditions aux limites du modèle : elle ne constitue pas une validation indépendante de l'assemblage. Les fréquences proches de la résonance restent celles du test ; aucun diagnostic de singularité supplémentaire ne modifie les critères.

## Observabilité ajoutée

Pour chaque fréquence, le sidecar conserve désormais les phasors calculés et de référence des six quantités, leurs écarts complexes, erreurs absolues et relatives, unités, pulsation, excitation, impédance, second membre et résidu physique libre scalaire. Chaque phasor est explicite (`shape`, parties réelle et imaginaire, amplitude et phase). Les valeurs indisponibles restent nulles ; une phase de phasor nul est indéfinie. L'erreur relative est nulle au sens JSON `null` lorsque la référence est inférieure au minimum normal float64, indisponible ou lorsque le calcul du rapport n'est pas fini. Les valeurs non finies sont conservées par les marqueurs explicites du writer existant. Aucun oracle, seuil, paramètre ou assertion n'est modifié.

Les tests utilisent uniquement des phasors fixes et des répertoires temporaires simulés. Ils vérifient valeurs complexes, unités, forme scalaire, phases nulles, références très faibles, valeurs non finies et débordement, archivage avant échec et liaison manifeste/tentative. La suite synthétique existante couvre écriture atomique, SHA-256, refus de chemins, `owner-authorized/` et non-écrasement.

## État Git et étapes à autoriser

Candidat scientifique sur `fix/wp12a-base-motion-observability-20261028`, HEAD `7406e34efc28ed8f18c15440115595dfa3dd9ca5`, tree `a618d0d1790ab8642f408a78b2d2856debcc60c0` ; fingerprint prospectif du nodeid `a7dcb27d51a4b4a99bbf288258581c21f4cffc3e5f899de91de9b3e68d53c6fc`. Ces données ne sont pas encore l'inscription active sur le worktree officiel. La branche d'intégration reprend le code pour revue sans fusionner toute la branche scientifique.

Après intégration autorisée, avancer proprement le worktree scientifique officiel, inspecter et enregistrer le nouveau fingerprint append-only, stabiliser la désignation du contrôleur par la procédure Git, puis vérifier le ledger courant. Faire ensuite un préflight officiel collect-only et préparer un manifeste inédit `PREPARED_NOT_AUTHORIZED`, `execution_authorized=false`, `do_not_execute=true`. Les preuves anciennes restent conservées ; le manifeste historique `c863f217e0a701f584a4d913ba5f352deb23b465c692cba5d5cf8b9009f1388b` est périmé.

Le ledger Dynamics v2 avait le SHA-256 `6cb6d166608adfeb8689502a24285c26f3fc63b36fb0cd72005059f9e74fbe5d` lors de cette préparation ; le prédécesseur immuable vaut `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`. Ils doivent être revérifiés avant tout nouveau préflight. Un nouveau calcul exige une décision Owner distincte ; un PASS de développement ne constitue pas une qualification générale.
