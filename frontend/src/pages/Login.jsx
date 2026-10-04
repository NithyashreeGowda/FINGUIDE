import { useEffect, useState } from "react";
import { Eye, EyeOff, Bell, TrendingUp } from "lucide-react";
import { BarChart, Bar, ResponsiveContainer } from "recharts";
import {
  forgotPassword,
  login,
  resendOtp,
  resetPassword,
  signup,
  verifySignup,
} from "../api";

const miniChartData = [
  { v: 40 }, { v: 65 }, { v: 50 }, { v: 80 }, { v: 60 }, { v: 90 }, { v: 70 },
];

export default function Login({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [view, setView] = useState("form"); // "form" | "otp" | "forgot" | "reset"
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [shake, setShake] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // countdown for "Resend code"
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const triggerError = (msg) => {
    setError(msg);
    setInfo("");
    setShake(true);
    setTimeout(() => setShake(false), 400);
  };

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const goTo = (next) => {
    setView(next);
    setCode("");
    setError("");
    setInfo("");
  };

  const backToLogin = () => {
    setMode("login");
    goTo("form");
  };

  const run = async (fn) => {
    setError("");
    setSubmitting(true);
    try {
      await fn();
    } catch (err) {
      triggerError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { name, email, password, confirmPassword } = formData;
    const cleanEmail = email.trim();

    // --- enter the code to finish creating the account ---
    if (view === "otp") {
      if (code.length !== 6) return triggerError("Enter the 6-digit code.");
      return run(async () => onAuth(await verifySignup({ email: cleanEmail, code })));
    }

    // --- forgot password: ask for the email, send a code ---
    if (view === "forgot") {
      if (!cleanEmail) return triggerError("Please enter your email.");
      return run(async () => {
        await forgotPassword({ email: cleanEmail });
        setCode("");
        setInfo("If that email has an account, we've sent a code to it.");
        setCooldown(30);
        setView("reset");
      });
    }

    // --- reset password: code + new password ---
    if (view === "reset") {
      if (code.length !== 6) return triggerError("Enter the 6-digit code.");
      if (password.length < 8) return triggerError("Password must be at least 8 characters.");
      if (password !== confirmPassword) return triggerError("Passwords do not match.");
      return run(async () => {
        await resetPassword({ email: cleanEmail, code, new_password: password });
        setFormData((prev) => ({ ...prev, password: "", confirmPassword: "" }));
        setMode("login");
        setView("form");
        setCode("");
        setInfo("Password updated. Please log in.");
      });
    }

    // --- create account: validate, then email a code ---
    if (mode === "signup") {
      if (!name || !email || !password || !confirmPassword) return triggerError("Please fill in all fields.");
      if (password.length < 8) return triggerError("Password must be at least 8 characters.");
      if (password !== confirmPassword) return triggerError("Passwords do not match.");
      return run(async () => {
        await signup({ name: name.trim(), email: cleanEmail, password });
        setCode("");
        setInfo(`We sent a 6-digit code to ${cleanEmail}.`);
        setCooldown(30);
        setView("otp");
      });
    }

    // --- login ---
    if (!email || !password) return triggerError("Please fill in all fields.");
    run(async () => onAuth(await login({ username: cleanEmail, password })));
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    try {
      await resendOtp({
        email: formData.email.trim(),
        purpose: view === "otp" ? "signup" : "reset",
      });
      setError("");
      setInfo("A new code has been sent.");
      setCooldown(30);
    } catch (err) {
      triggerError(err.message);
    }
  };

  const shownEmail = formData.email.trim();

  const title =
    view === "otp" ? "Verify your email"
    : view === "forgot" ? "Forgot password?"
    : view === "reset" ? "Reset password"
    : mode === "login" ? "Welcome back"
    : "Create your account";

  const subtitle =
    view === "otp" ? `We sent a 6-digit code to ${shownEmail}. Enter it below to finish creating your account.`
    : view === "forgot" ? "Enter your email and we'll send you a code to reset your password."
    : view === "reset" ? `Enter the code sent to ${shownEmail} and choose a new password.`
    : mode === "login" ? "Understand your finances confidently, wherever you are, whenever you need to."
    : "Set up your FinGuide account to get personalized financial insights.";

  const submitLabel =
    view === "otp" ? "Verify & Create Account"
    : view === "forgot" ? "Send Code"
    : view === "reset" ? "Reset Password"
    : mode === "login" ? "Login"
    : "Create Account";

  return (
    <div className="mb-page">
      <div className="mb-outer-card">

        {/* LEFT PANEL — AUTH FORM */}
        <div className="mb-left">
          <div className="mb-logo-row">
            <div className="mb-logo-mark">F</div>
            <div>
              <div className="mb-logo-name">FinGuide</div>
              <div className="mb-logo-sub">financial assistant</div>
            </div>
          </div>

          {view === "form" && (
            <div className="mb-tabs">
              <button
                type="button"
                className={mode === "login" ? "mb-tab active" : "mb-tab"}
                onClick={() => { setMode("login"); setError(""); setInfo(""); }}
              >
                Login
              </button>
              <button
                type="button"
                className={mode === "signup" ? "mb-tab active" : "mb-tab"}
                onClick={() => { setMode("signup"); setError(""); setInfo(""); }}
              >
                Create Account
              </button>
            </div>
          )}

          <h1 className="mb-login-title">{title}</h1>
          <p className="mb-login-sub">{subtitle}</p>

          <form onSubmit={handleSubmit} className={shake ? "shake" : ""} noValidate autoComplete="off">

            {view === "form" && mode === "signup" && (
              <>
                <label className="mb-field-label">Full Name</label>
                <input
                  type="text"
                  autoComplete="off"
                  className="mb-input"
                  placeholder="Jane Doe"
                  value={formData.name}
                  onChange={(e) => updateField("name", e.target.value)}
                />
              </>
            )}

            {(view === "form" || view === "forgot") && (
              <>
                <label className="mb-field-label">Email</label>
                <input
                  type="email"
                  autoComplete="off"
                  className="mb-input"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) => updateField("email", e.target.value)}
                />
              </>
            )}

            {(view === "otp" || view === "reset") && (
              <>
                <label className="mb-field-label">Verification code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  autoComplete="one-time-code"
                  className="mb-input mb-otp"
                  placeholder="------"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                />
              </>
            )}

            {(view === "form" || view === "reset") && (
              <>
                <label className="mb-field-label">{view === "reset" ? "New Password" : "Password"}</label>
                <div className="mb-password-wrap">
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    className="mb-input"
                    placeholder={view === "reset" ? "Choose a new password" : "Type your password"}
                    value={formData.password}
                    onChange={(e) => updateField("password", e.target.value)}
                  />
                  <button type="button" className="mb-password-toggle" onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </>
            )}

            {((view === "form" && mode === "signup") || view === "reset") && (
              <>
                <label className="mb-field-label">Re-enter Password</label>
                <div className="mb-password-wrap">
                  <input
                    type={showConfirm ? "text" : "password"}
                    autoComplete="new-password"
                    className="mb-input"
                    placeholder="Confirm your password"
                    value={formData.confirmPassword}
                    onChange={(e) => updateField("confirmPassword", e.target.value)}
                  />
                  <button type="button" className="mb-password-toggle" onClick={() => setShowConfirm(!showConfirm)}>
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </>
            )}

            {view === "form" && mode === "login" && (
              <div className="mb-form-row">
                <label className="mb-checkbox-row">
                  <input type="checkbox" defaultChecked /> Remember me
                </label>
                <a
                  href="#"
                  className="mb-link"
                  onClick={(e) => { e.preventDefault(); goTo("forgot"); }}
                >
                  Forgot password?
                </a>
              </div>
            )}

            {info && !error && <div className="mb-info">{info}</div>}
            {error && <div className="mb-error">{error}</div>}

            <button type="submit" className="mb-login-btn" disabled={submitting}>
              {submitting ? "Please wait..." : submitLabel}
            </button>

            {view !== "form" && (
              <div className="mb-otp-row">
                {view === "forgot" ? (
                  <span />
                ) : (
                  <button type="button" className="mb-linkbtn" onClick={handleResend} disabled={cooldown > 0}>
                    {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
                  </button>
                )}
                <button type="button" className="mb-linkbtn" onClick={backToLogin}>
                  ← Back to login
                </button>
              </div>
            )}
          </form>

          {view === "form" && (
            <p className="mb-signup-text">
              {mode === "login" ? (
                <>Don't have an account? <a href="#" className="mb-link" onClick={(e) => { e.preventDefault(); setMode("signup"); setError(""); setInfo(""); }}>Create one</a></>
              ) : (
                <>Already have an account? <a href="#" className="mb-link" onClick={(e) => { e.preventDefault(); setMode("login"); setError(""); setInfo(""); }}>Log in</a></>
              )}
            </p>
          )}
        </div>

        {/* RIGHT PANEL — PREVIEW */}
        <div className="mb-right">
          <div className="mb-right-headline">
            <div className="mb-right-line1">Understand your money.</div>
            <div className="mb-right-line2">Clearly. Confidently.</div>
          </div>

          <div className="mb-phone-mock">
            <div className="mb-phone-topbar">
              <span>9:41</span>
              <span className="mb-phone-icons">••• 📶 🔋</span>
            </div>

            <div className="mb-phone-balance-label">Your portfolio</div>
            <div className="mb-phone-balance-row">
              <div className="mb-phone-balance">₹2,50,000</div>
              <div className="mb-phone-bell"><Bell size={16} /></div>
            </div>

            <div className="mb-phone-card">
              <div className="mb-phone-card-toggle" />
              <div className="mb-phone-card-info">
                <div className="mb-phone-card-title">Moderate Risk Profile</div>
                <div className="mb-phone-card-sub">5–10 year horizon</div>
              </div>
              <div className="mb-phone-card-switch" />
            </div>

            <div className="mb-phone-ops-row">
              <div>
                <div className="mb-phone-ops-label">Growth (YTD)</div>
                <div className="mb-phone-ops-value positive">+9.2%</div>
                <div className="mb-phone-ops-bar"><div style={{ width: "62%" }} /></div>
              </div>
              <div>
                <div className="mb-phone-ops-label">Confidence</div>
                <div className="mb-phone-ops-value">84%</div>
                <div className="mb-phone-ops-bar"><div style={{ width: "84%", background: "#B7A9E0" }} /></div>
              </div>
            </div>

            <div className="mb-phone-chart">
              <div className="mb-phone-chart-badge"><TrendingUp size={11} /> Trending up</div>
              <ResponsiveContainer width="100%" height={70}>
                <BarChart data={miniChartData}>
                  <Bar dataKey="v" radius={[4, 4, 0, 0]} fill="rgba(255,255,255,0.75)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mb-right-footer">
            <span>Context-Aware</span>
            <span>Explainable AI</span>
            <span>Source Transparent</span>
          </div>
        </div>

      </div>
    </div>
  );
}