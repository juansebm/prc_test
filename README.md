# prc_test — prueba técnica (~15 min)

Filtro técnico corto: clonar, levantar un entorno local y abrir una app web.
El CSV no una tarea de anotación larga.

## Entregable

Copia `plantilla/zonas_agrupamiento.csv` → `entregable/zonas_agrupamiento.csv` y completa `sistema_agrupamiento` de la zona **C** en 1990 / 1992 / 1996.

Separador `;`. No cambies columnas ni años.

## Setup

Clonar el repositorio y activar el entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

```bash
pip install -r requirements.txt
```

## Qué hacer

Luego, ejecutar:

```bash
python scripts/run_visualizador.py
```

Abre la URL que imprime la consola → comuna **SANTIAGO** → los 3 markdowns.
Rellena el CSV (notas abajo) y entrega `entregable/zonas_agrupamiento.csv`.

## Notas metodológicas (CSV)

- Solo zona **C** (código alfanumérico). Ignora sectores/subzonas (C1, C2, C3, “Sector Especial…”, etc.).
- Año = prefijo `YYYY_` del archivo. Una fila por año.
- La notación para Agrupamiento debe ser de la forma: `Aislado` / `Pareado` / `Continuo`. Unir solo con `/` (sin "y", "o", comas). Capitalizar.
  - `"Aislado, Pareado o Continuo"` → `Aislado/Pareado/Continuo`

## Reglas

- El único script a correr: `scripts/run_visualizador.py` (exige `.env`).
- Sin LLM.
