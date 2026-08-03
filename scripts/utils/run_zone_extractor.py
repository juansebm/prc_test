"""Corre zone_extractor local sobre los 3 markdowns → outputs/zonas.csv."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from utils.zone_extractor import (  # noqa: E402
    _filtrar_contenido_prc,
    descubrir_zonas,
    eliminar_marcadores_paginacion_markdown,
)

DATA = ROOT / "data" / "datalab_markdown"
OUT = ROOT / "outputs" / "zonas.csv"
ZONA_OBJETIVO = "C"
_YEAR_RE = re.compile(r"^(\d{4})_")


def _mds() -> list[Path]:
    files = sorted(DATA.rglob("*.md"))
    if len(files) != 3:
        raise SystemExit(f"Se esperan 3 .md bajo {DATA}, hay {len(files)}")
    return files


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    filas: list[tuple[str, str]] = []

    for md in _mds():
        m = _YEAR_RE.match(md.name)
        if not m:
            raise SystemExit(f"Nombre sin año YYYY_: {md.name}")
        ano = m.group(1)
        es_mod = "modificaciones" in md.parts
        print(f"\n--- {ano} · {md.name} ---")
        raw = md.read_text(encoding="utf-8", errors="replace")
        contenido = eliminar_marcadores_paginacion_markdown(
            _filtrar_contenido_prc(raw),
        )
        zonas = descubrir_zonas(contenido, es_modificacion=es_mod)
        print(f"  {len(zonas)} zona(s)")
        for z in zonas:
            filas.append((ano, z))

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ano", "zona"])
        for ano, z in filas:
            w.writerow([ano, z])

    anos_c = sorted({ano for ano, z in filas if z == ZONA_OBJETIVO})
    print(f"\nTotal filas: {len(filas)}")
    print(f"{ZONA_OBJETIVO} en años: {', '.join(anos_c) or '(ninguno)'}")
    print(f"salida={OUT}")
    print(
        f"Siguiente: escribe entregable/zonas_agrupamiento.csv "
        f"({ZONA_OBJETIVO} + sistema_agrupamiento + ano)."
    )


if __name__ == "__main__":
    main()
