from __future__ import annotations

import threading
from pathlib import Path
from urllib.request import urlopen

import pytest

from solveur.documentation.server import create_server, main, site_problems


ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


def require_generated_site() -> None:
    problems = site_problems(SITE)
    if problems:
        pytest.skip("Build the documentation site before generated-site checks: " + ", ".join(problems))


def test_generated_site_is_ready_for_local_server() -> None:
    require_generated_site()
    assert site_problems(SITE) == []
    assert main(["--site-dir", str(SITE), "--check"]) == 0


def test_incomplete_site_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert "index.html" in site_problems(tmp_path)
    assert main(["--site-dir", str(tmp_path), "--check"]) == 2
    assert "SITE DOCUMENTAIRE INCOMPLET" in capsys.readouterr().err


def test_server_is_loopback_only_and_serves_utf8_html() -> None:
    require_generated_site()
    server = create_server(SITE, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        assert host == "127.0.0.1"
        with urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:  # noqa: S310
            content = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert '<meta charset="utf-8">' in content
            assert "QF_solver" in content
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
