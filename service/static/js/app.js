// service/static/js/app.js

function setStatus(msg) {
  const el = document.getElementById("status");
  el.textContent = msg;
}

function pickName(p) {
  // Fallback order for name-like fields returned by different backends
  return (
    (p && (p.name ||
           p.promotion_name ||
           p.promo_name ||
           p.title ||
           p.code)) || ""
  );
}

function renderOne(p) {
  if (!p) return "";
  const v = (x) => (x === undefined || x === null ? "" : x);
  const nameVal = pickName(p);
  return `<tr>
    <td>${v(p.id)}</td><td>${v(nameVal)}</td><td>${v(p.promotion_type)}</td>
    <td>${v(p.value)}</td><td>${v(p.product_id)}</td><td>${v(p.start_date)}</td><td>${v(p.end_date)}</td>
  </tr>`;
}

function render(list) {
  const tbody = document.querySelector("#results tbody");
  const rows = Array.isArray(list) ? list : list ? [list] : [];
  tbody.innerHTML = rows.map(renderOne).join("");
}

async function api(path, options = {}) {
  const headers = options.body ? { "Content-Type": "application/json" } : undefined;
  const resp = await fetch(path, { headers, ...options });
  const ct = (resp.headers.get("content-type") || "").toLowerCase();
  let data = null;
  try {
    if (ct.includes("application/json")) {
      data = await resp.json();
    } else {
      const text = await resp.text();
      try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
    }
  } catch (e) {
    data = null;
  }
  if (!resp.ok) {
    const msg = data && (data.message || data.error) ? (data.message || data.error) : resp.statusText;
    const err = new Error(`${resp.status} ${msg}`);
    err.response = resp;
    err.data = data;
    throw err;
  }
  return { data, resp };
}

function toInt(value) {
  const n = parseInt(value, 10);
  return Number.isFinite(n) ? n : null;
}

async function createPromotion(body) {
  // Compatibility payload: include both 'name' and a common alias
  const payload = { ...body, promotion_name: body.name };

  // 1) POST to create
  const { data, resp } = await api("/promotions", { method: "POST", body: JSON.stringify(payload) });

  // 2) Hydrate a full representation of the created resource
  let created = data;
  let id = created && typeof created === "object" ? created.id : null;

  // Prefer Location header, if present
  const location = resp.headers.get("Location") || resp.headers.get("location");
  if ((!created || pickName(created) === "") && location) {
    const g = await api(location, { method: "GET" });
    created = g.data;
    id = created?.id ?? id;
  }

  // If we have an id, fetch by id to ensure full shape
  if ((!created || pickName(created) === "") && id) {
    const g = await api(`/promotions/${id}`, { method: "GET" });
    created = g.data;
  }

  // As a last resort, query by likely name keys (server-side list filters may vary)
  if ((!created || pickName(created) === "") && body.name) {
    const candidates = [
      `/promotions?name=${encodeURIComponent(body.name)}`,
      `/promotions?promotion_name=${encodeURIComponent(body.name)}`
    ];
    for (const path of candidates) {
      const g = await api(path, { method: "GET" });
      const list = Array.isArray(g.data) ? g.data : [];
      if (list.length > 0) { created = list[0]; break; }
    }
  }

  return { created, id: id ?? created?.id ?? null };
}

window.addEventListener("DOMContentLoaded", () => {
  const createBtn = document.getElementById("btn-create");
  createBtn?.addEventListener("click", async () => {
    try {
      const body = {
        name: document.getElementById("c-name").value.trim(),
        promotion_type: document.getElementById("c-type").value.trim(),
        value: toInt(document.getElementById("c-value").value),
        product_id: toInt(document.getElementById("c-product").value),
        start_date: document.getElementById("c-start").value.trim(),
        end_date: document.getElementById("c-end").value.trim(),
      };

      const { created, id } = await createPromotion(body);

      // UI fallback for display: if no name-like field is present, show the value the user entered
      let toRender = created || {};
      if (!pickName(toRender) && body.name) {
        toRender = { ...toRender, name: body.name };
      }

      setStatus(`Created id=${id ?? ""}`);
      render(toRender);
    } catch (e) {
      setStatus(e && e.message ? e.message : String(e));
      render([]); // keep table deterministic on error
    }
  });
});
