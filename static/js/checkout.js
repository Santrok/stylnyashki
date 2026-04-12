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

// Payment method chooser logic
(function () {
  // ensure DOM ready
  document.addEventListener('DOMContentLoaded', function () {
    const paymentRadios = document.querySelectorAll('[data-payment-radio]');
    const paymentPanels = document.querySelectorAll('[data-payment-panel]');

    function setActivePayment(method) {
      // set label active classes
      document.querySelectorAll('.co-payment-btn').forEach(lbl => lbl.classList.remove('is-active'));
      const input = document.querySelector(`[data-payment-radio][value="${method}"]`);
      if (input) {
        const label = input.closest('.co-payment-btn');
        if (label) label.classList.add('is-active');
      }

      // show/hide panels
      paymentPanels.forEach(p => {
        if (p.getAttribute('data-payment-panel') === method) {
          p.style.display = '';
          p.setAttribute('data-visible', '1');
        } else {
          p.style.display = 'none';
          p.removeAttribute('data-visible');
        }
      });
    }

    // initialize: find checked or default to cod
    const initial = document.querySelector('[data-payment-radio]:checked');
    if (initial) {
      setActivePayment(initial.value);
    } else if (paymentRadios.length) {
      paymentRadios[0].checked = true;
      setActivePayment(paymentRadios[0].value);
    }

    // click/change handler
    document.addEventListener('change', function (e) {
      if (e.target && e.target.matches('[data-payment-radio]')) {
        setActivePayment(e.target.value);
      }
    });

    // also allow clicking on label (just add .is-active visually)
    document.querySelectorAll('.co-payment-btn').forEach(lbl => {
      lbl.addEventListener('click', function (ev) {
        const input = this.querySelector('[data-payment-radio]');
        if (input) {
          input.checked = true;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    });
  });
})();

document.addEventListener('click', function (e) {
  const lbl = e.target.closest('.co-payment-btn.is-disabled');
  if (!lbl) return;
  // предотвращаем любые действия и показываем короткое сообщение
  e.preventDefault();
  // Можно показать ваш кастомный tooltip/modal или toast
  const title = lbl.getAttribute('title') || 'Временно недоступно';
  // простой визуальный фидбек:
  lbl.classList.add('shake'); // если есть CSS-анимация shake
  setTimeout(() => lbl.classList.remove('shake'), 600);

});