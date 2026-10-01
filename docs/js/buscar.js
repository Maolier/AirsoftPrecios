GEARUP.comun.armarEncabezado();
var q = GEARUP.comun.parametro("q").trim().toLowerCase();
document.getElementById("titulo").textContent = q
  ? "Resultados para \u201c" + GEARUP.comun.parametro("q") + "\u201d"
  : "Búsqueda";
var lista = (GEARUP.PRODUCTOS || []).filter(function (p) {
  if (!q) return false;
  var texto = [p.nombre, p.tienda_nombre, p.tienda].join(" ").toLowerCase();
  return texto.indexOf(q) !== -1;
});
document.getElementById("miga").textContent = lista.length + " producto(s)";
GEARUP.comun.aplicarOrden(document.getElementById("listado"), lista);
