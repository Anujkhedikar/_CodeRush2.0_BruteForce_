/* YUKTI — Tactical telemetry frontend behaviors */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    /* ================= NAV ================= */
    var navBar = document.getElementById('navBar');
    var prevY = window.scrollY;
    function navScroll() {
      if (!navBar) return;
      navBar.classList.toggle('nav-scrolled', window.scrollY > 8);
      prevY = window.scrollY;
    }
    navScroll();
    window.addEventListener('scroll', navScroll, { passive: true });

    var burger = document.getElementById('navBurger');
    var panel = document.getElementById('mobilePanel');
    if (burger && panel) {
      burger.addEventListener('click', function () {
        var open = panel.classList.toggle('open');
        burger.setAttribute('aria-expanded', String(open));
      });
    }

    /* ================= FOOTER YEAR ================= */
    document.querySelectorAll('[data-year]').forEach(function (el) {
      el.textContent = new Date().getFullYear();
    });

    /* ================= BACK TO TOP ================= */
    var backTop = document.getElementById('backTop');
    if (backTop) {
      function toggleBackTop() {
        backTop.classList.toggle('show', window.scrollY > 420);
      }
      toggleBackTop();
      window.addEventListener('scroll', toggleBackTop, { passive: true });
    }

    /* ================= REVEAL ================= */
    var reveals = document.querySelectorAll('.reveal');
    if (reveals.length && 'IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      reveals.forEach(function (el) { io.observe(el); });
    } else {
      reveals.forEach(function (el) { el.classList.add('revealed'); });
    }

    /* ================= HERO TERMINAL TICKER ================= */
    var tickLog = document.getElementById('tickLog');
    var TICKS = [
      'SCAN_ACTIVE [REPO] : structure index engaged...',
      'DISPATCH_MATCH [MENTOR-2241] : telemetry handshake done',
      'VERIFY_PASS [PYTHON] : blocks_parsed=2 issues=0',
      'OTP_LOCK [SESSION] : secure gateway ID-89483 sealed',
      'PING_GRID [ZONE-07] : 12MS · node operational',
      'LEDGER_APPEND [TURN] : tokens/cost recorded · immutable',
    ];
    if (tickLog) {
      var ti = 0;
      setInterval(function () {
        ti = (ti + 1) % TICKS.length;
        tickLog.textContent = TICKS[ti];
      }, 3200);
    }

    /* ================= LIFECYCLE PIPELINE ================= */
    var stepBtns = document.querySelectorAll('.step-btn');
    var steps = {
      1: { name: 'CONFIGURE_SPECIALTY', status: 'selecting operand grid…', handshake: '…' },
      2: { name: 'SECURE_VERIFICATION', status: 'OTP pending · license match query…', handshake: '…' },
      3: { name: 'EXECUTE_VALIDATE', status: 'parsing hint :: output sealed to gateway', handshake: '✓ LOCKED' }
    };
    if (stepBtns.length) {
      stepBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
          stepBtns.forEach(function (b) { b.classList.remove('is-active'); });
          btn.classList.add('is-active');
          var step = steps[btn.getAttribute('data-step')];
          var readout = document.getElementById('visReadout');
          var ssStep = document.getElementById('ssStep');
          if (readout) readout.textContent = 'STEP_' + btn.getAttribute('data-step') + ' : ' + step.name + ' :: ' + step.status;
          var shield = document.getElementById('shieldSync');
          if (shield) {
            shield.style.borderColor = btn.getAttribute('data-step') === '3'
              ? 'rgba(16,185,129,0.7)' : 'rgba(16,185,129,0.4)';
          }
          if (ssStep) ssStep.textContent = step.handshake;
        });
      });
    }

    /* ================= FAQ ACCORDION ================= */
    document.querySelectorAll('.acc-item').forEach(function (item) {
      var q = item.querySelector('.acc-q');
      if (!q) return;
      q.addEventListener('click', function () {
        var a = item.querySelector('.acc-a');
        var open = item.classList.toggle('open');
        if (a) a.style.maxHeight = open ? a.scrollHeight + 'px' : '0px';
      });
    });

    /* ================= CURSOR GLOW ================= */
    var glow = document.getElementById('cursor-glow');
    if (glow) {
      window.addEventListener('mousemove', function (e) {
        glow.style.opacity = '1';
        glow.style.transform = 'translate3d(' + e.clientX + 'px, ' + e.clientY + 'px, 0) translate(-50%, -50%)';
      });
      document.addEventListener('mouseleave', function () {
        glow.style.opacity = '0';
      });
    }

    /* ================= TELEMETRY :: LANDING ================= */
    if (document.getElementById('sSessions')) {
      fetch('/stats', { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (d) {
          var total = d.totals || {};
          var el = document.getElementById('sSessions');
          if (el) el.textContent = (total.sessions || 0).toLocaleString();
        })
        .catch(function () {});
    }

    /* ================= TELEMETRY :: LIVE PAGE ================= */
    if (document.getElementById('kpiSessions')) {
      measurePing();
      loadStats();
    }
  });

  /* ================= PING TO /health ================= */
  function measurePing() {
    var pingEl = document.getElementById('pingReadout');
    var nodeEl = document.getElementById('nodeMsg');
    var start = performance.now();
    fetch('/health', { headers: { Accept: 'application/json' }, cache: 'no-store' })
      .then(function (r) {
        var ms = Math.max(1, Math.round(performance.now() - start));
        if (pingEl) pingEl.textContent = ms + 'MS';
        return r.json();
      })
      .then(function (j) {
        if (nodeEl) nodeEl.textContent = (j && j.message) ? j.message : 'node operational';
      })
      .catch(function () {
        if (pingEl) pingEl.textContent = '—';
        if (nodeEl) nodeEl.textContent = 'node unreachable';
      });
  }

  /* ================= /stats RENDER ================= */
  function loadStats() {
    fetch('/stats', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(renderStats)
      .catch(function () {
        ['kpiSessions', 'kpiTurns', 'kpiTokens', 'kpiCost'].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) el.textContent = '—';
        });
        var t = document.getElementById('topSessions');
        if (t) t.innerHTML = '<tr><td colspan="6" class="muted">Analytics unavailable while the mentor is idle.</td></tr>';
      });
  }

  function setText(id, v) {
    var el = document.getElementById(id);
    if (el) el.textContent = v;
  }

  function renderStats(d) {
    var totals = d.totals || {};
    setText('kpiSessions', (totals.sessions || 0).toLocaleString());
    setText('kpiTurns', (totals.turns || 0).toLocaleString());
    setText('kpiTokens', (totals.total_tokens || 0).toLocaleString());
    var cost = totals.cost || 0;
    setText('kpiCost', cost >= 0.01 ? '$' + cost.toFixed(2) : '$<0.01');

    renderDays((d.by_day || []));
    renderBars('modeBars', (d.by_mode || []), 'turns');
    renderBars('providerBars', (d.by_provider || []), 'turns');
    renderBars('modelBars', (d.by_model || []), 'turns');
    renderTopSessions((d.top_sessions || []));
  }

  /* 14-day series -> vertical bars */
  function renderDays(days) {
    var chart = document.getElementById('daysChart');
    if (!chart) return;
    if (!days.length) {
      chart.innerHTML = '<div class="muted" style="font-size:12px;align-self:center">No data yet.</div>';
      return;
    }
    var max = days.reduce(function (m, d) { return Math.max(m, d.turns || 0); }, 0) || 1;
    chart.innerHTML = days.map(function (d) {
      var v = d.turns || 0;
      var h = v === 0 ? 3 : Math.max(8, Math.round((v / max) * 120));
      var hot = v > 0;
      return '<div class="day-tick">' +
        '<div class="day-bar' + (hot ? ' hot' : '') + '" style="height:' + h + 'px" title="' + (d.day || '') + ' · ' + v + ' turns"></div>' +
        '<span class="day-label">' + String(d.day || '').slice(5) + '</span></div>';
    }).join('');
  }

  function renderBars(id, rows, valueKey) {
    var el = document.getElementById(id);
    if (!el) return;
    var items = rows.slice(0, 6);
    if (!items.length) {
      el.innerHTML = '<div class="muted" style="font-size:12px;padding:8px 0">No ' + id.replace('Bars', '') + ' usage yet.</div>';
      return;
    }
    var max = items.reduce(function (m, r) { return Math.max(m, r[valueKey] || 0); }, 0) || 1;
    el.innerHTML = items.map(function (r) {
      var pct = Math.max(4, Math.round(((r[valueKey] || 0) / max) * 100));
      return '<div class="bar-row">' +
        '<span class="bar-label" title="' + esc(r.name) + '">' + esc(r.name) + '</span>' +
        '<div class="bar-track"><span class="bar-fill" style="width:' + pct + '%">&nbsp;</span></div>' +
        '<span class="bar-value">' + (r[valueKey] || 0) + '</span></div>';
    }).join('');
  }

  function fmtTime(v) {
    if (v == null || v === '') return '—';
    if (typeof v === 'number') {
      var d = new Date(v * 1000);
      if (!isNaN(d.getTime())) return d.toLocaleDateString();
      return String(v);
    }
    return String(v).slice(0, 10);
  }

  function renderTopSessions(list) {
    var t = document.getElementById('topSessions');
    if (!t) return;
    if (!list.length) {
      t.innerHTML = '<tr><td colspan="6" class="muted">No sessions recorded yet — run the mentor first.</td></tr>';
      return;
    }
    t.innerHTML = list.map(function (s) {
      var prev = s.preview || s.id || '—';
      if (prev.length > 48) prev = prev.slice(0, 48) + '…';
      var cost = s.cost || 0;
      return '<tr>' +
        '<td class="mono">' + esc(s.id || '—') + '</td>' +
        '<td>' + esc(prev) + '</td>' +
        '<td class="mono">' + (s.turns || 0) + '</td>' +
        '<td class="mono">' + (s.tokens || 0).toLocaleString() + '</td>' +
        '<td class="mono">' + (cost >= 0.01 ? '$' + cost.toFixed(2) : '$<0.01') + '</td>' +
        '<td class="mono muted">' + fmtTime(s.updated_at) + '</td>' +
        '</tr>';
    }).join('');
  }

  var escMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return escMap[c]; });
  }
})();