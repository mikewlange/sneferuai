/* Progressive enhancement. The story and pricing-free pitch are plain HTML. */
(() => {
  'use strict';
  const dialog = document.querySelector('#demo');
  let opener;
  document.querySelectorAll('[data-demo]').forEach(link => {
    link.addEventListener('click', event => {
      if (!dialog || typeof dialog.showModal !== 'function') return;
      event.preventDefault();
      opener = link;
      dialog.showModal();
    });
  });
  if (dialog) {
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => opener?.focus());
    const form = dialog.querySelector('form');
    const status = dialog.querySelector('[role="status"]');
    const submit = form.querySelector('[type="submit"]');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (submit.disabled || !form.reportValidity()) return;
      submit.disabled = true;
      submit.textContent = 'Sending…';
      status.textContent = '';
      status.classList.remove('error');
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      try {
        const result = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' }, credentials: 'omit', signal: controller.signal });
        if (!result.ok) throw new Error('Request not accepted');
        form.hidden = true;
        status.textContent = 'Thanks. Your demo request is on its way to Michael. He’ll be in touch.';
      } catch (_) {
        status.classList.add('error');
        status.textContent = 'That didn’t go through. Please try again, or email mike@sneferu.ai.';
      } finally {
        clearTimeout(timeout);
        submit.disabled = false;
        submit.textContent = 'Request a demo ↗';
      }
    });
  }
  const chapters = [...document.querySelectorAll('[data-chapter]')];
  if (chapters.length && 'IntersectionObserver' in window) {
    const label = document.querySelector('[data-stage-name]');
    const names = ['The idea', 'The build', 'Your software'];
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const stage = Number(entry.target.dataset.chapter);
        document.querySelectorAll('[data-art-layer]').forEach(layer => layer.classList.toggle('active', Number(layer.dataset.artLayer) <= stage));
        if (label) label.textContent = names[stage];
      }
    }, { rootMargin: '-25% 0px -35% 0px', threshold: 0 });
    chapters.forEach(chapter => observer.observe(chapter));
  }
  const progress = document.querySelector('.progress');
  if (progress) {
    let queued = false;
    const update = () => {
      const range = document.documentElement.scrollHeight - innerHeight;
      progress.style.transform = `scaleX(${range > 0 ? Math.min(1, Math.max(0, scrollY / range)) : 0})`;
      queued = false;
    };
    addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(update); } }, { passive: true });
    addEventListener('resize', update);
    update();
  }
})();
