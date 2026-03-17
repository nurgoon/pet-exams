(() => {
  const applyLight = () => {
    try {
      localStorage.setItem('jazzmin-theme-mode', 'light');
      localStorage.setItem('jazzmin-theme', 'default');
    } catch (error) {
      // Ignore storage errors (private mode / disabled storage)
    }
    document.documentElement.setAttribute('data-bs-theme', 'light');
  };

  applyLight();

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
        if (document.documentElement.getAttribute('data-bs-theme') !== 'light') {
          applyLight();
        }
      }
    }
  });

  observer.observe(document.documentElement, { attributes: true });
})();
