(function () {
  function parametro(nombre) {
    return new URLSearchParams(window.location.search).get(nombre) || "";
  }

  function escapar(texto) {
    return String(texto == null ? "" : texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatoPeso(valor) {
    return "$" + Math.round(Number(valor) || 0).toLocaleString("es-CL");
  }

  function esOferta(producto) {
    return Number(producto.precio_actual) < Number(producto.precio_normal);
  }

  function descuento(producto) {
    var normal = Number(producto.precio_normal);
    if (!normal) return 0;
    return (normal - Number(producto.precio_actual)) / normal;
  }

  function ordenarLista(productos, modo) {
    var copia = (productos || []).slice();
    if (modo === "menor") {
      copia.sort(function (a, b) {
        return Number(a.precio_actual) - Number(b.precio_actual);
      });
    } else if (modo === "mayor") {
      copia.sort(function (a, b) {
        return Number(b.precio_actual) - Number(a.precio_actual);
      });
    } else if (modo === "descuento") {
      copia.sort(function (a, b) {
        return descuento(b) - descuento(a);
      });
    }
    return copia;
  }

  function aplicarOrden(destino, productos) {
    var selector = document.getElementById("orden");
    function pintar() {
      var modo = selector ? selector.value : parametro("orden");
      pintarRejilla(destino, ordenarLista(productos, modo));
      if (!selector) return;
      var url = new URL(window.location.href);
      if (modo) url.searchParams.set("orden", modo);
      else url.searchParams.delete("orden");
      history.replaceState({}, "", url);
    }
    if (selector) {
      var inicial = parametro("orden");
      if (inicial) selector.value = inicial;
      selector.addEventListener("change", pintar);
    }
    pintar();
  }

  function categoriaPorId(id) {
    return (GEARUP.MENU || []).find(function (c) {
      return c.id === id;
    });
  }

  function nombreCategoria(id) {
    var cat = categoriaPorId(id);
    return cat ? cat.nombre : id;
  }

  function nombreSub(catId, subId) {
    var cat = categoriaPorId(catId);
    if (!cat || !subId) return "";
    var sub = (cat.sub || []).find(function (s) {
      return s.id === subId;
    });
    return sub ? sub.nombre : subId;
  }

  function colorCategoria(id) {
    var mapa = {
      replicas: "#3f5340",
      cargadores: "#5a4a32",
      municion: "#6b3a2a",
      proteccion: "#2f4a5a",
      uniforme: "#3d4a32",
      externos: "#4a3f55",
      internos: "#35524a",
      repuestos: "#5a4038",
      baterias: "#3a4d5c",
      packs: "#5c4a20",
      otros: "#4a4a46",
    };
    return mapa[id] || "#4a4a46";
  }

  function respaldoProducto(producto) {
    var color = colorCategoria(producto.categoria);
    var iniciales = (producto.tienda_nombre || "?")
      .split(" ")
      .map(function (p) {
        return p[0];
      })
      .join("")
      .slice(0, 3)
      .toUpperCase();
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">' +
      '<rect width="400" height="400" fill="' +
      color +
      '"/>' +
      '<text x="200" y="190" text-anchor="middle" fill="#f4f1ea" font-size="28" font-family="Segoe UI, sans-serif">' +
      iniciales +
      "</text>" +
      "</svg>";
    return "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg);
  }

  function urlFotoTienda(producto) {
    var url = String((producto && producto.imagen) || "").trim();
    return /^https?:\/\//i.test(url) ? url : "";
  }

  function imagenProducto(producto) {
    return urlFotoTienda(producto) || respaldoProducto(producto);
  }

  function htmlFoto(producto) {
    return (
      '<img alt="" src="' +
      escapar(imagenProducto(producto)) +
      '" referrerpolicy="no-referrer" loading="lazy" data-respaldo="' +
      escapar(respaldoProducto(producto)) +
      '" onerror="this.onerror=null;this.src=this.getAttribute(\'data-respaldo\')">'
    );
  }

  function tarjetaHTML(producto) {
    var oferta = esOferta(producto);
    var pct = oferta ? Math.round(descuento(producto) * 100) : 0;
    return (
      '<a class="tarjeta" href="producto.html?id=' +
      encodeURIComponent(producto.id) +
      '">' +
      '<div class="tarjeta-foto">' +
      htmlFoto(producto) +
      '<span class="etiqueta-tienda">' +
      escapar(producto.tienda_nombre || producto.tienda || "Tienda") +
      "</span>" +
      (oferta ? '<span class="sello-oferta">-' + pct + "%</span>" : "") +
      "</div>" +
      '<div class="tarjeta-cuerpo">' +
      '<div class="tarjeta-nombre">' +
      escapar(producto.nombre || "Producto") +
      "</div>" +
      '<div class="precios">' +
      (oferta
        ? '<span class="precio-antes">' + formatoPeso(producto.precio_normal) + "</span>"
        : "") +
      '<span class="precio-actual' +
      (oferta ? " oferta" : "") +
      '">' +
      formatoPeso(producto.precio_actual) +
      "</span>" +
      "</div>" +
      '<div class="tarjeta-credito">Imagen de la tienda</div>' +
      "</div></a>"
    );
  }

  function pintarRejilla(destino, productos) {
    if (!destino) return;
    if (!productos.length) {
      destino.innerHTML = '<div class="vacio">No hay productos en esta vista.</div>';
      return;
    }
    destino.innerHTML =
      '<div class="rejilla">' + productos.map(tarjetaHTML).join("") + "</div>";
  }

  function svgLucide(contenido) {
    return (
      '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
      contenido +
      "</svg>"
    );
  }

  // Íconos Lucide (MIT): mismo trazo, 24×24. Repuestos ya no está en el menú.
  var ICONOS_MENU = {
    replicas: svgLucide(
      '<circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/>'
    ),
    cargadores: svgLucide(
      '<rect x="7" y="3" width="10" height="18" rx="1.5"/><path d="M9 3v3h6V3"/><path d="M9 11h6"/><path d="M9 15h6"/>'
    ),
    municion: svgLucide(
      '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>'
    ),
    proteccion: svgLucide(
      '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
    ),
    uniforme: svgLucide(
      '<path d="M4 10a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M8 21v-5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v5"/><path d="M8 10h8"/>'
    ),
    externos: svgLucide(
      '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
    ),
    internos: svgLucide(
      '<path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"/><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>'
    ),
    baterias: svgLucide(
      '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
    ),
    packs: svgLucide(
      '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5A4.8 8 0 0 1 12 8a4.8 8 0 0 1 4.5-5 2.5 2.5 0 0 1 0 5"/>'
    ),
    otros: svgLucide(
      '<circle class="nav-icon-punto" cx="5" cy="12" r="1.7"/><circle class="nav-icon-punto" cx="12" cy="12" r="1.7"/><circle class="nav-icon-punto" cx="19" cy="12" r="1.7"/>'
    ),
  };

  function iconoCategoria(id) {
    return ICONOS_MENU[id] || ICONOS_MENU.otros;
  }

  var SLOTS_LOADOUT = [
    {
      id: "casco",
      nombre: "Casco",
      detalle: "Cascos",
      categoria: "proteccion",
      sub: "cascos",
      grupo: "cabeza",
    },
    {
      id: "audifonos",
      nombre: "Audífonos",
      detalle: "Headset y protección auditiva",
      grupo: "cabeza",
      palabras: [
        "headset",
        "comtac",
        "ptt",
        "protector auditivo",
        "proteccion auditiva",
        "ear pro",
        "ear protection",
        "sordina",
        "laringofono",
        "manos libres",
      ],
      excluir: ["adaptador", "adaptor", "montura", "mount", "mascara", "mask"],
    },
    {
      id: "lentes",
      nombre: "Antiparra / lentes",
      detalle: "Antiparras y lentes",
      categoria: "proteccion",
      sub: "mascaras-lentes",
      grupo: "facial",
      modo: "lentes",
      palabras: ["lente", "antiparra", "goggle", "gafa", "wiley", "pyramex"],
      excluir: ["mascara", "mask", "balaclava", "pasamontana"],
    },
    {
      id: "mascara",
      nombre: "Máscara",
      detalle: "Máscaras",
      categoria: "proteccion",
      sub: "mascaras-lentes",
      grupo: "facial",
      modo: "mascara",
      palabras: ["mascara", "mask"],
      excluir: ["balaclava", "pasamontana"],
    },
    {
      id: "balaclava",
      nombre: "Balaclava",
      detalle: "Balaclavas y pasamontañas",
      categoria: "uniforme",
      sub: "gorras",
      grupo: "facial",
      modo: "balaclava",
      palabras: ["balaclava", "pasamontana"],
    },
    {
      id: "chestplate",
      nombre: "Chest plate",
      detalle: "Chalecos y plate carriers",
      categoria: "uniforme",
      sub: "chalecos",
      grupo: "izq",
    },
    {
      id: "chestrig",
      nombre: "Chest rig",
      detalle: "Pouches y bolsos",
      categoria: "uniforme",
      sub: "pouches",
      grupo: "der",
    },
    {
      id: "guantes",
      nombre: "Guantes",
      detalle: "Guantes",
      categoria: "proteccion",
      sub: "guantes",
      grupo: "izq",
    },
    {
      id: "adicional",
      nombre: "Protección adicional",
      detalle: "Rodilleras, coderas",
      categoria: "proteccion",
      sub: "rodilleras-coderas",
      grupo: "der",
    },
    {
      id: "botas",
      nombre: "Botas",
      detalle: "Botas",
      categoria: "uniforme",
      sub: "botas",
      grupo: "izq",
    },
  ];

  var LISTAS_LOADOUT = [
    {
      id: "accesorios",
      nombre: "Accesorios",
      detalle: "Cualquier producto, salvo réplicas",
      lista: true,
      catalogo: true,
    },
    {
      id: "vestimenta",
      nombre: "Vestimenta",
      detalle: "Poleras, pantalones, chaquetas y más",
      lista: true,
      categoria: "uniforme",
      sub: "uniformes",
    },
  ];

  var MODOS_FACIAL = [
    { id: "lentes", nombre: "Solo lentes" },
    { id: "mascara", nombre: "Solo máscara" },
    { id: "balaclava", nombre: "Solo balaclava" },
    { id: "todos", nombre: "Todos" },
  ];

  var CLAVE_LOADOUT = "gearup-loadout";

  function todosLosSlots() {
    return SLOTS_LOADOUT.concat(LISTAS_LOADOUT);
  }

  function slotPorId(id) {
    return todosLosSlots().find(function (s) {
      return s.id === id;
    });
  }

  function sinAcento(texto) {
    return String(texto || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function coincidePalabras(producto, slot) {
    var texto = sinAcento(producto.nombre);
    if (slot.palabras && slot.palabras.length) {
      var ok = slot.palabras.some(function (palabra) {
        return texto.indexOf(sinAcento(palabra)) !== -1;
      });
      if (!ok) return false;
    }
    if (slot.excluir && slot.excluir.length) {
      var mala = slot.excluir.some(function (palabra) {
        return texto.indexOf(sinAcento(palabra)) !== -1;
      });
      if (mala) return false;
    }
    return true;
  }

  function productoPorId(id) {
    if (!id) return null;
    return (GEARUP.PRODUCTOS || []).find(function (p) {
      return p.id === id;
    }) || null;
  }

  function cabeEnSlot(producto, slot) {
    if (!producto || !slot) return false;
    if (slot.catalogo) return producto.categoria !== "replicas";
    if (!slot.categoria && producto.categoria === "replicas") return false;
    if (slot.categoria && producto.categoria !== slot.categoria) return false;
    if (slot.sub && producto.subcategoria !== slot.sub) return false;
    if ((slot.palabras && slot.palabras.length) || (slot.excluir && slot.excluir.length)) {
      return coincidePalabras(producto, slot);
    }
    return true;
  }

  function slotParaProducto(producto) {
    if (!producto) return null;
    var fijo = SLOTS_LOADOUT.find(function (slot) {
      return cabeEnSlot(producto, slot);
    });
    if (fijo) return fijo;
    var lista = LISTAS_LOADOUT.find(function (slot) {
      return slot.id !== "accesorios" && cabeEnSlot(producto, slot);
    });
    if (lista) return lista;
    var accesorios = slotPorId("accesorios");
    if (accesorios && cabeEnSlot(producto, accesorios)) return accesorios;
    return null;
  }

  function modoFacialValido(modo) {
    return MODOS_FACIAL.some(function (item) {
      return item.id === modo;
    });
  }

  function slotVisible(slot, modo) {
    if (!slot || slot.grupo !== "facial") return true;
    var actual = modo || (leerLoadout().modoFacial || "todos");
    return actual === "todos" || slot.modo === actual;
  }

  function leerLoadout() {
    var datos = {};
    try {
      var bruto = localStorage.getItem(CLAVE_LOADOUT);
      var leido = bruto ? JSON.parse(bruto) : {};
      if (leido && typeof leido === "object" && !Array.isArray(leido)) datos = leido;
    } catch (e) {
      datos = {};
    }
    if (normalizarLoadout(datos)) {
      localStorage.setItem(CLAVE_LOADOUT, JSON.stringify(datos));
    }
    return datos;
  }

  function normalizarLoadout(datos) {
    var cambio = false;
    if (datos.cabeza) {
      if (!datos.casco) datos.casco = datos.cabeza;
      delete datos.cabeza;
      cambio = true;
    }
    if (Object.prototype.hasOwnProperty.call(datos, "facial")) {
      delete datos.facial;
      cambio = true;
    }
    if (Object.prototype.hasOwnProperty.call(datos, "replica")) {
      delete datos.replica;
      cambio = true;
    }
    if (Object.prototype.hasOwnProperty.call(datos, "bucal")) {
      delete datos.bucal;
      cambio = true;
    }
    if (!Array.isArray(datos.accesorios)) {
      datos.accesorios = [];
      cambio = true;
    }
    if (!Array.isArray(datos.vestimenta)) {
      datos.vestimenta = [];
      cambio = true;
    }
    if (!modoFacialValido(datos.modoFacial)) {
      datos.modoFacial = "todos";
      cambio = true;
    }
    return cambio;
  }

  function guardarLoadout(datos) {
    localStorage.setItem(CLAVE_LOADOUT, JSON.stringify(datos || {}));
    actualizarCuentaLoadout();
  }

  function asignarLoadout(slotId, productoId) {
    var datos = leerLoadout();
    if (productoId) datos[slotId] = productoId;
    else delete datos[slotId];
    guardarLoadout(datos);
    return datos;
  }

  function alternarListaLoadout(slotId, productoId) {
    var datos = leerLoadout();
    var lista = Array.isArray(datos[slotId]) ? datos[slotId].slice() : [];
    var indice = lista.indexOf(productoId);
    if (indice === -1) lista.push(productoId);
    else lista.splice(indice, 1);
    datos[slotId] = lista;
    guardarLoadout(datos);
    return datos;
  }

  function quitarDeLista(slotId, productoId) {
    var datos = leerLoadout();
    var lista = Array.isArray(datos[slotId]) ? datos[slotId].slice() : [];
    datos[slotId] = lista.filter(function (id) {
      return id !== productoId;
    });
    guardarLoadout(datos);
    return datos;
  }

  function definirModoFacial(modo) {
    var datos = leerLoadout();
    datos.modoFacial = modoFacialValido(modo) ? modo : "todos";
    guardarLoadout(datos);
    return datos;
  }

  function vaciarLoadout() {
    guardarLoadout({
      accesorios: [],
      vestimenta: [],
      modoFacial: "todos",
    });
  }

  function productoEnLoadout(slotId, productoId) {
    if (!productoId) return false;
    var datos = leerLoadout();
    var slot = slotPorId(slotId);
    if (!slot) return false;
    if (slot.lista) {
      return Array.isArray(datos[slotId]) && datos[slotId].indexOf(productoId) !== -1;
    }
    return datos[slotId] === productoId;
  }

  function loadoutTieneDatos() {
    var datos = leerLoadout();
    if ((datos.modoFacial || "todos") !== "todos") return true;
    if (SLOTS_LOADOUT.some(function (slot) { return !!datos[slot.id]; })) return true;
    return LISTAS_LOADOUT.some(function (slot) {
      return Array.isArray(datos[slot.id]) && datos[slot.id].length > 0;
    });
  }

  function itemsLoadout() {
    var datos = leerLoadout();
    var modo = datos.modoFacial || "todos";
    var items = [];
    SLOTS_LOADOUT.forEach(function (slot) {
      if (!slotVisible(slot, modo)) return;
      var producto = productoPorId(datos[slot.id]);
      if (producto) items.push({ slot: slot, producto: producto });
    });
    LISTAS_LOADOUT.forEach(function (slot) {
      var ids = Array.isArray(datos[slot.id]) ? datos[slot.id] : [];
      ids.forEach(function (id) {
        var producto = productoPorId(id);
        if (producto) items.push({ slot: slot, producto: producto });
      });
    });
    return items;
  }

  function totalLoadout() {
    return itemsLoadout().reduce(function (suma, item) {
      return suma + (Number(item.producto.precio_actual) || 0);
    }, 0);
  }

  function actualizarCuentaLoadout() {
    var marca = document.querySelector(".loadout-cuenta");
    if (!marca) return;
    var n = itemsLoadout().length;
    marca.textContent = String(n);
    if (n) marca.removeAttribute("hidden");
    else marca.setAttribute("hidden", "");
  }

  var ICONO_LOADOUT = svgLucide(
    '<circle cx="12" cy="8" r="4"/><path d="M4 20a8 8 0 0 1 16 0"/>'
  );

  function htmlMenu() {
    return (GEARUP.MENU || [])
      .map(function (cat) {
        var subs = (cat.sub || [])
          .map(function (sub) {
            return (
              '<a href="categoria.html?c=' +
              cat.id +
              "&s=" +
              sub.id +
              '">' +
              sub.nombre +
              "</a>"
            );
          })
          .join("");
        return (
          '<li class="nav-item">' +
          '<a class="nav-enlace" href="categoria.html?c=' +
          cat.id +
          '">' +
          iconoCategoria(cat.id) +
          '<span class="nav-texto">' +
          escapar(cat.nombre) +
          "</span></a>" +
          (subs ? '<div class="sublista">' + subs + "</div>" : "") +
          "</li>"
        );
      })
      .join("");
  }

  function armarEncabezado() {
    var q = parametro("q");
    var enLoadout = /loadout\.html$/i.test(window.location.pathname);
    document.body.insertAdjacentHTML(
      "afterbegin",
      '<header class="encabezado">' +
        '<div class="marca-barra">' +
        '<a class="marca" href="index.html">Gear<span>Up</span></a>' +
        '<div class="marca-acciones">' +
        '<a class="enlace-loadout' +
        (enLoadout ? " activo" : "") +
        '" href="loadout.html">' +
        ICONO_LOADOUT +
        "<span>Equipo/Loadout</span>" +
        '<span class="loadout-cuenta" hidden>0</span></a>' +
        '<button class="boton-menu" type="button" aria-label="Abrir menú">☰</button>' +
        "</div></div>" +
        '<div class="buscador"><form action="buscar.html" method="get">' +
        '<input type="search" name="q" placeholder="Buscar productos, marcas o tiendas" value="' +
        q.replace(/"/g, "&quot;") +
        '" required>' +
        "<button type=\"submit\">Buscar</button></form></div>" +
        '<nav class="nav-principal" id="nav-principal"><ul class="nav-lista">' +
        htmlMenu() +
        "</ul></nav></header>"
    );
    actualizarCuentaLoadout();

    var boton = document.querySelector(".boton-menu");
    var nav = document.getElementById("nav-principal");
    boton.addEventListener("click", function () {
      nav.classList.toggle("abierto");
    });

    nav.querySelectorAll(".nav-item").forEach(function (item) {
      var enlace = item.querySelector(".nav-enlace");
      var sub = item.querySelector(".sublista");
      if (!sub) return;
      enlace.addEventListener("click", function (evento) {
        if (window.innerWidth > 800) return;
        if (!item.classList.contains("abierto")) {
          evento.preventDefault();
          nav.querySelectorAll(".nav-item.abierto").forEach(function (otro) {
            if (otro !== item) otro.classList.remove("abierto");
          });
          item.classList.add("abierto");
        }
      });
    });
  }

  function formatoFechaCorta(iso) {
    var m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return iso || "";
    return m[3] + "/" + m[2] + "/" + m[1];
  }

  function dibujarGrafico(svg, historial) {
    if (!svg || !historial || historial.length < 1) return;
    var w = 560;
    var h = 220;
    var padL = 72;
    var padR = 20;
    var padT = 22;
    var padB = 36;
    var precios = historial.map(function (p) {
      return Number(p.precio) || 0;
    });
    var min = Math.min.apply(null, precios);
    var max = Math.max.apply(null, precios);
    if (min === max) {
      min = Math.max(0, min - Math.max(1000, min * 0.08));
      max = max + Math.max(1000, max * 0.08);
    }
    var plotW = w - padL - padR;
    var plotH = h - padT - padB;
    function x(i) {
      if (historial.length === 1) return padL + plotW / 2;
      return padL + (i * plotW) / (historial.length - 1);
    }
    function y(valor) {
      return padT + plotH - ((Number(valor) - min) * plotH) / (max - min);
    }
    var puntos = historial
      .map(function (p, i) {
        return x(i).toFixed(1) + "," + y(p.precio).toFixed(1);
      })
      .join(" ");
    var primero = historial[0];
    var ultimo = historial[historial.length - 1];
    var yMin = (h - padB).toFixed(1);
    var yMax = padT.toFixed(1);
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.innerHTML =
      '<line class="eje" x1="' +
      padL +
      '" y1="' +
      (padT - 4) +
      '" x2="' +
      padL +
      '" y2="' +
      (h - padB + 8) +
      '" stroke="#1c211e" stroke-width="2"/>' +
      '<line class="eje" x1="' +
      (padL - 8) +
      '" y1="' +
      (h - padB) +
      '" x2="' +
      (w - padR + 6) +
      '" y2="' +
      (h - padB) +
      '" stroke="#1c211e" stroke-width="2"/>' +
      '<polyline fill="none" stroke="#54582f" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="' +
      puntos +
      '"/>' +
      historial
        .map(function (p, i) {
          var cx = x(i).toFixed(1);
          var cy = y(p.precio).toFixed(1);
          return (
            '<g class="punto-grafico" data-fecha="' +
            escapar(formatoFechaCorta(p.fecha)) +
            '" data-precio="' +
            escapar(formatoPeso(p.precio)) +
            '">' +
            '<circle class="punto-hit" cx="' +
            cx +
            '" cy="' +
            cy +
            '" r="14" fill="transparent"/>' +
            '<circle class="punto-visible" cx="' +
            cx +
            '" cy="' +
            cy +
            '" r="5" fill="#1c211e"/>' +
            "</g>"
          );
        })
        .join("") +
      '<text x="' +
      (padL - 8) +
      '" y="' +
      (Number(yMax) + 4) +
      '" text-anchor="end" fill="#5c635c" font-size="11">' +
      formatoPeso(max) +
      "</text>" +
      '<text x="' +
      (padL - 8) +
      '" y="' +
      (Number(yMin) + 4) +
      '" text-anchor="end" fill="#5c635c" font-size="11">' +
      formatoPeso(min) +
      "</text>" +
      '<text x="' +
      padL +
      '" y="' +
      (h - 10) +
      '" fill="#5c635c" font-size="11">' +
      formatoFechaCorta(primero.fecha) +
      "</text>" +
      '<text x="' +
      (w - padR) +
      '" y="' +
      (h - 10) +
      '" text-anchor="end" fill="#5c635c" font-size="11">' +
      formatoFechaCorta(ultimo.fecha) +
      "</text>";

    var caja = svg.closest(".bloque-grafico") || svg.parentNode;
    if (!caja) return;
    caja.classList.add("bloque-grafico");
    var tip = caja.querySelector(".grafico-tip");
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "grafico-tip";
      tip.hidden = true;
      caja.appendChild(tip);
    }
    function ocultarTip() {
      tip.hidden = true;
      svg.querySelectorAll(".punto-visible").forEach(function (c) {
        c.setAttribute("r", "5");
      });
    }
    function mostrarTip(grupo) {
      var vis = grupo.querySelector(".punto-visible");
      if (!vis) return;
      svg.querySelectorAll(".punto-visible").forEach(function (c) {
        c.setAttribute("r", "5");
      });
      vis.setAttribute("r", "7");
      tip.hidden = false;
      tip.textContent =
        (grupo.getAttribute("data-fecha") || "") +
        " · " +
        (grupo.getAttribute("data-precio") || "");
      var rCaja = caja.getBoundingClientRect();
      var rPunto = vis.getBoundingClientRect();
      tip.style.left = rPunto.left + rPunto.width / 2 - rCaja.left + "px";
      tip.style.top = rPunto.top - rCaja.top + "px";
    }
    svg.querySelectorAll(".punto-grafico").forEach(function (grupo) {
      grupo.addEventListener("mouseenter", function () {
        mostrarTip(grupo);
      });
      grupo.addEventListener("mouseleave", ocultarTip);
    });
  }

  function cuandoListo(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  GEARUP.comun = {
    cuandoListo: cuandoListo,
    parametro: parametro,
    formatoPeso: formatoPeso,
    esOferta: esOferta,
    descuento: descuento,
    nombreCategoria: nombreCategoria,
    nombreSub: nombreSub,
    imagenProducto: imagenProducto,
    htmlFoto: htmlFoto,
    pintarRejilla: pintarRejilla,
    ordenarLista: ordenarLista,
    aplicarOrden: aplicarOrden,
    armarEncabezado: armarEncabezado,
    slotsLoadout: SLOTS_LOADOUT,
    listasLoadout: LISTAS_LOADOUT,
    modosFacial: MODOS_FACIAL,
    slotPorId: slotPorId,
    slotParaProducto: slotParaProducto,
    cabeEnSlot: cabeEnSlot,
    slotVisible: slotVisible,
    productoPorId: productoPorId,
    leerLoadout: leerLoadout,
    asignarLoadout: asignarLoadout,
    alternarListaLoadout: alternarListaLoadout,
    quitarDeLista: quitarDeLista,
    definirModoFacial: definirModoFacial,
    productoEnLoadout: productoEnLoadout,
    loadoutTieneDatos: loadoutTieneDatos,
    vaciarLoadout: vaciarLoadout,
    itemsLoadout: itemsLoadout,
    totalLoadout: totalLoadout,
    actualizarCuentaLoadout: actualizarCuentaLoadout,
    dibujarGrafico: dibujarGrafico,
    escapar: escapar,
  };
})();
