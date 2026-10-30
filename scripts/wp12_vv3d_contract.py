"""Prospective VV3D closed-contract validation; does not authorize or run FEM."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAMPAIGN = "WP12-VV3D-ADAPTIVE-20261029-R1"
SCHEMA = "qf-wp12-vv3d-contract-v1"
DECISION_SCHEMA = "qf-wp12-vv3d-owner-decision-v1"
INITIAL_CASE_IDS = tuple(
    f"VV3D-{family}-L{level}"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
    for level in (1, 2, 3)
)
INITIAL_IDS = frozenset(INITIAL_CASE_IDS)
QPOST_IDS = frozenset(f"VV3D-ADAPT-{family}-QPOST" for family in ("TET4", "TET10", "HEX8", "HEX20"))
BUDGET = {"attempts_max":24,"cumulative_seconds_max":28800,"timeout_max_seconds":1200,
          "rss_soft_limit_mib":4096,"dofs_max":30000,"concurrency":1,"implicit_retry":False}
STOP_STATES = frozenset({"INFRASTRUCTURE_FAILURE", "PROVENANCE_FAILURE", "LEDGER_FAILURE", "INSUFFICIENT_BUDGET"})
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
SAFE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


class VV3DContractError(ValueError):
    """Reject incomplete, ambiguous or unapproved prospective contracts."""


def _sha(value: Any) -> bool:
    return isinstance(value,str) and SHA_RE.fullmatch(value) is not None


def _strict_json_bytes(raw: bytes) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key,value in pairs:
            if key in out:
                raise VV3DContractError("JSON artifact contains duplicate keys")
            out[key] = value
        return out
    try:
        return json.loads(raw,object_pairs_hook=unique_pairs,
                          parse_constant=lambda _value: (_ for _ in ()).throw(VV3DContractError("nonfinite JSON")))
    except (TypeError,ValueError,UnicodeDecodeError) as exc:
        raise VV3DContractError("artifact bytes are not strict JSON") from exc


def canonical_sha256(value: Mapping[str, Any]) -> str:
    try:
        raw=json.dumps(value,sort_keys=True,separators=(",", ":"),allow_nan=False).encode("utf-8")
    except (TypeError,ValueError) as exc:
        raise VV3DContractError("contract is not finite strict JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def validate_contract(contract: Mapping[str, Any], *, registered_nodeids: set[str],
                      controller_fingerprint: str, scientific_fingerprint: str) -> None:
    """Validate a frozen proposal against the caller's actual registration and fingerprints.

    Does not attest an Owner's identity, inspect manifests on disk, reserve a ledger,
    or enable execution. The runner must additionally validate all raw-byte hashes.
    """
    required = {"schema","campaign_id","budget","controller_fingerprint","scientific_fingerprint",
                "cases","adaptive_catalog","qpost_jobs","transitions","initial_ledger_sha256"}
    if not isinstance(contract, Mapping) or set(contract) != required:
        raise VV3DContractError("contract has missing or unexpected fields")
    if (contract["schema"] != SCHEMA or contract["campaign_id"] != CAMPAIGN
            or not isinstance(contract["budget"],Mapping)
            or canonical_sha256(contract["budget"]) != canonical_sha256(BUDGET)
            or not _sha(controller_fingerprint) or not _sha(scientific_fingerprint)
            or contract["controller_fingerprint"] != controller_fingerprint
            or contract["scientific_fingerprint"] != scientific_fingerprint
            or not _sha(contract["initial_ledger_sha256"])):
        raise VV3DContractError("campaign, budget, fingerprints or initial ledger mismatch")
    cases=contract["cases"]
    if not isinstance(cases,list) or not 12 <= len(cases) <= 24:
        raise VV3DContractError("contract requires exactly 12 initial and at most 12 adaptive cases")
    fields={"case_id","phase","nodeid","family","mesh_sha256","manifest_sha256","oracle_sha256",
            "criteria_sha256","mesh_path","manifest_path","oracle_path","criteria_path",
            "selected_dofs","timeout_seconds","rss_soft_limit_mib","max_attempts","trigger"}
    ids: set[str]=set()
    nodes: set[str]=set()
    initial: set[str]=set()
    adaptive: set[str]=set()
    for case in cases:
        if not isinstance(case,Mapping) or set(case) != fields:
            raise VV3DContractError("case has missing or unexpected fields")
        cid=case["case_id"]
        node=case["nodeid"]
        if (not isinstance(cid,str) or not SAFE_RE.fullmatch(cid) or cid in ids
                or not isinstance(node,str) or node not in registered_nodeids or node in nodes
                or not isinstance(case["family"],str) or case["family"] not in {"TET4","TET10","HEX8","HEX20"}
                or not all(_sha(case[field]) for field in ("mesh_sha256","manifest_sha256","oracle_sha256","criteria_sha256"))
                or not all(_safe_relative_path(case[field]) for field in ("mesh_path","manifest_path","oracle_path","criteria_path"))
                or type(case["selected_dofs"]) is not int or not 0 < case["selected_dofs"] <= BUDGET["dofs_max"]
                or type(case["timeout_seconds"]) is not int or not 0 < case["timeout_seconds"] <= BUDGET["timeout_max_seconds"]
                or type(case["rss_soft_limit_mib"]) is not int
                or case["rss_soft_limit_mib"] != BUDGET["rss_soft_limit_mib"] or type(case["max_attempts"]) is not int
                or case["max_attempts"] != 1):
            raise VV3DContractError("case identity, registration, fingerprint or budget invalid")
        ids.add(cid)
        nodes.add(node)
        if case["phase"] == "INITIAL":
            if cid not in INITIAL_IDS or case["trigger"] is not None or not cid.startswith(f"VV3D-{case['family']}-"):
                raise VV3DContractError("initial case identity, family or trigger invalid")
            initial.add(cid)
        elif case["phase"] == "ADAPTIVE":
            trigger=case["trigger"]
            if (cid in INITIAL_IDS or not isinstance(trigger,Mapping)
                    or set(trigger) != {"source_case_id","observable","operator","threshold","unit"}
                    or not all(isinstance(trigger.get(k),str) and trigger[k] for k in ("source_case_id","observable","unit"))
                    or not isinstance(trigger["operator"],str) or trigger["operator"] not in {"LT","LE","GT","GE"}
                    or isinstance(trigger["threshold"],bool) or not isinstance(trigger["threshold"],(int,float))
                    or not math.isfinite(trigger["threshold"])):
                raise VV3DContractError("adaptive trigger must be exact, measurable and finite")
            adaptive.add(cid)
        else:
            raise VV3DContractError("case phase is invalid")
    if initial != INITIAL_IDS:
        raise VV3DContractError("initial case set is incomplete")
    if any(case["trigger"]["source_case_id"] not in initial for case in cases if case["phase"] == "ADAPTIVE"):
        raise VV3DContractError("adaptive trigger refers to an unknown initial case")
    qpost_jobs = contract["qpost_jobs"]
    qpost_fields = {"job_id","nodeid","source_family","manifest_sha256","oracle_sha256","criteria_sha256",
                    "manifest_path","oracle_path","criteria_path","timeout_seconds","rss_soft_limit_mib","max_jobs"}
    if not isinstance(qpost_jobs, list) or len(qpost_jobs) != len(QPOST_IDS):
        raise VV3DContractError("campaign contract must register exactly four catalogued QPOST jobs")
    seen_qpost: set[str] = set()
    for job in qpost_jobs:
        if (not isinstance(job, Mapping) or set(job) != qpost_fields
                or job.get("job_id") not in QPOST_IDS or job.get("job_id") in seen_qpost
                or job.get("nodeid") not in registered_nodeids or job.get("nodeid") in nodes
                or job.get("source_family") not in {"TET4","TET10","HEX8","HEX20"}
                or not all(_sha(job.get(key)) for key in ("manifest_sha256","oracle_sha256","criteria_sha256"))
                or not all(_safe_relative_path(job.get(key)) for key in ("manifest_path","oracle_path","criteria_path"))
                or type(job.get("timeout_seconds")) is not int or not 0 < job["timeout_seconds"] <= BUDGET["timeout_max_seconds"]
                or job.get("rss_soft_limit_mib") != BUDGET["rss_soft_limit_mib"]
                or job.get("max_jobs") != 1):
            raise VV3DContractError("QPOST identity, registration, paths or budget is invalid")
        seen_qpost.add(job["job_id"])
    adaptive_catalog=contract["adaptive_catalog"]
    adaptive_ids={f"VV3D-ADAPT-{family}-{kind}" for family in ("TET4","TET10","HEX8","HEX20")
                  for kind in ("H1","QLOAD","QPOST")}
    if (not isinstance(adaptive_catalog,Mapping) or set(adaptive_catalog) != {"catalog_sha256","candidates"}
            or not _sha(adaptive_catalog.get("catalog_sha256"))
            or not isinstance(adaptive_catalog.get("candidates"),Mapping)
            or set(adaptive_catalog["candidates"]) != adaptive_ids):
        raise VV3DContractError("campaign contract must bind the exact closed 12-candidate adaptive catalog")
    for candidate_id,binding in adaptive_catalog["candidates"].items():
        if (not isinstance(binding,Mapping)
                or set(binding) != {"candidate_sha256","mesh_sha256","criteria_sha256","rule_sha256"}
                or not all(_sha(binding.get(field)) for field in binding)):
            raise VV3DContractError(f"adaptive candidate binding is incomplete for {candidate_id}")
    transitions=contract["transitions"]
    if not isinstance(transitions,Mapping) or set(transitions) != STOP_STATES | {"PASS", "SCIENTIFIC_DEVIATION"}:
        raise VV3DContractError("transition table is incomplete")
    if (any(transitions[s] != "STOP" for s in STOP_STATES)
            or transitions["PASS"] != "CONTINUE_INITIAL_ORDER_AND_TRIGGERED_ADAPTIVE"):
        raise VV3DContractError("infrastructure, provenance, ledger and budget failures must stop")
    if transitions["SCIENTIFIC_DEVIATION"] != "STOP":
        raise VV3DContractError("scientific deviation must stop this campaign; diagnostics require a separate campaign")
    canonical_sha256(contract)


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value,str) or not value or "\\" in value or ":" in value or "\x00" in value:
        return False
    path=Path(value)
    return not path.is_absolute() and all(part not in {"", "..", "."} for part in value.split("/"))


def verify_artifact_bindings(contract: Mapping[str, Any], *, roots: Mapping[str, Path]) -> None:
    """Read and verify each bound file's raw SHA, without modifying evidence."""
    if set(roots) != {"mesh", "manifest", "oracle", "criteria"}:
        raise VV3DContractError("artifact roots must be explicit for all four binding classes")
    def read_bound(kind: str, relative: Any, expected_sha: str) -> bytes:
        if not _safe_relative_path(relative):
            raise VV3DContractError(f"{kind} path is not a safe relative path")
        try:
            base=roots[kind].resolve(strict=True)
            path=(base / relative).resolve(strict=True)
            path.relative_to(base)
            if not path.is_file():
                raise VV3DContractError(f"{kind} artifact is not a regular file")
            raw=path.read_bytes()
        except (OSError, ValueError) as exc:
            raise VV3DContractError(f"{kind} artifact missing or outside its root") from exc
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise VV3DContractError(f"{kind} artifact SHA-256 mismatch")
        return raw
    for case in contract["cases"]:
        contents: dict[str, bytes] = {}
        for kind,root in roots.items():
            relative=case.get(f"{kind}_path")
            if not _safe_relative_path(relative):
                raise VV3DContractError(f"{kind} path is not a safe relative path")
            try:
                base=root.resolve(strict=True)
                path=(base / relative).resolve(strict=True)
                path.relative_to(base)
                if not path.is_file():
                    raise VV3DContractError(f"{kind} artifact is not a regular file")
                raw=path.read_bytes()
                digest=hashlib.sha256(raw).hexdigest()
            except (OSError, ValueError) as exc:
                raise VV3DContractError(f"{kind} artifact missing or outside its root") from exc
            if digest != case.get(f"{kind}_sha256"):
                raise VV3DContractError(f"{kind} artifact SHA-256 mismatch")
            contents[kind]=raw
        try:
            manifest=_strict_json_bytes(contents["manifest"])
            mesh=_strict_json_bytes(contents["mesh"])
            criteria=_strict_json_bytes(contents["criteria"])
        except (ValueError,TypeError) as exc:
            raise VV3DContractError("bound JSON artifact is invalid or nonfinite") from exc
        expected={field:case[field] for field in ("case_id","nodeid","family","mesh_sha256","oracle_sha256",
                                                  "criteria_sha256","selected_dofs","timeout_seconds",
                                                  "rss_soft_limit_mib","max_attempts")}
        if (not isinstance(manifest,Mapping) or manifest.get("schema") != "qf-wp12-vv3d-case-manifest-v1"
                or manifest.get("state") != "PREPARED_NOT_AUTHORIZED"
                or any(manifest.get(key) != value for key,value in expected.items())):
            raise VV3DContractError("bound case manifest does not match the exact registered case")
        if (not isinstance(mesh,Mapping) or mesh.get("schema") != "qf-wp12-vv3d-mesh-v1"
                or mesh.get("family") != case["family"] or not isinstance(mesh.get("summary"),Mapping)
                or mesh["summary"].get("dofs") != case["selected_dofs"]):
            raise VV3DContractError("bound mesh family or DOF count mismatch")
        if (not isinstance(criteria,Mapping) or criteria.get("schema") != "qf-wp12-vv3d-criteria-v1"
                or not isinstance(criteria.get("criteria"),list) or not criteria["criteria"]):
            raise VV3DContractError("bound case criteria are missing or malformed")
        rules=criteria["criteria"]
        seen_rules:set[str]=set()
        for rule in rules:
            if (not isinstance(rule,Mapping) or set(rule) != {"id","classification","operator","threshold","unit"}
                    or not isinstance(rule["id"],str) or not SAFE_RE.fullmatch(rule["id"])
                    or rule["id"] in seen_rules or not isinstance(rule["classification"],str) or rule["classification"] not in
                    {"CASE_GATE","CASE_DIAGNOSTIC","CAMPAIGN_GATE"}
                    or not isinstance(rule["operator"],str) or rule["operator"] not in {"ALL_TRUE","LT","LE","GT","GE"}
                    or not isinstance(rule["unit"],str) or not rule["unit"]):
                raise VV3DContractError("bound criteria contain an invalid or duplicate rule")
            if rule["operator"] == "ALL_TRUE":
                if rule["threshold"] is not None:
                    raise VV3DContractError("ALL_TRUE criterion cannot carry a numeric threshold")
            elif (isinstance(rule["threshold"],bool) or not isinstance(rule["threshold"],(int,float))
                    or not math.isfinite(rule["threshold"])):
                raise VV3DContractError("bound criterion threshold must be finite")
            seen_rules.add(rule["id"])
        mandatory={"finite","det_j_positive","free_residual","energy_identity","force_closure","moment_closure"}
        if not mandatory.issubset(seen_rules) or any(
            rule["classification"] != "CASE_GATE" for rule in rules if rule["id"] in mandatory
        ):
            raise VV3DContractError("mandatory numerical gates are missing or reclassified")
        by_rule={rule["id"]:rule for rule in rules}
        if (by_rule["finite"]["operator"] != "ALL_TRUE"
                or by_rule["det_j_positive"]["operator"] != "GT"
                or by_rule["det_j_positive"]["threshold"] != 0
                or any(by_rule[name]["operator"] != "LE" or by_rule[name]["threshold"] < 0
                       for name in mandatory - {"finite","det_j_positive"})):
            raise VV3DContractError("mandatory criteria require explicit consistent numerical limits")
    for job in contract["qpost_jobs"]:
        manifest_raw=read_bound("manifest",job["manifest_path"],job["manifest_sha256"])
        read_bound("oracle",job["oracle_path"],job["oracle_sha256"])
        criteria_raw=read_bound("criteria",job["criteria_path"],job["criteria_sha256"])
        try:
            manifest=_strict_json_bytes(manifest_raw)
            criteria=_strict_json_bytes(criteria_raw)
        except (ValueError,TypeError) as exc:
            raise VV3DContractError("QPOST manifest or criteria is invalid strict JSON") from exc
        expected={"schema":"qf-wp12-vv3d-qpost-manifest-v1","state":"PREPARED_NOT_AUTHORIZED",
                  "job_id":job["job_id"],"nodeid":job["nodeid"],"source_family":job["source_family"],
                  "oracle_sha256":job["oracle_sha256"],"criteria_sha256":job["criteria_sha256"],
                  "timeout_seconds":job["timeout_seconds"],"rss_soft_limit_mib":job["rss_soft_limit_mib"],
                  "max_jobs":job["max_jobs"]}
        if not isinstance(manifest,Mapping) or any(manifest.get(key) != value for key,value in expected.items()):
            raise VV3DContractError("QPOST manifest does not match its exact catalog binding")
        if (not isinstance(criteria,Mapping) or criteria.get("schema") != "qf-wp12-vv3d-qpost-criteria-v1"
                or not isinstance(criteria.get("criteria"),list) or not criteria["criteria"]):
            raise VV3DContractError("QPOST criteria are missing or malformed")


def validate_decision(contract: Mapping[str, Any], decision: Mapping[str, Any], *, contract_bytes: bytes) -> None:
    """Bind one decision to the exact ordered initial FEM tranche.

    The scientific contract remains the complete closed catalogue. This first
    decision intentionally authorizes only the twelve initial FEM cases; H1,
    QLOAD, QPOST, and all other catalogued work require a separate decision.
    The SHA-256 binding detects changes but does not authenticate the Owner.
    """
    if not isinstance(decision,Mapping) or set(decision) != {"schema","campaign_id","decision_id","approved_by",
        "approved_at_utc","contract_sha256","case_ids","status"}:
        raise VV3DContractError("Owner decision has missing or unexpected fields")
    parsed = _strict_json_bytes(contract_bytes)
    contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
    expected_case_ids = list(INITIAL_CASE_IDS)
    contract_initial_ids = [
        case.get("case_id") for case in contract.get("cases", [])
        if isinstance(case, Mapping) and case.get("phase") == "INITIAL"
    ]
    if (parsed != contract or not _sha(contract_sha256)
            or contract_initial_ids != expected_case_ids
            or decision["schema"] != DECISION_SCHEMA or decision["campaign_id"] != CAMPAIGN
            or decision["contract_sha256"] != contract_sha256 or decision["status"] != "APPROVED"
            or decision["approved_by"] != "Owner" or not isinstance(decision["decision_id"],str)
            or not SAFE_RE.fullmatch(decision["decision_id"]) or decision["case_ids"] != expected_case_ids):
        raise VV3DContractError("Owner decision does not bind this exact contract and ordered cases")
    try:
        instant=datetime.fromisoformat(decision["approved_at_utc"].replace("Z","+00:00"))
    except (AttributeError,ValueError) as exc:
        raise VV3DContractError("Owner decision requires UTC timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() != timezone.utc.utcoffset(instant):
        raise VV3DContractError("Owner decision timestamp must be UTC")


def validate_decision_scope(decision: Mapping[str, Any], item_id: str) -> None:
    """Refuse any catalog item not explicitly named by the campaign decision."""
    if (not isinstance(decision, Mapping) or not isinstance(item_id, str)
            or not isinstance(decision.get("case_ids"), list)
            or item_id not in decision["case_ids"]):
        raise VV3DContractError("campaign decision does not authorize this case or QPOST job")


def validate_transition_eligibility(
    contract: Mapping[str, Any], decision: Mapping[str, Any], *, contract_sha256: str,
    decision_sha256: str, source_case_id: str, destination_case_id: str,
    source_status: str, source_result_sha256: str, source_observables: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> None:
    """Validate a closed-catalog continuation receipt before an adaptive reservation.

    A PASS continuation must satisfy the destination's frozen measurable trigger.
    Only PASS can continue within this campaign. A scientific deviation closes
    the campaign; any post-failure diagnostic must use an independently
    authorized campaign, ledger, manifest, and provenance chain.
    """
    if not all(_sha(value) for value in (contract_sha256, decision_sha256, source_result_sha256)):
        raise VV3DContractError("transition receipt is missing a valid source/contract/decision digest")
    by_id={case["case_id"]:case for case in contract["cases"]}
    source=by_id.get(source_case_id)
    destination=by_id.get(destination_case_id)
    if source is None or destination is None or destination.get("phase") != "ADAPTIVE":
        raise VV3DContractError("transition source or adaptive destination is outside the frozen case catalog")
    if destination["trigger"]["source_case_id"] != source_case_id:
        raise VV3DContractError("adaptive destination trigger names a different source case")
    expected_fields={"schema","campaign_id","contract_sha256","decision_id","decision_sha256",
                     "source_case_id","destination_case_id","source_status","source_result_sha256",
                     "transition_kind","trigger_observation"}
    if not isinstance(receipt,Mapping) or set(receipt) != expected_fields:
        raise VV3DContractError("transition eligibility receipt has missing or unexpected fields")
    if any(receipt.get(key) != value for key,value in {
        "schema":"qf-wp12-vv3d-transition-eligibility-v1","campaign_id":CAMPAIGN,
        "contract_sha256":contract_sha256,"decision_id":decision.get("decision_id"),
        "decision_sha256":decision_sha256,"source_case_id":source_case_id,
        "destination_case_id":destination_case_id,"source_status":source_status,
        "source_result_sha256":source_result_sha256,
    }.items()):
        raise VV3DContractError("transition eligibility receipt is bound to a different run or Owner contract")
    if source_status == "PASS":
        trigger=destination["trigger"]
        observation=receipt.get("trigger_observation")
        if not isinstance(observation,Mapping) or set(observation) != {"observable","value","unit","operator","threshold","result"}:
            raise VV3DContractError("PASS adaptive transition requires the exact measured trigger observation")
        value=source_observables.get(trigger["observable"])
        if isinstance(value,Mapping):
            actual=value.get("value")
            unit=value.get("unit")
        else:
            actual=value
            unit=trigger["unit"]
        if (isinstance(actual,bool) or not isinstance(actual,(int,float)) or not math.isfinite(actual)
                or unit != trigger["unit"]):
            raise VV3DContractError("source run does not expose the finite trigger observable in its declared unit")
        operators={"LT":lambda a,b:a<b,"LE":lambda a,b:a<=b,"GT":lambda a,b:a>b,"GE":lambda a,b:a>=b}
        passed=operators[trigger["operator"]](actual,trigger["threshold"])
        expected_observation={"observable":trigger["observable"],"value":actual,"unit":unit,
                              "operator":trigger["operator"],"threshold":trigger["threshold"],"result":passed}
        if observation != expected_observation or not passed:
            raise VV3DContractError("adaptive trigger is not satisfied by the source run's archived observable")
    else:
        raise VV3DContractError("non-PASS outcomes stop this campaign; a diagnostic requires a separate authorization")
    expected_kind="PASS_TRIGGER"
    if receipt.get("transition_kind") != expected_kind:
        raise VV3DContractError("transition receipt kind does not match the approved transition")
