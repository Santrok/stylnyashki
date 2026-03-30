document.addEventListener('DOMContentLoaded', function () {
  const imagesInput = document.getElementById('imagesInput');
  const filesCount = document.getElementById('filesCount');
  const startBtn = document.getElementById('startUploadBtn');
  const progressWrap = document.getElementById('progressWrap');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const uploadStatus = document.getElementById('uploadStatus');
  const resultArea = document.getElementById('resultArea');

  // client-side limits (optional)
  const MAX_FILE_SIZE = 12 * 1024 * 1024; // 12 MB per file
  const MAX_TOTAL_FILES = 150;

  // files array holds selected File objects across multiple selects
  let files = [];

  // ensure ModelForm fields look consistent (adds .f__input to selects/inputs if not present)
  (function normalizeFormFields() {
    const form = document.getElementById('bulkUploadForm');
    if (!form) return;
    const selectors = [
      'select',
      'input[type="text"]',
      'input[type="number"]',
      'input[type="email"]',
      'textarea'
    ];
    selectors.forEach(sel => {
      form.querySelectorAll(sel).forEach(el => {
        if (!el.classList.contains('f__input')) el.classList.add('f__input');
      });
    });
  })();

  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  function updateFilesCount() {
    filesCount.textContent = `Выбрано файлов: ${files.length}`;
  }

  function appendFiles(fileList) {
    // Accept FileList or Array<File>
    const added = [];
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i];
      if (!f || !f.type || !f.type.startsWith('image/')) continue; // skip non-images

      if (f.size && f.size > MAX_FILE_SIZE) {
        // skip files that are too large
        alert(`Файл "${f.name}" пропущен — превышает максимальный размер ${Math.round(MAX_FILE_SIZE/1024/1024)}MB`);
        continue;
      }

      // avoid duplicates (name + size + type)
      const exists = files.some(existing => existing.name === f.name && existing.size === f.size && existing.type === f.type);
      if (exists) continue;

      // total files limit
      if (files.length + added.length >= MAX_TOTAL_FILES) {
        alert(`Достигнут лимит файлов: ${MAX_TOTAL_FILES}. Остальные файлы проигнорированы.`);
        break;
      }

      added.push(f);
    }

    if (added.length) {
      files = files.concat(added);
      updateFilesCount();
    }
  }

  // expose accessor for other scripts (upload code will use this files array)
  window.getBulkFiles = () => files;
  window.clearBulkFiles = () => { files = []; updateFilesCount(); };

  // handle input change: append, then clear input.value so user can select same file(s) again
  if (imagesInput) {
    imagesInput.addEventListener('change', function (e) {
      appendFiles(e.target.files || []);
      // reset input to allow picking same files again if needed
      imagesInput.value = '';
    });
  }

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
    const category_id = document.getElementById('category_id') ? document.getElementById('category_id').value : '';
    const season = document.getElementById('season') ? document.getElementById('season').value : '';
    const price = document.getElementById('price') ? document.getElementById('price').value : '';
    const discount = document.getElementById('discount') ? document.getElementById('discount').value : '';
    const is_active = document.getElementById('is_active') ? (document.getElementById('is_active').checked ? '1' : '') : '';
    const sizesSelect = document.getElementById('sizes');
    const sizes = sizesSelect ? Array.from(sizesSelect.selectedOptions).map(o => o.value) : [];

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