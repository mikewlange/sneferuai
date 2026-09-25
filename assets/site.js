(() => {
  'use strict';
  // Progressive enhancement: content is visible before JS, and stays visible
  // when reduced motion is requested or the visitor pauses the presentation.
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const motionButton = document.querySelector('.motion-toggle');
  let motionPaused = false;
  const pendingReveals = new Set();
  const reveal = element => {
    element.classList.remove('motion-pending');
    pendingReveals.delete(element);
  };
  const applyMotion = () => {
    const enabled = !reducedMotion.matches && !motionPaused;
    document.documentElement.dataset.motion = enabled ? 'on' : 'off';
    if (!enabled) pendingReveals.forEach(reveal);
    if (!motionButton) return;
    motionButton.hidden = false;
    motionButton.disabled = reducedMotion.matches;
    motionButton.setAttribute('aria-pressed', String(!enabled));
    motionButton.setAttribute('aria-label', enabled ? 'Pause decorative motion' : 'Resume decorative motion');
    motionButton.querySelector('.motion-label').textContent = reducedMotion.matches ? 'Reduced motion' : enabled ? 'Motion on' : 'Motion off';
    motionButton.querySelector('.motion-icon').textContent = enabled ? 'Ⅱ' : '▷';
  };
  applyMotion();
  motionButton?.addEventListener('click', () => { motionPaused = !motionPaused; applyMotion(); });
  reducedMotion.addEventListener('change', applyMotion);
  if ('IntersectionObserver' in window && !reducedMotion.matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { reveal(entry.target); observer.unobserve(entry.target); }
      });
    }, {threshold: 0.08});
    document.querySelectorAll('.split-heading, .featured-build, .product-principles>div, .engine-layout, .sod-feature-layout, .founder-quote').forEach(element => {
      if (element.getBoundingClientRect().top < window.innerHeight) return;
      element.classList.add('motion-reveal', 'motion-pending');
      pendingReveals.add(element);
      observer.observe(element);
    });
    document.addEventListener('focusin', event => {
      const pending = event.target.closest('.motion-pending');
      if (pending) { reveal(pending); observer.unobserve(pending); }
    });
  }
  const menuButton = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#site-nav');
  const closeMenu = () => {
    if (!menuButton || !navigation) return;
    menuButton.setAttribute('aria-expanded', 'false');
    navigation.classList.remove('is-open');
  };
  menuButton?.addEventListener('click', () => {
    const expanded = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!expanded));
    navigation?.classList.toggle('is-open', !expanded);
  });
  navigation?.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menuButton.focus();
    }
  });
  const desktop = window.matchMedia('(min-width: 821px)');
  desktop.addEventListener('change', event => { if (event.matches) closeMenu(); });

  document.querySelectorAll('[role="tablist"]').forEach(list => {
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const activate = tab => {
      tabs.forEach(item => {
        const selected = item === tab;
        item.setAttribute('aria-selected', String(selected));
        item.tabIndex = selected ? 0 : -1;
        const panel = document.getElementById(item.getAttribute('aria-controls'));
        if (panel) {
          panel.hidden = !selected;
          if (!selected) panel.querySelectorAll('video').forEach(video => video.pause());
        }
      });
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activate(tab));
      tab.addEventListener('keydown', event => {
        const forward = event.key === 'ArrowDown' || event.key === 'ArrowRight';
        const backward = event.key === 'ArrowUp' || event.key === 'ArrowLeft';
        if (!forward && !backward && event.key !== 'Home' && event.key !== 'End') return;
        event.preventDefault();
        let target = index;
        if (forward) target = (index + 1) % tabs.length;
        if (backward) target = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') target = 0;
        if (event.key === 'End') target = tabs.length - 1;
        activate(tabs[target]);
        tabs[target].focus();
      });
    });
  });

  const dialogOpeners = new WeakMap();
  document.querySelectorAll('[data-dialog]').forEach(opener => {
    opener.addEventListener('click', () => {
      const dialog = document.getElementById(opener.dataset.dialog);
      if (!(dialog instanceof HTMLDialogElement)) return;
      dialogOpeners.set(dialog, opener);
      dialog.showModal();
      dialog.scrollTop = 0;
      document.body.classList.add('modal-open');
    });
  });
  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.querySelector('.dialog-close')?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
      dialog.querySelectorAll('video').forEach(video => video.pause());
      document.body.classList.remove('modal-open');
      dialogOpeners.get(dialog)?.focus();
    });
  });

  document.querySelectorAll('form[data-onsite-submit]').forEach(form => {
    const status = document.getElementById(`${form.id}-status`);
    const submit = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity() || submit.disabled) return;
      if (form.elements.namedItem('_gotcha')?.value) return;
      const original = submit.innerHTML;
      submit.disabled = true;
      submit.textContent = 'Sending…';
      status.hidden = false;
      status.textContent = 'Sending your message…';
      let timeout;
      try {
        const controller = new AbortController();
        timeout = window.setTimeout(() => controller.abort(), 20000);
        const response = await fetch(form.action, {method: 'POST', body: new FormData(form), headers: {Accept: 'application/json'}, signal: controller.signal});
        if (!response.ok) throw new Error('submission failed');
        status.textContent = 'Thank you. Your message is with Sneferu. We’ll be in touch.';
        form.reset();
      } catch {
        status.textContent = 'We couldn’t confirm delivery. Your message is still here. Please try again, or email mike@sneferu.ai.';
      } finally {
        window.clearTimeout(timeout);
        submit.disabled = false;
        submit.innerHTML = original;
        status.focus();
      }
    });
  });
})();
