// API wrappers for Promotions service

async function handleJsonResponse(res, actionLabel) {
  if (res.ok) {
    // Some endpoints (DELETE) may return empty body
    const contentType = res.headers.get("Content-Type") || "";
    const contentLength = res.headers.get("Content-Length");
    const hasBody =
      res.status !== 204 &&
      contentType.includes("application/json") &&
      contentLength !== "0";
    if (hasBody) {
      try {
        return await res.json();
      } catch (e) {
        // Empty/invalid JSON: treat as empty body for success responses
        return null;
      }
    }
    return null;
  }
  let message = actionLabel + " failed";
  try {
    const body = await res.json();
    if (body && body.message) {
      message = body.message;
    }
  } catch (e) {
    // ignore JSON parse errors, fall back to default message
  }
  throw new Error(message);
}

export async function fetchPromotions(queryParams) {
  let url = "/api/promotions";
  if (queryParams) {
    url += "?" + queryParams;
  }
  const res = await fetch(url, { credentials: "same-origin", cache: "no-cache" });
  if (!res.ok) {
    throw new Error("GET /promotions failed: " + res.status);
  }
  return res.json();
}

export async function createPromotion(payload) {
  const res = await fetch("/api/promotions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res, "Create");
}

export async function updatePromotion(id, payload) {
  const res = await fetch("/api/promotions/" + id, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res, "Update");
}

export async function deletePromotion(id) {
  const res = await fetch("/api/promotions/" + id, {
    method: "DELETE",
    credentials: "same-origin",
  });
  return handleJsonResponse(res, "Delete");
}

export async function deactivatePromotion(id) {
  const res = await fetch("/api/promotions/" + id + "/deactivate", {
    method: "PUT",
    credentials: "same-origin",
  });
  return handleJsonResponse(res, "Deactivate");
}
