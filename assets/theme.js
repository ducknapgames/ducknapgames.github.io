/* Follow the system until the visitor explicitly chooses a theme. */
(() => {
  const key = 'ducknap-theme';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let choice = null;
  try {
    const saved = localStorage.getItem(key);
    if (saved === 'light' || saved === 'dark') choice = saved;
  } catch (_) { /* The switch still works when storage is unavailable. */ }

  function apply() {
    const dark = choice ? choice === 'dark' : system.matches;
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.querySelectorAll('.theme-toggle').forEach(button => {
      button.setAttribute('aria-checked', String(dark));
      button.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
    });
    document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
      meta.content = dark ? '#1b1920' : '#faf8f3';
    });
  }
  apply();
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.querySelectorAll('.theme-toggle').forEach(button => {
      button.addEventListener('click', () => {
        choice = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(key, choice); } catch (_) { /* Optional persistence. */ }
        apply();
      });
    });
  });
  system.addEventListener('change', () => { if (!choice) apply(); });
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    choice = event.newValue === 'light' || event.newValue === 'dark' ? event.newValue : null;
    apply();
  });
})();
