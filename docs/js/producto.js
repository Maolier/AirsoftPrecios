function htmlLoadoutFicha(producto) {
  var slot = GEARUP.comun.slotParaProducto(producto);
  if (!slot) return "";
  var actual = GEARUP.comun.leerLoadout()[slot.id];
  var ya = actual === producto.id;
  return (
    '<div class="ficha-loadout">' +
    '<button type="button" class="boton-loadout' +
    (ya ? " activo" : "") +
    '" id="btn-loadout" data-slot="' +
    GEARUP.comun.escapar(slot.id) +
    '">' +
    (ya ? "Quitar del loadout" : "Añadir al loadout · " + slot.nombre) +
    "</button>" +
    '<a href="loadout.html?slot=' +
    encodeURIComponent(slot.id) +
    '">Ver loadout</a></div>'
  );
}

GEARUP.comun.armarEncabezado();
var id = GEARUP.comun.parametro("id");
var producto = (GEARUP.PRODUCTOS || []).find(function (p) {
  return p.id === id;
});
var caja = document.getElementById("ficha");
if (!producto) {
  caja.innerHTML = '<p class="vacio">No encontramos ese producto.</p>';
} else {
  var oferta = GEARUP.comun.esOferta(producto);
  var cat = GEARUP.comun.nombreCategoria(producto.categoria);
  var sub = GEARUP.comun.nombreSub(producto.categoria, producto.subcategoria);
  var enlace = producto.enlace_tienda || "";
  var tienda = GEARUP.comun.escapar(producto.tienda_nombre || producto.tienda || "la tienda");
  var botonComprar = /^https?:\/\//i.test(enlace)
    ? '<a class="boton-comprar" href="' +
      GEARUP.comun.escapar(enlace) +
      '" target="_blank" rel="noopener">Comprar en ' +
      tienda +
      "</a>"
    : '<span class="boton-comprar">Enlace no disponible</span>';
  document.title = (producto.nombre || "Producto") + " · GearUp";
  caja.innerHTML =
    '<div><div class="ficha-foto">' +
    GEARUP.comun.htmlFoto(producto) +
    '</div><p class="ficha-credito">Imagen de la tienda</p></div>' +
    "<div>" +
    '<p class="miga"><a href="categoria.html?c=' +
    encodeURIComponent(producto.categoria || "otros") +
    '">' +
    GEARUP.comun.escapar(cat) +
    "</a>" +
    (sub ? " / " + GEARUP.comun.escapar(sub) : "") +
    "</p>" +
    "<h1>" +
    GEARUP.comun.escapar(producto.nombre || "Producto") +
    "</h1>" +
    '<p class="ficha-tienda">' +
    tienda +
    "</p>" +
    (oferta
      ? '<span class="precio-antes">' +
        GEARUP.comun.formatoPeso(producto.precio_normal) +
        "</span>"
      : "") +
    '<div class="precio-actual' +
    (oferta ? " oferta" : "") +
    '">' +
    GEARUP.comun.formatoPeso(producto.precio_actual) +
    "</div>" +
    botonComprar +
    htmlLoadoutFicha(producto) +
    '<div class="bloque-grafico"><h2>Historial de precio en esta tienda</h2>' +
    '<svg class="grafico" id="grafico" role="img" aria-label="Historial de precio"></svg></div>' +
    '<div class="proximos">' +
    '<div class="proximo"><strong>Comparar en otras tiendas</strong>Próximamente: el mismo producto en el resto de las tiendas.</div>' +
    '<div class="proximo"><strong>Especificaciones</strong>Próximamente: sistema, peso, material y ficha técnica.</div>' +
    "</div></div>";
  GEARUP.comun.dibujarGrafico(document.getElementById("grafico"), producto.historial || []);
  var btnLoadout = document.getElementById("btn-loadout");
  if (btnLoadout) {
    btnLoadout.addEventListener("click", function () {
      var slotId = btnLoadout.getAttribute("data-slot");
      var actual = GEARUP.comun.leerLoadout()[slotId];
      var ya = actual === producto.id;
      GEARUP.comun.asignarLoadout(slotId, ya ? "" : producto.id);
      var ahora = GEARUP.comun.leerLoadout()[slotId] === producto.id;
      btnLoadout.classList.toggle("activo", ahora);
      btnLoadout.textContent = ahora
        ? "Quitar del loadout"
        : "Añadir al loadout · " + GEARUP.comun.slotPorId(slotId).nombre;
    });
  }
}
