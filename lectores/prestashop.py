"""
Lector de tiendas PrestaShop (por ejemplo airsoftrhino.cl).

Lee el menú de la portada, recorre cada categoría y saca nombre, enlace,
precio y stock desde la lista de la categoría.
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

# Vacío = recorre todas las categorías del menú.
CATEGORIA_PRUEBA = ""

ARTICULO = re.compile(
    r'<article class="product-miniature js-product-miniature".*?</article>',
    re.S | re.I,
)


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
    texto = str(valor).replace("\xa0", "").replace(".", "").replace(" ", "")
    texto = re.sub(r"[^\d.,-]", "", texto)
    texto = texto.replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return str(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:.2f}"


def categorias_del_menu(html: str, direccion: str) -> list[str]:
    """Saca /ID-nombre del megamenú de la portada."""
    inicio = html.find("leo-top-menu")
    bloque = html[inicio : inicio + 120000] if inicio >= 0 else html
    encontrados = re.findall(
        r'href="(?:https?://[^/]+)?/(\d{1,3}-[a-z0-9-]+)"',
        bloque,
        re.I,
    )
    slugs: list[str] = []
    vistos: set[str] = set()
    for slug in encontrados:
        bajo = slug.lower()
        if bajo.endswith("-home") or bajo.endswith("-large"):
            continue
        if slug in vistos:
            continue
        vistos.add(slug)
        slugs.append(slug)
    return slugs


def id_producto_en_enlace(url: str) -> str:
    archivo = url.rstrip("/").rsplit("/", 1)[-1]
    coincidencia = re.match(r"(\d+)-", archivo)
    return coincidencia.group(1) if coincidencia else ""


def nombres_jsonld(html: str) -> dict[str, str]:
    """Nombre completo por id de producto, desde el ItemList de la página."""
    nombres: dict[str, str] = {}
    decoder = json.JSONDecoder()
    marca = '<script type="application/ld+json">'
    pos = 0
    while True:
        i = html.find(marca, pos)
        if i < 0:
            break
        try:
            obj, fin = decoder.raw_decode(html, i + len(marca))
        except json.JSONDecodeError:
            pos = i + len(marca)
            continue
        pos = i + fin
        if not isinstance(obj, dict) or obj.get("@type") != "ItemList":
            continue
        for item in obj.get("itemListElement") or []:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or ""
            nombre = unescape(item.get("name") or "")
            pid = id_producto_en_enlace(url)
            if pid and nombre:
                nombres[pid] = nombre
    return nombres


def total_declarado(html: str) -> int | None:
    coincidencia = re.search(r"Hay\s+(\d+)\s+productos?", html, re.I)
    if coincidencia:
        return int(coincidencia.group(1))
    return None


def parsear_articulo(bloque: str) -> dict | None:
    pid_m = re.search(r'data-id-product="(\d+)"', bloque)
    pid = pid_m.group(1) if pid_m else ""
    enlace_m = re.search(r'href="(https?://[^"]+\.html)"', bloque)
    if not enlace_m:
        enlace_m = re.search(r'href="(https?://[^"]+)"', bloque)
    if not enlace_m:
        return None
    enlace = unescape(enlace_m.group(1)).split("#")[0].rstrip("/")
    nombre_m = re.search(r'itemprop="name">\s*<a[^>]*>([^<]+)', bloque)
    if not nombre_m:
        nombre_m = re.search(r'product-title"[^>]*>\s*<a[^>]*>([^<]+)', bloque)
    nombre = unescape((nombre_m.group(1) if nombre_m else "").strip())
    precio_m = re.search(r'itemprop="price"\s+content="([^"]+)"', bloque)
    precio = a_entero_precio(precio_m.group(1) if precio_m else "")
    normal_m = re.search(r'class="regular-price"[^>]*>\s*([^<]+)', bloque)
    precio_normal = a_entero_precio(normal_m.group(1).strip()) if normal_m else ""
    if not precio_normal:
        precio_normal = precio
    hay = "out_of_stock" not in bloque and "Fuera de stock" not in bloque
    foto = ""
    for patron in (
        r'data-full-size-image-url\s*=\s*"([^"]+)"',
        r'<img[^>]+src\s*=\s*"([^"]+)"',
    ):
        img_m = re.search(patron, bloque, re.I)
        if img_m:
            foto = url_imagen(img_m.group(1), enlace)
            if foto:
                break
    return {
        "id": pid or id_producto_en_enlace(enlace),
        "nombre": nombre,
        "enlace": enlace,
        "precio_actual": precio,
        "precio_normal": precio_normal,
        "hay_stock": "si" if hay else "no",
        "cantidad": "N/A",
        "imagen": foto,
    }


def productos_de_html(html: str) -> list[dict]:
    nombres = nombres_jsonld(html)
    por_enlace: dict[str, dict] = {}
    for bloque in ARTICULO.findall(html):
        fila = parsear_articulo(bloque)
        if not fila or not fila["enlace"]:
            continue
        if fila["enlace"] in por_enlace:
            continue
        if fila["id"] and fila["id"] in nombres:
            fila["nombre"] = nombres[fila["id"]]
        por_enlace[fila["enlace"]] = fila
    return list(por_enlace.values())


def productos_de_categoria(direccion: str, slug: str, pausa: float) -> tuple[list[dict], int | None]:
    items: list[dict] = []
    pagina = 1
    total = None
    vistos: set[str] = set()

    while True:
        url = f"{direccion.rstrip('/')}/{slug}"
        if pagina > 1:
            url = f"{url}?page={pagina}"
        html = pedir(url)
        if total is None:
            total = total_declarado(html)

        lote = productos_de_html(html)
        nuevos = [p for p in lote if p["enlace"] not in vistos]
        if not nuevos:
            break

        print(f"    {slug} página {pagina} ({len(nuevos)} productos)")
        for p in nuevos:
            vistos.add(p["enlace"])
            items.append(p)

        if total is not None and len(items) >= total:
            break

        pagina += 1
        time.sleep(pausa)

    return items, total


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
            enlace = item["enlace"]
            if enlace in por_enlace:
                duplicados += 1
                if item.get("imagen") and not por_enlace[enlace].get("imagen"):
                    por_enlace[enlace]["imagen"] = item["imagen"]
                continue
            por_enlace[enlace] = {
                "fecha": fecha_hoy,
                "hora": hora_lectura,
                "tienda": nombre,
                "nombre": item["nombre"],
                "enlace": enlace,
                "precio_actual": item["precio_actual"],
                "precio_normal": item["precio_normal"],
                "hay_stock": item["hay_stock"],
                "cantidad": item["cantidad"],
                "imagen": item.get("imagen") or "",
            }
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
