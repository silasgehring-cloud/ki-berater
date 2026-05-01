(function () {
  'use strict';

  const cfg = window.KIB_ADMIN || {};
  const i18n = cfg.i18n || {};

  const $msg = document.getElementById('kib-status-msg');
  const $test = document.getElementById('kib-test-connection');
  const $bulk = document.getElementById('kib-bulk-sync');

  function setMsg(text, level) {
    if (!$msg) return;
    $msg.textContent = text;
    $msg.className = 'kib-status-msg kib-status-msg--' + level;
  }

  function postAjax(action) {
    const body = new URLSearchParams();
    body.set('action', action);
    body.set('_wpnonce', cfg.nonce);
    return fetch(cfg.ajaxUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    }).then(function (r) {
      return r.json().then(function (j) {
        return { status: r.status, body: j };
      });
    });
  }

  if ($test) {
    $test.addEventListener('click', function () {
      setMsg(i18n.testing || 'Testing...', 'info');
      postAjax('kib_test_connection').then(function (res) {
        if (res.body && res.body.success) {
          const d = res.body.data || {};
          setMsg((i18n.okFor || 'OK %s').replace('%s', d.domain || ''), 'ok');
        } else if (res.status === 401) {
          setMsg(i18n.authFailed || 'Auth failed', 'error');
        } else {
          const detail = res.body && res.body.data && res.body.data.message
            ? res.body.data.message
            : (i18n.noConn || 'No connection');
          setMsg(detail, 'error');
        }
      }).catch(function () {
        setMsg(i18n.noConn || 'No connection', 'error');
      });
    });
  }

  if ($bulk) {
    $bulk.addEventListener('click', function () {
      setMsg(i18n.syncing || 'Syncing...', 'info');
      postAjax('kib_bulk_sync_start').then(function (res) {
        if (res.body && res.body.success) {
          const d = res.body.data || {};
          const total = d.total || 0;
          setMsg((i18n.syncDone || 'Sync started: %d products').replace('%d', total), 'info');
          pollSyncStatus();
        } else {
          const detail = res.body && res.body.data && res.body.data.message
            ? res.body.data.message
            : 'unknown error';
          setMsg((i18n.syncFailed || 'Sync failed: %s').replace('%s', detail), 'error');
        }
      });
    });
  }

  // ---- Overview stats ----

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function fmtEur(value) {
    const n = parseFloat(value || '0');
    return isFinite(n) ? n.toFixed(2) + ' €' : '–';
  }

  function loadOverview() {
    if (!document.getElementById('kib-overview-table')) return;
    postAjax('kib_analytics_overview').then(function (res) {
      if (!res.body || !res.body.success) return;
      const d = res.body.data || {};
      const c = d.conversations || {};
      const r = d.revenue || {};
      setText('kib-stat-total', String(c.total || 0));
      setText('kib-stat-converted', String(c.converted || 0));
      setText('kib-stat-rate', (c.conversion_rate_percent || 0).toFixed(1) + ' %');
      setText('kib-stat-revenue', fmtEur(r.total_eur));
      setText('kib-stat-llm', fmtEur(d.llm_cost_eur));
    });
  }

  // Auto-load on settings page open.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadOverview);
  } else {
    loadOverview();
  }

  function pollSyncStatus() {
    let attempts = 0;
    const maxAttempts = 60; // ~2 min
    const poll = function () {
      attempts++;
      postAjax('kib_bulk_sync_status').then(function (res) {
        if (res.body && res.body.success) {
          const s = res.body.data || {};
          if (s.status === 'complete') {
            setMsg((i18n.syncDone || 'Sync done: %d products').replace('%d', s.processed || 0), 'ok');
            return;
          }
          if (s.status === 'failed') {
            setMsg((i18n.syncFailed || 'Sync failed: %s').replace('%s', s.error || ''), 'error');
            return;
          }
          if (attempts < maxAttempts) {
            setTimeout(poll, 2000);
          }
        }
      });
    };
    setTimeout(poll, 2000);
  }
})();
