(function () {
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
    btn.classList.toggle('is-in-cart', !!active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  }

  function setFavActive(btn, active) {
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
  }

  function updateHeaderBadges(summary) {
    // Опционально: если в хедере будут элементы:
    // <span data-badge="cart-qty"></span>, <span data-badge="fav-count"></span>
    if (!summary) return;

    const cartQtyEl = document.querySelector('[data-badge="cart-qty"]');
    if (cartQtyEl && summary.cart_summary) cartQtyEl.textContent = String(summary.cart_summary.total_qty || 0);

    const favCountEl = document.querySelector('[data-badge="fav-count"]');
    if (favCountEl && summary.favorites_summary) favCountEl.textContent = String(summary.favorites_summary.count || 0);
  }

  async function loadState() {
    const data = await apiGet('/api/state/');
    state.cart = new Set((data.cart_product_ids || []).map(String));
    state.favorites = new Set((data.favorite_ids || []).map(String));

    applyStateToDOM();
    updateHeaderBadges(data);
  }

  // клики везде (каталог, главная, модалки, акции)
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

        // применяем ко всем кнопкам этого товара на странице (в т.ч. в модалке)
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

        document.querySelectorAll(`[data-action="toggle-cart"][data-product-id="${pid}"]`)
          .forEach((btn) => {
            setCartActive(btn, data.in_cart);

            // если это кнопка в модалке — меняем текст
            const txt = btn.querySelector('#pmCartText') || btn.querySelector('[data-cart-text]');
            const pmCartText = document.getElementById('pmCartText');
            if (btn.id === 'pmCartBtn' && pmCartText) {
              pmCartText.textContent = data.in_cart ? 'В корзине' : 'В корзину';
            }
          });

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

  // если ты рендеришь HTML модалки динамически (innerHTML), можно дергать:
  // window.ShopApplyStateToDOM = applyStateToDOM;
    window.ShopState = {
    hasInCart: (pid) => state.cart.has(String(pid)),
    hasInFav: (pid) => state.favorites.has(String(pid)),
    applyToDOM: applyStateToDOM,
  };
    window.addEventListener('cart:changed', function () {
  loadState().catch(() => {});
});
})();