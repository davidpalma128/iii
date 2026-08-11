// Minimal progressive enhancement: delete confirmations + auto-submit filters.
document.addEventListener("submit", function (event) {
  var form = event.target.closest("form[data-confirm]");
  if (form && !window.confirm(form.getAttribute("data-confirm"))) {
    event.preventDefault();
  }
});

document.addEventListener("change", function (event) {
  if (event.target.matches("select[data-autosubmit]")) {
    event.target.form.submit();
  }
});
