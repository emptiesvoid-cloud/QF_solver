# WP12-S — Actions Owner avant toute campagne

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**
Toutes les actions ci-dessous sont en attente. Aucune n'a été exécutée par cette revue.

## OWNER_ACTION_REQUIRED — O-1 : établir la racine de confiance Ed25519

**Action exacte.** Provisionner une clé publique Ed25519 hors checkout, l'associer à une identité Owner vérifiée indépendamment, protéger le trust store et son pin HKLM. Garder la clé privée uniquement dans le gestionnaire matériel/secret ou le support hors ligne contrôlé par l'Owner. Ne jamais la déposer dans Git, les journaux ou le chat.

**Prérequis.** Hôte Windows approuvé et administré par l'Owner; identifiant de compte runner standard déterminé; chemin dédié `C:\ProgramData\QFSolver`; inventaire des valeurs et ACL existantes sauvegardé; choix de canonicalisation signé/verifié (voir O-2). Si l'une des valeurs HKLM existe déjà, arrêter et auditer au lieu de l'écraser.

**Format public attendu.** Le fichier public doit être UTF-8 JSON correspondant au schéma `qualification/0_2_12/wp12_preparation/wp12_owner_trust_store.schema.json`, par exemple :

```json
{
  "schema": "qf-wp12-owner-trust-store-v1",
  "keys": [
    {
      "key_id": "<identifiant stable>",
      "principal": "<identité Owner vérifiée hors runner>",
      "public_key_base64": "<clé publique Ed25519 brute de 32 octets, Base64>",
      "revoked": false
    }
  ]
}
```

Le champ `principal` est une assertion de configuration; son propriétaire doit être identifié hors de l'application. La clé privée n'apparaît jamais dans ce fichier.

**Étapes Windows proposées par l'Owner (non exécutées).** Le répertoire doit être dédié et vide avant de retirer l'héritage. Adapter le principal du compte runner et examiner l'ACL existante avant application.

```powershell
$trustDir = 'C:\ProgramData\QFSolver'
$trustFile = Join-Path $trustDir 'wp12-owner-trust.json'
$runnerPrincipal = "$env:COMPUTERNAME\QFSolverRunner"
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'

# Créer le répertoire dédié seulement après vérification qu'il n'existe pas.
if (Test-Path -LiteralPath $trustDir) { throw 'Inspecter le répertoire existant avant toute modification.' }
New-Item -ItemType Directory -Path $trustDir | Out-Null

# Après avoir écrit le document PUBLIC et vérifié sa structure :
icacls $trustDir /inheritance:r
icacls $trustDir /grant:r '*S-1-5-18:(OI)(CI)(F)' '*S-1-5-32-544:(OI)(CI)(F)' "$($runnerPrincipal):(OI)(CI)(RX)"
icacls $trustFile /inheritance:r
icacls $trustFile /grant:r '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' "$($runnerPrincipal):(R)"

# Refuser tout remplacement d'une configuration machine préexistante.
$props = Get-ItemProperty -LiteralPath $regPath -ErrorAction Stop
$names = @('QF_WP12_TRUST_STORE', 'QF_WP12_TRUST_STORE_SHA256')
$existing = @($props.PSObject.Properties.Name | Where-Object { $_ -in $names })
if ($existing.Count -ne 0) { throw "Valeur HKLM déjà présente: $($existing -join ', ')" }
$pin = (Get-FileHash -LiteralPath $trustFile -Algorithm SHA256).Hash.ToLowerInvariant()
New-ItemProperty -LiteralPath $regPath -Name 'QF_WP12_TRUST_STORE' -PropertyType String -Value $trustFile | Out-Null
New-ItemProperty -LiteralPath $regPath -Name 'QF_WP12_TRUST_STORE_SHA256' -PropertyType String -Value $pin | Out-Null
```

Ces commandes changent le registre machine et les ACL : l'Owner les exécute manuellement après validation du compte, des droits administratifs et de la sauvegarde. Elles ne sont pas exécutées par WP12-S.

**Vérification indépendante requise.**

```powershell
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
$trustFile = 'C:\ProgramData\QFSolver\wp12-owner-trust.json'
Get-ItemProperty -LiteralPath $regPath -Name QF_WP12_TRUST_STORE,QF_WP12_TRUST_STORE_SHA256
Get-FileHash -LiteralPath $trustFile -Algorithm SHA256
icacls 'C:\ProgramData\QFSolver'
icacls $trustFile
Get-Acl -LiteralPath $trustFile | Format-List
Get-Acl -LiteralPath 'Registry::HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment' | Format-List
```

Un administrateur indépendant vérifie que le hash fichier est identique au pin, que le compte runner lit le trust store, qu'il ne peut modifier ni le fichier, ni son répertoire, ni le pin HKLM et que la clé publique correspond à l'Owner. Tester les droits d'écriture sur un fichier factice placé sous une ACL équivalente, jamais en tentant de modifier le trust store réel.

**PASS.** Schéma valide, clé publique 32 octets, clé non révoquée, principal justifié hors runner, pin exact, chemin local hors checkout, ACL vérifiées, compte runner non administrateur et sans accès d'écriture au pin/fichier.
**FAIL.** Toute divergence de hash, ACL héritée non maîtrisée, principal non attribuable, clé de provenance incertaine, configuration partielle ou droit d'écriture runner : laisser `OWNER_TRUST_NOT_CONFIGURED`/exécution refusée et corriger sous contrôle Owner.

**Retour arrière.** Conserver une sauvegarde sécurisée du fichier public, des ACL et de l'état initial HKLM. Ne retirer que les deux valeurs créées par cette action, et seulement après comparaison à l'inventaire initial; restaurer les ACL sauvegardées. Ne pas supprimer une valeur préexistante ni écraser une configuration concurrente. Une rotation/révocation requiert un changement signé du trust store et de son pin, une nouvelle revue et la conservation des décisions antérieures.

## OWNER_ACTION_REQUIRED — O-2 : approuver la canonicalisation et la validité temporelle

**Action exacte.** Choisir une règle de sérialisation commune au signataire et au vérificateur, plus le moyen de vérifier l'heure d'expiration.

**Constat.** Le vérificateur utilise un JSON UTF-8 à clés triées et séparateurs compacts avec NaN/Inf rejetés. Ce n'est pas certifié comme RFC 8785 et aucun outil Owner de signature conforme n'est livré. L'horloge locale sert à `not_before_utc` / `expires_utc` sans attestation externe.

**Décision recommandée.** Avant toute clé réelle, fournir un profil canonique versionné et des vecteurs synthétiques connus que les implémentations de signature et vérification doivent toutes deux valider; effectuer les tests avec une clé éphémère. Choisir également une politique de synchronisation/écart d'horloge acceptable. Aucun secret n'est requis pour cette revue.

**PASS.** La même séquence d'octets est obtenue à partir des vecteurs sur l'outil Owner et le validateur; mutation, Unicode, valeurs limites et expirations sont refusés comme attendu; l'Owner approuve la source de temps.
**FAIL.** Toute divergence de bytes ou dépendance à une horloge non approuvée : aucune décision réelle n'est signée.

## OWNER_ACTION_REQUIRED — O-3 : séparer compte d'exécution et stockage

**Action exacte.** Choisir un compte standard dédié; configurer des ACL qui rendent le checkout, les fixtures et les archives v0.2.11/v0.2.12 en lecture seule; ne rendre inscriptible que la destination unique de preuves et le stockage temporaire explicitement approuvés. Le compte doit pouvoir lire le trust store, pas le modifier.

Un Job Object ne sandboxe pas les accès fichiers. Le processus enfant hérite des autorisations de son compte. Pour une assurance contre code non fiable ou une menace d'écriture concurrente, utiliser une VM ou un environnement isolé avec sources/archives montées en lecture seule et volume de preuve séparé. Le Job R2 n'impose pas de quota CPU, de threads ou de stockage; si ces limites sont requises, choisir un environnement qui les impose ou refuser le lot.

**Vérification.** Revue des ACL effectives par administrateur distinct; tests d'accès lecture/écriture sur fichiers factices dans chaque racine; démontrer que l'archive reste non modifiable par le compte runner; vérifier la terminaison des processus factices via Job Object. Ne pas tester d'écriture sur une archive de preuve réelle.

**PASS.** Compte non administrateur et séparation démontrée entre sources protégées et sorties autorisées.
**FAIL.** Si le processus peut modifier les archives, le lancement est refusé; corriger les ACL ou retenir un hôte isolé.

## OWNER_ACTION_REQUIRED — O-4 : figer WP12-1 après décision de périmètre

**Action exacte.** Approuver une nouvelle révision du manifeste qui lie le contenu exact, le périmètre, l'environnement, l'interpréteur, les ressources et les sorties; conserver les R1/R2 existants comme historiques.

Décisions requises :

1. Retirer `test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume` de WP12-1 vers WP12-2 ou approuver explicitement cette unité Newmark. Elle appelle `solve_model(model)` afin de produire un checkpoint courant avant de vérifier le refus du checkpoint legacy : ce n'est pas un simple contrôle documentaire ou algébrique.
2. Déplacer `test_v2_checkpoint_metadata_identity_tampering_fails_integrity` vers WP12-3 ou approuver explicitement cette unité de checkpoint non linéaire comme vérification transversale. Le code et le test helper direct doivent être ajoutés à l'inventaire par fichier.
3. Décider si `test_prepared_identity_is_deterministic_and_dof_maps_are_defensive` reste dans WP12-1 : il prépare un modèle et dépend du plan d'assemblage, donc couvre aussi le dispatch d'assemblage partagé.
4. Calculer des empreintes exactes pour les valeurs inline par une extraction déterministe et versionnée; le champ actuel `byte_sha256` dit `Compute for extracted bytes at freeze` et ne constitue pas un hash.
5. Épingler le chemin absolu du Python/venv, les versions/chemins des dépendances, lock d'environnement, variables de threads, budgets exacts, limites dures vs observées et destination exclusive. `python` et les budgets `null` ne définissent pas encore une commande/enveloppe reproductible.
6. Décider si la seule vérification dense analytique à 2 DDL et les invariants algébriques satisfont le gate visé. Ne pas les présenter comme validation de chaîne FEM, convergence ou qualification générale.

**PASS.** Manifeste révisé complet, hash calculé, nodeids exacts, tous fichiers et dépendances directes identifiés, fixtures gelées, environnement/budgets/destination décidés et approbation signée séparée.
**FAIL.** Tout placeholder, dépendance non inventoriée, unité hors scope ou limite non applicable maintient `PREPARED_NOT_AUTHORIZED`.

## OWNER_ACTION_REQUIRED — O-5 : ancrer les reçus et autoriser séparément

**Action exacte.** Choisir un stockage indépendant append-only ou une archive Owner contrôlée pour le hash initial, chaque décision signée, le ledger, les stdout/stderr, les reçus et le hash final. Le ledger local est seulement append-only logique : un acteur en écriture peut réécrire toutes les lignes et leurs hashes.

Avant campagne, une nouvelle implémentation d'`EXECUTE` doit établir dans l'ordre l'authentification, le manifeste, les identités, l'environnement, l'intégrité des entrées, les ressources, le ledger, la destination, la sélection réelle du nodeid et le résultat/oracle. Un code retour zéro seul n'est pas un PASS scientifique. L'Owner signe ensuite une décision nouvelle et propre à la campagne/tentative. R2 reste désactivé; cette mission n'active pas EXECUTE.

**PASS.** Reçu et ledger archivés par un acteur/système indépendant avec vérification des hashes, plus revue d'activation et décision Owner propre à l'unité.
**FAIL.** Sans ancrage, intégrité de sortie ou orchestration revue, aucun lancement scientifique.
