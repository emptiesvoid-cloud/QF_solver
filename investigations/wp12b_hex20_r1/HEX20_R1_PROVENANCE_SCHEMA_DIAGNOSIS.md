# HEX20 R1 — contrat de provenance du sidecar

**Cause CONFIRMED.** Le sidecar R1 contient `qfsolver-wp12b-hex20-affine-diagnostic-v2`; son émetteur scientifique figé déclare v2. Le contrôleur R1, HEAD `0d91fc5a9bc09875526af6f17cf42c3ac666c5b7`, exige exclusivement v1 dans `_wp12b_hex20_diagnostic_sidecar`. Les tests synthétiques historiques du contrôleur fabriquaient v1, alors que les tests de l'émetteur attendaient v2. Le reçu R1 indique `sidecar schema mismatch` et demeure `PROVENANCE_MISMATCH`.

Le contrat courant de l'émetteur est v2; v1 reste un contrat historique à conserver pour les anciens sidecars. Le correctif prospectif du validateur énumère explicitement v1 et v2. Il conserve les contrôles de chemin, taille, JSON strict, nodeid, DDL, tentative, manifest ID/SHA et liaison `run.json`; une version inconnue, une valeur de type incorrect ou une identité altérée reste refusée. Il ne change ni l'émetteur, ni le sidecar R1, ni le ledger.

La vérification en lecture seule du sidecar R1 par le **validateur candidat** a renvoyé `VERIFIED` pour la liaison de provenance et le SHA `dee3c6976929954b7f4c5a678d474b3a151f7821db9c334f0f01d22320d2133e`. Ce résultat prospectif n'est pas une révision du reçu R1, ne change pas le ledger et ne change pas l'échec pytest.

Un changement du contrôleur modifie son fingerprint. Après intégration et désignation officielle d'un checkout propre, les manifestes et préflights liés à une ancienne identité doivent être réévalués suivant le contrat du runner. Aucun ancien mandat ou certificat ne peut être transféré automatiquement.
