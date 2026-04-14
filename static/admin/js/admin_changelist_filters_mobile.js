// admin_changelist_filters_mobile_simple.js
// Простое перемещение блока фильтра (#changelist-filter) перед контентом на мобильных.
// При ширине больше порога — возвращаем на исходное место.
// Никаких sticky/position/fixed — только reorder в DOM.

(function () {
  const MOBILE_MAX = 900; // порог ширины (px) — подправьте при необходимости
  let filterEl = null;
  let originalParent = null;
  let originalNext = null;
  let moved = false;
  let contentEl = null;

  function init() {
    filterEl = document.getElementById('changelist-filter') || document.querySelector('#changelist-filter');
    contentEl = document.getElementById('content') || document.getElementById('content-main') || document.querySelector('#content');
    if (!filterEl || !contentEl) return;

    originalParent = filterEl.parentNode;
    originalNext = filterEl.nextElementSibling;

    handleResize();

    window.addEventListener('resize', debounce(handleResize, 120));
    // на случай PJAX/динамики в админке
    document.addEventListener('pjax:complete', function () { setTimeout(handleResize, 100); });
  }

  function handleResize() {
    const w = window.innerWidth || document.documentElement.clientWidth;
    if (w <= MOBILE_MAX) {
      moveFilterToTop();
    } else {
      restoreFilter();
    }
  }

  function moveFilterToTop() {
    if (moved || !filterEl || !contentEl) return;
    const parent = contentEl.parentNode;
    if (!parent) return;
    parent.insertBefore(filterEl, contentEl);
    filterEl.classList.add('admin-changelist-filter-mobile-top-simple');
    moved = true;
  }

  function restoreFilter() {
    if (!moved || !filterEl) return;
    if (originalParent) {
      if (originalNext) {
        originalParent.insertBefore(filterEl, originalNext);
      } else {
        originalParent.appendChild(filterEl);
      }
    }
    filterEl.classList.remove('admin-changelist-filter-mobile-top-simple');
    moved = false;
  }

  function debounce(fn, delay) {
    let t;
    return function () {
      const args = arguments;
      const ctx = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, delay);
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();