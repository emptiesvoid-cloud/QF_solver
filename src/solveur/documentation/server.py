"""Serve the generated technical site through the system browser."""

from __future__ import annotations

import argparse
import functools
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Sequence

from solveur.paths import project_path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
REQUIRED_SITE_FILES = (
    Path("index.html"),
    Path("assets/stylesheets/engineering.css"),
    Path("search/search_index.json"),
)


class DocumentationRequestHandler(SimpleHTTPRequestHandler):
    """Quiet local handler with conservative browser security headers."""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


def site_problems(site_dir: str | Path) -> list[str]:
    """Return missing generated-site artifacts without starting a server."""
    root = Path(site_dir).resolve()
    return [str(relative) for relative in REQUIRED_SITE_FILES if not (root / relative).is_file()]


def create_server(site_dir: str | Path, *, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Create a loopback-only documentation server."""
    if not 0 <= int(port) <= 65535:
        raise ValueError("port must be between 0 and 65535")
    root = Path(site_dir).resolve()
    missing = site_problems(root)
    if missing:
        raise FileNotFoundError("generated documentation is incomplete: " + ", ".join(missing))
    handler = functools.partial(DocumentationRequestHandler, directory=str(root))
    return ThreadingHTTPServer((DEFAULT_HOST, int(port)), handler)


def _default_site_dir() -> Path:
    working_site = Path.cwd() / "site"
    if working_site.is_dir():
        return working_site
    return project_path("site")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ouvre le manuel QF_solver dans le navigateur systeme.")
    parser.add_argument("--site-dir", type=Path, default=None, help="Repertoire MkDocs genere (defaut: ./site).")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Port local, 8000 par defaut; 0 choisit un port libre."
    )
    parser.add_argument("--no-open", action="store_true", help="Demarre le serveur sans ouvrir le navigateur systeme.")
    parser.add_argument("--check", action="store_true", help="Verifie le site genere puis quitte sans serveur.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate, serve and optionally open the generated documentation."""
    args = _parser().parse_args(argv)
    site_dir = (args.site_dir or _default_site_dir()).resolve()
    missing = site_problems(site_dir)
    if missing:
        print("SITE DOCUMENTAIRE INCOMPLET: " + ", ".join(missing), file=sys.stderr)
        print("Executer: python .\\scripts\\build_docs.py --profile engineering", file=sys.stderr)
        return 2
    if args.check:
        print(f"SITE DOCUMENTAIRE: PASS ({site_dir})")
        return 0

    try:
        server = create_server(site_dir, port=args.port)
    except (OSError, ValueError) as exc:
        print(f"SERVEUR DOCUMENTAIRE: FAIL ({exc})", file=sys.stderr)
        print("Choisir un autre port avec --port, par exemple --port 8001.", file=sys.stderr)
        return 2

    port = int(server.server_address[1])
    address = f"http://{DEFAULT_HOST}:{port}/"
    print("SITE DOCUMENTAIRE: PRET")
    print(f"Adresse locale: {DEFAULT_HOST}, port {port}")
    print("Arret du serveur: Ctrl+C")
    if not args.no_open and not webbrowser.open_new_tab(address):
        print("Le navigateur systeme n'a pas pu etre ouvert automatiquement.", file=sys.stderr)
        print(f"Saisir manuellement l'adresse locale {DEFAULT_HOST} avec le port {port}.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSERVEUR DOCUMENTAIRE: ARRETE")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
