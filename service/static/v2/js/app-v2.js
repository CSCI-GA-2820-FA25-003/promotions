// service/static/v2/js/app-v2.js
(function () {
  'use strict';

  /* -------------------------
     Helpers
  ------------------------- */
  function $id(id) { return document.getElementById(id); }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;').replaceAll("'", '&#39;');
  }

  function formatDateShort(d) {
    if (!d) return '';
    try { return String(d).slice(0, 10); } catch (e) { return String(d); }
  }

  function normalizeResponse(json) {
    if (Array.isArray(json)) return json;
    if (!json) return [];
    if (Array.isArray(json.promotions)) return json.promotions;
    if (Array.isArray(json.data)) return json.data;
    if (Array.isArray(json.payload)) return json.payload;
    for (var k in json) {
      if (Array.isArray(json[k])) return json[k];
    }
    return [];
  }

  /* -------------------------
     Table rendering / loader
  ------------------------- */
  async function loadPromotions() {
    var tbody = document.querySelector('#promotions_table tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" class="text-center small text-muted">Loading...</td></tr>';
    try {
      var res = await fetch('/promotions', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('GET /promotions failed: ' + res.status);
      var json = await res.json();
      console.log('raw /promotions response:', json);
      var items = normalizeResponse(json);
      renderRows(items);
    } catch (err) {
      console.error(err);
      tbody.innerHTML = '<tr><td colspan="7" class="text-danger">Failed to load promotions. See console.</td></tr>';
      var info = $id('page_info');
      if (info) info.textContent = 'Error';
    }
  }

  function renderRows(items) {
    var tbody = document.querySelector('#promotions_table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No promotions available</td></tr>';
      var info0 = $id('page_info');
      if (info0) info0.textContent = '0 promotions';
      return;
    }
    var frag = document.createDocumentFragment();
    items.forEach(function (p) {
      var tr = document.createElement('tr');
      var id = escapeHtml(p.id ?? p.promotion_id ?? '');
      var name = escapeHtml(p.name ?? p.title ?? '');
      var type = escapeHtml(p.promotion_type ?? p.type ?? '');
      var value = escapeHtml((p.value === 0 || p.value) ? p.value : (p.discount ?? ''));
      var productId = escapeHtml(p.product_id ?? p.sku ?? '');
      var startDate = escapeHtml(formatDateShort(p.start_date ?? p.start ?? p.starts_at));
      var endDate = escapeHtml(formatDateShort(p.end_date ?? p.end ?? p.ends_at));

      tr.innerHTML = [
        '<td class="text-center">' + id + '</td>',
        '<td>' + name + '</td>',
        '<td>' + type + '</td>',
        '<td class="text-center">' + value + '</td>',
        '<td class="text-center">' + productId + '</td>',
        '<td class="text-center">' + startDate + '</td>',
        '<td class="text-center">' + endDate + '</td>'
      ].join('');
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);

    var info = $id('page_info');
    if (info) info.textContent = items.length + ' promotions';
  }

  /* -------------------------
     Create modal: helpers
  ------------------------- */
  function normalizeDateInput(s) {
    if (!s) return null;
    var t = String(s).trim().replace(/\//g, '-');
    if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
    // try Date parse
    var d = new Date(t);
    if (!isNaN(d.getTime())) {
      var y = d.getFullYear();
      var m = String(d.getMonth() + 1).padStart(2, '0');
      var day = String(d.getDate()).padStart(2, '0');
      return y + '-' + m + '-' + day;
    }
    return null;
  }

  function showCreateFieldError(fieldId, message) {
    var el = $id(fieldId);
    if (!el) return;
    el.classList.add('is-invalid');
    // find the next .invalid-feedback
    var fb = el.nextElementSibling;
    if (fb && fb.classList && fb.classList.contains('invalid-feedback')) {
      fb.textContent = message;
    } else {
      // fallback: global error box
      var ce = $id('createError');
      if (ce) { ce.classList.remove('d-none'); ce.textContent = message; }
    }
  }

  function clearCreateFieldErrors() {
    var ids = ['inputProductId', 'inputValue', 'inputName', 'inputType', 'inputStart', 'inputEnd'];
    ids.forEach(function (id) {
      var el = $id(id);
      if (el) {
        el.classList.remove('is-invalid');
      }
    });
    var ce = $id('createError');
    if (ce) { ce.classList.add('d-none'); ce.textContent = ''; }
  }

  function showSuccessToast(msg) {
    try {
      var toast = document.createElement('div');
      toast.className = 'alert alert-success position-fixed';
      // position top-right
      toast.style.top = '1rem';
      toast.style.right = '1rem';
      toast.style.zIndex = 12000;
      toast.textContent = msg || 'Success';
      document.body.appendChild(toast);
      setTimeout(function () { toast.remove(); }, 3000);
    } catch (e) {
      console.log('toast failed', e);
    }
  }

  /* -------------------------
     Initialize: load table
  ------------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    loadPromotions();
  });

  /* -------------------------
     Create modal: logic
     (kept in same IIFE so loadPromotions is visible)
  ------------------------- */
  (function initCreateModal() {
    var createModalEl = $id('createModal');
    var createModal = null;
    if (createModalEl && window.bootstrap && window.bootstrap.Modal) {
      try {
        createModal = new bootstrap.Modal(createModalEl, {});
      } catch (e) {
        console.warn('Bootstrap Modal init failed', e);
      }
    }

    // auto-focus first input when modal shown
    if (createModalEl) {
      createModalEl.addEventListener('shown.bs.modal', function () {
        var el = $id('inputName');
        if (el) el.focus();
      });
      createModalEl.addEventListener('hidden.bs.modal', function () {
        // clear the form when modal is hidden
        var form = $id('createForm');
        if (form) {
          form.reset();
          form.classList.remove('was-validated');
        }
        clearCreateFieldErrors();
      });
    }

    var createForm = $id('createForm');
    if (!createForm) return;

    createForm.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      ev.stopPropagation();

      createForm.classList.add('was-validated');

      // basic HTML5 validity
      if (!createForm.checkValidity()) {
        return;
      }

      // gather and coerce fields
      clearCreateFieldErrors();

      var rawName = ($id('inputName').value || '').trim();
      var rawType = ($id('inputType').value || '').trim();
      var rawValue = $id('inputValue').value;
      var rawProductId = ($id('inputProductId').value || '').trim();
      var rawStart = $id('inputStart').value || '';
      var rawEnd = $id('inputEnd').value || '';

      // product_id: if provided, must be integer
      var productId = null;
      if (rawProductId !== '') {
        var parsedPid = parseInt(rawProductId, 10);
        if (Number.isNaN(parsedPid) || !Number.isFinite(parsedPid)) {
          showCreateFieldError('inputProductId', 'Product ID must be an integer');
          return;
        }
        productId = parsedPid;
      } else {
        productId = null;
      }

      // value coercion
      var valueNum = Number(rawValue);
      if (!Number.isFinite(valueNum) || valueNum < 0) {
        showCreateFieldError('inputValue', 'Value must be a non-negative number');
        return;
      }

      // normalize dates
      var startDate = normalizeDateInput(rawStart);
      var endDate = normalizeDateInput(rawEnd);
      // If user typed an unparsable date, leave null (backend will validate)
      // or if you want to enforce: showCreateFieldError('inputStart', 'Invalid date');
      // but we'll allow null and rely on server checks for requiredness.

      var payload = {
        name: rawName || null,
        promotion_type: rawType || null,
        value: valueNum,
        product_id: productId,
        start_date: startDate,
        end_date: endDate
      };

      // UI: disable submit
      var submitBtn = $id('createSubmit');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';
      }
      // mark form busy
      createForm.setAttribute('aria-busy', 'true');

      try {
        var res = await fetch('/promotions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          // try to parse structured errors
          var errText = '';
          try {
            var errJson = await res.json();
            // if backend returns {errors: {product_id: 'must be integer'}} or {message: '...'}
            if (errJson) {
              if (errJson.errors && typeof errJson.errors === 'object') {
                for (var f in errJson.errors) {
                  // input ids use camelCase mapping (product_id -> inputProductId)
                  var fid = 'input' + f.split('_').map(function (s, i) { return i === 0 ? s.charAt(0).toUpperCase() + s.slice(1) : s.charAt(0).toUpperCase() + s.slice(1); }).join('');
                  // ex: 'product_id' => 'inputProductId'
                  if ($id(fid)) {
                    showCreateFieldError(fid, errJson.errors[f]);
                  } else {
                    var ce = $id('createError');
                    if (ce) { ce.classList.remove('d-none'); ce.textContent += (errJson.errors[f] + '\n'); }
                  }
                }
              } else if (errJson.message) {
                errText = errJson.message;
              } else {
                errText = JSON.stringify(errJson);
              }
            }
          } catch (e) {
            try { errText = await res.text(); } catch (e2) { errText = 'HTTP ' + res.status; }
          }
          if (errText) {
            var ce2 = $id('createError');
            if (ce2) { ce2.classList.remove('d-none'); ce2.textContent = errText; }
          }
          throw new Error(errText || ('HTTP ' + res.status));
        }

        // success
        var created = null;
        try { created = await res.json(); } catch (e) { created = null; }
        if (createModal) {
          try { createModal.hide(); } catch (e) { /* ignore */ }
        } else {
          // fallback: try to click close
          var btnClose = document.querySelector('#createModal .btn-close');
          if (btnClose) btnClose.click();
        }

        // refresh table
        try {
          if (typeof loadPromotions === 'function') loadPromotions();
        } catch (e) { console.warn('reload failed', e); }

        // show toast
        showSuccessToast('Promotion created');

      } catch (err) {
        console.error('Create failed:', err);
        // err message already placed into createError by above logic where possible
        var ce3 = $id('createError');
        if (ce3 && ce3.classList.contains('d-none')) {
          ce3.classList.remove('d-none');
          ce3.textContent = err.message || String(err);
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create';
        }
        createForm.removeAttribute('aria-busy');
      }
    });
  })();

  // end of IIFE
})();
