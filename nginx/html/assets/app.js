(function() {
  const root = document.documentElement;
  const STORAGE_KEY = 'ars-theme';
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'dark' || saved === 'light') {
    root.setAttribute('data-theme', saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    root.setAttribute('data-theme', 'dark');
  }

  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  }

  // Smooth scroll for nav links
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const hash = a.getAttribute('href');
      if (!hash || hash === '#') return;
      const el = document.querySelector(hash);
      if (!el) return;
      e.preventDefault();
      const y = el.getBoundingClientRect().top + window.pageYOffset - 64;
      window.scrollTo({ top: y, behavior: 'smooth' });
      history.pushState(null, '', hash);
    });
  });

  // Back to top
  const backToTop = document.getElementById('backToTop');
  const onScroll = () => {
    if (!backToTop) return;
    if (window.scrollY > 360) backToTop.classList.add('show');
    else backToTop.classList.remove('show');
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  if (backToTop) {
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  // Active nav link highlight
  const sections = ['#features','#architecture','#quickstart','#api','#contact']
    .map(id => document.querySelector(id))
    .filter(Boolean);
  const links = Array.from(document.querySelectorAll('.menu a'));
  const spy = () => {
    const y = window.scrollY + 72;
    for (let i = sections.length - 1; i >= 0; i--) {
      const s = sections[i];
      if (s.offsetTop <= y) {
        const id = '#' + s.id;
        links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === id));
        break;
      }
    }
  };
  window.addEventListener('scroll', spy, { passive: true });
  spy();

  // Footer year
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
})(); 