import { Fragment, useEffect, useRef, useState } from "react";
import {
  User,
  TrendingUp,
  ShieldCheck,
  BriefcaseBusiness,
  Save,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  ChevronRight,
  Check,
} from "lucide-react";
import { createProfile, updateProfile } from "../api";

const RISK_PREFERENCES = ["conservative", "moderate", "aggressive"];
const LEVELS = ["low", "medium", "high"];

const INITIAL_FORM = {
  age: "",
  income: "",
  monthly_expenses: "",
  investment_amount: "",
  investment_horizon: "",
  financial_goal: "",
  risk_preference: "",
  risk_capacity: "",
  liquidity_requirement: "",
  existing_investments: "",
  liabilities: "",
  target_return_percent: "",
};

const isEmpty = (value) =>
  value === "" || value === null || value === undefined;

const titleCase = (value) => {
  if (!value) return "";
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

/* =====================================================
   FINANCIAL PROFILE PAGE (existing users, opened from Assistant)
===================================================== */

const SECTIONS = [
  {
    id: "about",
    title: "About You",
    desc: "Your age, income and monthly expenses.",
    icon: User,
    fields: ["age", "income", "monthly_expenses"],
  },
  {
    id: "investment",
    title: "Investment Plan",
    desc: "Your capital, time horizon and goals.",
    icon: TrendingUp,
    fields: ["investment_amount", "investment_horizon", "financial_goal"],
  },
  {
    id: "risk",
    title: "Risk Profile",
    desc: "Your comfort with risk and market volatility.",
    icon: ShieldCheck,
    fields: ["risk_preference", "risk_capacity"],
  },
  {
    id: "position",
    title: "Financial Position",
    desc: "Your investments, liabilities and liquidity.",
    icon: BriefcaseBusiness,
    fields: ["existing_investments", "liabilities", "liquidity_requirement"],
  },
];

const TEXT_FIELDS = ["financial_goal", "risk_preference", "risk_capacity", "liquidity_requirement"];

const HORIZON_OPTIONS = [
  ["1", "Less than 1 year"],
  ["3", "1–3 years"],
  ["5", "3–5 years"],
  ["10", "5–10 years"],
  ["15", "10+ years"],
];

const GOAL_OPTIONS = [
  ["wealth_creation", "Wealth Creation"],
  ["retirement", "Retirement"],
  ["home_purchase", "Home Purchase"],
  ["education", "Education"],
  ["capital_preservation", "Capital Preservation"],
  ["short_term_savings", "Short-Term Savings"],
  ["other", "Other"],
];

export default function MyProfile({ initial = null, onSaved, onBack }) {
  const [formData, setFormData] = useState(() => {
    const state = { ...INITIAL_FORM };
    if (initial) {
      Object.keys(INITIAL_FORM).forEach((k) => {
        state[k] = initial[k] == null ? "" : String(initial[k]);
      });
    }
    return state;
  });
  const [openId, setOpenId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const panelRef = useRef(null);

  const allFields = SECTIONS.flatMap((s) => s.fields);
  const completeness = Math.round(
    (allFields.filter((f) => !isEmpty(formData[f])).length / allFields.length) * 100
  );
  const sectionDone = (s) => s.fields.every((f) => !isEmpty(formData[f]));

  useEffect(() => {
    if (openId) {
      panelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [openId]);

  const updateField = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setMessage(null);
  };

  const handleSave = async () => {
    const age = Number(formData.age);
    if (!isEmpty(formData.age) && (age < 18 || age > 100)) {
      setMessage({ type: "error", text: "Age must be between 18 and 100." });
      return;
    }

    setLoading(true);
    setMessage(null);

    const payload = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value === "") payload[key] = null;
      else if (TEXT_FIELDS.includes(key)) payload[key] = value;
      else payload[key] = Number(value);
    });

    try {
      onSaved?.(await updateProfile(payload));
    } catch (error) {
      setMessage({
        type: "error",
        text: error.message || "Unable to save your financial profile.",
      });
      setLoading(false);
    }
  };

  const openSection = SECTIONS.find((s) => s.id === openId);

  return (
    <div className="fp-page">

      {/* HEADER */}
      <div className="fp-head">
        <div>
          <h1>Financial Profile</h1>
          <p>
            Your financial information helps us provide personalized
            recommendations and guidance.
          </p>
        </div>

        <button type="button" className="btn-outline fp-back" onClick={onBack}>
          <ArrowLeft size={15} /> Back to Assistant
        </button>
      </div>

      {/* PROFILE STATUS BAR + SAVE */}
      <div className="fp-status">
        <div className="fp-status-main">
          <div className="fp-status-top">
            <span>Profile status</span>
            <strong>{completeness}% complete</strong>
          </div>
          <div className="fp-bar">
            <div style={{ width: `${completeness}%` }} />
          </div>
        </div>

        <span className={`fp-pill ${completeness === 100 ? "ok" : "warn"}`}>
          {completeness === 100 ? "Ready for recommendations" : "Needs information"}
        </span>

        <button
          type="button"
          className="profile-save-btn"
          onClick={handleSave}
          disabled={loading}
        >
          <Save size={16} />
          {loading ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {message && (
        <div className={`profile-message ${message.type}`}>
          <AlertCircle size={16} />
          <span>{message.text}</span>
        </div>
      )}

      {/* SECTION CARDS */}
      <div className="fp-grid">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const done = sectionDone(s);

          return (
            <button
              type="button"
              key={s.id}
              className={`fp-card ${openId === s.id ? "open" : ""}`}
              onClick={() => setOpenId(openId === s.id ? null : s.id)}
            >
              <div className="fp-card-icon">
                <Icon size={24} />
              </div>

              <div className="fp-card-body">
                <div className="fp-card-title">{s.title}</div>
                <div className="fp-card-desc">{s.desc}</div>

                <span className={`fp-badge ${done ? "done" : "todo"}`}>
                  {done ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                  {done ? "Complete" : "Incomplete"}
                </span>
              </div>

              <ChevronRight size={18} className="fp-arrow" />
            </button>
          );
        })}
      </div>

      {/* EDITOR FOR THE CLICKED SECTION */}
      {openSection && (
        <section className="fp-editor" ref={panelRef}>
          <h2>{openSection.title}</h2>

          {openId === "about" && (
            <div className="fp-editor-grid">
              <InputField label="Age" type="number" value={formData.age}
                placeholder="Enter your age" onChange={(v) => updateField("age", v)} />
              <InputField label="Monthly Income" type="number" prefix="₹" value={formData.income}
                placeholder="85,000" onChange={(v) => updateField("income", v)} />
              <InputField label="Monthly Expenses" type="number" prefix="₹" value={formData.monthly_expenses}
                placeholder="52,000" onChange={(v) => updateField("monthly_expenses", v)} />
            </div>
          )}

          {openId === "investment" && (
            <div className="fp-editor-grid">
              <InputField label="Investment Capital" type="number" prefix="₹" value={formData.investment_amount}
                placeholder="2,50,000" onChange={(v) => updateField("investment_amount", v)} />
              <InputField label="Expected Return (optional)" type="number" suffix="%" value={formData.target_return_percent}
                placeholder="Optional" onChange={(v) => updateField("target_return_percent", v)} />
              <SelectField label="Investment Horizon" value={formData.investment_horizon}
                options={HORIZON_OPTIONS} onChange={(v) => updateField("investment_horizon", v)} />
              <SelectField label="Financial Goal" value={formData.financial_goal}
                options={GOAL_OPTIONS} onChange={(v) => updateField("financial_goal", v)} />
            </div>
          )}

          {openId === "risk" && (
            <div className="fp-editor-stack">
              <ChoiceGroup title="Risk Preference" options={RISK_PREFERENCES}
                value={formData.risk_preference} onChange={(v) => updateField("risk_preference", v)} />
              <ChoiceGroup title="Risk Capacity" options={LEVELS} compact
                value={formData.risk_capacity} onChange={(v) => updateField("risk_capacity", v)} />
            </div>
          )}

          {openId === "position" && (
            <div className="fp-editor-stack">
              <div className="fp-editor-grid">
                <InputField label="Existing Investments" type="number" prefix="₹" value={formData.existing_investments}
                  placeholder="4,20,000" onChange={(v) => updateField("existing_investments", v)} />
                <InputField label="Liabilities / EMI" type="number" prefix="₹" value={formData.liabilities}
                  placeholder="0" onChange={(v) => updateField("liabilities", v)} />
              </div>
              <ChoiceGroup title="Liquidity Requirement" options={LEVELS} compact
                value={formData.liquidity_requirement} onChange={(v) => updateField("liquidity_requirement", v)} />
            </div>
          )}
        </section>
      )}

    </div>
  );
}

function InputField({ label, value, type, prefix, suffix, placeholder, onChange }) {
  return (
    <div>
      <label className="profile-label">{label}</label>

      <div className="profile-input-shell">
        {prefix && <span>{prefix}</span>}

        <input
          type={type}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
        />

        {suffix && <span>{suffix}</span>}
      </div>
    </div>
  );
}

function SelectField({ label, value, options, onChange }) {
  return (
    <div>
      <label className="profile-label">{label}</label>

      <select
        className="profile-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select</option>

        {options.map(([optValue, optLabel]) => (
          <option key={optValue} value={optValue}>
            {optLabel}
          </option>
        ))}
      </select>
    </div>
  );
}

function ChoiceGroup({ title, options, value, onChange, compact = false }) {
  return (
    <div>
      <div className="choice-title">
        <h3>{title}</h3>
      </div>

      <div className={`choice-grid ${compact ? "choice-grid-compact" : ""}`}>
        {options.map((option) => (
          <button
            type="button"
            key={option}
            className={`choice-card ${value === option ? "selected" : ""}`}
            onClick={() => onChange(option)}
          >
            <strong>{titleCase(option)}</strong>
          </button>
        ))}
      </div>
    </div>
  );
}

/* =====================================================
   ONBOARDING WIZARD — new users only (step-by-step)
===================================================== */

const WZ_RISK_HINTS = {
  conservative: "Prioritises protecting your money over growth.",
  moderate: "Balances steady growth with manageable ups and downs.",
  aggressive: "Aims for maximum growth and accepts bigger swings.",
};

const WZ_STEPS = [
  { label: "About You", title: "About You", required: ["age", "income", "monthly_expenses"] },
  { label: "Investment", title: "Investment Plan", required: ["investment_amount", "investment_horizon", "financial_goal"] },
  { label: "Risk", title: "Risk Profile", required: ["risk_preference", "risk_capacity"] },
  { label: "Financial Position", title: "Financial Position", required: ["existing_investments", "liabilities", "liquidity_requirement"] },
];

const WZ_AMOUNT_FIELDS = ["income", "monthly_expenses", "investment_amount", "existing_investments", "liabilities", "target_return_percent"];

function wzPayload(form) {
  const payload = {};
  Object.entries(form).forEach(([key, value]) => {
    if (isEmpty(value)) payload[key] = null;
    else if (TEXT_FIELDS.includes(key)) payload[key] = value;
    else payload[key] = Number(value);
  });
  return payload;
}

export function OnboardingWizard({ user, onSaved }) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const last = step === WZ_STEPS.length - 1;
  const firstName = user?.name ? user.name.split(" ")[0] : "";

  const set = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setError("");
  };

  const validate = () => {
    const missing = WZ_STEPS[step].required.filter((f) => isEmpty(form[f]));
    if (missing.length) return "Please fill in all required fields to continue.";

    if (step === 0) {
      const age = Number(form.age);
      if (age < 18 || age > 100) return "Age must be between 18 and 100.";
    }
    if (WZ_AMOUNT_FIELDS.some((k) => !isEmpty(form[k]) && Number(form[k]) < 0)) {
      return "Amounts can't be negative.";
    }
    return "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }

    if (!last) {
      setStep(step + 1);
      return;
    }

    setSaving(true);
    try {
      onSaved(await createProfile(wzPayload(form))); // App then opens the Assistant
    } catch (err) {
      setError(err.message || "Unable to save your financial profile.");
      setSaving(false);
    }
  };

  const goBack = () => {
    setStep(step - 1);
    setError("");
  };

  const jumpTo = (i) => {
    if (i < step) {
      setStep(i);
      setError("");
    }
  };

  return (
    <div className="wz-page">
      <div className="wz-wrap">

        {/* HEADING */}
        <div className="wz-head">
          {firstName && <div className="wz-brand">Welcome, {firstName}</div>}
          <h1>Ready to navigate FinGuide?</h1>
          <p>Let’s understand your financial situation.</p>
        </div>

        {/* STEPPER */}
        <div className="wz-steps">
          {WZ_STEPS.map((s, i) => (
            <Fragment key={s.label}>
              {i > 0 && <div className={`wz-line ${i <= step ? "done" : ""}`} />}
              <button
                type="button"
                className={`wz-step ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}
                onClick={() => jumpTo(i)}
              >
                <span className="wz-dot">
                  {i < step && <Check size={13} strokeWidth={3} />}
                </span>
                <span>{s.label}</span>
              </button>
            </Fragment>
          ))}
        </div>

        {/* STEP CARD */}
        <form onSubmit={handleSubmit} noValidate>
          <section className="wz-card wz-fade" key={step}>

            <div className="wz-eyebrow">{WZ_STEPS[step].title.toUpperCase()}</div>

            {/* 1 — ABOUT YOU */}
            {step === 0 && (
              <div className="wz-fields">
                <div className="wz-grid2">
                  <InputField label="Age" type="number" placeholder="Enter your age"
                    value={form.age} onChange={(v) => set("age", v)} />
                  <InputField label="Monthly Income" type="number" prefix="₹" placeholder="85,000"
                    value={form.income} onChange={(v) => set("income", v)} />
                </div>
                <InputField label="Monthly Expenses" type="number" prefix="₹" placeholder="52,000"
                  value={form.monthly_expenses} onChange={(v) => set("monthly_expenses", v)} />
              </div>
            )}

            {/* 2 — INVESTMENT */}
            {step === 1 && (
              <div className="wz-fields">
                <div className="wz-grid2">
                  <InputField label="Investment Capital" type="number" prefix="₹" placeholder="2,50,000"
                    value={form.investment_amount} onChange={(v) => set("investment_amount", v)} />
                  <InputField label="Expected Return (optional)" type="number" suffix="%" placeholder="Optional"
                    value={form.target_return_percent} onChange={(v) => set("target_return_percent", v)} />
                </div>
                <div className="wz-grid2">
                  <SelectField label="Investment Horizon" options={HORIZON_OPTIONS}
                    value={form.investment_horizon} onChange={(v) => set("investment_horizon", v)} />
                  <SelectField label="Financial Goal" options={GOAL_OPTIONS}
                    value={form.financial_goal} onChange={(v) => set("financial_goal", v)} />
                </div>
              </div>
            )}

            {/* 3 — RISK */}
            {step === 2 && (
              <div className="wz-fields">
                <ChoiceGroup title="Risk Preference" options={RISK_PREFERENCES}
                  value={form.risk_preference} onChange={(v) => set("risk_preference", v)} />
                {form.risk_preference && (
                  <div className="wz-hint">{WZ_RISK_HINTS[form.risk_preference]}</div>
                )}
                <ChoiceGroup title="Risk Capacity" options={LEVELS} compact
                  value={form.risk_capacity} onChange={(v) => set("risk_capacity", v)} />
              </div>
            )}

            {/* 4 — FINANCIAL POSITION */}
            {step === 3 && (
              <div className="wz-fields">
                <div className="wz-grid2">
                  <InputField label="Existing Investments" type="number" prefix="₹" placeholder="Enter 0 if none"
                    value={form.existing_investments} onChange={(v) => set("existing_investments", v)} />
                  <InputField label="Liabilities / EMI" type="number" prefix="₹" placeholder="Enter 0 if none"
                    value={form.liabilities} onChange={(v) => set("liabilities", v)} />
                </div>
                <ChoiceGroup title="Liquidity Requirement" options={LEVELS} compact
                  value={form.liquidity_requirement} onChange={(v) => set("liquidity_requirement", v)} />
              </div>
            )}

            {error && (
              <div className="wz-error">
                <span>{error}</span>
              </div>
            )}

            <div className="wz-actions">
              {step > 0 ? (
                <button type="button" className="btn-outline wz-btn" onClick={goBack}>
                  ← Back
                </button>
              ) : (
                <span />
              )}

              <button type="submit" className="btn-fill wz-btn" disabled={saving}>
                {saving ? "Saving..." : last ? "Save & Continue →" : "Next →"}
              </button>
            </div>

          </section>
        </form>

      </div>
    </div>
  );
}