"""
Lector de tiendas WooCommerce.

Es el mismo método que ya usabas en airsoftgames y airsoftdefence:
pide el listado público de productos, página por página.
"""

from __future__ import annotations

import json
import re
import time
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lectores.comun import pausa_de, url_imagen

# Pide como máximo 100 productos por visita (límite de WooCommerce).
PRODUCTOS_POR_PAGINA = 100

ENCABEZADOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def url_productos(direccion: str) -> str:
    """Arma el enlace de la lista de productos de la tienda."""
    base = direccion.rstrip("/")
    return f"{base}/wp-json/wc/store/v1/products?per_page={PRODUCTOS_POR_PAGINA}"


def pedir_pagina(direccion: str, numero_pagina: int) -> tuple[list[dict], int | None]:
    """
    Visita una página y devuelve:
    - los productos de esa página
    - el total de páginas (si la tienda lo indica)
    """
    url = f"{url_productos(direccion)}&page={numero_pagina}"
    solicitud = Request(url, headers=ENCABEZADOS)

    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            encabezado_total = respuesta.headers.get("X-WP-TotalPages")
            total_paginas = int(encabezado_total) if encabezado_total else None
            productos = json.loads(respuesta.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} al pedir {url}") from error
    except URLError as error:
        raise RuntimeError(f"No se pudo conectar: {error.reason}") from error

    if not isinstance(productos, list):
        raise RuntimeError("La tienda no devolvió una lista de productos.")

    return productos, total_paginas


def a_pesos(precios: dict, campo: str) -> str:
    """Convierte el precio de la API a un número entendible."""
    if not precios:
        return ""

    crudo = precios.get(campo)
    if crudo in (None, ""):
        return ""

    try:
        valor = float(crudo)
        decimales = int(precios.get("currency_minor_unit") or 0)
        if decimales > 0:
            valor = valor / (10 ** decimales)
    except (TypeError, ValueError):
        return str(crudo)

    if valor.is_integer():
        return str(int(valor))
    return f"{valor:.2f}"


def hay_stock(producto: dict) -> str:
    """Devuelve 'si' o 'no' según si el producto se puede comprar ahora."""
    return "si" if producto.get("is_in_stock") else "no"


def cantidad_disponible(producto: dict) -> str:
    """Número de unidades si la tienda lo publica; si no, N/A."""
    if not producto.get("is_in_stock"):
        return "N/A"

    disponibilidad = producto.get("stock_availability") or {}
    texto = ""
    if isinstance(disponibilidad, dict):
        texto = str(disponibilidad.get("text") or "")
    coincidencia = re.search(r"\d+", texto)
    if coincidencia:
        return coincidencia.group(0)

    restante = producto.get("low_stock_remaining")
    if restante not in (None, ""):
        try:
            return str(int(restante))
        except (TypeError, ValueError):
            return str(restante)

    carrito = producto.get("add_to_cart") or {}
    maximo = carrito.get("maximum")
    if maximo not in (None, ""):
        try:
            valor = int(maximo)
        except (TypeError, ValueError):
            return "N/A"
        if 0 < valor < 9999:
            return str(valor)

    return "N/A"


def fila_producto(
    producto: dict, nombre_tienda: str, fecha_hoy: str, hora_lectura: str
) -> dict:
    """Arma una fila con las columnas del historial."""
    precios = producto.get("prices") or {}
    precio_actual = a_pesos(precios, "price")
    precio_normal = a_pesos(precios, "regular_price")
    if not precio_normal:
        precio_normal = precio_actual

    imagenes = producto.get("images") or []
    primera = imagenes[0] if imagenes and isinstance(imagenes[0], dict) else {}
    foto = url_imagen(primera.get("thumbnail") or primera.get("src") or "")

    return {
        "fecha": fecha_hoy,
        "hora": hora_lectura,
        "tienda": nombre_tienda,
        "nombre": unescape(producto.get("name") or ""),
        "enlace": producto.get("permalink") or "",
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "hay_stock": hay_stock(producto),
        "cantidad": cantidad_disponible(producto),
        "imagen": foto,
    }


def extraer(tienda: dict, fecha_hoy: str, hora_lectura: str, limite: int = 0) -> list[dict]:
    """
    Lee los productos de una tienda WooCommerce.

    limite: si es mayor que 0, se detiene al llegar a esa cantidad
    (sirve para probar sin bajar todo el catálogo).
    """
    filas: list[dict] = []
    pagina = 1
    direccion = tienda["direccion"]
    nombre = tienda["nombre"]
    pausa = pausa_de(tienda)

    while True:
        productos, total_paginas = pedir_pagina(direccion, pagina)

        if not productos:
            break

        print(f"  Página {pagina} ({len(productos)} productos)...")

        for producto in productos:
            filas.append(fila_producto(producto, nombre, fecha_hoy, hora_lectura))
            if limite and len(filas) >= limite:
                return filas

        if total_paginas is not None and pagina >= total_paginas:
            break

        pagina += 1
        time.sleep(pausa)

    return filas
