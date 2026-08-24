/* Envoltorio mínimo para comunicarse con el LMS (Moodle) vía SCORM 1.2.
   Busca el objeto API en la ventana padre/opener y expone funciones sencillas. */
(function (global) {
  "use strict";

  function findAPI(win) {
    var attempts = 0;
    while (win && !win.API && win.parent && win.parent !== win && attempts < 10) {
      win = win.parent;
      attempts++;
    }
    return win ? win.API : null;
  }

  var api = findAPI(window);
  if (!api && window.opener) {
    api = findAPI(window.opener);
  }

  var initialized = false;

  function initialize() {
    if (!api) return false;
    if (!initialized) {
      initialized = api.LMSInitialize("") !== "false";
    }
    return initialized;
  }

  function setValue(element, value) {
    if (!api || !initialized) return false;
    var ok = api.LMSSetValue(element, value) !== "false";
    api.LMSCommit("");
    return ok;
  }

  function getValue(element) {
    if (!api || !initialized) return "";
    return api.LMSGetValue(element);
  }

  function setStatus(status) {
    // status: "completed" | "incomplete" | "passed" | "failed"
    return setValue("cmi.core.lesson_status", status);
  }

  function setScore(scorePercent) {
    setValue("cmi.core.score.raw", String(Math.round(scorePercent)));
  }

  function finish() {
    if (!api || !initialized) return;
    api.LMSFinish("");
  }

  global.ScormAPI = {
    disponible: !!api,
    initialize: initialize,
    setStatus: setStatus,
    setScore: setScore,
    getValue: getValue,
    finish: finish,
  };

  window.addEventListener("beforeunload", function () {
    global.ScormAPI.finish();
  });
})(window);
