# WP11 — Audit API, résultats et sérialisation

## Décision de contrat

L’Owner accepte pour v0.2.12 les DTO ordinaires hétérogènes lorsqu’ils sont
documentés. Aucun schéma de résultat universel ou `load_result()` générique
n’est exigé. Les schémas versionnés existants, leurs refus et leurs limites
restent inchangés. Les références exactes aux tests et aux contrats figurent
dans [`wp11_acceptance_matrix.tsv`](wp11_acceptance_matrix.tsv).

## Inventaire et limites

- `SolveResult`, `ModalResult`, `DynamicResult` et `HarmonicResult` exposent
  des sorties propres à l’analyse; pas de schéma commun versionné ni de lecteur
  partagé.
- Modal-Newmark : `qf-modal-newmark-result/v1`, cartes DOF et champs temporels;
  `from_dict()` spécifique; maturité `EXPERIMENTAL`, qualification
  `NOT_ASSESSED`.
- Harmonique réduit : `qf-reduced-harmonic-result/v1`, fréquences et phasors
  réel/imaginaire explicites, disponibilité déclarée et provenance de base /
  opérateurs; `from_dict()` spécifique; `EXPERIMENTAL`, `NOT_ASSESSED`.
- D01 : configuration stricte `qf-harmonic-residual-flexibility-config/v1`
  et résultat imbriquant le résultat WP05 sans réécriture sous
  `qf-reduced-harmonic-residual-flexibility-result/v1`.
- Rotor/Campbell : payloads complexes dédiés et aides de sérialisation; aucun
  lecteur partagé. Les routes restent expérimentales et bornées.
- HDF5 mixte : lecteur, writer, sélecteurs et digest sémantique version `1.0`
  pour TET4/WEDGE6/HEX8; le round-trip synthétique vérifie le contenu et le
  digest logique.
- D02 : `qf-dynamic-solid-stress/v1` conserve convention, ordre, unités,
  identité et statut expérimental selon son périmètre borné.
- Checkpoints : contrats propres aux objets conservent identités de source,
  opérateur, base ou exécution lorsqu’ils s’appliquent; pas de chargeur
  universel.

## Compatibilité comportementale de `save_result`

La comparaison du writer historique au baseline de travail a montré que
`Path.write_text()` remplaçait silencieusement une cible existante. Le writer
actuel, introduit avant cette revue, refusait cette cible avec ouverture
exclusive. Ainsi, les appels existants à deux arguments vers une nouvelle
destination restent compatibles, mais ceux qui dépendaient du remplacement
implicite ne le sont pas.

Le contrat WP11 conserve la protection par défaut et rend le remplacement
explicite : `save_result(result, path, overwrite=True)`. Le paramètre est
keyword-only et optionnel; le CLI fournit `--overwrite` sur ses points de
sortie utilisant ce writer. Le test d’intégration existant qui réutilise son
chemin de résultat est migré vers ce flag; son exécution FEM reste exclue de
cette vérification. La matrice distingue donc la compatibilité des appels sur
nouveau chemin de la migration requise pour les anciens appels qui écrasaient.

Les autres corrections déjà enregistrées sont conservées : nettoyage HDF5
limité à l’identité du fichier créé par ce writer; vérification des nombres de
fréquences/réponses avant `zip()` pour `HarmonicResult`; validation des champs
dérivés redondants par les décodeurs v1 Modal-Newmark et harmonique réduit.

## Statuts scientifiques

D01 reste `INCONCLUSIVE`; C02 reste `CLOSED_BOUNDED` uniquement sur AR/N03; E01
reste `OPEN_WITH_BOUNDED_CERTIFICATES`. Ces statuts ne bloquent pas
l’acceptation des contrats API WP11 et ne sont pas promus par les preuves de ce
dossier. La V&V numérique et la performance sont affectées à WP12. Aucun calcul
FEM supplémentaire n’a été exécuté.
