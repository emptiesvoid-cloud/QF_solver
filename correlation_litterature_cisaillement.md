# Correlation avec la litterature du cisaillement

Ce document racine est conserve pour compatibilite. La formulation maintenue
de Reissner-Mindlin, les points de tying MITC4, le shear locking, les essais et
les references primaires sont dans :

- [`docs/elements/mitc4.md`](docs/elements/mitc4.md) ;
- [`docs/demonstrations/coques.md`](docs/demonstrations/coques.md) ;
- [`docs/reference/references.md`](docs/reference/references.md).

Construire le site local avec :

```powershell
python .\scripts\build_docs.py --profile engineering
python -m mkdocs serve --dev-addr 127.0.0.1:8000
```
