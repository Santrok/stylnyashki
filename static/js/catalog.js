// static/js/catalog.js
// Mobile filters drawer + double-range sync + form move logic with smooth transitions and reflow
document.addEventListener('DOMContentLoaded', function () {
  // Elements
  const mobileOverlay = document.getElementById('mobileFilters');
  const filtersOpenBtn = document.getElementById('filtersOpenBtn');
  const filtersCloseBtn = document.getElementById('filtersCloseBtn');
  const filtersApplyBtn = document.getElementById('filtersApplyBtn');
  const filtersDrawerBody = document.getElementById('filtersDrawerBody');
  const filtersForm = document.getElementById('filtersForm');
  const filtersSidebar = document.getElementById('filtersSidebar');

  // Drawer element inside overlay
  const filtersDrawer = mobileOverlay ? mobileOverlay.querySelector('.filters-drawer') : null;

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
    moveFormToDrawer();
    // Force reflow so transition will run when we add the class
    // eslint-disable-next-line no-unused-expressions
    void mobileOverlay.offsetWidth;
    mobileOverlay.classList.add('is-open');
    mobileOverlay.setAttribute('aria-hidden', 'false');
    const first = mobileOverlay.querySelector('button, a, input, select, textarea');
    if (first) first.focus();
    document.documentElement.style.overflow = 'hidden';
    waitingForCloseTransition = false;
  }

  function handleCloseTransitionEnd(e) {
    if (!waitingForCloseTransition) return;
    // ensure we only act for overlay's opacity transition or drawer transform end
    // move form back now
    moveFormBackToSidebar();
    waitingForCloseTransition = false;
    mobileOverlay.removeEventListener('transitionend', handleCloseTransitionEnd);
  }

  function closeFilters() {
    if (!mobileOverlay) return;
    // remove is-open to start hide transition
    mobileOverlay.classList.remove('is-open');
    mobileOverlay.setAttribute('aria-hidden', 'true');
    document.documentElement.style.overflow = '';
    if (filtersOpenBtn) filtersOpenBtn.focus();

    if (formMoved) {
      waitingForCloseTransition = true;
      // wait for the overlay transition to finish before moving form back
      mobileOverlay.addEventListener('transitionend', handleCloseTransitionEnd);
      // safety fallback
      setTimeout(() => {
        if (waitingForCloseTransition) handleCloseTransitionEnd({ target: mobileOverlay });
      }, 500);
    } else {
      moveFormBackToSidebar();
    }
  }

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

  // ---------- Double range (price) sync (unchanged logic) ----------
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