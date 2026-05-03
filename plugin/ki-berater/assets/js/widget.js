(function () {
  'use strict';

  const cfg = window.KIB_WIDGET || {};
  const i18n = cfg.i18n || {};
  const STORAGE_VISITOR = 'kib_visitor_id';
  const STORAGE_CONVO = 'kib_conversation_id';

  if (!cfg.backendUrl || !cfg.apiKey) {
    return;
  }

  const root = document.getElementById('kib-widget-root');
  if (!root) {
    return;
  }

  // ---- helpers ----
  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getOrCreate(key, factory) {
    let v = '';
    try { v = localStorage.getItem(key) || ''; } catch (e) {}
    if (!v) {
      v = factory();
      try { localStorage.setItem(key, v); } catch (e) {}
    }
    return v;
  }

  function clearConvo() {
    try { localStorage.removeItem(STORAGE_CONVO); } catch (e) {}
    document.cookie = 'kib_conv=; path=/; max-age=0; SameSite=Lax';
  }

  function setConvoCookie(id) {
    if (!id) return;
    document.cookie = 'kib_conv=' + encodeURIComponent(id) +
      '; path=/; max-age=2592000; SameSite=Lax';
  }

  function persistConvoId(id) {
    if (!id) return;
    try { localStorage.setItem(STORAGE_CONVO, id); } catch (e) {}
    setConvoCookie(id);
  }

  function el(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text) e.textContent = text;
    return e;
  }

  function supportsStreaming() {
    try {
      return typeof TextDecoder !== 'undefined'
        && typeof ReadableStream !== 'undefined'
        && 'getReader' in ReadableStream.prototype;
    } catch (e) {
      return false;
    }
  }

  // ---- branding (per-shop, from KIB_WIDGET) ----
  const brandName = (cfg.brandName || 'WoCom').slice(0, 32);
  const brandInitial = brandName.charAt(0).toUpperCase() || 'W';
  const greeting = cfg.greeting || (i18n.greeting || 'Looking for something specific? Happy to help.');
  const primaryColor = (typeof cfg.primaryColor === 'string'
    && /^#[0-9a-fA-F]{6}$/.test(cfg.primaryColor))
    ? cfg.primaryColor : '#7c3aed';
  // Slightly darker for hover — naive shade; good enough since input is locked to 6-char hex.
  const primaryHover = shadeHex(primaryColor, -12);

  function shadeHex(hex, percent) {
    const num = parseInt(hex.slice(1), 16);
    const amt = Math.round(2.55 * percent);
    let r = (num >> 16) + amt;
    let g = ((num >> 8) & 0xff) + amt;
    let b = (num & 0xff) + amt;
    r = Math.max(0, Math.min(255, r));
    g = Math.max(0, Math.min(255, g));
    b = Math.max(0, Math.min(255, b));
    return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
  }

  // ---- state ----
  const visitorId = getOrCreate(STORAGE_VISITOR, uuid);

  // ---- markup ----
  const widget = el('div', 'kib-widget');
  widget.style.setProperty('--kib-primary', primaryColor);
  widget.style.setProperty('--kib-primary-hover', primaryHover);

  const bubble = el('button', 'kib-widget__bubble');
  bubble.setAttribute('aria-label', i18n.open || 'Chat oeffnen');
  bubble.innerHTML =
    '<svg viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M12 3C6.48 3 2 6.92 2 11.5c0 2.04.91 3.92 2.43 5.36L3 21l4.45-1.4C8.78 20.5 10.34 21 12 21c5.52 0 10-3.92 10-9.5S17.52 3 12 3z"/>' +
    '</svg>';

  const panel = el('div', 'kib-widget__panel');

  // Header: Avatar + Brand-Name + "Online · …"
  const header = el('div', 'kib-widget__header');
  const avatar = el('div', 'kib-widget__avatar');
  avatar.textContent = brandInitial;
  header.appendChild(avatar);

  const brand = el('div', 'kib-widget__brand');
  brand.appendChild(el('div', 'kib-widget__brand-name', brandName));
  const status = el('div', 'kib-widget__brand-status');
  status.appendChild(el('span', 'kib-widget__online-dot'));
  status.appendChild(document.createTextNode(' '));
  status.appendChild(document.createTextNode(i18n.status || 'Online · antwortet sofort'));
  brand.appendChild(status);
  header.appendChild(brand);

  const closeBtn = el('button', 'kib-widget__close');
  closeBtn.setAttribute('aria-label', i18n.close || 'Schliessen');
  closeBtn.textContent = '×';
  header.appendChild(closeBtn);
  panel.appendChild(header);

  const messages = el('div', 'kib-widget__messages');
  panel.appendChild(messages);

  const form = el('form', 'kib-widget__form');
  const input = el('input', 'kib-widget__input');
  input.type = 'text';
  input.placeholder = i18n.placeholder || 'Antworten…';
  input.required = true;
  input.maxLength = 4000;
  form.appendChild(input);

  const sendBtn = el('button', 'kib-widget__send');
  sendBtn.type = 'submit';
  sendBtn.setAttribute('aria-label', i18n.send || 'Senden');
  sendBtn.innerHTML =
    '<svg viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" transform="rotate(-90 12 12)"/>' +
    '</svg>';
  form.appendChild(sendBtn);
  panel.appendChild(form);

  widget.appendChild(panel);
  widget.appendChild(bubble);
  root.appendChild(widget);

  // ---- behaviour ----
  function open() {
    widget.classList.add('kib-widget--open');
    if (messages.children.length === 0) {
      addAssistantMessage(greeting);
    }
    setTimeout(function () { input.focus(); }, 50);
  }

  function close() {
    widget.classList.remove('kib-widget--open');
  }

  bubble.addEventListener('click', function () {
    if (widget.classList.contains('kib-widget--open')) close();
    else open();
  });
  closeBtn.addEventListener('click', close);

  function scrollMessages() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addUserMessage(text) {
    messages.appendChild(el('div', 'kib-widget__msg kib-widget__msg--user', text));
    scrollMessages();
  }

  function addAssistantMessage(text) {
    messages.appendChild(el('div', 'kib-widget__msg kib-widget__msg--assistant', text));
    scrollMessages();
  }

  function newAssistantBubble() {
    const node = el('div', 'kib-widget__msg kib-widget__msg--assistant', '');
    messages.appendChild(node);
    scrollMessages();
    return node;
  }

  function trackClick(conversationId, productId, messageId) {
    if (!conversationId || !productId) return;
    fetch(backendUrl('/v1/conversations/' + encodeURIComponent(conversationId) + '/clicks'), {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify({ product_id: productId, message_id: messageId || null }),
      keepalive: true,
    }).catch(function () { /* fire-and-forget */ });
  }

  function renderProductCards(products, conversationId, messageId) {
    if (!products || !products.length) return;
    const wrap = el('div', 'kib-widget__products');
    products.forEach(function (p) {
      const card = el('a', 'kib-widget__product');
      card.href = p.url || '#';
      card.target = '_blank';
      card.rel = 'noopener noreferrer';
      if (p.image_url) {
        const img = document.createElement('img');
        img.className = 'kib-widget__product-img';
        img.src = p.image_url;
        img.alt = '';
        img.loading = 'lazy';
        card.appendChild(img);
      }
      const meta = el('div', 'kib-widget__product-meta');
      meta.appendChild(el('div', 'kib-widget__product-name', p.name || ''));
      if (p.price && p.currency) {
        meta.appendChild(el('div', 'kib-widget__product-price',
          parseFloat(p.price).toFixed(2) + ' ' + p.currency));
      }
      card.appendChild(meta);
      card.addEventListener('click', function () {
        trackClick(conversationId, p.id, messageId);
      });
      wrap.appendChild(card);
    });
    messages.appendChild(wrap);
    scrollMessages();
  }

  function addLoadingPlaceholder() {
    const node = el('div', 'kib-widget__msg kib-widget__msg--loading', i18n.thinking || 'Thinking…');
    messages.appendChild(node);
    scrollMessages();
    return node;
  }

  function addErrorMessage(text) {
    messages.appendChild(el('div', 'kib-widget__msg kib-widget__msg--error', text));
    scrollMessages();
  }

  function backendUrl(path) {
    return cfg.backendUrl.replace(/\/$/, '') + path;
  }

  function jsonHeaders() {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Api-Key': cfg.apiKey,
    };
  }

  // ---- streaming consumer ----
  // Parses standard SSE blocks (`event: NAME\ndata: JSON\n\n`).
  function consumeSSE(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    function pump() {
      return reader.read().then(function (chunk) {
        if (chunk.done) {
          if (buffer.trim()) parseBlock(buffer);
          return;
        }
        buffer += decoder.decode(chunk.value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          parseBlock(buffer.slice(0, idx));
          buffer = buffer.slice(idx + 2);
        }
        return pump();
      });
    }
    function parseBlock(block) {
      let evType = '';
      let data = '';
      block.split('\n').forEach(function (line) {
        if (line.indexOf('event:') === 0) evType = line.slice(6).trim();
        else if (line.indexOf('data:') === 0) data = line.slice(5).trim();
      });
      if (!evType || !data) return;
      try {
        onEvent({ type: evType, data: JSON.parse(data) });
      } catch (e) { /* ignore malformed */ }
    }
    return pump();
  }

  function streamMessage(text) {
    let convoId = '';
    try { convoId = localStorage.getItem(STORAGE_CONVO) || ''; } catch (e) {}
    const url = convoId
      ? backendUrl('/v1/conversations/' + encodeURIComponent(convoId) + '/messages/stream')
      : backendUrl('/v1/conversations/stream');
    const body = convoId
      ? { content: text }
      : { visitor_id: visitorId, initial_message: text };

    addUserMessage(text);
    const loading = addLoadingPlaceholder();
    sendBtn.disabled = true;

    let bubble = null;
    let assistantText = '';
    let gotChunk = false;
    let convoIdInUse = '';
    let assistantMsgId = '';
    let productList = [];

    return fetch(url, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    }).then(function (r) {
      if (!r.ok) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          throw new Error((j && j.detail) || ('HTTP ' + r.status));
        });
      }
      return consumeSSE(r, function (ev) {
        if (ev.type === 'start') {
          convoIdInUse = ev.data.conversation_id || '';
          assistantMsgId = ev.data.assistant_message_id || '';
          productList = (ev.data && ev.data.products) || [];
          persistConvoId(convoIdInUse);
          loading.remove();
          bubble = newAssistantBubble();
        } else if (ev.type === 'chunk') {
          gotChunk = true;
          if (!bubble) bubble = newAssistantBubble();
          assistantText += ev.data.delta || '';
          bubble.textContent = assistantText;
          scrollMessages();
        } else if (ev.type === 'error') {
          if (loading.parentNode) loading.remove();
          const detail = (ev.data && ev.data.detail) || (i18n.error || 'Error');
          addErrorMessage(detail);
        } else if (ev.type === 'end') {
          // After the assistant text settled, surface clickable product cards.
          renderProductCards(productList, convoIdInUse, assistantMsgId);
        }
      });
    }).catch(function (err) {
      if (loading.parentNode) loading.remove();
      // Stale conversation_id → clear and let the user retry from scratch.
      if (convoId && /HTTP\s*4(?:04|01)/i.test(String(err && err.message))) {
        clearConvo();
      }
      if (!gotChunk) addErrorMessage((err && err.message) || (i18n.error || 'Error'));
    }).then(function () {
      sendBtn.disabled = false;
    });
  }

  // ---- non-streaming fallback (older browsers) ----
  function postJSON(text) {
    let convoId = '';
    try { convoId = localStorage.getItem(STORAGE_CONVO) || ''; } catch (e) {}
    const url = convoId
      ? backendUrl('/v1/conversations/' + encodeURIComponent(convoId) + '/messages')
      : backendUrl('/v1/conversations');
    const body = convoId
      ? { content: text }
      : { visitor_id: visitorId, initial_message: text };

    addUserMessage(text);
    const loading = addLoadingPlaceholder();
    sendBtn.disabled = true;

    return fetch(url, {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    }).then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
      .then(function (res) {
        loading.remove();
        if (res.status === 404 && convoId) {
          clearConvo();
          return postJSON(text);
        }
        if (res.status >= 400) {
          addErrorMessage((res.body && res.body.detail) || (i18n.error || 'Error'));
          return;
        }
        if (res.body && res.body.conversation && res.body.conversation.id) {
          persistConvoId(res.body.conversation.id);
        }
        const a = res.body && res.body.assistant_message;
        if (a && a.content) addAssistantMessage(a.content);
      })
      .catch(function () {
        if (loading.parentNode) loading.remove();
        addErrorMessage(i18n.error || 'Error');
      })
      .then(function () { sendBtn.disabled = false; });
  }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    if (supportsStreaming()) {
      streamMessage(text);
    } else {
      postJSON(text);
    }
  });
})();
