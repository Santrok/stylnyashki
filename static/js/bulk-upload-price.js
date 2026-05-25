document.addEventListener('DOMContentLoaded', function () {
  const sizesSelect = document.getElementById('sizes');
  const priceInput = document.getElementById('price');
  if (!sizesSelect || !priceInput) return;

  // mapping: visible option text (range) -> price
  const PRICE_MAP = {
    "50-74": 7,
    "80-92": 7,
    "98-104": 10,
    "110-116": 10,
    "122-128": 10,
    "134-146": 12,
    "152-158": 12
  };

  function extractRangeFromOptionText(text) {
    if (!text) return null;
    const t = text.trim();
    // пытаемся вытащить шаблон "NN-NN" или "NNN-NNN" в начале строки
    const m = t.match(/^(\d{1,3}-\d{1,3})/);
    if (m) return m[1];
    // если не совпало, можно попробовать взять часть до скобки или до первого пробела
    const beforeParen = t.split('(')[0].trim();
    if (beforeParen) return beforeParen;
    return t;
  }

  function updatePriceFromSizes() {
    // Для single-select: selectedOptions всё равно вернёт выбранную опцию в виде списка длины 1
    const selected = Array.from(sizesSelect.selectedOptions || []);
    if (selected.length === 0) return;

    const prices = selected
      .map(opt => {
        const key = extractRangeFromOptionText(opt.textContent || opt.innerText || '');
        return key ? PRICE_MAP[key] : undefined;
      })
      .filter(p => p !== undefined)
      .map(Number)
      .filter(Number.isFinite);

    if (prices.length === 0) return;
    const target = Math.max(...prices); // логика: выбираем максимальную цену
    priceInput.value = target.toFixed(2);
    priceInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  sizesSelect.addEventListener('change', updatePriceFromSizes);
  updatePriceFromSizes(); // инициализация при загрузке страницы
});