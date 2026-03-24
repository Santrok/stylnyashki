(function () {
  const filtersOverlay = document.getElementById('mobileFilters');
  const filtersOpenBtn = document.getElementById('filtersOpenBtn');
  const filtersCloseBtn = document.getElementById('filtersCloseBtn');
  const filtersApplyBtn = document.getElementById('filtersApplyBtn');
  const sidebar = document.getElementById('filtersSidebar');
  const filtersDrawerBody = document.getElementById('filtersDrawerBody');

  function openFilters() {
    if (!filtersOverlay) return;

    if (sidebar && filtersDrawerBody) {
      filtersDrawerBody.innerHTML = '';

      const clone = sidebar.cloneNode(true);
      clone.style.display = 'flex';
      clone.style.width = '100%';
      clone.style.borderRight = 'none';
      clone.style.height = 'auto';
      clone.classList.remove('custom-scroll');

      filtersDrawerBody.appendChild(clone);
    }

    filtersOverlay.classList.add('is-open');
    filtersOverlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('menu-open');
  }

  function closeFilters() {
    if (!filtersOverlay) return;
    filtersOverlay.classList.remove('is-open');
    filtersOverlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-open');
  }

  filtersOpenBtn && filtersOpenBtn.addEventListener('click', openFilters);
  filtersCloseBtn && filtersCloseBtn.addEventListener('click', closeFilters);

  // Apply = submit form in drawer (if exists), else just close
  filtersApplyBtn && filtersApplyBtn.addEventListener('click', function () {
    const form = filtersDrawerBody ? filtersDrawerBody.querySelector('form') : null;
    if (form) {
      form.submit();
      return;
    }
    closeFilters();
  });

  filtersOverlay && filtersOverlay.addEventListener('click', function (e) {
    if (e.target === filtersOverlay) closeFilters();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeFilters();
  });
})();

  // ---------- Price range (double slider) ----------
  const minRange = document.getElementById('minPriceRange');
  const maxRange = document.getElementById('maxPriceRange');
  const minInput = document.getElementById('minPriceInput');
  const maxInput = document.getElementById('maxPriceInput');
  const fill = document.getElementById('priceRangeFill');
  const minLabel = document.getElementById('priceMinLabel');
  const maxLabel = document.getElementById('priceMaxLabel');
  const priceRange = document.getElementById('priceRange');

  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

  function updateFill(minVal, maxVal) {
    if (!priceRange || !fill) return;

    const min = parseFloat(priceRange.dataset.min || '0');
    const max = parseFloat(priceRange.dataset.max || '0');

    if (max <= min) {
      fill.style.left = '0%';
      fill.style.width = '100%';
      return;
    }

    const left = ((minVal - min) / (max - min)) * 100;
    const right = ((maxVal - min) / (max - min)) * 100;

    fill.style.left = `${left}%`;
    fill.style.width = `${Math.max(0, right - left)}%`;
  }

  function syncFromRanges() {
    if (!minRange || !maxRange) return;

    let minVal = parseInt(minRange.value || '0', 10);
    let maxVal = parseInt(maxRange.value || '0', 10);

    // не даём min > max
    if (minVal > maxVal) {
      // если двигаем min — подтянем max, если двигаем max — подтянем min
      const active = document.activeElement;
      if (active === minRange) maxVal = minVal;
      else minVal = maxVal;

      minRange.value = String(minVal);
      maxRange.value = String(maxVal);
    }

    if (minInput) minInput.value = String(minVal);
    if (maxInput) maxInput.value = String(maxVal);

    if (minLabel) minLabel.textContent = String(minVal);
    if (maxLabel) maxLabel.textContent = String(maxVal);

    updateFill(minVal, maxVal);
  }

  function syncFromInputs() {
    if (!minRange || !maxRange || !priceRange) return;

    const min = parseInt(priceRange.dataset.min || '0', 10);
    const max = parseInt(priceRange.dataset.max || '0', 10);

    let minVal = minInput && minInput.value !== '' ? parseInt(minInput.value, 10) : min;
    let maxVal = maxInput && maxInput.value !== '' ? parseInt(maxInput.value, 10) : max;

    if (Number.isNaN(minVal)) minVal = min;
    if (Number.isNaN(maxVal)) maxVal = max;

    minVal = clamp(minVal, min, max);
    maxVal = clamp(maxVal, min, max);

    if (minVal > maxVal) minVal = maxVal;

    minRange.value = String(minVal);
    maxRange.value = String(maxVal);

    if (minLabel) minLabel.textContent = String(minVal);
    if (maxLabel) maxLabel.textContent = String(maxVal);

    updateFill(minVal, maxVal);
  }

  // disable if one price
  if (priceRange) {
    const min = parseInt(priceRange.dataset.min || '0', 10);
    const max = parseInt(priceRange.dataset.max || '0', 10);
    if (max <= min) {
      if (minRange) minRange.disabled = true;
      if (maxRange) maxRange.disabled = true;
    }
  }

  minRange && minRange.addEventListener('input', syncFromRanges);
  maxRange && maxRange.addEventListener('input', syncFromRanges);

  minInput && minInput.addEventListener('input', syncFromInputs);
  maxInput && maxInput.addEventListener('input', syncFromInputs);

  // initial render
  syncFromRanges();
