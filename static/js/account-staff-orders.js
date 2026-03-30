// static/js/account-staff-orders.js
document.addEventListener('DOMContentLoaded', function () {
  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  document.querySelectorAll('.order-status-select').forEach(function (sel) {
    sel.addEventListener('change', async function () {
      const orderId = this.dataset.orderId;
      const newStatus = this.value;
      const selectEl = this;
      selectEl.disabled = true;
      try {
        const resp = await fetch(`/account/staff/orders/${orderId}/status/`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: new URLSearchParams({ status: newStatus }),
        });
        if (!resp.ok) {
          const text = await resp.text();
          alert('Ошибка при обновлении статуса: ' + text);
        } else {
          const data = await resp.json();
          // Optionally update badge text & class on the card
          const tr = selectEl.closest('.order-card');
          if (tr) {
            const badge = tr.querySelector('.order-badge');
            if (badge) {
              // update label text (display value)
              const opt = selectEl.options[selectEl.selectedIndex];
              badge.textContent = opt.text;
              // update class (we used uppercase in CSS)
              badge.className = 'order-badge ' + newStatus.toUpperCase();
            }
          }
          console.log('Status updated', data);
        }
      } catch (err) {
        alert('Network error: ' + err.message);
      } finally {
        selectEl.disabled = false;
      }
    });
  });
});