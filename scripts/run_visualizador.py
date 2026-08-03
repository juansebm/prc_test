"""Lanza el visualizador local (visualizador/server.py)."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "visualizador" / "server.py"
ENV_FILE = ROOT / ".env"


def _load_dotenv(path: Path) -> None:
    """ponytail: parser mínimo KEY=VAL; no soporta comillas multilínea."""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def main() -> None:
    if not ENV_FILE.is_file():
        raise SystemExit(
            "Falta .env - copia .env.example a .env y vuelve a intentar.\n"
            "  copy .env.example .env          # Windows\n"
            "  cp .env.example .env            # macOS/Linux"
        )
    _load_dotenv(ENV_FILE)

    if not (ROOT / "visualizador" / "dist" / "index.html").is_file():
        raise SystemExit(
            "Falta visualizador/dist (build React).\n"
            "  cd visualizador && npm install && npm run build"
        )
    argv = sys.argv[1:]
    if "--abrir" not in argv and "-h" not in argv and "--help" not in argv:
        argv = ["--abrir", *argv]
    sys.argv = [str(SERVER), *argv]
    print(f"datalab={ROOT / 'data' / 'datalab_markdown'}")
    print(f"UI: http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '8765')}/")
    runpy.run_path(str(SERVER), run_name="__main__")


if __name__ == "__main__":
    main()
