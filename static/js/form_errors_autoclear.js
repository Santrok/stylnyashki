(function () {
  function getInput(el) {
    if (!el) return null;
    return el.closest('.field__input, .f__input');
  }

  function clearFieldError(input) {
    if (!input) return;

    input.removeAttribute('data-has-error');

    // auth form: .field / .field__error
    const authField = input.closest('.field');
    if (authField) {
      authField.querySelectorAll('[data-field-error], .field__error').forEach((el) => el.remove());
      authField.removeAttribute('data-has-error');
      return;
    }

    // account form: .f / .f__error
    const accField = input.closest('.f');
    if (accField) {
      accField.querySelectorAll('.f__error').forEach((el) => el.remove());
      return;
    }
  }

  function clearFormErrorBlock(input) {
    const form = input && input.closest('form');
    if (!form) return;

    // общий блок ошибок формы (если есть атрибут)
    const formErr = form.querySelector('[data-form-error]');
    if (formErr) formErr.remove();

    // на всякий случай: если оставили без data-form-error, но с классом
    const formErr2 = form.querySelector('.form-errors[data-autoclear!="0"]');
    if (formErr2) formErr2.remove();
  }

  document.addEventListener('focusin', function (e) {
    const input = getInput(e.target);
    if (!input) return;
    clearFieldError(input);
    clearFormErrorBlock(input);
  });

  document.addEventListener('input', function (e) {
    const input = getInput(e.target);
    if (!input) return;
    clearFieldError(input);
    clearFormErrorBlock(input);
  });
})();