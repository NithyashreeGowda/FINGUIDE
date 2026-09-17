import { useState } from "react";
import {
  ArrowUp,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

const SUGGESTED_QUERIES = [
  "Why was this recommended?",
  "What are the risks?",
  "Explain my risk profile",
  "What is diversification?",
];

export default function Assistant({ profileComplete = true }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);

  const handleAsk = (text = query) => {
    const question = text.trim();

    if (!question) return;

    setMessages((prev) => [
      ...prev,
      {
        type: "user",
        text: question,
      },
    ]);

    setQuery("");
  };

  return (
    <div className="assistant-page">

      {messages.length === 0 ? (
        <>

          {/* WELCOME */}
          <div className="assistant-welcome">

            <h1>Financial Assistant</h1>

            <p>
              Your personalized financial companion for questions,
              analysis, and investment guidance.
            </p>

            {/* PROFILE INCOMPLETE */}
            {!profileComplete ? (
              <div className="assistant-profile-prompt">

                <div className="assistant-prompt-title">
                  Complete your financial profile
                </div>

                <p>
                  Add your financial goals, investment horizon,
                  risk tolerance, and other details to receive
                  personalized analysis.
                </p>

                <button>
                  Complete My Profile
                </button>

              </div>
            ) : (

              /* PERSONALIZED RECOMMENDATION */
              <div className="assistant-recommendation">

                <div className="assistant-rec-header">
                  <div>
                    <div className="assistant-rec-label">
                      PERSONALIZED ANALYSIS
                    </div>

                    <h2>Recommended Investment</h2>
                  </div>

                  <div className="assistant-rec-confidence">
                    84%
                    <span>Confidence</span>
                  </div>
                </div>


                {/* STOCK */}
                <div className="assistant-stock-row">

                  <div>
                    <div className="assistant-stock-name">
                      NVIDIA Corporation
                    </div>

                    <div className="assistant-stock-ticker">
                      NVDA
                    </div>
                  </div>

                  <div className="assistant-sentiment">
                    <TrendingUp size={14} />
                    Positive
                  </div>

                </div>


                {/* WHY */}
                <div className="assistant-rec-section">

                  <div className="assistant-rec-section-title">
                    Why this recommendation?
                  </div>

                  <p>
                    Strong alignment with your investment horizon
                    and moderate risk profile, supported by positive
                    recent financial signals.
                  </p>

                </div>


                {/* ADVANTAGES + RISKS */}
                <div className="assistant-rec-columns">

                  <div className="assistant-rec-box assistant-advantage">

                    <div className="assistant-rec-box-title">
                      <CheckCircle2 size={15} />
                      Advantages
                    </div>

                    <ul>
                      <li>Strong recent performance</li>
                      <li>Positive financial sentiment</li>
                      <li>Fits your investment horizon</li>
                    </ul>

                  </div>


                  <div className="assistant-rec-box assistant-risk">

                    <div className="assistant-rec-box-title">
                      <AlertTriangle size={15} />
                      Risks & Considerations
                    </div>

                    <ul>
                      <li>Market volatility</li>
                      <li>Sector concentration</li>
                      <li>Valuation risk</li>
                    </ul>

                  </div>

                </div>

              </div>
            )}

          </div>


          {/* SUGGESTED QUERIES */}
          <div className="assistant-suggestions">

            <div className="assistant-suggestions-title">
              Suggested Queries
            </div>

            <div className="assistant-query-list">

              {SUGGESTED_QUERIES.map((question) => (
                <button
                  key={question}
                  onClick={() => handleAsk(question)}
                >
                  {question}
                </button>
              ))}

            </div>

          </div>

        </>
      ) : (

        /* CHAT MODE */
        <div className="assistant-chat">

          {messages.map((message, index) => (
            <div
              key={index}
              className={`assistant-message ${
                message.type === "user"
                  ? "assistant-user-message"
                  : "assistant-ai-message"
              }`}
            >

              {message.type === "user" && (
                <div className="assistant-message-label">
                  You
                </div>
              )}

              <div className="assistant-message-text">
                {message.text}
              </div>

            </div>
          ))}

        </div>
      )}


      {/* INPUT */}
      <div
        className={`assistant-input-wrapper ${
          messages.length > 0
            ? "assistant-input-chat-mode"
            : ""
        }`}
      >

        <input
          type="text"
          value={query}
          placeholder="Ask anything about finance..."
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleAsk();
            }
          }}
        />

        <button
          onClick={() => handleAsk()}
          aria-label="Send question"
        >
          <ArrowUp size={17} />
        </button>

      </div>

    </div>
  );
}