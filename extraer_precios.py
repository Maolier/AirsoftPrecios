"""
Script principal del historial de precios.

Lee la lista de tiendas, usa el lector de cada plataforma y guarda
un CSV por tienda y por día, dentro de una carpeta del año.
Si se corre de nuevo el mismo día, reescribe solo el archivo de esa tienda.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from lectores import bsale, prestashop, wix, woocommerce

CARPETA = Path(__file__).resolve().parent
ARCHIVO_TIENDAS = CARPETA / "tiendas.json"
CARPETA_PRECIOS = CARPETA / "precios"

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

# Qué lector usar según el campo "plataforma" de tiendas.json
LECTORES = {
    "woocommerce": woocommerce.extraer,
    "bsale": bsale.extraer,
    "prestashop": prestashop.extraer,
    "wix": wix.extraer,
}

# Prueba: 5 productos por tienda. Pon 0 para leer el catálogo completo.
LIMITE_PRUEBA = 0


def cargar_tiendas() -> list[dict]:
    """Lee la lista de tiendas desde el archivo JSON."""
    with ARCHIVO_TIENDAS.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def ruta_csv_tienda(nombre_tienda: str, fecha_hoy: str) -> Path:
    """precios/2026/airsoftgames_2026-09-19.csv"""
    anio = fecha_hoy[:4]
    return CARPETA_PRECIOS / anio / f"{nombre_tienda}_{fecha_hoy}.csv"


def guardar_tienda(filas: list[dict], ruta: Path) -> None:
    """
    Escribe primero un archivo temporal y, si sale bien, lo pone en el lugar.
    Si algo falla a mitad de camino, el CSV anterior queda intacto.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".csv.tmp")

    try:
        with temporal.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
            escritor.writeheader()
            escritor.writerows(filas)
        temporal.replace(ruta)
    except Exception:
        if temporal.exists():
            temporal.unlink()
        raise


def extraer_tienda(tienda: dict, fecha_hoy: str, hora_lectura: str) -> tuple[int, str]:
    """
    Extrae una tienda.
    Devuelve: (cantidad de productos, texto de error o vacío si salió bien).
    """
    nombre = tienda.get("nombre", "sin_nombre")
    plataforma = (tienda.get("plataforma") or "").lower()
    lector = LECTORES.get(plataforma)

    if lector is None:
        return 0, f"plataforma no soportada aún: {plataforma}"

    print(f"Leyendo {nombre} ({plataforma})...")
    try:
        filas = lector(tienda, fecha_hoy, hora_lectura, limite=LIMITE_PRUEBA)
        if not filas:
            return 0, "la tienda no devolvió productos"
        guardar_tienda(filas, ruta_csv_tienda(nombre, fecha_hoy))
    except Exception as error:
        return 0, str(error)

    return len(filas), ""


def main() -> None:
    ahora = datetime.now()
    fecha_hoy = ahora.date().isoformat()
    hora_lectura = ahora.strftime("%H:%M:%S")
    tiendas = cargar_tiendas()
    resumen: list[tuple[str, int, str]] = []

    print(f"Fecha: {fecha_hoy}  Hora: {hora_lectura}")
    if LIMITE_PRUEBA:
        print(f"Modo prueba: máximo {LIMITE_PRUEBA} productos por tienda.\n")

    for tienda in tiendas:
        nombre = tienda.get("nombre", "sin_nombre")
        if tienda.get("activo", True) is False:
            print(f"Saltando {nombre}: desactivada en tiendas.json.\n")
            resumen.append((nombre, 0, "desactivada"))
            continue
        cantidad, error = extraer_tienda(tienda, fecha_hoy, hora_lectura)
        resumen.append((nombre, cantidad, error))
        if error:
            print(f"  Error en {nombre}: {error}")
            print("  Se dejó el archivo anterior de esta tienda, si existía.\n")
        else:
            print(f"  OK: {cantidad} productos -> {ruta_csv_tienda(nombre, fecha_hoy)}\n")

    print("=== Resumen ===")
    hubo_error = False
    for nombre, cantidad, error in resumen:
        if error == "desactivada":
            print(f"- {nombre}: no se leyó (desactivada).")
        elif error:
            hubo_error = True
            print(f"- {nombre}: 0 productos. Error: {error}")
        else:
            print(f"- {nombre}: {cantidad} productos. Sin errores.")
    print(f"\nCarpeta del año:\n{CARPETA_PRECIOS / fecha_hoy[:4]}")
    if hubo_error:
        print("\nHubo errores en al menos una tienda activa.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
