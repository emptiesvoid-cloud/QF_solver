"""Publication metadata, qualification status and manifests for documentation evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence, cast

import yaml

from scripts.docs_support import write_json, write_markdown_table
from solveur.api import list_benchmarks, run_qualification_campaign
from solveur.benchmarks import DemonstrationCatalog
from solveur.io.manifest import discovered_file_entries, git_source_state, runtime_fingerprint, sha256, utc_timestamp
from solveur.verification.traceability import FormulaRegistry
from solveur.version import DISPLAY_NAME, __version__


@dataclass(frozen=True)
class CachedDemoRecord:
    """A catalog entry reconstructed from a previously generated benchmark."""

    case_id: str
    family: str
    model_path: str
    input_sha256: str
    analysis: str
    method: str
    verdict: str
    maturity: str
    reference_type: str
    acceptance: str


class DocumentationPublisher:
    """Publish generated evidence metadata without owning mechanical demos."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        profile: str,
        records: Sequence[object],
        scales: dict[str, float],
        source_state: dict[str, Any] | None = None,
    ) -> None:
        self.root = Path(project_root).resolve()
        self.docs = self.root / "docs"
        self.generated = self.docs / "generated"
        self.profile = profile
        self.records: list[Any] = list(records) or _cached_benchmark_records(self.root)
        self.scales = dict(scales)
        self.source_state = dict(source_state) if source_state is not None else git_source_state(self.root)

    def publish(self) -> dict[str, Any]:
        self._document_registry()
        self._review_readiness()
        campaign = self._campaign()
        test_count = self._status(campaign)
        self._demo_catalog()
        self._demonstration_registry_catalog()
        self._ensure_benchmark_campaign()
        return self._manifest(campaign, test_count)

    def _campaign(self) -> dict[str, Any]:
        campaign = run_qualification_campaign(
            self.root / "qualification" / "campaign.json",
            self.generated / "qualification_campaign",
        )
        write_markdown_table(
            self.generated / "qualification_status.md",
            ("Campagne", "Cas", "Passes", "Echecs", "Candidats prets", "Verdict"),
            [
                (
                    campaign["campaign"],
                    campaign["case_count"],
                    campaign["passed_count"],
                    campaign["failed_count"],
                    f"{campaign['replacement_ready_count']}/{campaign['replacement_candidate_count']}",
                    campaign["status"],
                )
            ],
        )
        return campaign

    def _document_registry(self) -> None:
        registry = json.loads((self.docs / "document_registry.json").read_text(encoding="utf-8"))
        requirements = json.loads((self.root / "qualification" / "requirements.json").read_text(encoding="utf-8"))
        requirement_ids = {item["id"] for item in requirements["requirements"]}
        controlled_paths = {
            path.relative_to(self.docs).as_posix(): path
            for path in self.docs.rglob("*.md")
            if "generated" not in path.relative_to(self.docs).parts
            and path.relative_to(self.docs).as_posix() != "assets/vendor/README.md"
        }
        rows = []
        seen: set[str] = set()
        seen_paths: set[str] = set()
        for item in registry["documents"]:
            document_id = str(item["id"])
            if document_id in seen:
                raise ValueError(f"Duplicate document id {document_id}.")
            seen.add(document_id)
            relative_path = str(item["path"])
            if relative_path in seen_paths:
                raise ValueError(f"Duplicate document path {relative_path}.")
            seen_paths.add(relative_path)
            path = self.docs / relative_path
            if not path.is_file():
                raise FileNotFoundError(f"Registered document does not exist: {path}")
            metadata = read_document_metadata(path)
            if metadata.get("doc_id") != document_id:
                raise ValueError(f"Document id mismatch for {relative_path}: {metadata.get('doc_id')!r}.")
            metadata_status = normalize_document_status(str(metadata.get("status", "")))
            if metadata_status != item["status"]:
                raise ValueError(f"Document status mismatch for {document_id}.")
            for field in ("revision", "applicable_version", "reviewer", "approver"):
                if field not in metadata:
                    raise ValueError(f"Document {document_id} has no '{field}' metadata.")
            unknown = sorted(set(item.get("requirements", [])) - requirement_ids)
            if unknown:
                raise ValueError(f"Document {document_id} references unknown requirements: {unknown}")
            for reference in (*item.get("examples", []), *item.get("tests", [])):
                if "/" in reference and not (self.root / reference).is_file():
                    raise FileNotFoundError(f"Document {document_id} references missing artifact: {reference}")
            rows.append(
                (
                    document_id,
                    item["title"],
                    item["status"],
                    ", ".join(item.get("requirements", [])),
                    len(item.get("examples", [])),
                    len(item.get("tests", [])),
                    relative_path,
                )
            )
        missing = sorted(set(controlled_paths) - seen_paths)
        extra = sorted(seen_paths - set(controlled_paths))
        if missing or extra:
            raise ValueError(f"Document registry mismatch: missing={missing}, extra={extra}.")
        write_markdown_table(
            self.generated / "document_registry.md",
            ("ID", "Titre", "Statut", "Exigences", "Exemples", "Tests", "Source"),
            rows,
        )

    def _review_readiness(self) -> None:
        document_registry = json.loads((self.docs / "document_registry.json").read_text(encoding="utf-8"))
        requirement_registry = json.loads(
            (self.root / "qualification" / "requirements.json").read_text(encoding="utf-8")
        )
        formula_registry = FormulaRegistry(self.root / "qualification" / "formulas.json")
        requirement_ids = {str(item["id"]) for item in requirement_registry["requirements"]}
        formula_ids = sorted(formula_registry.formulas)
        formula_report = formula_registry.validate(formula_ids, requirement_ids)
        if formula_report.status != "PASS":
            raise ValueError("Formula traceability is incomplete: " + "; ".join(formula_report.issues))

        formula_rows = []
        for identifier in formula_ids:
            record = formula_registry.formulas[identifier]
            formula_rows.append(
                (
                    identifier,
                    record.get("title", ""),
                    record.get("requirement", ""),
                    f"{record.get('document', '')} - {record.get('section', '')}",
                    ", ".join(record.get("functions", [])),
                    ", ".join(record.get("tests", [])),
                    record.get("reference_id", ""),
                )
            )
        write_markdown_table(
            self.generated / "formula_traceability.md",
            ("ID", "Formule", "Exigence", "Document/section", "Fonctions", "Tests", "Reference"),
            formula_rows,
        )

        active_documents = [
            item for item in document_registry["documents"] if item.get("status") != "superseded"
        ]
        reviewed_documents = []
        for item in active_documents:
            metadata = read_document_metadata(self.docs / item["path"])
            if (
                item.get("status") in {"controlled", "approved", "accepted_for_release_0_2_3"}
                and str(metadata.get("reviewer", "")).strip()
                and str(metadata.get("approver", "")).strip()
            ):
                reviewed_documents.append(str(item["id"]))
        owner_review_status = "PASS" if len(reviewed_documents) == len(active_documents) else "BLOCKED"
        source_status = (
            "PASS"
            if self.source_state["revision"] not in {"uncommitted", "unknown"} and not self.source_state["dirty"]
            else "BLOCKED"
        )
        blockers = []
        if owner_review_status != "PASS":
            blockers.append(f"Owner review incomplete: {len(reviewed_documents)}/{len(active_documents)} documents")
        if source_status != "PASS":
            blockers.append("approved clean Git revision unavailable")
        payload = {
            "status": "PASS" if not blockers else "BLOCKED",
            "automated_traceability": formula_report.status,
            "formula_coverage": {
                "covered": formula_report.covered_count,
                "total": formula_report.requested_count,
            },
            "owner_review": {
                "status": owner_review_status,
                "reviewed_documents": len(reviewed_documents),
                "active_documents": len(active_documents),
            },
            "source_baseline": {"status": source_status, **self.source_state},
            "blockers": blockers,
        }
        write_json(self.generated / "review_readiness.json", payload)
        write_markdown_table(
            self.generated / "review_readiness.md",
            ("Controle", "Couverture", "Statut", "Decision"),
            [
                (
                    "Tracabilite des formules",
                    f"{formula_report.covered_count}/{formula_report.requested_count}",
                    formula_report.status,
                    "controle automatique bloquant",
                ),
                (
                    "Owner review",
                    f"{len(reviewed_documents)}/{len(active_documents)}",
                    owner_review_status,
                    "reviewer et approver non pre-remplis",
                ),
                (
                    "Baseline source",
                    str(self.source_state["revision"]),
                    source_status,
                    "revision Git approuvee et propre requise",
                ),
                ("Readiness documentaire", "P0", payload["status"], "; ".join(blockers) or "aucun blocage"),
            ],
        )

    def _status(self, campaign: dict[str, Any]) -> int:
        test_count = collect_test_count(self.root)
        version = solver_version()
        revision = str(self.source_state["revision"])
        revision_label = revision[:12] if revision not in {"uncommitted", "unknown"} else revision
        panels = f"""
<div class="status-grid">
  <section class="status-panel"><h3>Version du solveur</h3><span class="value">{version}</span><span>schema JSON v1</span></section>
  <section class="status-panel"><h3>Tests collectes</h3><span class="value">{test_count}</span><span>campagne locale courante</span></section>
  <section class="status-panel"><h3>Campagne souveraine</h3><span class="value">{campaign['status']}</span><span>{campaign['passed_count']}/{campaign['case_count']} cas</span></section>
  <section class="status-panel"><h3>Revision source</h3><span class="value">{revision_label}</span><span>dirty: {str(self.source_state['dirty']).lower()}</span></section>
</div>

| Perimetre | Maturite | Decision documentaire |
| --- | --- | --- |
| TET4 statique lineaire | <span class="maturity stable">stable</span> | Domaine borne documente |
| MITC3+/MITC4 et BEAM2 | <span class="maturity reinforced">tests renforces</span> | Scopes propres a chaque formulation |
| J2 small-strain / TET4-TET10-HEX8-HEX20 | <span class="maturity reinforced">qualifie borne</span> | G01, chemins et correlation documentes |
| Total-Lagrangian TET4/HEX8 et flambement | <span class="maturity reinforced">qualifie borne</span> | G02/G03, domaine pre-limite ou premier seuil |
| Contact sans frottement | <span class="maturity reinforced">qualifie borne</span> | G05, noeud/patch vers surface triangulee |
| Arc-length et couplages non lineaires | <span class="maturity experimental">experimental</span> | G04/G06 non qualifies dans 0.2.5a0 |
| Grand modele | <span class="maturity experimental">experimental</span> | Caracterisation separee, aucun claim nouveau |
""".strip()
        (self.generated / "status.md").write_text(panels + "\n", encoding="utf-8")
        write_markdown_table(
            self.generated / "roadmap_status.md",
            ("Action", "Etat genere", "Condition de fermeture"),
            [
                (
                    "Revision Git de reference",
                    "ouverte" if revision == "uncommitted" else "disponible",
                    "commit approuve et depot propre",
                ),
                ("Site engineering", "genere", "build strict et campagne PASS"),
                ("Owner review 0.2.5a0", "approuvee", "publication reste une action Owner separee"),
                ("Scope 1M PETSc", "hors scope", "requalification future avec environnement controle"),
            ],
        )
        return test_count

    def _demo_catalog(self) -> None:
        write_markdown_table(
            self.generated / "demo_catalog.md",
            ("Cas", "Famille", "Analyse/methode", "Maturite", "Reference", "Verdict", "Entree SHA-256"),
            [
                (
                    record.case_id,
                    record.family,
                    f"{record.analysis}/{record.method}",
                    record.maturity,
                    record.reference_type,
                    record.verdict,
                    record.input_sha256[:12],
                )
                for record in self.records
            ],
        )

    def _demonstration_registry_catalog(self) -> None:
        """Publish the public API catalog from its machine-readable source."""
        catalog = DemonstrationCatalog()
        report = catalog.validate_integrity(self.root)
        if report.status != "PASS":
            raise ValueError("Demonstration catalog integrity failed: " + "; ".join(report.issues))
        write_markdown_table(
            self.generated / "demonstration_registry.md",
            ("ID", "Execution", "Famille", "Methode", "Maturite", "Entree", "Page", "Tests"),
            [
                (
                    item.demo_id,
                    item.execution,
                    item.family,
                    item.method,
                    item.maturity,
                    item.model,
                    item.documentation,
                    len(item.tests),
                )
                for item in catalog.list()
            ],
        )

    def _ensure_benchmark_campaign(self) -> None:
        """Recreate the aggregate benchmark index from controlled cached outputs.

        A normal documentation build writes this file through
        ``MeshedBenchmarkDocumenter``.  The fallback is intentionally limited
        to recovery after an interrupted build and carries an explicit source
        marker in the JSON payload.
        """
        target = self.generated / "benchmarks" / "campaign_summary.json"
        if target.is_file():
            return
        cases: list[dict[str, Any]] = []
        for descriptor in list_benchmarks():
            summary_path = self.generated / "benchmarks" / descriptor.identifier / "benchmark_summary.json"
            if summary_path.is_file():
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                cases.append(
                    {
                        "id": descriptor.identifier,
                        "status": summary["status"],
                        "maturity": descriptor.maturity,
                        "checks": summary["checks"],
                    }
                )
                continue
            if descriptor.identifier == "BM-SOL-TET4-TORSION-001":
                probe = self.root / "VNV-TET4-TORSION-ANALYTIC-001" / "stress_probe_h9" / "stress_probe_summary.json"
                if probe.is_file():
                    summary = json.loads(probe.read_text(encoding="utf-8"))
                    cases.append(
                        {
                            "id": descriptor.identifier,
                            "status": summary["status"],
                            "maturity": descriptor.maturity,
                            "checks": summary["checks"],
                        }
                    )
        if len(cases) != len(list_benchmarks()):
            missing = sorted({item.identifier for item in list_benchmarks()} - {str(item["id"]) for item in cases})
            raise RuntimeError("Cached benchmark recovery is incomplete: " + ", ".join(missing))
        write_json(
            target,
            {
                "profile": self.profile,
                "status": "PASS" if all(item["status"] in {"PASS", "WARNING"} for item in cases) else "FAIL",
                "case_count": len(cases),
                "source": "recovered_from_controlled_cached_outputs",
                "cases": cases,
            },
        )

    def _manifest(self, campaign: dict[str, Any], test_count: int) -> dict[str, Any]:
        entries = discovered_file_entries(
            self.docs,
            lambda relative: "documentation_asset" if relative.startswith("assets/generated/") else "documentation_data",
            exclude_names=("docs_manifest.json",),
        )
        generated_entries = [
            entry
            for entry in entries
            if str(entry["path"]).startswith("generated/") or str(entry["path"]).startswith("assets/generated/")
        ]
        manifest = {
            "manifest_version": 2,
            "generated_at_utc": utc_timestamp(),
            "profile": self.profile,
            "solver_name": DISPLAY_NAME,
            "solver_version": solver_version(),
            # The manifest is generated after checkout and may be written to a
            # tracked documentation path.  This field identifies the source
            # revision it was generated from without making the manifest part
            # of that revision's own identity.
            "source_sha": str(self.source_state["revision"]),
            "source": self.source_state,
            "runtime": runtime_fingerprint(),
            "test_count": test_count,
            "qualification_campaign": {
                "name": campaign.get("campaign"),
                "status": campaign.get("status"),
                "case_count": campaign.get("case_count"),
            },
            "deformation_scales": self.scales,
            "demonstrations": [asdict(cast(Any, record)) for record in self.records],
            "files": generated_entries,
        }
        write_json(self.generated / "docs_manifest.json", manifest)
        return manifest


def read_document_metadata(path: Path) -> dict[str, Any]:
    """Read and validate the YAML header of a controlled Markdown page."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError(f"Controlled document has no YAML header: {path}")
    parts = content.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"Controlled document has an incomplete YAML header: {path}")
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        raise ValueError(f"Controlled document has invalid YAML metadata: {path}")
    return metadata


def normalize_document_status(status: str) -> str:
    """Map descriptive page states to the controlled lifecycle vocabulary."""
    normalized = status.strip().lower()
    if normalized in {
        "controlled",
        "approved",
        "superseded",
        "controlled_candidate",
        "owner_accepted",
        "owner_accepted_experimental",
        "owner_accepted_with_recommendations",
        "accepted_for_release_0_2_3",
        "ready_for_owner_review",
        "verified_development_external_correlation",
    }:
        return normalized
    if normalized == "owner_reviewed":
        return "controlled"
    return "draft"


def collect_test_count(root: Path) -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError("Unable to collect tests for documentation status:\n" + completed.stdout + completed.stderr)
    match = re.search(r"(\d+) tests collected", completed.stdout)
    if not match:
        raise RuntimeError("Pytest collection output does not expose a test count.")
    return int(match.group(1))


def _cached_benchmark_records(root: Path) -> list[CachedDemoRecord]:
    """Recover catalog rows from controlled outputs without rerunning benchmarks.

    This path is used only when a documentation publication resumes after an
    interrupted long benchmark build.  It labels every recovered row so the
    manifest cannot be confused with a freshly executed campaign.
    """
    from scripts.docs_benchmarks import PRIMARY_PREFIX

    output = root / "docs" / "generated" / "benchmarks"
    records: list[CachedDemoRecord] = []
    for descriptor in list_benchmarks():
        prefix = PRIMARY_PREFIX.get(descriptor.identifier)
        if prefix is None:
            continue
        model = output / descriptor.identifier / f"{prefix}.model.json"
        result = output / descriptor.identifier / f"{prefix}.json"
        if not model.is_file() or not result.is_file():
            continue
        records.append(
            CachedDemoRecord(
                case_id=descriptor.identifier,
                family=descriptor.family,
                model_path=model.relative_to(root).as_posix(),
                input_sha256=sha256(model),
                analysis="+".join(descriptor.analyses),
                method="cached_controlled_benchmark",
                verdict="CACHED_EVIDENCE",
                maturity=descriptor.maturity,
                reference_type=descriptor.reference_type,
                acceptance="Recovered from prior controlled output; rerun benchmark for a fresh campaign verdict.",
            )
        )
    return records


def solver_version() -> str:
    return __version__
