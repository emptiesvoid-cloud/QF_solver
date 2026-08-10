---
doc_id: DOC-ELEM-FRICTION-001
revision: 0.2
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Contact unilateral avec frottement

## Perimetre experimental

Cette extension conserve le contact normal noeud esclave - triangle maitre de
QF_solver et ajoute un frottement de Coulomb **regularise**. Le domaine est
intentionnellement borne : statique lineaire, petites transformations,
normale et projection initiales figees, methode directe et DDL de translation
stabilises par le modele. Ce n'est ni un algorithme surface-surface ni un
contact a grand glissement.

Le JSON declare un coefficient `friction_coefficient = mu >= 0` et, des que
`mu > 0`, une raideur de regularisation `tangential_stiffness = kt > 0`.
L'absence de ces deux champs garde exactement le chemin sans frottement.

```json
{
  "contacts": [{
    "name": "rough_plane",
    "slave_node": 3,
    "master_nodes": [0, 1, 2],
    "friction_coefficient": 0.5,
    "tangential_stiffness": 10000.0
  }]
}
```

## Base locale et cinematique tangentielle

La normale unitaire $n$ est celle du triangle maitre ordonne. Le premier
vecteur tangent $t_1$ est l'arete maitre $x_2-x_1$, projetee dans le plan puis
normalisee; le second est $t_2=n\times t_1$. Cette construction donne une
base orthonormee directe $(t_1,t_2,n)$, tracable dans chaque resultat de
contact.

Avec les memes poids barycentriques $b_i$ que pour le gap normal, le
glissement relatif est :

$$
s =
\begin{bmatrix}
t_1^T\\t_2^T
\end{bmatrix}
\left(u_s-\sum_i b_i u_i\right).
$$

Les forces publiees dans l'audit sont les efforts internes qui s'opposent a
ce glissement. Leur travail $f_t^T s$ est donc non negatif dans cette
convention.

## Loi de Coulomb regularisee

Le contact normal satisfait toujours :

$$
g\geq0,\qquad p=-\lambda\geq0,\qquad gp=0.
$$

L'effort tangent d'essai est $q_{\mathrm{trial}}=k_t s$, et la borne de
Coulomb vaut $q_{\max}=\mu p$. Deux etats sont exposes :

$$
\begin{cases}
\|q_{\mathrm{trial}}\|\leq q_{\max} &\Rightarrow\quad
\texttt{stick},\quad q=q_{\mathrm{trial}},\\
\|q_{\mathrm{trial}}\|>q_{\max} &\Rightarrow\quad
\texttt{slip},\quad q=q_{\max}
\dfrac{q_{\mathrm{trial}}}{\|q_{\mathrm{trial}}\|}.
\end{cases}
$$

En adhesion, la tangente ajoutee est
$K_t=k_t(B_{t1}^T B_{t1}+B_{t2}^T B_{t2})$. En glissement, QF_solver tente
d'abord une iteration externe directe : la force tangentielle bornee de
l'iteration precedente est appliquee, puis la pression, l'etat et la force
sont recalcules. Si ce point fixe alterne sur une structure deformable, un
repli resout les deux composantes de l'effort tangent actif avec la contrainte
normale exacte. Si la racine hybride est mal conditionnee, une minimisation
des moindres carres a region de confiance applique une globalisation au meme
residu actif. Avant ce dernier repli, `active_slip_consistent_newton` calcule
la reponse lineaire exacte du systeme selle a chaque effort tangent unitaire,
puis la combine avec la derivee analytique de la projection de Coulomb. Cette
tangente est donc consistante sur l'ensemble actif et la branche de glissement
figes; une recherche lineaire d'Armijo refuse un pas qui augmente le residu.
La reference de glissement du pas precedent reste gelee pendant cet equilibre
et n'est mise a jour qu'apres convergence. Le diagnostic publie la strategie
`direct`, `active_slip_root`, `active_slip_consistent_newton` ou
`active_slip_least_squares`. La derivee ne traverse pas encore une ouverture,
une fermeture ou un changement de normale : ce n'est pas une formulation
surface-surface a grands glissements.

## Resolution et diagnostics

La fermeture normale est imposee par le meme systeme selle a multiplicateurs
de Lagrange que le contact sans frottement. L'iteration termine lorsque
l'ensemble actif, les etats `open`/`stick`/`slip` et la force tangentielle ne
changent plus dans `contact_friction_tolerance`.

Chaque ligne d'audit contient : gap, pression, complementarite, base locale,
glissement local, force tangentielle, norme, borne $\mu p$, et etat. Le bilan
de moments publie egalement sa valeur brute et la correction de transport du
point de contact; celle-ci retire le couple artificiel cree lorsqu'une force
tangentielle est sommee au noeud esclave encore separe dans la configuration
de reference.

## Chemin de charge avec memoire

Par defaut, `contact_load_steps` repartit proportionnellement toutes les
charges nodales sur le nombre d'increments demande. Pour un cycle, le champ
`contact_load_history` contient une ligne de facteurs par charge nodale, dans
l'ordre du tableau JSON `loads`. Les charges reparties ne sont pas admises
avec ce chemin V1.

```json
"contact_load_history": [
  [0.0, 1.0],
  [0.2, 1.0],
  [1.0, 1.0],
  [-1.0, 1.0],
  [0.0, 1.0]
]
```

Pour chaque paire, QF_solver conserve une reference de glissement $s_p$.
L'essai elastique devient $q_{trial}=k_t(s-s_p)$. Lors du glissement,
$s_p$ est corrige pour ramener l'effort sur le cone de Coulomb. L'audit
publie les references, les forces locales et le travail dissipatif par pas.
La non-regression couvre une rampe a pression constante avec `1` a `16` pas;
elle ne doit pas etre interpretee comme une invariance pour un chemin dont la
pression normale varie.

## Verification interne et limites

`tests/unit/test_frictional_contact.py` verifie :

- separation sans force tangentielle ;
- adhesion en dessous de la borne de Coulomb ;
- glissement a $\|q\|=\mu p$, dissipation positive et equilibre global ;
- cycle adhesion-glissement avec memoire de glissement et changement de sens ;
- rejet d'un coefficient positif sans regularisation tangentielle.

Le cas `examples/frictional_contact_plane.json` est executable avec :

```powershell
python .\qf_solver.py solve --input .\examples\frictional_contact_plane.json --output .\results\friction.json
```

`VNV-CONTACT-FRICTION-TET4-STRUCTURAL-002` ajoute quatre maillages de barre
TET4 deformable. Il verifie fermeture normale, cone de Coulomb et les branches
`stick`/`slip`; une transition vers l'adherence sous raffinement est possible
si la reaction normale augmente. La campagne externe
`VNV-CONTACT-FRICTION-CODEASTER-CONTINUE-003` couvre le glissement sature
sur une surface triangulaire avec un ecart `UX` de `0,6070 %`; l'adherence et
les faces structurelles deformables restent a comparer. Restent obligatoires
avant une hausse de maturite : une tangente consistante pour les cas fortement
non lineaires et une correlation externe structurelle complete. Sont hors scope : grand
glissement, changement de normale, usure,
cohesion, thermique, vitesse, dynamique, MPC/RBE et contact multiple
complexe.

Cette page est reliee a `REQ-CONTACT-001`, `FORM-CONTACT-002` et aux tests
unitaires du contact.

## Contrat documentaire et demonstration

| Rubrique exigee | Contenu et preuve |
| --- | --- |
| Geometrie et DDL | Noeud esclave, facette maitre, normale et base tangentielle. |
| Formulation mathematique | Contact unilateral et Coulomb regularise, adhesion/glissement. |
| Integration et algorithme | Active-set normal et retour tangentiel incremental. |
| Exemple executable | `python .\qf_solver.py solve --input .\examples\frictional_contact_plane.json --output .\results\friction.json` |
| Maillage | Facette plane puis assemblages TET4 structurels. |
| Chargement et conditions limites | Compression normale, effort tangentiel et supports du JSON. |
| Tableau de resultats | [Rapport V&V](../verification/contact_frottement_vnv.md). |
| Figure de deformee | Comparaison des cas de frottement ci-dessous. |
| Invariants | Kuhn-Tucker, $\lVert t_t\rVert\le\mu p_n$, equilibre et statut stick/slip. |
| Convergence | Sensibilite maillage/pas et correlation Code_Aster. |
| Limites | Regularisation, petites transformations et pas de grand glissement. |
| References | `FORM-CONTACT-002`, `REQ-CONTACT-001` et preuves externes. |

![Comparaison des cas de frottement](../assets/generated/contact_friction_block_comparison.png){ .result-figure }

Owner review requise avant tout changement de maturite; demonstration et
qualification restent distinctes.
