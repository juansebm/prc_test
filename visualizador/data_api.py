"""Datos locales del visualizador (sin zoning_plan_thesis)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils import regex as rx
from utils.zone_extractor import (
    _filtrar_contenido_prc,
    construir_chunks_para_llm,
    eliminar_marcadores_paginacion_markdown,
)

_REPO = Path(__file__).resolve().parents[1]
DATALAB_ROOT = _REPO / "data" / "datalab_markdown"

_ZONA_PALETTE = [
    "#f97316", "#06b6d4", "#a855f7", "#22c55e", "#eab308",
    "#ec4899", "#3b82f6", "#14b8a6", "#ef4444", "#84cc16",
]


def listar_comunas() -> list[str]:
    if not DATALAB_ROOT.is_dir():
        return []
    return sorted(
        p.name
        for p in DATALAB_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def listar_markdown(comuna: str, *, tipo: str | None = None) -> list[dict[str, str]]:
    base = DATALAB_ROOT / comuna.upper()
    if not base.is_dir():
        return []
    filtro = (tipo or "").strip().upper() or None
    out: list[dict[str, str]] = []
    for sub, tipo_doc in (("origen", "ORIGEN"), ("modificaciones", "MOD")):
        if filtro and filtro != tipo_doc:
            continue
        carpeta = base / sub
        if not carpeta.is_dir():
            continue
        for md in sorted(carpeta.glob("*.md")):
            out.append({
                "rel": md.relative_to(DATALAB_ROOT).as_posix(),
                "nombre": md.name,
                "tipo": tipo_doc,
                "comuna": comuna.upper(),
            })
    return out


def listar_tipos(comuna: str) -> list[str]:
    return [t for t in ("ORIGEN", "MOD") if listar_markdown(comuna, tipo=t)]


def listar_keywords_catalogo() -> dict[str, Any]:
    return {"por_campo": {}, "todas": []}


def _color_zona(zona: str) -> str:
    z = (zona or "").upper()
    h = sum(ord(c) for c in z)
    return _ZONA_PALETTE[h % len(_ZONA_PALETTE)]


def _spans_zonas(texto: str, zonas: list[str], *, max_spans: int = 400) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    vistos: set[tuple[int, int, str]] = set()
    for zona in zonas:
        for start, end in rx.iter_spans_evidencia_codigo_zona(texto, zona, max_spans=50):
            if not rx._span_contiene_codigo_mayusculas(texto, start, end, zona):
                continue
            key = (start, end, zona)
            if key in vistos:
                continue
            vistos.add(key)
            spans.append({
                "type": "zona",
                "start": start,
                "end": end,
                "label": zona,
                "color": _color_zona(zona),
            })
            if len(spans) >= max_spans:
                return spans
    return spans


def analizar_documento(
    rel_path: str,
    *,
    capa_chunks: str = "llm",
    on_log=None,
) -> dict[str, Any]:
    path = DATALAB_ROOT / rel_path.replace("\\", "/")
    if not path.is_file():
        raise FileNotFoundError(rel_path)

    if on_log:
        on_log("Leyendo markdown…")
    raw = path.read_text(encoding="utf-8", errors="replace")
    es_mod = "modificaciones" in path.parts
    texto = eliminar_marcadores_paginacion_markdown(_filtrar_contenido_prc(raw))

    if on_log:
        on_log("Descubriendo zonas / chunks…")
    pack = construir_chunks_para_llm(texto, es_modificacion=es_mod, solo_relevantes=True)
    zonas: list[str] = list(pack.get("zonas") or [])
    chunks = list(pack.get("chunks") or [])

    bloques = []
    for n, ch in enumerate(chunks, start=1):
        t = ch.get("texto") or ""
        if not t.strip():
            continue
        zs = list(ch.get("zonas") or [])
        start = ch.get("start")
        if start is None:
            start = 0
        bloques.append({
            "fuente": "zone_extractor",
            "numero": n,
            "idx": ch.get("idx"),
            "hash": ch.get("hash"),
            "kind": ch.get("kind", ""),
            "inicio": start,
            "fin": start + len(t),
            "start": start,
            "end": start + len(t),
            "recuperado_tfidf": bool(ch.get("recuperado_zone_extractor")),
            "pasa_filtro": True,
            "tiene_keywords": False,
            "texto": t,
            "zonas": zs,
            "zonas_asignadas": zs,
            "chars": len(t),
            "highlights": _spans_zonas(t, zs),
        })

    if on_log:
        on_log(f"Listo: {len(zonas)} zona(s), {len(bloques)} chunk(s).")

    return {
        "rel": rel_path.replace("\\", "/"),
        "comuna": path.parts[-3] if len(path.parts) >= 3 else "",
        "nombre": path.name,
        "es_modificacion": es_mod,
        "chars": len(texto),
        "n_paginas": 1,
        "zonas": zonas,
        "zona_colors": {z: _color_zona(z) for z in zonas},
        "n_descartados_tfidf": 0,
        "chunks_ok_tfidf": len(bloques),
        "chunks_total_tfidf": len(bloques),
        "n_descartados_llm": 0,
        "chunks_ok_llm": len(bloques),
        "chunks_total_llm": len(bloques),
        "indices_relevantes": list(pack.get("indices_relevantes") or []),
        "n_chunks_corpus": int(pack.get("n_chunks_corpus") or 0),
        "bloques": bloques,
        "bloques_tfidf": None,
        "bloques_llm": None,
    }
