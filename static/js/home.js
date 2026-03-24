(function () {
  const overlay = document.getElementById("mobileMenu");
  const openBtn = document.getElementById("menuOpenBtn");
  const closeBtn = document.getElementById("menuCloseBtn");

  function openMenu() {
    if (!overlay) return;
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    if (openBtn) openBtn.setAttribute("aria-expanded", "true");
    document.body.classList.add("menu-open");
  }

  function closeMenu() {
    if (!overlay) return;
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    if (openBtn) openBtn.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-open");
  }

  if (openBtn) openBtn.addEventListener("click", openMenu);
  if (closeBtn) closeBtn.addEventListener("click", closeMenu);

  if (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeMenu();
    });

    const links = overlay.querySelectorAll("[data-close-menu]");
    links.forEach((a) => a.addEventListener("click", closeMenu));
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeMenu();
  });
})();