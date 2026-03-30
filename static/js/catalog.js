// static/js/catalog.js
// Mobile filters drawer + double-range sync + form move logic with smooth transitions (med slow)
//
// Notes:
// - Reads CSS vars --overlay-duration and --drawer-duration to sync JS fallback.
// - Waits for transitionend (opacity or transform) before moving form back to sidebar.
// - Forces reflow before adding .is-open to ensure transitions run.

document.addEventListener('DOMContentLoaded', function () {
  // Elements
  const mobileOverlay = document.getElementById('mobileFilters');
  const filtersOpenBtn = document.getElementById('filtersOpenBtn');
  const filtersCloseBtn = document.getElementById('filtersCloseBtn');
  const filtersApplyBtn = document.getElementById('filtersApplyBtn');
  const filtersDrawerBody = document.getElementById('filtersDrawerBody');
  const filtersForm = document.getElementById('filtersForm');
  const filtersSidebar = document.getElementById('filtersSidebar');

  // Helper: read CSS time string like "380ms" or "0.38s" -> ms number
  function msFromCssTime(s) {
    if (!s) return 400;
    s = s.trim();
    if (s.endsWith('ms')) return parseFloat(s);
    if (s.endsWith('s')) return parseFloat(s) * 1000;
    return parseFloat(s) || 400;
  }

  // read durations from CSS variables (fallback to our "slow" defaults)
  const css = getComputedStyle(document.documentElement);
  const overlayDurationMs = msFromCssTime(css.getPropertyValue('--overlay-duration').trim() || '380ms');
  const drawerDurationMs = msFromCssTime(css.getPropertyValue('--drawer-duration').trim() || '420ms');
  const fallbackDelay = Math.max(overlayDurationMs, drawerDurationMs) + 150; // safety margin

  // State
  let formMoved = false;
  let waitingForCloseTransition = false;

  function moveFormToDrawer() {
    if (!filtersForm || !filtersDrawerBody || formMoved) return;
    filtersDrawerBody.appendChild(filtersForm);
    formMoved = true;
  }

  function moveFormBackToSidebar() {
    if (!filtersForm || !filtersSidebar || !formMoved) return;
    filtersSidebar.appendChild(filtersForm);
    formMoved = false;
  }

  function openFilters() {
    if (!mobileOverlay) return;
    // move form first (so user sees real controls)
    moveFormToDrawer();
    // Force reflow so transition will animate
    // eslint-disable-next-line no-unused-expressions
    void mobileOverlay.offsetWidth;
    mobileOverlay.classList.add('is-open');
    mobileOverlay.setAttribute('aria-hidden', 'false');
    // focus first interactive
    const first = mobileOverlay.querySelector('button, a, input, select, textarea');
    if (first) first.focus();
    document.documentElement.style.overflow = 'hidden';
    waitingForCloseTransition = false;
  }

  function handleCloseTransitionEnd(e) {
    // Only react for overlay opacity or drawer transform completion (avoid other transitions)
    if (e && e.propertyName && !['opacity', 'transform'].includes(e.propertyName)) return;
    if (!waitingForCloseTransition) return;
    moveFormBackToSidebar();
    waitingForCloseTransition = false;
    mobileOverlay.removeEventListener('transitionend', handleCloseTransitionEnd);
  }

  function closeFilters() {
    if (!mobileOverlay) return;
    // start hide transition
    mobileOverlay.classList.remove('is-open');
    mobileOverlay.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = '';
    if (filtersOpenBtn) filtersOpenBtn.focus();

    if (formMoved) {
      waitingForCloseTransition = true;
      // listen for transitionend; transitionend bubbles so we can listen on overlay
      mobileOverlay.addEventListener('transitionend', handleCloseTransitionEnd);
      // fallback in case transitionend didn't fire
      setTimeout(() => {
        if (waitingForCloseTransition) handleCloseTransitionEnd({ propertyName: 'opacity', target: mobileOverlay });
      }, fallbackDelay);
    } else {
      moveFormBackToSidebar();
    }
  }

  // Attach listeners
  if (filtersOpenBtn) filtersOpenBtn.addEventListener('click', (e) => { e.preventDefault(); openFilters(); });
  if (filtersCloseBtn) filtersCloseBtn.addEventListener('click', (e) => { e.preventDefault(); closeFilters(); });
  if (filtersApplyBtn) filtersApplyBtn.addEventListener('click', (e) => {
    e.preventDefault();
    if (filtersForm) filtersForm.submit();
    else closeFilters();
  });

  if (mobileOverlay) {
    mobileOverlay.addEventListener('click', (e) => { if (e.target === mobileOverlay) closeFilters(); });
  }

  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && mobileOverlay && mobileOverlay.classList.contains('is-open')) closeFilters(); });

  // on resize back to desktop, return form immediately
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 768 && formMoved) {
      if (mobileOverlay && mobileOverlay.classList.contains('is-open')) {
        mobileOverlay.classList.remove('is-open');
        mobileOverlay.setAttribute('aria-hidden', 'true');
        document.documentElement.style.overflow = '';
      }
      moveFormBackToSidebar();
    }
  });

  // ---------- Double range (price) sync ----------
  const minRange = document.getElementById('minPriceRange');
  const maxRange = document.getElementById('maxPriceRange');
  const minInput = document.getElementById('minPriceInput');
  const maxInput = document.getElementById('maxPriceInput');
  const minLabel = document.getElementById('priceMinLabel');
  const maxLabel = document.getElementById('priceMaxLabel');
  const rangeFill = document.getElementById('priceRangeFill');
  const rangeWrapper = document.getElementById('priceRange');

  if (rangeWrapper && minRange && maxRange && rangeFill) {
    const minBound = Number(rangeWrapper.dataset.min || 0);
    const maxBound = Number(rangeWrapper.dataset.max || 0) || minBound;

    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    function updateFill(minVal, maxVal) {
      const total = (maxBound - minBound) || 1;
      const leftPct = ((minVal - minBound) / total) * 100;
      const rightPct = ((maxVal - minBound) / total) * 100;
      const width = Math.max(0, rightPct - leftPct);
      rangeFill.style.left = leftPct + '%';
      rangeFill.style.width = width + '%';
    }

    function syncFromRanges(e) {
      let minVal = Number(minRange.value);
      let maxVal = Number(maxRange.value);

      if (minVal > maxVal) {
        if (e && e.target === minRange) {
          minVal = maxVal;
          minRange.value = minVal;
        } else {
          maxVal = minVal;
          maxRange.value = maxVal;
        }
      }

      if (minInput) minInput.value = Math.round(minVal);
      if (maxInput) maxInput.value = Math.round(maxVal);
      if (minLabel) minLabel.textContent = minVal ? Math.round(minVal) : '—';
      if (maxLabel) maxLabel.textContent = maxVal ? Math.round(maxVal) : '—';

      updateFill(minVal, maxVal);
    }

    function syncFromInputs() {
      let minVal = Number(minInput && minInput.value ? minInput.value : minBound);
      let maxVal = Number(maxInput && maxInput.value ? maxInput.value : maxBound);

      minVal = clamp(minVal, minBound, maxBound);
      maxVal = clamp(maxVal, minBound, maxBound);

      if (minVal > maxVal) {
        const tmp = minVal; minVal = maxVal; maxVal = tmp;
      }

      minRange.value = minVal;
      maxRange.value = maxVal;
      if (minLabel) minLabel.textContent = minVal ? Math.round(minVal) : '—';
      if (maxLabel) maxLabel.textContent = maxVal ? Math.round(maxVal) : '—';
      updateFill(minVal, maxVal);
    }

    minRange.style.pointerEvents = 'auto';
    maxRange.style.pointerEvents = 'auto';

    minRange.addEventListener('input', syncFromRanges);
    maxRange.addEventListener('input', syncFromRanges);

    if (minInput) {
      minInput.addEventListener('input', syncFromInputs);
      minInput.addEventListener('change', syncFromInputs);
    }
    if (maxInput) {
      maxInput.addEventListener('input', syncFromInputs);
      maxInput.addEventListener('change', syncFromInputs);
    }

    (function initRange() {
      if (!minRange.hasAttribute('min')) minRange.min = minBound;
      if (!minRange.hasAttribute('max')) minRange.max = maxBound;
      if (!maxRange.hasAttribute('min')) maxRange.min = minBound;
      if (!maxRange.hasAttribute('max')) maxRange.max = maxBound;

      const initMin = Number(minRange.value || (minInput && minInput.value) || minBound);
      const initMax = Number(maxRange.value || (maxInput && maxInput.value) || maxBound);

      minRange.value = clamp(initMin, minBound, maxBound);
      maxRange.value = clamp(initMax, minBound, maxBound);

      syncFromRanges();
    })();
  }

  // Make sort select full-width on small screens
  const sortMobile = document.querySelector('.sort-mobile');
  if (sortMobile) {
    function adjustSortWidth() { if (window.innerWidth <= 480) sortMobile.style.width = '100%'; else sortMobile.style.width = ''; }
    adjustSortWidth();
    window.addEventListener('resize', adjustSortWidth);
  }
});