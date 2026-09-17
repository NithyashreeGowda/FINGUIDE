import { useState } from "react";
import { Eye, EyeOff, Bell, TrendingUp } from "lucide-react";
import { BarChart, Bar, ResponsiveContainer } from "recharts";

const miniChartData = [
  { v: 40 }, { v: 65 }, { v: 50 }, { v: 80 }, { v: 60 }, { v: 90 }, { v: 70 },
];

export default function Login({ onLogin }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [error, setError] = useState("");
  const [shake, setShake] = useState(false);

  const triggerError = (msg) => {
    setError(msg);
    setShake(true);
    setTimeout(() => setShake(false), 400);
  };

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (mode === "signup") {
      if (!formData.name || !formData.email || !formData.password || !formData.confirmPassword) {
        triggerError("Please fill in all fields.");
        return;
      }
      if (formData.password.length < 8) {
        triggerError("Password must be at least 8 characters.");
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        triggerError("Passwords do not match.");
        return;
      }
      setError("");
      onLogin({ name: formData.name, email: formData.email, provider: "email" });
      return;
    }

    if (!formData.email || !formData.password) {
      triggerError("Please fill in all fields.");
      return;
    }
    setError("");
    onLogin({ email: formData.email, provider: "email" });
  };

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

          <div className="mb-tabs">
            <button
              type="button"
              className={mode === "login" ? "mb-tab active" : "mb-tab"}
              onClick={() => { setMode("login"); setError(""); }}
            >
              Login
            </button>
            <button
              type="button"
              className={mode === "signup" ? "mb-tab active" : "mb-tab"}
              onClick={() => { setMode("signup"); setError(""); }}
            >
              Create Account
            </button>
          </div>

          <h1 className="mb-login-title">{mode === "login" ? "Welcome " : "Create your account"}</h1>
          <p className="mb-login-sub">
            {mode === "login"
              ? "Understand your finances confidently, wherever you are, whenever you need to."
              : "Set up your FinGuide account to get personalized financial insights."}
          </p>

          <form onSubmit={handleSubmit} className={shake ? "shake" : ""}>
            {mode === "signup" && (
              <>
                <label className="mb-field-label">Full Name</label>
                <input
                  type="text"
                  className="mb-input"
                  placeholder="Jane Doe"
                  value={formData.name}
                  onChange={(e) => updateField("name", e.target.value)}
                />
              </>
            )}

            <label className="mb-field-label">Email</label>
            <input
              type="email"
              className="mb-input"
              placeholder="you@example.com"
              value={formData.email}
              onChange={(e) => updateField("email", e.target.value)}
            />

            <label className="mb-field-label">Password</label>
            <div className="mb-password-wrap">
              <input
                type={showPassword ? "text" : "password"}
                className="mb-input"
                placeholder="Type your password"
                value={formData.password}
                onChange={(e) => updateField("password", e.target.value)}
              />
              <button type="button" className="mb-password-toggle" onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {mode === "signup" && (
              <>
                <label className="mb-field-label">Re-enter Password</label>
                <div className="mb-password-wrap">
                  <input
                    type={showConfirm ? "text" : "password"}
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

            {mode === "login" && (
              <div className="mb-form-row">
                <label className="mb-checkbox-row">
                  <input type="checkbox" defaultChecked /> Remember me
                </label>
                <a href="#" className="mb-link">Forgot password?</a>
              </div>
            )}

            {error && <div className="mb-error">{error}</div>}

            <button type="submit" className="mb-login-btn">
              {mode === "login" ? "Login" : "Create Account"}
            </button>
          </form>

          <p className="mb-signup-text">
            {mode === "login" ? (
              <>Don't have an account? <a href="#" className="mb-link" onClick={() => { setMode("signup"); setError(""); }}>Create one</a></>
            ) : (
              <>Already have an account? <a href="#" className="mb-link" onClick={() => { setMode("login"); setError(""); }}>Log in</a></>
            )}
          </p>
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