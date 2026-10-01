"""
Junta todos los CSV diarios de la carpeta precios/ en un solo archivo.

Este archivo (historial_completo.csv) se puede borrar y volver a generar.
Los CSV por fecha y tienda son la fuenNte principal.
"""

from __future__ import annotations

import csv
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
CARPETA_PRECIOS = CARPETA / "precios"
ARCHIVO_SALIDA = CARPETA / "historial_completo.csv"

COLUMNAS = [
    "fecha",
    "hora",
    "tienda",
    "nombre",
    "enlace",
    "precio_actual",
    "precio_normal",
    "hay_stock",
    "cantidad",
    "imagen",
]


def es_carpeta_anio(ruta: Path) -> bool:
    """Una carpeta de año se llama 2026, 2027, etc."""
    return ruta.is_dir() and ruta.name.isdigit() and len(ruta.name) == 4


def csv_diarios() -> list[Path]:
    """
    Recorre precios/año/ y junta los CSV de cada año.
    Ejemplo: precios/2026/airsoftgames_2026-09-19.csv
    Ignora archivos temporales y carpetas que no sean un año.
    """
    if not CARPETA_PRECIOS.exists():
        return []

    archivos: list[Path] = []
    for carpeta_anio in sorted(CARPETA_PRECIOS.iterdir()):
        if not es_carpeta_anio(carpeta_anio):
            continue
        for ruta in sorted(carpeta_anio.glob("*.csv")):
            if ruta.name.endswith(".tmp"):
                continue
            archivos.append(ruta)
    return archivos


def leer_filas(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def main() -> None:
    archivos = csv_diarios()
    if not archivos:
        print("No hay CSV en la carpeta precios/. Nada que juntar.")
        return

    filas: list[dict] = []
    for ruta in archivos:
        filas.extend(leer_filas(ruta))

    filas.sort(
        key=lambda fila: (
            fila.get("fecha") or "",
            fila.get("hora") or "",
            fila.get("tienda") or "",
            fila.get("nombre") or "",
        )
    )

    with ARCHIVO_SALIDA.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)

    print(f"Se juntaron {len(filas)} filas desde {len(archivos)} archivos.")
    print(f"Salida:\n{ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()
