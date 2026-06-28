// src/assets/pages/dashboard.jsx
import React, { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../../config.js";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

// Register chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const API_ROOT = (API_BASE || "").replace(/\/auth\/?$/, "");

// IMPORTANT: keys must match backend normalize_host() return values
const platforms = [
  { key: "facebook", label: "Facebook", badge: "FB", gradient: "from-[#1877F2] to-[#0E5AC4]" },
  { key: "instagram", label: "Instagram", badge: "IG", gradient: "from-[#F58529] via-[#DD2A7B] to-[#8134AF]" },
  { key: "linkedin", label: "LinkedIn", badge: "IN", gradient: "from-[#0A66C2] to-[#004182]" },
  { key: "x", label: "X (Twitter)", badge: "X", gradient: "from-black to-slate-800" },
  { key: "other", label: "Other", badge: "OT", gradient: "from-slate-700 to-slate-900" },
];

function classNames(...arr) {
  return arr.filter(Boolean).join(" ");
}

const Check = (p) => (
  <svg viewBox="0 0 24 24" className={p.className || "h-4 w-4"} fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

const Shield = (p) => (
  <svg viewBox="0 0 24 24" className={p.className || "h-4 w-4"} fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 3l7 4v5c0 5-3.5 9-7 9s-7-4-7-9V7l7-4z" />
  </svg>
);

export default function Dashboard() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [globalErr, setGlobalErr] = useState("");

  const [selected, setSelected] = useState(null);
  const [platformData, setPlatformData] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [toast, setToast] = useState({ type: "", msg: "" });

  // Report window (minutes)
  const [minutes, setMinutes] = useState(10);

  const access = localStorage.getItem("access");

  // AbortController ref (prevents stale responses when clicking quickly)
  const abortRef = useRef(null);

  const guard401 = useCallback(
    (res) => {
      if (res.status === 401) {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        navigate("/login", { replace: true });
        return true;
      }
      return false;
    },
    [navigate]
  );

  // Cleanup pending request on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        if (!access) {
          navigate("/login", { replace: true });
          return;
        }

        const res = await fetch(`${API_ROOT}/user/me/`, {
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${access}`,
          },
        });

        if (guard401(res)) return;

        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data?.detail || data?.error || "Failed to load user");

        setUser(data);
      } catch (e) {
        setGlobalErr(e.message || "Error");
      } finally {
        setLoadingUser(false);
      }
    })();
  }, [access, guard401, navigate]);

  async function handleLogout() {
    try {
      const refresh = localStorage.getItem("refresh");
      await fetch(`${API_ROOT}/logout/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...(access ? { Authorization: `Bearer ${access}` } : {}),
        },
        body: JSON.stringify({ refresh }),
      }).catch(() => {});
    } finally {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      navigate("/login", { replace: true });
    }
  }

  function onSelectPlatform(key) {
    setSelected(key);
    fetchPlatformData(key, minutes);

    setToast({ type: "ok", msg: `${key.toUpperCase()} selected. Loading report...` });
    setTimeout(() => setToast({ type: "", msg: "" }), 2000);
  }

  const selectedObj = useMemo(() => platforms.find((p) => p.key === selected) || null, [selected]);

  async function fetchPlatformData(platformKey, windowMinutes) {
    // Cancel previous in-flight request (if any)
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setGraphLoading(true);
    setPlatformData(null);

    try {
      // NEW: Instant report endpoint
      const url = `${API_ROOT}/reports/instant-ai/?platform=${encodeURIComponent(platformKey)}&minutes=${minutes}`;

      const response = await fetch(url, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${access}`,
        },
        signal: controller.signal,
      });

      if (guard401(response)) return;

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data?.detail || data?.error || "Failed to load report");
      }

      setPlatformData(data);
    } catch (error) {
      // Abort is expected when user clicks another platform quickly
      if (error?.name === "AbortError") return;

      console.error("Error fetching report:", error);
      setToast({ type: "err", msg: error.message || "Failed to load report" });
      setTimeout(() => setToast({ type: "", msg: "" }), 2500);
    } finally {
      if (!controller.signal.aborted) setGraphLoading(false);
    }
  }

  function onChangeMinutes(e) {
    const v = Number(e.target.value || 10);
    setMinutes(v);

    // If platform already selected, refresh report immediately
    if (selected) fetchPlatformData(selected, v);
  }

  function renderGraphAndSummary() {
    if (!platformData) return null;

    const spam = platformData?.summary?.spam ?? 0;
    const nonSpam = platformData?.summary?.non_spam ?? 0;
    const total = platformData?.summary?.total ?? (spam + nonSpam);
    const accuracy = platformData?.summary?.accuracy ?? 0;

    const labels = platformData?.graph?.labels || [];
    const values = platformData?.graph?.values || [];

    const chartData = {
      labels,
      datasets: [
        {
          label: "Packets per minute",
          data: values,
          fill: false,
          tension: 0.25,
          pointRadius: 2,
        },
      ],
    };

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        title: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    };

    return (
  <div className="w-full">
    {/* Summary */}
    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
      <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
        <div className="text-xs text-slate-400">Spam</div>
        <div className="text-lg font-semibold">{spam}</div>
      </div>
      <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
        <div className="text-xs text-slate-400">Non-Spam</div>
        <div className="text-lg font-semibold">{nonSpam}</div>
      </div>
      <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
        <div className="text-xs text-slate-400">Total</div>
        <div className="text-lg font-semibold">{total}</div>
      </div>
      <div className="rounded-xl border border-slate-800/60 bg-slate-950/40 p-3">
        <div className="text-xs text-slate-400">Accuracy</div>
        <div className="text-lg font-semibold">{accuracy}%</div>
      </div>
    </div>

    {/* Graph */}
    <div className="h-80">
      <Line data={chartData} options={options} />
    </div>

    <div className="mt-3 text-xs text-slate-500">
      Window: last {platformData?.window_minutes ?? minutes} minutes
    </div>

    {/* AI Report (paste here) */}
    {platformData?.ai_report ? (
      <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-950/40 p-4">
        <div className="text-sm font-semibold mb-2">AI Generated Report</div>
        <p className="text-sm text-slate-300 whitespace-pre-line">{platformData.ai_report}</p>
      </div>
    ) : null}
  </div>
);

    
  }

  if (loadingUser) {
    return (
      <div className="min-h-screen bg-slate-950">
        <div className="max-w-6xl mx-auto p-6 grid gap-4">
          <div className="h-24 rounded-2xl bg-slate-800/40 animate-pulse" />
          <div className="h-56 rounded-2xl bg-slate-800/40 animate-pulse" />
        </div>
      </div>
    );
  }

  if (globalErr) {
    return (
      <div className="min-h-screen bg-slate-950">
        <div className="max-w-2xl mx-auto p-6">
          <div className="rounded-xl border border-rose-500/30 bg-rose-950/40 text-rose-100 px-4 py-3">
            {globalErr}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(1200px_500px_at_50%_-100px,rgba(59,130,246,0.18),transparent_60%)] bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-800/60 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 h-16 grid grid-cols-[1fr_auto] items-center gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 rounded-xl bg-slate-900 ring-1 ring-slate-700 flex items-center justify-center text-xs font-bold shrink-0">
              {user?.username?.slice(0, 2)?.toUpperCase() || "U"}
            </div>
            <div className="leading-tight min-w-0">
              <div className="font-semibold truncate">Hi, {user?.username}</div>
              <div className="text-xs text-slate-400 truncate">{user?.email || "Welcome back"}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span
              className={classNames(
                "rounded-full px-2 py-0.5 text-xs border hidden sm:inline",
                user?.email_verified ? "border-emerald-400/40 text-emerald-200" : "border-amber-400/40 text-amber-200"
              )}
            >
              {user?.email_verified ? "Email verified" : "Email not verified"}
            </span>

            <span
              className={classNames(
                "rounded-full px-2 py-0.5 text-xs border hidden sm:inline",
                user?.two_factor_enabled ? "border-emerald-400/40 text-emerald-200" : "border-slate-600 text-slate-300"
              )}
            >
              {user?.two_factor_enabled ? "2FA ON" : "2FA OFF"}
            </span>

            <button onClick={() => navigate("/profile")} className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-900">
              Profile
            </button>

            <button onClick={handleLogout} className="rounded-lg bg-slate-100 text-slate-900 px-3 py-1.5 text-sm font-semibold hover:bg-white">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="hidden lg:block">
          <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 backdrop-blur p-5 sticky top-20 space-y-5">
            <div className="text-xs uppercase tracking-wider text-slate-400/80">Platforms</div>

            <div className="grid gap-2">
              {platforms.map((p) => {
                const active = selected === p.key;
                return (
                  <button
                    key={p.key}
                    onClick={() => onSelectPlatform(p.key)}
                    className={classNames(
                      "w-full flex items-center gap-3 rounded-xl px-3 py-2 text-sm border transition",
                      active
                        ? "bg-slate-900/70 border-cyan-400/30 ring-1 ring-cyan-400/20"
                        : "bg-slate-900/30 border-slate-800/60 hover:bg-slate-900/50"
                    )}
                  >
                    <span
                      className={classNames(
                        "inline-flex h-8 w-8 items-center justify-center rounded-lg text-[11px] font-semibold",
                        `bg-gradient-to-br ${p.gradient}`
                      )}
                    >
                      {p.badge}
                    </span>
                    <div className="flex-1 text-left">{p.label}</div>
                    {active && <Check className="h-4 w-4 text-cyan-300" />}
                  </button>
                );
              })}
            </div>

            <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3">
              <div className="flex items-center gap-2 text-sm">
                <Shield className="h-4 w-4 text-slate-300" />
                <span className="font-medium">Heads up</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Platform select → Instant report API → summary + time graph (no report saved).
              </p>
            </div>
          </div>
        </aside>

        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-800/60 bg-gradient-to-br from-slate-900/60 to-slate-900/30 p-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <h1 className="text-xl font-bold">Profile Checker</h1>
                <p className="text-sm text-slate-400">
                  Select a platform to load an instant report and graph from your packet events.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs text-slate-400">Window</label>
                <select
                  value={minutes}
                  onChange={onChangeMinutes}
                  className="rounded-lg border border-slate-700 bg-slate-950/40 px-2 py-1 text-sm text-slate-200"
                >
                  <option value={5}>Last 5 min</option>
                  <option value={10}>Last 10 min</option>
                  <option value={30}>Last 30 min</option>
                  <option value={60}>Last 60 min</option>
                </select>
              </div>
            </div>
          </div>

          <div className="lg:hidden grid grid-cols-2 sm:grid-cols-5 gap-3">
            {platforms.map((p) => {
              const active = selected === p.key;
              return (
                <button
                  key={p.key}
                  onClick={() => onSelectPlatform(p.key)}
                  className={classNames(
                    "rounded-xl p-3 border text-sm",
                    active ? "bg-slate-900/70 border-cyan-400/30 ring-1 ring-cyan-400/20" : "bg-slate-900/30 border-slate-800/60"
                  )}
                >
                  <div
                    className={classNames(
                      "h-9 w-9 rounded-lg mx-auto mb-2 flex items-center justify-center text-[11px] font-semibold",
                      `bg-gradient-to-br ${p.gradient}`
                    )}
                  >
                    {p.badge}
                  </div>
                  <div className="text-center">{p.label}</div>
                </button>
              );
            })}
          </div>

          <div className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="text-sm font-semibold">
                  {selectedObj ? `${selectedObj.label} Report` : "Select a platform"}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {selectedObj ? `Instant report (last ${minutes} minutes) based on PacketEvent logs.` : "Use the buttons to pick a platform."}
                </p>
              </div>
            </div>

            <div className="mt-5 rounded-xl border border-slate-800/60 bg-slate-950/40 p-4">
              {graphLoading ? "Loading data..." : renderGraphAndSummary()}
              {!graphLoading && !platformData && selectedObj ? (
                <div className="text-xs text-slate-500">No data yet. Send some packets first.</div>
              ) : null}
            </div>
          </div>

          {toast.msg && (
            <div
              className={classNames(
                "rounded-xl px-3 py-2 text-sm border",
                toast.type === "ok" && "border-emerald-400/30 bg-emerald-900/20 text-emerald-200",
                toast.type === "err" && "border-rose-400/30 bg-rose-900/20 text-rose-200",
                toast.type === "warn" && "border-amber-400/30 bg-amber-900/20 text-amber-200"
              )}
            >
              {toast.msg}
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-slate-800/60 py-6">
        <div className="mx-auto max-w-7xl px-4 text-sm text-slate-400 flex items-center justify-between">
          <span>© {new Date().getFullYear()} SMP</span>
          <div className="hidden sm:flex gap-4">
            <button onClick={() => navigate("/profile")} className="hover:text-slate-200">
              Profile
            </button>
            <button onClick={handleLogout} className="hover:text-slate-200">
              Logout
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
