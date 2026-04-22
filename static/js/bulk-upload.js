// static/js/bulk_upload.js
// Bulk image uploader with per-thumbnail remove, retries, failed-list handling,
// removal of successfully uploaded files, batching, timeout and cancel support.

document.addEventListener('DOMContentLoaded', function () {
  const imagesInput = document.getElementById('imagesInput');
  const filesCount = document.getElementById('filesCount');
  const startBtn = document.getElementById('startUploadBtn');
  const cancelBtn = document.getElementById('cancelUploadBtn'); // optional
  const progressWrap = document.getElementById('progressWrap');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const uploadStatus = document.getElementById('uploadStatus');
  const resultArea = document.getElementById('resultArea');
  const dropArea = document.getElementById('imagesDropArea'); // optional

  // Config
  const MAX_FILE_SIZE = 12 * 1024 * 1024; // 12 MB
  const MAX_TOTAL_FILES = 150;
  const BATCH_SIZE = 2;
  const MAX_RETRIES = 1; // <-- retry attempts per file
  const REQUEST_TIMEOUT_MS = 5*60*100; // 5 min

  // Internal state
  // files: array of { file: File, attempts: number }
  let files = [];
  // failed files list: array of { file: File, attempts: number, reason: string }
  let failedFiles = [];
  let uploading = false;
  let currentAbortController = null;

  // Helpers
  function fileIdFromFile(file) {
    return `${file.name}::${file.size}`;
  }
  function fileIdFromObj(obj) {
    return fileIdFromFile(obj.file);
  }
  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  function updateFilesCount() {
    if (!filesCount) return;
    filesCount.textContent = `Выбрано файлов: ${files.length}`;
  }

  function isImageFile(f) {
    return f && ((f.type && f.type.startsWith('image/')) || /\.(jpe?g|png|gif|webp|avif|heic?)$/i.test(f.name));
  }

  // Render thumbnail with remove button and attempts/status badge
  function renderPreviewThumbnail(fileObj) {
    if (!resultArea) return;
    const id = fileIdFromObj(fileObj);

    // Avoid duplicate thumbnail if exists
    if (resultArea.querySelector(`[data-file-id="${CSS.escape(id)}"]`)) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'thumb-item';
    wrapper.dataset.fileId = id;
    wrapper.style.display = 'inline-block';
    wrapper.style.margin = '6px';
    wrapper.style.textAlign = 'center';
    wrapper.style.width = '92px';
    wrapper.style.verticalAlign = 'top';

    const imgWrap = document.createElement('div');
    imgWrap.style.position = 'relative';
    imgWrap.style.width = '80px';
    imgWrap.style.height = '80px';
    imgWrap.style.margin = '0 auto';
    imgWrap.style.borderRadius = '4px';
    imgWrap.style.overflow = 'hidden';
    imgWrap.style.background = '#f6f6f6';

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'thumb-remove';
    removeBtn.title = 'Удалить';
    removeBtn.style.position = 'absolute';
    removeBtn.style.right = '4px';
    removeBtn.style.top = '4px';
    removeBtn.style.zIndex = '5';
    removeBtn.style.border = 'none';
    removeBtn.style.background = 'rgba(0,0,0,0.5)';
    removeBtn.style.color = '#fff';
    removeBtn.style.width = '22px';
    removeBtn.style.height = '22px';
    removeBtn.style.borderRadius = '50%';
    removeBtn.style.cursor = 'pointer';
    removeBtn.innerHTML = '×';

    removeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      removeFileById(id);
    });

    imgWrap.appendChild(removeBtn);

    const img = document.createElement('img');
    img.style.width = '80px';
    img.style.height = '80px';
    img.style.objectFit = 'cover';
    img.style.display = 'block';
    img.alt = fileObj.file.name;

    const reader = new FileReader();
    reader.onload = function (ev) {
      img.src = ev.target.result;
    };
    reader.readAsDataURL(fileObj.file);

    imgWrap.appendChild(img);
    wrapper.appendChild(imgWrap);

    const label = document.createElement('div');
    label.style.fontSize = '11px';
    label.style.marginTop = '6px';
    label.style.whiteSpace = 'nowrap';
    label.style.overflow = 'hidden';
    label.style.textOverflow = 'ellipsis';
    label.style.width = '92px';
    label.textContent = fileObj.file.name.length > 18 ? fileObj.file.name.slice(0, 16) + '…' : fileObj.file.name;
    wrapper.appendChild(label);

    const statusSpan = document.createElement('div');
    statusSpan.className = 'thumb-status';
    statusSpan.style.fontSize = '11px';
    statusSpan.style.marginTop = '4px';
    statusSpan.textContent = `Попыток: ${fileObj.attempts}`;
    wrapper.appendChild(statusSpan);

    resultArea.appendChild(wrapper);
  }

  function updateThumbnailAttempts(fileObj) {
    if (!resultArea) return;
    const id = fileIdFromObj(fileObj);
    const wrapper = resultArea.querySelector(`[data-file-id="${CSS.escape(id)}"]`);
    if (!wrapper) return;
    const statusSpan = wrapper.querySelector('.thumb-status');
    if (statusSpan) statusSpan.textContent = `Попыток: ${fileObj.attempts}`;
  }

  function markThumbnailFailed(fileObj, reason) {
    if (!resultArea) return;
    const id = fileIdFromObj(fileObj);
    const wrapper = resultArea.querySelector(`[data-file-id="${CSS.escape(id)}"]`);
    if (!wrapper) return;
    wrapper.classList.add('thumb-failed');
    const statusSpan = wrapper.querySelector('.thumb-status');
    if (statusSpan) statusSpan.textContent = `Ошибка: ${reason || 'неизвестно'}`;
    // optionally style
    wrapper.style.opacity = '0.55';
  }

  function removeThumbnailById(id) {
    if (!resultArea) return;
    const el = resultArea.querySelector(`[data-file-id="${CSS.escape(id)}"]`);
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  // Append new files (from FileList)
  function appendFiles(fileList) {
    if (!fileList || !fileList.length) return;
    const added = [];
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i];
      if (!f) continue;
      if (!isImageFile(f)) continue;
      if (f.size && f.size > MAX_FILE_SIZE) {
        alert(`Файл "${f.name}" пропущен — превышает максимальный размер ${Math.round(MAX_FILE_SIZE / 1024 / 1024)} MB`);
        continue;
      }
      const id = fileIdFromFile(f);
      const exists = files.some(existing => fileIdFromFile(existing.file) === id) || failedFiles.some(fr => fileIdFromFile(fr.file) === id);
      if (exists) continue;
      if (files.length + added.length >= MAX_TOTAL_FILES) {
        alert(`Достигнут лимит файлов: ${MAX_TOTAL_FILES}. Остальные файлы проигнорированы.`);
        break;
      }
      const fileObj = { file: f, attempts: 0 };
      added.push(fileObj);
    }
    if (added.length) {
      files = files.concat(added);
      updateFilesCount();
      renderPreviewThumbnails(added);
    }
  }

  function renderPreviewThumbnails(arr) {
    arr.forEach(obj => renderPreviewThumbnail(obj));
  }

  // remove file by id from queue and DOM
  function removeFileById(id) {
    const idx = files.findIndex(o => fileIdFromObj(o) === id);
    if (idx !== -1) {
      files.splice(idx, 1);
      updateFilesCount();
    }
    // also remove thumbnail
    removeThumbnailById(id);
  }

  // remove files by mapping (array of {name, size?} or strings) and return removed ids
  function removeFilesByNameAndSize(mapping, batchArray) {
    if (!Array.isArray(mapping) || mapping.length === 0) return [];
    const removedIds = [];
    // try to match mapping to files (prefer files in batchArray)
    for (const m of mapping) {
      let name = '', size = null;
      if (typeof m === 'string') name = m;
      else if (m && typeof m === 'object') {
        name = m.name || m.filename || m.original_filename || '';
        size = m.size || m.filesize || null;
      }
      if (!name) continue;
      // first try to find matching in files that are within batchArray
      let idx = files.findIndex(f => f.file.name === name && (size == null || f.file.size == size) && batchArray.some(b => fileIdFromObj(b) === fileIdFromObj(f)));
      if (idx === -1) {
        // then any matching in files
        idx = files.findIndex(f => f.file.name === name && (size == null || f.file.size == size));
      }
      if (idx !== -1) {
        const id = fileIdFromObj(files[idx]);
        removedIds.push(id);
        files.splice(idx, 1);
      }
    }
    // remove thumbnails for removed ids
    removedIds.forEach(id => removeThumbnailById(id));
    if (removedIds.length) updateFilesCount();
    return removedIds;
  }

  // Expose helpers
  window.getBulkFiles = () => files.map(o => o.file);
  window.getFailedFiles = () => failedFiles.map(o => o.file);
  window.clearBulkFiles = () => {
    files = [];
    failedFiles = [];
    updateFilesCount();
    if (resultArea) resultArea.innerHTML = '';
    if (imagesInput) imagesInput.value = '';
  };
  window.removeBulkFileByName = function (filename) {
    const idsToRemove = files.filter(o => o.file.name === filename).map(o => fileIdFromObj(o));
    files = files.filter(o => o.file.name !== filename);
    updateFilesCount();
    idsToRemove.forEach(id => removeThumbnailById(id));
  };

  // file input change
  if (imagesInput) {
    imagesInput.addEventListener('change', function (e) {
      appendFiles(e.target.files || []);
      imagesInput.value = '';
    });
  }

  // drag & drop support
  if (dropArea) {
    ['dragenter', 'dragover'].forEach(ev => dropArea.addEventListener(ev, e => { e.preventDefault(); dropArea.classList.add('drag-over'); }));
    ['dragleave', 'drop'].forEach(ev => dropArea.addEventListener(ev, e => { e.preventDefault(); dropArea.classList.remove('drag-over'); }));
    dropArea.addEventListener('drop', function (e) {
      const dt = e.dataTransfer;
      if (!dt) return;
      appendFiles(dt.files);
    });
  }

  // uploadBatch via fetch
  async function uploadBatch(batchFilesObjs, commonData, signal) {
    const fd = new FormData();
    Object.entries(commonData).forEach(([k, v]) => {
      if (Array.isArray(v)) v.forEach(x => fd.append(k, x));
      else if (v !== null && typeof v !== 'undefined' && v !== '') fd.append(k, v);
    });
    // append files
    batchFilesObjs.forEach(o => fd.append('images', o.file, o.file.name));
    const resp = await fetch('/api/staff/products/bulk-upload/', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrftoken, 'Accept': 'application/json' },
      signal
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`Server responded with ${resp.status}: ${text}`);
    }
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) return resp.json();
    const text = await resp.text();
    try { return JSON.parse(text); } catch (e) { return { created: 0, raw: text }; }
  }

  function withTimeout(promise, ms) {
    const timeout = new Promise((_, reject) => {
      const id = setTimeout(() => reject(new Error('Request timed out')), ms);
    });
    return Promise.race([promise, new Promise((resolve, reject) => setTimeout(() => reject(new Error('Request timed out')), ms)), promise]);
  }
  // Note: implemented with Promise.race inlined above to ensure consistent timeout behavior

  // Reset form & UI
  function resetForm() {
    files = [];
    failedFiles = [];
    updateFilesCount();
    if (resultArea) resultArea.innerHTML = '';
    if (imagesInput) imagesInput.value = '';
    const form = document.getElementById('bulkUploadForm');
    if (form) form.reset();
    if (progressBar) progressBar.style.width = '0%';
    if (progressText) progressText.textContent = '';
    if (progressWrap) progressWrap.style.display = 'none';
    if (uploadStatus) uploadStatus.textContent = '';
    if (startBtn) startBtn.disabled = false;
    if (cancelBtn) cancelBtn.disabled = true;
    if (currentAbortController) { try { currentAbortController.abort(); } catch (e) {} currentAbortController = null; }
    uploading = false;
  }
  window.resetBulkUploadForm = resetForm;

  // Start upload handler (main logic with retries)
  if (startBtn) {
    startBtn.addEventListener('click', async function () {
      if (uploading) { alert('Загрузка уже выполняется.'); return; }
      if (!files.length) { alert('Выберите изображения для загрузки'); return; }

      // collect common form fields
      const nameEl = document.getElementById('name');
      const name = nameEl ? nameEl.value.trim() : '';
      if (!name) { alert('Поле Название обязательно'); return; }
      const brand = document.getElementById('brand') ? document.getElementById('brand').value.trim() : '';
      const category_id = document.getElementById('category_id') ? document.getElementById('category_id').value : '';
      const season = document.getElementById('season') ? document.getElementById('season').value : '';
      const price = document.getElementById('price') ? document.getElementById('price').value : '';
      const discount = document.getElementById('discount') ? document.getElementById('discount').value : '';
      const is_active = document.getElementById('is_active') ? (document.getElementById('is_active').checked ? '1' : '') : '';
      const sizesSelect = document.getElementById('sizes');
      const sizes = sizesSelect ? Array.from(sizesSelect.selectedOptions).map(o => o.value) : [];

      const commonData = { name, brand, category_id, season, price, discount, is_active };
      if (sizes.length) commonData['sizes'] = sizes;

      // UI init
      const initialTotal = files.length;
      let completedCount = 0;
      let createdTotal = 0;
      let allErrors = [];

      if (progressWrap) progressWrap.style.display = 'block';
      if (progressBar) progressBar.style.width = '0%';
      if (progressText) progressText.textContent = `0%`;
      if (uploadStatus) uploadStatus.textContent = 'Запуск...';

      startBtn.disabled = true;
      if (cancelBtn) cancelBtn.disabled = false;
      uploading = true;
      currentAbortController = new AbortController();

      // process until queue empty or cancelled
      while (files.length > 0 && uploading) {
        // take batch from head
        const batchObjs = files.slice(0, Math.min(BATCH_SIZE, files.length));
        if (batchObjs.length === 0) break;

        if (uploadStatus) uploadStatus.textContent = `Загрузка ${completedCount + 1}–${Math.min(completedCount + batchObjs.length, initialTotal)} из ${initialTotal}...`;

        try {
          // with timeout
          const respPromise = uploadBatch(batchObjs, commonData, currentAbortController.signal);
          const result = await Promise.race([
            respPromise,
            new Promise((_, reject) => setTimeout(() => reject(new Error('Request timed out')), REQUEST_TIMEOUT_MS))
          ]);

          // Determine which files were created by server
          let removedIds = [];

          if (Array.isArray(result.created_objects) && result.created_objects.length) {
            const mapping = result.created_objects.map(o => ({ name: o.original_filename || o.filename || o.name, size: o.filesize || o.size || null })).filter(m => m.name);
            removedIds = removeFilesByNameAndSize(mapping, batchObjs);
          } else if (Array.isArray(result.success) && result.success.length) {
            const mapping = result.success.map(s => (typeof s === 'string' ? s : { name: s.name || s.filename || s.original_filename, size: s.size || s.filesize || null }));
            removedIds = removeFilesByNameAndSize(mapping, batchObjs);
          } else if (typeof result.created === 'number' && result.created === batchObjs.length) {
            const mapping = batchObjs.map(o => ({ name: o.file.name, size: o.file.size }));
            removedIds = removeFilesByNameAndSize(mapping, batchObjs);
          } else {
            // try to infer successes by exclusion if structured errors present
            if (result.errors && Array.isArray(result.errors) && result.errors.length) {
              const errNames = new Set();
              result.errors.forEach(err => {
                if (err && typeof err === 'object') {
                  if (err.filename) errNames.add(err.filename);
                  if (err.name) errNames.add(err.name);
                  if (err.file) errNames.add(err.file);
                }
              });
              const successCandidates = batchObjs.filter(b => !errNames.has(b.file.name)).map(b => ({ name: b.file.name, size: b.file.size }));
              if (successCandidates.length) {
                removedIds = removeFilesByNameAndSize(successCandidates, batchObjs);
              }
            }
          }

          // For remaining files in batch (not removed), increase attempts
          const remainingBatchObjs = batchObjs.filter(b => !removedIds.includes(fileIdFromObj(b)));
          for (const obj of remainingBatchObjs) {
            obj.attempts = (obj.attempts || 0) + 1;
            updateThumbnailAttempts(obj);
            if (obj.attempts >= MAX_RETRIES) {
              // move to failedFiles
              failedFiles.push({ file: obj.file, attempts: obj.attempts, reason: 'max_retries' });
              markThumbnailFailed(obj, 'превышено число попыток');
              // remove from files queue
              const idx = files.findIndex(x => fileIdFromObj(x) === fileIdFromObj(obj));
              if (idx !== -1) files.splice(idx, 1);
              completedCount += 1;
            } else {
              // rotate: move this object to end of queue
              const idx = files.findIndex(x => fileIdFromObj(x) === fileIdFromObj(obj));
              if (idx !== -1) {
                const [moved] = files.splice(idx, 1);
                files.push(moved);
              }
            }
          }

          createdTotal += removedIds.length;
          completedCount += removedIds.length;

          if (result.errors && Array.isArray(result.errors) && result.errors.length) {
            allErrors.push(...result.errors);
          }
        } catch (err) {
          // network / timeout / server error - increment attempts for all batch files and handle retries/failures
          const errMsg = String(err.message || err);
          allErrors.push({ batchSize: batchObjs.length, error: errMsg });

          // increment attempts and either requeue or mark failed
          for (const obj of batchObjs) {
            obj.attempts = (obj.attempts || 0) + 1;
            updateThumbnailAttempts(obj);
            if (obj.attempts >= MAX_RETRIES) {
              failedFiles.push({ file: obj.file, attempts: obj.attempts, reason: errMsg });
              markThumbnailFailed(obj, errMsg);
              // remove from files queue
              const idx = files.findIndex(x => fileIdFromObj(x) === fileIdFromObj(obj));
              if (idx !== -1) files.splice(idx, 1);
              completedCount += 1;
            } else {
              // rotate to end
              const idx = files.findIndex(x => fileIdFromObj(x) === fileIdFromObj(obj));
              if (idx !== -1) {
                const [moved] = files.splice(idx, 1);
                files.push(moved);
              }
            }
          }
        }

        // update progress UI
        const pct = Math.round((completedCount / initialTotal) * 100);
        if (progressBar) progressBar.style.width = pct + '%';
        if (progressText) progressText.textContent = `Обработано ${completedCount} из ${initialTotal} (${pct}%)`;

        // small delay
        await new Promise(r => setTimeout(r, 150));
      } // end while

      // finalize
      uploading = false;
      if (cancelBtn) cancelBtn.disabled = true;
      startBtn.disabled = false;
      currentAbortController = null;

      if (uploadStatus) uploadStatus.textContent = `Готово. Создано: ${createdTotal}. Ошибок: ${allErrors.length}. Неудачных файлов: ${failedFiles.length}`;

      if (allErrors.length) {
        const pre = document.createElement('pre');
        pre.style.whiteSpace = 'pre-wrap';
        pre.textContent = JSON.stringify(allErrors, null, 2);
        if (resultArea) resultArea.appendChild(pre);
      }

      // if queue empty and no failed files => reset form
      if (files.length === 0 && failedFiles.length === 0) {
        resetForm();
      } else {
        // leave remaining files and failed files visible for manual action
        updateFilesCount();
      }
    });
  }

  // cancel handler
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      if (!uploading) return;
      if (currentAbortController) currentAbortController.abort();
      uploading = false;
      if (uploadStatus) uploadStatus.textContent = 'Загрузка отменена.';
      if (progressBar) progressBar.style.width = '0%';
      if (progressText) progressText.textContent = '';
      if (cancelBtn) cancelBtn.disabled = true;
      if (startBtn) startBtn.disabled = false;
      // files remain for retry
    });
  }

  // initial UI
  updateFilesCount();
});