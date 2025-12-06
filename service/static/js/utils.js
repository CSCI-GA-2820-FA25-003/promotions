// Utility helpers shared across the frontend

// Ensure dayjs relativeTime plugin is registered if available
if (typeof dayjs !== "undefined" && typeof dayjs.extend === "function") {
  const relativeTimePlugin = window?.dayjs_plugin_relativeTime;
  if (relativeTimePlugin) {
    dayjs.extend(relativeTimePlugin);
  }
}

export function $id(id) {
  return document.getElementById(id);
}

export function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function formatDateShort(d) {
  if (!d) return "";
  try {
    return String(d).slice(0, 10);
  } catch (e) {
    return String(d);
  }
}

export function normalizeResponse(json) {
  if (Array.isArray(json)) return json;
  if (!json) return [];
  if (Array.isArray(json.promotions)) return json.promotions;
  if (Array.isArray(json.data)) return json.data;
  if (Array.isArray(json.payload)) return json.payload;
  for (const k in json) {
    if (Array.isArray(json[k])) return json[k];
  }
  return [];
}

export function formatRelativeDateRange(startStr, endStr) {
  const now = dayjs();
  const start = dayjs(startStr);
  const end = dayjs(endStr);

  if (!start.isValid() || !end.isValid()) {
    return '<span class="text-muted">Invalid date</span>';
  }

  const startFormatted = start.format("MMM D");
  const endFormatted = end.format("MMM D, YYYY");

  if (now.isAfter(end)) {
    return (
      "Ended " +
      end.fromNow() +
      '<br><small class="text-muted">' +
      startFormatted +
      " &rarr; " +
      endFormatted +
      "</small>"
    );
  }
  if (now.isBefore(start)) {
    return (
      "Starts " +
      start.fromNow() +
      '<br><small class="text-muted">' +
      startFormatted +
      " &rarr; " +
      endFormatted +
      "</small>"
    );
  }
  return (
    "Ends " +
    end.fromNow() +
    '<br><small class="text-muted">' +
    startFormatted +
    " &rarr; " +
    endFormatted +
    "</small>"
  );
}

export function showSuccessToast(msg) {
  try {
    const toast = document.createElement("div");
    toast.className = "alert alert-success position-fixed";
    toast.style.top = "1rem";
    toast.style.right = "1rem";
    toast.style.zIndex = 12000;
    toast.textContent = msg || "Success";
    document.body.appendChild(toast);
    setTimeout(function () {
      toast.remove();
    }, 3000);
  } catch (e) {
    console.log("toast failed", e);
  }
}

export function normalizeDateInput(s) {
  if (!s) return null;
  const t = String(s).trim().replaceAll("/", "-");
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
  const d = new Date(t);
  if (!isNaN(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }
  return null;
}
