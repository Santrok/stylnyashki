// static/js/checkout.js
(function () {
  function getCheckedValue() {
    const checked = document.querySelector('[data-delivery-radio]:checked');
    return checked ? checked.value : 'post';
  }

  function syncPanels() {
    const val = getCheckedValue();

    document.querySelectorAll('.co-panel[data-panel]').forEach(function (p) {
      p.style.display = (p.getAttribute('data-panel') === val) ? 'block' : 'none';
    });
  }

  document.addEventListener('change', function (e) {
    const t = e.target;
    if (t && t.matches && t.matches('[data-delivery-radio]')) {
      syncPanels();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    syncPanels();
  });
})();