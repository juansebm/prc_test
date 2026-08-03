"""Descubrimiento de zonas PRC: regex + filtros de evidencia sobre el documento (sin LLM). Ver normativa_extraccion."""

from __future__ import annotations

import sys
from pathlib import Path

# `python scripts/utils/zone_extractor.py`: Python inserta .../scripts/utils/ en sys.path[0].
# Eso hace que `import regex` (p. ej. tiktoken) cargue *este* repo: utils/regex.py en vez del
# paquete PyPI `regex` → AttributeError: module 'regex' has no attribute 'escape'.
_utils_dir = Path(__file__).resolve().parent
_scripts_dir = _utils_dir.parent
_sp_utils = str(_utils_dir)
if _sp_utils in sys.path:
    sys.path.remove(_sp_utils)
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import argparse
import csv
import hashlib
import os
import re

import tiktoken
from rich.console import Console

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

console = Console()

# Glosas legibles para avisos de filtrado (Paso 1 — descubrimiento de zonas).
_GLOSA_EVIDENCIA_ZONA = (
    "sin uso normativo de zona (p. ej. «ZONA B1», «Sector Especial E10», celda | E1 | en tabla)"
)
_GLOSA_FORMA_ZONA = (
    "forma inválida para zonificación (esperado A–H±dígitos, Z-*, sectores E*; "
    "no planos ni admin.: CUS, PRM, FA…, MH…)"
)

def _normalizar_zona(zona: str) -> str:
    from utils import regex as _rx

    return _rx.normalizar_zona(zona)


def _normalizar_codigo_zona(raw: str) -> str:
    from utils import regex as _rx

    return _rx.normalizar_codigo_zona(raw)


def _es_codigo_zona_token(nz: str) -> bool:
    if not nz or not nz[0].isalnum():
        return False
    for c in nz[1:]:
        if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-":
            return False
    return True


def _longitud_maxima_codigo_prc(z: str) -> int:
    from utils import regex as _rx

    return _rx.longitud_maxima_codigo_prc(z)


def _tiene_digito(z: str) -> bool:
    return any(c.isdigit() for c in z)


def _prefijo_2mas_letras_dig(z: str) -> str | None:
    i = 0
    while i < len(z) and "A" <= z[i] <= "Z":
        i += 1
    if i < 2:
        return None
    j = i
    while j < len(z) and z[j].isdigit():
        j += 1
    if j == i or j != len(z):
        return None
    return z[:i]


def _max_run_digitos(s: str) -> int:
    best = cur = 0
    for c in s:
        if c.isdigit():
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


# Prefijos típicos de IDs de plano / parcela en tablas (no códigos de zona PRC).
_PREFIJOS_RUIDO_PLANO: frozenset[str] = frozenset({"PR", "MP", "RO", "CF"})

# Zonas PRC de una sola letra (Santiago A–H; Valparaíso I = plazas del plan, etc.).
_LETRAS_ZONA_MACRO_UNA = frozenset("ABCDEFGHI")


def _es_compuesto_tipo_b15b1(u: str) -> bool:
    """Código compuesto tipo B15B1: bloque inicial letras + dígitos + letra + dígito final."""
    if len(u) != 5:
        return False
    i = 0
    while i < len(u) and u[i].isalpha():
        i += 1
    if i == 0 or i > 3:
        return False
    j = i
    while j < len(u) and u[j].isdigit():
        j += 1
    if j == i or (j - i) > 3:
        return False
    if j >= len(u) or not u[j].isalpha():
        return False
    j += 1
    if j >= len(u) or not u[j].isdigit():
        return False
    return j + 1 == len(u)


# Subzonas jerárquicas colapsadas (Iquique: BC2-2.1 → BC221, FC2-1 → FC21).
# Primera letra A–H: evita IDs administrativos (NE5030, LRD411, …).
_RE_CODIGO_JERARQUICO_COLAPSADO = re.compile(r"^[A-H][A-Z]\d{2,4}$")


def _es_codigo_zona_prefijo_z(z: str) -> bool:
    """ZCC, ZAP, ZRB, ZEPCC… (prefijo Z + siglas del instrumento, con o sin dígito)."""
    u = z.strip().upper()
    if not u.startswith("Z") or len(u) < 2:
        return False
    if re.fullmatch(r"Z\d+-\d+", u):
        return True
    suf = u[1:]
    return bool(suf) and all(c.isalnum() for c in suf)


def _es_codigo_subzona_z_parent_guion_sub(z: str) -> bool:
    """Subzonas Z{n}-{m} (p. ej. Z1-1, Z7-1), distintas de Z11/Z12 sin guión."""
    return bool(re.fullmatch(r"Z\d+-\d+", (z or "").strip().upper()))


def _es_codigo_zona_prefijo_m(z: str) -> bool:
    """Iquique Plan Seccional Sur: M1–M12, subzona M-6-1 → M61."""
    u = z.strip().upper()
    if not u.startswith("M") or len(u) < 2:
        return False
    tail = u[1:]
    if not tail.isdigit():
        return False
    n = int(tail)
    return 1 <= n <= 99


def _es_codigo_zona_prefijo_u_r(z: str) -> bool:
    """PRCT Talca 2011: U1–U22 urbanas, R1–R7 (+ subzonas R3A, R7B…)."""
    u = z.strip().upper()
    m = re.fullmatch(r"([UR])(\d{1,2})([A-Z])?", u)
    if not m:
        return False
    pref, digs, _suf = m.group(1), int(m.group(2)), m.group(3)
    if pref == "U":
        return 1 <= digs <= 30
    return 1 <= digs <= 20


def _es_codigo_zona_prefijo_v(z: str) -> bool:
    """Viña del Mar: V1–V11, V6A, V6B… (residencial / plan seccional)."""
    u = z.strip().upper()
    m = re.fullmatch(r"V(\d{1,2})([A-Z])?", u)
    if not m:
        return False
    return 1 <= int(m.group(1)) <= 99


def _codigo_zona_tiene_letra(z: str) -> bool:
    from utils import regex as _rx

    return _rx.codigo_zona_tiene_letra(z)


def _estructura_codigo_prc_plausible(z: str) -> bool:
    """
    Alineado con patrones del GT (p. ej. SANTIAGO.csv): descarta ruido tipo CF907B, AB, PR5,
    Y84 (letra+dígitos fuera del esquema), manteniendo Z* para comunas como Ñuñoa.
    """
    u = z.strip().upper()
    if not u or u.isdigit() or not _codigo_zona_tiene_letra(u):
        return False
    if not u[0].isalpha():
        return False
    # CUS1, CUS 2, ... son "Cuadros de Usos de Suelo", no zonas.
    if u.startswith("CUS") and u[3:].isdigit():
        return False
    # CU03 = OCR de «Cuadro CUS 3» (identificador de cuadro, no zona).
    if re.fullmatch(r"CU\d{1,2}", u):
        return False
    # PRM99, etc.: láminas del Plan Regulador Metropolitano de Santiago, no zonas comunales.
    if u.startswith("PRM") and u[3:].isdigit():
        return False
    # PS1, PS2…: láminas de Plano Seccional (p. ej. AH-AM-0496 PS1), no zonas PRC.
    if re.fullmatch(r"PS\d{1,2}", u):
        return False
    # C17O, T57O: códigos de vía en tablas PRMS (orientación), no zonas PRC.
    if re.fullmatch(r"[A-Z]\d{1,2}O", u):
        return False
    if _es_codigo_numeral_romano_no_zona(u):
        return False
    if _es_codigo_subzona_z_parent_guion_sub(u):
        return True
    # ZCHAL-V / ZCHAL-B (Valparaíso): subzona con sufijo de una letra.
    if re.fullmatch(r"Z[A-Z]{2,7}-[A-Z]", u):
        return True
    # Subzonas jerárquicas colapsadas (Iquique: BC2-2.1 → BC221, FC2-1 → FC21).
    if _RE_CODIGO_JERARQUICO_COLAPSADO.fullmatch(u):
        return True
    if _max_run_digitos(u) > 2:
        return False
    if len(u) > _longitud_maxima_codigo_prc(u):
        return False
    for p in _PREFIJOS_RUIDO_PLANO:
        if u.startswith(p) and len(u) > len(p):
            return False
    if len(u) == 2 and u.isalpha():
        return u not in _CODIGOS_LEXICOS_SPURIOUS
    if len(u) == 1:
        # Una letra de zona macro del catálogo (A–I); evita S, T, D de siglas sueltas.
        return u in _LETRAS_ZONA_MACRO_UNA
    if _es_codigo_zona_prefijo_z(u):
        return True
    if _es_codigo_zona_prefijo_u_r(u):
        return True
    if _es_codigo_zona_prefijo_v(u):
        return True
    if _es_codigo_zona_prefijo_m(u):
        return True
    # Instrumentos / densificación fuera del esquema «A–H + dígito» de Santiago (p. ej. Ñuñoa 2019).
    if u.startswith("ICH") and len(u) >= 4:
        tail = u[3:]
        if tail.isdigit() and 1 <= len(tail) <= 3:
            return True
    if _es_compuesto_tipo_b15b1(u):
        return True
    # Rancagua y similares: SM1, EQS, EQ, CH (2–4 letras o letras+dígito).
    if re.fullmatch(r"[A-Z]{2,4}", u) and u not in _CODIGOS_LEXICOS_SPURIOUS:
        return True
    if re.fullmatch(r"[A-Z]{2,3}\d{1,2}", u):
        return True
    resto = u[1:]
    if resto.isdigit():
        if not (1 <= len(resto) <= 3):
            return False
        # GT Santiago y mods típicos: letra inicial A–H (Y84, A96 espurios quedan fuera).
        return "A" <= u[0] <= "H"
    return False


def _skip_ws(u: str, k: int) -> int:
    while k < len(u) and u[k] in " \t\n\r\f\v":
        k += 1
    return k


def _buscar_indice_inicio_ordenanza(contenido: str) -> int | None:
    """Equivalente a RE_INICIO_ORDENANZA: primera coincidencia entre alternativas."""
    lo = contenido.lower()
    cands: list[int] = []

    j = lo.find("ordenanza local")
    if j >= 0:
        cands.append(j)

    pos = 0
    while True:
        j = lo.find("capitulo", pos)
        if j < 0:
            break
        k = j + len("capitulo")
        k = _skip_ws(lo, k)
        if k < len(lo) and lo[k] == "i":
            nxt = k + 1
            if nxt >= len(lo) or not lo[nxt].isalpha():
                cands.append(j)
        pos = j + 1

    for needle in ("artículo 1", "articulo 1"):
        pos = 0
        while True:
            j = lo.find(needle, pos)
            if j < 0:
                break
            tail = lo[j + len(needle) : j + len(needle) + 80]
            if "la presente ordenanza" in tail or "presente ordenanza" in tail:
                cands.append(j)
                break
            pos = j + 1

    return min(cands) if cands else None

TIKTOKEN_MODEL = os.environ.get("TIKTOKEN_MODEL", os.environ.get("LLM_MODEL", "gpt-4o-mini"))

CHUNK_TOKENS = int(os.environ.get("ZONE_CHUNK_TOKENS", "512"))
CHUNK_OVERLAP_TOKENS = int(os.environ.get("ZONE_CHUNK_OVERLAP_TOKENS", "96"))
CHUNK_SIZE = max(256, CHUNK_TOKENS * 4)
CHUNK_OVERLAP = max(64, CHUNK_OVERLAP_TOKENS * 4)
# Tablas: tope por trozo (cabecera repetida en cada uno); por defecto igual que prosa.
TABLE_CHUNK_TOKENS = int(os.environ.get("ZONE_TABLE_CHUNK_TOKENS", str(CHUNK_TOKENS)))

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_COMUNAS_INTERES_DEFAULT = _REPO_ROOT / "scripts" / "comunas_interes.txt"
_DATALAB_MARKDOWN_DEFAULT = _REPO_ROOT / "data" / "datalab_markdown"

MAX_ZONAS = 80

# Numerales romanos (II, III, IV…): «Punto II», «Zona II» PRMS/Providencia, no zonas PRC.
_RE_CODIGO_NUMERAL_ROMANO = re.compile(r"^[IVXLCDM]{2,}$")


def _es_codigo_numeral_romano_no_zona(u: str) -> bool:
    return bool(_RE_CODIGO_NUMERAL_ROMANO.fullmatch((u or "").strip().upper()))


# Códigos de 2 letras que casi siempre son ruido (preposiciones / OCR), no zona.
_CODIGOS_LEXICOS_SPURIOUS: frozenset[str] = frozenset({
    "DE", "EN", "EL", "LA", "LO", "AL", "UN", "HA", "SE", "SI", "NO", "ES", "ME", "TE", "SU", "MI",
    "DA", "YA", "OH", "EH", "UH",
    # Abreviaturas frecuentes en títulos («Av.», «Ed.»), no zonas PRC.
    "AV", "ED", "PG", "CM", "ID",
})

# PREPROCESAMIENTO DEL DOCUMENTO
# ═══════════════════════════════════════════════════════════════════════════


def _filtrar_contenido_prc(contenido: str) -> str:
    """
    Elimina el encabezado de Diario Oficial (otras resoluciones, columnas
    paralelas, etc.) que precede al texto de la Ordenanza Local del PRC.

    Si el marcador se encuentra después del 3 % inicial del documento,
    recorta desde 200 chars antes de ese punto para conservar contexto.
    Si no se detecta inicio claro, devuelve el contenido íntegro.
    """
    idx = _buscar_indice_inicio_ordenanza(contenido)
    if idx is not None and idx > len(contenido) * 0.03:
        inicio = max(0, idx - 200)
        pct = inicio / len(contenido) * 100
        console.print(
            f"  [dim]✂ Encabezado previo al PRC descartado "
            f"(chars 0–{inicio:,}, {pct:.1f}% del doc)[/dim]"
        )
        return contenido[inicio:]
    return contenido


# Rótulos de paginación insertados al convertir PDF→markdown (no son normativa).
_RE_SOLO_LINEA_PAGINA_MD = re.compile(
    r"^[ \t]*(?:Página|Page)\s+\d+(?:\s+(?:de|of)\s+\d+)?[^\n]*\r?$",
    re.MULTILINE | re.IGNORECASE,
)
_RE_LLAVE_NUM_SEPARADOR = re.compile(
    r"^[ \t]*\{[ \t]*\d+[ \t]*\}[ \t]*-+[ \t]*\r?$",
    re.MULTILINE,
)


def eliminar_marcadores_paginacion_markdown(texto: str) -> str:
    """
    Quita líneas de paginación típicas del markdown Datalab/PDF (p. ej. «Página 77 de 84»,
    «{77}------------------------------------------------») para que no se mezclen con códigos de zona.
    """
    if not (texto or "").strip():
        return texto
    t = _RE_SOLO_LINEA_PAGINA_MD.sub("", texto)
    t = _RE_LLAVE_NUM_SEPARADOR.sub("", t)
    return re.sub(r"\n{3,}", "\n\n", t)


# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES TIKTOKEN
# ═══════════════════════════════════════════════════════════════════════════

# Codificador para TIKTOKEN_MODEL; si tiktoken no conoce el modelo cae a cl100k_base
_TIKTOKEN_ENC: object | None = None


class _FallbackCharEncoding:
    """Fallback offline mínimo: preserva offsets usando un token por carácter."""

    def encode(self, texto: str) -> list[int]:
        return [ord(ch) for ch in texto]

    def decode(self, ids: list[int]) -> str:
        return "".join(chr(i) for i in ids)


def _get_enc() -> object:
    global _TIKTOKEN_ENC
    if _TIKTOKEN_ENC is None:
        try:
            _TIKTOKEN_ENC = tiktoken.encoding_for_model(TIKTOKEN_MODEL)
        except Exception as e:
            try:
                _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")
            except Exception:
                console.print(
                    f"[yellow]  ⚠ tiktoken no disponible offline ({type(e).__name__}); "
                    "usando segmentación por caracteres[/yellow]"
                )
                _TIKTOKEN_ENC = _FallbackCharEncoding()
    return _TIKTOKEN_ENC


# ═══════════════════════════════════════════════════════════════════════════
# Descubrimiento regex (scanners + ventanas con dígito)
# ═══════════════════════════════════════════════════════════════════════════

_ZONA_DENY = frozenset({
    "DE", "DEL", "LOS", "LAS", "UN", "UNA", "EL", "LA", "EN", "AL",
    "QUE", "COMO", "O", "Y",
})

_SECT_ESP_HDR = (
    "SECTORES ESPECIALES",
    "SECTORES ESPECIAL",
    "SECTOR ESPECIALES",
    "SECTOR ESPECIAL",
)


def _al_inicio_token_alnum(u: str, i: int) -> bool:
    return i == 0 or not u[i - 1].isalnum()


def _sufijo_z_post_digito_es_codigo_plausible(suf: str) -> bool:
    """
    Tras «Zona Z-N » + espacio, regla general (sin lista casuística de palabras):

    - 1 letra → subzona típica (Z-1 C, Z-2 A).
    - 2 caracteres solo si es letra + dígito (p. ej. … Z-1 A1).
    - 2 letras seguidas → casi siempre español colado («en», «no», «lo», «de»… en MAYÚSCULAS),
      no código PRC → rechazar.
    """
    if not suf or not suf[0].isalpha():
        return False
    if len(suf) == 1:
        # «… Zona Z-3 y Zona Z-4» / «… Z-3 o Z-4»: una sola letra, no subzona.
        if suf in ("Y", "O"):
            return False
        return True
    if len(suf) == 2:
        return suf[0].isalpha() and suf[1].isdigit()
    return False


def _extender_codigo_letras_espaciadas_tras_zona(
    u: str, tok_start: int, tok_end: int,
) -> tuple[int, int]:
    """
    OCR/Datalab: «ZONA S M 1», «ZONA E Q S», «ZONA C H» → letras sueltas separadas por espacio.
    """
    if tok_end <= tok_start or not u[tok_start:tok_end].isalpha():
        return tok_start, tok_end
    n_letters = tok_end - tok_start
    k = tok_end
    while k < len(u) and n_letters < 5:
        k2 = _skip_ws(u, k)
        if k2 >= len(u):
            break
        c = u[k2]
        if c.isdigit():
            num_start = k2
            while k2 < len(u) and u[k2].isdigit() and (k2 - num_start) < 4:
                k2 += 1
            tok_end = k2
            k = k2
            continue
        if not ("A" <= c <= "Z"):
            break
        nxt = k2 + 1
        if nxt < len(u) and u[nxt].isalpha():
            break
        n_letters += 1
        tok_end = k2 + 1
        k = tok_end
    return tok_start, tok_end


def _extender_sufijo_guion_espaciado(u: str, tok_start: int, tok_end: int) -> tuple[int, int]:
    """
    «Zona R - M», «Zona A - V», «Zona H - 1», «Zona ZCHAL – V» → extiende el token tras la letra inicial.
    """
    from utils import regex as _rx

    if tok_end <= tok_start or not u[tok_end - 1].isalpha():
        return tok_start, tok_end
    k = _skip_ws(u, tok_end)
    if k >= len(u) or u[k] not in _rx._CHARS_GUION_DO:
        return tok_start, tok_end
    k = _skip_ws(u, k + 1)
    if k >= len(u):
        return tok_start, tok_end
    suffix_start = k
    while k < len(u) and k - suffix_start < 3 and u[k] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        k += 1
    if k == suffix_start or (k < len(u) and u[k].isalnum()):
        return tok_start, tok_end
    return tok_start, k


def _finalizar_token_tras_zona(u: str, tok_start: int, tok_end: int) -> tuple[str, int]:
    ts, te = _extender_sufijo_guion_espaciado(u, tok_start, tok_end)
    ts, te = _extender_codigo_letras_espaciadas_tras_zona(u, ts, te)
    return u[ts:te], te


def _leer_token_tras_zona(u: str, j: int) -> tuple[str, int] | None:
    """
    Token inmediatamente tras «ZONA» (p. ej. Z1, B5, ZI2).

    Además acepta la grafía frecuente «Z 1», «ZI 1», «ZR 1» (espacio antes de los dígitos),
    que de otro modo deja solo «Z»/«ZI» y rompe descubrimiento y evidencia.
    """
    if j >= len(u) or not u[j].isalnum():
        return None
    k = j
    _tok_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-–—‑"
    while k < len(u) and k - j < 13 and u[k] in _tok_chars:
        k += 1
    tok_start, tok_end = j, k
    if tok_end < len(u) and u[tok_end] in " \t\n\r\f\v":
        k2 = _skip_ws(u, tok_end)
        # «Zona Z-2 Tramo A» → mismo código normalizado que «Zona Z2A» / «Z-2A».
        if (
            tok_end > tok_start
            and u[tok_end - 1].isdigit()
            and k2 < len(u)
            and u.startswith("TRAMO", k2)
        ):
            after_tramo = k2 + len("TRAMO")
            if after_tramo >= len(u) or not u[after_tramo].isalpha():
                k_t = _skip_ws(u, after_tramo)
                if k_t < len(u) and ("A" <= u[k_t] <= "Z"):
                    suf_ch = u[k_t]
                    k_after_suf = k_t + 1
                    if k_after_suf >= len(u) or not u[k_after_suf].isalnum():
                        return u[tok_start:tok_end] + suf_ch, k_after_suf
        if k2 < len(u) and u[k2].isdigit():
            num_start = k2
            while k2 < len(u) and u[k2].isdigit() and (k2 - num_start) < 4:
                k2 += 1
            return _finalizar_token_tras_zona(u, tok_start, k2)
        # Grafía frecuente en PRC: «Zona Z-1 C», «Zona Z-2 A» (espacio entre número y letra final).
        # Se acepta SOLO para códigos que parten por Z*, para no ensanchar el espacio de búsqueda
        # de zonas letra+dígitos típico de Santiago (A1, B5, etc.).
        if (
            k2 < len(u)
            and ("A" <= u[k2] <= "Z")
            and tok_end > tok_start
            and u[tok_start] == "Z"
            and u[tok_end - 1].isdigit()
        ):
            # Sufijo acotado: típicamente 1 letra (Z-1 C) o 1 letra + dígito (Z-1 A1).
            # Evitar capturar palabras (“DEL”, “DE”, etc.) como en «Zona Z-3 del PRCN».
            k3 = k2
            suffix: list[str] = []
            while k3 < len(u) and len(suffix) < 2 and u[k3] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
                suffix.append(u[k3])
                k3 += 1
            suf = "".join(suffix)
            if (
                _sufijo_z_post_digito_es_codigo_plausible(suf)
                and (k3 == len(u) or not u[k3].isalnum())
            ):
                return _finalizar_token_tras_zona(u, tok_start, k3)
    return _finalizar_token_tras_zona(u, tok_start, tok_end)


def _codigo_en_linea_antes_de_zona(u: str, pos_zona: int) -> str | None:
    """
    Grafía «##### Z5 ZONA AREA…», «ZCH ZONA DE…»: el código va al inicio del
    encabezado (tras # / **), no en prosa («PARA CADA ZONA»).
    """
    line_start = u.rfind("\n", 0, pos_zona) + 1
    line_prefix = u[line_start:pos_zona]
    m = re.match(
        r"^(?:#{1,6}\s*)?(?:\*\*)?\s*"
        r"([A-Z]{1,4}\d{0,2}(?:-\d{1,2})?)"
        r"\s*$",
        line_prefix,
    )
    if not m:
        return None
    raw = m.group(1)
    if not _raw_plausible_codigo_catalogo_prc(raw):
        return None
    return raw


def _scan_zona_codigos(u: str, cands: set[str]) -> None:
    i = 0
    while i < len(u) - 3:
        if u.startswith("ZONA", i) and _al_inicio_token_alnum(u, i):
            j = i + 4
            j = _skip_ws(u, j)
            cod_prev = _codigo_en_linea_antes_de_zona(u, i)
            if cod_prev:
                cod = _normalizar_codigo_zona(cod_prev)
                if cod and _es_codigo_zona_token(cod):
                    cands.add(cod)
            else:
                got = _leer_token_tras_zona(u, j)
                if got:
                    tok, _end = got
                    if tok and tok not in _ZONA_DENY:
                        cands.add(_normalizar_codigo_zona(tok))
            i += 1
            continue
        i += 1


def _read_upper_letters(u: str, k: int, lo: int, hi: int) -> tuple[str, int] | None:
    start = k
    n = 0
    while k < len(u) and n < hi and "A" <= u[k] <= "Z":
        n += 1
        k += 1
    if n < lo:
        return None
    return u[start:k], k


def _read_digits_len(u: str, k: int, lo: int, hi: int) -> tuple[str, int] | None:
    start = k
    n = 0
    while k < len(u) and n < hi and u[k].isdigit():
        n += 1
        k += 1
    if n < lo:
        return None
    return u[start:k], k


def _scan_sectors_conserv_especial(u: str, cands: set[str]) -> None:
    i = 0
    while i < len(u):
        seg: int | None = None
        if u.startswith("SECTORES", i) and _al_inicio_token_alnum(u, i):
            seg = i + len("SECTORES")
        elif u.startswith("SECTOR", i) and _al_inicio_token_alnum(u, i):
            seg = i + len("SECTOR")
        else:
            i += 1
            continue
        j = _skip_ws(u, seg)
        if u.startswith("DE", j) and (j + 2 == len(u) or not u[j + 2].isalpha()):
            j = _skip_ws(u, j + 2)
        j = _skip_ws(u, j)
        ok = False
        if u.startswith("CONSERVACION", j):
            j += len("CONSERVACION")
            ok = True
        elif u.startswith("CONSERVACIÓN", j):
            j += len("CONSERVACIÓN")
            ok = True
        elif u.startswith("ESPECIAL", j):
            j += len("ESPECIAL")
            ok = True
        if not ok:
            i += 1
            continue
        j = _skip_ws(u, j)
        r1 = _read_upper_letters(u, j, 1, 4)
        if not r1:
            i += 1
            continue
        letters, k = r1
        k = _skip_ws(u, k)
        if k < len(u) and u[k] == "-":
            k += 1
            k = _skip_ws(u, k)
        r2 = _read_digits_len(u, k, 1, 3)
        if not r2:
            i += 1
            continue
        digits, k = r2
        if k < len(u) and u[k].isalnum():
            i += 1
            continue
        cands.add(_normalizar_codigo_zona(letters + digits))
        i += 1


_RE_SUBSECTOR_PRC = re.compile(
    r"(?i)(?:sub[\s-]*(?:zonas?|sectores?)|sub[\s-]*sector|subsector)\s+"
    r"([A-Z])\s*-\s*(\d{1,3})(?:\s+([A-Z]))?(?![A-Z0-9])"
)
_RE_SUBSECTOR_LINEA_USO = re.compile(
    r"(?i)(?<![A-Za-z])([A-Z])\s*-\s*(\d{1,3})(?:\s*([A-Z]))?\s+"
    r"(?:TEATRO|EQUIPAMIENTO|PLAZA)\b"
)


def _codigo_subsector_letra_dig_suf(letra: str, digs: str, suf: str | None) -> str:
    return _normalizar_codigo_zona(letra + digs + (suf or "").strip())


def _scan_subsectores_prc(u: str, cands: set[str]) -> None:
    """Sub-Sector / Subsector D - 1 / D - 1A (PRC seccionales; p. ej. Teatro Municipal)."""
    for m in _RE_SUBSECTOR_PRC.finditer(u):
        cands.add(_codigo_subsector_letra_dig_suf(m.group(1), m.group(2), m.group(3)))
    for m in _RE_SUBSECTOR_LINEA_USO.finditer(u):
        cands.add(_codigo_subsector_letra_dig_suf(m.group(1), m.group(2), m.group(3)))


_RE_CODIGO_ZONA_GUION = re.compile(
    r"(?<![A-Z])(Z(?:E|R|U)?)\s*[-–—]\s*(\d{1,2}|[A-Z])(?![A-Z0-9])",
    re.IGNORECASE,
)

_RE_CODIGO_UR_GUION = re.compile(
    r"(?<![A-Z])([UR])\s*[-–—‑]\s*(\d{1,2})(?:\s+([A-Z]))?(?![A-Z0-9])",
    re.IGNORECASE,
)

_RE_CODIGO_M_GUION = re.compile(
    r"(?<![A-Z])M\s*[-–—‑]\s*(\d{1,2})(?:\s*[-–—‑]\s*(\d))?(?![A-Z0-9.])",
    re.IGNORECASE,
)

# Catálogo PRC en markdown / listados (Gorbea: «- **ZC**»; Alto Hospicio: «Z1-1 Zona…»).
_RE_MD_BULLET_CODIGO_ZONA = re.compile(
    r"(?m)^\s*-\s*\*\*([A-Z]{1,4}\d{0,2}(?:-\d{1,2})?)\*\*\s*$",
)
_RE_MD_ENCABEZADO_CODIGO_ZONA = re.compile(
    r"(?m)^#{1,6}\s*(?:\*\*)?\s*"
    r"([A-Z]{1,4}\d{0,2}(?:-\d{1,2})?)"
    r"\s*(?:[-–—]\s*)?"
    r"(?:ZONA|ÁREA|AREA)\b",
    re.IGNORECASE,
)
_RE_LINEA_CATALOGO_CODIGO_ZONA = re.compile(
    r"(?m)^[ \t]*((?:Z\d{1,2}-\d{1,2})|[A-Z]{1,3}\d{0,2})\s+Zona\b",
    re.IGNORECASE,
)
_RE_CODIGO_Z_SUBZONA_INLINE = re.compile(
    r"(?<![A-Z0-9])Z(\d{1,2})[-–—](\d{1,2})(?![A-Z0-9])",
)


def _codigo_desde_prefijo_sufijo_guion(pref: str, suf: str) -> str:
    """Z-1 → Z1, ZE-1 → ZE1, ZU-1 → ZU1, Z-D → ZD (vía _normalizar_codigo_zona)."""
    p = pref.upper().strip()
    s = suf.upper().strip()
    if s.isdigit():
        return _normalizar_codigo_zona(p + s)
    if len(s) == 1 and s.isalpha():
        return _normalizar_codigo_zona(p + s)
    return ""


def _scan_codigos_zona_guion(u: str, cands: set[str]) -> None:
    """
    Códigos con guión (o raya tipográfica) entre prefijo y sufijo: Z-1, ZE—3, ZR-8, ZU-1, Z-D.
    PRC Talca 1990 y listados «Zonas siguientes: Z-1, Z-2, …».
    """
    for m in _RE_CODIGO_ZONA_GUION.finditer(u):
        cod = _codigo_desde_prefijo_sufijo_guion(m.group(1), m.group(2))
        if cod and _es_codigo_zona_token(cod):
            cands.add(cod)


def _scan_codigos_ur_guion(u: str, cands: set[str]) -> None:
    """U-1, R-3, Subzona R-3 A → U1, R3, R3A (PRCT Talca 2011)."""
    for m in _RE_CODIGO_UR_GUION.finditer(u):
        pref, dig, suf = m.group(1), m.group(2), m.group(3)
        cod = _normalizar_codigo_zona(pref + dig + (suf or ""))
        if cod and _es_codigo_zona_token(cod):
            cands.add(cod)


def _scan_codigos_m_guion(u: str, cands: set[str]) -> None:
    """M-1, M-10, M-6-1 → M1, M10, M61 (Iquique Plan Seccional Sur)."""
    for m in _RE_CODIGO_M_GUION.finditer(u):
        d1, d2 = m.group(1), m.group(2)
        cod = _normalizar_codigo_zona("M" + d1 + (d2 or ""))
        if cod and _es_codigo_zona_token(cod):
            cands.add(cod)


def _raw_plausible_codigo_catalogo_prc(raw: str) -> bool:
    u = raw.strip().upper()
    if not u or u in _ZONA_DENY or u in _CODIGOS_LEXICOS_SPURIOUS:
        return False
    if _es_codigo_subzona_z_parent_guion_sub(u):
        return True
    if _es_codigo_zona_prefijo_z(u):
        return True
    if re.fullmatch(r"ZM\d+", u):
        return True
    return _estructura_codigo_prc_plausible(u)


def _scan_codigos_zona_catalogo_md(u: str, cands: set[str]) -> None:
    """
    Códigos en catálogos y rótulos markdown sin prefijo «ZONA» delante:
    «- **ZC**», «##### ZE - ZONA…», «Z1-1 Zona Equipamiento», «Z7-1 Zona…».
    """
    for pat in (
        _RE_MD_BULLET_CODIGO_ZONA,
        _RE_MD_ENCABEZADO_CODIGO_ZONA,
        _RE_LINEA_CATALOGO_CODIGO_ZONA,
    ):
        for m in pat.finditer(u):
            raw = m.group(1)
            if _raw_plausible_codigo_catalogo_prc(raw):
                cod = _normalizar_codigo_zona(raw)
                if cod and _es_codigo_zona_token(cod):
                    cands.add(cod)
    for m in _RE_CODIGO_Z_SUBZONA_INLINE.finditer(u):
        cod = _normalizar_codigo_zona(f"Z{m.group(1)}-{m.group(2)}")
        if cod and _es_codigo_zona_token(cod):
            cands.add(cod)


def _parse_pareja_especiales(u: str, j: int) -> tuple[str, str] | None:
    r1 = _read_upper_letters(u, j, 1, 4)
    if not r1:
        return None
    let1, k = r1
    k = _skip_ws(u, k)
    if k < len(u) and u[k] == "-":
        k += 1
        k = _skip_ws(u, k)
    d1 = _read_digits_len(u, k, 1, 3)
    if not d1:
        return None
    dig1, k = d1
    k = _skip_ws(u, k)
    if k >= len(u) or u[k] != "Y":
        return None
    k = _skip_ws(u, k + 1)
    r2 = _read_upper_letters(u, k, 1, 4)
    if not r2:
        return None
    let2, k = r2
    k = _skip_ws(u, k)
    if k < len(u) and u[k] == "-":
        k += 1
        k = _skip_ws(u, k)
    d2 = _read_digits_len(u, k, 1, 3)
    if not d2:
        return None
    dig2, k = d2
    if k < len(u) and u[k].isalnum():
        return None
    return let1 + dig1, let2 + dig2


def _scan_sectores_especiales_pareja(u: str, cands: set[str]) -> None:
    i = 0
    while i < len(u):
        seg: int | None = None
        for hdr in _SECT_ESP_HDR:
            if u.startswith(hdr, i) and _al_inicio_token_alnum(u, i):
                seg = i + len(hdr)
                break
        if seg is None:
            i += 1
            continue
        j = _skip_ws(u, seg)
        pair = _parse_pareja_especiales(u, j)
        if pair:
            a, b = pair
            cands.add(_normalizar_codigo_zona(a))
            cands.add(_normalizar_codigo_zona(b))
        i += 1


def _leer_codigo_zch_se(u: str, k: int) -> str | None:
    if k >= len(u) or not ("A" <= u[k] <= "Z"):
        return None
    start = k
    k += 1
    if k >= len(u) or not u[k].isdigit():
        return None
    k += 1
    ntrail = 0
    while k < len(u) and ntrail < 10:
        c = u[k]
        if ("A" <= c <= "Z") or c.isdigit():
            ntrail += 1
            k += 1
        else:
            break
    if k < len(u) and u[k].isalnum():
        return None
    return u[start:k]


def _scan_zch_y_se(u: str, cands: set[str]) -> None:
    i = 0
    while i < len(u):
        if u.startswith("ZCH", i) and _al_inicio_token_alnum(u, i):
            j = i + 3
            j = _skip_ws(u, j)
            cod = _leer_codigo_zch_se(u, j)
            if cod:
                cands.add(_normalizar_codigo_zona(cod))
            i += 1
            continue
        if (
            u.startswith("SE", i)
            and _al_inicio_token_alnum(u, i)
            and not u.startswith("SECTOR", i)
            and not u.startswith("SECTORES", i)
        ):
            j = i + 2
            j = _skip_ws(u, j)
            cod = _leer_codigo_zch_se(u, j)
            if cod:
                cands.add(_normalizar_codigo_zona(cod))
            i += 1
            continue
        i += 1


def _scan_entre_las_zonas_efgh(u: str, cands: set[str]) -> None:
    key = "ENTRE LAS ZONAS "
    pos = 0
    while True:
        j = u.find(key, pos)
        if j < 0:
            break
        k = j + len(key)
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] not in "ABCDEFGH":
            pos = j + 1
            continue
        lets: list[str] = [u[k]]
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] != ",":
            pos = j + 1
            continue
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] not in "ABCDEFGH":
            pos = j + 1
            continue
        lets.append(u[k])
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] != ",":
            pos = j + 1
            continue
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] not in "ABCDEFGH":
            pos = j + 1
            continue
        lets.append(u[k])
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] != "Y":
            pos = j + 1
            continue
        k += 1
        k = _skip_ws(u, k)
        if k >= len(u) or u[k] not in "ABCDEFGH":
            pos = j + 1
            continue
        lets.append(u[k])
        k += 1
        if k < len(u) and u[k].isalnum():
            pos = j + 1
            continue
        for L in lets:
            cands.add(_normalizar_codigo_zona(L))
        pos = j + 1


def _extraer_token_subzona_ventana(w: str, i: int) -> str | None:
    if i > 0 and w[i - 1].isalnum():
        return None
    k = i
    nlet = 0
    while k < len(w) and nlet < 3 and "A" <= w[k] <= "Z":
        nlet += 1
        k += 1
    if nlet < 1:
        return None
    nd = 0
    while k < len(w) and nd < 3 and w[k].isdigit():
        nd += 1
        k += 1
    if nd < 1:
        return None
    t = 0
    while k < len(w) and t < 3:
        c = w[k]
        if ("A" <= c <= "Z") or c.isdigit():
            t += 1
            k += 1
        else:
            break
    tok = w[i:k]
    if k < len(w) and w[k].isalnum():
        return None
    return tok


_RE_MD_ATX_HEADER = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def _titulo_md_atx_sin_marcado(linea: str) -> str:
    t = linea.strip()
    if t.startswith("**") and t.endswith("**") and len(t) > 4:
        t = t[2:-2].strip()
    return t


def _header_md_menciona_vias(titulo: str) -> bool:
    """True si el rótulo ATX (# … ######) contiene «vía(s)» (con o sin tilde)."""
    return bool(re.search(r"\bv[ií]as?\b", titulo, re.IGNORECASE))


def _eliminar_secciones_header_vias(contenido: str) -> tuple[str, int]:
    """
    Omite bloques bajo encabezados markdown (#–######) cuyo título incluye «vía(s)»
    (p. ej. listados de anchos de vías comunales / intercomunales).
    """
    if not (contenido or "").strip():
        return contenido, 0
    matches = list(_RE_MD_ATX_HEADER.finditer(contenido))
    if not matches:
        return contenido, 0
    omit: list[tuple[int, int]] = []
    n_vias = 0
    for i, m in enumerate(matches):
        titulo = _titulo_md_atx_sin_marcado(m.group(2))
        if not _header_md_menciona_vias(titulo):
            continue
        n_vias += 1
        start = m.start()
        level = len(m.group(1))
        end = len(contenido)
        for m2 in matches[i + 1 :]:
            if len(m2.group(1)) <= level:
                end = m2.start()
                break
        omit.append((start, end))
    if not omit:
        return contenido, 0
    out: list[str] = []
    pos = 0
    for a, b in omit:
        out.append(contenido[pos:a])
        pos = b
    out.append(contenido[pos:])
    return "".join(out), n_vias


def _preparar_contenido_descubrimiento(contenido: str) -> str:
    """Recorte previo a la extracción de candidatos (sin alterar evidencia PRC posterior)."""
    texto, n_vias = _eliminar_secciones_header_vias(contenido)
    if n_vias:
        console.print(
            f"  [dim]✂ {n_vias} sección(es) de listado de anchos de vías "
            f"(encabezado con «vía(s)») excluidas del descubrimiento[/dim]"
        )
    return texto


def _segmentar_prose_y_tablas(md: str) -> list[dict]:
    """Segmentos ordenados: kind 'prose'|'table', offsets en el markdown original."""
    lines = md.splitlines(keepends=True)
    segments: list[dict] = []
    offset = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            start = offset
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            block = "".join(lines[i:j])
            end = start + len(block)
            segments.append({"kind": "table", "start": start, "end": end, "text": block})
            offset = end
            i = j
            continue
        start = offset
        j = i
        while j < len(lines):
            st = lines[j].strip()
            if st.startswith("|") and st.count("|") >= 2:
                break
            j += 1
        block = "".join(lines[i:j])
        end = start + len(block)
        if block:
            segments.append({"kind": "prose", "start": start, "end": end, "text": block})
        offset = end
        i = j
    return segments


def _chunk_prose_segment_sized(
    text: str,
    gs: int,
    enc: tiktoken.Encoding,
    chunk_tokens: int,
    overlap_tokens: int,
) -> list[tuple[int, int, str]]:
    """Trozos solapados por tokens; *chunk_tokens* / *overlap_tokens* acotan el coste LLM."""
    if not text.strip():
        return []
    ids = enc.encode(text)
    if not ids:
        return []
    ct = max(256, int(chunk_tokens))
    ov = max(0, min(int(overlap_tokens), ct - 1))
    step = max(1, ct - ov)
    out: list[tuple[int, int, str]] = []
    pos = 0
    while pos < len(ids):
        end_tok = min(pos + ct, len(ids))
        ids_chunk = ids[pos:end_tok]
        chunk_text = enc.decode(ids_chunk)
        char_start = len(enc.decode(ids[:pos]))
        char_end = char_start + len(chunk_text)
        out.append((gs + char_start, gs + char_end, chunk_text))
        if end_tok >= len(ids):
            break
        pos += step
    return out


def _chunk_prose_segment(text: str, gs: int, enc: tiktoken.Encoding) -> list[tuple[int, int, str]]:
    """Trozos solapados por tokens sobre un bloque de prosa; offsets globales gs+."""
    return _chunk_prose_segment_sized(
        text, gs, enc, CHUNK_TOKENS, CHUNK_OVERLAP_TOKENS,
    )


def _es_linea_separador_tabla_md(line: str) -> bool:
    s = line.strip()
    if not s.startswith("|"):
        return False
    return "---" in s


def _chunk_markdown_table_por_filas(
    text: str,
    gs: int,
    enc: tiktoken.Encoding,
    max_tokens: int,
) -> list[tuple[int, int, str]]:
    """
    Trocea una tabla markdown por filas sin superar max_tokens (tiktoken).
    Cada trozo repite cabecera (+ línea separadora si existe) para columnas legibles.
    Los offsets (g0, g1) cubren las filas de cuerpo incluidas en el trozo (sin duplicar cabecera).
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return []
    st0 = lines[0].lstrip()
    if not (st0.startswith("|") and lines[0].count("|") >= 2):
        return _chunk_prose_segment_sized(text, gs, enc, max_tokens, 0)

    line_starts: list[int] = []
    pos = 0
    for ln in lines:
        line_starts.append(pos)
        pos += len(ln)

    if len(lines) >= 2 and _es_linea_separador_tabla_md(lines[1]):
        header_block = lines[0:2]
        body_start = 2
    else:
        header_block = lines[0:1]
        body_start = 1

    prefix = "".join(header_block)
    prefix_tok = len(enc.encode(prefix))
    # Tope efectivo (sin imponer 256 como en prosa: aquí debe respetarse TABLE_CHUNK_TOKENS).
    max_tok = max(64, int(max_tokens))
    if prefix_tok >= max_tok:
        return _chunk_prose_segment_sized(text, gs, enc, max_tok, 0)

    body_lines = lines[body_start:]
    if not body_lines:
        return [(gs, gs + len(text), prefix)]

    max_budget = max_tok - prefix_tok
    out: list[tuple[int, int, str]] = []
    buf: list[tuple[int, str]] = []
    buf_tok = 0

    def flush() -> None:
        nonlocal buf, buf_tok
        if not buf:
            return
        chunk_text = prefix + "".join(ln for _, ln in buf)
        fi = buf[0][0]
        li = buf[-1][0]
        first_line = body_start + fi
        last_line = body_start + li
        g0 = gs + line_starts[first_line]
        g1 = gs + line_starts[last_line] + len(lines[last_line])
        out.append((g0, g1, chunk_text))
        buf.clear()
        buf_tok = 0

    for bi, row in enumerate(body_lines):
        row_tok = len(enc.encode(row))
        if row_tok > max_budget:
            flush()
            row_gs = gs + line_starts[body_start + bi]
            big = prefix + row
            out.extend(_chunk_prose_segment_sized(big, row_gs, enc, max_tok, 0))
            continue
        if buf and buf_tok + row_tok > max_budget:
            flush()
        buf.append((bi, row))
        buf_tok += row_tok
    flush()
    return out if out else [(gs, gs + len(text), prefix)]


def _construir_corpus_chunks(contenido: str) -> tuple[list[str], list[dict]]:
    """Documentos de recuperación: chunks de prosa (tokens + solape) + tablas troceadas por filas."""
    segs = _segmentar_prose_y_tablas(contenido)
    enc = _get_enc()
    docs: list[str] = []
    meta: list[dict] = []
    for seg in segs:
        if seg["kind"] == "prose":
            for g0, g1, txt in _chunk_prose_segment(seg["text"], seg["start"], enc):
                docs.append(txt)
                meta.append({"kind": "prose", "start": g0, "end": g1})
        else:
            for g0, g1, txt in _chunk_markdown_table_por_filas(
                seg["text"], seg["start"], enc, TABLE_CHUNK_TOKENS,
            ):
                docs.append(txt)
                meta.append({"kind": "table", "start": g0, "end": g1})
    return docs, meta


def _extraer_candidatos_desde_texto_hits(blob: str) -> set[str]:
    """
    Extrae códigos sobre *blob* (fragmentos recuperados y/o documento completo).
    «ZONA DE USOS», «ZONA DEL …» no deben capturar «DE» como código.
    """
    from utils import regex as _rx

    cands: set[str] = set()
    u = _rx.unificar_guiones_do(blob.upper())
    _scan_zona_codigos(u, cands)
    _scan_codigos_zona_catalogo_md(u, cands)
    _scan_codigos_zona_guion(u, cands)
    _scan_codigos_ur_guion(u, cands)
    _scan_codigos_m_guion(u, cands)
    _scan_sectors_conserv_especial(u, cands)
    _scan_subsectores_prc(u, cands)
    _scan_sectores_especiales_pareja(u, cands)
    _scan_zch_y_se(u, cands)
    _scan_entre_las_zonas_efgh(u, cands)
    return {c for c in cands if c}


def _candidatos_subzonas_con_digito_ventanas(texto: str) -> set[str]:
    """
    Recupera códigos tipo A1, B12 cuando el OCR rompe el encabezado «ZONA …».
    Solo tokens con al menos un dígito (evita DE, EN, SE, HA).
    """
    from utils import regex as _rx

    u = _rx.unificar_guiones_do(texto.upper())
    win = 100
    step = max(14, win // 4)
    cands: set[str] = set()
    for i in range(0, max(1, len(u) - win), step):
        w = u[i : i + win]
        p = 0
        while p < len(w):
            tok = _extraer_token_subzona_ventana(w, p)
            if tok:
                z0 = _normalizar_codigo_zona(tok)
                if re.fullmatch(r"PS\d{1,2}", z0):
                    p += 1
                    continue
                if _es_codigo_zona_token(z0) and _tiene_digito(z0):
                    cands.add(z0)
                p += len(tok)
            else:
                p += 1
    return cands


def _extraer_zonas_crudas_desde_corpus(corpus: str) -> list[str]:
    """Candidatos normalizados (sin filtros de evidencia) desde el texto preparado."""
    cands: set[str] = set()
    cands |= _extraer_candidatos_desde_texto_hits(corpus)
    cands |= _candidatos_subzonas_con_digito_ventanas(corpus)
    zonas: list[str] = []
    seen: set[str] = set()
    for raw in sorted(cands):
        nz = _normalizar_zona(raw)
        if not nz or nz in seen:
            continue
        if not _codigo_zona_tiene_letra(nz):
            continue
        if not _es_codigo_zona_token(nz):
            continue
        seen.add(nz)
        zonas.append(nz)
    return zonas


def _chunk_menciona_alguna_zona(chunk_text: str, zonas: list[str]) -> bool:
    from utils import regex as _rx

    for z in zonas:
        if _rx.codigo_zona_en_mayusculas_en_texto(chunk_text or "", z):
            return True
    return False


def _indices_corpus_para_llm(
    meta: list[dict],
    docs: list[str],
    zonas: list[str],
) -> frozenset[int]:
    """Tablas siempre ∪ trozos de prosa que mencionan alguna zona del catálogo."""
    out: set[int] = {i for i, m in enumerate(meta) if m.get("kind") == "table"}
    if zonas:
        for i, txt in enumerate(docs):
            if i in out:
                continue
            if _chunk_menciona_alguna_zona(txt, zonas):
                out.add(i)
    return frozenset(out)


def _chunk_hash(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8", errors="replace")).hexdigest()[:12]


def _descubrir_zonas_interno(
    contenido: str,
    *,
    incluir_corpus: bool = False,
) -> tuple[list[str], frozenset[int]] | tuple[list[str], frozenset[int], list[str], list[dict]]:
    corpus = _preparar_contenido_descubrimiento(contenido)
    raw = _extraer_zonas_crudas_desde_corpus(corpus)
    if not incluir_corpus:
        return raw, frozenset()
    docs, meta = _construir_corpus_chunks(corpus)
    idx = _indices_corpus_para_llm(meta, docs, raw)
    return raw, idx, docs, meta


# ponytail: alias legado; quitar cuando no queden referencias externas
_descubrir_zonas_coseno_interno = _descubrir_zonas_interno


# ═══════════════════════════════════════════════════════════════════════════
# PASO 1: DESCUBRIMIENTO
# ═══════════════════════════════════════════════════════════════════════════

def _filtrar_zonas_sospechosas(zonas: list[str]) -> list[str]:
    """
    Elimina códigos que parecen IDs de parcela o lote (p.ej. SM1-SM997),
    no códigos de zona normativa.

    Criterio: si un mismo prefijo de 2+ letras agrupa más de 20 zonas
    consecutivas (patrón XY1, XY2, …, XY997), son identificadores seccionales.
    Códigos de zona real típicos: A, B1, R1, ZH, C3 — máximo 1-2 letras + 1-2 dígitos.

    No recorta por MAX_ZONAS; el tope se eliminó para no perder zonas válidas.
    """
    from collections import Counter

    prefijo_count: Counter = Counter()
    for z in zonas:
        pfx = _prefijo_2mas_letras_dig(z)
        if pfx:
            prefijo_count[pfx] += 1

    prefijos_id = {p for p, cnt in prefijo_count.items() if cnt > 20}
    if not prefijos_id:
        return zonas

    filtradas = [
        z for z in zonas
        if not (
            (pfx := _prefijo_2mas_letras_dig(z)) is not None and pfx in prefijos_id
        )
    ]
    n_desc = len(zonas) - len(filtradas)
    if n_desc:
        console.print(
            f"[yellow]  ⚠ {n_desc} identificador(es) de parcela descartado(s) "
            f"(prefijos: {', '.join(sorted(prefijos_id))})[/yellow]"
        )
    return filtradas if filtradas else zonas


_RE_LINEA_TABLA_FICHA_ADMIN = re.compile(
    r"(?i)(?:correo\s*electr[oó]nico|participantes|asistentes|registro\s+de\s+asistencia|"
    r"instituci[oó]n|tel[eé]fono|\bfirma\b|\[Firma\]|@|\.com\b|\.cl\b)"
)


def _linea_tabla_parece_ficha_admin(line: str) -> bool:
    """True si la fila de tabla parece registro administrativo (asistencia, contacto, etc.)."""
    return bool(_RE_LINEA_TABLA_FICHA_ADMIN.search(line or ""))


def _evidencia_codigo_en_celda_tabla_normativa(contenido: str, u: str) -> bool:
    """
    Celda | código | en tabla normativa PRC (no fichas de asistencia ni códigos institucionales).
    """
    if not _estructura_codigo_prc_plausible(u):
        return False
    for m in re.finditer(rf"(?m)(?<=\|)\s*{re.escape(u)}\s*(?=\|)", contenido):
        ls = contenido.rfind("\n", 0, m.start()) + 1
        le = contenido.find("\n", m.end())
        line = contenido[ls : le if le >= 0 else len(contenido)]
        if _linea_tabla_parece_ficha_admin(line):
            continue
        return True
    return False


def _frag_codigo_zona_en_fuente_do(u: str) -> str:
    """
    Variantes típicas DO/PRC: «Z-1», «Z 1», «Z1»; «Z-2 Tramo A» ↔ Z2A (subzona por tramo).
    """
    z = u.strip().upper()
    m3 = re.fullmatch(r"([A-Z]+)(\d+)([A-Z])", z)
    if m3:
        L, digs, suf = m3.group(1), m3.group(2), m3.group(3)
        hyp = rf"{re.escape(L)}-{re.escape(digs)}"
        hyp_sp = rf"{re.escape(L)}\s*-\s*{re.escape(digs)}"
        sp = rf"{re.escape(L)}\s+{re.escape(digs)}"
        cmpct = rf"{re.escape(L)}{re.escape(digs)}"
        return (
            rf"(?:{hyp}\s+TRAMO\s+{re.escape(suf)}|"
            rf"{sp}\s+TRAMO\s+{re.escape(suf)}|"
            rf"{hyp}{re.escape(suf)}|"
            rf"{cmpct}{re.escape(suf)}|"
            rf"{hyp_sp}\s*{re.escape(suf)}|"
            rf"{hyp_sp}{re.escape(suf)}|"
            rf"{re.escape(z)})"
        )
    m = re.fullmatch(r"([A-Z]+)(\d+)", z)
    if m:
        letras, digs = m.group(1), m.group(2)
        hyp = rf"{re.escape(letras)}-{re.escape(digs)}"
        hyp_sp = rf"{re.escape(letras)}\s*-\s*{re.escape(digs)}"
        sp = rf"{re.escape(letras)}\s+{re.escape(digs)}"
        return rf"(?:{hyp_sp}|{hyp}|{sp}|{re.escape(z)})"
    m2 = re.fullmatch(r"([A-Z])([A-Z])", z)
    if m2:
        a, b = m2.group(1), m2.group(2)
        hyp = rf"{re.escape(a)}-{re.escape(b)}"
        sp = rf"{re.escape(a)}\s+-\s+{re.escape(b)}"
        return rf"(?:{hyp}|{sp}|{re.escape(z)})"
    return re.escape(z)


def _frag_codigo_zona_estricto(u: str) -> str:
    """Variantes seguras para buscar códigos sueltos, sin aceptar «a 1» como A1."""
    from utils import regex as _rx

    z = _rx.unificar_guiones_do(u.strip().upper())
    g = r"[-–—‑]"
    gs = rf"\s*{g}\s*"
    m_subz = re.fullmatch(r"Z(\d+)-(\d+)$", z)
    if m_subz:
        d1, d2 = m_subz.group(1), m_subz.group(2)
        hyp = rf"Z{g}{d1}{g}{d2}"
        hyp_sp = rf"Z{gs}{d1}{gs}{d2}"
        mid = rf"Z{d1}{g}{d2}"
        return rf"(?:{hyp_sp}|{hyp}|{mid}|{re.escape(z)})"
    m_z_suf = re.fullmatch(r"(Z[A-Z]{2,7})-([A-Z])$", z)
    if m_z_suf:
        base, suf = m_z_suf.group(1), m_z_suf.group(2)
        hyp = rf"{re.escape(base)}{g}{re.escape(suf)}"
        hyp_sp = rf"{re.escape(base)}{gs}{re.escape(suf)}"
        sp = rf"{re.escape(base)}\s+{re.escape(suf)}"
        return rf"(?:{hyp_sp}|{hyp}|{sp}|{re.escape(z)})"
    m_ld = re.fullmatch(r"([A-Z]+\d+[A-Z])(\d+)$", z)
    if m_ld:
        base, sub = m_ld.group(1), m_ld.group(2)
        hyp = rf"{re.escape(base)}{g}{re.escape(sub)}"
        hyp_sp = rf"{re.escape(base)}{gs}{re.escape(sub)}"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    m3 = re.fullmatch(r"([A-Z]+)(\d+)([A-Z])", z)
    if m3:
        letras, digs, suf = m3.group(1), m3.group(2), m3.group(3)
        hyp_sp = rf"{re.escape(letras)}\s*-\s*{re.escape(digs)}\s*{re.escape(suf)}"
        hyp = rf"{re.escape(letras)}-{re.escape(digs)}{re.escape(suf)}"
        compact = re.escape(z)
        tramo_hyp = rf"{re.escape(letras)}-{re.escape(digs)}\s+TRAMO\s+{re.escape(suf)}"
        return rf"(?:{tramo_hyp}|{hyp_sp}|{hyp}|{compact})"
    m2 = re.fullmatch(r"([A-Z])(\d{2,})$", z)
    if m2:
        letra, digs = m2.group(1), m2.group(2)
        hyp = rf"{re.escape(letra)}-{re.escape(digs)}"
        hyp_sp = rf"{re.escape(letra)}\s*-\s*{re.escape(digs)}"
        if letra == "M" and len(digs) == 2:
            hyp_sep = rf"M-{digs[0]}-{digs[1]}"
            return rf"(?:{hyp_sep}|{hyp_sp}|{hyp}|{re.escape(z)})"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    m = re.fullmatch(r"([A-Z]+)(\d+)", z)
    if m:
        letras, digs = m.group(1), m.group(2)
        hyp_sp = rf"{re.escape(letras)}\s*-\s*{re.escape(digs)}"
        hyp = rf"{re.escape(letras)}-{re.escape(digs)}"
        compact = re.escape(z)
        return rf"(?:{hyp_sp}|{hyp}|{compact})"
    m2 = re.fullmatch(r"([A-Z])([A-Z])", z)
    if m2:
        a, b = m2.group(1), m2.group(2)
        hyp = rf"{re.escape(a)}-{re.escape(b)}"
        return rf"(?:{hyp}|{re.escape(z)})"
    return re.escape(z)


def _evidencia_codigo_como_zona_prc_explicita(contenido: str, u: str) -> bool:
    """
    Evidencia fuerte: «ZONA …», Sector, celda de tabla o ítem de catálogo normativo.
    No usa apariciones sueltas en prosa administrativa del DO.
    """
    from utils import regex as _rx

    frag = _rx.regex_fragmento_zona_en_fuente(u)
    fcs = _rx.frag_codigo_zona_case_sensitive(frag)
    if u.startswith("CUS") and u[3:].isdigit():
        return False
    if re.fullmatch(r"CU\d{1,2}", u):
        return False
    if _es_codigo_numeral_romano_no_zona(u):
        return False
    if re.search(rf"(?i)(?<![A-Za-z])ZONA\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?i)(?<![A-Za-z])ZONAS\s+{fcs}\b", contenido):
        return True
    if re.search(
        rf"(?i)\bZona\s+de\s+Conservaci[oó]n\s+Hist[oó]rica\s+{fcs}\b",
        contenido,
    ):
        return True
    if re.search(
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
        contenido,
    ):
        return True
    if re.search(rf"(?i)sectores?\s+especiales?\s+{fcs}\b", contenido):
        return True
    if re.search(
        rf"(?i)(?:sub[\s-]*sectores?|sub[\s-]*sector|subsector)\s+{fcs}\b",
        contenido,
    ):
        return True
    if re.search(rf"(?i)(?<![A-Za-z])ZCH\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?i)(?<![A-Za-z])SE\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?m)^\s*-\s*\*\*{re.escape(u)}\*\*\s*$", contenido):
        return True
    if re.search(
        rf"(?m)^#{{1,6}}\s*(?:\*\*)?\s*{re.escape(u)}\b",
        contenido,
        re.IGNORECASE,
    ):
        return True
    if _evidencia_codigo_en_celda_tabla_normativa(contenido, u):
        return True
    frag = _frag_codigo_zona_estricto(u)
    for m in re.finditer(
        rf"(?m)^\s*-\s*(?:(?:Sub[\s-]*zonas?|Subzona)\s+)?{frag}\b",
        contenido,
        re.IGNORECASE,
    ):
        ls = contenido.rfind("\n", 0, m.start()) + 1
        le = contenido.find("\n", m.end())
        line = contenido[ls : le if le >= 0 else len(contenido)]
        if re.search(r"(?i)monumento\s+hist[oó]ric|monumentos\s+hist[oó]ric", line):
            continue
        return True
    return False


def _evidencia_codigo_como_zona_prc(contenido: str, u: str) -> bool:
    """
    True si el texto trata el código como zona/sector del PRC (encabezado «ZONA …», etc.).
    No cuenta el sufijo …-Cx de identificadores de plano PRMS (codificación de tramos viales).
    """
    from utils import regex as _rx

    if _evidencia_codigo_como_zona_prc_explicita(contenido, u):
        return True
    # Lista / encabezado / norma «Z-1», «#### Z-2», «ZE—3» (sin «ZONA» delante).
    # No aplicar a códigos de una sola letra (evita «S» espurio en texto en mayúsculas).
    if not re.fullmatch(r"[A-Z]", u):
        frag_estricto = _frag_codigo_zona_estricto(u)
        for m in re.finditer(
            rf"(?<![A-Za-z0-9]){frag_estricto}(?![A-Za-z0-9])",
            contenido,
        ):
            if _rx._match_es_unidad_superficie_m2(contenido, m):
                continue
            if _rx._match_es_numeral_o_estructura_no_zona(contenido, m):
                continue
            if _rx._match_es_referencia_administrativa_no_zona(contenido, m):
                continue
            if _rx._match_es_sufijo_modificacion_prms(contenido, m):
                continue
            if _rx._match_es_sufijo_plano_ps(contenido, m):
                continue
            if not _rx._match_es_sufijo_identificador_plano_prs(contenido, m):
                return True
    return False


def _filtrar_letra_mas_digito_sin_evidencia_prc(contenido: str, zonas: list[str]) -> list[str]:
    """
    Letra + 1–3 dígitos (p. ej. A1, H7): sin «Zona …» / celda PRC suele ser ruido
    (vías «2-A1», PRMS, etc.). No aplica a códigos solo letras ni a H01 (filtro aparte).
    """
    if not contenido.strip():
        return zonas
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if re.fullmatch(r"[A-Z]\d{1,3}", z) and not (
            _evidencia_codigo_como_zona_prc_explicita(contenido, z)
            or (
                _estructura_codigo_prc_plausible(z)
                and _evidencia_codigo_como_zona_prc(contenido, z)
            )
            or (
                re.fullmatch(r"M\d{1,3}", z, re.I)
                and _codigo_m_es_zona_prc(contenido, z)
            )
        ):
            drop.append(z)
            continue
        out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) letra+dígitos (p. ej. B69, C1) descartado(s): "
            f"{_GLOSA_EVIDENCIA_ZONA}: {', '.join(drop)}[/yellow]"
        )
    return out


def _codigo_m_es_zona_prc(contenido: str, z: str) -> bool:
    """True si M* aparece como zona del PRC (no solo código de monumento en tabla)."""
    u = _normalizar_zona(z)
    if not re.fullmatch(r"M\d{1,3}", u):
        return False
    frag = _frag_codigo_zona_estricto(u)
    if re.search(rf"(?i)(?<![A-Za-z])ZONA\s+{frag}\b", contenido):
        return True
    if re.search(
        rf"(?m)^\s*-\s*(?:(?:Sub[\s-]*zonas?|Subzona)\s+)?{frag}\b",
        contenido,
        re.IGNORECASE,
    ):
        return True
    if re.search(rf"(?m)^#{{1,6}}\s*(?:\*\*)?\s*{frag}\b", contenido, re.IGNORECASE):
        return True
    if re.search(rf"(?i)\*\*{frag}\b", contenido):
        return True
    from utils import regex as _rx

    for m in re.finditer(
        rf"(?<![A-Za-z0-9]){frag}(?![A-Za-z0-9])",
        contenido,
    ):
        if _rx._match_es_unidad_superficie_m2(contenido, m):
            continue
        if _rx._match_es_numeral_o_estructura_no_zona(contenido, m):
            continue
        if _rx._match_es_referencia_administrativa_no_zona(contenido, m):
            continue
        return True
    return False


def _filtrar_codigos_monumento_nacional(contenido: str, zonas: list[str]) -> list[str]:
    """M1… en tablas de Monumentos Nacionales no son zonas del PRCT."""
    if not contenido.strip():
        return zonas
    from utils import regex as _rx

    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if not re.fullmatch(r"M\d{1,2}", z, re.I):
            out.append(z)
            continue
        if _codigo_m_es_zona_prc(contenido, z):
            out.append(z)
            continue
        nz = _normalizar_zona(z)
        solo_monumento = True
        for start, _end in _rx.iter_spans_evidencia_codigo_zona(
            contenido, nz, max_spans=40
        ):
            bloque = _rx.bloque_contexto_para_posicion(contenido, start) or ""
            if re.search(r"(?i)monumentos?\s+nacionales?", bloque):
                continue
            if re.search(r"(?i)<b>COD\.</b>|\bCOD\.\b", bloque) and re.search(
                r"(?i)denominaci[oó]n", bloque
            ):
                continue
            solo_monumento = False
            break
        if solo_monumento:
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) M* descartado(s) "
            f"(tabla Monumentos Nacionales, no zonas): {', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_monumento_historico(zonas: list[str]) -> list[str]:
    """MH* = registro de Monumentos Históricos en planos/leyendas, no zonas del PRC."""
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if re.fullmatch(r"MH\d{1,3}", _normalizar_zona(z)):
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) MH* descartado(s) "
            f"(Monumentos Históricos, no zonas): {', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_estructura_no_prc(zonas: list[str]) -> list[str]:
    """Descarta códigos cuya forma no corresponde a zona PRC (p. ej. FA39361 en ficha admin)."""
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if _estructura_codigo_prc_plausible(z):
            out.append(z)
        else:
            drop.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s): "
            f"{_GLOSA_FORMA_ZONA}: "
            f"{', '.join(drop[:12])}{'…' if len(drop) > 12 else ''}[/yellow]"
        )
    return out


def _filtrar_zonas_sin_evidencia_mayusculas_prc(
    contenido: str, zonas: list[str],
) -> list[str]:
    """
    Conserva zonas con código en MAYÚSCULAS y evidencia PRC en el documento
    (sin exigir keyword normativa del CSV).
    """
    if not contenido.strip():
        return zonas
    from utils import regex as _rx

    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if not _rx.codigo_zona_en_mayusculas_en_texto(contenido, z):
            drop.append(z)
            continue
        if (
            _evidencia_codigo_como_zona_prc(contenido, z)
            or _rx.documento_evidencia_prosa_normativa(contenido, z)
            or (len(z) == 1 and _rx.documento_evidencia_codigo_zona(contenido, z))
        ):
            out.append(z)
        else:
            drop.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s): "
            f"no aparece en MAYÚSCULAS en el DO o {_GLOSA_EVIDENCIA_ZONA}: "
            f"{', '.join(drop[:12])}{'…' if len(drop) > 12 else ''}[/yellow]"
        )
    return out


def _filtrar_letra_mas_dd_sin_evidencia_prc(contenido: str, zonas: list[str]) -> list[str]:
    """
    Una letra + exactamente 2 dígitos (p. ej. H01, D49): coincide con planos DGAC «PP-97-H01»,
    hashes en rutas de imagen («…ced49…»), «Ord. Nº 49», etc. Sin «Zona/Zonas …» / celda | … |
    es ruido, no zona PRC. No aplica a Z1, A1, Z12 (longitud o forma distinta).
    """
    if not contenido.strip():
        return zonas
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if not re.fullmatch(r"[A-Z]\d{2}", z):
            out.append(z)
            continue
        if _evidencia_codigo_como_zona_prc(contenido, z):
            out.append(z)
            continue
        drop.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) letra+2 dígitos (p. ej. D45, H01) descartado(s): "
            f"{_GLOSA_EVIDENCIA_ZONA}: {', '.join(drop)}[/yellow]"
        )
    return out


def _es_solo_sufijo_identificador_prms(contenido: str, nz: str) -> bool:
    """
    Códigos tipo A1…H99 collisionan con letras de codificación vial en tablas PRMS.
    Si solo aparecen como sufijo «RM-PRMS-…-Cx» / «PRMS-…-Cx» y no como ZONA Cx, descartar.
    """
    from utils import regex as _rx

    u = _normalizar_zona(nz)
    if not re.fullmatch(r"[A-H]\d{1,3}", u):
        return False
    if not _rx.codigo_aparece_como_sufijo_modificacion_prms(contenido, u):
        return False
    if _evidencia_codigo_como_zona_prc(contenido, u):
        return False
    return True


def _filtrar_codigos_solo_tramo_prms(contenido: str, zonas: list[str]) -> list[str]:
    if not contenido.strip():
        return zonas
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if _es_solo_sufijo_identificador_prms(contenido, z):
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s) "
            f"(solo sufijo PRMS/plano vial, sin «ZONA …» en el texto): "
            f"{', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_prefijo_prs(zonas: list[str]) -> list[str]:
    """PRS0, PRS03… son identificadores de plano, no zonas PRC."""
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if _normalizar_zona(z).startswith("PRS"):
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s) "
            f"(prefijo PRS-/plano cartográfico): {', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_identificador_plano_no_zona(
    contenido: str, zonas: list[str],
) -> list[str]:
    """PRM99 (lámina PRM), C17O/T57O (vial PRMS), H01 (plano DGAC PP-97-…)."""
    if not contenido.strip():
        return zonas
    from utils import regex as _rx

    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if (
            _rx.codigo_es_identificador_plano_prm(contenido, z)
            or _rx.codigo_es_codigo_vial_tabla_prms(contenido, z)
            or             _rx.codigo_es_solo_plano_dgac_pp(contenido, z)
            or _rx.codigo_es_sufijo_plano_ps(contenido, z)
            or (
                _rx.codigo_aparece_como_sufijo_modificacion_prms(contenido, z)
                and not _evidencia_codigo_como_zona_prc(contenido, z)
            )
        ):
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s) "
            f"(plano PRM/DGAC/PS, vialidad PRMS o sufijo RM-PRMS-NN-Cx, no zona PRC): "
            f"{', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_solo_sufijo_plano_prs(contenido: str, zonas: list[str]) -> list[str]:
    """Descarta sufijos de láminas «PRS-…» (p. ej. O1A en «Plano PRS-O1A») que no son zonas PRC."""
    if not contenido.strip():
        return zonas
    from utils import regex as _rx

    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if _rx.codigo_es_solo_sufijo_plano_prs(contenido, z):
            drop.append(z)
        else:
            out.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s) "
            f"(solo sufijo PRS-/plano cartográfico, no zona PRC): "
            f"{', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigos_sin_letra(zonas: list[str]) -> list[str]:
    """Descarta numerales puros (1, 2, 3…) detectados por error en listas o tablas."""
    out: list[str] = []
    drop: list[str] = []
    for z in zonas:
        if _codigo_zona_tiene_letra(z):
            out.append(z)
        else:
            drop.append(z)
    if drop:
        console.print(
            f"[yellow]  ⚠ {len(drop)} código(s) descartado(s) "
            f"(solo dígitos, no zonas PRC): {', '.join(drop)}[/yellow]"
        )
    return out


def _filtrar_codigo_truncado_ante_subzona(zonas: list[str]) -> list[str]:
    """
    Si hay ZCHAL-V / ZCHAL-B, el prefijo ZCHAL suelto suele ser truncamiento del guión
    tipográfico (p. ej. «ZCHAL–V» leído como ZCHAL).
    Si hay Z11B1 / Z11B2, descarta Z11B (padre sustituido por subzonas numeradas).
    """
    s = set(zonas)
    drop: set[str] = set()
    subz = {z for z in zonas if re.fullmatch(r"Z[A-Z]{2,7}-[A-Z]", z)}
    if subz:
        drop |= {z.rsplit("-", 1)[0] for z in subz} - subz
    for p in zonas:
        # Solo Z11B→Z11B1 (letras+dígitos+letra final). No A→A1 ni B→B10 (Santiago).
        if not re.fullmatch(r"[A-Z]+\d+[A-Z]", p):
            continue
        if any(z != p and z.startswith(p) and z[len(p) :].isdigit() for z in s):
            drop.add(p)
    if not drop:
        return zonas
    out = [z for z in zonas if z not in drop]
    console.print(
        f"[yellow]  ⚠ {len(drop)} código(s) prefijo truncado(s) descartado(s) "
        f"(subzona presente): {', '.join(sorted(drop))}[/yellow]"
    )
    return out


def _refinar_zonas_descubiertas(
    zonas: list[str],
    contenido: str = "",
    *,
    es_modificacion: bool = False,
) -> list[str]:
    """Normaliza, deduplica y filtra la lista cruda de códigos del paso de descubrimiento."""
    zonas_unificadas: list[str] = []
    seen_n: set[str] = set()
    for z in zonas:
        nz = _normalizar_zona(z)
        if nz and nz not in seen_n:
            seen_n.add(nz)
            zonas_unificadas.append(nz)
    zonas = zonas_unificadas

    zonas = _filtrar_zonas_sospechosas(zonas)

    def _es_codigo_valido(z: str) -> bool:
        if not _codigo_zona_tiene_letra(z):
            return False
        if len(z) == 2 and z in _CODIGOS_LEXICOS_SPURIOUS:
            return False
        if len(z) == 2 and z == "M2" and not _es_codigo_zona_prefijo_m(z):
            return False
        if _es_codigo_zona_prefijo_z(z):
            return True
        if _es_codigo_zona_prefijo_u_r(z):
            return True
        if _es_codigo_zona_prefijo_v(z):
            return True
        if _es_codigo_zona_prefijo_m(z):
            return True
        if re.fullmatch(r"Z[A-Z]{2,7}-[A-Z]", _normalizar_zona(z)):
            return True
        if len(z) == 1:
            return z in _LETRAS_ZONA_MACRO_UNA
        if len(z) == 2 and z.isalpha():
            return z not in _CODIGOS_LEXICOS_SPURIOUS
        if _RE_CODIGO_JERARQUICO_COLAPSADO.fullmatch(z):
            return True
        if len(z) in (3, 4) and not _tiene_digito(z):
            return z.isalpha() and z not in _CODIGOS_LEXICOS_SPURIOUS
        if len(z) <= 3:
            return True
        if _tiene_digito(z):
            return True
        return False

    # Ítems i), j)… en listas; I queda fuera porque es zona PRC (p. ej. Valparaíso).
    _LETRAS_MARCADORES_LISTA = frozenset("JKLMNÑOPQ")

    def _es_marcador_lista(z: str) -> bool:
        return len(z) == 1 and z.upper() in _LETRAS_MARCADORES_LISTA

    def _zona_pasa_filtro_post_descubrimiento(z: str) -> bool:
        u = _normalizar_zona(z)
        if not _codigo_zona_tiene_letra(u):
            return False
        if u.startswith("PRS"):
            return False
        if not _es_codigo_valido(z):
            return False
        if _es_marcador_lista(z):
            return False
        if len(z) == 1:
            from utils import regex as _rx

            return _rx.documento_evidencia_codigo_zona(contenido, z)
        if _evidencia_codigo_como_zona_prc_explicita(contenido, z):
            return True
        if not _estructura_codigo_prc_plausible(z):
            return False
        if re.fullmatch(r"M\d{1,3}", u, re.I):
            return _codigo_m_es_zona_prc(contenido, z)
        if _evidencia_codigo_como_zona_prc(contenido, z):
            return True
        return True

    antes = len(zonas)
    zonas = [z for z in zonas if _zona_pasa_filtro_post_descubrimiento(z)]
    if len(zonas) < antes:
        console.print(
            f"[yellow]  ⚠ {antes - len(zonas)} candidato(s) descartado(s) tras descubrimiento: "
            f"palabra común, numeral de lista o forma ajena a zonificación[/yellow]"
        )
    zonas = _filtrar_codigos_solo_tramo_prms(contenido, zonas)
    zonas = _filtrar_codigos_prefijo_prs(zonas)
    zonas = _filtrar_codigos_solo_sufijo_plano_prs(contenido, zonas)
    zonas = _filtrar_codigos_identificador_plano_no_zona(contenido, zonas)
    zonas = _filtrar_letra_mas_digito_sin_evidencia_prc(contenido, zonas)
    zonas = _filtrar_letra_mas_dd_sin_evidencia_prc(contenido, zonas)
    zonas = _filtrar_codigos_sin_letra(zonas)
    zonas = _filtrar_codigos_monumento_nacional(contenido, zonas)
    zonas = _filtrar_codigos_monumento_historico(zonas)
    zonas = _filtrar_codigos_estructura_no_prc(zonas)
    zonas = _filtrar_zonas_sin_evidencia_mayusculas_prc(contenido, zonas)
    zonas = _filtrar_codigo_truncado_ante_subzona(zonas)
    return zonas


_refinar_zonas_post_coseno = _refinar_zonas_descubiertas


def descubrir_zonas(
    contenido: str,
    es_modificacion: bool = False,
) -> list[str]:
    """
    Paso 1: lista de zonas/subzonas vía regex sobre el documento (sin LLM).
    """
    console.print(
        "  [dim]Descubrimiento: regex + filtros de evidencia — sin LLM.[/dim]"
    )
    raw, _chunk_idx = _descubrir_zonas_interno(contenido)
    zonas = _refinar_zonas_descubiertas(raw, contenido, es_modificacion=es_modificacion)
    console.print(f"[cyan]Paso 1 — {len(zonas)} zonas: {', '.join(zonas)}[/cyan]")
    return zonas


def _chunk_contiene_zona(
    chunk_text: str,
    zona: str,
    *,
    contenido: str = "",
    chunk_global_start: int | None = None,
) -> bool:
    """True si el chunk menciona el código de zona en MAYÚSCULAS."""
    from utils import regex as _rx

    texto = chunk_text or contenido
    return _rx.codigo_zona_en_mayusculas_en_texto(texto, zona)


def _construir_evidencia_chunks_zonas(
    zonas: list[str],
    docs: list[str],
    meta: list[dict],
    indices_relevantes: frozenset[int],
    *,
    contenido: str = "",
) -> tuple[list[dict], dict[str, list[str]]]:
    chunks: list[dict] = []
    zona_chunks: dict[str, list[str]] = {z: [] for z in zonas}

    for idx, texto in enumerate(docs):
        info = dict(meta[idx]) if idx < len(meta) else {}
        gstart = info.get("start")
        zonas_en_chunk = [
            z
            for z in zonas
            if _chunk_contiene_zona(
                texto,
                z,
                contenido=contenido,
                chunk_global_start=gstart if gstart is not None else None,
            )
        ]
        if not zonas_en_chunk:
            continue
        h = _chunk_hash(texto)
        chunk = {
            "idx": idx,
            "hash": h,
            "kind": info.get("kind", ""),
            "start": info.get("start"),
            "end": info.get("end"),
            "chars": len(texto),
            "recuperado_zone_extractor": idx in indices_relevantes,
            "seleccionado_para_llm": idx in indices_relevantes,
            "zonas": zonas_en_chunk,
            "texto": texto,
        }
        chunks.append(chunk)
        for z in zonas_en_chunk:
            zona_chunks.setdefault(z, []).append(h)

    return chunks, zona_chunks


def descubrir_zonas_con_evidencia(
    contenido: str,
    es_modificacion: bool = False,
) -> dict:
    """
    Variante trazable de `descubrir_zonas`.

    Devuelve:
    - zonas: lista final refinada.
    - chunks: chunks internos del zone_extractor donde aparecen esas zonas, con hash.
    - zona_chunks: zona -> hashes de chunks.
    - indices_relevantes: tablas + trozos con zonas del catálogo.
    """
    console.print(
        "  [dim]Descubrimiento: regex + filtros de evidencia — sin LLM, con evidencia de chunks.[/dim]"
    )
    raw, _, docs, meta = _descubrir_zonas_interno(
        contenido,
        incluir_corpus=True,
    )
    zonas = _refinar_zonas_descubiertas(
        raw, contenido, es_modificacion=es_modificacion,
    )
    indices_relevantes = _indices_corpus_para_llm(meta, docs, zonas)
    chunks, zona_chunks = _construir_evidencia_chunks_zonas(
        zonas,
        docs,
        meta,
        indices_relevantes,
        contenido=contenido,
    )
    console.print(f"[cyan]Paso 1 — {len(zonas)} zonas: {', '.join(zonas)}[/cyan]")
    console.print(
        f"[dim]Evidencia: {len(chunks)} chunk(s) con zonas; "
        f"{len(indices_relevantes)} chunk(s) seleccionados (tablas + zonas).[/dim]"
    )
    return {
        "zonas": zonas,
        "chunks": chunks,
        "zona_chunks": zona_chunks,
        "indices_relevantes": sorted(indices_relevantes),
    }


def construir_chunks_para_llm(
    contenido: str,
    es_modificacion: bool = False,
    *,
    solo_relevantes: bool = True,
) -> dict:
    """
    Troceado del PRC para el LLM: prosa por tokens con solape, tablas por filas.

    Devuelve tablas y trozos que mencionan zonas del catálogo (Paso 1), con zonas
    asignadas por evidencia en cada fragmento.
    """
    raw, _, docs, meta = _descubrir_zonas_interno(
        contenido,
        incluir_corpus=True,
    )
    zonas = _refinar_zonas_descubiertas(
        raw, contenido, es_modificacion=es_modificacion,
    )
    indices_relevantes = _indices_corpus_para_llm(meta, docs, zonas)

    if solo_relevantes:
        indices = sorted(indices_relevantes)
    else:
        indices = list(range(len(docs)))

    chunks: list[dict] = []
    for idx in indices:
        if idx < 0 or idx >= len(docs):
            continue
        texto = docs[idx]
        info = dict(meta[idx]) if idx < len(meta) else {}
        gstart = info.get("start")
        zonas_en_chunk = [
            z
            for z in zonas
            if _chunk_contiene_zona(
                texto,
                z,
                contenido=contenido,
                chunk_global_start=gstart if gstart is not None else None,
            )
        ]
        chunks.append(
            {
                "idx": idx,
                "hash": _chunk_hash(texto),
                "kind": info.get("kind", ""),
                "start": info.get("start"),
                "end": info.get("end"),
                "chars": len(texto),
                "recuperado_zone_extractor": idx in indices_relevantes,
                "seleccionado_para_llm": idx in indices_relevantes,
                "zonas": zonas_en_chunk,
                "texto": texto,
            }
        )

    return {
        "zonas": zonas,
        "chunks": chunks,
        "indices_relevantes": sorted(indices_relevantes),
        "n_chunks_corpus": len(docs),
    }


def crear_chunks_tfidf(
    contenido: str,
    es_modificacion: bool = False,
    *,
    solo_relevantes: bool = True,
) -> list[dict]:
    """
    Lista de chunks en formato plano (numero, inicio, fin, texto, zonas, idx, …).
    Alias de `construir_chunks_para_llm` (nombre legado; ya no usa TF-IDF).
    """
    pack = construir_chunks_para_llm(
        contenido,
        es_modificacion=es_modificacion,
        solo_relevantes=solo_relevantes,
    )
    out: list[dict] = []
    for n, ch in enumerate(pack.get("chunks") or [], start=1):
        texto = ch.get("texto") or ""
        start = ch.get("start")
        if start is None:
            start = 0
        out.append(
            {
                "numero": n,
                "idx": ch.get("idx"),
                "inicio": start,
                "fin": start + len(texto),
                "texto": texto,
                "zonas": list(ch.get("zonas") or []),
                "hash": ch.get("hash"),
                "kind": ch.get("kind", ""),
                "recuperado_tfidf": bool(ch.get("recuperado_zone_extractor")),
            }
        )
    return out


# ═══════════════════════════════════════════════════════════════════════════
# CLI standalone (descubrimiento de zonas sin extracción LLM)
# ═══════════════════════════════════════════════════════════════════════════
def _leer_comunas_interes_txt(path: Path) -> list[str]:
    if not path.is_file():
        console.print(f"[red]❌ No encontrado: {path}[/red]")
        return []
    return [
        ln.strip().upper()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


def _listar_md_bajo_comuna(base_comuna: Path) -> list[tuple[Path, bool]]:
    """(ruta .md, es_modificacion)."""
    out: list[tuple[Path, bool]] = []
    for subfolder, es_mod in (("origen", False), ("modificaciones", True)):
        carpeta = base_comuna / subfolder
        if not carpeta.is_dir():
            continue
        for p in sorted(carpeta.glob("*.md")):
            out.append((p, es_mod))
    return out


def _iter_documentos_standalone(
    *,
    carpeta: Path | None,
    todas_las_comunas: bool,
    comunas_file: Path,
) -> list[tuple[str, Path]]:
    """Lista (comuna, path_md)."""
    if carpeta is not None:
        base = carpeta if carpeta.is_absolute() else _REPO_ROOT / carpeta
        base = base.resolve()
        if base.is_file() and base.suffix.lower() == ".md":
            try:
                idx = base.parts.index("datalab_markdown")
                comuna = base.parts[idx + 1].upper()
            except (ValueError, IndexError):
                comuna = base.parent.parent.name.upper()
            return [(comuna, base)]
        if not base.is_dir():
            console.print(f"[red]❌ No es carpeta válida: {base}[/red]")
            return []
        if (base / "origen").is_dir() or (base / "modificaciones").is_dir():
            comuna = base.name.upper()
            return [(comuna, p) for p, _ in _listar_md_bajo_comuna(base)]
        if base.name.lower() in ("origen", "modificaciones") and base.parent.is_dir():
            comuna = base.parent.name.upper()
            return [(comuna, p) for p in sorted(base.glob("*.md"))]
        sub_md = sorted(base.glob("*.md"))
        if sub_md:
            comuna = base.parent.name.upper()
            return [(comuna, p) for p in sub_md]
        console.print(
            "[red]❌ --carpeta debe ser …/datalab_markdown/<COMUNA> "
            "(con origen/ o modificaciones/), una subcarpeta origen|modificaciones, "
            "carpeta con .md, o un .md bajo ese árbol.[/red]"
        )
        return []

    if todas_las_comunas:
        if not _DATALAB_MARKDOWN_DEFAULT.is_dir():
            return []
        out: list[tuple[str, Path]] = []
        for comuna_dir in sorted(_DATALAB_MARKDOWN_DEFAULT.iterdir()):
            if not comuna_dir.is_dir():
                continue
            comuna = comuna_dir.name.upper()
            for p, _ in _listar_md_bajo_comuna(comuna_dir):
                out.append((comuna, p))
        return out

    comunas = _leer_comunas_interes_txt(comunas_file)
    if not comunas:
        return []
    out = []
    for comuna in comunas:
        for p, _ in _listar_md_bajo_comuna(_DATALAB_MARKDOWN_DEFAULT / comuna):
            out.append((comuna, p))
    return out


def _normalizar_zona_gt(z: str) -> str:
    """Normalización alineada con data/gt/*.csv y compare_gt."""
    return re.sub(r"[^A-Z0-9]", "", z.upper())


def _stem_documento_fuente(path_or_name: str) -> str:
    return Path(path_or_name).name.replace(".md", "")


def _cargar_gt_por_documento(path: Path) -> dict[str, set[str]]:
    """documento_fuente (sin .md) → zonas normalizadas."""
    by_doc: dict[str, set[str]] = {}
    if not path.is_file():
        return by_doc
    raw = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if raw is None:
        return by_doc
    for row in csv.DictReader(raw.splitlines(), delimiter=";"):
        doc = _stem_documento_fuente(row.get("documento_fuente", ""))
        zona = (row.get("ZONA") or row.get("\ufeffZONA") or row.get("zona") or "").strip()
        if doc and zona:
            by_doc.setdefault(doc, set()).add(_normalizar_zona_gt(zona))
    return by_doc


def _construir_pred_por_documento(filas: list[dict[str, str]]) -> dict[str, set[str]]:
    pred: dict[str, set[str]] = {}
    for row in filas:
        doc = _stem_documento_fuente(row.get("documento", ""))
        zona = (row.get("zona") or "").strip()
        if not doc or not zona:
            continue
        pred.setdefault(doc, set()).add(_normalizar_zona_gt(zona))
    return pred


def _reportar_coincidencia_gt(
    comunas: set[str],
    filas: list[dict[str, str]],
    docs_procesados: set[str],
) -> None:
    """Recall/precisión de zonas descubiertas vs data/gt/<COMUNA>.csv."""
    if not filas or not docs_procesados:
        return
    pred = _construir_pred_por_documento(filas)
    gt_root = _REPO_ROOT / "data" / "gt"
    alguna_comparacion = False

    for comuna in sorted(comunas):
        gt_path = gt_root / f"{comuna}.csv"
        gt = _cargar_gt_por_documento(gt_path)
        if not gt:
            console.print(
                f"[dim]Sin GT para {comuna} ({gt_path.name} no encontrado o vacío).[/dim]"
            )
            continue

        docs_en_gt = sorted(d for d in docs_procesados if d in gt)
        if not docs_en_gt:
            console.print(
                f"[dim]Sin documentos en común entre la corrida y {gt_path.name}.[/dim]"
            )
            continue

        alguna_comparacion = True
        hits = 0
        total_gt = 0
        total_pred = 0
        console.print(f"\n[bold]Coincidencia vs GT — {comuna}[/bold]")
        console.print(
            "[dim]  GT = data/gt/{comuna}.csv  ·  "
            "descubiertas = salida de este comando[/dim]".format(comuna=comuna)
        )
        console.print(
            "[dim]  falta = en GT, no descubierta  ·  "
            "extra = descubierta, no está en GT[/dim]"
        )
        for doc in docs_en_gt:
            g = gt[doc]
            p = pred.get(doc, set())
            h = g & p
            miss = g - p
            extra = p - g
            hits += len(h)
            total_gt += len(g)
            total_pred += len(p)
            console.print(
                f"  [dim]{doc}[/dim]: recall {len(h)}/{len(g)}  "
                f"(GT={len(g)}, descubiertas={len(p)})"
            )
            if miss:
                console.print(
                    f"    [yellow]falta (en GT, no descubierta):[/yellow] "
                    f"{', '.join(sorted(miss))}"
                )
            if extra:
                console.print(
                    f"    [yellow]extra (descubierta, no en GT):[/yellow] "
                    f"{', '.join(sorted(extra))}"
                )

        recall_pct = 100.0 * hits / total_gt if total_gt else 0.0
        precision_pct = 100.0 * hits / total_pred if total_pred else 0.0
        console.print(
            f"\n[bold green]Recall global {comuna}:[/bold green] "
            f"{hits}/{total_gt} ({recall_pct:.1f}%) "
            f"[dim]— zonas del GT que sí se descubrieron[/dim]"
        )
        console.print(
            f"[bold]Precisión global {comuna}:[/bold] "
            f"{hits}/{total_pred} ({precision_pct:.1f}%) "
            f"[dim]— descubiertas que están en el GT[/dim]"
        )

    if not alguna_comparacion and comunas:
        console.print(
            "[dim]No hubo comparación con GT (faltan CSV en data/gt/ o sin solape de documentos).[/dim]"
        )


def _imprimir_chunks_evidencia(
    evidencia: dict,
    *,
    max_chunks: int,
    max_chars: int,
    only_hash: str | None = None,
) -> None:
    chunks = list(evidencia.get("chunks") or [])
    if only_hash:
        chunks = [ch for ch in chunks if str(ch.get("hash") or "") == only_hash]
    if max_chunks > 0:
        chunks = chunks[:max_chunks]

    if not chunks:
        console.print("[yellow]Sin chunks de evidencia para mostrar con esos filtros.[/yellow]")
        return

    for ch in chunks:
        texto = str(ch.get("texto") or "")
        if max_chars > 0 and len(texto) > max_chars:
            texto = texto[:max_chars].rstrip() + "\n[...]"
        zonas = ", ".join(str(z) for z in (ch.get("zonas") or []))
        recuperado = "sí" if ch.get("recuperado_zone_extractor") else "no"
        console.rule(
            f"chunk {ch.get('hash')} · idx={ch.get('idx')} · zonas={zonas} · recuperado={recuperado}"
        )
        console.print(
            f"[dim]kind={ch.get('kind')} · chars={ch.get('chars')} · "
            f"offsets={ch.get('start')}–{ch.get('end')}[/dim]"
        )
        console.print(texto)


def _main_cli() -> None:
    ap = argparse.ArgumentParser(
        description="Descubrimiento de zonas (regex + tablas; sin LLM). Genera CSV solo con ZONA.",
    )
    ap.add_argument(
        "--carpeta",
        type=Path,
        default=None,
        help="Carpeta de una comuna bajo data/datalab_markdown/<COMUNA> "
        "(procesa origen/ y modificaciones/), o ruta a un .md concreto.",
    )
    ap.add_argument(
        "--comunas-archivo",
        type=Path,
        default=_COMUNAS_INTERES_DEFAULT,
        help="Lista de comunas (por defecto scripts/comunas_interes.txt).",
    )
    ap.add_argument(
        "--todas-las-comunas",
        action="store_true",
        help="Ignora comunas_interes.txt y recorre todas las carpetas en data/datalab_markdown.",
    )
    ap.add_argument(
        "--salida",
        type=Path,
        default=_REPO_ROOT / "data" / "resultados" / "zonas.csv",
        help="CSV de salida (se crea el directorio si no existe).",
    )
    ap.add_argument(
        "--salida-evidencia",
        type=Path,
        default=None,
        help="CSV opcional con zona -> hash de chunk y offsets de evidencia.",
    )
    ap.add_argument(
        "--mostrar-chunks-zonas",
        action="store_true",
        help="Imprime en consola los chunks internos donde aparecieron zonas descubiertas.",
    )
    ap.add_argument(
        "--max-chunks-consola",
        type=int,
        default=12,
        help="Máximo de chunks a imprimir por corrida cuando se usa --mostrar-chunks-zonas.",
    )
    ap.add_argument(
        "--chunk-chars",
        type=int,
        default=2500,
        help="Máximo de caracteres por chunk impreso en consola (0 = completo).",
    )
    ap.add_argument(
        "--chunk-hash",
        default=None,
        help="Si se usa --mostrar-chunks-zonas, imprime solo el chunk con este hash.",
    )
    args = ap.parse_args()

    docs = _iter_documentos_standalone(
        carpeta=args.carpeta,
        todas_las_comunas=args.todas_las_comunas,
        comunas_file=args.comunas_archivo,
    )
    if not docs:
        console.print("[yellow]Sin documentos .md para procesar.[/yellow]")
        raise SystemExit(1)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    filas: list[dict[str, str]] = []
    filas_evidencia: list[dict[str, str]] = []
    comunas_vistas: set[str] = set()
    docs_procesados: set[str] = set()
    for comuna, path in docs:
        try:
            rel = str(path.relative_to(_REPO_ROOT))
        except ValueError:
            rel = str(path)
        es_modificacion = "modificaciones" in path.parts
        console.print(f"\n[bold cyan]{comuna}[/bold cyan] [dim]— {rel}[/dim]")
        try:
            texto = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            console.print(f"[red]No se pudo leer {path}: {e}[/red]")
            continue
        contenido = eliminar_marcadores_paginacion_markdown(
            _filtrar_contenido_prc(texto),
        )
        if args.mostrar_chunks_zonas or args.salida_evidencia:
            evidencia = descubrir_zonas_con_evidencia(
                contenido, es_modificacion=es_modificacion,
            )
            zonas = list(evidencia.get("zonas") or [])
            if args.mostrar_chunks_zonas:
                _imprimir_chunks_evidencia(
                    evidencia,
                    max_chunks=args.max_chunks_consola,
                    max_chars=args.chunk_chars,
                    only_hash=args.chunk_hash,
                )
            chunk_by_hash = {
                str(ch.get("hash") or ""): ch
                for ch in (evidencia.get("chunks") or [])
                if ch.get("hash")
            }
            zona_chunks = evidencia.get("zona_chunks") or {}
            for z in zonas:
                for h in zona_chunks.get(z, []):
                    ch = chunk_by_hash.get(str(h), {})
                    filas_evidencia.append(
                        {
                            "comuna": comuna,
                            "documento": rel,
                            "zona": z,
                            "chunk_hash": str(h),
                            "chunk_idx": str(ch.get("idx", "")),
                            "kind": str(ch.get("kind", "")),
                            "start": str(ch.get("start", "")),
                            "end": str(ch.get("end", "")),
                            "chars": str(ch.get("chars", "")),
                            "recuperado_zone_extractor": "1" if ch.get("recuperado_zone_extractor") else "0",
                        }
                    )
        else:
            zonas = descubrir_zonas(contenido, es_modificacion=es_modificacion)
        comunas_vistas.add(comuna)
        docs_procesados.add(path.stem)
        for z in zonas:
            filas.append({"comuna": comuna, "documento": rel, "zona": z})

    with open(args.salida, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["comuna", "documento", "zona"], delimiter=";")
        w.writeheader()
        w.writerows(filas)

    if args.salida_evidencia:
        args.salida_evidencia.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "comuna",
            "documento",
            "zona",
            "chunk_hash",
            "chunk_idx",
            "kind",
            "start",
            "end",
            "chars",
            "recuperado_zone_extractor",
        ]
        with open(args.salida_evidencia, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
            w.writeheader()
            w.writerows(filas_evidencia)
        console.print(
            f"[bold green]✅ {len(filas_evidencia)} fila(s) evidencia → {args.salida_evidencia}[/bold green]"
        )

    console.print(f"[bold green]✅ {len(filas)} fila(s) → {args.salida}[/bold green]")
    _reportar_coincidencia_gt(comunas_vistas, filas, docs_procesados)


def _self_check_codigo_antes_zona() -> None:
    """ponytail: regresión «Z5 ZONA AREA» vs «PARA CADA ZONA»."""
    blob = (
        "##### Z5 ZONA AREA VERDE - DEPORTE\n"
        "PARA CADA ZONA ESTABLECE ESTA ORDENANZA\n"
        "ZONA B1 RESIDENCIAL\n"
    ).upper()
    p_hdr = blob.find("ZONA")
    assert _codigo_en_linea_antes_de_zona(blob, p_hdr) == "Z5"
    p_prosa = blob.find("ZONA", p_hdr + 1)
    assert _codigo_en_linea_antes_de_zona(blob, p_prosa) is None
    cands: set[str] = set()
    _scan_zona_codigos(blob, cands)
    norm = {_normalizar_codigo_zona(c) for c in cands}
    assert "Z5" in norm and "AREA" not in norm and "CADA" not in norm
    assert "B1" in norm
    blob_ps = "GRAFICADAS EN LOS PLANOS: AH-AM-0496 PS1, NOVIEMBRE 2001\nZONA B1 RESIDENCIAL\n"
    cands_ps: set[str] = set()
    _scan_zona_codigos(blob_ps, cands_ps)
    norm_ps = {_normalizar_codigo_zona(c) for c in cands_ps}
    assert "PS1" not in norm_ps and "B1" in norm_ps
    from utils import regex as _rx

    assert _rx.codigo_es_sufijo_plano_ps(blob_ps, "PS1")


if __name__ == "__main__":
    _self_check_codigo_antes_zona()
    _main_cli()
