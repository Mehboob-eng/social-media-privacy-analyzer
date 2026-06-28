export async function apiFetch(path, { method="GET", headers={}, body } = {}) {
  const access = localStorage.getItem("access");
  const opts = {
    method,
    headers: { Accept: "application/json", ...headers, ...(access ? { Authorization: `Bearer ${access}` } : {}) },
    ...(body ? { body: typeof body === "string" ? body : JSON.stringify(body) } : {})
  };
  const res = await fetch(path, opts);
  let data = {};
  try { data = await res.json(); } catch {}
  if (res.status === 401) {
    localStorage.removeItem("access"); localStorage.removeItem("refresh");
    // let caller decide navigation; you can throw a special error
    const err = new Error(data?.detail || "Unauthorized"); err.code = 401; throw err;
  }
  if (!res.ok) throw new Error(data?.detail || data?.error || "Request failed");
  return data;
}
