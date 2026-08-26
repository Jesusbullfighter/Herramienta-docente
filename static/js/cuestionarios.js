// Editor de preguntas: mantiene el modelo en memoria y lo serializa a JSON al exportar.
(function () {
  "use strict";

  var contenedor = document.getElementById("preguntas-container");
  var preguntas = window.PREGUNTAS_INICIALES || [];
  var contadorIds = preguntas.length;

  function nuevoId() {
    contadorIds += 1;
    return "q" + contadorIds + "_" + Date.now();
  }

  function crearEl(tag, clase, texto) {
    var el = document.createElement(tag);
    if (clase) el.className = clase;
    if (texto !== undefined) el.textContent = texto;
    return el;
  }

  function badge(tipo) {
    var etiquetas = {
      opcion_multiple: "Opción múltiple",
      verdadero_falso: "Verdadero o falso",
      completar: "Completar huecos",
      emparejamiento: "Emparejamiento",
    };
    return etiquetas[tipo] || tipo;
  }

  function eliminarPregunta(idx) {
    preguntas.splice(idx, 1);
    render();
  }

  function render() {
    contenedor.innerHTML = "";
    preguntas.forEach(function (p, idx) {
      contenedor.appendChild(renderPregunta(p, idx));
    });
    var contador = document.getElementById("contador-preguntas");
    if (contador) contador.textContent = preguntas.length;
  }

  function renderPregunta(p, idx) {
    var card = crearEl("div", "pregunta-card");
    card.appendChild(crearEl("span", "tipo-badge", badge(p.tipo) + " · #" + (idx + 1)));

    if (p.tipo === "opcion_multiple") renderOpcionMultiple(card, p);
    else if (p.tipo === "verdadero_falso") renderVerdaderoFalso(card, p);
    else if (p.tipo === "completar") renderCompletar(card, p);
    else if (p.tipo === "emparejamiento") renderEmparejamiento(card, p);

    var acciones = crearEl("div", "acciones-pregunta");
    var btnEliminar = crearEl("button", "btn peligro", "Eliminar pregunta");
    btnEliminar.type = "button";
    btnEliminar.addEventListener("click", function () { eliminarPregunta(idx); });
    acciones.appendChild(btnEliminar);
    card.appendChild(acciones);

    return card;
  }

  function campoTexto(label, valor, onChange, esArea) {
    var wrap = document.createElement("div");
    wrap.appendChild(crearEl("label", null, label));
    var input = document.createElement(esArea ? "textarea" : "input");
    if (!esArea) input.type = "text";
    input.value = valor || "";
    input.addEventListener("input", function () { onChange(input.value); });
    wrap.appendChild(input);
    return wrap;
  }

  function renderOpcionMultiple(card, p) {
    card.appendChild(campoTexto("Enunciado", p.enunciado, function (v) { p.enunciado = v; }, true));
    var lista = crearEl("div", "opciones-lista");
    lista.appendChild(crearEl("label", null, "Opciones (marca la correcta)"));
    (p.opciones || []).forEach(function (op, i) {
      var fila = crearEl("div", "opcion-fila");
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "correcta_" + p.id;
      radio.checked = !!op.correcta;
      radio.addEventListener("change", function () {
        p.opciones.forEach(function (o) { o.correcta = false; });
        op.correcta = true;
      });
      var texto = document.createElement("input");
      texto.type = "text";
      texto.value = op.texto || "";
      texto.addEventListener("input", function () { op.texto = texto.value; });
      var btnBorrar = crearEl("button", null, "✕");
      btnBorrar.type = "button";
      btnBorrar.addEventListener("click", function () {
        p.opciones.splice(i, 1);
        render();
      });
      fila.appendChild(radio);
      fila.appendChild(texto);
      fila.appendChild(btnBorrar);
      lista.appendChild(fila);
    });
    var btnAnadir = crearEl("button", "btn secundario", "Añadir opción");
    btnAnadir.type = "button";
    btnAnadir.addEventListener("click", function () {
      p.opciones = p.opciones || [];
      p.opciones.push({ texto: "", correcta: false });
      render();
    });
    lista.appendChild(btnAnadir);
    card.appendChild(lista);
    card.appendChild(campoTexto("Retroalimentación si acierta", p.retroalimentacion_correcta, function (v) { p.retroalimentacion_correcta = v; }));
    card.appendChild(campoTexto("Retroalimentación si falla", p.retroalimentacion_incorrecta, function (v) { p.retroalimentacion_incorrecta = v; }));
  }

  function renderVerdaderoFalso(card, p) {
    card.appendChild(campoTexto("Afirmación", p.enunciado, function (v) { p.enunciado = v; }, true));
    var wrap = document.createElement("div");
    wrap.appendChild(crearEl("label", null, "Valor correcto"));
    ["true", "false"].forEach(function (val) {
      var lbl = crearEl("label", null);
      lbl.style.display = "inline-flex";
      lbl.style.gap = "6px";
      lbl.style.marginRight = "16px";
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "vf_" + p.id;
      radio.checked = (val === "true") === !!p.correcta;
      radio.addEventListener("change", function () { p.correcta = (val === "true"); });
      lbl.appendChild(radio);
      lbl.appendChild(document.createTextNode(val === "true" ? "Verdadero" : "Falso"));
      wrap.appendChild(lbl);
    });
    card.appendChild(wrap);
    card.appendChild(campoTexto("Retroalimentación", p.retroalimentacion, function (v) { p.retroalimentacion = v; }));
  }

  function renderCompletar(card, p) {
    var wrap = campoTexto(
      "Texto con huecos — usa el formato {{respuesta:PALABRA}} para cada hueco",
      p.enunciado_con_huecos,
      function (v) { p.enunciado_con_huecos = v; },
      true
    );
    card.appendChild(wrap);
    card.appendChild(campoTexto("Retroalimentación", p.retroalimentacion, function (v) { p.retroalimentacion = v; }));
  }

  function renderEmparejamiento(card, p) {
    card.appendChild(campoTexto("Instrucción", p.enunciado, function (v) { p.enunciado = v; }, true));
    var lista = crearEl("div", null);
    lista.appendChild(crearEl("label", null, "Pares a relacionar"));
    (p.pares || []).forEach(function (par, i) {
      var fila = crearEl("div", "par-fila");
      var izq = document.createElement("input");
      izq.type = "text";
      izq.value = par.izquierda || "";
      izq.placeholder = "Concepto";
      izq.addEventListener("input", function () { par.izquierda = izq.value; });
      var der = document.createElement("input");
      der.type = "text";
      der.value = par.derecha || "";
      der.placeholder = "Definición";
      der.addEventListener("input", function () { par.derecha = der.value; });
      var btnBorrar = crearEl("button", null, "✕");
      btnBorrar.type = "button";
      btnBorrar.addEventListener("click", function () { p.pares.splice(i, 1); render(); });
      fila.appendChild(izq);
      fila.appendChild(der);
      fila.appendChild(btnBorrar);
      lista.appendChild(fila);
    });
    var btnAnadir = crearEl("button", "btn secundario", "Añadir par");
    btnAnadir.type = "button";
    btnAnadir.addEventListener("click", function () {
      p.pares = p.pares || [];
      p.pares.push({ izquierda: "", derecha: "" });
      render();
    });
    lista.appendChild(btnAnadir);
    card.appendChild(lista);
  }

  function plantillaNueva(tipo) {
    var base = { id: nuevoId(), tipo: tipo };
    if (tipo === "opcion_multiple") {
      return Object.assign(base, {
        enunciado: "",
        opciones: [{ texto: "", correcta: true }, { texto: "", correcta: false }],
        retroalimentacion_correcta: "",
        retroalimentacion_incorrecta: "",
      });
    }
    if (tipo === "verdadero_falso") {
      return Object.assign(base, { enunciado: "", correcta: true, retroalimentacion: "" });
    }
    if (tipo === "completar") {
      return Object.assign(base, { enunciado_con_huecos: "", retroalimentacion: "" });
    }
    if (tipo === "emparejamiento") {
      return Object.assign(base, { enunciado: "", pares: [{ izquierda: "", derecha: "" }] });
    }
    return base;
  }

  document.querySelectorAll(".anadir-tipo").forEach(function (btn) {
    btn.addEventListener("click", function () {
      preguntas.push(plantillaNueva(btn.dataset.tipo));
      render();
    });
  });

  var formExportar = document.getElementById("form-exportar");
  if (formExportar) {
    formExportar.addEventListener("submit", function () {
      document.getElementById("preguntas_json").value = JSON.stringify(preguntas);
    });
  }

  render();
})();
