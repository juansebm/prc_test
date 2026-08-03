"""Patrones y utilidades regex compartidos (PRC, zonas normativas, D.S., LLM)."""

from __future__ import annotations

import re
from re import Pattern

# ── Ordenanza / sección de zona ─────────────────────────────────────────────
RE_INICIO_ORDENANZA = re.compile(
    r"(?:"
    r"ORDENANZA\s+LOCAL"
    r"|CAPITULO\s+I\b"
    r"|Art[íi]culo\s+1[\s\S]{0,60}(?:La presente Ordenanza|presente ordenanza)"
    r")",
    re.IGNORECASE,
)

RE_MARCADORES_SECCION_ZONA = re.compile(
    r"(?:"
    r"Usos\s+de\s+suelo\s+permitidos"
    r"|Usos\s+de\s+suelo\s+prohibidos"
    r"|Usos\s+permitidos"
    r"|Usos\s+prohibidos"
    r"|Los\s+permisos\s+para\s+obras"
    r"|Corresponde\s+a\s+(?:la|una)\s+[Zz]ona"
    r"|Para\s+ella\s+reg[ií]r"
    r"|Condiciones\s+de\s+Subdivisi[oó]n"
    r")",
    re.IGNORECASE,
)

RE_ZONA_TERMINADOR = (
    r"(?="
    r"\s*(?:\n|[:\.,]\s)"
    r"|\s+ZONA\b"
    r"|\s+ZCH\b"
    r"|\s+SE\b"
    r"|\s+(?:Usos|Corresponde|Las|Los|Párrafo|Normas|CAP[IÍ]TULO|ART[IÍ]CULO|El\s+territorio|Los\s+l[ií]mites)\b"
    r"|\s*</?(?:li|ul|td|th|p|div|tr)\b"
    r"|\s*<"
    r"|$"
    r")"
)

RE_ZONA_CODIGO_PARTES = r"([A-Z0-9]{1,5}(?:\s(?!ZCH\b|SE\b)[A-Z0-9]{1,5}){0,2})"

RE_ZONA_ESTRICTO = re.compile(
    r"(?<![A-Za-z])"
    r"ZONA\s+"
    + RE_ZONA_CODIGO_PARTES
    + RE_ZONA_TERMINADOR,
    re.IGNORECASE,
)

RE_ZONA_LOOKBACK = re.compile(
    r"(?<![A-Za-z])"
    r"ZONA\s*"
    + RE_ZONA_CODIGO_PARTES
    + RE_ZONA_TERMINADOR,
    re.IGNORECASE,
)

RE_SECTOR_CODIGO = re.compile(
    r"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+"
    r"([A-Z]+)-?(\d{1,3})\b",
)

RE_SUBSECTOR_CODIGO = re.compile(
    r"(?i)(?:sub[\s-]*(?:zonas?|sectores?)|sub[\s-]*sector|subsector)\s+"
    r"([A-Z])\s*-\s*(\d{1,3})(?:\s+([A-Z]))?\b",
)

RE_SUBSECTOR_LINEA_USO = re.compile(
    r"(?i)(?<![A-Za-z])([A-Z])\s*-\s*(\d{1,3})(?:\s*([A-Z]))?\s+"
    r"(?:teatro|equipamiento|plaza)\b",
)

RE_SECT_ESP_PAREJA = re.compile(
    r"(?i)sectores?\s+especiales?\s+"
    r"([A-Z]+)-?(\d{1,3})\s+y\s+([A-Z]+)-?(\d{1,3})\b",
)

# Guiones tipográficos en DO/PRC (Talca «ZE—3», «ZR—1», etc.).
_SEP_GUION_DO = r"[\-—–‑]"
_CHARS_GUION_DO = frozenset("-–—‑")
_RE_UNIFICAR_GUIONES_DO = re.compile(r"[\-–—‑]")
# Subzonas ZCHAL-V / ZCHAL-B (Valparaíso): sufijo de una letra tras guión.
_RE_Z_SUBZONA_LETRA_SUFFIX = re.compile(r"^(Z[A-Z]{2,7})-([A-Z])$")

RE_ZCH_TABLA = re.compile(
    r"(?<![A-Za-z])ZCH\s+([A-Z]+\d[A-Z0-9]*)\b",
    re.IGNORECASE,
)

RE_SE_TABLA = re.compile(
    r"(?<![A-Za-z])SE\s+([A-Z]+\d[A-Z0-9]*)\b",
    re.IGNORECASE,
)

RE_ZONAS_ENUM_EFGH = re.compile(
    r"(?i)entre\s+las\s+zonas\s+"
    r"([A-H])\s*,\s*([A-H])\s*,\s*([A-H])\s+y\s+([A-H])\b",
)

RE_ZONAS_LISTA_COMAS_Y_FINAL = re.compile(
    r"(?i)(?<![A-Za-z-])Zonas?\s+((?:[A-Z]\d*|[A-Z])(?:\s*,\s*(?:[A-Z]\d*|[A-Z]))*\s+y\s+(?:[A-Z]\d*|[A-Z])\b)",
)

# Talca (Z-1…), Iquique (M-1, A-1, BC2-1.1…): listados «Zonas siguientes: …» / «zonas M-11 y M-12».
_RE_TOKEN_LISTA_ZONA_PRC = (
    r"(?:Z(?:E|R|U|I|CH)?-\d+|Z-\d+|Z-[A-Z]|"
    r"ZR-[A-Z]|ZEP-[A-Z]{2}|"
    r"[A-Z]{1,4}(?:-\d+)+(?:\.\d+)?|"
    r"[A-H]\d+)"
)
RE_ZONAS_LISTA_TRAS_DOS_PUNTOS = re.compile(
    rf"(?i)(?<![A-Za-z-])Zonas?\s+"
    rf"(?:siguientes|se\s+se[nñ]alan[^\n:]{{0,80}}|indicadas[^\n:]{{0,80}}|"
    rf"compuesta\s+por\s+las\s+Zonas\s+siguientes|formada\s+por\s+las\s+Zonas\s+siguientes|"
    rf"que\s+se\s+se[nñ]alan[^\n:]{{0,40}})"
    rf"\s*:\s*"
    rf"({_RE_TOKEN_LISTA_ZONA_PRC}"
    rf"(?:\s*,\s*{_RE_TOKEN_LISTA_ZONA_PRC})*"
    rf"(?:\s+y\s+{_RE_TOKEN_LISTA_ZONA_PRC})?"
    rf")"
)
RE_ZONAS_LISTA_INLINE = re.compile(
    rf"(?i)(?<![A-Za-z-])Zonas?\s+"
    rf"({_RE_TOKEN_LISTA_ZONA_PRC}"
    rf"(?:\s*,\s*{_RE_TOKEN_LISTA_ZONA_PRC})*"
    rf"(?:\s+y\s+{_RE_TOKEN_LISTA_ZONA_PRC})?"
    rf")"
)

RE_ZONAS_LISTA_AREA = re.compile(
    rf"(?i)(?<![A-Za-z-])(?:Área|Area)\s+"
    rf"(?:Consolidad[ao]|de\s+Extensi[oó]n|Especial(?:es)?)\s*:\s*"
    rf"({_RE_TOKEN_LISTA_ZONA_PRC}"
    rf"(?:\s*,\s*{_RE_TOKEN_LISTA_ZONA_PRC})*"
    rf"(?:\s+y\s+{_RE_TOKEN_LISTA_ZONA_PRC})?"
    rf")"
)

RE_SPLIT_LISTA_COMAS_Y = re.compile(r"\s*,\s*|\s+y\s+", re.I)

# ── Normalización de código de zona ───────────────────────────────────────────
CPAT_COLAPSAR_WS = re.compile(r"\s+")
CPAT_GUION_LETRA_DIG = re.compile(r"([A-Z])-(\d)")
CPAT_GUION_ENTRE_DIGITOS_ZONA = re.compile(r"(\d)-(\d)")
CPAT_GUION_ENTRE_LETRAS_ZONA = re.compile(r"([A-Z])-([A-Z])")
CPAT_PUNTUACION_FINAL = re.compile(r"[\.\-,:;]+$")
CPAT_OCR_I_ENTRE_LETRA_DIG = re.compile(r"([A-Z])I([0-9])")
CPAT_OCR_I_FINAL_MULTILETRA = re.compile(r"([A-Z]{2,})I$")
CPAT_FULLMATCH_SE = re.compile(r"SE(?!CTOR)([A-Z]+\d+[A-Z0-9]*)")
CPAT_FULLMATCH_ZCH = re.compile(r"ZCH([A-Z]+\d+[A-Z0-9]*)")
CPAT_FULLMATCH_LETRAS_DIGS = re.compile(r"([A-Z]+)(\d+)")
CPAT_CODIGO_ZONA_TOKEN = re.compile(r"^[A-Z0-9][A-Z0-9\.\-]*$")
CPAT_DIGITO_EN_CADENA = re.compile(r"\d")
CPAT_PREFIJO_2MAS_LETRAS_DIG = re.compile(r"^([A-Z]{2,})\d+$")

RE_FENCE_OPEN = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
RE_FENCE_CLOSE = re.compile(r"\s*```\s*$")

# ── Posición de zona en documento ────────────────────────────────────────────
RE_NORMA_SECCION = re.compile(
    r"(?:sistema\s+de\s+agrupamiento|altura|normas\s+de\s+edificaci[oó]n|"
    r"D\.S\b|Decreto\s+Supremo|subdivisi[oó]n)",
    re.IGNORECASE,
)

RE_CTX_ZONA = re.compile(
    r"(?i)(?:art[\.\s]*[ií]culo\s*22|zona\s+[a-z]|sector|sectores?\s+especiales|"
    r"conservaci[oó]n|reempl[aá]zase|modific|ordenanza|plan\s+regulador)",
)

RE_FULLMATCH_ZONA_LETRAS_DIG = re.compile(r"[A-Z]+\d+")

# ── Subdivisión / saneo LLM ───────────────────────────────────────────────────
RE_EVIDENCIA_SUBDIVISION_PREDIAL = re.compile(
    r"subdivisi|subdividir|subdivid"
    r"|predial"
    r"|sub[\s-]*parcel"
    r"|\blotes?\b"
    r"|\bparcela\b"
    r"|\bm\.?\s*²\b|\bm2\b",
    re.IGNORECASE,
)

RE_CITA_LINEA_OCUPACION_MAX_SUelo = re.compile(
    r"(?is)porcentaje\s+m[aá]ximo\s+de\s+ocupaci[oó]n|"
    r"ocupaci[oó]n\s+(?:m[aá]xima\s+)?del\s+suelo"
)

RE_CITA_COEFICIENTE_O_FAR = re.compile(
    r"(?is)coeficiente|constructibilidad|f\.?\s*o\.?|f\.?\s*a\.?|"
    r"relaci[oó]n\s+(?:de\s+)?(?:pisos|edificaci)|pisos\s*/\s*terreno",
)

CPAT_QUITAR_DIGITOS_FINAL = re.compile(r"\d+$")
CPAT_VALOR_NUMERICO_MILES = re.compile(r"\d[\d,.]*")

# ── Decreto Supremo / citas ─────────────────────────────────────────────────
RE_REFERENCIA_DS_CAMPO = re.compile(
    r"(?is)^\s*(?:"
    r"d\.?\s*s\.?(?:\s*u\.?)?\s*(?:(?:n|n°|nº|nr\.?|n\.)\s*[°º]?\s*)?\d"
    r"|decreto\s+supremo(?:\s+exento)?\s+(?:n\s*[°º]?\s*)?\d"
    r")",
)

RE_NUMERO_EN_CITA_DS = re.compile(
    r"(?is)(?:d\.?\s*s\.?\s*(?:u\.?\s*)?(?:n\s*[°º]?\s*)?\s*|"
    r"decreto\s+supremo(?:\s+exento)?\s+(?:n\s*[°º]?\s*)?)\s*([\d\.]+)",
)

RE_MENCION_DS = re.compile(r"d\.?\s*s\.?|decreto\s+supremo", re.IGNORECASE)

RE_TEXTO_CONTIENE_DS_INICIO = re.compile(r"(?is)\bd\.?\s*s\.?|decreto\s+supremo")

RE_FECHA_DS_LITERAL = re.compile(
    r"(?is)del\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(19\d{2}|20\d{2})\b",
)

RE_FECHA_DS_LITERAL_ANO = re.compile(
    r"(?is)del\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+del\s+año\s+(19\d{2}|20\d{2})\b",
)

RE_FECHA_DS_SLASH = re.compile(
    r"(?is)(?:fecha\s+)?(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",
)

RE_PRIMER_DS_EN_TEXTO = re.compile(
    r"(?is)\b(?:d\.?\s*s\.?\s*(?:u\.?\s*)?(?:n\s*[°º]?\s*)?\s*[\d\.]+"
    r"|decreto\s+supremo(?:\s+exento)?\s+(?:n\s*[°º]?\s*)?\s*[\d\.]+)",
)

RE_ITEM_LISTA_HTML = re.compile(r"(?is)\s*</li>")

# ── Ventana normativa / remisión D.S. ───────────────────────────────────────
RE_PIS_AREA_COMUNAL_SANTIAGO = re.compile(
    r"(?is)área\s+correspondiente\s+a\s+la\s+comuna\s+de\s+santiago",
)

RE_ALTURA_METROS_EN_VENTANA = re.compile(
    r"(?is)(?:altura|edificaci[oó]n|rasantes).{0,120}?"
    r"\b\d+(?:[.,]\d+)?\s*(?:m|metros)\b",
)

RE_REMISION_NORMAS_DS = re.compile(
    r"(?is)(?:normas\s+de\s+(?:edificaci[oó]n|uso|ocupaci[oó]n).{0,400}?"
    r"(?:ser[aá]n|establecidas|establecidas en el|del)\s+(?:el\s+)?(?:d\.?\s*s\.?|decreto))",
)

RE_REMISION_COND_EDIF_DS = re.compile(
    r"(?is)(?:condiciones\s+de\s+edificaci[oó]n).{0,200}?"
    r"(?:d\.?\s*s\.?|decreto\s+supremo)",
)

RE_ESTABLECIDAS_EN_DS = re.compile(r"(?is)(?:establecidas\s+en\s+(?:el\s+)?d\.?\s*s\.?)")

RE_LIGA_ALTURAS_DS = re.compile(
    r"(?is)(?:altura|rasantes|pisos|edificaci[oó]n|condiciones\s+de\s+edificaci[oó]n)"
    r".{0,420}?(?:d\.?\s*s\.?|decreto\s+supremo)|"
    r"(?:d\.?\s*s\.?|decreto\s+supremo).{0,420}?"
    r"(?:altura|rasantes|pisos|edificaci[oó]n|condiciones\s+de\s+edificaci[oó]n)",
)

RE_VENTANA_COEF_CONSTRUCT_DS = re.compile(
    r"(?is)(?:coeficiente|constructibilidad|f\.?\s*o\.?|f\.?\s*a\.?|"
    r"relaci[oó]n\s+pisos|pisos\s*/\s*terreno|r\.?p\.?i\.?)",
)

# ── Sector conservación (extracción determinística) ─────────────────────────
RE_SUP_PREDIAL_MIN = re.compile(
    r"(?is)superficie\s+predial\s+m[íi]nima\s+ser[aá]\s+de\s+(\d+)\s*m",
)

# Bloque general «b) … Superficie Predial Mínima: … N m2» (con o sin «**» tras los dos puntos).
RE_SUP_APARTADO_BLOQUE_ZONA = re.compile(
    r"(?is)b\)\s*\*?\*?\s*Superficie\s+Predial\s+M[ií]nima:\s*(?:\*+\s*)?(\d+)\s*m",
)

RE_FRENTE_MIN = re.compile(
    r"(?is)frente\s+m[íi]nimo\s+de\s+(\d+)\s*m",
)

RE_SISTEMA_AGRUP_LISTA = re.compile(
    r"(?is)sistema\s+de\s+agrupamiento\s+ser[aá]\s+([A-Za-zÀ-ÿ,\s]+?)(?:\.|</|$)",
)

RE_ALTURA_MIN_MAX_BLOQUE = re.compile(
    r"(?is)altura\s+m[íi]nima.{0,220}?(\d+)\s*m.{0,120}?máxima.{0,220}?(\d+)\s*m",
)

RE_ALTURA_UNICA_BLOQUE = re.compile(
    r"(?is)altura\s+[úu]nica\s+de\s+edificaci[oó]n\s+ser[aá]\s+de\s+(\d+(?:[.,]\d+)?)\s*m",
)

RE_ALTURA_MAX_BLOQUE = re.compile(
    r"(?is)altura\s+m[aá]xima\s+de\s+edificaci[oó]n\s+ser[aá]\s+de\s+(\d+(?:[.,]\d+)?)\s*m",
)

CPAT_WS_UNICO = re.compile(r"\s+")

# ── Valores cuantitativos / CSV ───────────────────────────────────────────────
CPAT_NUM_OPCIONAL_DECIMAL = re.compile(r"-?\d+(?:\.\d+)?")
CPAT_ENTERO_TEXTO = re.compile(r"-?\d+")
CPAT_DECIMAL_PUNTO = re.compile(r"-?\d+\.\d+")

# ── Merge por zona (orden) ───────────────────────────────────────────────────
CPAT_ZONA_SORT = re.compile(r"^([A-Za-z]+)(\d*)")

# ── Evaluación (GT vs extracción) ───────────────────────────────────────────
RE_STEM_PREFIJO_TS_RESULTADO = re.compile(r"^\d{8}_\d{6}_\d{6}_(.+)$")

RE_DS_NUMERO = re.compile(
    r"(?:d\.?\s*s\.?|decreto\s+supremo)"
    r"[^\d]*?"
    r"(\d[\d.]*)",
    re.IGNORECASE,
)

RE_EVAL_NORM_TXT_NO_ALNUM = re.compile(r"[^\w\d\s\./]")

# ── API LLM (sanitizar JSON) ─────────────────────────────────────────────────
RE_CONTROL_API = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# ── extractor.py (metadata / batch) ───────────────────────────────────────────
RE_AÑO_4_DIGITOS = re.compile(r"(19|20)\d{2}")
RE_CODIGO_ARCHIVO_PREFIX = re.compile(r"^(\d+)_")
RE_FECHA_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
RE_PLANO_SECCIONAL_STEM = re.compile(
    r"[_\s](?:P[_\.]?\s*Seccional|Plano[_\s]Seccional|Seccional)",
    re.IGNORECASE,
)


def unificar_guiones_do(texto: str) -> str:
    """Normaliza rayas tipográficas del DO a guión ASCII (-)."""
    return _RE_UNIFICAR_GUIONES_DO.sub("-", texto or "")


def longitud_maxima_codigo_prc(codigo: str) -> int:
    """
    Tope de longitud para validar forma de código PRC.
    ZCH* y subzonas Z…-L (p. ej. ZCHSJP, ZCHAL-V) pueden superar 5 caracteres.
    """
    u = unificar_guiones_do((codigo or "").strip().upper())
    if _RE_Z_SUBZONA_LETRA_SUFFIX.fullmatch(u):
        return 8
    if re.fullmatch(r"ZCH[A-Z0-9]{1,5}", u):
        return 8
    return 5


def _colapsar_guion_entre_letras_zona(s: str) -> str:
    """«R-M», «E-P» → RM, EP (guión entre letras sueltas)."""
    while True:
        ns = CPAT_GUION_ENTRE_LETRAS_ZONA.sub(r"\1\2", s)
        if ns == s:
            return s
        s = ns


def _colapsar_guiones_entre_digitos_zona(s: str) -> str:
    """«BC2-21», «FC2-1» → BC221, FC21 (subzonas jerárquicas con guión)."""
    while True:
        ns = CPAT_GUION_ENTRE_DIGITOS_ZONA.sub(r"\1\2", s)
        if ns == s:
            return s
        s = ns


def normalizar_zona(zona: str) -> str:
    """
    Normaliza el código de zona para consistencia entre documentos (debe coincidir
    con evaluación GT vs extraído).

    - Quita espacios, puntos y guiones jerárquicos: BC2-2.1 → BC221, FC2-1 → FC21,
      ZEP-CC → ZEPCC, A-1 → A1.
    - Conserva prefijo Z cuando forma parte del código oficial (ZCC, ZAP, ZI…).
    """
    s = zona.strip().upper()
    s = unificar_guiones_do(s)
    s = CPAT_COLAPSAR_WS.sub("", s)
    s = s.replace(".", "")
    while True:
        ns = CPAT_GUION_LETRA_DIG.sub(r"\1\2", s)
        if ns == s:
            break
        s = ns
    # Subzonas ZCHAL-V / ZCHAL-B: conservar guión + letra (no colapsar a ZCHALV).
    m_z_suf = _RE_Z_SUBZONA_LETRA_SUFFIX.fullmatch(s)
    if m_z_suf:
        return f"{m_z_suf.group(1)}-{m_z_suf.group(2)}"
    s = _colapsar_guion_entre_letras_zona(s)
    # Subzonas Z{n}-{m} (p. ej. Z1-1, Z7-1): no colapsar a Z11/Z71 si coexisten Z11, Z12…
    m_subz = re.fullmatch(r"Z(\d+)-(\d+)$", s, re.I)
    if m_subz:
        return f"Z{m_subz.group(1)}-{m_subz.group(2)}"
    s = _colapsar_guiones_entre_digitos_zona(s)
    m_se = CPAT_FULLMATCH_SE.fullmatch(s)
    if m_se:
        s = m_se.group(1)
    m_zch = CPAT_FULLMATCH_ZCH.fullmatch(s)
    if m_zch:
        s = m_zch.group(1)
    return s


def codigo_zona_tiene_letra(codigo: str) -> bool:
    """Un código PRC válido incluye al menos una letra (no numerales de lista/fila)."""
    u = normalizar_zona((codigo or "").strip())
    return bool(u) and any(c.isalpha() for c in u)


_RE_ZONA_LETRA_A_H = re.compile(r"^[A-H]$")


def es_zona_urbana_letra_a_h(zona: str) -> bool:
    """Zonas principales del PRC Santiago (A–H), una sola letra."""
    return bool(_RE_ZONA_LETRA_A_H.fullmatch(normalizar_zona((zona or "").strip())))


def _match_es_coordenada_utm(contenido: str, m: re.Match[str]) -> bool:
    """
    True si la letra es eje Este/Norte UTM (E = …, N = …), no zona PRC E/F/G/H.
    """
    letra = contenido[m.start() : m.end()].upper()
    if letra not in "EN":
        return False
    ini = max(0, m.start() - 60)
    fin = min(len(contenido), m.end() + 60)
    ventana = contenido[ini:fin]
    if re.search(r"(?i)UTM", ventana) and re.search(
        rf"(?i)\b{letra}\s*=\s*[\d.,]+",
        ventana,
    ):
        return True
    if re.search(rf"(?i)coordenadas?\s+(?:geogr[aá]ficas?\s+)?(?:UTM\s+)?{letra}\s*=", ventana):
        return True
    if re.search(rf"(?i)\b{letra}\s*=\s*[\d.,]{{3,}}", ventana):
        return True
    return False


def _linea_contiene_utm(linea: str) -> bool:
    return bool(re.search(r"(?i)UTM|coordenadas?\s+geogr", linea or ""))


def _match_es_referencia_administrativa_no_zona(contenido: str, m: re.Match[str]) -> bool:
    """
    True si el match es código administrativo ajeno al PRC (p. ej. concesión radiodifusión
    «(Y84 - 048)» en encabezados del Diario Oficial), no una zona/subzona.
    """
    start, end = m.start(), m.end()
    code = contenido[start:end].strip().upper()
    if not code:
        return False
    ventana = contenido[max(0, start - 140) : min(len(contenido), end + 140)]
    if re.search(
        rf"\(\s*{re.escape(code)}\s*-\s*\d",
        ventana,
        re.I,
    ):
        return True
    if re.search(
        r"(?i)radiodifusi[oó]n|concesi[oó]n\s+de\s+radiodifusi|frecuencia\s+modulada|"
        r"radiodifusi[oó]n\s+sonora|plant[ao]\s+transmisora|radiomemoria",
        ventana,
    ):
        return True
    return False


def _match_es_numeral_o_estructura_no_zona(contenido: str, m: re.Match[str]) -> bool:
    """
    True si el match es numeral de lista, versión de artículo, N°, plano, etc.,
    no un código de zona/subzona del PRC.
    """
    start, end = m.start(), m.end()
    line_start = contenido.rfind("\n", 0, start) + 1
    prefix = contenido[line_start:start]
    if re.fullmatch(r"[\s>*#\-]*", prefix) and end < len(contenido):
        tail = contenido[end : end + 2]
        if tail.startswith(".") or tail.startswith(")"):
            return True
    if start > 0 and contenido[start - 1] == ".":
        return True
    pre = contenido[max(0, start - 14) : start]
    if re.search(
        r"(?:N[°º]|Art[ií]culo|Ord\.?|P[aá]gina|Secc\.?|Inciso|literal|Acuerdo)\s*$",
        pre,
        re.I,
    ):
        return True
    if re.search(r"(?:PRS|Plano)\s*[-\s]*$", pre, re.I):
        return True
    pre20 = contenido[max(0, start - 20): start]
    tok = contenido[start:end].strip().upper()
    if re.fullmatch(r"PS\d{1,2}", tok) and re.search(r"\d{3,5}\s*$", pre20):
        return True
    post = contenido[end : end + 12]
    if re.match(r"(?i)\s+Parte\b", post):
        return True
    pre2 = contenido[max(0, start - 24) : start]
    if re.search(r"(?i)\b(?:Punto|Parte|Colectiva|Cap[ií]tulo|T[ií]tulo)\s*$", pre2):
        return True
    pre_ctx = contenido[max(0, start - 50) : start]
    # Folios / cartas «N° B63 al B69» (extremo final del rango).
    if re.search(r"N[°º]\s*[A-Z]\d+\s+al\s*$", pre_ctx, re.I):
        return True
    # Código de establecimiento educacional («escuela D45»).
    if re.search(r"(?i)\bescuela\s*$", pre_ctx):
        return True
    # Identificador de cuadro normativo («Cuadro CUS3», «Cuadro CU03»).
    if re.search(r"(?i)Cuadro\s+(?:CUS|CU)?\s*$", pre_ctx):
        return True
    return False


def _match_es_unidad_superficie_m2(contenido: str, m: re.Match[str]) -> bool:
    """
    True si «M2» / «M»+dígito es metros cuadrados (p. ej. «2500 M2», «Por M2»),
    no un código de zona tipo Plan Seccional Sur (Iquique: «ZONA M2»).
    """
    start, end = m.start(), m.end()
    tok = contenido[start:end].strip().upper()
    if not re.fullmatch(r"M\d{1,2}", tok):
        return False
    pre = contenido[max(0, start - 28) : start]
    if re.search(r"\d[\d.,\s]*$", pre):
        return True
    line_start = contenido.rfind("\n", 0, start) + 1
    line_end = contenido.find("\n", end)
    if line_end < 0:
        line_end = len(contenido)
    line = contenido[line_start:line_end]
    if re.search(rf"(?i)\bpor\s+{re.escape(tok)}\b", line):
        return True
    lo = line.lower()
    if re.search(
        r"(?i)(?:superficie|construidos|estacionamiento|predial|m[ií]nima)",
        lo,
    ) and re.search(rf"(?i)\d[\d.,\s]*\s*{re.escape(tok)}\b", line):
        return True
    return False


def normalizar_codigo_zona(raw: str) -> str:
    """Normaliza código extraído por regex (OCR, puntuación)."""
    z = CPAT_COLAPSAR_WS.sub("", raw.strip().upper())
    z = z.replace(".", "")
    while True:
        nz = CPAT_GUION_LETRA_DIG.sub(r"\1\2", z)
        if nz == z:
            break
        z = nz
    z = CPAT_PUNTUACION_FINAL.sub("", z)

    def _ocr_i_quita_i_espuria(m: re.Match[str]) -> str:
        # «ZI1», «ZI2» son códigos reales (p. ej. PRC Ñuñoa); no confundir con OCR «Z1».
        if m.group(1) == "Z":
            return m.group(0)
        return m.group(1) + m.group(2)

    z = CPAT_OCR_I_ENTRE_LETRA_DIG.sub(_ocr_i_quita_i_espuria, z)
    z = CPAT_OCR_I_FINAL_MULTILETRA.sub(r"\g<1>1", z)
    return normalizar_zona(z)


def _frag_caracteres_espaciados_do(z: str) -> str:
    """OCR/Datalab: «S M 1», «E Q S», «C H» además de la forma compacta."""
    u = (z or "").strip().upper()
    if len(u) < 2 or len(u) > 5 or not all(c.isalnum() for c in u):
        return re.escape(u)
    spaced = r"\s+".join(re.escape(c) for c in u)
    return rf"(?:{spaced}|{re.escape(u)})"


def regex_fragmento_zona_en_fuente(zona: str) -> str:
    """Fragmento regex que reconoce el código como en el DO (p. ej. A-1 vs A1 vs «Z 5», «ZI 1»)."""
    z = zona.strip().upper()
    g = _SEP_GUION_DO
    gs = rf"\s*{g}\s*"
    m3 = re.fullmatch(r"([A-Z]+)(\d+)([A-Z])", z)
    if m3:
        L, digs, suf = m3.group(1), m3.group(2), m3.group(3)
        hyp = rf"{re.escape(L)}{g}{re.escape(digs)}"
        hyp_sp = rf"{re.escape(L)}{gs}{re.escape(digs)}"
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
    # Iquique Playa Blanca: BC211 en DO como «BC2-1.1» / «BC2-1-1».
    mh = re.fullmatch(r"([A-Z]+\d)(\d)(\d)$", z)
    if mh:
        base, d1, d2 = mh.groups()
        dotted = rf"{re.escape(base)}{g}{d1}\.{d2}"
        hyp = rf"{re.escape(base)}{g}{d1}{g}{d2}"
        joined = rf"{re.escape(base)}{g}{d1}{d2}"
        return rf"(?:{dotted}|{hyp}|{joined}|{re.escape(z)})"
    # Z11B-1 / Z11B-2 → Z11B1 (subzona: dígitos+letra final + guión + subíndice).
    m_ld = re.fullmatch(r"([A-Z]+\d+[A-Z])(\d+)$", z)
    if m_ld:
        base, sub = m_ld.group(1), m_ld.group(2)
        hyp = rf"{re.escape(base)}{g}{re.escape(sub)}"
        hyp_sp = rf"{re.escape(base)}{gs}{re.escape(sub)}"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    # BC21 / FC21 en DO como «BC2-1» (un solo subnivel).
    ms = re.fullmatch(r"([A-Z]{2,}\d)(\d)$", z)
    if ms:
        base, d1 = ms.groups()
        hyp = rf"{re.escape(base)}{g}{d1}"
        hyp_sp = rf"{re.escape(base)}{gs}{d1}"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    # Iquique: ZRB en DO como «ZR-B».
    mz = re.fullmatch(r"(ZR)([A-Z])$", z)
    if mz:
        pfx, suf = mz.groups()
        hyp = rf"{re.escape(pfx)}{g}{re.escape(suf)}"
        hyp_sp = rf"{re.escape(pfx)}{gs}{re.escape(suf)}"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    # M-6.1 → M61; M-12 → M12 (variantes con punto o guión compuesto).
    md = re.fullmatch(r"([A-Z])(\d)(\d)$", z)
    if md:
        letra, d1, d2 = md.groups()
        dotted = rf"{letra}{g}{d1}\.{d2}"
        hyp12 = rf"{letra}{g}{d1}{d2}"
        hyp_sep = rf"{letra}{g}{d1}{g}{d2}"
        return rf"(?:{dotted}|{hyp12}|{hyp_sep}|{re.escape(z)})"
    # Subzonas Z1-1, Z7-1 (Alto Hospicio): conservar guión; no confundir con Z11/Z12.
    m_subz = re.fullmatch(r"Z(\d+)-(\d+)$", z)
    if m_subz:
        d1, d2 = m_subz.group(1), m_subz.group(2)
        hyp = rf"Z{g}{d1}{g}{d2}"
        hyp_sp = rf"Z{gs}{d1}{gs}{d2}"
        mid = rf"Z{d1}{g}{d2}"
        return rf"(?:{hyp_sp}|{hyp}|{mid}|{re.escape(z)})"
    # ZCHAL-V / ZCHAL-B (Valparaíso): sufijo de una letra tras guión.
    m_z_suf = re.fullmatch(r"(Z[A-Z]{2,7})-([A-Z])$", z)
    if m_z_suf:
        base, suf = m_z_suf.group(1), m_z_suf.group(2)
        hyp = rf"{re.escape(base)}{g}{re.escape(suf)}"
        hyp_sp = rf"{re.escape(base)}{gs}{re.escape(suf)}"
        sp = rf"{re.escape(base)}\s+{re.escape(suf)}"
        return rf"(?:{hyp_sp}|{hyp}|{sp}|{re.escape(z)})"
    # ZEPCC en DO como «ZEP-CC».
    mzep = re.fullmatch(r"(ZEP)(CC)$", z)
    if mzep:
        pfx, suf = mzep.groups()
        hyp = rf"{re.escape(pfx)}{g}{re.escape(suf)}"
        hyp_sp = rf"{re.escape(pfx)}{gs}{re.escape(suf)}"
        return rf"(?:{hyp_sp}|{hyp}|{re.escape(z)})"
    m = CPAT_FULLMATCH_LETRAS_DIGS.fullmatch(z)
    if m:
        letras, digs = m.group(1), m.group(2)
        # Muchos PRC escriben «ZONA Z 1», «ZONA ZI 2» (espacio entre bloque alfabético y dígitos)
        # o «M - 1» (espacios alrededor del guión; p. ej. Plan Seccional Sur, Iquique 1989).
        hyp = rf"{re.escape(letras)}{g}{re.escape(digs)}"
        hyp_sp = rf"{re.escape(letras)}{gs}{re.escape(digs)}"
        sp = rf"{re.escape(letras)}\s+{re.escape(digs)}"
        sp_all = _frag_caracteres_espaciados_do(z)
        no_subcodigo = r"(?!\s*[-.]\s*\d)"
        return rf"(?:{hyp_sp}{no_subcodigo}|{hyp}{no_subcodigo}|{sp}{no_subcodigo}|{sp_all}{no_subcodigo})"
    m2 = re.fullmatch(r"([A-Z])([A-Z])", z)
    if m2:
        a, b = m2.group(1), m2.group(2)
        hyp = rf"{re.escape(a)}{g}{re.escape(b)}"
        hyp_sp = rf"{re.escape(a)}{gs}{re.escape(b)}"
        sp_letters = rf"{re.escape(a)}\s+{re.escape(b)}"
        return rf"(?:{hyp_sp}|{hyp}|{sp_letters}|{re.escape(z)})"
    if re.fullmatch(r"[A-Z]{2,5}", z):
        return rf"{_frag_caracteres_espaciados_do(z)}(?!\s*-\s*[A-Z0-9])"
    return re.escape(z)


def frag_codigo_zona_case_sensitive(frag: str) -> str:
    """
    Código de zona/subzona en el DO va en MAYÚSCULAS (A, B15, A-1).
    Dentro de un patrón (?i) evita matchear la preposición «a» como zona A.
    """
    return f"(?-i:{frag})"


def codigo_zona_solo_una_letra(zona: str) -> bool:
    z = normalizar_zona((zona or "").strip())
    return len(z) == 1 and z.isalpha()


def iter_spans_evidencia_codigo_zona(
    contenido: str,
    zona: str,
    *,
    max_spans: int = 200,
):
    """Posiciones del código de zona con evidencia PRC (código en mayúsculas)."""
    nz = normalizar_zona((zona or "").strip())
    if not nz or not codigo_zona_tiene_letra(nz):
        return
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    n = 0
    patrones: list[str] = [
        rf"(?i)(?<![A-Za-z])ZONA\s+{fcs}\b",
        rf"(?i)(?<![A-Za-z])ZONAS\s+{fcs}\b",
        rf"(?i)\bZona\s+de\s+Conservaci[oó]n\s+Hist[oó]rica\s+{fcs}\b",
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
        rf"(?i)sectores?\s+especiales?\s+{fcs}\b",
        rf"(?m)(?<=\|)\s*{re.escape(nz)}\s*(?=\|)",
    ]
    if not codigo_zona_solo_una_letra(nz):
        patrones.append(rf"(?<![A-Za-z0-9]){fcs}(?![A-Za-z0-9])")
    vistos: set[tuple[int, int]] = set()
    for pat in patrones:
        for m in re.finditer(pat, contenido):
            if _match_es_coordenada_utm(contenido, m):
                continue
            key = (m.start(), m.end())
            if key in vistos:
                continue
            vistos.add(key)
            yield m.start(), m.end()
            n += 1
            if n >= max_spans:
                return

    # Encabezados «#### Z-1», «#### **ZR—1 CURSOS…**» (Talca y homólogos).
    for m in re.finditer(
        rf"(?m)^#{{1,6}}\s*(?:\*\*)?\s*{frag}(?:\*\*)?(?:\s|:|$)",
        contenido,
    ):
        key = (m.start(), m.end())
        if key in vistos:
            continue
        vistos.add(key)
        yield m.start(), m.end()
        n += 1
        if n >= max_spans:
            return
    # Ítem de catálogo PRCT: «- U-10 …», «  - Subzona R-3 A».
    for m in re.finditer(
        rf"(?m)^\s*-\s*(?:(?:Sub[\s-]*zonas?|Subzona)\s+)?{frag}\b",
        contenido,
        re.IGNORECASE,
    ):
        key = (m.start(), m.end())
        if key in vistos:
            continue
        vistos.add(key)
        yield m.start(), m.end()
        n += 1
        if n >= max_spans:
            return

    # Título de zona en línea sola: «Z-7», «ZE-2», «Z-D».
    for m in re.finditer(
        rf"(?m)^\s*(?:\*\*)?\s*{frag}\s*(?:\*\*)?\s*$",
        contenido,
    ):
        key = (m.start(), m.end())
        if key in vistos:
            continue
        vistos.add(key)
        yield m.start(), m.end()
        n += 1
        if n >= max_spans:
            return

    # «Sectores Especiales C1 y C2» — un span por cada código de la pareja.
    for m in RE_SECT_ESP_PAREJA.finditer(contenido):
        cod_a = normalizar_zona(m.group(1) + m.group(2))
        cod_b = normalizar_zona(m.group(3) + m.group(4))
        parejas: list[tuple[int, int]] = []
        if nz == cod_a:
            parejas.append((m.start(1), m.end(2)))
        if nz == cod_b:
            parejas.append((m.start(3), m.end(4)))
        for start, end in parejas:
            key = (start, end)
            if key in vistos:
                continue
            vistos.add(key)
            yield start, end
            n += 1
            if n >= max_spans:
                return


def codigos_zona_desde_listado_comas_y(inner: str) -> set[str]:
    partes = RE_SPLIT_LISTA_COMAS_Y.split(inner)
    return {normalizar_zona(p.strip()) for p in partes if p.strip()}


def hay_evidencia_zona_en_listados_normativos(contenido: str, zona: str) -> bool:
    """Listados explícitos de códigos (p. ej. «Zonas siguientes: Z-1, Z-2, Z-D»)."""
    nz = normalizar_zona(zona.strip())
    if not nz:
        return False
    for pat in (
        RE_ZONAS_LISTA_COMAS_Y_FINAL,
        RE_ZONAS_LISTA_TRAS_DOS_PUNTOS,
        RE_ZONAS_LISTA_INLINE,
        RE_ZONAS_LISTA_AREA,
    ):
        for m in pat.finditer(contenido):
            inner = m.group(1)
            if not inner:
                continue
            for c in codigos_zona_desde_listado_comas_y(inner):
                raw = c.strip()
                if normalizar_zona(raw) == nz and raw == raw.upper():
                    return True
    return False


def zonas_mencionadas_en_fragmento(texto: str, zonas: list[str]) -> list[str]:
    """Zonas del catálogo mencionadas en un fragmento (visualizador; sin exigir keyword)."""
    out: list[str] = []
    seen: set[str] = set()
    for z in zonas:
        nz = normalizar_zona(str(z).strip())
        if not nz or nz in seen:
            continue
        if codigo_zona_en_mayusculas_en_texto(texto or "", nz) and documento_evidencia_codigo_zona(
            texto or "", nz
        ):
            seen.add(nz)
            out.append(nz)
    return out


# Remisión a categoría del PRMS (p. ej. estacionamiento «Zona C, según PRMS y O.G.U.C.»): no define zona del PRC.
_RE_REMISION_ZONA_LETRA_TRAS_COMA_PRMS = re.compile(
    r"(?is)^\s*,\s*según\s+PRMS(?:\s+y\s+O\.?\s*G\.?\s*U\.?\s*C\.?)?"
)


# Sufijos de láminas cartográficas PRS (Santiago y homólogos): PRS-01, PRS03-A1, PRS-O1A…
_RE_PRS_PREFIJO_INMEDIATO = re.compile(r"(?i)PRS(?:\d{1,3})?[-\s]*$")

# Sufijo de modificación/plano PRMS: RM-PRMS-15-C1, plano RM-PRMS-15-C3 (categoría metropolitana).
_RE_PRMS_MOD_PREFIJO_INMEDIATO = re.compile(r"(?i)(?:RM[-\s]*)?PRMS[-\s]*\d+[-\s]*$")


def _variantes_sufijo_plano_prs(codigo: str) -> list[str]:
    """Variantes OCR O/0 en sufijos de plano (PRS-O1A vs PRS-01A)."""
    u = normalizar_zona((codigo or "").strip())
    if not u:
        return []
    out = {u}
    if len(u) >= 2 and u[0] in "OQ" and u[1].isdigit():
        out.add("0" + u[1:])
    elif len(u) >= 2 and u[0] == "0" and u[1].isdigit():
        out.add("O" + u[1:])
    return list(out)


def _match_es_sufijo_identificador_plano_prs(contenido: str, m: re.Match[str]) -> bool:
    pre = contenido[max(0, m.start() - 24): m.start()]
    return bool(_RE_PRS_PREFIJO_INMEDIATO.search(pre))


def _match_es_sufijo_modificacion_prms(contenido: str, m: re.Match[str]) -> bool:
    """True si el match es Cx en «RM-PRMS-15-Cx» / «plano RM-PRMS-15-Cx», no zona PRC."""
    pre = contenido[max(0, m.start() - 48): m.start()]
    return bool(_RE_PRMS_MOD_PREFIJO_INMEDIATO.search(pre))


def _match_es_sufijo_plano_ps(contenido: str, m: re.Match[str]) -> bool:
    """PS1/PS2 tras código de plano (AH-AM-0496 PS1), no zona PRC."""
    tok = contenido[m.start() : m.end()].strip().upper()
    if not re.fullmatch(r"PS\d{1,2}", tok):
        return False
    pre = contenido[max(0, m.start() - 28) : m.start()]
    if re.search(r"\d{3,5}\s*$", pre):
        return True
    if re.search(r"(?i)(?:plano[s]?|graficad[ao]s|zonificaci[oó]n)\s*[^\n]{0,72}$", pre):
        return True
    if re.search(r"(?i)codigo\s*:?\s*[^\n]{0,48}$", pre):
        return True
    return False


def codigo_es_sufijo_plano_ps(contenido: str, codigo: str) -> bool:
    """True si PS* solo figura como lámina de Plano Seccional, no como zona PRC."""
    nz = normalizar_zona((codigo or "").strip())
    if not re.fullmatch(r"PS\d{1,2}", nz):
        return False
    frag = regex_fragmento_zona_en_fuente(nz)
    if hay_evidencia_zona_tras_zona_keyword(contenido, frag):
        return False
    if re.search(rf"(?m)^#{{1,6}}\s*(?:\*\*)?\s*{re.escape(nz)}\b", contenido, re.I):
        return False
    for m in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(nz)}(?![A-Za-z0-9])", contenido):
        if not _match_es_sufijo_plano_ps(contenido, m):
            return False
    return True


def codigo_aparece_como_sufijo_modificacion_prms(contenido: str, codigo: str) -> bool:
    """¿Aparece como sufijo de identificador de modificación PRMS (RM-PRMS-NN-Cx)?"""
    nz = normalizar_zona((codigo or "").strip())
    if not re.fullmatch(r"[A-H]\d{1,3}", nz):
        return False
    return bool(
        re.search(
            rf"(?i)(?:RM[-\s]*)?PRMS[-\s]*\d+[-\s]*{re.escape(nz)}\b",
            contenido,
        )
    )


def codigo_aparece_en_identificador_plano_prs(contenido: str, codigo: str) -> bool:
    for v in _variantes_sufijo_plano_prs(codigo):
        esc = re.escape(v)
        if re.search(rf"(?i)PRS(?:\d{{1,3}})?[-\s]+{esc}\b", contenido):
            return True
        if re.search(rf"(?i)PRS[-\s]*{esc}\b", contenido):
            return True
    return False


def codigo_es_solo_sufijo_plano_prs(contenido: str, codigo: str) -> bool:
    """
    True si el código solo figura como sufijo de identificador «PRS-…» (lámina de plano),
    sin mención PRC autónoma (ZONA, Sector, celda de tabla de zonificación, etc.).
    """
    if not codigo_aparece_en_identificador_plano_prs(contenido, codigo):
        return False
    nz = normalizar_zona((codigo or "").strip())
    if not nz:
        return False
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    if re.search(
        rf"(?i)\bZona\s+de\s+Conservaci[oó]n\s+Hist[oó]rica\s+{fcs}\b",
        contenido,
    ):
        return False
    if hay_evidencia_zona_tras_zona_keyword(contenido, frag):
        return False
    if re.search(
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
        contenido,
    ):
        return False
    if re.search(rf"(?i)sectores?\s+especiales?\s+{fcs}\b", contenido):
        return False
    if re.search(
        rf"(?i)(?:sub[\s-]*sectores?|subsector)\s+{fcs}\b",
        contenido,
    ):
        return False
    for m in RE_SECT_ESP_PAREJA.finditer(contenido):
        cod_a = normalizar_zona(m.group(1) + m.group(2))
        cod_b = normalizar_zona(m.group(3) + m.group(4))
        if nz == cod_a or nz == cod_b:
            return False
    if re.search(rf"(?<![A-Za-z])ZCH\s+{frag}\b", contenido, re.IGNORECASE):
        return False
    if re.search(rf"(?<![A-Za-z])SE\s+{frag}\b", contenido, re.IGNORECASE):
        return False
    if re.search(rf"(?is)\*\*(?:{frag})\*\*", contenido):
        return False
    for m in RE_ZONAS_ENUM_EFGH.finditer(contenido):
        if nz.upper() in {m.group(i).upper() for i in range(1, 5)}:
            return False
    if re.search(rf"(?is)<li[^>]*>\s*Zona\s+{frag}\s*</li>", contenido):
        return False
    for m in RE_ZONAS_LISTA_COMAS_Y_FINAL.finditer(contenido):
        if nz.upper() in {c.upper() for c in codigos_zona_desde_listado_comas_y(m.group(1))}:
            return False
    if re.search(rf"(?m)(?<=\|)\s*{frag}\s*(?=\|)", contenido):
        return False
    for m in re.finditer(rf"(?<![A-Za-z]){frag}(?![A-Za-z])", contenido):
        if _match_es_sufijo_modificacion_prms(contenido, m):
            continue
        if _match_es_sufijo_plano_ps(contenido, m):
            continue
        if not _match_es_sufijo_identificador_plano_prs(contenido, m):
            return False
    return True


def hay_evidencia_zona_tras_zona_keyword(contenido: str, frag: str) -> bool:
    """
    True si hay al menos una mención «ZONA» + fragmento que no sea solo la remisión tabular
    «…, según PRMS (y O.G.U.C.)» (categoría metropolitana, no código de zona del documento).
    """

    def _no_es_remision_prms(m: re.Match[str]) -> bool:
        tail = contenido[m.end() : m.end() + 220]
        return _RE_REMISION_ZONA_LETRA_TRAS_COMA_PRMS.match(tail) is None

    fcs = frag_codigo_zona_case_sensitive(frag)
    for m in re.finditer(rf"(?<![A-Za-z-])ZONA\s+{fcs}\b", contenido, re.IGNORECASE):
        if _no_es_remision_prms(m):
            return True
    for m in re.finditer(rf"(?<![A-Za-z-])ZONA\s*{fcs}\b", contenido, re.IGNORECASE):
        if _no_es_remision_prms(m):
            return True
    for m in re.finditer(
        rf"(?i)(?<![A-Za-z-])Zona\s+(?:denominada\s+)?{fcs}\b",
        contenido,
    ):
        if _no_es_remision_prms(m):
            return True
    return False


def hay_evidencia_codigo_en_encabezado_normativo(contenido: str, frag: str) -> bool:
    """
    Encabezados e ítems normativos (Iquique: «##### M-10», «- M-1 Industria», «**M-11 …:**»,
    «- SUBZONA A-3**», «<b>BC2-1.1</b>» en tabla de zonificación).
    """
    if re.search(
        rf"(?m)^#{{1,6}}\s*(?:\*\*)?\s*{frag}(?:\*\*)?(?:\s|:|$)",
        contenido,
    ):
        return True
    if re.search(rf"(?m)^\s*[-*]\s*(?:\*\*)?\s*(?:SUB[\s-]*ZONA\s+)?{frag}\b", contenido, re.I):
        return True
    if re.search(rf"(?m)(?:\*\*){frag}(?:\*\*)?\s*[:\*]", contenido):
        return True
    if re.search(rf"(?is)<b[^>]*>\s*{frag}\s*</b>", contenido):
        return True
    if re.search(rf"(?m)(?:\*\*){frag}(?:\*\*)?\s", contenido):
        return True
    return False


def documento_evidencia_prosa_normativa(contenido: str, zona: str) -> bool:
    """
    True si el código aparece en prosa normativa PRC (encabezado «ZONA …», Sector
    Especial/Conservación, listados «… B8, B9 …», etc.).

    No cuenta apariciones sueltas en celdas ``| S10 |`` de tablas cartográficas ni
    menciones aisladas sin encabezado normativo.
    """
    nz = normalizar_zona(zona.strip())
    if not nz or not codigo_zona_tiene_letra(nz):
        return False
    if not codigo_zona_en_mayusculas_en_texto(contenido, nz):
        return False
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    # «Zona de Conservación Histórica A1 - …» (PRC Santiago; subzonas patrimoniales)
    if re.search(
        rf"(?i)\bZona\s+de\s+Conservaci[oó]n\s+Hist[oó]rica\s+{fcs}\b",
        contenido,
    ):
        return True
    if hay_evidencia_zona_tras_zona_keyword(contenido, frag):
        return True
    if hay_evidencia_codigo_en_encabezado_normativo(contenido, frag):
        return True
    if hay_evidencia_zona_en_listados_normativos(contenido, nz):
        return True
    if re.search(
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
        contenido,
    ):
        return True
    if re.search(rf"(?i)\bSector\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?i)sectores?\s+especiales?\s+{fcs}\b", contenido):
        return True
    if re.search(
        rf"(?im)^\s*(?:#{{1,6}}\s*)?(?:sub[\s-]*(?:sectores?|zonas?)|subsector|subzona)"
        rf"\s+(?:ZONA\s+)?{fcs}\b",
        contenido,
    ):
        return True
    # Encabezados tipo «Sectores Especiales C1 y C2» (el código no va pegado a «Especiales»).
    for m in RE_SECT_ESP_PAREJA.finditer(contenido):
        cod_a = normalizar_zona(m.group(1) + m.group(2))
        cod_b = normalizar_zona(m.group(3) + m.group(4))
        if nz == cod_a or nz == cod_b:
            return True
    if re.search(rf"(?<![A-Za-z])ZCH\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?<![A-Za-z])SE\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?is)\*\*(?:{fcs})\*\*", contenido):
        return True
    for m in RE_ZONAS_ENUM_EFGH.finditer(contenido):
        if nz.upper() in {m.group(i).upper() for i in range(1, 5)}:
            return True
    if re.search(rf"(?is)<li[^>]*>\s*Zona\s+{fcs}\s*</li>", contenido):
        return True
    for m in RE_ZONAS_LISTA_COMAS_Y_FINAL.finditer(contenido):
        if nz.upper() in {c.upper() for c in codigos_zona_desde_listado_comas_y(m.group(1))}:
            return True
    return False


def documento_evidencia_codigo_zona(contenido: str, zona: str) -> bool:
    """True si el documento menciona el código de zona de forma equiparable al descubrimiento."""
    nz = normalizar_zona(zona.strip())
    if not nz or not codigo_zona_tiene_letra(nz):
        return False
    if documento_evidencia_prosa_normativa(contenido, zona):
        return True
    frag = regex_fragmento_zona_en_fuente(nz)

    # Zonas A–H (una letra): solo encabezado ZONA/Sector o celda | E | sin UTM en la fila.
    if es_zona_urbana_letra_a_h(nz):
        for m in re.finditer(rf"(?m)(?<=\|)\s*{re.escape(nz)}\s*(?=\|)", contenido):
            line_start = contenido.rfind("\n", 0, m.start()) + 1
            line_end = contenido.find("\n", m.end())
            line = contenido[line_start : line_end if line_end >= 0 else len(contenido)]
            if _linea_contiene_utm(line):
                continue
            return True
        return False

    # Celda de tabla Markdown: | Z3 | … | (sin la palabra «ZONA» en la misma celda).
    for m in re.finditer(rf"(?m)(?<=\|)\s*{frag}\s*(?=\|)", contenido):
        line_start = contenido.rfind("\n", 0, m.start()) + 1
        line_end = contenido.find("\n", m.end())
        line = contenido[line_start : line_end if line_end >= 0 else len(contenido)]
        if _linea_contiene_utm(line):
            continue
        return True
    # Lista / normas «- M-1 Industria**», «M - 2 Tirana» (case-sensitive; no m2 ni UTM E =).
    for m in re.finditer(rf"(?<![A-Za-z0-9]){frag}(?![A-Za-z0-9])", contenido):
        if _match_es_numeral_o_estructura_no_zona(contenido, m):
            continue
        if _match_es_coordenada_utm(contenido, m):
            continue
        if _match_es_sufijo_modificacion_prms(contenido, m):
            continue
        if _match_es_sufijo_plano_ps(contenido, m):
            continue
        if not _match_es_sufijo_identificador_plano_prs(contenido, m):
            return True
    return False


def _linea_es_fila_tabla_md(line: str) -> bool:
    s = (line or "").strip()
    return s.startswith("|") and s.count("|") >= 2


def extraer_tabla_markdown_en_posicion(contenido: str, pos: int) -> str | None:
    """Tabla markdown completa que contiene la posición *pos* (inclusive)."""
    if not contenido or pos < 0:
        return None
    pos = min(pos, max(0, len(contenido) - 1))
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    if not _linea_es_fila_tabla_md(contenido[line_start:line_end]):
        return None
    lines = contenido.splitlines(keepends=True)
    acc = 0
    idx = 0
    for i, ln in enumerate(lines):
        if acc <= pos < acc + len(ln):
            idx = i
            break
        acc += len(ln)
    i0 = idx
    while i0 > 0 and _linea_es_fila_tabla_md(lines[i0 - 1]):
        i0 -= 1
    i1 = idx
    while i1 + 1 < len(lines) and _linea_es_fila_tabla_md(lines[i1 + 1]):
        i1 += 1
    return "".join(lines[i0 : i1 + 1])


def _nivel_heading_markdown_line(line: str) -> int | None:
    m = re.match(r"^(#{1,6})\s", (line or "").lstrip())
    return len(m.group(1)) if m else None


# Talca / PRC: Z-*, ZE-*, ZR-*, U-* (urbanas), R-* (riesgo), p. ej. PRCT 2011.
_RE_ABRE_ZONA_PREFIJO_Z = re.compile(
    r"^(?:Zona\s+)?"
    r"(?:"
    r"Z[\s\-—–‑]*(?:\d+|[A-Z](?:I)?|D)\b"
    r"|Z(?:E|R|U)[\s\-—–‑]+(?:\d+|[A-Z](?:I)?)\b"
    r"|Z(?:E|R|U)\d+\b"
    r"|[UR][\s\-—–‑]+\d+(?:\s+[A-Z])?\b"
    r"|[UR]\d+[A-Z]?\b"
    r"|[M][\s\-—–‑]+\d+(?:\s*[\-—–‑]\s*\d+)?\b"
    r"|[M]\d+\b"
    r")",
    re.IGNORECASE,
)

_RE_ITEM_LISTA_ZONA_PRC = re.compile(
    r"^\s*-\s*(?:(?:Sub[\s-]*zonas?|Subzona)\s+)?"
    r"(?:Zona\s+)?(?:Z(?:E|R|U)?|[A-ZURM])[\s\-—–‑]*\d",
    re.IGNORECASE,
)

_RE_ARTICULO_ZONIFICACION = re.compile(
    r"zonificaci[oó]n",
    re.IGNORECASE,
)

_RE_SUBSECCION_LETRA_NORMATIVA = re.compile(
    r"^[A-Z]\.\s*(?:[—\-]|\*\*)",
    re.IGNORECASE,
)


def _linea_texto_titulo_sin_hashes(line: str) -> str:
    s = (line or "").strip()
    s = re.sub(r"^#{1,6}\s*", "", s)
    s = re.sub(r"^\*\*", "", s)
    s = re.sub(r"\*\*$", "", s)
    return s.strip()


def _linea_abre_zona_prefijo_z(line: str) -> bool:
    """True si la línea abre una zona Z / ZE / ZR / U / R (no subsección «B.— Condiciones»)."""
    inner = _linea_texto_titulo_sin_hashes(line)
    if not inner or _RE_SUBSECCION_LETRA_NORMATIVA.match(inner):
        return False
    return _RE_ABRE_ZONA_PREFIJO_Z.match(inner) is not None


def _linea_es_item_lista_zona_prc(line: str) -> bool:
    """Ítem de catálogo: «- U-10 …», «- R-3 …», «  - Subzona R-3 A»."""
    return _RE_ITEM_LISTA_ZONA_PRC.match(line or "") is not None


def _linea_es_solo_titulo_zona_plano(line: str) -> bool:
    """Título de zona sin markdown: «Z-7», «ZE-2», «Z-D» en una línea."""
    inner = (line or "").strip()
    inner = re.sub(r"^\*\*", "", inner)
    inner = re.sub(r"\*\*$", "", inner)
    if not inner or " " in inner.strip():
        return False
    return _RE_ABRE_ZONA_PREFIJO_Z.fullmatch(inner) is not None


def extraer_seccion_markdown_desde_posicion(contenido: str, pos: int) -> str | None:
    """
    Sección bajo un encabezado markdown (# … ######) que contiene *pos*.

    Si el encabezado abre una zona Z/ZE/ZR (p. ej. «#### Z-1»), incluye subsecciones
    «#### B.— Condiciones…» hasta la siguiente zona, no hasta el primer #### genérico.
    """
    if not contenido or pos < 0:
        return None
    pos = min(pos, max(0, len(contenido) - 1))
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    line = contenido[line_start:line_end]
    nivel = _nivel_heading_markdown_line(line)
    if nivel is None:
        return None
    lines = contenido.splitlines(keepends=True)
    acc = 0
    idx = 0
    for i, ln in enumerate(lines):
        if acc <= pos < acc + len(ln):
            idx = i
            break
        acc += len(ln)
    else:
        return None
    seccion_z = _linea_abre_zona_prefijo_z(lines[idx])
    out = [lines[idx]]
    for j in range(idx + 1, len(lines)):
        ln = lines[j]
        if seccion_z:
            if _linea_abre_zona_prefijo_z(ln) or _linea_es_solo_titulo_zona_plano(ln):
                break
            out.append(ln)
            continue
        n2 = _nivel_heading_markdown_line(ln)
        if n2 is not None and n2 <= nivel:
            break
        out.append(ln)
    return "".join(out)


def extraer_bloque_catalogo_zonificacion(contenido: str, pos: int) -> str | None:
    """
    Catálogo del Artículo de zonificación (listas U-1…, R-1… bajo ####/#####).
    Incluye el encabezado «Zonificación» para validar keywords en el listado índice.
    """
    if not contenido or pos < 0:
        return None
    pos = min(pos, max(0, len(contenido) - 1))
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    line = contenido[line_start:line_end]
    if not _linea_es_item_lista_zona_prc(line):
        inner = line.strip()
        if not re.search(
            r"(?i)(?:sub[\s-]*zonas?|subzona)\s+[UR][\s\-—–‑]*\d",
            inner,
        ):
            return None
    lines = contenido.splitlines(keepends=True)
    acc = 0
    idx = 0
    for i, ln in enumerate(lines):
        if acc <= line_start < acc + len(ln):
            idx = i
            break
        acc += len(ln)
    else:
        return None
    # Subir al encabezado más alto del catálogo (### normas urbanísticas, #### Art. 21, ##### áreas).
    anclas: list[int] = []
    for j in range(idx, -1, -1):
        ln = lines[j]
        inner = _linea_texto_titulo_sin_hashes(ln)
        niv = _nivel_heading_markdown_line(ln)
        if niv is not None and niv <= 4 and _RE_ARTICULO_ZONIFICACION.search(inner):
            anclas.append(j)
        if niv == 3 and re.search(r"(?i)zonific|normas\s+urban", inner):
            anclas.append(j)
        if niv == 5 and re.search(
            r"(?i)áreas?\s+urbanas|áreas?\s+de\s+riesgo|áreas?\s+restringidas",
            inner,
        ):
            anclas.append(j)
    sec_ini = min(anclas) if anclas else idx
    out = list(lines[sec_ini : idx + 1])
    for j in range(idx + 1, len(lines)):
        ln = lines[j]
        if re.match(r"^\{[0-9]+\}-+\s*$", ln.strip()):
            break
        niv = _nivel_heading_markdown_line(ln)
        if niv is not None and niv <= 4 and j > idx:
            inner = _linea_texto_titulo_sin_hashes(ln)
            if _RE_ARTICULO_ZONIFICACION.search(inner) or niv < 4:
                break
            if niv == 4 and not _linea_es_item_lista_zona_prc(ln):
                if not re.search(
                    r"(?i)áreas?\s+urbanas|áreas?\s+de\s+riesgo|áreas?\s+restringidas|monumentos",
                    inner,
                ):
                    break
        out.append(ln)
    bloque = "".join(out)
    if _RE_ARTICULO_ZONIFICACION.search(bloque):
        return bloque
    if re.search(r"(?i)normas\s+urban", bloque):
        return bloque
    return None


def extraer_bloque_zona_titulo_plano(contenido: str, pos: int) -> str | None:
    """
    Bloque bajo título de zona sin «#» (p. ej. «Z-7» en Talca 1990) hasta la siguiente zona.
    """
    if not contenido or pos < 0:
        return None
    pos = min(pos, max(0, len(contenido) - 1))
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    line = contenido[line_start:line_end]
    if not _linea_es_solo_titulo_zona_plano(line) and not _linea_abre_zona_prefijo_z(line):
        return None
    lines = contenido.splitlines(keepends=True)
    acc = 0
    idx = 0
    for i, ln in enumerate(lines):
        if acc <= line_start < acc + len(ln):
            idx = i
            break
        acc += len(ln)
    else:
        return None
    out = [lines[idx]]
    for j in range(idx + 1, len(lines)):
        ln = lines[j]
        if _linea_abre_zona_prefijo_z(ln) or _linea_es_solo_titulo_zona_plano(ln):
            break
        if re.match(r"^\{[0-9]+\}-+\s*$", ln.strip()):
            break
        out.append(ln)
    return "".join(out)


_RE_CITA_NORMA_TRAS_ZONA = re.compile(
    r"(?:"
    r"por\s+el\s+siguiente\s*:"
    r"|el\s+texto\s+donde\s+dice\s*:"
    r"|el\s+texto\s+del\s+punto[^:\n]{0,120}por\s+el\s+siguiente\s*:"
    r"|por\s+lo\s+siguiente\s*(?:nuevo\s+texto\s*)?:"
    r"|reempl[aá]zase\s+por\s+lo\s+siguiente\s*(?:nuevo\s+texto\s*)?:"
    r")",
    re.I,
)


def _bloque_tras_por_el_siguiente(contenido: str, pos: int) -> str | None:
    """Párrafo de cita + viñetas inmediatas tras fórmulas típicas de MOD/decreto."""
    if not contenido or pos < 0:
        return None
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    parrafo = contenido[line_start:line_end]
    if not _RE_CITA_NORMA_TRAS_ZONA.search(parrafo):
        return None
    rest = contenido[line_end:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    partes: list[str] = [parrafo]
    en_cuerpo = False
    blanks_seguidos = 0
    for ln in rest.splitlines(keepends=True):
        st = ln.strip()
        if not st:
            blanks_seguidos += 1
            if en_cuerpo and blanks_seguidos >= 2:
                break
            continue
        blanks_seguidos = 0
        if _nivel_heading_markdown_line(ln) is not None:
            break
        if st.startswith("|") and st.count("|") >= 2:
            break
        if re.match(r"^\{[0-9]+\}-+\s*$", st):
            break
        if en_cuerpo and re.match(r"^\d{1,3}\.\s", st):
            break
        en_cuerpo = True
        partes.append(ln)
        if len("".join(partes)) > 8000:
            break
    return "".join(partes) if en_cuerpo else parrafo


def extraer_bloque_prosa_en_posicion(
    contenido: str,
    pos: int,
    *,
    max_chars: int = 8000,
) -> str:
    """Párrafo(s) entre líneas en blanco que contienen *pos* (sin tablas)."""
    if not contenido or pos < 0:
        return ""
    pos = min(pos, max(0, len(contenido) - 1))
    line_start = contenido.rfind("\n", 0, pos) + 1
    line_end = contenido.find("\n", pos)
    if line_end < 0:
        line_end = len(contenido)
    if _linea_es_fila_tabla_md(contenido[line_start:line_end]):
        return contenido[line_start:line_end]
    bloque_ini = contenido.rfind("\n\n", 0, line_start)
    bloque_ini = 0 if bloque_ini < 0 else bloque_ini + 2
    bloque_fin = contenido.find("\n\n", line_end)
    if bloque_fin < 0:
        bloque_fin = len(contenido)
    bloque = contenido[bloque_ini:bloque_fin]
    if len(bloque) > max_chars:
        rel = pos - bloque_ini
        half = max_chars // 2
        ini = max(0, rel - half)
        bloque = bloque[ini : ini + max_chars]
    return bloque


def bloque_contexto_para_posicion(contenido: str, pos: int) -> str:
    """
    Bloque normativo que contextualiza una mención de zona:
    tabla markdown completa, sección bajo encabezado ####/#####, cita
    «por el siguiente:» + viñetas, o párrafo de prosa.
    """
    tabla = extraer_tabla_markdown_en_posicion(contenido, pos)
    if tabla:
        return tabla
    catalogo = extraer_bloque_catalogo_zonificacion(contenido, pos)
    if catalogo:
        return catalogo
    seccion = extraer_seccion_markdown_desde_posicion(contenido, pos)
    if seccion:
        return seccion
    bloque_z = extraer_bloque_zona_titulo_plano(contenido, pos)
    if bloque_z:
        return bloque_z
    cita = _bloque_tras_por_el_siguiente(contenido, pos)
    if cita:
        return cita
    return extraer_bloque_prosa_en_posicion(contenido, pos)


def _span_contiene_codigo_mayusculas(
    contenido: str,
    start: int,
    end: int,
    nz: str,
) -> bool:
    """True si el fragmento matched contiene el código en MAYÚSCULAS (no «zona a»)."""
    ventana = contenido[start:end]
    if not ventana.strip():
        return False
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    if re.search(rf"{fcs}", ventana):
        return True
    return re.search(rf"(?m)(?<=\|)\s*{re.escape(nz)}\s*(?=\|)", ventana) is not None


def _evidencia_zona_letra_a_h_en_texto(contenido: str, nz: str) -> bool:
    """
    Zonas macro A–H: encabezado ZONA/Sector o celda | A | en tabla normativa.
    No «A» de «Año», ni «E»/«N» de coordenadas UTM.
    """
    if not es_zona_urbana_letra_a_h(nz):
        return False
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    if re.search(rf"(?i)(?<![A-Za-z])ZONA\s+{fcs}\b", contenido):
        return True
    if re.search(rf"(?i)(?<![A-Za-z])ZONAS\s+{fcs}\b", contenido):
        return True
    if re.search(
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
        contenido,
    ):
        return True
    if re.search(rf"(?i)sectores?\s+especiales?\s+{fcs}\b", contenido):
        return True
    for m in re.finditer(rf"(?m)(?<=\|)\s*{re.escape(nz)}\s*(?=\|)", contenido):
        line_start = contenido.rfind("\n", 0, m.start()) + 1
        line_end = contenido.find("\n", m.end())
        line = contenido[line_start : line_end if line_end >= 0 else len(contenido)]
        if _linea_contiene_utm(line):
            continue
        return True
    return False


def codigo_zona_en_mayusculas_en_texto(contenido: str, zona: str) -> bool:
    """
    True si el código aparece en el texto fuente con letras en MAYÚSCULAS
    (p. ej. «SE B15b2» no cuenta como zona B15B2).

    Zonas A–H (una letra): exige evidencia PRC explícita (ZONA/Sector/celda de tabla),
    no «A» en «Año» ni «E» en coordenadas UTM.
    """
    nz = normalizar_zona((zona or "").strip())
    if not nz or not (contenido or "").strip():
        return False
    contenido_busqueda = unificar_guiones_do(contenido)
    if es_zona_urbana_letra_a_h(nz):
        return _evidencia_zona_letra_a_h_en_texto(contenido_busqueda, nz)
    for start, end in iter_spans_evidencia_codigo_zona(contenido_busqueda, nz, max_spans=8):
        if _span_contiene_codigo_mayusculas(contenido, start, end, nz):
            return True
    frag = regex_fragmento_zona_en_fuente(nz)
    fcs = frag_codigo_zona_case_sensitive(frag)
    for m in re.finditer(rf"(?<![A-Za-z0-9]){fcs}(?![A-Za-z0-9])", contenido_busqueda):
        if _match_es_coordenada_utm(contenido, m):
            continue
        if _match_es_numeral_o_estructura_no_zona(contenido, m):
            continue
        if _match_es_sufijo_plano_ps(contenido, m):
            continue
        return True
    if re.search(rf"(?m)(?<=\|)\s*{re.escape(nz)}\s*(?=\|)", contenido_busqueda):
        return True
    return False


def documento_evidencia_subsector_prc(contenido: str, zona: str) -> bool:
    """
    True si el código figura como Sub-Sector / Subsector «D - 1 A» en el PRC
    (catálogo seccional; no exige keyword normativa en el mismo bloque).
    """
    nz = normalizar_zona((zona or "").strip())
    m = re.fullmatch(r"([A-Z])(\d{1,3})([A-Z])?", nz)
    if not m:
        return False
    letra, digs, suf = m.group(1), m.group(2), m.group(3)
    texto = contenido or ""
    for rx in (RE_SUBSECTOR_CODIGO, RE_SUBSECTOR_LINEA_USO):
        for hit in rx.finditer(texto):
            g1 = hit.group(1) or ""
            if g1 != letra or hit.group(2) != digs:
                continue
            if g1 != g1.upper():
                continue
            hit_suf = (hit.group(3) or "").strip()
            if suf:
                if hit_suf == suf and hit_suf == hit_suf.upper():
                    return True
            elif not hit_suf:
                return True
    return False


def codigo_es_identificador_plano_prm(contenido: str, codigo: str) -> bool:
    """RM-PRM99-CH… / Plano: RM-PRM99 — identificador de lámina PRM, no zona PRC."""
    nz = normalizar_zona((codigo or "").strip())
    if not re.fullmatch(r"PRM\d{1,3}", nz):
        return False
    return bool(
        re.search(
            rf"(?i)(?:plano\s*:?\s*)?(?:RM[-\s]*)?{re.escape(nz)}(?:[-.][A-Z0-9]+)*\b",
            contenido,
        )
    )


def codigo_es_codigo_vial_tabla_prms(contenido: str, codigo: str) -> bool:
    """
    C17O, T57O, etc. en tablas del PRMS (Colectora/Troncal) — vialidad, no zonificación.
    """
    nz = normalizar_zona((codigo or "").strip())
    if not re.fullmatch(r"[A-Z]\d{1,2}O", nz):
        return False
    esc = re.escape(nz)
    if re.search(
        rf"(?is)\|[^\n|]*{esc}[^\n|]*\|[^\n|]*(?:colectora|troncal|arteria|vialidad)",
        contenido,
    ):
        return True
    if re.search(rf"(?is){esc}(?:<br>)?\s*\(PRMS\)", contenido):
        return True
    if re.search(
        rf"(?is){esc}[^\n|]{{0,80}}(?:colectora|troncal|PRMS)",
        contenido,
    ):
        return True
    return False


def codigo_es_solo_plano_dgac_pp(contenido: str, codigo: str) -> bool:
    """PP-97-H01, Plano D.G.A.C. … — lámina DGAC, no código de zona del PRC."""
    nz = normalizar_zona((codigo or "").strip())
    if not re.fullmatch(r"[A-Z]\d{2}", nz):
        return False
    esc = re.escape(nz)
    if re.search(rf"(?i)PP-\d+-{esc}\b", contenido):
        return True
    if re.search(
        rf"(?i)D\.?\s*G\.?\s*A\.?\s*C\.?[^\n]{{0,120}}PP-[^\s,]+-{esc}\b",
        contenido,
    ):
        return True
    if re.search(rf"(?i)plano\s+D\.?\s*G\.?\s*A\.?\s*C\.?[^\n]{{0,80}}{esc}\b", contenido):
        return True
    return False


def zona_cumple_evidencia_mayuscula_y_keyword_bloque(
    contenido: str,
    zona: str,
    *,
    chunk_text: str | None = None,
    chunk_global_start: int | None = None,
) -> bool:
    """
    True si el código aparece en MAYÚSCULAS y el bloque que lo contiene
    (tabla completa o párrafo de prosa) incluye al menos una keyword normativa del CSV.
    """
    from utils.keywords_normativa import texto_tiene_keyword_normativa

    nz = normalizar_zona((zona or "").strip())
    if not nz or not codigo_zona_tiene_letra(nz):
        return False

    base_doc = contenido if contenido else (chunk_text or "")
    if documento_evidencia_subsector_prc(base_doc, nz):
        return True

    scope = chunk_text if chunk_text is not None else contenido
    base_doc = contenido if contenido else scope
    if not (scope or "").strip():
        return False
    g0 = int(chunk_global_start or 0)

    for start, end in iter_spans_evidencia_codigo_zona(scope, nz):
        if not _span_contiene_codigo_mayusculas(scope, start, end, nz):
            continue
        pos_global = g0 + start
        bloque = bloque_contexto_para_posicion(base_doc, pos_global)
        if texto_tiene_keyword_normativa(bloque):
            return True
    return False


def documento_tiene_bloque_normativo_zona(contenido: str, zona: str) -> bool:
    """
    True si el código tiene un bloque normativo urbanístico en *este* documento
    (encabezado ZONA/Sector + parámetros, o fila de tabla de zonificación), no solo
    una mención incidental («Modifíquese la Zona B» al citar otra norma).
    """
    nz = normalizar_zona((zona or "").strip())
    if not nz or not codigo_zona_tiene_letra(nz):
        return False

    frag = regex_fragmento_zona_en_fuente(nz)
    patron_estricto, patron_relajado, patron_sector = compilar_patrones_posicion_zona(frag)

    # Keywords / señales de "sección de zona" (no depende de headings Markdown).
    for patron in (patron_estricto, patron_relajado):
        for m in patron.finditer(contenido):
            ventana = contenido[m.end() : m.end() + 600]
            if RE_MARCADORES_SECCION_ZONA.search(ventana):
                return True
            if RE_NORMA_SECCION.search(ventana[:300]):
                return True

    for m in patron_sector.finditer(contenido):
        if RE_NORMA_SECCION.search(contenido[m.end() : m.end() + 300]):
            return True

    pat_inline = compilar_patron_sectores_especiales_inline(frag)
    for m in pat_inline.finditer(contenido):
        if RE_NORMA_SECCION.search(contenido[m.end() : m.end() + 300]):
            return True

    # Tabla de emplazamiento / parámetros: cabecera normativa y fila con código + valor numérico.
    if re.search(
        rf"(?is)\|[^\n]*(?:emplazamiento|superficie|altura|agrupamiento|coeficiente)[^\n]*\|"
        rf"(?:[^\n|]*\|){{0,120}}?"
        rf"\|[^\n]*\b{re.escape(nz)}\b[^\n]*\|[^\n]*\d",
        contenido,
    ):
        return True

    return False


def compilar_patrones_posicion_zona(frag: str) -> tuple[
    Pattern[str],
    Pattern[str],
    Pattern[str],
]:
    """Patrones ZONA (estricto/relajado) y SECTOR para localizar encabezado."""
    fcs = frag_codigo_zona_case_sensitive(frag)
    patron_estricto = re.compile(
        rf"(?i)(?<![A-Za-z])ZONA\s*{fcs}\s*(?:\n|[:\.]\s)",
    )
    patron_relajado = re.compile(
        rf"(?i)(?<![A-Za-z])ZONA\s*{fcs}(?!\w)",
    )
    patron_sector = re.compile(
        rf"(?i)(?:Sector|Sectores)\s+(?:de\s+)?(?:Conservaci[oó]n|Especial)\s+{fcs}\b",
    )
    return patron_estricto, patron_relajado, patron_sector


def compilar_patron_sectores_especiales_inline(frag: str) -> Pattern[str]:
    fcs = frag_codigo_zona_case_sensitive(frag)
    return re.compile(rf"(?i)sectores?\s+especiales?\s+{fcs}\b")


def compilar_patron_codigo_suelto(frag: str) -> Pattern[str]:
    """Código suelto en mayúsculas (no matchear preposiciones ni palabras comunes)."""
    return re.compile(rf"(?<![A-Za-z0-9]){frag}(?![A-Za-z0-9])")


def zona_merge_sort_key(z: str) -> tuple:
    m = CPAT_ZONA_SORT.match(z)
    if m:
        return (m.group(1).upper(), int(m.group(2)) if m.group(2) else 0)
    return (z.upper(), 0)


def numero_decreto_sin_separador_miles(raw: str) -> str:
    s = raw.strip().replace(" ", "")
    if re.fullmatch(r"\d+", s):
        return str(int(s))
    if re.fullmatch(r"\d+\.\d{3}", s):
        return s.replace(".", "")
    if s.replace(".", "").isdigit():
        return s.replace(".", "")
    return raw.strip()


def documento_menciona_decreto_numero(contenido: str, num: str) -> bool:
    if not contenido or not num:
        return False
    n = numero_decreto_sin_separador_miles(str(num))
    if not n.isdigit():
        return True
    ne = re.escape(n)
    return bool(
        re.search(
            rf"(?is)(?:d\.?\s*s\.?(?:\s*u\.?)?|decreto\s+supremo(?:\s+exento)?)"
            rf".{{0,160}}?(?:n\s*[°º]?\s*)?{ne}\b",
            contenido,
        )
        or re.search(
            rf"(?is)(?:n\s*[°º]?\s*){ne}\b"
            rf".{{0,160}}?(?:d\.?\s*s\.?(?:\s*u\.?)?|decreto\s+supremo)",
            contenido,
        )
    )


def strip_llm_json_code_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        t = RE_FENCE_OPEN.sub("", t)
        t = RE_FENCE_CLOSE.sub("", t)
    return t


def eval_norm_txt_cmp(s: str) -> str:
    t = s.lower()
    t = CPAT_COLAPSAR_WS.sub(" ", t)
    for a, b in (("n°", "n"), ("nº", "n"), ("°", ""), ("¿", "")):
        t = t.replace(a, b)
    t = RE_EVAL_NORM_TXT_NO_ALNUM.sub(" ", t)
    return CPAT_COLAPSAR_WS.sub(" ", t).strip()


def eval_norm_agrup(s: str) -> str:
    t = CPAT_COLAPSAR_WS.sub(" ", s).strip().lower()
    t = t.replace(", ", "/").replace(" o ", "/").replace(" y ", "/")
    t = t.replace(",", "/")
    return t


def sanitizar_texto_control_api(s: str) -> str:
    if not s:
        return ""
    return RE_CONTROL_API.sub(" ", s)


def eval_extraer_numero_ds(s: str) -> int | None:
    m = RE_DS_NUMERO.search(s)
    if not m:
        return None
    return int(m.group(1).replace(".", ""))


def stem_resultado_sin_prefijo_ts(stem: str) -> str:
    m = RE_STEM_PREFIJO_TS_RESULTADO.match(stem)
    return m.group(1) if m else stem


def buscar_sector_conservacion_o_especial(contenido: str, nz: str):
    """Primera aparición de encabezado sectorial para una subzona."""
    directo = re.search(
        rf"(?is)\b(?:Sector\s+de\s+Conservación|Sector\s+Especial)\s+{re.escape(nz)}\b",
        contenido,
    )
    if directo:
        return directo
    for m in RE_SECT_ESP_PAREJA.finditer(contenido):
        cod_a = normalizar_zona(m.group(1) + m.group(2))
        cod_b = normalizar_zona(m.group(3) + m.group(4))
        if nz == cod_a or nz == cod_b:
            return m
    return None


def cita_menciona_coeficiente_o_far(cita: str) -> bool:
    return bool(RE_CITA_COEFICIENTE_O_FAR.search(cita or ""))
