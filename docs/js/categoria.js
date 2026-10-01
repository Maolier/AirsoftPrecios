GEARUP.comun.armarEncabezado();
var cat = GEARUP.comun.parametro("c");
var sub = GEARUP.comun.parametro("s");
var titulo = document.getElementById("titulo");
var miga = document.getElementById("miga");

if (!cat) {
  titulo.textContent = "Categoría";
  miga.textContent = "Falta el identificador de categoría.";
} else {
  var nombreCat = GEARUP.comun.nombreCategoria(cat);
  var nombreSub = GEARUP.comun.nombreSub(cat, sub);
  titulo.textContent = nombreSub || nombreCat;
  if (nombreSub) {
    miga.innerHTML =
      '<a href="categoria.html?c=' +
      encodeURIComponent(cat) +
      '">' +
      nombreCat +
      "</a> / " +
      nombreSub;
  } else {
    miga.textContent = "Todos los productos de " + nombreCat;
  }
  var lista = (GEARUP.PRODUCTOS || []).filter(function (p) {
    if (p.categoria !== cat) return false;
    if (sub && p.subcategoria !== sub) return false;
    return true;
  });
  GEARUP.comun.aplicarOrden(document.getElementById("listado"), lista);
}
