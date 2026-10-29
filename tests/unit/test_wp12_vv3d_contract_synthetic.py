"""Synthetic VV3D contract tests; no FEM process or reservation."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import pytest
from scripts import wp12_vv3d_contract as c


def fixture_contract():
    cases=[]
    for cid in sorted(c.INITIAL_IDS):
        family=cid.split('-')[1]
        cases.append({"case_id":cid,"phase":"INITIAL","nodeid":f"tests/unit/test_vv3d.py::test_case[{cid}]",
            "family":family,"mesh_sha256":"a"*64,"manifest_sha256":"b"*64,"oracle_sha256":"c"*64,
            "criteria_sha256":"d"*64,"mesh_path":f"{cid}-mesh.json","manifest_path":f"{cid}-manifest.json",
            "oracle_path":"oracle.py","criteria_path":"criteria.json",
            "selected_dofs":30,"timeout_seconds":1200,"rss_soft_limit_mib":4096,
            "max_attempts":1,"trigger":None})
    return {"schema":c.SCHEMA,"campaign_id":c.CAMPAIGN,"budget":dict(c.BUDGET),
        "controller_fingerprint":"e"*64,"scientific_fingerprint":"f"*64,"cases":cases,
        "adaptive_catalog":{"catalog_sha256":"a"*64,"candidates":{
            candidate:{"candidate_sha256":"b"*64,"mesh_sha256":"c"*64,
                      "criteria_sha256":"d"*64,"rule_sha256":"e"*64}
            for candidate in sorted(c.QPOST_IDS | {f"VV3D-ADAPT-{family}-{kind}"
                for family in ("TET4","TET10","HEX8","HEX20") for kind in ("H1","QLOAD")})}},
        "qpost_jobs":[{"job_id":job,"nodeid":f"tests/unit/test_vv3d.py::test_qpost[{job}]",
            "source_family":job.split("-")[2],"manifest_sha256":"1"*64,"oracle_sha256":"2"*64,
            "criteria_sha256":"3"*64,"manifest_path":f"{job}-manifest.json","oracle_path":f"{job}-oracle.txt",
            "criteria_path":f"{job}-criteria.json","timeout_seconds":1200,"rss_soft_limit_mib":4096,"max_jobs":1}
            for job in sorted(c.QPOST_IDS)],
        "transitions":{**dict.fromkeys(c.STOP_STATES,"STOP"),"PASS":"CONTINUE_INITIAL_ORDER_AND_TRIGGERED_ADAPTIVE",
                       "SCIENTIFIC_DEVIATION":"STOP"},
        "initial_ledger_sha256":"0"*64}


def validate(contract):
    base=fixture_contract()
    c.validate_contract(contract,registered_nodeids={x["nodeid"] for x in base["cases"]}
                        | {x["nodeid"] for x in base["qpost_jobs"]},
                        controller_fingerprint="e"*64,scientific_fingerprint="f"*64)


def test_vv3d_contract_accepts_and_refuses_invalid_budget_and_cases():
    good=fixture_contract()
    validate(good)
    mutants=[]
    for mutate in (
        lambda x:x["budget"].update(concurrency=True),
        lambda x:x["budget"].update(attempts_max=25),
        lambda x:x["cases"].pop(),
        lambda x:x["cases"][0].update(nodeid=x["cases"][1]["nodeid"]),
        lambda x:x["cases"][0].update(nodeid="tests/unit/test_unknown.py::test_unknown"),
        lambda x:x["cases"][0].update(selected_dofs=30001),
        lambda x:x["cases"][0].update(timeout_seconds=1201),
        lambda x:x["cases"][0].update(mesh_sha256="broken"),
        lambda x:x["transitions"].update(PROVENANCE_FAILURE="CONTINUE_REGISTERED"),
        lambda x:x.update(scientific_fingerprint="0"*64),
    ):
        bad=copy.deepcopy(good)
        mutate(bad)
        mutants.append(bad)
    for bad in mutants:
        with pytest.raises(c.VV3DContractError):
            validate(bad)


def test_vv3d_decision_binds_exact_raw_contract_and_case_order():
    contract=fixture_contract()
    validate(contract)
    raw=(json.dumps(contract,sort_keys=True,indent=2)+"\n").encode()
    sha=hashlib.sha256(raw).hexdigest()
    decision={"schema":c.DECISION_SCHEMA,"campaign_id":c.CAMPAIGN,"decision_id":"synthetic-owner-decision",
        "approved_by":"Owner","approved_at_utc":"2026-10-29T10:00:00Z","contract_sha256":sha,
        "case_ids":[x["case_id"] for x in contract["cases"]]
                   +[x["job_id"] for x in contract["qpost_jobs"]],"status":"APPROVED"}
    c.validate_decision(contract,decision,contract_bytes=raw)
    for bad in (dict(decision,status="NOT_AUTHORIZED"),dict(decision,contract_sha256="0"*64),
                dict(decision,case_ids=decision["case_ids"][:-1]),dict(decision,approved_by="other")):
        with pytest.raises(c.VV3DContractError):
            c.validate_decision(contract,bad,contract_bytes=raw)
    with pytest.raises(c.VV3DContractError):
        c.validate_decision(contract,decision,contract_bytes=raw+b" ")
    with pytest.raises(c.VV3DContractError):
        c.validate_decision(contract,decision,contract_bytes=b'{"schema":1,"schema":2}')


def test_vv3d_adaptive_cases_require_registered_trigger_and_explicit_transition():
    contract=fixture_contract()
    adaptive=copy.deepcopy(contract["cases"][0])
    adaptive.update(case_id="VV3D-ADAPTIVE-001",phase="ADAPTIVE",nodeid="tests/unit/test_vv3d.py::test_case[ADAPTIVE]",
        trigger={"source_case_id":contract["cases"][0]["case_id"],"observable":"energy_error",
                 "operator":"GT","threshold":0.02,"unit":"1"})
    contract["cases"].append(adaptive)
    source=contract["cases"][0]["case_id"]
    contract["transitions"]["SCIENTIFIC_DEVIATION"]={source:[adaptive["case_id"],contract["cases"][1]["case_id"]]}
    nodes={case["nodeid"] for case in contract["cases"]}|{job["nodeid"] for job in contract["qpost_jobs"]}
    c.validate_contract(contract,registered_nodeids=nodes,controller_fingerprint="e"*64,scientific_fingerprint="f"*64)
    for mutation in ("unknown_trigger","nonfinite","unlisted_transition","duplicate_transition"):
        bad=copy.deepcopy(contract)
        if mutation == "unknown_trigger":
            bad["cases"][-1]["trigger"]["source_case_id"]="VV3D-UNKNOWN"
        elif mutation == "nonfinite":
            bad["cases"][-1]["trigger"]["threshold"]=float("nan")
        elif mutation == "unlisted_transition":
            bad["transitions"]["SCIENTIFIC_DEVIATION"]={source:["VV3D-UNKNOWN"]}
        else:
            bad["transitions"]["SCIENTIFIC_DEVIATION"]={source:[adaptive["case_id"],adaptive["case_id"]]}
        with pytest.raises(c.VV3DContractError):
            c.validate_contract(bad,registered_nodeids=nodes,controller_fingerprint="e"*64,scientific_fingerprint="f"*64)


def test_adaptive_eligibility_requires_measured_trigger_or_approved_failure_route():
    contract=fixture_contract()
    source=contract["cases"][0]["case_id"]
    destination=copy.deepcopy(contract["cases"][0])
    destination.update(case_id="VV3D-ADAPT-TEST",phase="ADAPTIVE",nodeid="tests/unit/test_vv3d.py::test_adapt",
        trigger={"source_case_id":source,"observable":"energy_error","operator":"GT","threshold":0.02,"unit":"1"})
    contract["cases"].append(destination)
    contract["transitions"]["SCIENTIFIC_DEVIATION"]={source:[destination["case_id"]]}
    decision={"decision_id":"owner-decision"}
    receipt={"schema":"qf-wp12-vv3d-transition-eligibility-v1","campaign_id":c.CAMPAIGN,
        "contract_sha256":"1"*64,"decision_id":"owner-decision","decision_sha256":"2"*64,
        "source_case_id":source,"destination_case_id":destination["case_id"],"source_status":"PASS",
        "source_result_sha256":"3"*64,"transition_kind":"PASS_TRIGGER",
        "trigger_observation":{"observable":"energy_error","value":0.03,"unit":"1",
                               "operator":"GT","threshold":0.02,"result":True}}
    c.validate_transition_eligibility(contract,decision,contract_sha256="1"*64,decision_sha256="2"*64,
        source_case_id=source,destination_case_id=destination["case_id"],source_status="PASS",
        source_result_sha256="3"*64,source_observables={"energy_error":{"value":0.03,"unit":"1"}},receipt=receipt)
    bad=copy.deepcopy(receipt)
    bad["trigger_observation"]["value"]=0.01
    with pytest.raises(c.VV3DContractError):
        c.validate_transition_eligibility(contract,decision,contract_sha256="1"*64,decision_sha256="2"*64,
            source_case_id=source,destination_case_id=destination["case_id"],source_status="PASS",
            source_result_sha256="3"*64,source_observables={"energy_error":{"value":0.03,"unit":"1"}},receipt=bad)
    fail_receipt={**receipt,"source_status":"FAIL","transition_kind":"APPROVED_SCIENTIFIC_DEVIATION",
                  "trigger_observation":None}
    c.validate_transition_eligibility(contract,decision,contract_sha256="1"*64,decision_sha256="2"*64,
        source_case_id=source,destination_case_id=destination["case_id"],source_status="FAIL",
        source_result_sha256="3"*64,source_observables={},receipt=fail_receipt)
    with pytest.raises(c.VV3DContractError):
        c.validate_transition_eligibility(contract,decision,contract_sha256="1"*64,decision_sha256="2"*64,
            source_case_id=source,destination_case_id=destination["case_id"],source_status="TIMEOUT",
            source_result_sha256="3"*64,source_observables={},receipt=receipt)


def test_vv3d_artifact_bindings_are_confined_and_checked(tmp_path: Path):
    contract=fixture_contract()
    roots={kind:tmp_path/kind for kind in ("mesh","manifest","oracle","criteria")}
    for root in roots.values():
        root.mkdir()
    for case in contract["cases"]:
        rules=[{"id":"finite","classification":"CASE_GATE","operator":"ALL_TRUE","threshold":None,"unit":"1"},
               {"id":"det_j_positive","classification":"CASE_GATE","operator":"GT","threshold":0,"unit":"m3"}]
        rules += [{"id":name,"classification":"CASE_GATE","operator":"LE","threshold":1e-8,"unit":"1"}
                  for name in ("free_residual","energy_identity","force_closure","moment_closure")]
        artifacts={"mesh":json.dumps({"schema":"qf-wp12-vv3d-mesh-v1","family":case["family"],
                                      "summary":{"dofs":case["selected_dofs"]}}).encode(),
                   "criteria":json.dumps({"schema":"qf-wp12-vv3d-criteria-v1","criteria":rules}).encode(),
                   "oracle":b"synthetic analytic oracle"}
        for kind in ("mesh","criteria","oracle"):
            raw=artifacts[kind]
            case[f"{kind}_sha256"]=hashlib.sha256(raw).hexdigest()
            (roots[kind]/case[f"{kind}_path"]).write_bytes(raw)
        manifest={field:case[field] for field in ("case_id","nodeid","family","mesh_sha256","oracle_sha256",
                                                  "criteria_sha256","selected_dofs","timeout_seconds",
                                                  "rss_soft_limit_mib","max_attempts")}
        manifest.update(schema="qf-wp12-vv3d-case-manifest-v1",state="PREPARED_NOT_AUTHORIZED")
        raw=json.dumps(manifest).encode()
        case["manifest_sha256"]=hashlib.sha256(raw).hexdigest()
        (roots["manifest"]/case["manifest_path"]).write_bytes(raw)
    for job in contract["qpost_jobs"]:
        oracle=b"synthetic QPOST oracle"
        criteria=json.dumps({"schema":"qf-wp12-vv3d-qpost-criteria-v1","criteria":[{"id":"finite","operator":"ALL_TRUE"}]}).encode()
        job["oracle_sha256"]=hashlib.sha256(oracle).hexdigest()
        job["criteria_sha256"]=hashlib.sha256(criteria).hexdigest()
        (roots["oracle"]/job["oracle_path"]).write_bytes(oracle)
        (roots["criteria"]/job["criteria_path"]).write_bytes(criteria)
        manifest={"schema":"qf-wp12-vv3d-qpost-manifest-v1","state":"PREPARED_NOT_AUTHORIZED",
                  **{key:job[key] for key in ("job_id","nodeid","source_family","oracle_sha256","criteria_sha256",
                                               "timeout_seconds","rss_soft_limit_mib","max_jobs")}}
        raw=json.dumps(manifest).encode()
        job["manifest_sha256"]=hashlib.sha256(raw).hexdigest()
        (roots["manifest"]/job["manifest_path"]).write_bytes(raw)
    validate(contract)
    c.verify_artifact_bindings(contract,roots=roots)
    first=contract["cases"][0]
    criteria_path=roots["criteria"]/first["criteria_path"]
    manifest_path=roots["manifest"]/first["manifest_path"]
    original_criteria=criteria_path.read_bytes()
    original_manifest=manifest_path.read_bytes()
    original_criteria_sha=first["criteria_sha256"]
    original_manifest_sha=first["manifest_sha256"]
    changed=json.loads(original_criteria)
    changed["criteria"][0]["classification"]="CASE_DIAGNOSTIC"
    changed_bytes=json.dumps(changed).encode()
    criteria_path.write_bytes(changed_bytes)
    first["criteria_sha256"]=hashlib.sha256(changed_bytes).hexdigest()
    changed_manifest=json.loads(original_manifest)
    changed_manifest["criteria_sha256"]=first["criteria_sha256"]
    manifest_bytes=json.dumps(changed_manifest).encode()
    manifest_path.write_bytes(manifest_bytes)
    first["manifest_sha256"]=hashlib.sha256(manifest_bytes).hexdigest()
    with pytest.raises(c.VV3DContractError,match="missing or reclassified"):
        c.verify_artifact_bindings(contract,roots=roots)
    criteria_path.write_bytes(original_criteria)
    manifest_path.write_bytes(original_manifest)
    first["criteria_sha256"]=original_criteria_sha
    first["manifest_sha256"]=original_manifest_sha
    (roots["mesh"]/first["mesh_path"]).write_bytes(b"tampered")
    with pytest.raises(c.VV3DContractError,match="SHA-256 mismatch"):
        c.verify_artifact_bindings(contract,roots=roots)
    first["mesh_path"]="../outside"
    with pytest.raises(c.VV3DContractError,match="safe relative"):
        c.verify_artifact_bindings(contract,roots=roots)
