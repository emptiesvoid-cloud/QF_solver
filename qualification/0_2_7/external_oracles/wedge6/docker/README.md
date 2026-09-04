# WP09-R Code_Aster headless oracle

The pinned `simvia/code_aster:18.1.0` image contains `mpi4py`, NumPy and the
MPI/MED libraries in the `simvia_env` Spack view. Its stock Code_Aster profile
does not expose that view, so `run_aster --no-mpi` still imports
`mpi4py` from `run_aster.run_aster_main` and fails before the command file.

The derived image exposes the existing view through `PYTHONPATH` and
`LD_LIBRARY_PATH`. It does not install packages on the host and does not use a
GUI. `--no-mpi` means no `mpiexec` relaunch; Code_Aster still initializes a
one-process `mpi4py` communicator internally.

Build the local reproducible image from the repository root:

```text
docker build --pull=false -f qualification/0_2_7/external_oracles/wedge6/docker/Dockerfile -t qf-solver/code-aster-headless:18.1.0 .
```

Run the controlled affine PENTA6 deck:

```text
docker run --rm --mount type=bind,source=<deck-directory>,target=/work -w /work qf-solver/code-aster-headless:18.1.0 WP09R-A-penta6-affine.export --no-mpi
```

The `.export` links the `.mail` on unit 20 and writes the text result, MED
result, and machine-readable primary observables. The image digest, deck
digests, output digest and comparison are recorded in
`qualification/0_2_7/vnv_v2/wp09r_code_aster_evidence.json`.
