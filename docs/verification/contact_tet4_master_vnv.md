---
doc_id: DOC-VNV-CONTACT-TET4-MASTER-004
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# V&V contact avec face maitre TET4 deformable

## Objet

`VNV-CONTACT-TET4-MASTER-FACE-004` isole le transfert normal du contact vers
une face frontiere d'un solide TET4 reel. Les trois noeuds de la face sont
bloques tangentiellement et relies au quatrieme noeud du tetraedre; le noeud
esclave porte un ressort normal de `1000 N/m` et une charge de `200 N`.

La projection initiale utilise les poids barycentriques `[0.5, 0.25, 0.25]`.
Le contact applique donc la force normale repartie aux trois noeuds de la
face, lesquels se deplacent sous la raideur EF du tetraedre.

## Reference EF independante

Une resolution sans contact applique une charge unitaire suivant `-Z` aux
trois noeuds maitres, avec la meme repartition barycentrique. Sa compliance
normale mesuree est :

$$
c_m=-b^T u_m^{(1)}.
$$

Pour une pression inconnue $p$, l'equilibre du ressort esclave et la fermeture
du gap donnent :

$$
p = \frac{F/k_s-g_0}{1/k_s+c_m}.
$$

La resolution contactee est acceptee lorsque pression, gap, deplacement
esclave et deplacements normaux de la face retrouvent cette reference EF sous
les tolerances ecrites dans `summary.json`.

## Execution et preuves

```powershell
python .\qf_solver.py verify-contact --output .\results\VNV-CONTACT-V1-001
```

Le sous-dossier `tet4_master_face` contient `summary.json`, `report.md`,
`tet4_master_deformation.png` et `vnv_manifest.json`. Le PNG montre le
tetraedre, sa face maitre, le noeud esclave et la deformee amplifiee. Le test executable est
`tests/verification/test_contact_tet4_master_vnv.py`.

## Limites

Cette etude ne valide que le mouvement normal d'une face TET4 plane, avec
directions tangentielles stabilisees, normale et coordonnees barycentriques
figees. Elle ne prouve ni une recherche de contact de surface generale, ni
le contact surface-surface, le glissement, les grandes transformations ou une
correlation externe sans etat actif presuppose. La correlation Code_Aster
borne correspondante est documentee dans
[`VNV-CONTACT-CODEASTER-TET4-MASTER-004`](contact_code_aster_tet4_vnv.md).
Le statut reste donc `experimental`.
