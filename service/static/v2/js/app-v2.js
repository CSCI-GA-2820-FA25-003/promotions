// service/static/v2/js/app-v2.js
(function () {
  'use strict';

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

  function renderRows(items) {
    var tbody = document.querySelector('#promotions_table tbody');
    tbody.innerHTML = '';
    if (!items || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No promotions available</td></tr>';
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
        `<td class="text-center">${id}</td>`,
        `<td>${name}</td>`,
        `<td>${type}</td>`,
        `<td class="text-center">${value}</td>`,
        `<td class="text-center">${productId}</td>`,
        `<td class="text-center">${startDate}</td>`,
        `<td class="text-center">${endDate}</td>`
      ].join('');
      frag.appendChild(tr);
    });
    tbody.appendChild(frag);

    var info = document.querySelector('#page_info');
    if (info) info.textContent = items.length + ' promotions';
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

  async function loadPromotions() {
    try {
      var res = await fetch('/promotions', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('GET /promotions failed: ' + res.status);
      var json = await res.json();
      console.log('raw /promotions response:', json);
      var items = normalizeResponse(json);
      renderRows(items);
    } catch (err) {
      console.error(err);
      var tbody = document.querySelector('#promotions_table tbody');
      tbody.innerHTML = '<tr><td colspan="7" class="text-danger">Failed to load promotions. See console.</td></tr>';
      var info = document.querySelector('#page_info');
      if (info) info.textContent = 'Error';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadPromotions();
  });

})();
