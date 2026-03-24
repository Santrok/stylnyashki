document.addEventListener('click', function (e) {
  const btn = e.target.closest('[data-action="toggle-password"][data-target]');
  if (!btn) return;

  const input = document.querySelector(btn.dataset.target);
  if (!input) return;

  input.type = (input.type === 'password') ? 'text' : 'password';
});