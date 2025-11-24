// service/v2/js/app-v2.js
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

    if (now.isAfter(end)) {
      return 'Ended ' + end.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    } else if (now.isBefore(start)) {
      return 'Starts ' + start.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    } else {
      return 'Ends ' + end.fromNow() + '<br><small class="text-muted">' + startFormatted + ' &rarr; ' + endFormatted + '</small>';
    }
  }

  function showSuccessToast(msg) {
    try {
      var toast = document.createElement('div');
      toast.className = 'alert alert-success position-fixed';
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

  function normalizeDateInput(s) {
    if (!s) return null;
    var t = String(s).trim().replaceAll('/', '-');
    if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
    var d = new Date(t);
    if (!isNaN(d.getTime())) {
      var y = d.getFullYear();
      var m = String(d.getMonth() + 1).padStart(2, '0');
      var day = String(d.getDate()).padStart(2, '0');
      return y + '-' + m + '-' + day;
    }
    return null;
  }

  /* -------------------------
     State & Core Logic
  ------------------------- */
  var allPromotions = [];
  var currentView = 'table'; // 'table' or 'card'
  var currentFilters = {
    active: null,
    name: null,
    type: null,
    productId: null
  };

  // Main render function (uses global allPromotions)
  function render() {
    updateDashboardStats(allPromotions);
    updatePromotionsCount(allPromotions.length);
    if (currentView === 'table') {
      renderTable(allPromotions);
    } else {
      renderCards(allPromotions);
    }
  }

  async function loadPromotions(queryParams) {
    var tableView = $id('promotions_table_view');
    var cardView = $id('promotions_cards_view');
    if (currentView === 'table' && tableView.querySelector('tbody')) {
      tableView.querySelector('tbody').innerHTML = '<tr><td colspan="8" class="text-center small text-muted">Loading...</td></tr>';
    } else if (cardView) {
      cardView.innerHTML = '<div class="text-center small text-muted p-5">Loading...</div>';
    }

    try {
      var url = '/api/promotions';
      if (queryParams) {
        url += '?' + queryParams;
      }
      var res = await fetch(url, { credentials: 'same-origin', cache: 'no-cache' });
      if (!res.ok) throw new Error('GET /promotions failed: ' + res.status);
      var json = await res.json();
      allPromotions = normalizeResponse(json);
      render();
    } catch (err) {
      console.error(err);
      allPromotions = [];
      render();
    }
  }

  /* -------------------------
     UI Update Functions
  ------------------------- */
  function updatePromotionsCount(count) {
    $id('promotionsCount').textContent = count + ' promotion' + (count !== 1 ? 's' : '');
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

      var diffTime = Math.abs(end - now);
      var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      if (isActive && diffDays <= 7) expiringCount++;

      types[p.promotion_type] = (types[p.promotion_type] || 0) + 1;
    });

    if ($id('statActiveCount')) $id('statActiveCount').textContent = activeCount;
    if ($id('statExpiringCount')) $id('statExpiringCount').textContent = expiringCount;
    updateTypeChart(types);
  }

  function updateTypeChart(typesData) {
    var ctx = document.getElementById('typeChart');
    if (!ctx) return;
    if (typeChartInstance) {
      typeChartInstance.destroy();
    }
    typeChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(typesData),
        datasets: [{ data: Object.values(typesData), backgroundColor: ['#5e72e4', '#2dce89', '#11cdef'], borderWidth: 0 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
        cutout: '70%'
      }
    });
  }

  /* -------------------------
     View-Specific Renderers
  ------------------------- */
  function renderCards(items) {
    var cardView = $id('promotions_cards_view');
    if (!cardView) return;
    cardView.innerHTML = '';

    if (!items || items.length === 0) {
      cardView.innerHTML = '<div class="empty-card-view"><p class="text-muted">No promotions to display.</p></div>';
      return;
    }

    var frag = document.createDocumentFragment();
    items.forEach(function (p) {
      var card = document.createElement('div');
      card.className = 'promo-card';

      var id = escapeHtml(p.id ?? '');
      var name = escapeHtml(p.name ?? '');
      var type = escapeHtml(p.promotion_type ?? '');
      var productId = escapeHtml(p.product_id ?? '');

      var today = new Date();
      var isActive = new Date(p.start_date) <= today && new Date(p.end_date) >= today;
      var statusBadge = isActive ? '<span class="badge badge-soft-success">Active</span>' : '<span class="badge badge-soft-danger">Inactive</span>';

      var typeBadgeClass = 'badge-soft-primary';
      if (p.promotion_type === 'BOGO') typeBadgeClass = 'badge-soft-success';
      if (p.promotion_type === 'DISCOUNT') typeBadgeClass = 'badge-soft-danger';
      var typeHtml = '<span class="badge ' + typeBadgeClass + '">' + type + '</span>';

      var imageUrl = 'https://picsum.photos/seed/' + (p.product_id || p.id) + '/400/260';

      card.innerHTML = [
        '<div class="promo-card-img-container">',
        '<img src="' + imageUrl + '" class="promo-card-img" alt="Promotion Image for ' + name + '">',
        '</div>',
        '<div class="promo-card-content">',
        '<div class="promo-card-actions">',
        '<button class="edit-btn" data-id="' + id + '" data-name="' + name + '" data-promotion=\'' + escapeHtml(JSON.stringify(p)) + '\'>' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg></button>',
        '<button class="deactivate-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-ban" viewBox="0 0 16 16"><path d="M15 8a6.973 6.973 0 0 0-1.71-4.584l-9.874 9.875A7 7 0 0 0 15 8M2.71 12.584l9.874-9.875a7 7 0 0 0-9.874 9.874ZM16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0"/></svg></button>',
        '<button class="delete-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg></button>',
        '</div>',
        '<h3 class="promo-card-title" title="' + name + '">' + name + '</h3>',
        '<div class="promo-card-tags">' + statusBadge + typeHtml + '</div>',
        '<div class="promo-card-date"> Product ID: <span class="product-id-tag">' + productId + '</span></div>',
        '<div class="promo-card-date" style="margin-top: 0.25rem;">' + formatRelativeDateRange(p.start_date, p.end_date) + '</div>',
        '</div>'
      ].join('');
      frag.appendChild(card);
    });
    cardView.appendChild(frag);
  }

  function renderTable(items) {
    var tbody = document.querySelector('#promotions_table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No promotions available</td></tr>';
      return;
    }
    var frag = document.createDocumentFragment();
    items.forEach(function (p) {
      var tr = document.createElement('tr');
      var id = escapeHtml(p.id ?? '');
      var name = escapeHtml(p.name ?? '');
      var type = escapeHtml(p.promotion_type ?? '');
      var value = escapeHtml(p.value ?? '');
      var productId = escapeHtml(p.product_id ?? '');

      var today = new Date();
      var isActive = new Date(p.start_date) <= today && new Date(p.end_date) >= today;
      var statusBadge = isActive ? '<span class="badge badge-soft-success">Active</span>' : '<span class="badge badge-soft-danger">Inactive</span>';

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
        '<button class="edit-btn" data-id="' + id + '" data-name="' + name + '" data-promotion=\'' + escapeHtml(JSON.stringify(p)) + '\'>' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/></svg></button>',
        '<button class="deactivate-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-ban" viewBox="0 0 16 16"><path d="M15 8a6.973 6.973 0 0 0-1.71-4.584l-9.874 9.875A7 7 0 0 0 15 8M2.71 12.584l9.874-9.875a7 7 0 0 0-9.874 9.874ZM16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0"/></svg></button>',
        '<button class="delete-btn" data-id="' + id + '" data-name="' + name + '">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg></button>',
        '</td>'
      ].join('');
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);
  }
  /* -------------------------
     Initialization & Event Handlers
  ------------------------- */
  document.addEventListener('DOMContentLoaded', function () {
    // Initial load
    loadPromotions();

    // View switcher logic
    var viewTableBtn = $id('view-table-btn');
    var viewCardBtn = $id('view-card-btn');
    var tableView = $id('promotions_table_view');
    var cardView = $id('promotions_cards_view');

    function switchView(view) {
      if (currentView === view) return;
      currentView = view;

      if (view === 'table') {
        tableView.classList.remove('d-none');
        cardView.classList.add('d-none');
        viewTableBtn.classList.add('active');
        viewCardBtn.classList.remove('active');
      } else {
        tableView.classList.add('d-none');
        cardView.classList.remove('d-none');
        viewTableBtn.classList.remove('active');
        viewCardBtn.classList.add('active');
      }
      render();
    }

    if (viewTableBtn) viewTableBtn.addEventListener('click', function () { switchView('table'); });
    if (viewCardBtn) viewCardBtn.addEventListener('click', function () { switchView('card'); });

    // Modal and Filter initializations
    (function initCreateModal() {
      var createModalEl = $id('createModal');
      var createModal = bootstrap.Modal.getOrCreateInstance(createModalEl);

      createModalEl?.addEventListener('shown.bs.modal', function () { $id('inputName')?.focus(); });
      createModalEl?.addEventListener('hidden.bs.modal', function () {
        $id('createForm')?.reset();
        $id('createForm')?.classList.remove('was-validated');
        $id('createError')?.classList.add('d-none');
      });

      $id('createForm')?.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        this.classList.add('was-validated');
        if (!this.checkValidity()) return;

        var payload = {
          name: ($id('inputName').value || '').trim(),
          promotion_type: ($id('inputType').value || '').trim(),
          value: Number($id('inputValue').value),
          product_id: parseInt($id('inputProductId').value, 10) || null,
          start_date: normalizeDateInput($id('inputStart').value),
          end_date: normalizeDateInput($id('inputEnd').value)
        };

        var submitBtn = $id('createSubmit');
        if (submitBtn) submitBtn.disabled = true;

        try {
          var res = await fetch('/api/promotions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
          });
          if (!res.ok) {
            var errText = (await res.json()).message || 'Create failed';
            throw new Error(errText);
          }
          createModal.hide();
          showSuccessToast('Promotion created');
          loadPromotions();
        } catch (err) {
          console.error('Create failed:', err);
          var ce = $id('createError');
          if (ce) {
            ce.classList.remove('d-none');
            ce.textContent = err.message;
          }
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });
    })();

    (function initDeleteModal() {
      var deleteModalEl = $id('deleteModal');
      var deleteModal = bootstrap.Modal.getOrCreateInstance(deleteModalEl);
      var currentDeleteId = null;

      document.addEventListener('click', function (e) {
        var deleteBtn = e.target.closest('.delete-btn');
        if (deleteBtn) {
          currentDeleteId = deleteBtn.dataset.id;
          $id('deletePromotionId').textContent = currentDeleteId;
          $id('deletePromotionName').textContent = deleteBtn.dataset.name;
          deleteModal.show();
        }
      });

      $id('confirmDelete')?.addEventListener('click', async function () {
        if (!currentDeleteId) return;
        this.disabled = true;
        try {
          var res = await fetch('/api/promotions/' + currentDeleteId, { method: 'DELETE', credentials: 'same-origin' });
          if (!res.ok) throw new Error('DELETE failed: ' + res.status);
          deleteModal.hide();
          showSuccessToast('Promotion deleted');
          loadPromotions();
        } catch (err) {
          console.error('Delete failed:', err);
          alert('Failed to delete promotion: ' + err.message);
        } finally {
          this.disabled = false;
          currentDeleteId = null;
        }
      });
    })();

    (function initDeactivateAction() {
      document.addEventListener('click', async function (e) {
        var btn = e.target.closest('.deactivate-btn');
        if (!btn) return;

        var id = btn.dataset.id;
        var name = btn.dataset.name || 'this promotion';
        if (!window.confirm('Deactivate "' + name + '"?')) return;

        btn.disabled = true;
        try {
          var res = await fetch('/api/promotions/' + id + '/deactivate', { method: 'PUT', credentials: 'same-origin' });
          if (!res.ok) throw new Error('PUT failed: ' + res.status);
          showSuccessToast('Promotion deactivated');
          loadPromotions();
        } catch (err) {
          console.error('Deactivate failed:', err);
          alert('Failed to deactivate promotion: ' + err.message);
        } finally {
          btn.disabled = false;
        }
      });
    })();

    (function initEditModal() {
      var editModalEl = $id('editModal');
      var editModal = bootstrap.Modal.getOrCreateInstance(editModalEl);
      var currentEditId = null;

      document.addEventListener('click', function (e) {
        var editBtn = e.target.closest('.edit-btn');
        if (editBtn) {
          try {
            var promotion = JSON.parse(editBtn.dataset.promotion);
            currentEditId = promotion.id;
            $id('editId').value = promotion.id;
            $id('editName').value = promotion.name || '';
            $id('editType').value = promotion.promotion_type || '';
            $id('editValue').value = promotion.value ?? '';
            $id('editProductId').value = promotion.product_id ?? '';
            $id('editStart').value = formatDateShort(promotion.start_date) || '';
            $id('editEnd').value = formatDateShort(promotion.end_date) || '';
            editModal.show();
          } catch (err) {
            console.error('Failed to parse promotion data for edit:', err);
          }
        }
      });

      $id('editForm')?.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        this.classList.add('was-validated');
        if (!this.checkValidity() || !currentEditId) return;

        var payload = {
          name: ($id('editName').value || '').trim(),
          promotion_type: ($id('editType').value || '').trim(),
          value: Number($id('editValue').value),
          product_id: parseInt($id('editProductId').value, 10) || null,
          start_date: normalizeDateInput($id('editStart').value),
          end_date: normalizeDateInput($id('editEnd').value)
        };

        var submitBtn = $id('editSubmit');
        if (submitBtn) submitBtn.disabled = true;

        try {
          var res = await fetch('/api/promotions/' + currentEditId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
          });
          if (!res.ok) {
            var errText = (await res.json()).message || 'Update failed';
            throw new Error(errText);
          }
          editModal.hide();
          showSuccessToast('Promotion updated');
          loadPromotions();
        } catch (err) {
          console.error('Update failed:', err.message);
          var ee = $id('editError');
          if (ee) {
            ee.classList.remove('d-none');
            ee.textContent = err.message;
          }
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });

      editModalEl?.addEventListener('hidden.bs.modal', function () {
        $id('editForm')?.classList.remove('was-validated');
        $id('editError')?.classList.add('d-none');
        currentEditId = null;
      });
    })();

    (function initFilters() {
      var searchInput = $id('searchInput');
      var filterPills = document.querySelectorAll('.filter-pill');
      var filterType = $id('filterType');
      var filterProductId = $id('filterProductId');
      var btnClearFilters = $id('btnClearFilters');
      var searchTimeout = null;

      function applyFilters() {
        var queryParams = new URLSearchParams();
        if (currentFilters.active && currentFilters.active !== 'all') {
          queryParams.set('active', currentFilters.active === 'active');
        }

        if (currentFilters.name) {
          queryParams.set('name', currentFilters.name);
        }

        if (currentFilters.type) {
          queryParams.set('promotion_type', currentFilters.type);
        }

        if (currentFilters.productId) {
          queryParams.set('product_id', currentFilters.productId);
        }

        var qs = queryParams.toString();
        var newUrl = qs ? window.location.pathname + '?' + qs : window.location.pathname;
        window.history.pushState({}, '', newUrl);
        loadPromotions(qs);
      }

      function resetOtherFilters(except) {
        if (except !== 'name') { currentFilters.name = null; if (searchInput) searchInput.value = ''; }
        if (except !== 'active') { currentFilters.active = null; filterPills.forEach(p => p.classList.remove('active')); }
        if (except !== 'type') { currentFilters.type = null; if (filterType) filterType.value = ''; }
        if (except !== 'productId') { currentFilters.productId = null; if (filterProductId) filterProductId.value = ''; }
      }

      searchInput?.addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
          resetOtherFilters('name');
          currentFilters.name = e.target.value.trim();
          applyFilters();
        }, 300);
      });

      filterPills.forEach(function (pill) {
        pill.addEventListener('click', function () {
          resetOtherFilters('active');
          filterPills.forEach(function (p) { p.classList.remove('active'); });
          this.classList.add('active');
          currentFilters.active = this.dataset.filter;
          applyFilters();
        });
      });

      filterType?.addEventListener('change', function (e) {
        resetOtherFilters('type');
        currentFilters.type = e.target.value;
        applyFilters();
      });

      filterProductId?.addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
          resetOtherFilters('productId');
          currentFilters.productId = e.target.value.trim();
          applyFilters();
        }, 300);
      });

      btnClearFilters?.addEventListener('click', function () {
        resetOtherFilters('none');
        var allPill = document.querySelector('.filter-pill[data-filter="all"]');
        if (allPill) allPill.classList.add('active');
        applyFilters();
      });
    })();
  });

})();
