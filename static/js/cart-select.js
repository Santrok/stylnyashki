// static/js/cart-select.js
// Пересчёт суммы и количества в корзине с учётом чекбоксов (GET -> checkout).
// Учитываются только отмеченные чекбоксы и только доступные позиции (data-availability="available").
// Если товар удалён/добавлен — MutationObserver обновит расчёт.

(function () {
  'use strict';

  function parseNumberSafe(v) {
    if (v === undefined || v === null) return 0;
    if (typeof v === 'number') return v;
    // remove non-digit, non-dot, non-minus
    const s = String(v).replace(/[^\d\.\-]/g, '');
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : 0;
  }

  document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('cart-select-form');
    if (!form) return;

    const totalQtyEl = document.querySelector('[data-cart-total-qty]');
    const totalSumEl = document.querySelector('[data-cart-total-sum]');
    const cartPayEl = document.querySelector('[data-cart-pay]');
    const submitBtn = document.getElementById('cartGoCheckoutBtn');

    // Get current item rows
    function getItemRows() {
      return Array.from(form.querySelectorAll('[data-cart-item]'));
    }

    // Read subtotal from element (prefer dataset.subtotal)
    function readSubtotal(row) {
      // Prefer data attribute on sum element
      const subtotalEl = row.querySelector('[data-subtotal]');
      if (subtotalEl) {
        // try dataset first
        if (subtotalEl.dataset && subtotalEl.dataset.subtotal) {
          return parseNumberSafe(subtotalEl.dataset.subtotal);
        }
        // fallback to text content
        return parseNumberSafe(subtotalEl.textContent);
      }
      // fallback: try to compute from price and quantity
      const priceEl = row.querySelector('.price-now');
      const qty = parseInt(row.dataset.quantity || '1', 10) || 0;
      const price = priceEl ? parseNumberSafe(priceEl.textContent) : 0;
      return price * qty;
    }

    function recalc() {
      const rows = getItemRows();
      let totalQty = 0;
      let totalSum = 0;

      rows.forEach((row) => {
        const available = String(row.dataset.availability || '').toLowerCase() === 'available';
        const checkbox = row.querySelector('.cart-item__checkbox');
        if (!checkbox) return;

        // Only count if checkbox is checked and item is available (and checkbox not disabled)
        if (!checkbox.checked) return;
        if (checkbox.disabled) return;
        if (!available) return;

        const qty = parseInt(row.dataset.quantity || '1', 10) || 0;
        const subtotal = readSubtotal(row) || 0;

        totalQty += qty;
        totalSum += subtotal;
      });

      // Update UI
      if (totalQtyEl) {
        totalQtyEl.textContent = `Товары (${totalQty})`;
      }
      if (totalSumEl) {
        totalSumEl.innerHTML = `${Math.round(totalSum)} <span class="by-currency">ƃ</span>`;
      }
      if (cartPayEl) {
        cartPayEl.innerHTML = `${Math.round(totalSum)} <span class="by-currency">ƃ</span>`;
      }

      // Enable/disable submit
      if (submitBtn) {
        if (totalQty > 0) {
          submitBtn.disabled = false;
          submitBtn.classList.remove('btn--disabled');
        } else {
          submitBtn.disabled = true;
          submitBtn.classList.add('btn--disabled');
        }
      }
    }

    // Delegate change events for checkboxes
    form.addEventListener('change', function (e) {
      const target = e.target;
      if (!target) return;
      if (target.classList && target.classList.contains('cart-item__checkbox')) {
        // On change of a checkbox, recalc totals
        recalc();
      }
    }, false);

    // MutationObserver to detect DOM changes (item removed/added)
    const observer = new MutationObserver(function (mutations) {
      // If nodes removed/added -> recalc. We keep it simple and recalc on any mutation.
      let shouldRecalc = false;
      for (const m of mutations) {
        if (m.type === 'childList' && (m.addedNodes.length || m.removedNodes.length)) {
          shouldRecalc = true;
          break;
        }
        if (m.type === 'attributes' && m.attributeName === 'data-availability') {
          shouldRecalc = true;
          break;
        }
      }
      if (shouldRecalc) {
        // Small delay for other scripts (e.g., cart.js) to finish DOM updates
        setTimeout(recalc, 30);
      }
    });

    observer.observe(form, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-availability'] });

    // Initial calculation (on load)
    recalc();

    // Optional: re-run recalc when window gains focus (user may have changed something in other tab)
    window.addEventListener('focus', function () {
      setTimeout(recalc, 50);
    });

    // Expose a small API in case other scripts want to trigger recalc manually
    window.cartSelect = {
      recalc: recalc
    };
  });
})();