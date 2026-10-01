GEARUP.comun.armarEncabezado();

var C = GEARUP.comun;
var slotActivo = C.parametro("slot") || "";
var colIzq = document.getElementById("col-izq");
var colDer = document.getElementById("col-der");
var colCabeza = document.getElementById("slot-cabeza");
var picker = document.getElementById("picker");
var pickerListado = document.getElementById("picker-listado");
var pickerQ = document.getElementById("picker-q");
var pickerOrden = document.getElementById("picker-orden");

function htmlSlot(slot, producto, activo) {
  var clases = "loadout-slot" + (activo ? " activo" : "") + (producto ? " ocupado" : "");
  var cuerpo = producto
    ? '<div class="loadout-slot-foto">' +
      C.htmlFoto(producto) +
      "</div>" +
      '<div class="loadout-slot-datos">' +
      '<strong>' +
      C.escapar(slot.nombre) +
      "</strong>" +
      '<span class="loadout-slot-nombre">' +
      C.escapar(producto.nombre || "Producto") +
      "</span>" +
      '<span class="loadout-slot-precio">' +
      C.formatoPeso(producto.precio_actual) +
      "</span></div>" +
      '<button type="button" class="loadout-quitar" data-quitar="' +
      C.escapar(slot.id) +
      '" aria-label="Quitar">×</button>'
    : '<div class="loadout-slot-vacio">' +
      "<strong>" +
      C.escapar(slot.nombre) +
      "</strong>" +
      "<span>+ " +
      C.escapar(slot.detalle) +
      "</span></div>";
  return (
    '<div class="' +
    clases +
    '" data-slot="' +
    C.escapar(slot.id) +
    '" role="button" tabindex="0">' +
    cuerpo +
    "</div>"
  );
}

function pintarSlots() {
  var datos = C.leerLoadout();
  var izq = "";
  var der = "";
  var cabeza = "";
  C.slotsLoadout.forEach(function (slot) {
    var html = htmlSlot(slot, C.productoPorId(datos[slot.id]), slot.id === slotActivo);
    if (slot.col === "izq") izq += html;
    else if (slot.col === "der") der += html;
    else cabeza += html;
  });
  colIzq.innerHTML = izq;
  colDer.innerHTML = der;
  colCabeza.innerHTML = cabeza;
  document.getElementById("total-loadout").textContent =
    "Total: " + C.formatoPeso(C.totalLoadout());
}

function productosDelSlot(slot) {
  return (GEARUP.PRODUCTOS || []).filter(function (p) {
    return C.cabeEnSlot(p, slot);
  });
}

function htmlTarjetaPicker(producto, elegido) {
  var oferta = C.esOferta(producto);
  var pct = oferta ? Math.round(C.descuento(producto) * 100) : 0;
  return (
    '<article class="tarjeta' +
    (elegido ? " loadout-elegida" : "") +
    '">' +
    '<button type="button" class="loadout-elegir" data-elegir="' +
    C.escapar(producto.id) +
    '">' +
    '<div class="tarjeta-foto">' +
    C.htmlFoto(producto) +
    '<span class="etiqueta-tienda">' +
    C.escapar(producto.tienda_nombre || producto.tienda || "Tienda") +
    "</span>" +
    (oferta ? '<span class="sello-oferta">-' + pct + "%</span>" : "") +
    (elegido ? '<span class="sello-elegido">En el loadout</span>' : "") +
    "</div>" +
    '<div class="tarjeta-cuerpo">' +
    '<div class="tarjeta-nombre">' +
    C.escapar(producto.nombre || "Producto") +
    "</div>" +
    '<div class="precios">' +
    (oferta
      ? '<span class="precio-antes">' + C.formatoPeso(producto.precio_normal) + "</span>"
      : "") +
    '<span class="precio-actual' +
    (oferta ? " oferta" : "") +
    '">' +
    C.formatoPeso(producto.precio_actual) +
    "</span></div>" +
    '<div class="tarjeta-credito">Imagen de la tienda</div>' +
    "</div></button>" +
    '<a class="loadout-ver" href="producto.html?id=' +
    encodeURIComponent(producto.id) +
    '">Ver ficha</a></article>'
  );
}

function pintarPicker() {
  var slot = C.slotPorId(slotActivo);
  if (!slot) {
    picker.hidden = true;
    return;
  }
  picker.hidden = false;
  document.getElementById("picker-titulo").textContent = "Elegir: " + slot.nombre;
  document.getElementById("picker-miga").textContent = slot.detalle;
  var q = (pickerQ.value || "").trim().toLowerCase();
  var lista = productosDelSlot(slot).filter(function (p) {
    if (!q) return true;
    return String(p.nombre || "")
      .toLowerCase()
      .indexOf(q) !== -1;
  });
  lista = C.ordenarLista(lista, pickerOrden.value);
  var actual = C.leerLoadout()[slot.id];
  if (!lista.length) {
    pickerListado.innerHTML = '<div class="vacio">No hay productos para este espacio.</div>';
    return;
  }
  pickerListado.innerHTML =
    '<div class="rejilla">' +
    lista
      .map(function (p) {
        return htmlTarjetaPicker(p, p.id === actual);
      })
      .join("") +
    "</div>";
}

function abrirSlot(id) {
  slotActivo = id;
  var url = new URL(window.location.href);
  if (id) url.searchParams.set("slot", id);
  else url.searchParams.delete("slot");
  history.replaceState({}, "", url);
  pintarSlots();
  pintarPicker();
  if (id && !picker.hidden) {
    picker.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function onClickTablero(evento) {
  var quitar = evento.target.closest("[data-quitar]");
  if (quitar) {
    evento.preventDefault();
    evento.stopPropagation();
    C.asignarLoadout(quitar.getAttribute("data-quitar"), "");
    pintarSlots();
    pintarPicker();
    return;
  }
  var boton = evento.target.closest("[data-slot]");
  if (!boton) return;
  abrirSlot(boton.getAttribute("data-slot"));
}

document.querySelector(".loadout-tablero").addEventListener("click", onClickTablero);
document.querySelector(".loadout-tablero").addEventListener("keydown", function (evento) {
  if (evento.key !== "Enter" && evento.key !== " ") return;
  var slot = evento.target.closest("[data-slot]");
  if (!slot || evento.target.closest("[data-quitar]")) return;
  evento.preventDefault();
  abrirSlot(slot.getAttribute("data-slot"));
});

pickerListado.addEventListener("click", function (evento) {
  var elegir = evento.target.closest("[data-elegir]");
  if (!elegir || !slotActivo) return;
  var id = elegir.getAttribute("data-elegir");
  var actual = C.leerLoadout()[slotActivo];
  C.asignarLoadout(slotActivo, actual === id ? "" : id);
  pintarSlots();
  pintarPicker();
});

pickerQ.addEventListener("input", pintarPicker);
pickerOrden.addEventListener("change", pintarPicker);

document.getElementById("cerrar-picker").addEventListener("click", function () {
  abrirSlot("");
});

document.getElementById("vaciar-loadout").addEventListener("click", function () {
  if (!C.itemsLoadout().length) return;
  C.vaciarLoadout();
  pintarSlots();
  pintarPicker();
});

pintarSlots();
if (slotActivo && C.slotPorId(slotActivo)) pintarPicker();
