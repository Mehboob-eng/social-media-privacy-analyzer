// src/assets/pages/profile.jsx
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../../config.js";

/* ---------- Tokens ---------- */
const inputClass =
  "w-full rounded-lg border border-slate-700/60 bg-slate-900/60 px-3 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400";
const cardClass =
  "rounded-2xl border border-slate-800/70 bg-slate-900/50 backdrop-blur p-5 shadow-xl shadow-slate-950/40";

export default function Profile() {
  const navigate = useNavigate();
  const access = localStorage.getItem("access");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");

  const [user, setUser] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    email_verified: false,
    two_factor_enabled: false,
  });

  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");

  // password
  const [curPass, setCurPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [showCur, setShowCur] = useState(false);
  const [showNew, setShowNew] = useState(false);

  // flags
  const [savingNames, setSavingNames] = useState(false);
  const [saving2fa, setSaving2fa] = useState(false);
  const [changingPass, setChangingPass] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    setError(""); setOkMsg("");
    try {
      const res = await fetch(`${API_BASE}/user/me/`, {
        headers: { Accept: "application/json", Authorization: `Bearer ${access}` },
      });
      if (res.status === 401) {
        localStorage.removeItem("access"); localStorage.removeItem("refresh");
        navigate("/login", { replace: true });
        return;
      }
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Failed to load user");

      setUser({
        username: data.username ?? "",
        email: data.email ?? "",
        first_name: data.first_name ?? "",
        last_name: data.last_name ?? "",
        email_verified: !!data.email_verified,
        two_factor_enabled: !!data.two_factor_enabled,
      });
      setFirst(data.first_name || "");
      setLast(data.last_name || "");
    } catch (e) {
      setError(e.message || "Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!access) { navigate("/login", { replace: true }); return; }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveNames(e) {
    e.preventDefault();
    setSavingNames(true); setError(""); setOkMsg("");
    try {
      const res = await fetch(`${API_BASE}/user/me/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` },
        body: JSON.stringify({ first_name: first.trim(), last_name: last.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || "Update failed");
      setOkMsg("Profile updated.");
      await load();
    } catch (e) {
      setError(e.message || "Update failed");
    } finally { setSavingNames(false); }
  }

  async function toggle2FA() {
    const next = !user.two_factor_enabled;
    setSaving2fa(true); setError(""); setOkMsg("");
    try {
      const res = await fetch(`${API_BASE}/user/me/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` },
        body: JSON.stringify({ two_factor_enabled: next }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || "Failed to update 2FA");
      setUser((u) => ({ ...u, two_factor_enabled: next }));
      setOkMsg(next ? "Two-factor authentication enabled." : "Two-factor authentication disabled.");
    } catch (e) {
      setError(e.message || "Failed to update 2FA");
    } finally { setSaving2fa(false); }
  }

  async function changePassword(e) {
    e.preventDefault();
    setChangingPass(true); setError(""); setOkMsg("");
    if (!curPass || !newPass) { setError("Please fill both password fields."); setChangingPass(false); return; }
    if (newPass.length < 8) { setError("New password must be at least 8 characters."); setChangingPass(false); return; }
    try {
      const res = await fetch(`${API_BASE}/user/password/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}` },
        body: JSON.stringify({ current_password: curPass, new_password: newPass }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || data?.error || "Password change failed");
      setCurPass(""); setNewPass(""); setShowCur(false); setShowNew(false);
      setOkMsg("Password changed successfully.");
    } catch (e) {
      setError(e.message || "Password change failed");
    } finally { setChangingPass(false); }
  }

  async function deleteAccount() {
    if (!window.confirm("Are you sure? This will permanently delete your account.")) return;
    setDeleting(true); setError(""); setOkMsg("");
    try {
      const res = await fetch(`${API_BASE}/user/me/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${access}` },
      });
      if (res.status !== 204 && !res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || data?.error || "Delete failed");
      }
      // local logout + go to login
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      navigate("/login", { replace: true });
    } catch (e) {
      setError(e.message || "Delete failed");
    } finally { setDeleting(false); }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Topbar */}
      <header className="sticky top-0 z-10 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto max-w-4xl px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(-1)}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900"
            >
              ← Back
            </button>
            <h1 className="font-semibold text-base sm:text-lg">Profile & Security</h1>
          </div>
          <button onClick={load} className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900">
            Refresh
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6 space-y-6">
        {/* Alerts */}
        {error && (
          <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-2 text-rose-200 text-sm">
            {error}
          </div>
        )}
        {okMsg && (
          <div className="rounded-lg border border-emerald-400/30 bg-emerald-900/25 px-3 py-2 text-emerald-200 text-sm">
            {okMsg}
          </div>
        )}

        {/* Account */}
        <section className={cardClass}>
          <h2 className="font-semibold">Account</h2>
          <div className="mt-3 grid gap-2 text-sm">
            <Row label="Username" value={loading ? "…" : user.username} />
            <Row label="Email" value={loading ? "…" : user.email} />
            <div className="flex items-center justify-between gap-4 pt-2 border-t border-slate-800/60 mt-2">
              <span className="text-sm text-slate-300">Email status</span>
              {loading ? (
                <span className="text-slate-400 text-sm">…</span>
              ) : user.email_verified ? (
                <Badge tone="success">● verified</Badge>
              ) : (
                <Badge tone="warn">○ not verified</Badge>
              )}
            </div>
          </div>
        </section>

        {/* Basic details */}
        <section className={cardClass}>
          <h2 className="font-semibold">Basic details</h2>
          <form onSubmit={saveNames} className="mt-3 grid gap-3 max-w-xl">
            <LabeledInput label="First name" value={first} onChange={setFirst} />
            <LabeledInput label="Last name" value={last} onChange={setLast} />
            <div className="pt-1">
              <button
                type="submit"
                disabled={savingNames}
                className="rounded-xl bg-cyan-500 text-slate-900 px-4 py-2 text-sm font-semibold hover:bg-cyan-400 disabled:opacity-60"
              >
                {savingNames ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
        </section>

        {/* Security */}
        <section className={cardClass}>
          <h2 className="font-semibold">Security</h2>

          {/* 2FA */}
          <div className="mt-3 flex items-center justify-between gap-3 border border-slate-800/60 rounded-xl px-3 py-3 bg-slate-900/40">
            <div>
              <div className="font-medium">Two-Factor Authentication</div>
              <div className="text-xs text-slate-400">Add an extra step at sign-in.</div>
            </div>
            <button
              onClick={toggle2FA}
              disabled={saving2fa || loading}
              className={
                "rounded-xl px-4 py-2 text-sm font-semibold disabled:opacity-60 " +
                (user.two_factor_enabled
                  ? "bg-emerald-500 text-slate-900 hover:bg-emerald-400"
                  : "bg-slate-800 text-slate-200 hover:bg-slate-700")
              }
            >
              {saving2fa ? "Saving…" : user.two_factor_enabled ? "Disable 2FA" : "Enable 2FA"}
            </button>
          </div>

          {/* Change password */}
          <form onSubmit={changePassword} className="mt-4 grid gap-3 max-w-xl">
            <LabeledInput
              label="Current password"
              type={showCur ? "text" : "password"}
              value={curPass}
              onChange={setCurPass}
              right={<SmallBtn onClick={() => setShowCur((s) => !s)}>{showCur ? "Hide" : "Show"}</SmallBtn>}
            />
            <LabeledInput
              label="New password"
              type={showNew ? "text" : "password"}
              value={newPass}
              onChange={setNewPass}
              right={<SmallBtn onClick={() => setShowNew((s) => !s)}>{showNew ? "Hide" : "Show"}</SmallBtn>}
            />
            <div className="pt-1">
              <button
                type="submit"
                disabled={changingPass}
                className="rounded-xl bg-cyan-500 text-slate-900 px-4 py-2 text-sm font-semibold hover:bg-cyan-400 disabled:opacity-60"
              >
                {changingPass ? "Updating…" : "Update password"}
              </button>
            </div>
          </form>
        </section>

        {/* Danger Zone */}
        <section className="rounded-2xl border border-rose-400/30 bg-rose-900/20 backdrop-blur p-5 shadow-xl shadow-rose-950/20">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold text-rose-200">Danger Zone</h3>
              <p className="text-xs text-rose-300/80">This will permanently delete your account.</p>
            </div>
            <button
              onClick={deleteAccount}
              disabled={deleting}
              className="rounded-xl border border-rose-400/50 bg-transparent px-4 py-2 text-sm text-rose-200 hover:bg-rose-900/30 disabled:opacity-60"
            >
              {deleting ? "Deleting…" : "Delete Account"}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}

/* ---------- Small UI helpers ---------- */
function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-slate-300">{label}</span>
      <span className="text-sm font-medium text-slate-100">{value}</span>
    </div>
  );
}
function Badge({ tone = "success", children }) {
  const tones = {
    success: "border-emerald-400/30 bg-emerald-900/25 text-emerald-200",
    warn: "border-amber-400/30 bg-amber-900/25 text-amber-200",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${tones[tone]}`}>
      {children}
    </span>
  );
}
function SmallBtn({ onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md px-3 py-1 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200"
    >
      {children}
    </button>
  );
}
function LabeledInput({ label, type = "text", value, onChange, right }) {
  return (
    <label className="block text-sm">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-slate-300 font-medium">{label}</span>
        {right ?? null}
      </div>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
        required
      />
    </label>
  );
}



// import { API_BASE } from "../../config.js";
// import React, { useEffect, useState } from "react";
// import { useNavigate } from "react-router-dom";

// export default function Profile() {
//   const navigate = useNavigate();
//   const [user, setUser] = useState(null);
//   const [loadingUser, setLoadingUser] = useState(true);
//   const [err, setErr] = useState("");

//   const [first, setFirst] = useState("");
//   const [last, setLast] = useState("");
//   const [saving, setSaving] = useState(false);

//   const [curPass, setCurPass] = useState("");
//   const [newPass, setNewPass] = useState("");
//   const [changing, setChanging] = useState(false);

//   const API_ROOT = API_BASE.replace(/\/auth\/?$/, "");
//   const access = localStorage.getItem("access");

//   async function loadUser() {
//     try {
//       const res = await fetch(`${API_ROOT}/user/`, {
//         headers: { Accept: "application/json", ...(access ? { Authorization: `Bearer ${access}` } : {}) },
//       });
//       if (res.status === 401) {
//         localStorage.removeItem("access"); localStorage.removeItem("refresh");
//         navigate("/login"); return;
//       }
//       const data = await res.json().catch(() => ({}));
//       if (!res.ok) throw new Error(data?.detail || "Failed to load user");
//       setUser(data);
//       setFirst(data?.first_name || "");
//       setLast(data?.last_name || "");
//     } catch (e) { setErr(e.message || "Error"); }
//     finally { setLoadingUser(false); }
//   }

//   useEffect(() => { loadUser(); /* eslint-disable-next-line */ }, []);

//   async function saveProfile(e) {
//     e.preventDefault();
//     setSaving(true);
//     try {
//       const res = await fetch(`${API_ROOT}/user/`, {
//         method: "PUT",
//         headers: {
//           "Content-Type": "application/json",
//           Accept: "application/json",
//           ...(access ? { Authorization: `Bearer ${access}` } : {}),
//         },
//         body: JSON.stringify({ first_name: first, last_name: last }),
//       });
//       const data = await res.json().catch(() => ({}));
//       if (!res.ok) throw new Error(data?.detail || "Update failed");
//       await loadUser();
//       alert("✅ Profile updated");
//     } catch (e) {
//       alert(e.message || "Update failed");
//     } finally { setSaving(false); }
//   }

//   async function changePassword(e) {
//     e.preventDefault();
//     if (newPass.length < 8) return alert("New password must be at least 8 characters");
//     setChanging(true);
//     try {
//       const res = await fetch(`${API_ROOT}/user/password/`, {
//         method: "PUT",
//         headers: {
//           "Content-Type": "application/json",
//           Accept: "application/json",
//           ...(access ? { Authorization: `Bearer ${access}` } : {}),
//         },
//         body: JSON.stringify({ current_password: curPass, new_password: newPass }),
//       });
//       const data = await res.json().catch(() => ({}));
//       if (!res.ok) throw new Error(data?.detail || "Password change failed");
//       setCurPass(""); setNewPass("");
//       alert("✅ Password changed");
//     } catch (e) {
//       alert(e.message || "Password change failed");
//     } finally { setChanging(false); }
//   }

//   if (loadingUser) {
//     return <div className="max-w-5xl mx-auto p-4"><div className="h-24 rounded-xl bg-gray-100 animate-pulse" /></div>;
//   }
//   if (err) {
//     return <div className="max-w-5xl mx-auto p-4"><div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">{err}</div></div>;
//   }

//   return (
//     <div className="max-w-5xl mx-auto p-4 grid gap-6 lg:grid-cols-2">
//       <section className="rounded-xl border bg-white p-5 shadow-sm">
//         <h2 className="font-semibold mb-4">Account</h2>
//         <dl className="grid grid-cols-3 gap-y-2 text-sm">
//           <dt className="text-gray-500">Username</dt><dd className="col-span-2">{user?.username}</dd>
//           <dt className="text-gray-500">Email</dt><dd className="col-span-2">{user?.email}</dd>
//           <dt className="text-gray-500">Email verified</dt><dd className="col-span-2">{user?.email_verified ? "Yes" : "No"}</dd>
//           <dt className="text-gray-500">2FA</dt><dd className="col-span-2">{user?.two_factor_enabled ? "Enabled" : "Disabled"}</dd>
//         </dl>
//       </section>

//       <section className="rounded-xl border bg-white p-5 shadow-sm">
//         <h2 className="font-semibold mb-3">Basic details</h2>
//         <form onSubmit={saveProfile} className="grid gap-3">
//           <div>
//             <label className="block text-sm mb-1">First name</label>
//             <input className="w-full rounded-lg border px-3 py-2" value={first} onChange={(e)=>setFirst(e.target.value)} />
//           </div>
//           <div>
//             <label className="block text-sm mb-1">Last name</label>
//             <input className="w-full rounded-lg border px-3 py-2" value={last} onChange={(e)=>setLast(e.target.value)} />
//           </div>
//           <button disabled={saving} className="rounded-md bg-black text-white py-2 disabled:opacity-50">
//             {saving ? "Saving…" : "Save changes"}
//           </button>
//         </form>
//       </section>

//       <section className="rounded-xl border bg-white p-5 shadow-sm lg:col-span-2">
//         <h2 className="font-semibold mb-3">Change password</h2>
//         <form onSubmit={changePassword} className="grid sm:grid-cols-3 gap-3">
//           <div className="sm:col-span-1">
//             <label className="block text-sm mb-1">Current password</label>
//             <input className="w-full rounded-lg border px-3 py-2" type="password" value={curPass} onChange={(e)=>setCurPass(e.target.value)} />
//           </div>
//           <div className="sm:col-span-1">
//             <label className="block text-sm mb-1">New password</label>
//             <input className="w-full rounded-lg border px-3 py-2" type="password" value={newPass} onChange={(e)=>setNewPass(e.target.value)} />
//           </div>
//           <div className="sm:col-span-1 flex items-end">
//             <button disabled={changing} className="w-full rounded-md bg-black text-white py-2 disabled:opacity-50">
//               {changing ? "Updating…" : "Update password"}
//             </button>
//           </div>
//         </form>
//       </section>
//     </div>
//   );
// }
