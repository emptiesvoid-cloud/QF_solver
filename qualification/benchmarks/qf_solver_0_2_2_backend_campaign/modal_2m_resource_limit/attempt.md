# Limite de ressource : modal 2M DDL

La tentative SLEPc à `2 044 416` DDL et deux rangs MPI a été arrêtée par le
conteneur avec le signal `9` pendant la factorisation shift-invert. La mémoire
observée était d'environ `33,5 GiB`, avec environ `24 GiB` par processus au
moment du contrôle.

Cette sortie ne constitue pas une validation modale multi-million. Elle ferme
en revanche le diagnostic du chemin : le shift-invert direct doit rester borné
aux tailles modales intermédiaires tant qu'un opérateur spectral itératif,
une factorisation distribuée réutilisable ou une stratégie de réduction n'est
pas disponible.
