// src/assets/pages/signup.jsx
import { API_BASE } from "../../config.js";
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Signup() {
  const navigate = useNavigate();

  // 1 = Register, 2 = OTP
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [showPwd, setShowPwd] = useState(false);
  const [showPwd2, setShowPwd2] = useState(false);

  const [otp, setOtp] = useState("");
  const [userId, setUserId] = useState(null);

  const [fieldErr, setFieldErr] = useState({ email: "", username: "", password: "" });

  // resend cooldown (refresh safe)
  const [cooldown, setCooldown] = useState(0);
  useEffect(() => {
    const savedId = sessionStorage.getItem("reg_id");
    const savedEmail = sessionStorage.getItem("reg_email");
    const until = Number(sessionStorage.getItem("reg_cooldown_until") || 0);
    const now = Date.now();
    if (until > now) setCooldown(Math.ceil((until - now) / 1000));
    if (savedId) {
      setUserId(Number(savedId));
      setStep(2);
      if (savedEmail) setForm((f) => ({ ...f, email: savedEmail }));
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
    sessionStorage.setItem("reg_cooldown_until", String(until));
    setCooldown(sec);
  };

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  function maskEmail(email) {
    if (!email || !email.includes("@")) return "your email";
    const [name, domain] = email.split("@");
    const visible = name.slice(0, 2);
    return `${visible}${"*".repeat(Math.max(0, name.length - 2))}@${domain}`;
  }
  async function parseJSON(res) { try { return await res.json(); } catch { return {}; } }

  async function handleRegister(e) {
    e.preventDefault();
    setError(""); setInfo(""); setFieldErr({ email: "", username: "", password: "" });

    if (!/^\S+@\S+\.\S+$/.test(form.email)) return setError("Invalid email format");
    if (!form.username.trim()) return setError("Username is required");
    if (form.password.length < 8) return setError("Password must be at least 8 characters");
    if (form.password !== form.confirmPassword) return setError("Passwords do not match");

    setLoading(true);
    try {
      const payload = {
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      };
      const res = await fetch(`${API_BASE}/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await parseJSON(res);

      if (!res.ok) {
        setFieldErr({
          email: data.email || "",
          username: data.username || "",
          password: data.password || "",
        });
        throw new Error(data.detail || data.error || "Registration failed");
      }

      if (data?.OTP_SENT && data?.id) {
        setUserId(data.id);
        // store for refresh + resend (password kept only in sessionStorage)
        sessionStorage.setItem("reg_id", String(data.id));
        sessionStorage.setItem("reg_email", form.email);
        sessionStorage.setItem("reg_payload", JSON.stringify(payload));
        startCooldown(45);
        setStep(2);
      } else {
        throw new Error("OTP not sent");
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally { setLoading(false); }
  }

  async function handleVerifyOtp(e) {
    e.preventDefault();
    setError(""); setInfo("");
    if (otp.length !== 6) return setError("Enter 6-digit code");

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/verify/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ id: userId, otp }),
      });
      const data = await parseJSON(res);

      if (!res.ok) throw new Error(data?.detail || data?.error || "OTP verification failed");

      alert(`✅ Registration complete! ${data?.message || ""}`);
      sessionStorage.removeItem("reg_id");
      sessionStorage.removeItem("reg_email");
      sessionStorage.removeItem("reg_payload");
      sessionStorage.removeItem("reg_cooldown_until");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally { setLoading(false); }
  }

  async function resendSignupOtp() {
    if (cooldown > 0 || loading) return;
    setError(""); setInfo("");
    const payloadStr = sessionStorage.getItem("reg_payload");
    const payload = payloadStr ? JSON.parse(payloadStr) : null;
    if (!payload?.password) {
      setError("Cannot resend without registration details. Go back and register again.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await parseJSON(res);
      if (!res.ok) throw new Error(data?.detail || data?.error || "Resend failed");

      if (data?.OTP_SENT && data?.id) {
        setUserId(data.id);
        sessionStorage.setItem("reg_id", String(data.id));
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
      {/* BG glow */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 -left-32 h-72 w-72 rounded-full bg-indigo-300/25 blur-3xl" />
        <div className="absolute -bottom-40 -right-24 h-72 w-72 rounded-full bg-cyan-300/25 blur-3xl" />
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
            {/* shield + spark icon */}
            <svg viewBox="0 0 24 24" className="h-7 w-7 text-white" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 3l7 3v5a9 9 0 11-14 0V6l7-3z" />
              <path d="M12 7v5" strokeLinecap="round" />
              <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Create your account</h1>
          <p className="mt-2 text-sm text-slate-600">It takes less than a minute</p>
        </div>

        {/* Stepper */}
        <div className="mb-5 flex items-center justify-center gap-3 text-xs">
          <StepDot active={step === 1} label="Register" />
          <div className="h-px w-10 bg-slate-300" />
          <StepDot active={step === 2} label="Verify OTP" />
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur p-6 sm:p-8 shadow-xl">
          {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
          {info && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{info}</div>}

          {step === 1 ? (
            <form onSubmit={handleRegister} className="space-y-5">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Email</label>
                <div className="mt-2 relative">
                  <input
                    name="email" type="email" value={form.email} onChange={handleChange} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pl-11 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                  <span className="pointer-events-none absolute inset-y-0 left-3 my-auto text-slate-400">✉️</span>
                </div>
                {fieldErr.email && <p className="mt-1 text-sm text-rose-600">{fieldErr.email}</p>}
              </div>

              {/* Username */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Username</label>
                <div className="mt-2 relative">
                  <input
                    name="username" value={form.username} onChange={handleChange} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pl-11 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="yourusername"
                    autoComplete="username"
                  />
                  <span className="pointer-events-none absolute inset-y-0 left-3 my-auto text-slate-400">👤</span>
                </div>
                {fieldErr.username && <p className="mt-1 text-sm text-rose-600">{fieldErr.username}</p>}
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Password</label>
                <div className="mt-2 relative">
                  <input
                    name="password" type={showPwd ? "text" : "password"} value={form.password} onChange={handleChange} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pl-11 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="••••••••"
                    autoComplete="new-password"
                  />
                  <span className="pointer-events-none absolute inset-y-0 left-3 my-auto text-slate-400">🔒</span>
                  <button type="button" onClick={() => setShowPwd((s) => !s)} className="absolute inset-y-0 right-2 my-auto h-9 px-3 rounded-lg text-sm text-slate-600 hover:bg-slate-100">
                    {showPwd ? "Hide" : "Show"}
                  </button>
                </div>
                {fieldErr.password && <p className="mt-1 text-sm text-rose-600">{fieldErr.password}</p>}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-slate-700">Re-enter Password</label>
                <div className="mt-2 relative">
                  <input
                    name="confirmPassword" type={showPwd2 ? "text" : "password"} value={form.confirmPassword} onChange={handleChange} required
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 pl-11 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    placeholder="••••••••"
                    autoComplete="new-password"
                  />
                  <span className="pointer-events-none absolute inset-y-0 left-3 my-auto text-slate-400">🔒</span>
                  <button type="button" onClick={() => setShowPwd2((s) => !s)} className="absolute inset-y-0 right-2 my-auto h-9 px-3 rounded-lg text-sm text-slate-600 hover:bg-slate-100">
                    {showPwd2 ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-gradient-to-r from-indigo-600 via-cyan-500 to-emerald-500 px-4 py-2.5 font-semibold text-white shadow-md hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-60"
              >
                {loading ? "Registering..." : "Register"}
              </button>

              <p className="text-xs text-slate-500">
                You’ll receive a 6-digit OTP at <span className="font-medium">{maskEmail(form.email)}</span>.
              </p>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-5">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-slate-900">Verify OTP</h2>
                <p className="text-sm text-slate-600 mt-1">
                  Enter the 6-digit code sent to <span className="font-medium">{maskEmail(form.email)}</span>
                </p>
              </div>

              <div className="mt-2">
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
                  {loading ? "Verifying..." : "Verify OTP"}
                </button>
                <button
                  type="button"
                  onClick={resendSignupOtp}
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
          Already have an account?{" "}
          <button type="button" onClick={() => navigate("/login")} className="font-semibold text-indigo-700 hover:underline">
            Log in
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
