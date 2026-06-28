// src/assets/pages/login.jsx
import { API_BASE } from "../../config.js";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  // 1 = credentials, 2 = 2FA OTP
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [identity, setIdentity] = useState(""); // email or username
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);

  // NEW: remember me (UI + simple identity restore)
  const [remember, setRemember] = useState(false);

  const [otp, setOtp] = useState("");
  const [loginId, setLoginId] = useState(null);
  const [masked, setMasked] = useState("");

  // cooldown (refresh safe)
  const [cooldown, setCooldown] = useState(0);

  // Prefill from localStorage if previously remembered
  useEffect(() => {
    const rememberedIdentity = localStorage.getItem("remember_identity");
    if (rememberedIdentity) {
      setIdentity(rememberedIdentity);
      setRemember(true);
    }

    const id = sessionStorage.getItem("login_2fa_id");
    const em = sessionStorage.getItem("login_identity");
    const until = Number(sessionStorage.getItem("login_cooldown_until") || 0);
    const pwd = sessionStorage.getItem("login_password");
    if (until > Date.now()) setCooldown(Math.ceil((until - Date.now()) / 1000));
    if (id) {
      setLoginId(Number(id));
      setMasked(em && em.includes("@") ? maskEmail(em) : "");
      setStep(2);
      if (!password && pwd) setPassword(pwd); // to allow resend without asking again
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const startCooldown = (sec = 45) => {
    const until = Date.now() + sec * 1000;
    sessionStorage.setItem("login_cooldown_until", String(until));
    setCooldown(sec);
  };

  function maskEmail(email) {
    if (!email || !email.includes("@")) return "";
    const [n, d] = email.split("@");
    const visible = n.slice(0, 2);
    return `${visible}${"*".repeat(Math.max(0, n.length - 2))}@${d}`;
  }
  async function parseJSON(res) { try { return await res.json(); } catch { return {}; } }

  async function handleLogin(e) {
    e.preventDefault();
    setError(""); setInfo("");
    if (!identity.trim()) return setError("Enter email or username");
    if (!password) return setError("Enter password");

    setLoading(true);
    try {
      // store/remove identity if remember me
      if (remember) localStorage.setItem("remember_identity", identity.trim());
      else localStorage.removeItem("remember_identity");

      const res = await fetch(`${API_BASE}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: identity.trim(), password }),
      });
      const data = await parseJSON(res);

      if (!res.ok) throw new Error(data?.detail || data?.error || "Invalid credentials");

      if (data?.token?.access) {
        localStorage.setItem("access", data.token.access);
        if (data.token.refresh) localStorage.setItem("refresh", data.token.refresh);
        navigate("/dashboard", { replace: true });
        return;
      }

      if ((data?.id || data?.Id) && data?.OTP_SENT) {
        const twoId = data.id || data.Id;
        setLoginId(twoId);
        setMasked(identity.includes("@") ? maskEmail(identity) : "");
        sessionStorage.setItem("login_2fa_id", String(twoId));
        sessionStorage.setItem("login_identity", identity);
        sessionStorage.setItem("login_password", password); // for resend
        startCooldown(45);
        setStep(2);
        return;
      }

      throw new Error("Unexpected response");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally { setLoading(false); }
  }

  async function handleVerify2FA(e) {
    e.preventDefault();
    setError(""); setInfo("");
    if (otp.length !== 6) return setError("Enter 6-digit code");

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/verify/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ id: loginId, otp }),
      });
      const data = await parseJSON(res);

      if (!res.ok) throw new Error(data?.detail || data?.error || "OTP verification failed");

      const token = data?.token || data;
      if (!token?.access) throw new Error("No tokens received");

      localStorage.setItem("access", token.access);
      if (token.refresh) localStorage.setItem("refresh", token.refresh);

      sessionStorage.removeItem("login_2fa_id");
      sessionStorage.removeItem("login_identity");
      sessionStorage.removeItem("login_password");
      sessionStorage.removeItem("login_cooldown_until");

      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally { setLoading(false); }
  }

  async function resend2FAOtp() {
    if (cooldown > 0 || loading) return;
    setError(""); setInfo("");
    const user = sessionStorage.getItem("login_identity");
    const pwd = sessionStorage.getItem("login_password");
    if (!user || !pwd) { setError("Cannot resend without credentials. Please sign in again."); return; }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ username: user, password: pwd }),
      });
      const data = await parseJSON(res);
      if (!res.ok) throw new Error(data?.detail || data?.error || "Resend failed");
      if ((data?.id || data?.Id) && data?.OTP_SENT) {
        const twoId = data.id || data.Id;
        setLoginId(twoId);
        sessionStorage.setItem("login_2fa_id", String(twoId));
        startCooldown(45);
        setInfo("OTP resent. Please check your email.");
      } else if (data?.token?.access) {
        // some backends might disable 2FA mid-flow; log user in
        localStorage.setItem("access", data.token.access);
        if (data.token.refresh) localStorage.setItem("refresh", data.token.refresh);
        navigate("/app", { replace: true });
      } else {
        throw new Error("OTP not sent");
      }
    } catch (e) {
      setError(e.message || "Resend failed");
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 py-10 sm:py-14">
      {/* BG glow */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 -left-32 h-72 w-72 rounded-full bg-indigo-300/25 blur-3xl" />
        <div className="absolute -bottom-40 -right-20 h-72 w-72 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
      </div>

      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8 mt-2">
          <a
            href="/"
            className="mx-auto mb-4 h-12 w-12 rounded-2xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-emerald-500 shadow-lg shadow-indigo-500/20 flex items-center justify-center"
            aria-label="Home"
          >
            {/* Shield/check icon */}
            <svg viewBox="0 0 24 24" className="h-7 w-7 text-white" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 3l7 3v5a9 9 0 11-14 0V6l7-3z" />
              <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Sign in</h1>
          <p className="mt-2 text-sm text-slate-600">Welcome back</p>
        </div>

        {/* Stepper */}
        <div className="mb-5 flex items-center justify-center gap-3 text-xs">
          <StepDot active={step === 1} label="Login" />
          <div className="h-px w-10 bg-slate-300" />
          <StepDot active={step === 2} label="2FA" />
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur p-6 sm:p-8 shadow-xl">
          {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
          {info && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{info}</div>}

          {step === 1 ? (
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700">Email or Username</label>
                <input
                  className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  value={identity} onChange={(e) => setIdentity(e.target.value)} required
                  placeholder="you@example.com or yourusername"
                  autoComplete="username"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Password</label>
                <div className="mt-2 relative">
                  <input
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    type={showPwd ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required
                    placeholder="••••••••"
                    autoComplete="current-password"
                  />
                  <button type="button" onClick={() => setShowPwd((s) => !s)} className="absolute inset-y-0 right-2 my-auto h-9 px-3 rounded-lg text-sm text-slate-600 hover:bg-slate-100">
                    {showPwd ? "Hide" : "Show"}
                  </button>
                </div>

                {/* Remember me row */}
                <div className="mt-3 flex items-center justify-between">
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600 select-none">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                      checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                    />
                    Remember me
                  </label>

                  <button
                    type="button"
                    onClick={() => navigate("/PasswordReset")}
                    className="text-sm text-indigo-700 hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-gradient-to-r from-indigo-600 via-cyan-500 to-emerald-500 px-4 py-2.5 font-semibold text-white shadow-md hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerify2FA} className="space-y-5">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-slate-900">Two-factor verification</h2>
                <p className="text-sm text-slate-600 mt-1">
                  Enter the 6-digit code {masked ? <>sent to <span className="font-medium">{masked}</span></> : "we sent you"}.
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

              <div className="flex items-center justify-between">
                <button type="submit" disabled={loading} className="rounded-2xl bg-emerald-600 px-4 py-2.5 font-semibold text-white shadow-md hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-600 disabled:opacity-60">
                  {loading ? "Verifying..." : "Verify & continue"}
                </button>
                <button
                  type="button"
                  onClick={resend2FAOtp}
                  disabled={loading || cooldown > 0}
                  className="text-sm text-indigo-700 hover:underline disabled:opacity-50"
                >
                  {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="mt-8 text-center text-sm text-slate-600">
          New here?{" "}
          <button type="button" onClick={() => navigate("/signup")} className="font-semibold text-indigo-700 hover:underline">
            Create account
          </button>
        </p>
      </div>
    </div>
  );
}

function StepDot({ active, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${active ? "bg-indigo-600" : "bg-slate-300"}`} aria-hidden />
      <span className={`text-slate-600 ${active ? "font-medium text-slate-900" : ""}`}>{label}</span>
    </div>
  );
}
