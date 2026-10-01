"""
Arma el catálogo liviano que lee la web a partir de:
- productos_clasificados.csv (categoría ya resuelta, con correcciones)
- todos los CSV diarios de precios/ (historial completo)

No modifica los CSV de precios ni categorias.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from clasificar_productos import (
    ARCHIVO_SALIDA as ARCHIVO_CLASIFICADOS,
    CARPETA,
    CARPETA_PRECIOS,
    SIN_CLASIFICAR,
    clave_enlace,
    cargar_categorias,
    es_carpeta_anio,
    leer_filas,
)

ARCHIVO_JS = CARPETA / "docs" / "js" / "datos-catalogo.js"

NOMBRES_TIENDA = {
    "airsoftgames": "Airsoft Games",
    "airsoftdefence": "Airsoft Defence",
    "commandostore": "Commando Store",
    "gogogo": "GoGoGo",
    "airsoftrhino": "Airsoft Rhino",
    "ironwolf": "Iron Wolf",
}

# El menú de la web se mantiene igual; solo cambia la fuente de productos.
MENU = [
    {
        "id": "replicas",
        "nombre": "Réplicas",
        "sub": [
            {"id": "pistolas", "nombre": "Pistolas"},
            {"id": "fusil", "nombre": "Fusil"},
            {"id": "subfusil", "nombre": "Subfusil"},
            {"id": "escopeta", "nombre": "Escopeta"},
            {"id": "sniper", "nombre": "Sniper"},
            {"id": "soporte", "nombre": "Soporte"},
        ],
    },
    {"id": "cargadores", "nombre": "Cargadores", "sub": []},
    {
        "id": "municion",
        "nombre": "Munición",
        "sub": [
            {"id": "bbs", "nombre": "BBs"},
            {"id": "gas", "nombre": "Gas"},
            {"id": "varios", "nombre": "Varios"},
        ],
    },
    {
        "id": "proteccion",
        "nombre": "Protección",
        "sub": [
            {"id": "mascaras-lentes", "nombre": "Máscaras y lentes"},
            {"id": "guantes", "nombre": "Guantes"},
            {"id": "rodilleras-coderas", "nombre": "Rodilleras y coderas"},
            {"id": "cascos", "nombre": "Cascos"},
        ],
    },
    {
        "id": "uniforme",
        "nombre": "Uniforme y equipamiento",
        "sub": [
            {"id": "uniformes", "nombre": "Uniformes"},
            {"id": "chalecos", "nombre": "Chalecos y plate carriers"},
            {"id": "mochilas", "nombre": "Mochilas"},
            {"id": "pouches", "nombre": "Pouches y bolsos"},
            {"id": "botas", "nombre": "Botas"},
            {"id": "gorras", "nombre": "Gorras y balaclavas"},
        ],
    },
    {
        "id": "externos",
        "nombre": "Accesorios externos",
        "sub": [
            {"id": "miras", "nombre": "Miras y ópticas"},
            {"id": "linternas", "nombre": "Linternas y láseres"},
            {"id": "rieles", "nombre": "Rieles y adaptadores"},
            {"id": "bipodes", "nombre": "Bípodes"},
            {"id": "supresores", "nombre": "Supresores"},
            {"id": "grips-stocks", "nombre": "Grips y stocks"},
        ],
    },
    {
        "id": "internos",
        "nombre": "Accesorios internos / upgrades",
        "sub": [
            {"id": "hop-up", "nombre": "Hop-up"},
            {"id": "resortes", "nombre": "Resortes"},
            {"id": "gearbox", "nombre": "Gearbox y piezas de gearbox"},
            {"id": "canones", "nombre": "Cañones internos"},
            {"id": "motores", "nombre": "Motores"},
            {"id": "valvulas", "nombre": "Válvulas y nozzles"},
        ],
    },
    {"id": "baterias", "nombre": "Baterías", "sub": []},
    {"id": "packs", "nombre": "Packs y combos", "sub": []},
    {"id": "otros", "nombre": "Otros", "sub": []},
]


def id_estable(tienda: str, enlace: str) -> str:
    """
    Identificador estable: tienda + enlace normalizado (sin www, query ni / final).
    El hash corto cabe en la URL de la ficha y no cambia si solo varía el precio.
    """
    tienda_limpia = re.sub(r"[^a-z0-9]+", "", (tienda or "").lower()) or "tienda"
    digest = hashlib.sha1(
        f"{tienda_limpia}|{clave_enlace(enlace)}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{tienda_limpia}-{digest}"


def clave_producto(tienda: str, enlace: str) -> tuple[str, str]:
    return ((tienda or "").strip().lower(), clave_enlace(enlace))


def precio_num(valor) -> int | None:
    texto = str(valor or "").strip().replace("$", "").replace(" ", "")
    if not texto or texto.upper() in {"N/A", "NA", "NONE", "-"}:
        return None
    texto = texto.replace(".", "").replace(",", "")
    try:
        return int(round(float(texto)))
    except ValueError:
        return None


def mapas_categoria(categorias: list[dict]) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    cat_por_nombre: dict[str, str] = {SIN_CLASIFICAR: "otros"}
    sub_por_nombre: dict[tuple[str, str], str] = {}
    for cat in categorias:
        cat_id = cat.get("id") or ""
        cat_por_nombre[cat.get("nombre") or ""] = cat_id
        for sub in cat.get("subcategorias") or []:
            sub_por_nombre[(cat_id, sub.get("nombre") or "")] = sub.get("id") or ""
    return cat_por_nombre, sub_por_nombre


def csv_historial() -> list[Path]:
    if not CARPETA_PRECIOS.exists():
        return []
    archivos: list[Path] = []
    for carpeta_anio in CARPETA_PRECIOS.iterdir():
        if not es_carpeta_anio(carpeta_anio):
            continue
        for ruta in carpeta_anio.glob("*.csv"):
            if ruta.name.endswith(".tmp"):
                continue
            archivos.append(ruta)
    return sorted(archivos)


def cargar_historial() -> dict[tuple[str, str], list[dict]]:
    """
    Un punto por día (el de la hora más tarde si se leyó más de una vez).
    Clave: (tienda, enlace normalizado).
    """
    por_dia: dict[tuple[str, str], dict[str, tuple[str, int]]] = defaultdict(dict)
    for ruta in csv_historial():
        for fila in leer_filas(ruta):
            precio = precio_num(fila.get("precio_actual"))
            fecha = (fila.get("fecha") or "").strip()
            if precio is None or not fecha:
                continue
            clave = clave_producto(fila.get("tienda") or "", fila.get("enlace") or "")
            if not clave[0] or not clave[1]:
                continue
            hora = (fila.get("hora") or "").strip()
            actual = por_dia[clave].get(fecha)
            if actual is None or hora >= actual[0]:
                por_dia[clave][fecha] = (hora, precio)

    historial: dict[tuple[str, str], list[dict]] = {}
    for clave, dias in por_dia.items():
        historial[clave] = [
            {"fecha": fecha, "precio": precio}
            for fecha, (_hora, precio) in sorted(dias.items())
        ]
    return historial


def leer_clasificados() -> list[dict]:
    ruta = ARCHIVO_CLASIFICADOS
    temporal = ruta.with_suffix(".csv.tmp")
    if temporal.exists() and (
        not ruta.exists() or temporal.stat().st_mtime > ruta.stat().st_mtime
    ):
        ruta = temporal
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def nombre_tienda(tienda: str) -> str:
    clave = (tienda or "").strip().lower()
    return NOMBRES_TIENDA.get(clave, tienda or "Tienda")


def producto_web(
    fila: dict,
    historial: dict[tuple[str, str], list[dict]],
    cat_por_nombre: dict[str, str],
    sub_por_nombre: dict[tuple[str, str], str],
) -> dict | None:
    tienda = (fila.get("tienda") or "").strip()
    enlace = (fila.get("enlace") or "").strip()
    if not tienda or not enlace:
        return None

    cat_nombre = (fila.get("categoria") or "").strip() or SIN_CLASIFICAR
    cat_id = cat_por_nombre.get(cat_nombre) or "otros"
    if cat_nombre == SIN_CLASIFICAR:
        cat_id = "otros"

    sub_nombre = (fila.get("subcategoria") or "").strip()
    sub_id = sub_por_nombre.get((cat_id, sub_nombre), "") if sub_nombre else ""

    precio_actual = precio_num(fila.get("precio_actual"))
    precio_normal = precio_num(fila.get("precio_normal"))
    if precio_actual is None:
        precio_actual = precio_normal if precio_normal is not None else 0
    if precio_normal is None:
        precio_normal = precio_actual

    clave = clave_producto(tienda, enlace)
    puntos = historial.get(clave) or [{"fecha": (fila.get("fecha") or "").strip(), "precio": precio_actual}]
    puntos = [p for p in puntos if p.get("fecha") and p.get("precio") is not None]

    return {
        "id": id_estable(tienda, enlace),
        "nombre": (fila.get("nombre") or "").strip() or "Producto",
        "tienda": tienda,
        "tienda_nombre": nombre_tienda(tienda),
        "enlace_tienda": enlace,
        "imagen": (fila.get("imagen") or "").strip(),
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "categoria": cat_id,
        "subcategoria": sub_id,
        "historial": puntos,
    }


def generar() -> Path:
    categorias = cargar_categorias()
    cat_por_nombre, sub_por_nombre = mapas_categoria(categorias)
    historial = cargar_historial()
    productos: list[dict] = []
    vistos: set[str] = set()
    omitidos = 0

    for fila in leer_clasificados():
        item = producto_web(fila, historial, cat_por_nombre, sub_por_nombre)
        if item is None:
            omitidos += 1
            continue
        if item["id"] in vistos:
            continue
        vistos.add(item["id"])
        productos.append(item)

    productos.sort(key=lambda p: (p["categoria"], p["subcategoria"], p["nombre"].lower()))

    ARCHIVO_JS.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = (
        "window.GEARUP=window.GEARUP||{};\n"
        "GEARUP.MENU="
        + json.dumps(MENU, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
        "GEARUP.PRODUCTOS="
        + json.dumps(productos, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    temporal = ARCHIVO_JS.with_suffix(".js.tmp")
    temporal.write_text(cuerpo, encoding="utf-8")
    temporal.replace(ARCHIVO_JS)

    print(f"Catálogo web: {len(productos)} productos")
    if omitidos:
        print(f"Omitidos (sin tienda o enlace): {omitidos}")
    print(f"Historial armado desde {len(csv_historial())} CSV diarios.")
    print(f"Salida:\n{ARCHIVO_JS}")
    return ARCHIVO_JS


def main() -> None:
    if not ARCHIVO_CLASIFICADOS.exists() and not ARCHIVO_CLASIFICADOS.with_suffix(".csv.tmp").exists():
        print("No hay productos_clasificados.csv. Corre clasificar_productos.py primero.")
        return
    generar()


if __name__ == "__main__":
    main()
