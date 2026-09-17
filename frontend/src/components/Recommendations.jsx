import {
  Calendar,
  ExternalLink,
  CheckCircle2,
  Info,
} from "lucide-react";

const SOURCES = [
  {
    name: "Reuters",
    category: "Financial News",
    date: "15 Sep 2026",
    summary: "Recent company performance and market developments.",
    relevance: "Highly Relevant",
    cta: "Open Source",
  },
  {
    name: "Yahoo Finance",
    category: "Market Data",
    date: "15 Sep 2026",
    summary: "Price, volume, and historical market information.",
    relevance: "Relevant",
    cta: "Open Source",
  },
  {
    name: "Company Financial Report",
    category: "Financial Filing",
    date: "12 Sep 2026",
    summary: "Revenue, earnings, and financial metrics.",
    relevance: "Supporting",
    cta: "View Report",
  },
];

const ALTERNATIVES = [
  {
    name: "Microsoft",
    sentiment: "Positive",
    confidence: "78%",
    reason: "Strong fundamentals with lower contextual fit.",
  },
  {
    name: "Apple",
    sentiment: "Neutral",
    confidence: "72%",
    reason: "Good fundamentals with weaker profile alignment.",
  },
];

export default function Recommendations({ onUpdateProfile }) {
  return (
    <div className="rec-page">

      {/* HEADER */}
      <div className="rec-header">
        <div>
          

          <h2 className="section-heading">
            Personalized Recommendation
          </h2>

          <p className="section-sub">
            Based on your financial profile, market data, and supporting evidence.
          </p>

          <div className="rec-date">
            <Calendar size={13} />
            Analysis updated: 15 Sep 2026
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="rec-grid">

        {/* LEFT */}
        <div className="rec-main g-card">

          {/* STOCK HEADER */}
          <div className="rec-title-row">
            <div>
              <div className="stat-label">
                RECOMMENDED INVESTMENT
              </div>

              <div className="rec-stock-name">
                NVIDIA Corporation{" "}
                <span className="rec-ticker">NVDA</span>
              </div>

              <div className="rec-sentiment-row">
                <span className="pill pill-positive">
                  Positive
                </span>

                <span className="rec-confidence-text">
                  84% Confidence
                </span>
              </div>
            </div>

            <div className="rec-price-block">
              <div className="rec-price">
                ₹8,420.00
              </div>

              <div className="rec-price-change positive">
                +1.82%
              </div>
            </div>
          </div>

          {/* WHY */}
          <Section title="Why this recommendation?">
            <p className="rec-body-text">
              Strong fit for your investment horizon and moderate risk
              profile, supported by positive recent financial signals.
            </p>
          </Section>

          
          {/* ADVANTAGES + RISKS */}
          <div className="rec-two-column-sections">

            <Section title="Advantages">
              <ReasonRow
                title="Strong performance"
                desc="Recent revenue and earnings support the analysis."
                tone="sage"
              />

              <ReasonRow
                title="Positive sentiment"
                desc="Recent financial coverage remains favorable."
                tone="sage"
              />

              <ReasonRow
                title="Long-term fit"
                desc="Matches your stated investment horizon."
                tone="sage"
              />
            </Section>

            <Section title="Risks & Considerations">
              <ReasonRow
                title="Market volatility"
                desc="Price fluctuations may be significant."
                tone="peach"
              />

              <ReasonRow
                title="Sector concentration"
                desc="May increase exposure to one sector."
                tone="peach"
              />

              <ReasonRow
                title="Valuation risk"
                desc="Higher valuation can increase downside risk."
                tone="peach"
              />
            </Section>

          </div>

          {/* ACTIONS */}
          <div className="rec-actions">
            <button className="btn-fill">
              View Full Analysis
            </button>

            <button
              className="btn-outline"
              onClick={onUpdateProfile}
            >
              Update Financial Profile
            </button>
          </div>
        </div>

        {/* RIGHT */}
        <div className="rec-side">

          {/* SUMMARY */}
          <div className="g-card">
            <div className="section-heading" style={{ fontSize: 14 }}>
              Recommendation
            </div>

            <div className="rec-sentiment-row">
              <span className="pill pill-positive">
                Positive
              </span>

              <span className="rec-confidence-text">
                84% Confidence
              </span>
            </div>

            <ConfidenceBar percent={84} />

            <div className="rec-summary-list">
              <SummaryRow
                label="Status"
                value="Ready"
              />

              <SummaryRow
                label="Profile Match"
                value="Strong"
              />

              <SummaryRow
                label="Evidence"
                value="High"
              />

              <SummaryRow
                label="Context"
                value="Complete"
              />
            </div>
          </div>

          {/* READINESS */}
          <div
            className="g-card"
            style={{ marginTop: 16 }}
          >
            <div
              className="section-heading"
              style={{ fontSize: 14 }}
            >
              Decision Readiness
            </div>

            <div className="decision-ready">
              <CheckCircle2 size={16} />
              READY
            </div>

            <p className="rec-small-text">
              Sufficient and consistent financial information is
              available for this analysis.
            </p>
          </div>

        </div>
      </div>

      {/* SOURCES */}
      <div className="rec-evidence-section">

        <div className="rec-section-heading-row">
          <div>
            <h3 className="section-heading">
              Evidence and Sources
            </h3>

            
          </div>
        </div>

        <div className="sources-grid">
          {SOURCES.map((source) => (
            <div
              className="g-card source-card"
              key={source.name}
            >
              <div className="source-top">
                <div>
                  <div className="source-name">
                    {source.name}
                  </div>

                  <div className="rec-small-text">
                    {source.category} · {source.date}
                  </div>
                </div>

                <span className="relevance-tag">
                  {source.relevance}
                </span>
              </div>

              <p className="rec-small-text source-summary">
                {source.summary}
              </p>

              <a
                href="#"
                className="source-link"
              >
                {source.cta}
                <ExternalLink size={13} />
              </a>
            </div>
          ))}
        </div>

        {/* ALTERNATIVES */}
        <h3
          className="section-heading"
          style={{ marginTop: 28 }}
        >
          Other Options Considered
        </h3>

        <div className="grid-2 alternatives-grid">
          {ALTERNATIVES.map((option) => (
            <div
              className="g-card alternative-card"
              key={option.name}
            >
              <div className="alternative-top">
                <div>
                  <div className="alternative-name">
                    {option.name}
                  </div>

                  <div className="rec-small-text">
                    {option.confidence} Confidence
                  </div>
                </div>

                <span
                  className={`pill ${
                    option.sentiment === "Positive"
                      ? "pill-positive"
                      : "pill-neutral"
                  }`}
                >
                  {option.sentiment}
                </span>
              </div>

              <p className="rec-small-text">
                {option.reason}
              </p>
            </div>
          ))}
        </div>

        {/* DISCLAIMER */}
        <div className="disclaimer-box">
          <Info size={14} />

          <span>
            FinGuide provides educational and analytical information
            based on available financial data and user-provided
            context. It does not guarantee investment returns and
            should not be treated as guaranteed financial advice.
          </span>
        </div>

      </div>
    </div>
  );
}


/* ---------------- COMPONENTS ---------------- */

function Section({ title, children }) {
  return (
    <div className="rec-section">
      <div className="rec-section-title">
        {title}
      </div>

      {children}
    </div>
  );
}


function ReasonRow({ title, desc, tone }) {
  return (
    <div className={`reason-row reason-${tone}`}>
      <div
        style={{
          fontWeight: 650,
          fontSize: 12.5,
        }}
      >
        {title}
      </div>

      <div className="rec-small-text">
        {desc}
      </div>
    </div>
  );
}


function SummaryRow({ label, value }) {
  return (
    <div className="summary-row">
      <span className="rec-small-text">
        {label}
      </span>

      <span
        style={{
          fontWeight: 650,
          fontSize: 12.5,
        }}
      >
        {value}
      </span>
    </div>
  );
}


function ConfidenceBar({ percent }) {
  return (
    <div className="confidence-bar-track">
      <div
        className="confidence-bar-fill"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}