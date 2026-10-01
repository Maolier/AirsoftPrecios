"""
Lector de tiendas Wix eCommerce (por ejemplo ironwolf.cl).

Lee el sitemap de productos y, en cada ficha, saca nombre, precios y stock
desde el bloque de datos del catálogo (con respaldo en JSON-LD).
"""

from __future__ import annotations

import gzip
import json
import re
import time
from html import unescape
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from lectores.comun import pausa_de

ENCABEZADOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip",
}

# Reintentos cuando Wix responde 429 (demasiadas solicitudes).
ESPERAS_429 = (30, 90)
# Wix corta si el sitemap y las fichas van muy seguidos.
PAUSA_TRAS_SITEMAP = 45

JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)
SITEMAP_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.I)
DECODADOR = json.JSONDecoder()


def decir(*args) -> None:
    print(*args, flush=True)


def opener_con_cookies():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def pedir(url: str, opener) -> str:
    """Pide una URL. Si Wix corta por exceso de visitas, espera y reintenta."""
    ultimo_error: Exception | None = None
    for intento, espera in enumerate([0, *ESPERAS_429]):
        if espera:
            decir(f"    Wix pidió pausa (429). Espero {espera}s y reintento...")
            time.sleep(espera)
        solicitud = Request(url, headers=ENCABEZADOS)
        try:
            with opener.open(solicitud, timeout=60) as respuesta:
                crudo = respuesta.read()
                encoding = (respuesta.headers.get("Content-Encoding") or "").lower()
                if "gzip" in encoding:
                    try:
                        crudo = gzip.decompress(crudo)
                    except OSError:
                        pass
                return crudo.decode("utf-8", errors="replace")
        except HTTPError as error:
            ultimo_error = error
            try:
                error.read()
            except Exception:
                pass
            if error.code == 429 and intento < len(ESPERAS_429):
                continue
            raise RuntimeError(f"HTTP {error.code} al pedir {url}") from error
        except URLError as error:
            raise RuntimeError(f"No se pudo conectar: {error.reason}") from error
    raise RuntimeError(f"HTTP 429 al pedir {url}") from ultimo_error


def a_entero_precio(valor) -> str:
    if valor in (None, ""):
        return ""
    texto = str(valor).replace("\xa0", "").replace(" ", "")
    texto = re.sub(r"[^\d.,-]", "", texto)
    if texto.count(",") == 1 and texto.count(".") == 0:
        texto = texto.replace(",", ".")
    elif texto.count(".") > 1:
        texto = texto.replace(".", "")
    try:
        numero = float(texto)
    except ValueError:
        return str(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}"


def a_numero(valor) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        texto = a_entero_precio(valor)
        try:
            return float(texto)
        except ValueError:
            return None


def urls_de_sitemap(xml: str, direccion: str) -> list[str]:
    """Enlaces de ficha /product-page/... que declara el sitemap."""
    base = direccion.rstrip("/")
    host = urlparse(base).netloc.replace("www.", "")
    vistos: set[str] = set()
    urls: list[str] = []
    for loc in SITEMAP_LOC.findall(xml):
        enlace = unescape(loc.strip())
        if "/product-page/" not in enlace.lower():
            continue
        if urlparse(enlace).netloc.replace("www.", "") != host:
            enlace = urljoin(base + "/", enlace.lstrip("/"))
        if enlace in vistos:
            continue
        vistos.add(enlace)
        urls.append(enlace)
    return urls


def lista_productos(direccion: str, opener) -> list[str]:
    """Lee el índice y el sitemap de productos de la tienda."""
    base = direccion.rstrip("/")
    indice = pedir(base + "/sitemap.xml", opener)
    destinos = SITEMAP_LOC.findall(indice)
    sitemap_productos = next(
        (loc.strip() for loc in destinos if "store-products-sitemap" in loc.lower()),
        "",
    )
    if sitemap_productos:
        xml = pedir(sitemap_productos, opener)
    else:
        xml = indice
    return urls_de_sitemap(xml, direccion)


def producto_del_catalogo(html: str) -> dict | None:
    """Bloque catalog.product que Wix deja dentro del código de la ficha."""
    marca = '"catalog":{"product":'
    pos = html.find(marca)
    if pos < 0:
        return None
    try:
        bloque, _fin = DECODADOR.raw_decode(html, pos + len('"catalog":'))
    except json.JSONDecodeError:
        return None
    producto = bloque.get("product") if isinstance(bloque, dict) else None
    if isinstance(producto, dict) and producto.get("name"):
        return producto
    return None


def producto_jsonld(html: str) -> dict | None:
    coincidencia = JSON_LD.search(html)
    if not coincidencia:
        return None
    try:
        data = json.loads(coincidencia.group(1).strip())
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
        data = data[0] if data else None
    if isinstance(data, dict) and data.get("@type") == "Product":
        return data
    return None


def ofertas_jsonld(nodo: dict | None) -> dict:
    if not isinstance(nodo, dict):
        return {}
    ofertas = nodo.get("offers")
    if isinstance(ofertas, list):
        ofertas = ofertas[0] if ofertas else {}
    return ofertas if isinstance(ofertas, dict) else {}


def hay_stock_texto(estado: str, disponibilidad: str) -> str:
    junto = f"{estado} {disponibilidad}".lower()
    if "out_of_stock" in junto or "outofstock" in junto or "agotado" in junto:
        return "no"
    if "in_stock" in junto or "instock" in junto or "limited" in junto:
        return "si"
    if estado or disponibilidad:
        return "si"
    return "no"


def precios_de_producto(producto: dict, ofertas: dict) -> tuple[str, str]:
    """Precio actual y precio normal (tachado, si hay oferta)."""
    actual_num = a_numero(producto.get("discountedPrice"))
    lista_num = a_numero(producto.get("price"))
    compare_num = a_numero(producto.get("comparePrice"))

    if actual_num in (None, 0) and lista_num not in (None, 0):
        actual_num = lista_num
    if actual_num in (None, 0):
        actual_num = a_numero(ofertas.get("price"))

    normal_num = compare_num
    if normal_num in (None, 0) and lista_num not in (None, 0) and actual_num is not None:
        if lista_num > actual_num:
            normal_num = lista_num
    if normal_num in (None, 0) or (actual_num is not None and normal_num < actual_num):
        normal_num = actual_num

    return a_entero_precio(actual_num), a_entero_precio(normal_num)


def cantidad_de_inventario(inventario: dict, hay: str) -> str:
    if hay != "si":
        return "N/A"
    cantidad = inventario.get("quantity")
    if cantidad in (None, ""):
        return "N/A"
    try:
        return str(int(float(cantidad)))
    except (TypeError, ValueError):
        return "N/A"


def variantes_con_precios_distintos(producto: dict) -> bool:
    precios = {
        a_entero_precio(item.get("price"))
        for item in (producto.get("productItems") or [])
        if isinstance(item, dict) and a_entero_precio(item.get("price"))
    }
    return len(precios) > 1


def parsear_ficha(html: str, enlace: str) -> dict:
    producto = producto_del_catalogo(html) or {}
    ld = producto_jsonld(html) or {}
    ofertas = ofertas_jsonld(ld)
    inventario = producto.get("inventory") if isinstance(producto.get("inventory"), dict) else {}

    nombre = unescape(str(producto.get("name") or ld.get("name") or "")).strip()
    precio_actual, precio_normal = precios_de_producto(producto, ofertas)
    disponibilidad = str(ofertas.get("availability") or "")
    estado = str(inventario.get("status") or "")
    hay = hay_stock_texto(estado, disponibilidad)

    return {
        "nombre": nombre,
        "enlace": enlace,
        "precio_actual": precio_actual,
        "precio_normal": precio_normal,
        "hay_stock": hay,
        "cantidad": cantidad_de_inventario(inventario, hay),
        "variantes_distintas": variantes_con_precios_distintos(producto),
    }


def extraer(tienda: dict, fecha_hoy: str, hora_lectura: str, limite: int = 0) -> list[dict]:
    """
    Lee los productos de una tienda Wix.

    limite: si es mayor que 0, se detiene al llegar a esa cantidad
    (sirve para probar sin bajar todo el catálogo).
    """
    direccion = tienda["direccion"].rstrip("/")
    nombre = tienda["nombre"]
    pausa = pausa_de(tienda)
    opener = opener_con_cookies()

    decir("  Leyendo sitemap de productos...")
    urls = lista_productos(direccion, opener)
    if limite:
        urls = urls[:limite]
        decir(f"  Modo prueba: máximo {limite} fichas.")
    decir(f"  Fichas a leer: {len(urls)}")
    decir(f"  Pausa extra de {PAUSA_TRAS_SITEMAP}s antes de las fichas...")
    time.sleep(PAUSA_TRAS_SITEMAP)

    filas: list[dict] = []
    fallidas: list[str] = []
    sin_precio = 0
    oferta = 0
    sin_stock = 0
    variantes = 0
    total = len(urls)
    seguidos_429 = 0

    for indice, enlace in enumerate(urls, start=1):
        try:
            html = pedir(enlace, opener)
            item = parsear_ficha(html, enlace)
            seguidos_429 = 0
        except Exception as error:
            decir(f"    Error en ficha {indice}/{total}: {error}")
            fallidas.append(enlace)
            if "429" in str(error):
                seguidos_429 += 1
                if seguidos_429 >= 2:
                    raise RuntimeError(
                        "Wix sigue bloqueando (429). Se conserva el CSV anterior"
                    ) from error
            else:
                seguidos_429 = 0
            time.sleep(pausa)
            continue

        if not item["nombre"]:
            item["nombre"] = enlace.rsplit("/", 1)[-1]

        if not item["precio_actual"]:
            sin_precio += 1
        if item["precio_actual"] and item["precio_normal"] and item["precio_actual"] != item["precio_normal"]:
            oferta += 1
        if item["hay_stock"] == "no":
            sin_stock += 1
        if item["variantes_distintas"]:
            variantes += 1

        filas.append(
            {
                "fecha": fecha_hoy,
                "hora": hora_lectura,
                "tienda": nombre,
                "nombre": item["nombre"],
                "enlace": item["enlace"],
                "precio_actual": item["precio_actual"],
                "precio_normal": item["precio_normal"] or item["precio_actual"],
                "hay_stock": item["hay_stock"],
                "cantidad": item["cantidad"],
                "imagen": "",
            }
        )

        if indice == 1 or indice % 25 == 0 or indice == total:
            decir(f"    {indice}/{total} fichas leídas...")
        time.sleep(pausa)

    decir(f"\n  === Resumen {nombre} ===")
    decir(f"  Fichas del sitemap: {total}")
    decir(f"  Productos guardados: {len(filas)}")
    decir(f"  Fichas con error: {len(fallidas)}")
    decir(f"  Sin precio: {sin_precio}")
    decir(f"  En oferta: {oferta}")
    decir(f"  Sin stock: {sin_stock}")
    decir(f"  Con variantes de precio distinto: {variantes}")
    if fallidas:
        decir("  Errores:")
        for enlace in fallidas[:15]:
            decir(f"    - {enlace}")
        if len(fallidas) > 15:
            decir(f"    - ... y {len(fallidas) - 15} más")

    if total and len(filas) < max(1, int(total * 0.9)):
        raise RuntimeError(
            f"solo se leyeron {len(filas)} de {total} productos; se conserva el CSV anterior"
        )

    return filas
