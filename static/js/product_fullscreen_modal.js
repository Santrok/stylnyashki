// ---------- Product fullscreen modal ----------
const modal = document.getElementById('productModal');
const pmImg = document.getElementById('pmImg');
const pmBrand = document.getElementById('pmBrand');
const pmName = document.getElementById('pmName');
const pmSizes = document.getElementById('pmSizes');
const pmPriceOld = document.getElementById('pmPriceOld');
const pmPrice = document.getElementById('pmPrice');

function openProductModal(card) {
  if (!modal || !card) return;

  // контекст (например: cart) — чтобы управлять видимостью кнопок
  const context = card.dataset.modalContext || '';
  const actionsBlock = modal.querySelector('.p-modal__actions');

  if (actionsBlock) {
    // В корзине скрываем кнопки "в корзину" и "в избранное"
    actionsBlock.style.display = (context === 'cart') ? 'none' : '';
  }

  const productId = card.dataset.productId || '';
  const pmCartBtn = document.getElementById('pmCartBtn');
  const pmFavBtn = document.getElementById('pmFavBtn');
  const pmCartText = document.getElementById('pmCartText');

  if (pmCartBtn) pmCartBtn.dataset.productId = productId;
  if (pmFavBtn) pmFavBtn.dataset.productId = productId;

  // состояние "в корзине" + текст
  const inCart = window.ShopState && typeof window.ShopState.hasInCart === 'function'
    ? window.ShopState.hasInCart(productId)
    : false;

  if (pmCartBtn) {
    pmCartBtn.classList.toggle('is-in-cart', inCart);
    if (pmCartText) pmCartText.textContent = inCart ? 'В корзине' : 'В корзину';
  }

  // состояние избранного (иконка)
  if (window.ShopState && typeof window.ShopState.applyToDOM === 'function') {
    window.ShopState.applyToDOM(modal); // применит fav/cart состояния ко всем кнопкам внутри модалки
  }

  const name = card.dataset.name || '';
  const brand = card.dataset.brand || '';
  const image = card.dataset.image || '';
  const price = card.dataset.price || '';
  const discount = parseInt(card.dataset.discount || '0', 10);
  const discounted = card.dataset.priceDiscounted || price;

  if (pmImg) { pmImg.src = image; pmImg.alt = name; }
  if (pmBrand) pmBrand.textContent = brand;
  if (pmName) pmName.textContent = name;

  // sizes: берём из pill'ов на карточке (каталог: .meta-pill, корзина: .pill)
  if (pmSizes) {
    pmSizes.innerHTML = '';
    const pills = card.querySelectorAll('.meta-pill, .pill');
    pills.forEach(p => {
      const el = document.createElement('span');
      el.className = 'p-modal__size';
      el.textContent = p.textContent.trim();
      pmSizes.appendChild(el);
    });
  }

  if (discount > 0) {
    if (pmPriceOld) { pmPriceOld.style.display = ''; pmPriceOld.textContent = `${price} ƃ`; }
    if (pmPrice) pmPrice.textContent = `${discounted} ƃ`;
  } else {
    if (pmPriceOld) { pmPriceOld.style.display = 'none'; pmPriceOld.textContent = ''; }
    if (pmPrice) pmPrice.textContent = `${price} ƃ`;
  }

  modal.classList.remove('is-leaving');
  modal.classList.add('is-open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('menu-open');
}

function closeProductModal() {
  if (!modal) return;

  // если уже закрываем — не дёргаем повторно
  if (!modal.classList.contains('is-open')) return;

  modal.classList.add('is-leaving');

  // время должно совпадать с CSS transition (180-200ms)
  window.setTimeout(function () {
    modal.classList.remove('is-open');
    modal.classList.remove('is-leaving');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-open');
  }, 200);
}

document.addEventListener('click', function (e) {
  // 1) закрытие
  const closeBtn = e.target.closest('[data-close="1"]');
  if (closeBtn) {
    closeProductModal();
    return;
  }

  // 2) запрет открытия модалки по клику на элементы управления
  // (удаление, кнопки корзины/избранного и т.п.)
  const noOpen = e.target.closest('[data-no-open="1"]');
  if (noOpen) return;

  // 3) универсальное открытие:
  // - карточки каталога (.js-product-card)
  // - элементы из корзины/главной/акций, где есть data-action="open-product-modal"
  const opener = e.target.closest('[data-action="open-product-modal"][data-product-id]');
  if (opener) {
    openProductModal(opener);
    return;
  }

  const card = e.target.closest('.js-product-card');
  if (card) {
    openProductModal(card);
  }
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closeProductModal();
});

document.addEventListener('keydown', function (e) {
  if (e.key !== 'Enter') return;

  // поддержка Enter:
  // 1) если фокус на .js-product-card
  if (document.activeElement && document.activeElement.classList.contains('js-product-card')) {
    openProductModal(document.activeElement);
    return;
  }

  // 2) если фокус на любом opener с data-action="open-product-modal"
  if (document.activeElement && document.activeElement.matches('[data-action="open-product-modal"][data-product-id]')) {
    openProductModal(document.activeElement);
  }
});