# Profil d'execution du backend 0.2.2a0

Ce profil ferme la condition R1 de la revue Owner sans modifier les anciens
manifestes de preuve ni leurs empreintes SHA-256.

| Champ | Valeur |
| --- | --- |
| Image | `qf-solver-large:0.2.0` |
| Digest | `sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8` |
| `slepc4py` | `3.25.1` |
| `petsc4py` | `3.25.1` |
| CPU visible | AMD Ryzen 5 5500 |
| Coeurs logiques visibles | `12` |
| Memoire visible | `49 275 492 KiB`, soit environ `46,97 GiB` |
| Limite cgroup memoire | `max` |
| Limite cgroup CPU | `max 100000` |

La mesure a ete realisee le 2026-08-23 dans l'image epinglee. La memoire et le
processeur sont les ressources visibles par le conteneur au moment du probe ;
ils ne constituent pas une generalisation de performance a une autre machine.
Le profil est un addendum de tracabilite et n'altere aucun manifeste historique.
