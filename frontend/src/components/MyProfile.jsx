import { useMemo, useState } from "react";
import {
  Wallet,
  TrendingUp,
  ShieldCheck,
  BriefcaseBusiness,
  Droplets,
  Target,
  Save,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

const RISK_PREFERENCES = ["conservative", "moderate", "aggressive"];
const LEVELS = ["low", "medium", "high"];

const INITIAL_FORM = {
  age: "",
  income: "",
  monthly_expenses: "",
  investment_amount: "",
  investment_horizon_years: "",
  financial_goal: "",
  risk_preference: "moderate",
  risk_capacity: "medium",
  liquidity_requirement: "",
  existing_investments: "",
  liabilities: "",
  target_return_percent: "",
};

const REQUIRED_FIELDS = [
  "age",
  "income",
  "monthly_expenses",
  "investment_amount",
  "investment_horizon_years",
  "financial_goal",
  "risk_preference",
  "risk_capacity",
];

const ALL_FIELDS = [
  "age",
  "income",
  "monthly_expenses",
  "investment_amount",
  "investment_horizon_years",
  "financial_goal",
  "risk_preference",
  "risk_capacity",
  "liquidity_requirement",
  "existing_investments",
  "liabilities",
  "target_return_percent",
];

const isEmpty = (value) =>
  value === "" || value === null || value === undefined;

const titleCase = (value) => {
  if (!value) return "";
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const formatCurrency = (value) => {
  if (isEmpty(value)) return "Not specified";

  const number = Number(value);

  if (Number.isNaN(number)) return String(value);

  return `₹${number.toLocaleString("en-IN")}`;
};

export default function MyProfile({ onProfileSaved }) {
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [submittedData, setSubmittedData] = useState(null);
  const [editing, setEditing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const data = submittedData || formData;

  const completeness = useMemo(() => {
    const completed = ALL_FIELDS.filter(
      (field) => !isEmpty(data[field])
    ).length;

    return Math.round((completed / ALL_FIELDS.length) * 100);
  }, [data]);

  const missingRequired = REQUIRED_FIELDS.filter((field) =>
    isEmpty(formData[field])
  );

  const updateField = (name, value) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    setMessage(null);
  };

  const handleSubmit = async (e) => {
  e.preventDefault();

  if (missingRequired.length > 0) {
    setMessage({
      type: "warning",
      text: "Please complete the required financial profile information before saving.",
    });

    return;
  }

  setLoading(true);
  setMessage(null);

  const payload = {};

  Object.entries(formData).forEach(([key, value]) => {
    if (value === "") {
      payload[key] = null;
    } else if (
      [
        "financial_goal",
        "risk_preference",
        "risk_capacity",
        "liquidity_requirement",
      ].includes(key)
    ) {
      payload[key] = value;
    } else {
      payload[key] = Number(value);
    }
  });

  try {
    const response = await fetch(
      "http://127.0.0.1:8000/profile",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      throw new Error(
        `Profile save failed (${response.status})`
      );
    }

    await response.json();

    setSubmittedData(payload);
    setFormData(payload);
    setEditing(false);

    setMessage({
      type: "success",
      text: "Financial profile saved successfully.",
    });

    /*
      Move directly to Assistant after
      the profile has been successfully saved.
    */
    onProfileSaved?.();

  } catch (error) {
    setMessage({
      type: "error",
      text:
        error.message ||
        "Unable to save your financial profile.",
    });
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="profile-page">

      {/* HEADER */}
      <div className="profile-page-header">
        <div>
          
          <h1> Financial Profile</h1>

          <p>
            Tell FinGuide about your financial situation for personalized
            investment analysis.
          </p>
        </div>
      </div>

      {/* FORM */}
      <form onSubmit={handleSubmit}>

        <div className="profile-main-grid">

          {/* =====================================================
              ROW 1 — FINANCIAL OVERVIEW
              ===================================================== */}

          <section className="profile-card">
            <SectionHeader
              icon={<Wallet size={18} />}
              title="Financial Overview"
            />

            <div className="profile-grid">

              <InputField
                label="Age"
                type="number"
                value={formData.age}
                placeholder="Enter your age"
                onChange={(value) => updateField("age", value)}
              />

              <InputField
                label="Monthly Income"
                type="number"
                prefix="₹"
                value={formData.income}
                placeholder="85,000"
                onChange={(value) => updateField("income", value)}
              />

              <InputField
                label="Monthly Expenses"
                type="number"
                prefix="₹"
                value={formData.monthly_expenses}
                placeholder="52,000"
                onChange={(value) =>
                  updateField("monthly_expenses", value)
                }
              />

              <InputField
                label="Liabilities / EMI"
                type="number"
                prefix="₹"
                value={formData.liabilities}
                placeholder="Optional"
                onChange={(value) =>
                  updateField("liabilities", value)
                }
              />

            </div>
          </section>

          {/* =====================================================
              ROW 1 — INVESTMENT PROFILE
              ===================================================== */}

          <section className="profile-card">
            <SectionHeader
              icon={<TrendingUp size={18} />}
              title="Investment Profile"
            />

            <div className="profile-grid">

              <InputField
                label="Investment Capital"
                type="number"
                prefix="₹"
                value={formData.investment_amount}
                placeholder="2,50,000"
                onChange={(value) =>
                  updateField("investment_amount", value)
                }
              />

              <SelectField
                label="Investment Horizon"
                value={formData.investment_horizon_years}
                options={[
                  ["1", "Less than 1 year"],
                  ["3", "1–3 years"],
                  ["5", "3–5 years"],
                  ["10", "5–10 years"],
                  ["15", "10+ years"],
                ]}
                onChange={(value) =>
                  updateField("investment_horizon_years", value)
                }
              />

              <SelectField
                label="Financial Goal"
                value={formData.financial_goal}
                options={[
                  ["wealth_creation", "Wealth Creation"],
                  ["retirement", "Retirement"],
                  ["home_purchase", "Home Purchase"],
                  ["education", "Education"],
                  ["capital_preservation", "Capital Preservation"],
                  ["short_term_savings", "Short-Term Savings"],
                  ["other", "Other"],
                ]}
                onChange={(value) =>
                  updateField("financial_goal", value)
                }
              />

              <InputField
                label="Expected Return"
                type="number"
                suffix="%"
                value={formData.target_return_percent}
                placeholder="Optional"
                onChange={(value) =>
                  updateField("target_return_percent", value)
                }
              />

            </div>
          </section>

          {/* =====================================================
              ROW 2 — RISK PROFILE
              ===================================================== */}

          <section className="profile-card">
            <SectionHeader
              icon={<ShieldCheck size={18} />}
              title="Risk Profile"
            />

            <ChoiceGroup
              title="Risk Preference"
              options={RISK_PREFERENCES}
              value={formData.risk_preference}
              descriptive
              onChange={(value) =>
                updateField("risk_preference", value)
              }
            />

            
            <div className="risk-capacity">
  <ChoiceGroup
    title="Risk Capacity"
    options={LEVELS}
    value={formData.risk_capacity}
    onChange={(value) =>
      updateField("risk_capacity", value)
    }
    compact
  />
</div>
          </section>

          {/* =====================================================
              ROW 2 — PORTFOLIO & LIQUIDITY
              ===================================================== */}

          <section className="profile-card">
            <SectionHeader
              icon={<BriefcaseBusiness size={18} />}
              title="Portfolio & Liquidity"
            />

            <label className="profile-label">
              Existing Investments
            </label>

            <div className="investment-chips">
              {[
                "Stocks",
                "Mutual Funds",
                "ETFs",
                "Bonds",
                "Fixed Deposits",
                "None",
              ].map((item) => (
                <button
                  type="button"
                  key={item}
                  className="investment-chip"
                >
                  {item}
                </button>
              ))}
            </div>

            <div className="portfolio-input">
              <InputField
                label="Current Portfolio Value"
                type="number"
                prefix="₹"
                value={formData.existing_investments}
                placeholder="4,20,000"
                onChange={(value) =>
                  updateField("existing_investments", value)
                }
              />
            </div>

            <div className="liquidity-section">
              <ChoiceGroup
                title="Liquidity Requirement"
                options={LEVELS}
                value={formData.liquidity_requirement}
                onChange={(value) =>
                  updateField("liquidity_requirement", value)
                }
                compact
              />
            </div>
          </section>

        </div>

        {/* =====================================================
            ROW 3 — ONE COMBINED STATUS CARD
            ===================================================== */}

        <section className="profile-status-card">

          <div className="status-column">

            <div className="status-eyebrow">
              PROFILE STATUS
            </div>

            <h2>Profile Completeness</h2>

            <div className="status-score">
              {completeness}%
            </div>

            <div className="status-progress">
              <div
                style={{
                  width: `${completeness}%`,
                }}
              />
            </div>

            <div className="readiness-title">
              Recommendation Readiness
            </div>

            <div
              className={`readiness-pill ${
                missingRequired.length === 0
                  ? "ready"
                  : "needs"
              }`}
            >
              {missingRequired.length === 0
                ? "READY"
                : "NEEDS INFORMATION"}
            </div>

          </div>

          <div className="status-divider" />

          <div className="context-column">

            <div className="status-eyebrow">
              FINANCIAL CONTEXT
            </div>

            <ContextRow
              label="Income"
              complete={!isEmpty(data.income)}
            />

            <ContextRow
              label="Investment Capital"
              complete={!isEmpty(data.investment_amount)}
            />

            <ContextRow
              label="Investment Horizon"
              complete={!isEmpty(data.investment_horizon_years)}
            />

            <ContextRow
              label="Financial Goal"
              complete={!isEmpty(data.financial_goal)}
            />

            <ContextRow
              label="Risk Profile"
              complete={
                !isEmpty(data.risk_preference) &&
                !isEmpty(data.risk_capacity)
              }
            />

            <ContextRow
              label="Current Portfolio"
              complete={!isEmpty(data.existing_investments)}
            />

            <ContextRow
              label="Liquidity"
              complete={!isEmpty(data.liquidity_requirement)}
            />

          </div>

        </section>

        {/* MESSAGE */}
        {message && (
          <div className={`profile-message ${message.type}`}>
            {message.type === "success" ? (
              <CheckCircle2 size={16} />
            ) : (
              <AlertCircle size={16} />
            )}

            <span>{message.text}</span>
          </div>
        )}

        {/* SAVE */}
        <div className="profile-save-row">
          <button
            type="submit"
            className="profile-save-btn"
            disabled={loading}
          >
            <Save size={16} />

            {loading
              ? "Saving Profile..."
              : "Save Financial Profile"}
          </button>
        </div>

      </form>
    </div>
  );
}

/* =====================================================
   COMPONENTS
===================================================== */

function SectionHeader({ icon, title }) {
  return (
    <div className="section-header">
      <div className="section-icon">{icon}</div>

      <h2>{title}</h2>
    </div>
  );
}

function InputField({
  label,
  value,
  type,
  prefix,
  suffix,
  placeholder,
  onChange,
}) {
  return (
    <div>
      <label className="profile-label">
        {label}
      </label>

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

function SelectField({
  label,
  value,
  options,
  onChange,
}) {
  return (
    <div>
      <label className="profile-label">
        {label}
      </label>

      <select
        className="profile-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select</option>

        {options.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );
}

function ChoiceGroup({
  title,
  options,
  value,
  onChange,
  descriptive = false,
  compact = false,
}) {
  return (
    <div>
      <div className="choice-title">
        <h3>{title}</h3>
      </div>

      <div
        className={`choice-grid ${
          compact ? "choice-grid-compact" : ""
        }`}
      >
        {options.map((option) => (
          <button
            type="button"
            key={option}
            className={`choice-card ${
              value === option ? "selected" : ""
            }`}
            onClick={() => onChange(option)}
          >
            <strong>{titleCase(option)}</strong>

            {descriptive && (
              <span>
                {option === "conservative" }

                {option === "moderate"}

                {option === "High"}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function ContextRow({ label, complete }) {
  return (
    <div className="context-row">
      <div className="context-label">
        {complete ? (
          <CheckCircle2 size={14} />
        ) : (
          <AlertCircle size={14} />
        )}

        <span>{label}</span>
      </div>

      <span
        className={
          complete
            ? "context-status complete"
            : "context-status missing"
        }
      >
        {complete ? "Complete" : "Missing"}
      </span>
    </div>
  );
}