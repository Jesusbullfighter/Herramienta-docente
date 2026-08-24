// Alterna entre los paneles de origen de contenido: texto pegado, PDF, Word o URL.
document.addEventListener("DOMContentLoaded", function () {
  var botones = document.querySelectorAll(".tabs-origen button");
  var paneles = document.querySelectorAll(".origen-panel");
  var inputOrigen = document.getElementById("origen-seleccionado");

  function activar(origen) {
    botones.forEach(function (b) {
      b.classList.toggle("activo", b.dataset.origen === origen);
    });
    paneles.forEach(function (p) {
      p.classList.toggle("activo", p.dataset.origen === origen);
    });
    if (inputOrigen) inputOrigen.value = origen;
  }

  botones.forEach(function (b) {
    b.addEventListener("click", function (e) {
      e.preventDefault();
      activar(b.dataset.origen);
    });
  });

  if (botones.length) activar(botones[0].dataset.origen);
});
