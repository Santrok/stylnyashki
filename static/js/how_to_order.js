// how_to_order.js — TOC scrollspy + smooth anchors + PDF generation
document.addEventListener('DOMContentLoaded', function () {
  const tocLinks = Array.from(document.querySelectorAll('.howto-toc a'));
  const sections = tocLinks.map(a => document.getElementById(a.getAttribute('href').slice(1)));
  const downloadBtn = document.getElementById('downloadPdfBtn');
  const content = document.getElementById('howtoContent');

  function onScroll() {
    const scrollPos = window.scrollY + (window.innerHeight * 0.15);
    let currentIndex = -1;
    for (let i = 0; i < sections.length; i++) {
      const s = sections[i];
      if (!s) continue;
      const top = s.getBoundingClientRect().top + window.scrollY;
      if (scrollPos >= top) currentIndex = i;
    }
    tocLinks.forEach((a, idx) => {
      if (idx === currentIndex) a.classList.add('active');
      else a.classList.remove('active');
    });
  }

  let scrollTimer;
  window.addEventListener('scroll', function () {
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(onScroll, 50);
  });
  onScroll();

  tocLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const id = this.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (!el) return;
      const headerOffset = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-height')) || 64;
      const top = el.getBoundingClientRect().top + window.scrollY - headerOffset - 12;
      window.scrollTo({ top, behavior: 'smooth' });
      tocLinks.forEach(a => a.classList.remove('active'));
      this.classList.add('active');
    });
  });

  if (downloadBtn) {
    downloadBtn.addEventListener('click', function () {
      const clone = content.cloneNode(true);
      clone.querySelectorAll('a').forEach(a => a.removeAttribute('href'));
      const opt = {
        margin: [15, 10, 15, 10],
        filename: `how-to-order-${new Date().toISOString().slice(0,10)}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['css', 'legacy'] }
      };
      const original = downloadBtn.textContent;
      downloadBtn.textContent = 'Генерируется PDF…';
      downloadBtn.disabled = true;
      const wrapper = document.createElement('div');
      wrapper.style.padding = '10mm';
      wrapper.style.background = '#fff';
      wrapper.appendChild(clone);
      html2pdf().set(opt).from(wrapper).save().then(() => {
        downloadBtn.textContent = original; downloadBtn.disabled = false;
      }).catch(err => {
        console.error(err);
        downloadBtn.textContent = original; downloadBtn.disabled = false;
        alert('Ошибка при генерации PDF');
      });
    });
  }
});