# VNV-MITC4-MODAL-PLATE-003

## Objet

Quatre premiers modes de flexion d'une plaque carree MITC4 simplement appuyee,
compares a la solution de Navier. Frequences analytiques `(11, 12, 21, 22)` :
`48.406724, 121.016810, 121.016810, 193.626896 Hz`.

| Maillage | Elements | Frequences MITC4 (Hz) | Erreurs | MAC 11 | MAC sous-espace 12/21 | MAC 22 |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 4x4 | 16 | 51.8855, 159.6628, 159.6628, 259.9424 | 7.187 %, 31.934 %, 31.934 %, 34.249 % | 1.000000 | 1.000000 | 1.000000 |
| 6x6 | 36 | 49.8873, 135.7304, 135.7304, 219.2389 | 3.059 %, 12.158 %, 12.158 %, 13.228 % | 1.000000 | 1.000000 | 1.000000 |
| 8x8 | 64 | 49.2123, 128.8390, 128.8390, 207.2541 | 1.664 %, 6.464 %, 6.464 %, 7.038 % | 1.000000 | 1.000000 | 1.000000 |
| 12x12 | 144 | 48.7326, 124.2864, 124.2864, 199.2657 | 0.673 %, 2.702 %, 2.702 %, 2.912 % | 1.000000 | 1.000000 | 1.000000 |
| 16x16 | 256 | 48.5605, 122.7522, 122.7522, 196.5556 | 0.318 %, 1.434 %, 1.434 %, 1.513 % | 1.000000 | 1.000000 | 1.000000 |

Statut : **PASS**.

![Convergence](VNV-MITC4-MODAL-PLATE-003-convergence.png)

![Premier mode](VNV-MITC4-MODAL-PLATE-003-mode-11.png)

## Limites

- The Navier reference assumes Kirchhoff thin-plate behavior.
- The repeated (1,2)/(2,1) eigenspace is compared as a subspace because individual vectors are not unique.
- A same-mesh Abaqus S4R/S4 correlation remains pending.
