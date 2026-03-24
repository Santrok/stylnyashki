(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  async function apiPostJson(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error((data && data.detail) || 'Request failed');
    return data;
  }

  const pop = document.getElementById('cartRemovePopover');
  if (!pop) return;

  let activeItemId = null;
  let activeRow = null;

  const btnCancel = pop.querySelector('[data-popover-cancel]');
  const btnConfirm = pop.querySelector('[data-popover-confirm]');

  function closePopover() {
    pop.hidden = true;
    activeItemId = null;
    activeRow = null;
  }

  function placePopoverNear(buttonEl) {
    const r = buttonEl.getBoundingClientRect();
    const pad = 10;

    let top = r.bottom + pad;
    let left = r.right - pop.offsetWidth;

    const maxTop = window.innerHeight - pop.offsetHeight - pad;
    if (top > maxTop) top = r.top - pop.offsetHeight - pad;

    const minLeft = pad;
    const maxLeft = window.innerWidth - pop.offsetWidth - pad;
    left = Math.min(Math.max(left, minLeft), maxLeft);

    pop.style.top = `${Math.round(top)}px`;
    pop.style.left = `${Math.round(left)}px`;
  }

  function openPopover(buttonEl, itemId, rowEl) {
    activeItemId = itemId;
    activeRow = rowEl;

    pop.hidden = false;
    requestAnimationFrame(() => placePopoverNear(buttonEl));
  }

  // Закрытие при клике вне
  document.addEventListener('mousedown', (e) => {
    if (pop.hidden) return;
    if (e.target.closest('#cartRemovePopover')) return;
    if (e.target.closest('[data-action="cart-remove-ask"]')) return;
    closePopover();
  });

  // Закрытие при скролле
  window.addEventListener('scroll', () => {
    if (!pop.hidden) closePopover();
  }, { passive: true });

  const scrollContainers = document.querySelectorAll('.custom-scroll, .cart-list__body');
  scrollContainers.forEach((el) => {
    el.addEventListener('scroll', () => {
      if (!pop.hidden) closePopover();
    }, { passive: true });
  });

  // Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !pop.hidden) closePopover();
  });

  // Клик по "Удалить" (открыть popover)
  document.addEventListener('click', (e) => {
    const askBtn = e.target.closest('[data-action="cart-remove-ask"]');
    if (!askBtn) return;

    const row = askBtn.closest('[data-cart-item][data-item-id]');
    if (!row) return;

    const itemId = row.dataset.itemId;

    if (!pop.hidden && activeItemId === itemId) {
      closePopover();
      return;
    }

    openPopover(askBtn, itemId, row);
  });

  btnCancel && btnCancel.addEventListener('click', closePopover);

  btnConfirm && btnConfirm.addEventListener('click', async () => {
    if (!activeItemId) return;

    btnConfirm.disabled = true;
    try {
      // оптимистично удаляем
      if (activeRow) activeRow.remove();

      await apiPostJson('/api/cart/remove/', { item_id: activeItemId });

      closePopover();

      window.dispatchEvent(new CustomEvent('cart:changed'));

      // всегда перезагружаем, чтобы сервер пересчитал totals (учитывая availability)
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert('Не удалось удалить товар из корзины');
      window.location.reload();
    } finally {
      btnConfirm.disabled = false;
    }
  });

  window.addEventListener('resize', () => {
    if (!pop.hidden) closePopover();
  });
})();