"""
Clasifica el catálogo actual según categorias.json.

Lee el CSV más reciente de cada tienda, no modifica los CSV de precios
y guarda el resultado en productos_clasificados.csv.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
ARCHIVO_CATEGORIAS = CARPETA / "categorias.json"
ARCHIVO_CORRECCIONES = CARPETA / "correcciones_categoria.json"
CARPETA_PRECIOS = CARPETA / "precios"
ARCHIVO_SALIDA = CARPETA / "productos_clasificados.csv"

COLUMNAS_ORIGEN = [
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

COLUMNAS_SALIDA = COLUMNAS_ORIGEN + [
    "categoria",
    "subcategoria",
    "grupo_propio",
    "coincidencias",
    "conflicto",
    "categoria_tienda",
]

SIN_CLASIFICAR = "Sin clasificar"
OTROS = "Otros"
MUESTRA_POR_CATEGORIA = 8


def quitar_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con puntuación convertida en espacios."""
    texto = quitar_tildes((texto or "").lower())
    texto = texto.replace("&", " ").replace("%20", " ")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return f" {texto.strip()} "


def separar_letras_y_numeros(texto: str) -> str:
    """AK47 y fullmetal pasan a tokens que se pueden comparar: ak 47."""
    texto = re.sub(r"([a-z])([0-9])", r"\1 \2", texto)
    texto = re.sub(r"([0-9])([a-z])", r"\1 \2", texto)
    return re.sub(r"\s+", " ", texto)


def preparar(texto: str) -> str:
    return separar_letras_y_numeros(normalizar(texto))


def texto_enlace(enlace: str) -> str:
    """Saca del enlace la ruta (ahí a veces viene la categoría de la tienda)."""
    if not enlace:
        return ""
    sin_query = enlace.split("?", 1)[0]
    partes = [p for p in sin_query.split("/") if p and "://" not in p]
    # Quita dominio si quedó pegado
    if partes and "." in partes[0]:
        partes = partes[1:]
    return " ".join(partes)


def categoria_desde_enlace(enlace: str) -> str:
    """Primer segmento útil de la URL, si no es un genérico tipo /producto/."""
    ignorar = {
        "producto",
        "product",
        "products",
        "inicio",
        "www",
        "https:",
        "http:",
        "",
    }
    for parte in texto_enlace(enlace).split():
        limpio = parte.strip().lower()
        if limpio and limpio not in ignorar and not limpio.replace("-", "").isdigit():
            if not re.match(r"^\d", limpio):
                return limpio
    return ""


_PATRONES: dict[str, re.Pattern[str]] = {}


def patron_palabra(palabra: str) -> re.Pattern[str] | None:
    pal = preparar(palabra).strip()
    if not pal:
        return None
    compilado = _PATRONES.get(pal)
    if compilado is None:
        nucleo = r"\s*".join(re.escape(p) for p in pal.split())
        # Plural simple: mascara→mascaras, boot→boots. No corta a medias (mag≠magazine).
        compilado = re.compile(rf"(?<![a-z0-9]){nucleo}s?(?![a-z0-9])")
        _PATRONES[pal] = compilado
    return compilado


def contiene_estricto(texto_norm: str, palabra: str) -> bool:
    """El matcher anterior: falla con AK47 vs ak-47 y con palabras pegadas."""
    pal = normalizar(palabra).strip()
    if not pal:
        return False
    return re.search(rf"(?<![a-z]){re.escape(pal)}(?![a-z])", texto_norm) is not None


def contiene(texto_prep: str, palabra: str) -> bool:
    """
    Mayúsculas y tildes no importan.
    Los espacios del JSON son opcionales: ak-47, ak 47 y AK47 calzan igual.
    Separa letras de números: 1000rds y m4a1 también calzan.
    Acepta una «s» final (mascara→mascaras, boot→boots).
    No corta a medias (mag ≠ magazine).
    texto_prep debe venir de preparar().
    """
    patron = patron_palabra(palabra)
    return bool(patron and patron.search(texto_prep))


def alguna_palabra(texto_norm: str, palabras: list[str]) -> list[str]:
    return [p for p in palabras if contiene(texto_norm, p)]


def cargar_archivo_categorias() -> dict:
    with ARCHIVO_CATEGORIAS.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar_categorias() -> list[dict]:
    return cargar_archivo_categorias()["categorias"]


def cargar_marcas_replicas() -> dict:
    """Paso 2: marcas que solo se usan si el producto quedó sin clasificar."""
    return cargar_archivo_categorias().get("marcas_replicas") or {}


def clave_enlace(enlace: str) -> str:
    e = (enlace or "").strip().lower()
    e = e.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    e = e.replace("://www.", "://")
    return e


def cargar_correcciones() -> dict[str, dict]:
    if not ARCHIVO_CORRECCIONES.exists():
        return {}
    with ARCHIVO_CORRECCIONES.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)
    por_enlace: dict[str, dict] = {}
    for item in datos.get("correcciones") or []:
        clave = clave_enlace(item.get("enlace") or "")
        if clave and item.get("categoria"):
            por_enlace[clave] = item
    return por_enlace


def es_carpeta_anio(ruta: Path) -> bool:
    return ruta.is_dir() and ruta.name.isdigit() and len(ruta.name) == 4


def csv_actuales() -> list[Path]:
    """
    Un CSV por tienda: el de la fecha más reciente.
    Así no se clasifica el mismo producto varias veces.
    """
    if not CARPETA_PRECIOS.exists():
        return []

    por_tienda: dict[str, Path] = {}
    for carpeta_anio in CARPETA_PRECIOS.iterdir():
        if not es_carpeta_anio(carpeta_anio):
            continue
        for ruta in carpeta_anio.glob("*.csv"):
            if ruta.name.endswith(".tmp"):
                continue
            # airsoftgames_2026-09-23.csv
            nombre = ruta.stem
            if "_" not in nombre:
                continue
            tienda, _, fecha = nombre.partition("_")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
                continue
            actual = por_tienda.get(tienda)
            if actual is None or fecha > actual.stem.partition("_")[2]:
                por_tienda[tienda] = ruta
    return [por_tienda[k] for k in sorted(por_tienda)]


def leer_filas(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def calza_nodo(texto_norm: str, nodo: dict) -> list[str]:
    """Devuelve las palabras que calzaron, o vacío si no aplica."""
    if alguna_palabra(texto_norm, nodo.get("excluir") or []):
        return []
    return alguna_palabra(texto_norm, nodo.get("palabras") or [])


def texto_de_nodo(nombre_prep: str, enlace_prep: str, nodo: dict) -> str:
    """Por defecto busca también en el enlace; se puede apagar en el JSON."""
    if nodo.get("buscar_en_enlace", True):
        return nombre_prep + " " + enlace_prep
    return nombre_prep


def aplicar_correccion(item: dict) -> dict:
    return {
        "categoria": item.get("categoria") or OTROS,
        "subcategoria": item.get("subcategoria") or "",
        "grupo_propio": "",
        "coincidencias": "corrección manual",
        "conflicto": "no",
        "detalle": [],
    }


def intentar_marca(nombre_prep: str, marcas_replicas: dict | None) -> dict | None:
    """
    Solo para los que el paso 1 dejó sin clasificar.
    Marca en el nombre y ninguna palabra de pieza/accesorio → Réplicas.
    Si hay marca y también una exclusión, no se adivina.
    """
    if not marcas_replicas:
        return None
    marcas_hit = alguna_palabra(nombre_prep, marcas_replicas.get("marcas") or [])
    if not marcas_hit:
        return None
    if alguna_palabra(nombre_prep, marcas_replicas.get("excluir") or []):
        return None
    return {
        "categoria": "Réplicas",
        "subcategoria": "",
        "grupo_propio": "",
        "coincidencias": "marca: " + ", ".join(marcas_hit),
        "conflicto": "no",
        "detalle": [],
    }


def clasificar(
    fila: dict,
    categorias: list[dict],
    correcciones: dict[str, dict] | None = None,
    marcas_replicas: dict | None = None,
) -> dict:
    enlace = fila.get("enlace") or ""
    if correcciones:
        manual = correcciones.get(clave_enlace(enlace))
        if manual:
            return aplicar_correccion(manual)

    nombre = fila.get("nombre") or ""
    nombre_prep = preparar(nombre)
    enlace_prep = preparar(texto_enlace(enlace))

    coincidencias: list[dict] = []
    for cat in categorias:
        texto_cat = texto_de_nodo(nombre_prep, enlace_prep, cat)
        if alguna_palabra(texto_cat, cat.get("excluir") or []):
            continue
        palabras_cat = alguna_palabra(texto_cat, cat.get("palabras") or [])
        sub_hits: list[dict] = []
        for sub in cat.get("subcategorias") or []:
            texto_sub = texto_de_nodo(nombre_prep, enlace_prep, sub)
            palabras_sub = calza_nodo(texto_sub, sub)
            if palabras_sub:
                sub_hits.append(
                    {
                        "id": sub.get("id", ""),
                        "nombre": sub.get("nombre", ""),
                        "prioridad": int(sub.get("prioridad", 99)),
                        "grupo_propio": bool(sub.get("grupo_propio")),
                        "palabras": palabras_sub,
                    }
                )

        if palabras_cat or sub_hits:
            coincidencias.append(
                {
                    "id": cat.get("id", ""),
                    "nombre": cat.get("nombre", ""),
                    "prioridad": int(cat.get("prioridad", 99)),
                    "palabras": palabras_cat,
                    "subcategorias": sub_hits,
                }
            )

    if not coincidencias:
        por_marca = intentar_marca(nombre_prep, marcas_replicas)
        if por_marca:
            return por_marca
        return {
            "categoria": OTROS,
            "subcategoria": "",
            "grupo_propio": "",
            "coincidencias": "",
            "conflicto": "no",
            "detalle": [],
        }

    coincidencias.sort(key=lambda c: c["prioridad"])
    principal = coincidencias[0]
    sub_ordenadas = sorted(principal["subcategorias"], key=lambda s: s["prioridad"])
    sub_principal = sub_ordenadas[0] if sub_ordenadas else None

    textos = []
    for cat in coincidencias:
        if cat["subcategorias"]:
            for sub in cat["subcategorias"]:
                textos.append(f"{cat['nombre']} > {sub['nombre']}")
        else:
            textos.append(cat["nombre"])

    varias_cats = len(coincidencias) > 1
    varias_subs = len(principal["subcategorias"]) > 1
    conflicto = "si" if varias_cats or varias_subs else "no"

    return {
        "categoria": principal["nombre"],
        "subcategoria": sub_principal["nombre"] if sub_principal else "",
        "grupo_propio": (
            sub_principal["nombre"]
            if sub_principal and sub_principal["grupo_propio"]
            else ""
        ),
        "coincidencias": " | ".join(textos),
        "conflicto": conflicto,
        "detalle": coincidencias,
    }


def guardar(filas: list[dict]) -> Path:
    """
    Escribe un temporal y lo pone en el lugar.
    Si Excel tiene abierto el CSV, deja el temporal para no perder el resultado.
    """
    temporal = ARCHIVO_SALIDA.with_suffix(".csv.tmp")
    with temporal.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(
            archivo, fieldnames=COLUMNAS_SALIDA, extrasaction="ignore"
        )
        escritor.writeheader()
        escritor.writerows(filas)
    try:
        temporal.replace(ARCHIVO_SALIDA)
        return ARCHIVO_SALIDA
    except OSError:
        print(
            f"No se pudo reemplazar {ARCHIVO_SALIDA.name} "
            "(ciérralo en Excel si está abierto)."
        )
        print(f"El resultado quedó en:\n{temporal}")
        return temporal


def imprimir_conteos(filas: list[dict], categorias: list[dict]) -> None:
    por_cat: dict[str, int] = defaultdict(int)
    por_sub: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    grupos: dict[str, int] = defaultdict(int)

    for fila in filas:
        cat = fila["categoria"]
        sub = fila["subcategoria"]
        por_cat[cat] += 1
        if sub:
            por_sub[cat][sub] += 1
        if fila["grupo_propio"]:
            grupos[fila["grupo_propio"]] += 1

    print("=== Productos por categoría ===")
    orden = [c["nombre"] for c in categorias]
    if SIN_CLASIFICAR in por_cat:
        orden.append(SIN_CLASIFICAR)
    for nombre in orden:
        if nombre not in por_cat:
            print(f"- {nombre}: 0")
            continue
        print(f"- {nombre}: {por_cat[nombre]}")
        cat_conf = next((c for c in categorias if c["nombre"] == nombre), None)
        if cat_conf:
            for sub in cat_conf.get("subcategorias") or []:
                cantidad = por_sub[nombre].get(sub["nombre"], 0)
                extra = "  (también grupo propio)" if sub.get("grupo_propio") else ""
                print(f"    - {sub['nombre']}: {cantidad}{extra}")
            solo_cat = por_cat[nombre] - sum(por_sub[nombre].values())
            if solo_cat:
                print(f"    - (sin subcategoría): {solo_cat}")
        elif nombre != SIN_CLASIFICAR and por_sub[nombre]:
            for sub, cantidad in sorted(por_sub[nombre].items()):
                print(f"    - {sub}: {cantidad}")

    if grupos:
        print("\n=== Grupos propios (filtrables aparte) ===")
        for nombre, cantidad in sorted(grupos.items()):
            print(f"- {nombre}: {cantidad}")


def imprimir_muestras(filas: list[dict], categorias: list[dict]) -> None:
    print("\n=== Muestra por categoría ===")
    orden = [c["nombre"] for c in categorias]
    for nombre in orden:
        de_cat = [f for f in filas if f["categoria"] == nombre]
        if not de_cat:
            print(f"\n{nombre}: (sin productos)")
            continue
        print(f"\n{nombre} ({len(de_cat)} productos, muestra de hasta {MUESTRA_POR_CATEGORIA}):")
        vistos = set()
        mostrados = 0
        for fila in de_cat:
            clave = (fila["tienda"], fila["nombre"])
            if clave in vistos:
                continue
            vistos.add(clave)
            sub = f"  |  {fila['subcategoria']}" if fila["subcategoria"] else ""
            print(f"  - [{fila['tienda']}] {fila['nombre']}{sub}")
            mostrados += 1
            if mostrados >= MUESTRA_POR_CATEGORIA:
                break


def imprimir_sin_clasificar(filas: list[dict]) -> None:
    pendientes = [
        f
        for f in filas
        if f["categoria"] in {OTROS, SIN_CLASIFICAR}
        and not str(f.get("coincidencias") or "").startswith("corrección")
    ]
    print(f"\n=== Otros / sin palabras clave ({len(pendientes)}) ===")
    if not pendientes:
        print("Ninguno.")
        return
    for fila in pendientes:
        print(f"  - [{fila['tienda']}] {fila['nombre']}")


def imprimir_por_marca(filas: list[dict]) -> None:
    por_marca = [f for f in filas if str(f.get("coincidencias") or "").startswith("marca:")]
    print(f"\n=== Entraron por marca, paso 2 ({len(por_marca)}) ===")
    if not por_marca:
        print("Ninguno.")
        return
    for fila in por_marca:
        print(f"  - [{fila['tienda']}] {fila['nombre']}")
        print(f"      {fila['coincidencias']}")


def imprimir_conflictos(filas: list[dict]) -> None:
    conflictos = [f for f in filas if f["conflicto"] == "si"]
    print(f"\n=== Calce en más de una categoría o subcategoría ({len(conflictos)}) ===")
    if not conflictos:
        print("Ninguno.")
        return
    print("Asignación actual = la de menor 'prioridad' en categorias.json.\n")
    for fila in conflictos:
        print(f"  - [{fila['tienda']}] {fila['nombre']}")
        print(f"      quedó en: {fila['categoria']}"
              + (f" > {fila['subcategoria']}" if fila["subcategoria"] else ""))
        print(f"      calzó con: {fila['coincidencias']}")


def palabras_de_categorias(categorias: list[dict]) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    for cat in categorias:
        for p in cat.get("palabras") or []:
            pares.append((cat["nombre"], p))
        for sub in cat.get("subcategorias") or []:
            etiqueta = f"{cat['nombre']} > {sub['nombre']}"
            for p in sub.get("palabras") or []:
                pares.append((etiqueta, p))
    return pares


def informar_flexibilidad(filas_origen: list[dict], categorias: list[dict]) -> None:
    """Productos donde una palabra clave solo calza con el matcher flexible."""
    pares = palabras_de_categorias(categorias)
    recuperados: list[tuple[str, str, str, str]] = []
    for fila in filas_origen:
        nombre = fila.get("nombre") or ""
        texto = f"{nombre} {texto_enlace(fila.get('enlace') or '')}"
        texto_norm = normalizar(texto)
        texto_prep = preparar(texto)
        for etiqueta, palabra in pares:
            if contiene(texto_prep, palabra) and not contiene_estricto(
                texto_norm, palabra
            ):
                recuperados.append(
                    (fila.get("tienda") or "", nombre, palabra, etiqueta)
                )
                break
    print(
        f"=== Palabras que el matcher viejo no veía por forma ({len(recuperados)}) ==="
    )
    print(
        "Mayúsculas y tildes ya se ignoraban. Esto son guiones o pegados "
        "(AK47 vs ak-47, 1000rds, fullmetal).\n"
    )
    for tienda, nombre, palabra, etiqueta in recuperados[:40]:
        print(f"  - [{tienda}] {nombre}")
        print(f"      ahora calza «{palabra}» → {etiqueta}")
    if len(recuperados) > 40:
        print(f"  … y {len(recuperados) - 40} más.")
    print()


def main() -> None:
    categorias = cargar_categorias()
    marcas_replicas = cargar_marcas_replicas()
    correcciones = cargar_correcciones()
    archivos = csv_actuales()
    if not archivos:
        print("No hay CSV actuales en precios/. Nada que clasificar.")
        return

    filas_salida: list[dict] = []
    filas_origen: list[dict] = []
    print("CSV usados (el más reciente de cada tienda):")
    for ruta in archivos:
        origen = leer_filas(ruta)
        filas_origen.extend(origen)
        print(f"  - {ruta.name}: {len(origen)} productos")
        for fila in origen:
            resultado = clasificar(fila, categorias, correcciones, marcas_replicas)
            salida = {col: fila.get(col, "") for col in COLUMNAS_ORIGEN}
            salida.update(
                {
                    "categoria": resultado["categoria"],
                    "subcategoria": resultado["subcategoria"],
                    "grupo_propio": resultado["grupo_propio"],
                    "coincidencias": resultado["coincidencias"],
                    "conflicto": resultado["conflicto"],
                    "categoria_tienda": categoria_desde_enlace(fila.get("enlace") or ""),
                }
            )
            filas_salida.append(salida)

    ruta_salida = guardar(filas_salida)
    print(f"\nTotal clasificado: {len(filas_salida)} productos")
    if correcciones:
        print(f"Correcciones manuales cargadas: {len(correcciones)}")
    print(f"Salida (los CSV de precios no se tocaron):\n{ruta_salida}\n")

    informar_flexibilidad(filas_origen, categorias)
    imprimir_conteos(filas_salida, categorias)
    imprimir_muestras(filas_salida, categorias)
    imprimir_por_marca(filas_salida)
    imprimir_sin_clasificar(filas_salida)
    imprimir_conflictos(filas_salida)

    try:
        from generar_catalogo_web import generar

        print("\n=== Catálogo web ===")
        generar()
    except Exception as error:
        print(
            "La clasificación se guardó, pero no se pudo actualizar la web: "
            f"{error}"
        )


if __name__ == "__main__":
    main()
