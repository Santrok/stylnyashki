// static/js/bulk-upload.js
document.addEventListener('DOMContentLoaded', function () {
  const imagesInput = document.getElementById('imagesInput');
  const filesCount = document.getElementById('filesCount');
  const startBtn = document.getElementById('startUploadBtn');
  const progressWrap = document.getElementById('progressWrap');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const uploadStatus = document.getElementById('uploadStatus');
  const resultArea = document.getElementById('resultArea');

  let files = [];

  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  imagesInput.addEventListener('change', function () {
    files = Array.from(imagesInput.files || []);
    filesCount.textContent = `Выбрано файлов: ${files.length}`;
  });

  async function uploadBatch(batchFiles, commonData) {
    const fd = new FormData();
    // append common fields
    Object.entries(commonData).forEach(([k, v]) => {
      if (Array.isArray(v)) {
        v.forEach(x => fd.append(k, x));
      } else if (v !== null && typeof v !== 'undefined' && v !== '') {
        fd.append(k, v);
      }
    });
    // append images
    batchFiles.forEach(f => fd.append('images', f, f.name));

    const resp = await fetch('/api/staff/products/bulk-upload/', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrftoken
      }
    });

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(`Server responded with ${resp.status}: ${text}`);
    }
    return resp.json();
  }

  startBtn.addEventListener('click', async function () {
    if (!files || files.length === 0) {
      alert('Выберите изображения для загрузки');
      return;
    }

    startBtn.disabled = true;
    resultArea.innerHTML = '';
    uploadStatus.textContent = 'Готовлюсь...';

    // read common fields
    const name = document.getElementById('name').value.trim();
    if (!name) {
      alert('Поле Название обязательно');
      startBtn.disabled = false;
      return;
    }
    const brand = document.getElementById('brand').value.trim();
    const category_id = document.getElementById('category_id').value;
    const season = document.getElementById('season').value;
    const price = document.getElementById('price').value;
    const discount = document.getElementById('discount').value;
    const is_active = document.getElementById('is_active').checked ? '1' : '';
    const sizesSelect = document.getElementById('sizes');
    const sizes = Array.from(sizesSelect.selectedOptions).map(o => o.value);

    const commonData = {
      name, brand, category_id, season, price, discount, is_active
    };
    if (sizes.length) commonData['sizes'] = sizes;

    // batching
    const batchSize = 15; // recommended 10-20, server allows up to 50
    const total = files.length;
    let uploadedTotal = 0;
    let createdTotal = 0;
    let allErrors = [];

    progressWrap.style.display = 'block';

    for (let i = 0; i < files.length; i += batchSize) {
      const batch = files.slice(i, i + batchSize);
      uploadStatus.textContent = `Загрузка ${i + 1}–${Math.min(i + batchSize, total)} из ${total}...`;
      try {
        const result = await uploadBatch(batch, commonData);
        createdTotal += result.created || 0;
        if (result.errors && result.errors.length) {
          allErrors.push(...result.errors);
        }
      } catch (err) {
        allErrors.push({batchStart: i, error: err.message});
      }

      uploadedTotal = Math.min(i + batchSize, total);
      const pct = Math.round((uploadedTotal / total) * 100);
      progressBar.style.width = pct + '%';
      progressText.textContent = `Обработано ${uploadedTotal} из ${total} (${pct}%)`;
      // small delay to keep UI responsive
      await new Promise(r => setTimeout(r, 200));
    }

    uploadStatus.textContent = `Готово. Создано: ${createdTotal}. Ошибок: ${allErrors.length}`;
    resultArea.innerHTML = '';
    if (allErrors.length) {
      const el = document.createElement('pre');
      el.textContent = JSON.stringify(allErrors, null, 2);
      resultArea.appendChild(el);
    }

    startBtn.disabled = false;
  });
});