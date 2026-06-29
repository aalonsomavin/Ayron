(function () {
  "use strict";

  var EYE_OPEN =
    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
  var EYE_OFF =
    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9.88 9.88a3 3 0 0 0 4.24 4.24"></path><path d="M10.73 5.08A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a13.2 13.2 0 0 1-1.67 2.68"></path><path d="M6.61 6.61A13.5 13.5 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61"></path><path d="m2 2 20 20"></path></svg>';
  var SPINNER =
    '<svg class="ay-login-spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>';

  var pw = document.getElementById("id_password");
  var eye = document.getElementById("ay-eye");
  if (pw && eye) {
    eye.innerHTML = EYE_OPEN;
    eye.addEventListener("click", function () {
      var hidden = pw.type === "password";
      pw.type = hidden ? "text" : "password";
      eye.innerHTML = hidden ? EYE_OFF : EYE_OPEN;
    });
  }

  var form = document.getElementById("ay-login-form");
  var submit = document.getElementById("ay-login-submit");
  if (form && submit) {
    form.addEventListener("submit", function () {
      if (submit.disabled) return;
      submit.disabled = true;
      submit.innerHTML = SPINNER + "Iniciando sesión…";
    });
  }

  var forgot = document.getElementById("ay-forgot");
  if (forgot) {
    forgot.addEventListener("click", function (e) {
      e.preventDefault();
    });
  }

  var create = document.getElementById("ay-create");
  if (create) {
    create.addEventListener("click", function (e) {
      e.preventDefault();
    });
  }
})();
