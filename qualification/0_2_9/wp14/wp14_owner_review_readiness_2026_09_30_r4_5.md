# WP14 - audit de preparation a la revue Owner, R4.5

Date de l'audit : 30 septembre 2026. Verdict : **PASS_FOR_OWNER_REVIEW**, exclusivement pour le perimetre public selectionne et le dossier de preuve decrit ci-dessous. WP14 demeure **HOLD, 0/1** ; le total valide demeure **95/100**. Ce verdict ne ferme pas WP14 et n'autorise ni publication, ni tag, ni attribution du point.

## 1. Objet et identite de source

La source gouvernante est le merge `d37ab32e4f7ba0b9688ef78711453200486056f0` sur `0.2.9-unified-nonlinear` (PR #6). L'arbre de ce merge est identique a celui du commit CI `c36df868464d0cd4de0a5c982652aec21640667a` : `git diff --stat c36df868 d37ab32` est vide. La preuve G03 R4.4 reste historique a `a4a64123ec38304f2d1aa02bc3cd0617d31bbb5c` ; elle n'a pas ete transferee artificiellement au merge, car `docs/document_registry.json` avait change.

Le nouveau contrat prospectif `qualification/0_2_9/wp14/wp14_g03_bounded_public_surfaces_r4_5_contract.json` est fige dans `350289e867306dad4bb25374a8ec2249be39a92a`, apres la source gouvernante. Il conserve les memes regles, outils, seuils et exclusions de publication que R4.4. Le scan et le controle du paquet ont ete executes sur ce commit, arbre propre, avec des sorties externes neuves. Les ajouts subsequents au dossier de preuve et la correction du ledger sont hors des 1 513 chemins lies ; les fichiers deja presents sous `docs/verification/0_2_9/` sont, eux, figes par le contrat et restent inchanges. Le tracker controle conserve donc son ancien texte de synthese, que le present dossier actualise sans le reecrire. Le contrat et les enregistrements generes sont versionnes sur la branche locale `codex/wp14-current-head-rebind` ; au moment de ce rapport, cette branche n'est ni fusionnee ni poussee.

## 2. Resultat G03 R4.5 et paquet

Le scan strict des sources du paquet selectionne couvre **551 fichiers, zero constat**. Le scan strict des documents publics selectionnes couvre **745 fichiers, zero constat** ; **208 fichiers** du dossier controle `docs/verification/0_2_9/` sont comptes mais exclus de la publication et du scan public. Le registre documentaire modifie figure dans les 745 entrees, avec le blob Git `642ae4089eed65cb8ed9442fe35c45523d252a5a`. Le scanner lit les octets engages dans Git ; un hash des octets du checkout Windows peut differer par les fins de ligne.

Le paquet candidat est `0.2.8`, pas une release `0.2.9`. Wheel et sdist ont ete reconstruits a partir des 551 entrees figees. Le scan du wheel couvre 551 fichiers et celui du sdist 559, tous deux sans constat. Les sondes depuis et hors du checkout ont chacune verifie l'origine et les octets de **473 sources installees**. Le `verify-all` du paquet installe rend `UNSUPPORTED` comme prevu pour une commande reservee au checkout Git complet ; ce n'est pas un echec du paquet. L'environnement de sonde autorise des dependances de site systeme/utilisateur : l'identite des modules QF est verifiee, pas l'isolation de chaque dependance.

Les enregistrements du scan, du build, des sondes et des logs sont dans `qualification/0_2_9/wp14/g03_bounded_public_surfaces_r4_5/`. Les **26 fichiers generes recopies** ont ete compares a leur source externe : **26/26 SHA-256 identiques**. La synthese machine `wp14_g03_r4_5_execution_and_owner_review_audit.json` contient leurs tailles et hashes. Points de controle :

| Piece | Taille | SHA-256 |
| --- | ---: | --- |
| Contrat R4.5 | 10 065 o | `48abde11b2569bfc79f9d902321ff687a13897ccadd89b47cc8bf7712787c5a2` |
| Scan public | 396 290 o | `0864874ec7569a90edfee1032282da89c4b2e1513e3269c7c9565f6cd10532b0` |
| Resultat du paquet | 15 357 o | `bf03aefee79a5452e426e1497698c7d0dd214b1f98c43af3a7cab6af6c8b5f43` |
| Wheel externe 0.2.8 | 1 509 979 o | `24a3330a23a513bfb274830da2318362e87aeeb8a81a4623270a350aee3c9a73` |
| Sdist externe 0.2.8 | 1 138 014 o | `5584ba659a2e3bc1517810ddd6e6e0c8e8debc8750e61741824c50795283db4a` |

Les deux binaires restent dans le dossier externe temporaire ; seules leurs empreintes et les enregistrements du controle sont versionnes. Leurs SHA differents des binaires R4.4 ne prouvent pas un changement de source : les entrees du paquet selectionne sont identiques, et les archives de build ne sont pas traitees ici comme byte-reproductibles.

## 3. Gates de revue

| Gate | Attendu / preuve directe | Etat pour la revue Owner | Limite et action |
| --- | --- | --- | --- |
| G01 Provenance | Merge `d37ab32`, contrat posterieur `350289e`, scan source-bound, arbre propre a l'execution | PASS | Integrer separement la branche de preuve ; ne pas requalifier un futur changement des entrees figees. |
| G02 Ledger | 0/1 et 95/100 inchanges ; statut descriptif corrige en `HOLD` dans la branche candidate | PASS candidat | Le gouvernant `d37ab32` porte encore `NOT_STARTED` jusqu'a integration ; le tracker controle fige garde son ancien resume, supersede par ce dossier. Aucun point ajoute. |
| G03 Claims/registry | R4.5 : 551 sources + 745 documents, zero constat ; registre modifie couvert | PASS_BOUNDED_PUBLIC_SURFACES | Le depot entier et les echecs historiques R02-R05 restent FAIL ; pas de derogation globale. |
| G04 Qualite | Quatre jobs de matrice CI reussis ; Ruff, mypy progressif, tests, couverture >=80 %, P0, compileall, verification rapide dans le workflow | PASS sur la source CI | Le recheck 86,19 % est archive ; les tests locaux cibles ajoutent 118 PASS, 2 ignores mais ne remplacent pas la matrice. |
| G05 Engineering | Job `Full engineering campaign` du run #36707249001 reussi | PASS sur la source CI | Campagne et preuves recuperees selon le workflow ; aucune nouvelle campagne numerique par ce rebind. |
| G06 Documentation | R2.2 : 22/22 documents du perimetre Owner-review complets ; job documentaire CI reussi | PASS_WITH_LIMITATIONS | Backlog controle : 89 documents, 86 reviewer manquants, 89 approver manquants, advisory selon la politique R2.2 ; attribution Owner auto-attestee, non signee independamment. |
| G07 Paquet/source publique | Build, scans wheel/sdist, sondes d'installation PASS a R4.5 | PASS_CANDIDATE_PACKAGE_ONLY | Version 0.2.8 ; aucune revendication de release 0.2.9. |
| G08 Plateformes | Run GitHub `quality.yml` #36707249001 : 4 jambes Ubuntu/Windows x Python 3.10/3.13, documentation, preuves WP14 ciblees, engineering : 7/7 jobs reussis | PASS pour l'arbre source identique | Le run teste `c36df868`, arbre identique au merge `d37ab32`, et non les commits documentaires locaux posterieurs. |
| G09 Autorite release | Aucune decision de cloture ou de publication dans ce dossier | HOLD attendu | Decision Owner distincte pour point, version release, tag et publication. |

Le workflow CI est consultable a `https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/36707249001`. L'artefact GitHub `wp14-r23-recovered-evidence` de ce run expire le **3 octobre 2026 a 12:01:05 UTC** ; il sert au transfert CI, pas de politique de conservation durable.

## 4. Limites historiques et archivage

Le scan R4.5 ne balaie ni tout `scripts/`, ni tout `tests/`, ni tout `qualification/`, ni l'historique Git. Les constats du scan depot entier restent FAIL, y compris les enregistrements historiques R02-R05. Les 208 pieces controlees exclues du site ne sont pas un PASS public implicite. Les images et jeux binaires ne sont pas controles par ce scan texte/PDF.

Les quatre NPZ WP04-D reproduits conservent leurs correspondances de taille et SHA-256 avec les empreintes enregistrees, mais ce ne sont pas des originaux retrouves. La recomputation forensic et les JSON bruts historiques demeurent distincts. L'acceptation existante WP04-D 12/12 ne change pas. Les metadonnees des archives WP16 designees sont connues, mais aucun nouveau telechargement et rehash distant complet n'a ete effectue dans cette execution.

## 5. Verification complementaire et proposition de decision

Les tests cibles du scanner, du paquet, du contrat WP14, du ledger et des documents donnent **118 passes, 2 ignores** (`pytest` local, Python 3.13). Le JSON ledger reste valide, WP14 vaut 0/1 et le total 95/100. Aucun solve, seuil modifie, tag, publication, push ou merge n'a ete effectue par cette requalification.

L'Owner peut maintenant examiner et, s'il le souhaite, accepter **separement** : (1) G03 R4.5 pour les seules surfaces publiques selectionnees ; (2) G06 R2.2 avec son backlog advisory et son attestation de role ; (3) G08 pour l'arbre de source teste par CI. La decision ne doit pas valider le depot entier, attribuer le point WP14, ni autoriser la release. WP14 reste HOLD jusqu'a la decision G09 et aux travaux hors perimetre.
