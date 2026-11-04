/* Keep navigation available on an upward scroll without covering the games while reading. */
(() => {
  const header = document.querySelector('.header');
  if (!header) return;
  const space = document.createElement('div');
  space.className = 'header-space';
  space.style.height = `${header.getBoundingClientRect().height}px`;
  header.before(space);
  space.append(header);
  // Keep the scrim outside the transformed header, so it covers the whole page.
  const backdrop = header.querySelector('.mobile-menu-backdrop');
  if (backdrop) document.body.append(backdrop);
  header.classList.add('scroll-header');

  let last = Math.max(0, window.scrollY);
  let direction = 0;
  let distance = 0;
  let pending = false;
  const reveal = () => header.classList.remove('header-away');
  const update = () => {
    pending = false;
    const maximum = Math.max(0, document.documentElement.scrollHeight - innerHeight);
    const y = Math.max(0, Math.min(window.scrollY, maximum));
    const delta = y - last;
    last = y;
    const nearTop = y <= space.offsetHeight;
    header.classList.toggle('header-floating', !nearTop);
    const panelOpen = header.querySelector('.preferences-panel:not([hidden])');
    if (nearTop || panelOpen || document.querySelector('.language-dialog[open]') || header.querySelector(':focus-visible')) {
      reveal();
      distance = 0;
      return;
    }
    if (Math.abs(delta) < 1) return;
    const next = Math.sign(delta);
    if (next !== direction) { direction = next; distance = 0; }
    distance += Math.abs(delta);
    if (distance >= (next > 0 ? 30 : 12)) {
      header.classList.toggle('header-away', next > 0);
      distance = 0;
    }
  };
  const schedule = () => {
    if (!pending) { pending = true; requestAnimationFrame(update); }
  };
  window.addEventListener('scroll', schedule, { passive: true });
  header.addEventListener('focusin', reveal);
  window.addEventListener('resize', () => {
    // Measure its original responsive height, rather than the compact floating state.
    const floating = header.classList.contains('header-floating');
    const away = header.classList.contains('header-away');
    header.classList.remove('scroll-header', 'header-floating', 'header-away');
    space.style.height = `${header.getBoundingClientRect().height}px`;
    header.classList.add('scroll-header');
    header.classList.toggle('header-floating', floating);
    header.classList.toggle('header-away', away);
    schedule();
  });
  window.addEventListener('pageshow', schedule);
  schedule();
})();
