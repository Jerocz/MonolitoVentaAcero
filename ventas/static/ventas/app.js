// Mejoras progresivas de usabilidad. La pagina funciona igual sin JavaScript.
// No hay textos aqui: los mensajes llegan traducidos desde la plantilla (data-*).
(function () {
  // 1. Confirmar acciones que cobran dinero o cambian estado (data-confirm).
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      if (!window.confirm(form.dataset.confirm)) ev.preventDefault();
    });
  });

  // 2. Evitar doble envio (doble cobro): deshabilita el boton y muestra "procesando".
  document.querySelectorAll('form[method="post"]').forEach(function (form) {
    form.addEventListener('submit', function (ev) {
      if (ev.defaultPrevented) return;
      form.querySelectorAll('button[type="submit"]').forEach(function (btn) {
        if (btn.dataset.enviando) btn.textContent = btn.dataset.enviando;
        btn.disabled = true;
      });
    });
  });

  // 3. Cambiar de idioma al elegirlo (el boton queda para quien navega sin JS).
  document.querySelectorAll('.idioma select').forEach(function (select) {
    var boton = select.form.querySelector('button');
    if (boton) boton.hidden = true;
    select.addEventListener('change', function () { select.form.submit(); });
  });

  // 4. Llevar el foco al primer campo con error para lectores de pantalla y teclado.
  var invalido = document.querySelector('[aria-invalid="true"]');
  if (invalido) invalido.focus();
})();
