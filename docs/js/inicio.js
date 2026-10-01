GEARUP.comun.armarEncabezado();
var ofertas = (GEARUP.PRODUCTOS || []).filter(GEARUP.comun.esOferta).sort(function (a, b) {
  return GEARUP.comun.descuento(b) - GEARUP.comun.descuento(a);
});
GEARUP.comun.pintarRejilla(document.getElementById("ofertas"), ofertas);
