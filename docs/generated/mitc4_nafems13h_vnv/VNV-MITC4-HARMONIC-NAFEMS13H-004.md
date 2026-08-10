# VNV-MITC4-HARMONIC-NAFEMS13H-004

## Objet

Correlation externe de la reponse harmonique MITC4 avec le Test 13H NAFEMS
publie dans la documentation Abaqus/Standard 2024. Le modele QF_solver reprend
le maillage `8x8`, la geometrie, les blocages, la pression, l'amortissement de
Rayleigh et les 200 frequences du fichier officiel `nfh13f4x.inp`.

| Resultat | QF_solver | Abaqus S4R | Abaqus S4 | NAFEMS |
| --- | ---: | ---: | ---: | ---: |
| Pic deplacement (mm) | 44.271899 | 45.380000 | 44.930000 | 45.420000 |
| Pic S11 face (N/mm2) | 30.818589 | 30.370000 | 31.260000 | 30.030000 |
| Frequence du pic (Hz) | 2.425829 | 2.405000 | 2.420000 | 2.377000 |

- ecart deplacement QF/Abaqus: `2.442 %`;
- ecart frequence QF/Abaqus: `0.866 %`;
- ecart S11 QF/Abaqus: `1.477 %`;
- ecart S11 QF/Abaqus S4: `1.412 %`;
- ecart deplacement QF/NAFEMS: `2.528 %`;
- ecart frequence QF/NAFEMS: `2.054 %`;
- ecart S11 QF/NAFEMS: `2.626 %`;
- residu relatif maximal: `3.881e-10`.

Statut : **PASS**.

![Reponse frequentielle](VNV-MITC4-HARMONIC-NAFEMS13H-004-response.png)

![Contrainte harmonique S11](VNV-MITC4-HARMONIC-NAFEMS13H-004-stress-response.png)

![Deformee au pic](VNV-MITC4-HARMONIC-NAFEMS13H-004-deformed.png)

## Provenance et limite

Source primaire: https://docs.software.vt.edu/abaqusv2024/English/SIMACAEBMKRefMap/simabmk-c-forcedvibrationtest13h.htm

La contrainte comparee est l'amplitude de `S11` en face superieure au noeud
central, obtenue par moyenne complexe des quatre facettes adjacentes, comme la
sortie Abaqus `POSITION=AVERAGED AT NODES, ELSET=EMID`.
