GEARUP.comun.armarEncabezado();

var C = GEARUP.comun;
var slotActivo = C.parametro("slot") || "";
var colIzq = document.getElementById("col-izq");
var colDer = document.getElementById("col-der");
var colCabeza = document.getElementById("slot-cabeza");
var slotsFaciales = document.getElementById("slots-faciales");
var modosFacial = document.getElementById("modos-facial");
var zonaFacial = document.getElementById("zona-facial");
var extras = document.getElementById("extras-loadout");
var picker = document.getElementById("picker");
var pickerListado = document.getElementById("picker-listado");
var pickerQ = document.getElementById("picker-q");
var pickerOrden = document.getElementById("picker-orden");
var LIMITE_CATALOGO = 80;

function sinAcento(texto) {
  return String(texto || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

if (slotActivo && !C.slotPorId(slotActivo)) slotActivo = "";

function htmlSlot(slot, producto, activo) {
  var clases = "loadout-slot" + (activo ? " activo" : "") + (producto ? " ocupado" : "");
  var cuerpo = producto
    ? '<div class="loadout-slot-foto">' +
      C.htmlFoto(producto) +
      "</div>" +
      '<div class="loadout-slot-datos">' +
      "<strong>" +
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

function htmlModos(modo) {
  return C.modosFacial
    .map(function (item) {
      return (
        '<label class="loadout-modo">' +
        '<input type="radio" name="modo-facial" value="' +
        C.escapar(item.id) +
        '"' +
        (item.id === modo ? " checked" : "") +
        "> " +
        C.escapar(item.nombre) +
        "</label>"
      );
    })
    .join("");
}

function htmlLista(slot, datos) {
  var ids = Array.isArray(datos[slot.id]) ? datos[slot.id] : [];
  var filas = ids
    .map(function (id) {
      var producto = C.productoPorId(id);
      if (!producto) return "";
      return (
        '<li class="loadout-lista-item">' +
        '<div class="loadout-slot-foto">' +
        C.htmlFoto(producto) +
        "</div>" +
        '<div class="loadout-slot-datos">' +
        '<span class="loadout-slot-nombre">' +
        C.escapar(producto.nombre || "Producto") +
        "</span>" +
        '<span class="loadout-slot-precio">' +
        C.formatoPeso(producto.precio_actual) +
        "</span></div>" +
        '<button type="button" class="loadout-quitar" data-quitar-lista="' +
        C.escapar(slot.id) +
        '" data-producto="' +
        C.escapar(producto.id) +
        '" aria-label="Quitar">×</button></li>'
      );
    })
    .join("");
  var cuerpo = filas
    ? '<ul class="loadout-lista-items">' + filas + "</ul>"
    : '<p class="loadout-lista-vacio">Nada añadido todavía.</p>';
  return (
    '<section class="loadout-lista' +
    (slot.id === slotActivo ? " activo" : "") +
    '">' +
    '<div class="loadout-lista-cabecera">' +
    "<div><strong>" +
    C.escapar(slot.nombre) +
    "</strong><span>" +
    C.escapar(slot.detalle) +
    "</span></div>" +
    '<button type="button" class="boton-texto" data-slot="' +
    C.escapar(slot.id) +
    '">+ Añadir</button></div>' +
    cuerpo +
    "</section>"
  );
}

function pintarSlots() {
  var datos = C.leerLoadout();
  var modo = datos.modoFacial || "todos";
  var izq = "";
  var der = "";
  var cabeza = "";
  var facial = "";
  C.slotsLoadout.forEach(function (slot) {
    if (!C.slotVisible(slot, modo)) return;
    var html = htmlSlot(slot, C.productoPorId(datos[slot.id]), slot.id === slotActivo);
    if (slot.grupo === "izq") izq += html;
    else if (slot.grupo === "der") der += html;
    else if (slot.grupo === "cabeza") cabeza += html;
    else if (slot.grupo === "facial") facial += html;
  });
  colIzq.innerHTML = izq;
  colDer.innerHTML = der;
  colCabeza.innerHTML = cabeza;
  slotsFaciales.innerHTML = facial;
  modosFacial.innerHTML = htmlModos(modo);
  zonaFacial.classList.toggle("modo-solo", modo !== "todos");
  extras.innerHTML = C.listasLoadout
    .map(function (slot) {
      return htmlLista(slot, datos);
    })
    .join("");
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
  if (!slot || (slot.grupo === "facial" && !C.slotVisible(slot))) {
    picker.hidden = true;
    return;
  }
  picker.hidden = false;
  document.getElementById("picker-titulo").textContent =
    (slot.lista ? "Añadir: " : "Elegir: ") + slot.nombre;
  document.getElementById("picker-miga").textContent = slot.detalle;
  var q = sinAcento((pickerQ.value || "").trim());
  if (slot.catalogo && q.length < 2) {
    pickerListado.innerHTML =
      '<div class="vacio">Escribe al menos 2 letras para buscar en el catálogo.</div>';
    return;
  }
  var lista = productosDelSlot(slot).filter(function (p) {
    if (!q) return true;
    return sinAcento(p.nombre).indexOf(q) !== -1;
  });
  lista = C.ordenarLista(lista, pickerOrden.value);
  var datos = C.leerLoadout();
  var elegido = slot.lista
    ? function (id) {
        return (datos[slot.id] || []).indexOf(id) !== -1;
      }
    : function (id) {
        return datos[slot.id] === id;
      };
  if (!lista.length) {
    pickerListado.innerHTML = '<div class="vacio">No hay productos para este espacio.</div>';
    return;
  }
  var aviso = "";
  var visible = lista;
  if (slot.catalogo && lista.length > LIMITE_CATALOGO) {
    visible = lista.slice(0, LIMITE_CATALOGO);
    aviso =
      '<p class="loadout-aviso">Mostrando ' +
      LIMITE_CATALOGO +
      " de " +
      lista.length +
      ". Afina el filtro para ver el resto.</p>";
  }
  pickerListado.innerHTML =
    aviso +
    '<div class="rejilla">' +
    visible
      .map(function (p) {
        return htmlTarjetaPicker(p, elegido(p.id));
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

function onClickCuerpo(evento) {
  var quitarLista = evento.target.closest("[data-quitar-lista]");
  if (quitarLista) {
    evento.preventDefault();
    evento.stopPropagation();
    C.quitarDeLista(
      quitarLista.getAttribute("data-quitar-lista"),
      quitarLista.getAttribute("data-producto")
    );
    pintarSlots();
    pintarPicker();
    return;
  }
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
  if (!boton || picker.contains(boton)) return;
  abrirSlot(boton.getAttribute("data-slot"));
}

document.querySelector("main.contenido").addEventListener("click", onClickCuerpo);
document.querySelector(".loadout-tablero").addEventListener("keydown", function (evento) {
  if (evento.key !== "Enter" && evento.key !== " ") return;
  var slot = evento.target.closest("[data-slot]");
  if (!slot || evento.target.closest("[data-quitar]")) return;
  evento.preventDefault();
  abrirSlot(slot.getAttribute("data-slot"));
});

modosFacial.addEventListener("change", function (evento) {
  var input = evento.target;
  if (!input || input.name !== "modo-facial") return;
  C.definirModoFacial(input.value);
  var slot = C.slotPorId(slotActivo);
  if (slot && slot.grupo === "facial" && !C.slotVisible(slot)) abrirSlot("");
  else {
    pintarSlots();
    pintarPicker();
  }
});

pickerListado.addEventListener("click", function (evento) {
  var elegir = evento.target.closest("[data-elegir]");
  if (!elegir || !slotActivo) return;
  var id = elegir.getAttribute("data-elegir");
  var slot = C.slotPorId(slotActivo);
  if (!slot) return;
  if (slot.lista) C.alternarListaLoadout(slotActivo, id);
  else {
    var actual = C.leerLoadout()[slotActivo];
    C.asignarLoadout(slotActivo, actual === id ? "" : id);
  }
  pintarSlots();
  pintarPicker();
});

pickerQ.addEventListener("input", pintarPicker);
pickerOrden.addEventListener("change", pintarPicker);

document.getElementById("cerrar-picker").addEventListener("click", function () {
  abrirSlot("");
});

document.getElementById("vaciar-loadout").addEventListener("click", function () {
  if (!C.loadoutTieneDatos()) return;
  C.vaciarLoadout();
  pintarSlots();
  pintarPicker();
});

pintarSlots();
if (slotActivo && C.slotPorId(slotActivo)) pintarPicker();
