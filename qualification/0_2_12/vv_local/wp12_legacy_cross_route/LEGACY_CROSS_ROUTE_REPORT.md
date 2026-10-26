# WP12-A — Non-régression transversale des versions héritées

Date de l’audit : 2026-10-26
Worktree : E:/QFSolverAgents/wp12-legacy-cross-route
Branche : verify/wp12-legacy-cross-route
HEAD de base : cbdd54aadbb640a96c6b6b5b9726e1247da36012 (origin/emptiesvoids-cloud/0.2.12)

## Conclusion

Les rapports WP04, WP05, WP06, WP07 et WP13 donnent des résultats bornés positifs sur leurs branches et instantanés de campagne. Les oracles analytiques WP04/WP05/WP06/WP07 et les références indépendantes MPC/RBE sont identifiés dans la matrice jointe. Les statuts de maturité et les échecs historiques restent inchangés.

Les trois sentinelles instrumentées qui viennent de réussir — Newmark, harmonique et excitation de base — ont été exécutées sur d9deddbd6b42467c5fdc9e278bd54e97605f5738. Les fichiers sous src/solveur sont identiques entre ce commit et le HEAD candidat (git diff d9deddb..HEAD -- src/solveur est vide). En revanche, leurs trois fonctions exactes ont depuis disparu des modules de tests du candidat, tandis que les mêmes nodeids restent dans l’allowlist WP12. Leurs preuves sont donc PASS_REPORTED sur le code source scientifique identique, mais ces cibles sont ABSENT et NOT_RUN sur le checkout candidat. Cela bloque une nouvelle invocation exacte sans constituer un échec numérique.

La campagne D01 ajoute des opérateurs de projection symétrique et un chemin harmonique de flexibilité résiduelle opt-in. Les rapports D01 montrent des tests algébriques réussis; ils indiquent explicitement que les exécutions FEM M1/M2/M3 de flexibilité résiduelle n’ont pas été lancées. Le résultat harmonique WP12 sur d9deddb couvre le chemin réduit ordinaire avec le code opérateur courant, mais ne valide pas l’option de flexibilité résiduelle ni la sélection rayleigh_structured dans une campagne FEM.

Aucun défaut numérique du solveur n’est démontré par cet audit documentaire. La divergence entre les trois nodeids enregistrés et les tests présents est un problème de disponibilité de preuve. Je n’ai lancé ni test, ni assemblage, ni calcul FEM et n’ai modifié ni solveur, ni runner, ni politique.

## Identité et méthode

Le worktree a été créé proprement depuis origin/emptiesvoids-cloud/0.2.12. Le checkout original C:/Users/fari/Documents/qf_solver contenait des modifications E01 et des répertoires non suivis; ils sont restés intacts. Le présent worktree ne reçoit que ces deux documents d’audit.

J’ai examiné les rapports historiques qualification/0_2_8, les rapports de campagne qualification/0_2_12, l’historique Git des opérateurs, la politique WP12 et les fichiers d’évidence archivés. Les résultats de rapports de branches sont étiquetés PASS_REPORTED; ils ne sont pas présentés comme des exécutions fraîches sur cette branche.

Les PASS_REPORTED des campagnes WP04/WP05/WP06/WP07/WP13 et les PASS de développement WP12 sur une branche scientifique indépendante sont des résultats de tests, non une qualification formelle. Les nouvelles routes gardent leur maturité EXPERIMENTAL et leur qualification NOT_ASSESSED lorsqu’elle est ainsi définie par leur contrat. Aucun statut de release, certificat ou qualification générale n’est inféré ici.

Sens des statuts employés :

- PASS_REPORTED : une preuve de réussite est présente dans le rapport ou le journal cité, sur l’identité de source indiquée.
- FAIL_PRESERVED : échec historique conservé; ce n’est pas un nouvel échec sur le candidat.
- NOT_RUN : aucune preuve d’exécution correspondante n’a été trouvée, ou le nodeid exact n’existe pas dans le candidat.
- INFRA_FAIL : échec du lanceur ou de l’environnement avant une conclusion scientifique; ne compte pas comme échec numérique.
- SKIPPED : le corps du test n’a pas été exécuté; ce statut ne devient jamais PASS.

## Constats de couverture importants

1. Trois cibles WP12 ne sont plus collectables dans le candidat. Les fonctions test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables, test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation et test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization sont absentes de leurs fichiers actuels. Le diff net depuis le commit des preuves retire 397, 383 et 461 lignes respectivement. Les trois chaînes subsistent dans development_autonomous_policy.json et dans les tests statiques de la politique.
2. Les preuves récentes restent utiles mais doivent être attribuées correctement. Sur d9deddb, Newmark, le balayage harmonique et le balayage de base ont chacun fini avec return_code=0 et 1 passed. Les empreintes des observables archivées sont listées dans la matrice. Comme les sources solveur sont identiques, ces résultats attestent le code calcul actuel pour ces cas; ils ne restaurent pas les fonctions de test supprimées dans cbdd54a.
3. Un ancien échec Newmark est une panne d’identité du lanceur. La tentative dev-a81c2f0d9e74 a échoué avec “The launcher attempt directory does not match its unique series/attempt identity”. Une tentative ultérieure valide a réussi. Je la classe INFRA_FAIL, et non FAIL scientifique.
4. D01 n’a pas de preuve FEM pour le correcteur résiduel. Le rapport de récupération D01 consigne 87 tests algébriques réussis, trois tests natifs SKIPPED sous pytest ordinaire et FEM_RUN=NOT_RUN. La projection Rayleigh structurée possède 21 tests dédiés et trois tests algébriques connexes rapportés réussis, ainsi qu’un replay hors FEM de matrices archivées. Ces preuves couvrent l’algèbre et le refus de configurations invalides, pas une validation physique générale.
   Le statut de campagne D01 reste WP_D01_STATUS=INCONCLUSIVE, C4=NOT_ACQUIRED et WP05_FEM_QUALIFICATION=NOT_EVALUATED : des vérifications structurelles et une preuve FEM strictement opt-in restent manquantes.
5. Les anciennes matrices WP05/WP06/WP07 sont des noms ambigus. Dans qualification/0_2_8, WP05 concerne notamment le périmètre historique WEDGE6, WP06 le flambement HEX8 et WP07 le workflow statique mixte. Ils ne sont pas des preuves des nouveaux chemins harmonique réduit, Newmark modal ou accélération de base. Les comparateurs de ces nouvelles routes sont les solveurs directs conservés et les oracles analytiques dédiés.
6. Les limites historiques restent visibles. L’échec global G03 demeure FAIL_PRESERVED; l’ancien gate modal MITC4 à 2.6317e-8 contre 1e-8 reste un résultat historique. Aucun de ces statuts n’est effacé ou requalifié par les résultats WP12 récents.

## Sentinelles numériques minimales

| Domaine | Sentinelle et données reproductibles | Oracle et résultat disponible |
|---|---|---|
| WP04 projection modale | M=[[2,0.25],[0.25,1.5]], K=[[20,-2],[-2,8]]; deux modes généralisés. Contrôler Phi.T M Phi=I, Phi.T K Phi=diag(lambda) et la reconstruction M Phi Kr Phi.T M=K. | Oracle scipy.linalg.eigh et forme bilinéaire dense; le test analytique est inclus dans les 15 tests rapportés WP04. Oracle algébrique indépendant, pas comparaison expérimentale. |
| WP05 harmonique | SDOF M=2, K=20, C=0.8, F=3-2i, f=0.7 Hz, omega=2*pi*f; comparer U=F/(K+i*omega*C-omega^2*M), amplitude et phase. | Oracle fermé indépendant; PASS_REPORTED dans le module WP05 (19 cas), la campagne ciblée (135) et le full unit run rapporté (3232 pass, 93 skipped, 0 fail). |
| WP06 Newmark | BEAM2 axial SDOF, u0=1e-3 m, v0=0, T=0.08 s, gamma=0.5, beta=0.25, pas dt=0.002, 0.001, 0.0005 s. À dt=0.0005, erreur déplacement max 2.58989e-7 m (relative 2.58989e-4), résidu réduit max 6.7154e-13, dérive énergétique max 3.1811e-13. | Solution analytique de vibration libre et observables d’équilibre/énergie; PASS_REPORTED dans le JSON WP12 sur d9deddb. Le nodeid WP12 exact est absent du candidat. |
| WP05 balayage harmonique WP12 | TET4 à 3 DDL libres, base complète, balayage fréquentiel incluant 0 Hz; erreur relative vectorielle max réduit/direct 2.27963e-16. | Comparaison direct/réduit interne. Elle vérifie la cohérence entre routes, pas l’erreur physique ni la troncature générale. PASS_REPORTED sur d9deddb; nodeid absent du candidat. |
| WP07 base harmonique | BEAM2 axial, Ag=0.7-0.4i m/s^2, direction globale [1,0,0], fréquence propre 8.71727524699 Hz; à 4.35863762349 Hz, a_rel=0.35-0.2i et a_abs=1.05-0.6i m/s^2. | Contrôle a_rel=-omega^2 U_rel, a_abs=a_rel+Ag, frames et aller-retour complexe. PASS_REPORTED dans l’archive WP12 sur d9deddb; nodeid exact absent du candidat. |
| MPC | K=[[8,-2,0],[-2,5,-1],[0,-1,3]], f=[0,0,12], noeud 0 bloqué et égalité u1x-u0x=0; comparer l’élimination à la solution par multiplicateurs de Lagrange. Autre sentinelle ressort : k=1000 N/m, charge 20 N, u=[0.02,0.02] m. | Oracle Lagrange indépendant de la réduction, mais construit à partir des mêmes équations MPC. PASS_REPORTED dans la campagne WP13 à 100 tests. |
| RBE2 | Bras de 2 m, FX=20 N, ressort maître 1000 N/m; attendu UX=0.02 m; réaction transportée attendue RZ=40 N m pour l’exemple d’audit. | Référence condensée indépendante pour les tests multi-bras et cas Code_Aster 18.1 historique (erreur relative 3.47e-18), non rejoué dans la dernière campagne. 100 tests WP13 rapportés passés. |
| RBE3 rigide | Points x0=[1.7,-0.6,2.1], x1=[3.2,0.1,1.8], x2=[0.4,1.7,2.9], x3=[2,-1.1,4.4], x4=[0.9,0.3,0.8]; indépendants (1,0.7),(2,1.9),(3,2.2),(4,0.8); torseur [4,-2,3,5,7,-11]; contrôles H A=I, force et moment. | Oracle pondéré numpy.linalg.lstsq, indépendant de la construction centrée/SVD du solveur. Max historiques rapportés : H 7.77e-16, HA-I 1.78e-15, résultante 7.55e-15, moment 1.15e-14. Pas d’oracle externe RBE3. |

## Interprétation et limites

- La cohérence harmonique direct/réduit, l’équilibre Newmark réduit et l’identité des frames de base ont des preuves récentes sur des cas minuscules et bornés. Les comparaisons direct/réduit sont des contrôles internes; les oracles fermés SDOF sont les éléments indépendants les plus solides pour ces contrats.
- Les projections WP04 vérifient orthogonalité massique, symétrie exacte dans la route structurée, repli sur le chemin historique pour une matrice quasi symétrique, cohérence Rayleigh et refus fail-closed. Elles ne démontrent pas une conservation universelle des opérateurs à travers toutes les familles de maillage.
- Le correcteur de flexibilité résiduelle est une option explicite; l’absence de cette option conserve le chemin WP05 ordinaire. Ses 87 tests algébriques et les replays de matrices archivées ne remplacent pas M1/M2/M3 FEM, qui sont NOT_RUN dans le rapport de portage.
- La réduction MPC acyclique, les réactions et le transport de moment sont couverts sur petits modèles. Le rang MPC dense s’arrête à 180 DDL et emploie un seuil absolu conservateur. La couverture ne vaut pas pour tous les graphes MPC redondants ni tous les ordres de grandeur de raideur.
- RBE3 rigid_body_projection exige les six mouvements rigides, des poids positifs et un nuage de rang six (sigma_min/sigma_max > 1e-12). RBE3 weighted reste une interpolation algébrique pouvant extrapoler; aucune conservation générale des moments n’est promise.
- Il n’y a pas de défaut source reproduit dans cette mission; aucun correctif solveur n’est proposé. Une absence de nodeid est signalée comme dérive de couverture et ne doit pas être présentée comme un échec numérique.

## Tests complémentaires priorisés

1. P1 — Réconcilier les trois nodeids WP12 disparus. Avant une nouvelle invocation autorisée, remettre les trois corps de test à disposition sous les nodeids exacts de la politique, ou faire approuver une mise à jour de l’enregistrement commun. Cette mission n’a modifié ni l’un ni l’autre. Ne pas compter la réussite d9 comme une collection sur cbdd54a.
2. P1 — Exécuter le contrat de signe zéro après le correctif. Le nodeid exact est présent et enregistré, mais aucune tentative post-fix avec preuve trouvée dans les archives consultées ne l’accompagne. C’est une sentinelle de sérialisation pure, distincte du balayage harmonique; l’oracle doit vérifier le signe du zéro négatif et la phase 180° après JSON round-trip.
3. P2 — Compléter les tests opérateurs D01 par un cas assemblé borné. Comparer les projections directe/structurée et les invariants Phi.T M Phi / Phi.T K Phi sur un opérateur assemblé de petite taille, en gardant la tolérance et la branche de fallback actuelles. Toute exécution FEM correspondante nécessite une inscription exacte et une décision Owner; aucun nodeid n’est proposé comme autorisé ici.
4. P2 — Acquérir la preuve FEM D01 M1/M2/M3. Les trois tests natifs ont seulement été collectés puis SKIPPED; le rapport marque FEM_RUN=NOT_RUN. Ce n’est pas un prérequis pour la route WP05 par défaut, mais il manque pour consommer l’option résiduelle comme preuve numérique.
5. P2 — Conserver une référence externe RBE2/RBE3 distincte. La référence Code_Aster RBE2 d’un bras est historique et la corrélation actuelle n’a pas tourné; aucune corrélation RBE3 externe n’est disponible. Maintenir la portée bornée tant qu’un oracle externe indépendant n’est pas obtenu.
6. P3 — Étendre les cas de refus MPC et de rang seulement sur besoin concret. La limite 180 DDL, le refus au-delà, les cycles/conflits, les géométries RBE3 dégénérées et les poids invalides sont déjà documentés. Une campagne générale de rang ou de toutes combinaisons d’éléments n’est pas justifiée par la présente matrice.

## Références de preuve

- WP04 Modal Basis / Damping : qualification/0_2_12/wp04_modal_basis_damping_report.md — 15 tests de module, 92 tests ciblés, 3213 pass / 93 skipped / 0 fail dans le full unit run rapporté; G03 historique conservé.
- WP05 Reduced Harmonic : qualification/0_2_12/wp05_reduced_harmonic_report.md — 19 tests de module, 135 ciblés, 3232 pass / 93 skipped / 0 fail; route directe reste par défaut.
- WP06 Modal Newmark : qualification/0_2_12/wp06_modal_newmark_report.md — 32 tests de module, 3264 pass / 93 skipped / 0 fail; Newmark direct reste par défaut.
- WP07 Uniform Base Acceleration : qualification/0_2_12/wp07_uniform_base_acceleration_report.md — 70 tests ciblés, 3283 pass / 93 skipped / 0 fail et 88 tests doc rapportés.
- WP13 RBE/MPC : qualification/0_2_12/wp13_rbe_vnv_qualification_report.md — 100 pass, 0 fail, 0 skipped sur sept modules ciblés; corrélation Code_Aster non rejouée.
- D01 projection Rayleigh structurée : qualification/0_2_12/wp_d01_stable_projection_integration_report.md — 21 tests dédiés et 3 tests algébriques connexes rapportés; pas de FEM.
- D01 flexibilité résiduelle : qualification/0_2_12/wp_d01_capability_recovery_report.md — 87 pass algébriques, 3 skipped sur les tests natifs et FEM_RUN=NOT_RUN.
- Preuves récentes WP12 sous E:/QFSolverAgents/evidence/dynamics/worktrees/wp12_dynamics/ : Newmark dev-74c6cb1e73a1, harmonique dev-7b5e16653765, accélération de base dev-9a95b817d69d. Les empreintes SHA-256 des observables sont inscrites dans la matrice.

## État de l’exécution de cet audit

PYTEST_RUN=NOT_RUN
FEM_RUN=NOT_RUN
SOLVER_SOURCE_CHANGED=NO
RUNNER_OR_POLICY_CHANGED=NO
HISTORICAL_EVIDENCE_MODIFIED=NO
