"""Compare saved WP13-01K states using the frozen numerical gates."""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qualification/0_2_8/wp13_01k_runtime"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    contract = json.loads((OUT.parent / "wp13_01k_contract.json").read_text())
    gates = contract["gates"]
    prefix = "replay" if args.replay else "partition"
    first = np.load(OUT / (args.labels[0]+".npz"))
    base = json.loads((OUT / (args.labels[0]+".json")).read_text())["result"]
    comparisons = []
    for label in args.labels[1:]:
        state = np.load(OUT / (label+".npz"))
        result = json.loads((OUT / (label+".json")).read_text())["result"]
        values = {}
        for key in ("displacement", "reactions", "energy"):
            a,b = first[key],state[key]
            values[key] = float(np.linalg.norm(a-b) / max(
                float(np.linalg.norm(a)),float(np.linalg.norm(b)),np.finfo(float).tiny))
        passed = (
            values["displacement"] <= gates[prefix+"_displacement_relative_l2"]
            and values["reactions"] <= gates[prefix+"_reaction_relative_l2"]
            and values["energy"] <= gates[prefix+"_energy_relative"])
        values["residual_difference"] = abs(result["free_residual_relative"]-base["free_residual_relative"])
        values["equilibrium_difference"] = abs(result["equilibrium_relative"]-base["equilibrium_relative"])
        if args.replay:
            passed = passed and result["iterations"] == base["iterations"]
            passed = passed and values["residual_difference"] <= gates["replay_residual_absolute_difference"]
        comparisons.append({"reference":args.labels[0],"label":label,"values":values,
                            "pass":passed,"same_model":result["model_digest"]==base["model_digest"],
                            "raw_digest_equal":result["displacement_digest"]==base["displacement_digest"]})
    payload = {"mode":prefix,"comparisons":comparisons,
               "pass":all(r["pass"] and r["same_model"] for r in comparisons)}
    (OUT / (args.output+".json")).write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps(payload),flush=True)
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
