(function () {
  "use strict";

  var data = JSON.parse(document.getElementById("lesson-data").textContent);
  var root = document.getElementById("lesson-root");
  var estado = {
    seccionActual: 0,
    completadas: new Set(),
    respuestas: {}, // secId -> array de índices seleccionados (o null) por pregunta
    resultados: {}, // secId -> { aciertos, total, porcentaje }
  };

  function crearElemento(tag, clase, html) {
    var el = document.createElement(tag);
    if (clase) el.className = clase;
    if (html !== undefined) el.innerHTML = html;
    return el;
  }

  function conScrollFijo(fn) {
    var y = window.scrollY;
    fn();
    window.scrollTo(0, y);
  }

  function render() {
    root.innerHTML = "";

    var header = document.querySelector(".lesson-header");
    header.querySelector("h1").textContent = data.titulo;
    header.querySelector("p").textContent = data.objetivo || "";

    // Los paneles se construyen antes que las pestañas: construirPreguntas() puede marcar
    // la sección como completada, y las pestañas necesitan ese estado ya actualizado.
    var paneles = data.secciones.map(function (sec, i) {
      var panel = crearElemento("div", "section-panel" + (i === estado.seccionActual ? " activa" : ""));
      panel.appendChild(crearElemento("h2", null, sec.titulo));
      panel.appendChild(crearElemento("div", "contenido", sec.contenido_html));

      if (sec.terminos_clave && sec.terminos_clave.length) {
        var terminos = crearElemento("div", "terminos");
        sec.terminos_clave.forEach(function (t) {
          var card = crearElemento("div", "flashcard");
          card.innerHTML =
            '<div class="flashcard-inner">' +
            '<div class="flashcard-cara flashcard-frente">' + t.termino + "</div>" +
            '<div class="flashcard-cara flashcard-dorso">' + t.definicion + "</div>" +
            "</div>";
          card.addEventListener("click", function () {
            card.classList.toggle("volteada");
          });
          terminos.appendChild(card);
        });
        panel.appendChild(terminos);
      }

      if (sec.preguntas && sec.preguntas.length) {
        panel.appendChild(construirPreguntas(sec));
      } else {
        estado.completadas.add(sec.id);
      }

      return panel;
    });

    var tabs = crearElemento("div", "tabs");
    data.secciones.forEach(function (sec, i) {
      var btn = crearElemento("button", "tab-button" + (i === estado.seccionActual ? " activa" : ""));
      btn.textContent = sec.titulo;
      if (estado.completadas.has(sec.id)) btn.classList.add("completada");
      btn.addEventListener("click", function () {
        estado.seccionActual = i;
        render();
      });
      tabs.appendChild(btn);
    });
    root.appendChild(tabs);

    paneles.forEach(function (panel) {
      root.appendChild(panel);
    });

    var nav = crearElemento("div", "nav-buttons");
    var btnAnterior = crearElemento("button", "nav-btn");
    btnAnterior.textContent = "Anterior";
    btnAnterior.disabled = estado.seccionActual === 0;
    btnAnterior.addEventListener("click", function () {
      estado.seccionActual = Math.max(0, estado.seccionActual - 1);
      render();
    });

    var esUltima = estado.seccionActual === data.secciones.length - 1;
    var btnSiguiente = crearElemento("button", "nav-btn");
    btnSiguiente.textContent = esUltima ? "Ver resumen" : "Siguiente";
    btnSiguiente.addEventListener("click", function () {
      if (esUltima) {
        mostrarResumen();
      } else {
        estado.seccionActual += 1;
        render();
      }
    });

    nav.appendChild(btnAnterior);
    nav.appendChild(btnSiguiente);
    root.appendChild(nav);

    actualizarProgreso();
  }

  function construirPreguntas(sec) {
    var wrap = crearElemento("div", "autoeval-bloque");
    wrap.appendChild(
      crearElemento("h3", null, "Comprueba lo que has aprendido (" + sec.preguntas.length + " preguntas)")
    );

    if (!estado.respuestas[sec.id]) {
      estado.respuestas[sec.id] = new Array(sec.preguntas.length).fill(null);
    }
    var respuestas = estado.respuestas[sec.id];

    sec.preguntas.forEach(function (preg, qIdx) {
      var bloque = crearElemento("div", "pregunta-bloque");
      bloque.appendChild(crearElemento("p", "pregunta-texto", (qIdx + 1) + ". " + preg.pregunta));

      var yaRespondida = respuestas[qIdx] !== null;

      preg.opciones.forEach(function (opcion, oIdx) {
        var btn = crearElemento("button", "opcion-btn");
        btn.textContent = opcion;
        btn.disabled = yaRespondida;
        if (yaRespondida) {
          if (oIdx === preg.correcta_index) btn.classList.add("correcta");
          else if (oIdx === respuestas[qIdx]) btn.classList.add("incorrecta");
        }
        btn.addEventListener("click", function () {
          if (respuestas[qIdx] !== null) return;
          respuestas[qIdx] = oIdx;
          conScrollFijo(render);
        });
        bloque.appendChild(btn);
      });

      if (yaRespondida) {
        var correcta = respuestas[qIdx] === preg.correcta_index;
        var feedbackEl = crearElemento(
          "div",
          "feedback-msg " + (correcta ? "correcta" : "incorrecta"),
          correcta ? preg.feedback_correcto || "¡Correcto!" : preg.feedback_incorrecto || "No es correcto."
        );
        bloque.appendChild(feedbackEl);
      }

      wrap.appendChild(bloque);
    });

    var todasRespondidas = respuestas.every(function (r) {
      return r !== null;
    });

    if (todasRespondidas) {
      var aciertos = respuestas.filter(function (r, i) {
        return r === sec.preguntas[i].correcta_index;
      }).length;
      var total = sec.preguntas.length;
      var porcentaje = Math.round((aciertos / total) * 100);

      estado.completadas.add(sec.id);
      estado.resultados[sec.id] = { aciertos: aciertos, total: total, porcentaje: porcentaje };

      var resultado = crearElemento(
        "div",
        "resultado-apartado " + (porcentaje >= 50 ? "aprobado" : "suspenso"),
        "Resultado de este apartado: has acertado <strong>" +
          aciertos +
          " de " +
          total +
          "</strong> preguntas (" +
          porcentaje +
          "%)."
      );
      wrap.appendChild(resultado);
    }

    return wrap;
  }

  function calcularNotaMedia() {
    var claves = Object.keys(estado.resultados);
    if (!claves.length) return 0;
    var suma = 0;
    claves.forEach(function (k) {
      suma += estado.resultados[k].porcentaje;
    });
    return Math.round(suma / claves.length);
  }

  function actualizarProgreso() {
    var total = data.secciones.length;
    var hechas = estado.completadas.size;
    var porcentajeProgreso = total ? Math.round((hechas / total) * 100) : 0;
    var barra = document.querySelector(".lesson-progress-bar");
    if (barra) barra.style.width = porcentajeProgreso + "%";

    if (window.ScormAPI && window.ScormAPI.disponible) {
      window.ScormAPI.initialize();
      window.ScormAPI.setScore(calcularNotaMedia());
      window.ScormAPI.setStatus(porcentajeProgreso >= 100 ? "completed" : "incomplete");
    }
  }

  function mostrarResumen() {
    root.innerHTML = "";
    var notaMedia = calcularNotaMedia();

    var box = crearElemento("div", "resumen-final");
    box.appendChild(crearElemento("h2", null, "Resumen"));
    box.appendChild(crearElemento("p", null, data.resumen || ""));
    box.appendChild(
      crearElemento(
        "p",
        "resultado-apartado " + (notaMedia >= 50 ? "aprobado" : "suspenso"),
        "Nota media de tus autoevaluaciones: <strong>" + notaMedia + "%</strong>"
      )
    );
    root.appendChild(box);

    var nav = crearElemento("div", "nav-buttons");
    var btnVolver = crearElemento("button", "nav-btn");
    btnVolver.textContent = "Volver a la lección";
    btnVolver.addEventListener("click", function () {
      estado.seccionActual = 0;
      render();
    });
    nav.appendChild(btnVolver);
    root.appendChild(nav);

    if (window.ScormAPI && window.ScormAPI.disponible) {
      window.ScormAPI.initialize();
      window.ScormAPI.setScore(notaMedia);
      window.ScormAPI.setStatus("completed");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (window.ScormAPI && window.ScormAPI.disponible) {
      window.ScormAPI.initialize();
    }
    render();
  });
})();
