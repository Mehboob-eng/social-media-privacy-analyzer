// src/assets/pages/home.jsx
import { Link } from "react-router-dom";
import PF from "../../assets/PF.jpg"; // ✅ import asset (don’t use ../src/... in JSX)

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800/60 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto max-w-6xl h-16 px-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" aria-label="Privacy Checkup Home">
            <div className="h-9 w-9 rounded-xl bg-cyan-500/20 ring-1 ring-cyan-400/30 flex items-center justify-center">
              <img className="h-7 w-7 rounded-lg object-cover" src={PF} alt="Privacy Checkup logo" />
            </div>
            <span className="font-semibold text-base sm:text-lg">Privacy Checkup</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm text-slate-300" aria-label="Primary">
            <a href="#how" className="hover:text-slate-100">How it works</a>
            <a href="#trust" className="hover:text-slate-100">Trust & Security</a>
            <a href="#platforms" className="hover:text-slate-100">Platforms</a>
            <a href="#faq" className="hover:text-slate-100">FAQ</a>
          </nav>

          <div className="flex items-center gap-2">
            <Link to="/login" className="rounded-xl border border-slate-700 px-3 py-2 text-sm hover:bg-slate-900">
              Sign in
            </Link>
            <Link to="/signup" className="rounded-xl bg-cyan-500 px-3 py-2 text-sm text-slate-900 font-semibold hover:bg-cyan-400">
              Start checkup
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="relative">
          <div className="absolute -inset-20 bg-gradient-to-br from-cyan-500/10 via-fuchsia-500/10 to-emerald-400/10 blur-3xl pointer-events-none" />
          <div className="mx-auto max-w-6xl px-4 py-16 relative">
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/50 px-3 py-1 text-xs text-slate-300">
              Privacy • Security • Best Practices
            </span>
            <h1 className="mt-4 text-4xl sm:text-5xl font-extrabold tracking-tight">
              Privacy Checkup for your <span className="text-cyan-300">social accounts</span>
            </h1>
            <p className="mt-4 text-slate-300 text-lg max-w-2xl">
              We analyze your public profile signals and security settings to recommend actions that harden your accounts—2FA usage, password hygiene, visibility controls, and more.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/signup"
                className="rounded-xl bg-cyan-500 px-4 py-2 text-slate-900 text-sm font-semibold hover:bg-cyan-400"
              >
                Start checkup
              </Link>
              <Link
                to="/login"
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900"
              >
                I already have an account
              </Link>
            </div>

            {/* Consent banner */}
            <div className="mt-6 max-w-2xl rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-300">
              <strong className="text-slate-100">Consent first.</strong> We only access data you explicitly authorize.
              Password-based checks are optional; where possible we prefer official auth flows. Credentials (if supplied) are handled over HTTPS and stored encrypted or not stored at all, depending on your settings.
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="how" className="mx-auto max-w-6xl px-4 py-12 scroll-mt-20">
          <h2 className="text-2xl font-bold">How it works</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {[
              ["Connect", "Pick a platform and (optionally) provide credentials or use saved ones."],
              ["Analyze", "We fetch only what’s necessary, then run a privacy & security checklist."],
              ["Improve", "Get prioritized recommendations with clear steps and impact levels."],
            ].map(([t, d], i) => (
              <div key={t} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
                <div className="text-xs text-slate-400">Step {i + 1}</div>
                <div className="mt-1 font-semibold">{t}</div>
                <p className="mt-1 text-sm text-slate-300">{d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* TRUST & SECURITY */}
        <section id="trust" className="bg-slate-950/60 border-y border-slate-800/60 scroll-mt-20">
          <div className="mx-auto max-w-6xl px-4 py-12 grid gap-6 md:grid-cols-3">
            {[
              ["Minimal Access", "We request as little access as possible to run the check."],
              ["Encryption", "Transport is HTTPS; any stored secrets are encrypted at rest."],
              ["Transparency", "See exactly what we check and why each recommendation matters."],
            ].map(([t, d]) => (
              <div key={t} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
                <div className="font-semibold">{t}</div>
                <p className="mt-1 text-sm text-slate-300">{d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* PLATFORMS */}
        <section id="platforms" className="mx-auto max-w-6xl px-4 py-12 scroll-mt-20">
          <h2 className="text-2xl font-bold">Supported platforms</h2>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Instagram", "Brand & profile controls"],
              ["LinkedIn", "Visibility & connection safety"],
              ["Facebook", "Timeline & tagging privacy"],
              ["Threads", "Account & reply settings"],
            ].map(([name, desc]) => (
              <div key={name} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">
                <div className="font-semibold">{name}</div>
                <p className="mt-1 text-sm text-slate-300">{desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-6">
            <Link
              to="/signup"
              className="inline-flex rounded-xl bg-cyan-500 px-4 py-2 text-slate-900 text-sm font-semibold hover:bg-cyan-400"
            >
              Start checkup
            </Link>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="mx-auto max-w-3xl px-4 py-12 scroll-mt-20">
          <h2 className="text-2xl font-bold text-slate-100 text-center">FAQ</h2>
          <div className="mt-6 grid gap-3">
            {[
              [
                "Do you store my passwords?",
                "Where possible we use saved credentials or official flows. If you opt to enter a password, it’s transmitted over HTTPS and either ephemeral for the session or stored encrypted—based on your choice.",
              ],
              [
                "What do you check?",
                "Signal-based checks (public info), security settings (2FA, recovery), and profile hygiene. Each recommendation shows its impact level.",
              ],
              [
                "Can I delete my data?",
                "Yes. You can revoke access and delete your account any time from User Details.",
              ],
            ].map(([q, a]) => (
              <details key={q} className="group rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                <summary className="cursor-pointer list-none font-medium flex items-center justify-between">
                  {q}
                  <span className="text-slate-400 group-open:rotate-180 transition">⌄</span>
                </summary>
                <p className="mt-2 text-sm text-slate-300">{a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 py-8">
        <div className="mx-auto max-w-6xl px-4 flex items-center justify-between text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-xl bg-cyan-500/20 ring-1 ring-cyan-400/30 flex items-center justify-center">
              <img className="h-7 w-7 rounded-lg object-cover" src={PF} alt="Privacy Checkup logo" />
            </div>
            <span className="font-semibold text-slate-200">Privacy Checkup</span>
          </div>
          <span>© {new Date().getFullYear()} Privacy Checkup</span>
          <div className="hidden sm:flex gap-4">
            <a href="#how" className="hover:text-slate-200">How it works</a>
            <a href="#trust" className="hover:text-slate-200">Trust</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
