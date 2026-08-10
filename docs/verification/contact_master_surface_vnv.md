---
doc_id: DOC-VNV-CONTACT-MASTER-SURFACE-005
revision: 0.3
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# V&V selection initiale de surface maitre

## Objet

`VNV-CONTACT-MASTER-SURFACE-005` controle une surface plane de deux triangles
adjacents. La projection du noeud esclave appartient strictement a la seconde
face. Le solveur doit la choisir avant son active-set et ne doit pas imposer la
premiere face, qui est incompatible.

La charge et le ressort normal donnent la reference fermee suivante :

$$
g=0, \qquad p=100\ \mathrm{N}, \qquad u_{s,z}=-0.1\ \mathrm{m}.
$$

L'etude verifie la facette selectionnee, le gap, la pression et le
deplacement. Elle produit un PNG de la projection et un manifeste SHA-256.

## Execution

```powershell
python .\qf_solver.py verify-contact --output .\results\VNV-CONTACT-V1-001
```

Le sous-dossier `master_surface` contient le rapport, le resultat et
`master_surface_selection.png`. Le test direct est
`tests/verification/test_contact_master_surface_vnv.py`.

## Recherche actualisee sur surface pliee

Le second cas utilise deux facettes adjacentes non coplanaires. Sous une force
tangentielle et une charge normale, l'esclave part de la face `0`, atteint la
face `1` et la contrainte est reconstruite avec sa nouvelle normale :

$$
\mathbf n_1 =
\frac{[-0.5,-0.5,1]^T}{\sqrt{1.5}}
= [-0.408248,-0.408248,0.816497]^T.
$$

La position finale doit verifier simultanement `g=0` et le plan de la seconde
facette, `z=0.5(x+y-1)`. Le PNG
`master_surface_folded_updated_switch.png` rend visible le pli et la normale
actualisee. Cette etude apporte une preuve interne de relocalisation de
facette **et** de normale ; elle ne devient pas une preuve de grand glissement.

## Patch esclave a trois noeuds

Le meme pli est ensuite sollicite par trois noeuds esclaves formant un petit
triangle discret. Chaque noeud porte un tiers des ressorts et des charges. Les
trois projections passent de la face `0` a la face `1`, retrouvent la normale
inclinee et ferment leur gap au seuil machine. Cette etape fournit un champ de
deplacements moyen comparable a une future surface esclave Code_Aster, sans
pretendre encore que les deux discretisations sont identiques.

## Limites

La campagne couvre aussi le mode `contact_search_mode="updated"` : une
translation tangentielle fait passer l'esclave de la face 0 a la face 1, et la
contrainte normale est relocalisee jusqu'a stabilisation. Elle reste une
iteration bornee de petites translations, sans frottement. Le grand glissement,
les intersections de surfaces, la topologie variable et le contact
surface-surface restent hors scope. La commutation de facette en recherche
actualisee n'a pas encore de correlation externe independante : elle ne porte
donc qu'un verdict interne. Le statut demeure `experimental`.

La cinematique de la **normale finale** sur la surface pliee est neanmoins
correlee avec Code_Aster dans
[`VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006`](contact_code_aster_folded_vnv.md).
Cette preuve impose la facette finale et ne ferme donc pas la detection de
commutation, qui reste interne.
