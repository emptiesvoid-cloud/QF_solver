# WP13 — revue du README global et des liens

Date : 2026-11-01  
Branche : `codex/wp13-release-engineering-20261031`  
HEAD de départ : `357b4b5398c1d3e5059e0a1049f8494f4096f13e`

## Résultat de la revue éditoriale

Le README sert de porte d’entrée générale du projet, pas de fiche de publication 0.2.12. Il présente l’objectif du solveur, les familles d’éléments, matériaux et composites, charges et contraintes, analyses, méthodes numériques, interfaces, installation, exemples, limites, maturité et citation. Il renvoie aux contrats détaillés au lieu de recopier toutes les spécifications scientifiques.

La revue a conservé les informations techniques qui influencent le choix d’une route et l’interprétation d’un résultat. Elle clarifie trois frontières qui pouvaient être confondues : l’interface Python stable listée dans le contrat API contre les modules internes ou expérimentaux; disponibilité d’une fonction contre qualification de sa combinaison; version publiée contre candidat non publié.

Les sections actuelles couvrent notamment :

- TET4/TET10, HEX8/HEX20, WEDGE6, BEAM2, MITC3/MITC4 et entités discrètes;
- élasticité isotrope, solides orthotropes, stratifiés, indicateurs premier pli expérimentaux;
- MPC, RBE2/RBE3, masses, inerties, ressorts et limites des modèles mixtes;
- statique, modal, transitoire Newmark, harmonique, flambement linéarisé et non-linéarités bornées;
- plasticité J2, rotations corotationnelles, contact frictionnel et frictionless, et limites de petites déformations;
- rotordynamique et Campbell expérimentaux, solveur QEP dense, SciPy et usages optionnels PETSc/MPI;
- API Python, CLI, JSON, Gmsh, import `.inp` borné et exports spécialisés;
- vérification numérique, corrélation, maturité et validation physique comme catégories distinctes.

Le README indique explicitement que 0.2.11 est la dernière version publiée, que 0.2.12 est une candidate sans date/DOI, que le solveur n’est pas certifié, que les FAIL WP12 restent visibles et que G03 reste `FAIL`.

## Revue des liens et remappage

Le site officiel est `https://qfsolver.org/`. Les routes publiques ont été vérifiées individuellement le 2026-11-01; les anciennes routes GitHub Pages n’ont pas reçu de remplacement global aveugle.

| Destination historique ou besoin | Destination retenue | Motif |
| --- | --- | --- |
| Ancienne racine de documentation | [Site officiel](https://qfsolver.org/) | Point d’entrée général désormais canonique. |
| Guide de démarrage et choix d’un modèle | [Getting started](https://qfsolver.org/getting-started) et `docs/getting-started/*.md` | Le site fournit le parcours public; les pages locales donnent les contrats techniques détaillés. |
| Capacités publiques | [Capability matrix](https://qfsolver.org/capabilities) et `docs/capabilities/index.md` | Séparation entre résumé public et matrice détaillée propre à la branche candidate. |
| Versionnement et projet | [Project overview](https://qfsolver.org/project) et [versions publiées](https://qfsolver.org/versions) | Le README peut renvoyer au projet et à l’archive des releases sans annoncer 0.2.12 comme publiée. |
| Roadmap | [Roadmap officielle](https://qfsolver.org/roadmap) | La page publique qualifie 0.2.12 de cible de planification. |
| Anciennes pages techniques GitHub Pages | Liens Markdown relatifs vers le document `docs/` existant | Garde l’accès à la spécification réellement présente et évite de supposer une route identique sur le site. |
| Notes de maturité ou exemples hors `docs/` | Lien GitHub vers le fichier précis sur la branche candidate, ou note publique candidate dans `docs/whats-new/` | Les cibles ne sont pas servies comme pages MkDocs; le lien indique exactement la source/version. |
| DOI de projet et de releases publiées | DOI Zenodo existants | Les références historiques restent nécessaires; aucun DOI 0.2.12 n’est inventé. |

Les pages `/docs` et `/docs/api` ont aussi été vérifiées accessibles. Le README privilégie les guides d’entrée et contrats locaux pour les liens techniques, ce qui évite de créer une nouvelle équivalence de route sans nécessité. Le changelog reste un fichier versionné lié localement.

## Mesures de liens

Analyse du README final à cette révision :

| Mesure | Résultat |
| --- | ---: |
| Liens Markdown analysés | 106 |
| Cibles locales vérifiées, ancres Markdown comprises | 90 |
| Cibles locales/ancres cassées | 0 |
| URL HTTP/HTTPS externes uniques contrôlées | 16 |
| Réponses HTTP 200 | 16 |

La validation du site est distincte : 55 cibles dans le menu MkDocs, zéro cible absente, build strict réussi. Un contrôle documentaire ciblé a aussi détecté puis corrigé le périmètre d’un test qui appliquait le statut publié 0.2.11 aux deux contrats API candidats 0.2.12; ceux-ci sont maintenant testés explicitement comme `controlled_candidate`. Les 22 cas ciblés passent. Les liens de pages documentaires modifiées sont également passés dans ce build sans avertissement de lien non résolu.

## Décision de publication des liens

Le README utilise les URL du site officiel pour les pages équivalentes de projet, versions, démarrage, capacités et roadmap. Pour les pages spécialisées, il utilise le chemin `docs/` versionné. Les références de preuves historiques pointent vers leur release/branche d’origine lorsqu’elles portent une identité de version. Les routes non équivalentes n’ont pas été inventées.

## Limites et suites

- Le contrôle HTTP atteste l’accès au moment de la vérification; il ne garantit pas la disponibilité future.
- Les liens vers des éléments de qualification ne rendent pas leur contenu admissible à la publication ni ne changent leur statut.
- La documentation publique candidate n’a pas été déployée. La note candidate reste séparée de l’affirmation de version publiée.
- README et `pyproject.toml` font partie de la distribution. La preuve d’artefact v6 est historique et ne s’applique pas au nouveau contenu; un candidat doit être reconstruit et vérifié à partir des blobs finaux.

## Conclusion

Le README est une vue d’ensemble technique globale et maintenable. Les routes du site officiel et de la documentation locale sont choisies par équivalence de contenu. Les liens vérifiés ne justifient aucun changement de maturité scientifique, et aucun statut de publication n’est avancé.
