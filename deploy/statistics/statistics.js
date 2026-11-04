/* Format display values locally; this dashboard sends no analytics events. */
(() => {
  const lang = document.documentElement.lang || 'en';
  const number = new Intl.NumberFormat(lang);
  const date = new Intl.DateTimeFormat(lang, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
  document.querySelectorAll('[data-count]').forEach(node => { node.textContent = number.format(BigInt(node.dataset.count)); });
  document.querySelectorAll('time[datetime]').forEach(node => {
    const value = new Date(node.dateTime+'T12:00:00Z');
    if (!Number.isNaN(value.getTime())) node.textContent = date.format(value);
  });
})();
