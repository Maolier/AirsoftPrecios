"""Funciones compartidas por los lectores."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

PAUSA_POR_DEFECTO = 1.5

_NO_ES_FOTO = re.compile(
    r"logo|webpay|pago_web|favicon|placeholder|\{product\.image\}",
    re.I,
)


def url_imagen(valor: str, base: str = "") -> str:
    """Deja solo una URL http(s) de foto de producto. Si no sirve, vacío."""
    texto = unescape((valor or "").strip())
    if not texto or texto in {"#", "/", "None", "null"}:
        return ""
    if texto.startswith("//"):
        texto = "https:" + texto
    elif base and not re.match(r"^https?://", texto, re.I):
        texto = urljoin(base.rstrip("/") + "/", texto.lstrip("/"))
    if not re.match(r"^https?://", texto, re.I):
        return ""
    if _NO_ES_FOTO.search(texto):
        return ""
    return texto.split()[0]


def pausa_de(tienda: dict) -> float:
    """Segundos de espera entre peticiones. Si no viene en tiendas.json, usa 1,5."""
    try:
        valor = float(tienda.get("pausa", PAUSA_POR_DEFECTO))
    except (TypeError, ValueError):
        return PAUSA_POR_DEFECTO
    if valor < 0:
        return PAUSA_POR_DEFECTO
    return valor
