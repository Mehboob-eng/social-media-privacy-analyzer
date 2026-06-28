// src/assets/pages/PasswordReset.jsx
import { API_BASE } from "../../config.js";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function PasswordReset() {
  const navigate = useNavigate();

  // 1 = request OTP, 2 = confirm with OTP + new pass
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [identity, setIdentity] = useState(""); // email or username
  const [resetId, setResetId] = useState(null);
  const [masked, setMasked] = useState("");

  const [otp, setOtp] = useState("");
  const [pass, setPass] = useState("");
  const [confirm, setConfirm] = useState("");

  // 🔁 separate toggles for both fields
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // cooldown (refresh safe)
  const [cooldown, setCooldown] = useState(0);
  useEffect(() => {
    const id = sessionStorage.getItem("reset_id");
    const em = sessionStorage.getItem("reset_email_masked");
    const until = Number(sessionStorage.getItem("reset_cooldown_until") || 0);
    const un = sessionStorage.getItem("reset_username");
    if (until > Date.now()) setCooldown(Math.ceil((until - Date.now()) / 1000));
    if (id) { setResetId(Number(id)); setMasked(em || ""); setStep(2); }
    if (!identity && un) setIdentity(un);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);
  const startCooldown = (sec = 45) => {
    const until = Date.now() + sec * 1000;
    sessionStorage.setItem("reset_cooldown_until", String(until));
    setCooldown(sec);
  };

  function maskEmail(email) {
    if (!email || !email.includes("@")) return "your email";
    const [n, d] = email.split("@");
    const visible = n.slice(0, 2);
    return `${visible}${"*".repeat(Math.max(0, n.length - 2))}@${d}`;
  }
  async function parseJSON(res) { try { return await res.json(); } catch { return {}; } }

  async function handleRequest(e) {
    e.preventDefault();
    setError(""); setInfo("");
    if (!identity.trim()) return setError("Enter email or username");

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reset_password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: identity.trim() }),
      });
      const data = await parseJSON(res);

      if (!res.ok) throw new Error(data?.detail || data?.error || "User not found");

      if (data?.id && data?.OTP_SENT) {
        setResetId(data.id);
        const m = data?.email || (identity.includes("@") ? maskEmail(identity) : "your email");
        setMasked(m);
        sessionStorage.setItem("reset_id", String(data.id));
        sessionStorage.setItem("reset_email_masked", m);
        sessionStorage.setItem("reset_username", identity.trim());
        startCooldown(45);
        setStep(2);
      } else {
        throw new Error("OTP not sent");
      }
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally { setLoading(false); }
  }

  async function handleConfirm(e) {
    e.preventDefault();
    setError(""); setInfo("");

    if (otp.length !== 6) return setError("Enter 6-digit code");
    if (pass.length < 8) return setError("Password must be at least 8 characters");
    if (pass !== confirm) return setError("Passwords do not match");

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/verify/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ id: resetId, otp, password: pass }),
      });
      const data = await parseJSON(res);

      if (!res.ok) throw new Error(data?.detail || data?.error || "Reset failed");

      alert("✅ Password changed. Please login.");
      sessionStorage.removeItem("reset_id");
      sessionStorage.removeItem("reset_email_masked");
      sessionStorage.removeItem("reset_username");
      sessionStorage.removeItem("reset_cooldown_until");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally { setLoading(false); }
  }

  async function resendResetOtp() {
    if (cooldown > 0 || loading) return;
    setError(""); setInfo("");
    const user = sessionStorage.getItem("reset_username") || identity.trim();
    if (!user) { setError("Cannot resend without username/email. Start again."); return; }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reset_password/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: user }),
      });
      const data = await parseJSON(res);
      if (!res.ok) throw new Error(data?.detail || data?.error || "Resend failed");

      if (data?.id && data?.OTP_SENT) {
        setResetId(data.id);
        sessionStorage.setItem("reset_id", String(data.id));
        const m = data?.email || (user.includes("@") ? maskEmail(user) : "your email");
        setMasked(m);
        sessionStorage.setItem("reset_email_masked", m);
        startCooldown(45);
        setInfo("OTP resent. Please check your email.");
      } else {
        throw new Error("OTP not sent");
      }
    } catch (e) {
      setError(e.message || "Resend failed");
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 py-10 sm:py-14">
      {/* ===== background ===== */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 -left-32 h-72 w-72 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute -bottom-40 -right-20 h-72 w-72 rounded-full bg-indigo-300/25 blur-3xl" />
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
      </div>

      <div className="w-full max-w-md">
        {/* ===== brand (logo + title) ===== */}
        <div className="text-center mb-6">
          <a
            href="/"
            className="mx-auto mb-4 h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-emerald-500 shadow-lg shadow-indigo-500/20 flex items-center justify-center"
            aria-label="Home"
          >
            {/* checkmark logo (vector) */}
            <svg viewBox="0 0 24 24" className="h-7 w-7 text-white" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="12" cy="12" r="9.2" className="opacity-70" />
              <path d="M8 12.5l2.5 2.5L16 9.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Reset your password</h1>
          <p className="mt-1 text-slate-600 text-sm">We’ll send a 6-digit code to verify it’s you.</p>
        </div>

        {/* ===== stepper ===== */}
        <div className="mb-5 flex items-center justify-center gap-3 text-xs">
          <StepDot active={step === 1} label="Request" />
          <div className="h-px w-10 bg-slate-300" />
          <StepDot active={step === 2} label="Confirm" />
        </div>

        {/* ===== card ===== */}
        <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur p-6 sm:p-7 shadow-xl shadow-slate-900/5">
          {error && (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          {info && (
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
              {info}
            </div>
          )}

          {step === 1 ? (
            <form onSubmit={handleRequest} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700">Email or Username</label>
                <input
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  value={identity} onChange={(e) => setIdentity(e.target.value)} required
                  placeholder="you@example.com or yourusername"
                  autoComplete="username"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-gradient-to-r from-indigo-600 via-cyan-500 to-emerald-500 px-4 py-2.5 font-semibold text-white shadow-md hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
              >
                {loading ? "Sending..." : "Send reset code"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleConfirm} className="space-y-5">
              <div className="text-center">
                <p className="text-sm text-slate-600">
                  Enter the code sent to <span className="font-medium">{masked || "your email"}</span>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">6-digit OTP</label>
                <input
                  inputMode="numeric" pattern="\d*" maxLength="6"
                  value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))} required
                  className="mt-2 block w-full text-center tracking-[0.35em] rounded-xl border border-slate-300 bg-white px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  placeholder="••••••"
                  autoComplete="one-time-code"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">New password</label>
                <div className="mt-2 relative">
                  <input
                    type={showNew ? "text" : "password"} value={pass} onChange={(e) => setPass(e.target.value)} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="••••••••"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew((s) => !s)}
                    className="absolute inset-y-0 right-2 my-auto h-9 px-3 rounded-lg text-sm text-slate-600 hover:bg-slate-100"
                  >
                    {showNew ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Confirm password</label>
                <div className="mt-2 relative">
                  <input
                    type={showConfirm ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="••••••••"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((s) => !s)}
                    className="absolute inset-y-0 right-2 my-auto h-9 px-3 rounded-lg text-sm text-slate-600 hover:bg-slate-100"
                  >
                    {showConfirm ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-2xl bg-emerald-600 px-4 py-2.5 font-semibold text-white shadow-md hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:opacity-60"
                >
                  {loading ? "Updating..." : "Set new password"}
                </button>
                <button
                  type="button"
                  onClick={resendResetOtp}
                  disabled={loading || cooldown > 0}
                  className="text-sm text-indigo-700 hover:underline disabled:opacity-50"
                >
                  {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
                </button>
              </div>

              <p className="text-xs text-slate-500 text-center">
                Remembered your password?{" "}
                <button type="button" onClick={() => navigate("/login")} className="font-medium underline">Login</button>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function StepDot({ active, label }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`h-2.5 w-2.5 rounded-full transition-colors ${active ? "bg-indigo-600" : "bg-slate-300"}`}
        aria-hidden
      />
      <span className={`text-slate-600 ${active ? "font-medium text-slate-900" : ""}`}>{label}</span>
    </div>
  );
}
