(() => {
  'use strict';
  // Progressive enhancement. Every section is readable before this runs, and
  // stays readable when the visitor asks for reduced motion or pauses it.
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const motionButton = document.querySelector('.motion-toggle');
  let motionPaused = false;
  const pendingReveals = new Set();
  const motionListeners = [];
  const reveal = element => {
    element.classList.remove('motion-pending');
    element.classList.add('is-in');
    pendingReveals.delete(element);
  };
  const motionEnabled = () => !reducedMotion.matches && !motionPaused;
  const applyMotion = () => {
    const enabled = motionEnabled();
    document.documentElement.dataset.motion = enabled ? 'on' : 'off';
    if (!enabled) pendingReveals.forEach(reveal);
    motionListeners.forEach(listener => listener(enabled));
    if (!motionButton) return;
    motionButton.hidden = false;
    motionButton.disabled = reducedMotion.matches;
    motionButton.setAttribute('aria-pressed', String(!enabled));
    motionButton.setAttribute('aria-label', enabled ? 'Pause decorative motion' : 'Resume decorative motion');
    // The homepage uses an icon-only control. Optional decoration must not
    // prevent the navigation, tabs, dialogs, and form from initializing.
    const label = motionButton.querySelector('.motion-label');
    const icon = motionButton.querySelector('.motion-icon');
    if (label) label.textContent = reducedMotion.matches ? 'Reduced motion' : enabled ? 'Motion on' : 'Motion off';
    if (icon) icon.textContent = enabled ? 'Ⅱ' : '▷';
  };

  // ── Scroll reveals: sections below the fold rise in once, then stay put.
  if ('IntersectionObserver' in window && !reducedMotion.matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { reveal(entry.target); observer.unobserve(entry.target); }
      });
    }, {threshold: 0.08});
    document.querySelectorAll('.split-heading, [data-reveal], .why-card, .engine-layout, .process-layout').forEach(element => {
      if (element.getBoundingClientRect().top < window.innerHeight) { element.classList.add('is-in'); return; }
      element.classList.add('motion-reveal', 'motion-pending');
      pendingReveals.add(element);
      observer.observe(element);
    });
    // Sequences that should only start once they are on screen.
    document.querySelectorAll('[data-engine]').forEach(element => observer.observe(element));
    document.addEventListener('focusin', event => {
      const pending = event.target.closest('.motion-pending');
      if (pending) { reveal(pending); observer.unobserve(pending); }
    });
  } else {
    document.querySelectorAll('[data-engine], [data-reveal]').forEach(element => element.classList.add('is-in'));
  }

  // ── The run panel: one Sneferu run, played as five scenes.
  const run = document.querySelector('[data-run]');
  if (run) {
    const scenes = [...run.querySelectorAll('.run-scene')];
    const rail = [...run.querySelectorAll('.run-rail li')];
    const state = run.querySelector('[data-run-state]');
    const status = run.querySelector('[data-run-status]');
    const typed = run.querySelector('[data-run-type]');
    const replay = run.querySelector('[data-run-replay]');
    const labels = ['Request', 'Propose', 'Challenge', 'Prove', 'Finished'];
    // Half-speed playback gives each scene twice as much reading time.
    const durations = [6000, 4800, 6800, 6000, 5200];
    const request = typed ? typed.textContent : '';
    let index = -1;
    let timer = 0;
    let typing = 0;
    let playing = false;
    let visible = true;
    const show = position => {
      scenes.forEach((scene, i) => scene.classList.toggle('is-active', i === position));
      rail.forEach((item, i) => {
        item.classList.toggle('is-active', i === position);
        item.classList.toggle('is-done', i < position);
      });
      if (state) state.textContent = labels[position];
      if (status) status.textContent = scenes[position].dataset.status || '';
      run.style.setProperty('--run-speed', `${durations[position]}ms`);
      run.style.setProperty('--run-progress', `${((position + 1) / scenes.length) * 100}%`);
    };
    const typeRequest = () => {
      if (!typed) return;
      window.clearInterval(typing);
      let count = 0;
      typed.textContent = '';
      typing = window.setInterval(() => {
        count += 1;
        typed.textContent = request.slice(0, count);
        if (count >= request.length) window.clearInterval(typing);
      }, 40);
    };
    const step = () => {
      index = (index + 1) % scenes.length;
      show(index);
      if (index === 0) typeRequest();
      timer = window.setTimeout(step, durations[index]);
    };
    const stop = () => {
      playing = false;
      window.clearTimeout(timer);
      window.clearInterval(typing);
    };
    const settle = () => {
      // Motion off: every scene is laid out in sequence by CSS; show the final state.
      stop();
      if (typed) typed.textContent = request;
      scenes.forEach(scene => scene.classList.remove('is-active'));
      rail.forEach(item => { item.classList.remove('is-active'); item.classList.add('is-done'); });
      if (state) state.textContent = labels[labels.length - 1];
      run.style.removeProperty('--run-progress');
      run.classList.add('is-static');
    };
    const play = () => {
      if (playing || !motionEnabled() || !visible) return;
      run.classList.remove('is-static');
      playing = true;
      index = -1;
      step();
    };
    const restart = () => { stop(); play(); };
    motionListeners.push(enabled => { if (enabled) restart(); else settle(); });
    replay?.addEventListener('click', restart);
    document.addEventListener('visibilitychange', () => {
      if (!motionEnabled()) return;
      if (document.hidden) stop(); else play();
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(entries => {
        entries.forEach(entry => {
          visible = entry.isIntersecting;
          if (!motionEnabled()) return;
          if (visible) play(); else stop();
        });
      }, {threshold: 0.2}).observe(run);
    }
  }

  // ── Ticker: duplicate the track once for a seamless loop; pace by width.
  document.querySelectorAll('[data-ticker]').forEach(ticker => {
    const track = ticker.querySelector('.ticker-track');
    if (!track) return;
    const items = [...track.children];
    items.forEach(item => {
      const clone = item.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      clone.classList.add('is-clone');
      track.appendChild(clone);
    });
    const pace = () => {
      const width = track.scrollWidth / 2;
      if (width) ticker.style.setProperty('--ticker-duration', `${Math.max(30, Math.round(width / 55))}s`);
    };
    pace();
    window.addEventListener('resize', pace);
  });

  applyMotion();
  motionButton?.addEventListener('click', () => { motionPaused = !motionPaused; applyMotion(); });
  reducedMotion.addEventListener('change', applyMotion);

  // ── Navigation.
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

  // ── Tabs.
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

  // ── Example dialogs.
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

  // ── Contact form: stays on the page, reports honestly.
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
