"""
Lector de tiendas Bsale (por ejemplo gogogo.cl).

Lee el menú de la portada, recorre cada categoría y saca nombre, enlace,
precios y stock desde la lista (no abre cada producto).
"""

from __future__ import annotations

import json
import re
import time
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from lectores.comun import pausa_de, url_imagen

ENCABEZADOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

PRODUCTOS_POR_PAGINA = 50

# Vacío = recorre todas las categorías del menú.
CATEGORIA_PRUEBA = ""


def pedir(url: str) -> str:
    solicitud = Request(url, headers=ENCABEZADOS)
    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            return respuesta.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} al pedir {url}") from error
    except URLError as error:
        raise RuntimeError(f"No se pudo conectar: {error.reason}") from error


def a_entero_precio(valor) -> str:
    if valor in (None, ""):
        return ""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}"


def enlace_absoluto(base: str, relativo: str) -> str:
    return urljoin(base.rstrip("/") + "/", relativo.lstrip("/"))


def categorias_del_menu(html: str, direccion: str) -> list[str]:
    """Saca los enlaces /collection/... de las entradas del menú principal."""
    slugs: list[str] = []
    vistos: set[str] = set()
    host_tienda = urlparse(direccion).netloc.replace("www.", "")

    for etiqueta in re.finditer(r"<a\s[^>]*>", html, re.I):
        tag = etiqueta.group(0)
        if "bs-menu-lv" not in tag and "bs-menu__lv" not in tag:
            continue
        href_m = re.search(r'href="([^"]+)"', tag)
        if not href_m:
            continue
        href = unescape(href_m.group(1)).split("?")[0].strip()
        if href in ("#", "", "/"):
            continue
        absoluto = enlace_absoluto(direccion, href)
        parsed = urlparse(absoluto)
        if parsed.netloc and host_tienda not in parsed.netloc.replace("www.", ""):
            continue
        partes = [p for p in parsed.path.split("/") if p]
        if len(partes) < 2 or partes[0] != "collection":
            continue
        slug = partes[1]
        if slug in vistos:
            continue
        vistos.add(slug)
        slugs.append(slug)
    return slugs


def colecciones_json(html: str) -> list[dict]:
    """Lee el bloque window.INIT.collections.push({...}) que Bsale deja en la página."""
    out: list[dict] = []
    decoder = json.JSONDecoder()
    marca = "window.INIT.collections.push("
    inicio = 0
    while True:
        pos = html.find(marca, inicio)
        if pos < 0:
            break
        try:
            obj, fin = decoder.raw_decode(html, pos + len(marca))
            if isinstance(obj, dict):
                out.append(obj)
            inicio = pos + fin
        except json.JSONDecodeError:
            inicio = pos + len(marca)
    return out


def total_segun_texto(html: str) -> int | None:
    coincidencia = re.search(r"Mostrando\s+(\d+)\s+de\s+(\d+)", html)
    if coincidencia:
        return int(coincidencia.group(2))
    return None


def productos_de_categoria(direccion: str, slug: str, pausa: float) -> tuple[list[dict], int | None]:
    """Pide page=1, 2, 3... hasta que no haya más. Devuelve productos y el total declarado."""
    items: list[dict] = []
    pagina = 1
    total = None

    while True:
        url = (
            f"{direccion.rstrip('/')}/collection/{slug}"
            f"?limit={PRODUCTOS_POR_PAGINA}&page={pagina}"
        )
        html = pedir(url)
        if total is None:
            total = total_segun_texto(html)

        lote: list[dict] = []
        for coleccion in colecciones_json(html):
            lote.extend(coleccion.get("items") or [])

        if not lote:
            break

        print(f"    {slug} página {pagina} ({len(lote)} productos)")
        items.extend(lote)

        if total is not None and len(items) >= total:
            break
        if len(lote) < PRODUCTOS_POR_PAGINA:
            break

        pagina += 1
        time.sleep(pausa)

    return items, total


def fila_producto(item: dict, nombre_tienda: str, direccion: str, fecha_hoy: str, hora_lectura: str) -> dict:
    enlace = enlace_absoluto(direccion, item.get("link") or "")
    precio_actual = a_entero_precio(item.get("finalPrice"))
    precio_normal = a_entero_precio(item.get("fpWithoutDiscount"))
    if not precio_normal:
        precio_normal = precio_actual

    try:
        stock = float(item.get("totalStock") or 0)
    except (TypeError, ValueError):
        stock = 0
    hay = stock > 0

    return {
        "fecha": fecha_hoy,
        "hora": hora_lectura,
        "tienda": nombre_tienda,
        "nombre": unescape(item.get("title") or ""),
        "enlace": enlace,
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "hay_stock": "si" if hay else "no",
        "cantidad": str(int(stock)) if hay else "N/A",
        "imagen": url_imagen(item.get("defaultImage") or item.get("image") or "", direccion),
    }


def extraer(tienda: dict, fecha_hoy: str, hora_lectura: str, limite: int = 0) -> list[dict]:
    direccion = tienda["direccion"].rstrip("/")
    nombre = tienda["nombre"]
    pausa = pausa_de(tienda)

    print("  Leyendo menú de la portada...")
    portada = pedir(direccion + "/")
    slugs = categorias_del_menu(portada, direccion)
    time.sleep(pausa)

    if CATEGORIA_PRUEBA:
        slugs = [s for s in slugs if s == CATEGORIA_PRUEBA]
        if not slugs:
            slugs = [CATEGORIA_PRUEBA]
        print(f"  Modo prueba: solo categoría '{CATEGORIA_PRUEBA}'.")

    print(f"  Categorías a leer: {len(slugs)}")

    por_enlace: dict[str, dict] = {}
    duplicados = 0
    vacias: list[str] = []
    fallidas: list[str] = []
    desajustes: list[str] = []

    for slug in slugs:
        try:
            items, declarado = productos_de_categoria(direccion, slug, pausa)
        except Exception as error:
            print(f"  Error en categoría {slug}: {error}")
            fallidas.append(f"{slug} ({error})")
            time.sleep(pausa)
            continue

        leidos = len(items)
        if leidos == 0:
            vacias.append(slug)
            print(f"    {slug}: vacía")
        elif declarado is not None and leidos != declarado:
            desajustes.append(f"{slug}: leídos {leidos}, declarados {declarado}")
            print(f"    {slug}: no coincide (leídos {leidos}, declarados {declarado})")

        for item in items:
            fila = fila_producto(item, nombre, direccion, fecha_hoy, hora_lectura)
            enlace = fila["enlace"]
            if not enlace:
                continue
            if enlace in por_enlace:
                duplicados += 1
                continue
            por_enlace[enlace] = fila
            if limite and len(por_enlace) >= limite:
                break
        if limite and len(por_enlace) >= limite:
            break
        time.sleep(pausa)

    print(f"\n  === Resumen {nombre} ===")
    print(f"  Categorías recorridas: {len(slugs)}")
    print(f"  Categorías vacías: {len(vacias)}" + (f" ({', '.join(vacias)})" if vacias else ""))
    print(f"  Categorías con error: {len(fallidas)}" + (f" ({', '.join(fallidas)})" if fallidas else ""))
    print(f"  Productos únicos guardados: {len(por_enlace)}")
    print(f"  Duplicados eliminados: {duplicados}")
    if desajustes:
        print("  Categorías donde el total no coincide:")
        for linea in desajustes:
            print(f"    - {linea}")
    else:
        print("  Categorías donde el total no coincide: ninguna")

    return list(por_enlace.values())
