// service/static/v2/js/app-v2.js
var typeChartInstance = null;
dayjs.extend(window.dayjs_plugin_relativeTime);
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

  function formatRelativeDateRange(startStr, endStr) {
    var now = dayjs();
    var start = dayjs(startStr);
    var end = dayjs(endStr);

    if (!start.isValid() || !end.isValid()) {
      return '<span class="text-muted">Invalid date</span>';
    }

    var startFormatted = start.format('MMM D');
    var endFormatted = end.format('MMM D, YYYY');

    if (now.isBefore(start)) {
      return 'Starts ' + start.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    } else if (now.isAfter(end)) {
      return 'Ended ' + end.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    } else {
      return 'Ends ' + end.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    }
  }

  /* -------------------------
     Table rendering / loader
  ------------------------- */
  // Global filter state
  var currentFilters = {
    active: null,      // null, 'all', 'active', 'inactive'
    name: null,
    type: null,
    productId: null
  };

  async function loadPromotions(queryParams) {
    var tbody = document.querySelector('#promotions_table tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="8" class="text-center small text-muted">Loading...</td></tr>';

    try {
      var url = '/api/promotions';
      if (queryParams) {
        url += '?' + queryParams;
      }

      var res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('GET /promotions failed: ' + res.status);
      var json = await res.json();
      var items = normalizeResponse(json);
      renderRows(items);
      updatePromotionsCount(items.length);
    } catch (err) {
      console.error(err);
      tbody.innerHTML = '<tr><td colspan="8" class="text-danger">Failed to load promotions. See console.</td></tr>';
      updatePromotionsCount(0);
    }
  }

  function updatePromotionsCount(count) {
    var countEl = $id('promotionsCount');
    if (countEl) {
      countEl.textContent = count + ' promotion' + (count !== 1 ? 's' : '');
    }
  }

  function updateDashboardStats(items) {
    var now = new Date();
    var activeCount = 0;
    var expiringCount = 0;
    var types = { 'PERCENT': 0, 'DISCOUNT': 0, 'BOGO': 0 };

    items.forEach(function (p) {
      var start = new Date(p.start_date);
      var end = new Date(p.end_date);
      var isActive = start <= now && end >= now;

      if (isActive) activeCount++;

      // Expiring in next 7 days
      var diffTime = Math.abs(end - now);
      var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      if (isActive && diffDays <= 7) expiringCount++;

      // Type count
      if (types[p.promotion_type] !== undefined) {
        types[p.promotion_type]++;
      } else {
        // handle unknown types just in case
        types[p.promotion_type] = (types[p.promotion_type] || 0) + 1;
      }
    });

    // Update DOM text
    var elActive = document.getElementById('statActiveCount');
    if (elActive) elActive.textContent = activeCount;

    var elExpiring = document.getElementById('statExpiringCount');
    if (elExpiring) elExpiring.textContent = expiringCount;

    // Update Chart
    updateTypeChart(types);
  }

  function updateTypeChart(typesData) {
    var ctx = document.getElementById('typeChart');
    if (!ctx) return;

    // If chart exists, destroy it before re-creating
    if (typeChartInstance) {
      typeChartInstance.destroy();
    }

    typeChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(typesData),
        datasets: [{
          data: Object.values(typesData),
          backgroundColor: ['#5e72e4', '#2dce89', '#11cdef'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: true }
        },
        cutout: '70%'
      }
    });
  }

  function renderRows(items) {
    var tbody = document.querySelector('#promotions_table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    // Update stats based on the current view
    updateDashboardStats(items);

    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No promotions available</td></tr>';
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

      // Calculate Status Badge
      var today = new Date();
      var start = new Date(p.start_date);
      var end = new Date(p.end_date);
      var isActive = start <= today && end >= today;
      var statusBadge = isActive
        ? '<span class="badge badge-soft-success">Active</span>'
        : '<span class="badge badge-soft-danger">Inactive</span>';

      // Type Badge
      var typeBadgeClass = 'badge-soft-primary';
      if (p.promotion_type === 'BOGO') typeBadgeClass = 'badge-soft-success';
      if (p.promotion_type === 'DISCOUNT') typeBadgeClass = 'badge-soft-danger';
      var typeHtml = '<span class="badge ' + typeBadgeClass + '">' + type + '</span>';

      tr.innerHTML = [
        '<td class="text-center"><span class="text-muted">#' + id + '</span></td>',
        '<td class="fw-bold">' + name + '</td>',
        '<td>' + typeHtml + '</td>',
        '<td class="text-center font-monospace">' + value + '</td>',
        '<td class="text-center"><span class="product-id-tag">' + productId + '</span></td>',
        '<td class="text-center">' + statusBadge + '</td>',
        '<td class="text-center">' + formatRelativeDateRange(p.start_date, p.end_date) + '</td>',
        '<td class="text-center" style="white-space: nowrap;">' +
        '<button class="edit-btn" data-id="' + id + '" data-name="' + name + '" data-promotion=\'' + JSON.stringify(p) + '\'>' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-pencil" viewBox="0 0 16 16">' +
        '<path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/>' +
        '</svg>' +
        '</button>' +
        '<button class="deactivate-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-ban" viewBox="0 0 16 16">' +
        '<path d="M15 8a6.973 6.973 0 0 0-1.71-4.584l-9.874 9.875A7 7 0 0 0 15 8M2.71 12.584l9.874-9.875a7 7 0 0 0-9.874 9.874ZM16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0"/>' +
        '</svg>' +
        '</button>' +
        '<button class="delete-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">' +
        '<path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>' +
        '<path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>' +
        '</svg>' +
        '</button>' +
        '</td>'
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
        var res = await fetch('/api/promotions', {
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

  /* -------------------------
     Delete modal: logic
  ------------------------- */
  (function initDeleteModal() {
    var deleteModalEl = $id('deleteModal');
    var deleteModal = null;
    if (deleteModalEl && window.bootstrap && window.bootstrap.Modal) {
      try {
        deleteModal = new bootstrap.Modal(deleteModalEl, {});
      } catch (e) {
        console.warn('Bootstrap Modal init failed', e);
      }
    }

    var currentDeleteId = null;

    // Event delegation for delete buttons
    document.addEventListener('click', function (e) {
      if (e.target && e.target.closest('.delete-btn')) {
        var btn = e.target.closest('.delete-btn');
        var id = btn.getAttribute('data-id');
        var name = btn.getAttribute('data-name');

        // Set modal content
        $id('deletePromotionId').textContent = id;
        $id('deletePromotionName').textContent = name;
        currentDeleteId = id;

        // Show modal
        if (deleteModal) {
          deleteModal.show();
        }
      }
    });

    // Confirm delete button handler
    var confirmBtn = $id('confirmDelete');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', async function () {
        if (!currentDeleteId) return;

        // Disable button
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Deleting...';

        try {
          var res = await fetch('/api/promotions/' + currentDeleteId, {
            method: 'DELETE',
            credentials: 'same-origin'
          });

          if (!res.ok) {
            throw new Error('DELETE failed: ' + res.status);
          }

          // Close modal
          if (deleteModal) {
            deleteModal.hide();
          }

          // Show success toast
          showSuccessToast('Promotion deleted');

          // Refresh table
          if (typeof loadPromotions === 'function') loadPromotions();

        } catch (err) {
          console.error('Delete failed:', err);
          alert('Failed to delete promotion: ' + err.message);
        } finally {
          confirmBtn.disabled = false;
          confirmBtn.textContent = 'Delete';
          currentDeleteId = null;
        }
      });
    }
  })();

  /* -------------------------
     Deactivate action: logic
  ------------------------- */
  (function initDeactivateAction() {
    document.addEventListener('click', async function (e) {
      var btn = e.target && e.target.closest('.deactivate-btn');
      if (!btn) return;

      var id = btn.getAttribute('data-id');
      var name = btn.getAttribute('data-name') || 'this promotion';
      if (!id) return;

      var ok = window.confirm('Deactivate "' + name + '"? This ends the promotion as of yesterday.');
      if (!ok) return;

      var originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Working...';

      try {
        var res = await fetch('/api/promotions/' + id + '/deactivate', {
          method: 'PUT',
          credentials: 'same-origin'
        });

        if (!res.ok) {
          throw new Error('PUT failed: ' + res.status);
        }

        showSuccessToast('Promotion deactivated');
        if (typeof loadPromotions === 'function') loadPromotions();
      } catch (err) {
        console.error('Deactivate failed:', err);
        alert('Failed to deactivate promotion: ' + (err.message || err));
      } finally {
        btn.disabled = false;
        btn.textContent = originalText || 'Deactivate';
      }
    });
  })();

  /* -------------------------
     Edit modal: logic
  ------------------------- */
  (function initEditModal() {
    var editModalEl = $id('editModal');
    var editModal = null;
    if (editModalEl && window.bootstrap && window.bootstrap.Modal) {
      try {
        editModal = new bootstrap.Modal(editModalEl, {});
      } catch (e) {
        console.warn('Bootstrap Modal init failed', e);
      }
    }

    var currentEditId = null;

    // Clear edit form errors
    function clearEditFieldErrors() {
      var ids = ['editName', 'editType', 'editValue', 'editProductId', 'editStart', 'editEnd'];
      ids.forEach(function (id) {
        var el = $id(id);
        if (el) {
          el.classList.remove('is-invalid');
        }
      });
      var ee = $id('editError');
      if (ee) { ee.classList.add('d-none'); ee.textContent = ''; }
    }

    function showEditFieldError(fieldId, message) {
      var el = $id(fieldId);
      if (!el) return;
      el.classList.add('is-invalid');
      var fb = el.nextElementSibling;
      if (fb && fb.classList && fb.classList.contains('invalid-feedback')) {
        fb.textContent = message;
      } else {
        var ee = $id('editError');
        if (ee) { ee.classList.remove('d-none'); ee.textContent = message; }
      }
    }

    // Event delegation for edit buttons
    document.addEventListener('click', function (e) {
      if (e.target && e.target.closest('.edit-btn')) {
        var btn = e.target.closest('.edit-btn');
        var id = btn.getAttribute('data-id');
        var promotionJson = btn.getAttribute('data-promotion');

        try {
          var promotion = JSON.parse(promotionJson);

          // Populate form fields
          $id('editId').value = id;
          $id('editName').value = promotion.name || '';
          $id('editType').value = promotion.promotion_type || '';
          $id('editValue').value = promotion.value || '';
          $id('editProductId').value = promotion.product_id || '';
          $id('editStart').value = formatDateShort(promotion.start_date) || '';
          $id('editEnd').value = formatDateShort(promotion.end_date) || '';

          currentEditId = id;
          clearEditFieldErrors();

          // Show modal
          if (editModal) {
            editModal.show();
          }
        } catch (err) {
          console.error('Failed to parse promotion data:', err);
          alert('Failed to load promotion data');
        }
      }
    });

    // Handle modal close event
    if (editModalEl) {
      editModalEl.addEventListener('hidden.bs.modal', function () {
        var form = $id('editForm');
        if (form) {
          form.reset();
          form.classList.remove('was-validated');
        }
        clearEditFieldErrors();
        currentEditId = null;
      });
    }

    // Handle form submission
    var editForm = $id('editForm');
    if (!editForm) return;

    editForm.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      ev.stopPropagation();

      editForm.classList.add('was-validated');

      // Basic HTML5 validity
      if (!editForm.checkValidity()) {
        return;
      }

      if (!currentEditId) {
        alert('No promotion ID found');
        return;
      }

      // Gather and coerce fields
      clearEditFieldErrors();

      var rawName = ($id('editName').value || '').trim();
      var rawType = ($id('editType').value || '').trim();
      var rawValue = $id('editValue').value;
      var rawProductId = ($id('editProductId').value || '').trim();
      var rawStart = $id('editStart').value || '';
      var rawEnd = $id('editEnd').value || '';

      // product_id: if provided, must be integer
      var productId = null;
      if (rawProductId !== '') {
        var parsedPid = parseInt(rawProductId, 10);
        if (Number.isNaN(parsedPid) || !Number.isFinite(parsedPid)) {
          showEditFieldError('editProductId', 'Product ID must be an integer');
          return;
        }
        productId = parsedPid;
      } else {
        productId = null;
      }

      // value coercion
      var valueNum = Number(rawValue);
      if (!Number.isFinite(valueNum) || valueNum < 0) {
        showEditFieldError('editValue', 'Value must be a non-negative number');
        return;
      }

      // normalize dates
      var startDate = normalizeDateInput(rawStart);
      var endDate = normalizeDateInput(rawEnd);

      var payload = {
        name: rawName || null,
        promotion_type: rawType || null,
        value: valueNum,
        product_id: productId,
        start_date: startDate,
        end_date: endDate
      };

      // UI: disable submit
      var submitBtn = $id('editSubmit');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Updating...';
      }
      editForm.setAttribute('aria-busy', 'true');

      try {
        var res = await fetch('/api/promotions/' + currentEditId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          // Try to parse structured errors
          var errText = '';
          try {
            var errJson = await res.json();
            if (errJson) {
              if (errJson.errors && typeof errJson.errors === 'object') {
                for (var f in errJson.errors) {
                  var fid = 'edit' + f.split('_').map(function (s) { return s.charAt(0).toUpperCase() + s.slice(1); }).join('');
                  if ($id(fid)) {
                    showEditFieldError(fid, errJson.errors[f]);
                  } else {
                    var ee = $id('editError');
                    if (ee) { ee.classList.remove('d-none'); ee.textContent += (errJson.errors[f] + '\n'); }
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
            var ee2 = $id('editError');
            if (ee2) { ee2.classList.remove('d-none'); ee2.textContent = errText; }
          }
          throw new Error(errText || ('HTTP ' + res.status));
        }

        // Success
        var updated = null;
        try { updated = await res.json(); } catch (e) { updated = null; }
        if (editModal) {
          try { editModal.hide(); } catch (e) { /* ignore */ }
        } else {
          var btnClose = document.querySelector('#editModal .btn-close');
          if (btnClose) btnClose.click();
        }

        // Refresh table
        try {
          if (typeof loadPromotions === 'function') loadPromotions();
        } catch (e) { console.warn('reload failed', e); }

        // Show toast
        showSuccessToast('Promotion updated');

      } catch (err) {
        console.error('Update failed:', err);
        var ee3 = $id('editError');
        if (ee3 && ee3.classList.contains('d-none')) {
          ee3.classList.remove('d-none');
          ee3.textContent = err.message || String(err);
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Update';
        }
        editForm.removeAttribute('aria-busy');
      }
    });
  })();

  /* -------------------------
     Filters: Event Handlers
  ------------------------- */
  (function initFilters() {
    var searchInput = $id('searchInput');
    var filterPills = document.querySelectorAll('.filter-pill');
    var filterType = $id('filterType');
    var filterProductId = $id('filterProductId');
    var btnClearFilters = $id('btnClearFilters');

    var searchTimeout = null;

    // Initialize filters from URL on page load
    function initFromUrl() {
      var urlParams = new URLSearchParams(window.location.search);

      if (urlParams.has('active')) {
        var activeVal = urlParams.get('active');
        if (activeVal === 'true') {
          currentFilters.active = 'active';
          filterPills.forEach(function (pill) {
            pill.classList.remove('active');
            if (pill.getAttribute('data-filter') === 'active') {
              pill.classList.add('active');
            }
          });
        } else if (activeVal === 'false') {
          currentFilters.active = 'inactive';
          filterPills.forEach(function (pill) {
            pill.classList.remove('active');
            if (pill.getAttribute('data-filter') === 'inactive') {
              pill.classList.add('active');
            }
          });
        }
      } else if (urlParams.has('name')) {
        currentFilters.name = urlParams.get('name');
        if (searchInput) searchInput.value = currentFilters.name;
      } else if (urlParams.has('promotion_type')) {
        currentFilters.type = urlParams.get('promotion_type');
        if (filterType) filterType.value = currentFilters.type;
      } else if (urlParams.has('product_id')) {
        currentFilters.productId = urlParams.get('product_id');
        if (filterProductId) filterProductId.value = currentFilters.productId;
      }
    }

    // Initialize from URL
    initFromUrl();

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function () {
      // Reset filters
      currentFilters.active = null;
      currentFilters.name = null;
      currentFilters.type = null;
      currentFilters.productId = null;

      // Reinitialize from URL
      initFromUrl();

      // Apply filters without updating URL (already changed by popstate)
      var queryParams = window.location.search.substring(1);
      loadPromotions(queryParams);
    });

    function applyFilters() {
      var queryParams = '';

      // Priority: active > name > type > product_id (backend priority)
      if (currentFilters.active && currentFilters.active !== 'all') {
        // active: true or false
        if (currentFilters.active === 'active') {
          queryParams = 'active=true';
        } else if (currentFilters.active === 'inactive') {
          queryParams = 'active=false';
        }
      } else if (currentFilters.name && currentFilters.name.trim()) {
        queryParams = 'name=' + encodeURIComponent(currentFilters.name.trim());
      } else if (currentFilters.type) {
        queryParams = 'promotion_type=' + encodeURIComponent(currentFilters.type);
      } else if (currentFilters.productId) {
        queryParams = 'product_id=' + encodeURIComponent(currentFilters.productId);
      }

      // Update browser URL
      var newUrl = window.location.pathname;
      if (queryParams) {
        newUrl += '?' + queryParams;
      }
      window.history.pushState({}, '', newUrl);

      loadPromotions(queryParams);
    }

    // Search input (debounced)
    if (searchInput) {
      searchInput.addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
          currentFilters.name = e.target.value;
          // Clear other filters when searching by name
          if (currentFilters.name && currentFilters.name.trim()) {
            currentFilters.active = null;
            currentFilters.type = null;
            currentFilters.productId = null;
            // Reset UI
            filterPills.forEach(function (pill) { pill.classList.remove('active'); });
            if (filterType) filterType.value = '';
            if (filterProductId) filterProductId.value = '';
          }
          applyFilters();
        }, 300);
      });
    }

    // Status pills
    filterPills.forEach(function (pill) {
      pill.addEventListener('click', function () {
        var filter = this.getAttribute('data-filter');

        // Update active state
        filterPills.forEach(function (p) { p.classList.remove('active'); });
        this.classList.add('active');

        currentFilters.active = filter;

        // Clear other filters
        if (filter !== 'all') {
          currentFilters.name = null;
          currentFilters.type = null;
          currentFilters.productId = null;
          // Reset UI
          if (searchInput) searchInput.value = '';
          if (filterType) filterType.value = '';
          if (filterProductId) filterProductId.value = '';
        }

        applyFilters();
      });
    });

    // Type dropdown
    if (filterType) {
      filterType.addEventListener('change', function (e) {
        currentFilters.type = e.target.value;

        // Clear other filters when selecting type
        if (currentFilters.type) {
          currentFilters.active = null;
          currentFilters.name = null;
          currentFilters.productId = null;
          // Reset UI
          filterPills.forEach(function (pill) { pill.classList.remove('active'); });
          if (searchInput) searchInput.value = '';
          if (filterProductId) filterProductId.value = '';
        }

        applyFilters();
      });
    }

    // Product ID input (debounced)
    if (filterProductId) {
      filterProductId.addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
          currentFilters.productId = e.target.value;

          // Clear other filters when entering product ID
          if (currentFilters.productId) {
            currentFilters.active = null;
            currentFilters.name = null;
            currentFilters.type = null;
            // Reset UI
            filterPills.forEach(function (pill) { pill.classList.remove('active'); });
            if (searchInput) searchInput.value = '';
            if (filterType) filterType.value = '';
          }

          applyFilters();
        }, 300);
      });
    }

    // Clear filters button
    if (btnClearFilters) {
      btnClearFilters.addEventListener('click', function () {
        // Reset all filters
        currentFilters.active = null;
        currentFilters.name = null;
        currentFilters.type = null;
        currentFilters.productId = null;

        // Reset UI
        if (searchInput) searchInput.value = '';
        if (filterType) filterType.value = '';
        if (filterProductId) filterProductId.value = '';
        filterPills.forEach(function (pill) {
          pill.classList.remove('active');
          if (pill.getAttribute('data-filter') === 'all') {
            pill.classList.add('active');
          }
        });

        // Clear URL parameters
        window.history.pushState({}, '', window.location.pathname);

        // Reload all promotions
        loadPromotions();
      });
    }
  })();

  // end of IIFE
})();
