#!/usr/bin/env python3
"""
Servidor local del visualizador PRC (data/datalab_markdown).

Uso:
  cd visualizador && npm install && npm run build
  python server.py
  python server.py --port 8765 --abrir

Desarrollo frontend (proxy API en vite.config.js):
  python server.py --port 8765
  npm run dev
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import queue
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from data_api import (  # noqa: E402
    analizar_documento,
    listar_comunas,
    listar_keywords_catalogo,
    listar_markdown,
    listar_tipos,
)

_STATIC = _HERE / "dist"


class Handler(BaseHTTPRequestHandler):
    # Permite reutilizar el puerto tras Ctrl+C (TIME_WAIT).
    allow_reuse_address = True

    def log_message(self, fmt: str, *args) -> None:
        if args and str(args[0]).startswith("2"):
            return
        super().log_message(fmt, *args)

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _write_sse(self, event: str, data: str) -> None:
        payload = f"event: {event}\n"
        for line in str(data).split("\n"):
            payload += f"data: {line}\n"
        payload += "\n"
        self.wfile.write(payload.encode("utf-8"))
        self.wfile.flush()

    def _handle_analyze_stream(self, rel: str, capa: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        q: queue.Queue[tuple[str, object]] = queue.Queue()
        done = threading.Event()

        def on_log(line: str) -> None:
            q.put(("log", line))

        def worker() -> None:
            try:
                result = analizar_documento(rel, capa_chunks=capa, on_log=on_log)
                q.put(("result", result))
            except FileNotFoundError:
                q.put(("error", "archivo no encontrado"))
            except Exception as exc:
                q.put(("error", str(exc)))
            finally:
                done.set()

        threading.Thread(target=worker, daemon=True).start()

        while True:
            try:
                kind, payload = q.get(timeout=0.25)
            except queue.Empty:
                if done.is_set():
                    break
                continue
            if kind == "log":
                self._write_sse("log", json.dumps({"line": payload}, ensure_ascii=False))
            elif kind == "result":
                self._write_sse(
                    "result",
                    json.dumps(payload, ensure_ascii=False),
                )
                break
            elif kind == "error":
                self._write_sse("failed", json.dumps({"error": payload}, ensure_ascii=False))
                break

    def _send_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._send_bytes(data, ctype)
        return True

    def _send_spa(self) -> None:
        index = _STATIC / "index.html"
        if index.is_file():
            self._send_file(index)
        else:
            self.send_error(
                404,
                "Falta build: npm install && npm run build (en visualizador/)",
            )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/comunas":
            self._send_json(listar_comunas())
            return

        if path == "/api/files":
            comuna = (qs.get("comuna") or [""])[0]
            tipo = (qs.get("tipo") or [""])[0] or None
            self._send_json(listar_markdown(comuna, tipo=tipo))
            return

        if path == "/api/tipos":
            comuna = (qs.get("comuna") or [""])[0]
            self._send_json(listar_tipos(comuna))
            return

        if path == "/api/keywords":
            self._send_json(listar_keywords_catalogo())
            return

        if path == "/api/analyze/stream":
            rel = (qs.get("rel") or [""])[0]
            capa = (qs.get("capa") or ["llm"])[0]
            if not rel:
                self._send_json({"error": "falta parámetro rel"}, 400)
                return
            self._handle_analyze_stream(rel, capa)
            return

        if path == "/api/analyze":
            rel = (qs.get("rel") or [""])[0]
            capa = (qs.get("capa") or ["llm"])[0]
            if not rel:
                self._send_json({"error": "falta parámetro rel"}, 400)
                return
            try:
                data = analizar_documento(rel, capa_chunks=capa)
            except FileNotFoundError:
                self._send_json({"error": "archivo no encontrado"}, 404)
                return
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)
                return
            self._send_json(data)
            return

        if path.startswith("/assets/") or path in ("/", "/index.html"):
            if path == "/" or path == "/index.html":
                self._send_spa()
                return
            rel = path.lstrip("/")
            if self._send_file(_STATIC / rel):
                return
            self._send_spa()
            return

        candidate = _STATIC / path.lstrip("/")
        if candidate.is_file():
            self._send_file(candidate)
            return

        if path.startswith("/api/"):
            self.send_error(404)
            return

        self._send_spa()


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualizador PRC markdown")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="HOST env en Render (usar 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8765")),
        help="PORT lo define Render automáticamente",
    )
    parser.add_argument("--abrir", action="store_true", help="Abrir navegador")
    args = parser.parse_args()

    if not _STATIC.is_dir():
        print(f"No existe build React: {_STATIC}")
        print("  npm install && npm run build")
        sys.exit(1)

    url = f"http://{args.host}:{args.port}/"
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        if exc.errno in (98, 10048):  # EADDRINUSE (Linux / Windows)
            print(f"Puerto {args.port} en uso. Opciones:")
            print(f"  • Abrir el que ya corre: {url}")
            print(f"  • Matar proceso:  fuser -k {args.port}/tcp   (o  kill $(lsof -t -i:{args.port}))")
            print(f"  • Otro puerto:    python server.py --port {args.port + 1}")
            sys.exit(1)
        raise
    print(f"Visualizador PRC: {url}")
    print("Ctrl+C para detener")
    if args.abrir:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
