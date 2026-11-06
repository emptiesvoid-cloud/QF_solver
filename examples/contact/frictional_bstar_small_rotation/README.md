# Experimental B* small-rotation frictional contact

**Maturity: `EXPERIMENTAL_BOUNDED` (0.2.12 integration candidate; not a released capability).**

This example uses the archived R14 nine-step, one-slave-node/one-master-triangle
configuration. It demonstrates the opt-in API route and preserves the exact
fixture used for R14/R16; fixture SHA-256:
`b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5`.

## Scope

The route is linear static frictional node-to-triangle contact with one
initially frozen slave/master pair, a reference master triangle, and
first-order small-rotation transfer. The checked fixture sets
`analysis.contact_tangential_transfer` to
`small_rotation_work_conjugate`; the JSON reader places this accepted analysis
field in the model's analysis parameters. The default remains `legacy` when
the transfer option is omitted.
There is no implemented or qualified numeric angle cutoff; the caller must
keep rotations within the small-rotation regime.

Finite sliding or updated projection, large rotations, multiple pairs or
patches, a globally consistent slip tangent, general spatial convergence, and
industrial/production use are outside this contract. See
[`B* transfer mechanics`](../../../docs/contact_small_rotation_work_conjugate_transfer.md)
for the operator, units, and derivation.

## Run explicitly

From the repository root in an environment with the project dependencies:

```bash
python examples/contact/frictional_bstar_small_rotation/run_example.py
```

The command above only prints instructions. To launch the FEM calculation,
explicitly pass `--run` and choose an output path:

```bash
python examples/contact/frictional_bstar_small_rotation/run_example.py --run --output output/bstar_small_rotation_result.json
```

The script imports the supported `qf_solver` facade, loads the checked-in
fixture, calls `solve_model`, and serializes with `save_result`. Running it
performs a new calculation; it is never invoked by unit tests or documentation
generation.

## Archived comparison reference

R14 and the integrated R16 replay reported nine accepted load steps, stick at
steps 1–7, and slip at steps 8–9. The R17/R18 offline replay found a maximum
gap of `1.3878e-17 m`, maximum reconstructed Coulomb slip difference of
`5.457e-12 N`, and independent raw moment `1.8780385144291777e-12 N·m` against
the unchanged `0.002 N·m` limit. These are archived case-specific reference
observations, not promises for another environment or a qualification result.
The R16 pytest FAIL is retained as historical evidence; R17/R18 replayed its
original output archive without rerunning FEM.

Compare a new result against the archived run on the same fixture and source
revision. Check accepted steps, contact states, normal pressure, Coulomb
consistency, gaps, reactions and the raw moment. Do not infer physical
superiority over `legacy`, finite-sliding validity, or mesh convergence.

Evidence and exclusions are tracked in
[`WP-C01 R19 capability record`](../../../qualification/0_2_12/wp_c01_bstar_capability_record.json)
and the [integration progress ledger](../../../qualification/0_2_12/v0_2_12_integration_progress_ledger.md).
