// shop.js
// Управление избранным и корзиной + визуальные классы карточек/модалок
(function () {
  'use strict';

  /* -----------------------
     Network helpers
     ----------------------- */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  async function apiGet(url) {
    const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || 'Request failed');
    return data;
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
    if (!res.ok) throw new Error(data?.detail || 'Request failed');
    return data;
  }

  /* -----------------------
     Local state & small UI helpers
     ----------------------- */
  const state = {
    favorites: new Set(),
    cart: new Set(),
  };

  function setCartActive(btn, active) {
    if (!btn) return;
    btn.classList.toggle('is-in-cart', !!active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  }

  function setFavActive(btn, active) {
    if (!btn) return;
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    const icon = btn.querySelector('i');
    if (!icon) return;
    if (active) {
      icon.classList.remove('far'); icon.classList.add('fas');
    } else {
      icon.classList.remove('fas'); icon.classList.add('far');
    }
  }

  function updateHeaderBadges(summary) {
    if (!summary) return;
    const cartQtyEl = document.querySelector('[data-badge="cart-qty"]');
    if (cartQtyEl && summary.cart_summary) cartQtyEl.textContent = String(summary.cart_summary.total_qty || 0);
    const favCountEl = document.querySelector('[data-badge="fav-count"]');
    if (favCountEl && summary.favorites_summary) favCountEl.textContent = String(summary.favorites_summary.count || 0);
  }

  /* -----------------------
     Visual helpers for cards / rows / modal
     ----------------------- */
  // улучшенная функция применения визуального состояния с форсом перерисовки
function applyCartVisualStateForProduct(pid, in_cart) {
  // сначала обновим state на самих кнопках
  document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`)
    .forEach(btn => setCartActive(btn, in_cart));

  // затем пройдём по каждой найденной кнопке и обновим контейнеры
  document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`).forEach(btn => {
    // 1) карточка товара
    const card = btn.closest('.p-card');
    if (card) {
      // убираем возможный флаг удаления, чтобы корректно работать при быстром клике
      card.classList.remove('is-removed');

      // форсируем reflow перед установкой нового состояния,
      // чтобы мобильный браузер точно применил стили и transition
      // (чтение свойства вызывает layout flush)
      void card.offsetWidth;

      // теперь переключаем состояние "в корзине"
      if (in_cart) {
        // добавляем класс внутри rAF для плавности
        requestAnimationFrame(() => {
          card.classList.add('is-in-cart');
          // убираем is-removed на случай, если он ещё был
          card.classList.remove('is-removed');
        });
      } else {
        // удаляем класс is-in-cart и показываем краткую анимацию удаления
        card.classList.remove('is-in-cart');
        // small delay чтобы переход сработал корректно (обновление слоя)
        requestAnimationFrame(() => {
          card.classList.add('is-removed');
          // уберём is-removed после анимации
          window.setTimeout(() => card.classList.remove('is-removed'), 420);
        });
      }
    }

    // 2) строка корзины (mobile) — используем .cart-item или data-cart-item
    const row = btn.closest('.cart-item') || document.querySelector(`[data-cart-item="${pid}"]`);
    if (row) {
      row.classList.remove('is-removed');
      void row.offsetWidth;
      if (in_cart) {
        requestAnimationFrame(() => {
          row.classList.add('is-in-cart');
          row.classList.remove('is-removed');
        });
      } else {
        row.classList.remove('is-in-cart');
        requestAnimationFrame(() => {
          row.classList.add('is-removed');
          window.setTimeout(() => row.classList.remove('is-removed'), 420);
        });
      }
    }

    // 3) модалка: помечаем panel, меняем текст
    const pmPanel = document.querySelector('.p-modal.is-open .p-modal__panel') || document.querySelector('#productModal .p-modal__panel');
    if (pmPanel) {
      const pmBtn = pmPanel.querySelector(`[data-action="toggle-cart"][data-product-id="${pid}"]`);
      if (pmBtn) {
        pmPanel.classList.remove('is-removed');
        void pmPanel.offsetWidth;
        const pmCartText = pmPanel.querySelector('#pmCartText');
        if (in_cart) {
          requestAnimationFrame(() => {
            pmPanel.classList.add('is-in-cart');
            if (pmCartText) pmCartText.textContent = 'В корзине';
            pmPanel.classList.remove('is-removed');
          });
        } else {
          pmPanel.classList.remove('is-in-cart');
          requestAnimationFrame(() => {
            if (pmCartText) pmCartText.textContent = 'В корзину';
            pmPanel.classList.add('is-removed');
            window.setTimeout(() => pmPanel.classList.remove('is-removed'), 420);
          });
        }
      }
    }
  });
}

  function applyCartStateOnLoad(stateSet) {
    document.querySelectorAll('[data-action="toggle-cart"][data-product-id]').forEach(btn => {
      const pid = String(btn.dataset.productId);
      const inCart = stateSet.has(pid);
      setCartActive(btn, inCart);
      // set visual classes for containers
      applyCartVisualStateForProduct(pid, inCart);
    });
  }

  function applyFavStateOnLoad(stateSet) {
    document.querySelectorAll('[data-action="toggle-favorite"][data-product-id]').forEach(btn => {
      const pid = String(btn.dataset.productId);
      const inFav = stateSet.has(pid);
      setFavActive(btn, inFav);
    });
  }

  /* -----------------------
     Apply state to DOM (existing API)
     ----------------------- */
  function applyStateToDOM(root) {
    const scope = root || document;
    scope.querySelectorAll('[data-action="toggle-favorite"][data-product-id]').forEach((btn) => {
      const pid = String(btn.dataset.productId);
      setFavActive(btn, state.favorites.has(pid));
    });
    scope.querySelectorAll('[data-action="toggle-cart"][data-product-id]').forEach((btn) => {
      const pid = String(btn.dataset.productId);
      setCartActive(btn, state.cart.has(pid));
    });

    // Ensure visual containers are updated as well
    state.cart.forEach(pid => applyCartVisualStateForProduct(pid, true));
  }

  /* -----------------------
     Load / sync state with server
     ----------------------- */
  async function loadState() {
    try {
      const data = await apiGet('/api/state/');
      state.cart = new Set((data.cart_product_ids || []).map(String));
      state.favorites = new Set((data.favorite_ids || []).map(String));
      // apply to DOM (buttons + containers)
      applyStateToDOM();
      updateHeaderBadges(data);
    } catch (err) {
      console.warn('state load failed', err);
    }
  }

  /* -----------------------
     Delegated click handler
     ----------------------- */
  document.addEventListener('click', async (e) => {
    // toggle favorite
    const favBtn = e.target.closest('[data-action="toggle-favorite"][data-product-id]');
    if (favBtn) {
      e.preventDefault();
      const pid = favBtn.dataset.productId;
      favBtn.disabled = true;
      try {
        const data = await apiPostJson('/api/favorites/toggle/', { product_id: pid });
        if (data.is_favorite) state.favorites.add(String(pid));
        else state.favorites.delete(String(pid));
        // apply to all fav buttons for this product
        document.querySelectorAll(`[data-action="toggle-favorite"][data-product-id="${pid}"]`)
          .forEach((btn) => setFavActive(btn, data.is_favorite));
        updateHeaderBadges({ favorites_summary: data.summary });
      } catch (err) {
        console.error(err);
        alert('Не удалось изменить избранное');
      } finally {
        favBtn.disabled = false;
      }
      return;
    }

    // toggle cart
    const cartBtn = e.target.closest('[data-action="toggle-cart"][data-product-id]');
    if (cartBtn) {
      e.preventDefault();
      const pid = cartBtn.dataset.productId;
      cartBtn.disabled = true;
      try {
        const data = await apiPostJson('/api/cart/toggle/', { product_id: pid });
        if (data.in_cart) state.cart.add(String(pid));
        else state.cart.delete(String(pid));

        // update basic button active state
        document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`)
          .forEach((btn) => setCartActive(btn, data.in_cart));

        // New: update containers/cards/modal visuals
        applyCartVisualStateForProduct(pid, data.in_cart);

        updateHeaderBadges({ cart_summary: data.summary });
      } catch (err) {
        console.error(err);
        alert('Не удалось изменить корзину');
      } finally {
        cartBtn.disabled = false;
      }
      return;
    }
  });

  /* -----------------------
     Init on DOMContentLoaded
     ----------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    loadState().catch((e) => console.warn('state load failed', e));
  });

  // expose API for dynamic content
  window.ShopApplyStateToDOM = applyStateToDOM;
  window.ShopState = {
    hasInCart: (pid) => state.cart.has(String(pid)),
    hasInFav: (pid) => state.favorites.has(String(pid)),
    applyToDOM: applyStateToDOM,
  };

  // listen to custom event to refresh cart state
  window.addEventListener('cart:changed', function () {
    loadState().catch(() => {});
  });
})();