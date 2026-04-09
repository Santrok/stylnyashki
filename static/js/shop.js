// shop.js — исправленная версия с надежным обновлением визуального состояния карточек/строк/модалки на мобильных
(function () {
  'use strict';

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
      icon.classList.remove('far');
      icon.classList.add('fas');
    } else {
      icon.classList.remove('fas');
      icon.classList.add('far');
    }
  }

  // Новая, надёжная функция применения визуального состояния для карточки/строки/модалки
  function applyCartVisualStateForProduct(pid, in_cart) {
    // 1) обновляем кнопки (aria + иконки)
    document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`)
      .forEach(btn => setCartActive(btn, in_cart));

    // 2) для каждой кнопки обновляем ближайшие контейнеры
    document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`).forEach(btn => {
      function forceRepaint(el) {
        if (!el) return;
        // promote to composite layer for smoother repaint on mobile
        if (!el.__shop_transform_set) {
          el.style.transform = el.style.transform || 'translateZ(0)';
          el.__shop_transform_set = true;
          // remove after next frame
          requestAnimationFrame(() => {
            if (el && el.__shop_transform_set) {
              el.style.transform = '';
              delete el.__shop_transform_set;
            }
          });
        }
        // force layout flush
        void el.offsetWidth;
      }

      // product card (.p-card)
      const card = btn.closest('.p-card');
      if (card) {
        card.classList.remove('is-removed');
        forceRepaint(card);

        if (in_cart) {
          requestAnimationFrame(() => {
            card.classList.add('is-in-cart');
            // ensure no inline fallback remains
            card.style.backgroundColor = '';
          });
        } else {
          card.classList.remove('is-in-cart');

          // inline fallback to force immediate visible change on lagging renderers
          const fallbackBg = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#f3f4f6';
          card.style.backgroundColor = fallbackBg;

          requestAnimationFrame(() => {
            card.classList.add('is-removed');
            // clear inline fallback after animation
            window.setTimeout(() => {
              if (card) {
                card.classList.remove('is-removed');
                card.style.backgroundColor = '';
              }
            }, 420);
          });
        }
      }

      // cart row (mobile) — .cart-item or data-cart-item
      const row = btn.closest('.cart-item') || document.querySelector(`[data-cart-item="${pid}"]`);
      if (row) {
        row.classList.remove('is-removed');
        forceRepaint(row);

        if (in_cart) {
          requestAnimationFrame(() => {
            row.classList.add('is-in-cart');
            row.style.backgroundColor = '';
          });
        } else {
          row.classList.remove('is-in-cart');
          const fallbackBg = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#f3f4f6';
          row.style.backgroundColor = fallbackBg;
          requestAnimationFrame(() => {
            row.classList.add('is-removed');
            window.setTimeout(() => {
              if (row) {
                row.classList.remove('is-removed');
                row.style.backgroundColor = '';
              }
            }, 420);
          });
        }
      }

      // modal panel
      const pmPanel = document.querySelector('.p-modal.is-open .p-modal__panel') || document.querySelector('#productModal .p-modal__panel');
      if (pmPanel) {
        const pmBtn = pmPanel.querySelector(`[data-action="toggle-cart"][data-product-id="${pid}"]`);
        if (pmBtn) {
          pmPanel.classList.remove('is-removed');
          forceRepaint(pmPanel);

          const pmCartText = pmPanel.querySelector('#pmCartText');

          if (in_cart) {
            requestAnimationFrame(() => {
              pmPanel.classList.add('is-in-cart');
              if (pmCartText) pmCartText.textContent = 'В корзине';
              pmPanel.style.backgroundColor = '';
            });
          } else {
            pmPanel.classList.remove('is-in-cart');
            pmPanel.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#f3f4f6';
            requestAnimationFrame(() => {
              if (pmCartText) pmCartText.textContent = 'В корзину';
              pmPanel.classList.add('is-removed');
              window.setTimeout(() => {
                if (pmPanel) {
                  pmPanel.classList.remove('is-removed');
                  pmPanel.style.backgroundColor = '';
                }
              }, 420);
            });
          }
        }
      }
    });
  }

  function applyStateToDOM(root) {
    const scope = root || document;

    scope.querySelectorAll('[data-action="toggle-favorite"][data-product-id]').forEach((btn) => {
      const pid = btn.dataset.productId;
      setFavActive(btn, state.favorites.has(pid));
    });

    scope.querySelectorAll('[data-action="toggle-cart"][data-product-id]').forEach((btn) => {
      const pid = btn.dataset.productId;
      setCartActive(btn, state.cart.has(pid));
    });

    // ensure container visuals are applied for items currently in cart
    state.cart.forEach(pid => applyCartVisualStateForProduct(pid, true));
  }

  function updateHeaderBadges(summary) {
    if (!summary) return;

    const cartQtyEl = document.querySelector('[data-badge="cart-qty"]');
    if (cartQtyEl && summary.cart_summary) cartQtyEl.textContent = String(summary.cart_summary.total_qty || 0);

    const favCountEl = document.querySelector('[data-badge="fav-count"]');
    if (favCountEl && summary.favorites_summary) favCountEl.textContent = String(summary.favorites_summary.count || 0);
  }

  async function loadState() {
    try {
      const data = await apiGet('/api/state/');
      state.cart = new Set((data.cart_product_ids || []).map(String));
      state.favorites = new Set((data.favorite_ids || []).map(String));

      applyStateToDOM();
      updateHeaderBadges(data);
    } catch (e) {
      console.warn('state load failed', e);
    }
  }

  // делегированный обработчик кликов
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
          .forEach((btn) => {
            setCartActive(btn, data.in_cart);

            // если ��то кнопка в модалке — меняем текст на самой модалке (fallback)
            const pmCartText = document.getElementById('pmCartText');
            if (btn.id === 'pmCartBtn' && pmCartText) {
              pmCartText.textContent = data.in_cart ? 'В корзине' : 'В корзину';
            }
          });

        // New: update containers/cards/modal visuals reliably
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

  // старт
  document.addEventListener('DOMContentLoaded', function () {
    loadState().catch((e) => console.warn('state load failed', e));
  });

  // expose API & listener
  // window.ShopApplyStateToDOM = applyStateToDOM; // можно раскомментировать, если нужно
  window.ShopState = {
    hasInCart: (pid) => state.cart.has(String(pid)),
    hasInFav: (pid) => state.favorites.has(String(pid)),
    applyToDOM: applyStateToDOM,
  };

  window.addEventListener('cart:changed', function () {
    loadState().catch(() => {});
  });
})();

// ensure header always considered for main offset
(function () {
  function updateHeaderHeight() {
    var header = document.querySelector('.header');
    if (!header) return;
    var h = header.getBoundingClientRect().height;
    document.documentElement.style.setProperty('--header-height', Math.ceil(h) + 'px');
  }

  window.addEventListener('load', updateHeaderHeight);
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(updateHeaderHeight, 120);
  });

  updateHeaderHeight();
})();