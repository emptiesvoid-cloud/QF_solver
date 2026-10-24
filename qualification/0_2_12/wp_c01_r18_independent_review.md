# WP-C01-R18 — Revue indépendante des correctifs R17

## Portée

Revue indépendante en lecture seule du lecteur JSON, du validateur des checkpoints, du postprocesseur hors FEM, de ses tests unitaires et de la comparaison aux archives R14/R16. Aucun calcul FEM n'a été lancé.

## Conclusion

Avis favorable après correction du défaut fail-open initial. Le postprocesseur appelle désormais le contrôle du moment avant de produire un verdict PASS, refuse les valeurs non finies ou supérieures à la limite inchangée de `0.002 N.m`, et lie le rejeu aux SHA-256 exacts des archives R14/R16 et de la fixture. Chaque checkpoint accepté exige le contact actif attendu. Les tests couvrent la limite, les valeurs non finies et le refus d'un checkpoint sans contact.

La relecture n'a identifié aucun défaut P0/P1 restant dans ce périmètre. Les résultats de forces et de contact restent descriptifs hors le contrôle de moment; aucun seuil mécanique supplémentaire de force n'a été introduit. C'est une limite d'observabilité facultative pour ce rejeu à entrées épinglées, pas un changement de tolérance ou un motif pour requalifier le cas.

## Résultats vérifiés

- 18 tests unitaires du contrat: PASS.
- Rejeu hors FEM sur les octets R14/R16 originaux: PASS.
- 106 événements décodés; 9 paliers acceptés; stick 1–7, slip 8–9.
- Gap absolu maximal: `1.3877787807814457e-17 m`.
- Écart maximal Coulomb en slip: `5.4569682106375694e-12 N`.
- Moment brut indépendant: `1.8780385144291777e-12 N.m`, limite inchangée `0.002 N.m`.
- Ruff, compilation Python et `git diff --check`: PASS.

Le FAIL de la tentative pytest R16 d'origine demeure un fait historique. Le PASS porte uniquement sur le rejeu hors FEM de l'archive et ne remplace pas le verdict du run original.
