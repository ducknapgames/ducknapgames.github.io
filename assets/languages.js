/* Language URLs are authoritative; the picker keeps the current page and anchor. */
(() => {
  const dialog = document.getElementById('language-dialog');
  const toggle = document.querySelector('.language-toggle');
  if (!dialog || !toggle) return;
  const preferences = document.querySelector('.header-preferences');
  const trigger = preferences.querySelector('.preferences-trigger');
  const panel = preferences.querySelector('.preferences-panel');
  const header = preferences.closest('.header');
  const navigation = preferences.closest('.nav');
  const mobile = window.matchMedia('(max-width: 600px)');
  const desktopLabel = trigger.getAttribute('aria-label');
  const mobileLinks = document.createElement('nav');
  mobileLinks.className = 'mobile-menu-links';
  mobileLinks.setAttribute('aria-label', navigation.getAttribute('aria-label'));
  [...navigation.children].filter(node => node.tagName === 'A').forEach(link => {
    const item = link.cloneNode(true);
    const arrow = document.createElement('span');
    arrow.textContent = '→';
    arrow.setAttribute('aria-hidden', 'true');
    item.append(arrow);
    item.addEventListener('click', () => closePreferences());
    mobileLinks.append(item);
  });
  panel.prepend(mobileLinks);
  trigger.insertAdjacentHTML('beforeend', '<svg class="mobile-menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><path class="menu-bars" d="M4 7h16M4 12h16M4 17h16"/><path class="menu-cross" d="m6 6 12 12M18 6 6 18"/></svg>');
  const backdrop = document.createElement('div');
  backdrop.className = 'mobile-menu-backdrop';
  backdrop.hidden = true;
  backdrop.setAttribute('aria-hidden', 'true');
  header.append(backdrop);
  const background = [...document.querySelectorAll('main, body > footer')];
  const updateMobile = () => {
    const expanded = mobile.matches && !panel.hidden;
    header.classList.toggle('mobile-menu-open', expanded);
    backdrop.hidden = !expanded;
    background.forEach(element => { element.inert = expanded; });
    trigger.setAttribute('aria-label', mobile.matches ? navigation.getAttribute('aria-label') : desktopLabel);
  };
  const closePreferences = (restoreFocus = false) => {
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    updateMobile();
    if (restoreFocus) trigger.focus({ preventScroll: true });
  };
  trigger.addEventListener('click', () => {
    const opening = panel.hidden;
    panel.hidden = !opening;
    trigger.setAttribute('aria-expanded', String(opening));
    updateMobile();
    if (opening) (mobile.matches ? mobileLinks.querySelector('a') : toggle).focus({ preventScroll: true });
  });
  backdrop.addEventListener('click', () => closePreferences(true));
  mobile.addEventListener('change', () => closePreferences());
  updateMobile();
  document.addEventListener('click', event => {
    if (!preferences.contains(event.target)) closePreferences();
  });
  preferences.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) {
      event.preventDefault();
      closePreferences(true);
    }
    if (event.key === 'Tab' && mobile.matches && !panel.hidden) {
      const items = [trigger, ...mobileLinks.querySelectorAll('a'), toggle, panel.querySelector('.theme-toggle')];
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
  });
  preferences.addEventListener('focusout', event => {
    if (!preferences.contains(event.relatedTarget)) closePreferences();
  });
  const options = [...dialog.querySelectorAll('.language-option')];
  let copy = {};
  try { copy = JSON.parse(document.getElementById('site-translations')?.textContent || '{}'); } catch (_) {}
  const recommended = (navigator.languages || [navigator.language]).map(value => {
    const lc = value.toLowerCase();
    if (/^zh(-hant|-tw|-hk|-mo)/.test(lc)) return 'zh-Hant';
    if (lc.startsWith('zh')) return null;
    if (lc.startsWith('pt')) return 'pt-BR';
    return lc.split('-')[0];
  }).find(value => options.some(option => option.dataset.language === value));
  if (recommended) {
    const option = options.find(item => item.dataset.language === recommended);
    const note = document.createElement('span');
    note.className = 'language-recommendation';
    note.textContent = copy['Based on your browser'] || 'Based on your browser';
    option.querySelector('.language-copy').append(note);
  }
  // A fragment can remain in the address bar after the visitor scrolls away.
  // Carry it to another language only while its section is still in view.
  const visibleFragment = () => {
    if (!location.hash) return '';
    let anchor;
    try { anchor = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) { return ''; }
    if (!anchor) return '';
    const top = anchor.getBoundingClientRect().top;
    return top >= -96 && top <= Math.max(96, innerHeight / 3) ? location.hash : '';
  };
  toggle.addEventListener('click', () => {
    closePreferences();
    const fragment = visibleFragment();
    options.forEach(option => {
      const target = new URL(option.href);
      target.hash = fragment;
      option.href = target.href;
    });
    dialog.showModal();
    dialog.querySelector('.language-close').focus({ preventScroll: true });
  });
  const close = () => { dialog.close(); trigger.focus({ preventScroll: true }); };
  dialog.querySelector('.language-close').addEventListener('click', close);
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close();
  });
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  // The theme script runs in the head. Keep its changing accessible title translated.
  const theme = document.querySelector('.theme-toggle');
  if (theme) {
    const update = () => {
      const key = document.documentElement.dataset.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
      theme.title = copy[key] || key;
    };
    update();
    new MutationObserver(update).observe(theme, { attributes: true, attributeFilter: ['aria-checked'] });
  }
})();
