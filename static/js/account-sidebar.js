// static/js/account-sidebar.js
(function () {
  'use strict';

  function getScrollbarWidth() {
    return window.innerWidth - document.documentElement.clientWidth;
  }

  function getFocusableElements(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll(
      'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])'
    )).filter(function (el) {
      return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var openBtn = document.getElementById('accountNavOpenBtn');
    var closeBtn = document.getElementById('accountNavCloseBtn');
    var overlay = document.getElementById('accountSidebarOverlay');

    // sidebar may be identified by multiple ids / selectors depending on template
    var sidebar = document.getElementById('accountSidebar') || document.getElementById('desktopSidebar') || document.querySelector('.account-sidebar');

    if (!openBtn || !sidebar || !overlay) {
      // graceful fallback: nothing to do
      return;
    }

    var body = document.body;
    var previouslyFocused = null;
    var scrollbarCompensated = false;

    function enableScrollCompensation() {
      var sbw = getScrollbarWidth();
      if (sbw > 0) {
        body.style.paddingRight = sbw + 'px';
        scrollbarCompensated = true;
      }
    }
    function disableScrollCompensation() {
      if (scrollbarCompensated) {
        body.style.paddingRight = '';
        scrollbarCompensated = false;
      }
    }

    function trapFocus(e) {
      if (e.key !== 'Tab') return;
      var focusable = getFocusableElements(sidebar);
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first || document.activeElement === sidebar) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    function onKeyDown(e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        e.preventDefault();
        closeSidebar(openBtn);
        return;
      }
      trapFocus(e);
    }

    function openSidebar() {
      previouslyFocused = document.activeElement;

      sidebar.classList.add('is-open');
      overlay.classList.add('is-visible');

      sidebar.setAttribute('aria-hidden', 'false');
      openBtn.setAttribute('aria-expanded', 'true');
      overlay.setAttribute('aria-hidden', 'false');

      if (closeBtn) closeBtn.style.display = '';

      body.classList.add('no-scroll');
      enableScrollCompensation();

      // ensure sidebar on top of overlay by z-index (defensive)
      sidebar.style.zIndex = 1020;
      overlay.style.zIndex = 1010;

      // fallback inline transform in case CSS fails
      sidebar.style.transform = 'translateX(0)';

      // focus first focusable after short delay
      setTimeout(function () {
        var focusable = getFocusableElements(sidebar);
        if (focusable.length) focusable[0].focus();
      }, 160);

      document.addEventListener('keydown', onKeyDown);
    }

    function closeSidebar(restoreFocusTo) {
      // remove classes to trigger CSS transition
      sidebar.classList.remove('is-open');
      overlay.classList.remove('is-visible');

      // set aria and expanded
      overlay.setAttribute('aria-hidden', 'true');
      openBtn.setAttribute('aria-expanded', 'false');

      // Use transitionend to cleanup. If no transition, fallback timeout.
      var cleanup = function () {
        sidebar.setAttribute('aria-hidden', 'true');
        body.classList.remove('no-scroll');
        disableScrollCompensation();
        if (closeBtn) closeBtn.style.display = 'none';
        // remove inline fallback transform
        sidebar.style.transform = '';
        // restore focus
        var target = restoreFocusTo || previouslyFocused || openBtn;
        if (target && typeof target.focus === 'function') target.focus();
      };

      // try listen transitionend; else fallback after 300ms
      var hasTransition = window.getComputedStyle(sidebar).transitionDuration !== '0s';
      if (hasTransition) {
        var called = false;
        var onEnd = function () { if (!called) { called = true; cleanup(); } };
        sidebar.addEventListener('transitionend', onEnd, { once: true });
        // safety timeout
        setTimeout(function () { onEnd(); }, 420);
      } else {
        setTimeout(cleanup, 180);
      }

      document.removeEventListener('keydown', onKeyDown);
    }

    openBtn.addEventListener('click', function (e) {
      e.preventDefault();
      openSidebar();
    });

    overlay.addEventListener('click', function (e) {
      closeSidebar(openBtn);
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        closeSidebar(openBtn);
      });
      closeBtn.style.display = 'none';
    }

    // media change handler: if going to desktop, ensure menu visible and state cleaned
    var mql = window.matchMedia('(min-width: 1024px)');
    function onMediaChange(e) {
      if (e.matches) {
        sidebar.classList.remove('is-open');
        overlay.classList.remove('is-visible');
        sidebar.setAttribute('aria-hidden', 'false');
        overlay.setAttribute('aria-hidden', 'true');
        if (closeBtn) closeBtn.style.display = 'none';
        body.classList.remove('no-scroll');
        disableScrollCompensation();
        document.removeEventListener('keydown', onKeyDown);
      } else {
        sidebar.setAttribute('aria-hidden', 'true');
        overlay.setAttribute('aria-hidden', 'true');
        if (closeBtn) closeBtn.style.display = 'none';
      }
    }
    onMediaChange(mql);
    if (mql.addEventListener) {
      mql.addEventListener('change', onMediaChange);
    } else {
      mql.addListener(onMediaChange);
    }
  });
})();