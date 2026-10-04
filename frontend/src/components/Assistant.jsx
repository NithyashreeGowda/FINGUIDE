import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import MyProfile from "./MyProfile";
import ContextStatus from "./ContextStatus";
import { addMessage, createConversation, getConversation } from "../api";

const SUGGESTED_QUERIES = [
  "Why was this recommended?",
  "What are the risks?",
  "Explain my risk profile",
  "What is diversification?",
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Assistant({ user, profileData, onProfileUpdated, openConvId }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState("");
  const [convId, setConvId] = useState(openConvId || null);
  const chatEndRef = useRef(null);

  const { profile, completeness, context } = profileData;
  const ready = context.status === "READY";
  const firstName = user.name.split(" ")[0];

  const openEditor = () => setEditing(true);

  // opened from History: load that saved conversation
  useEffect(() => {
    if (!openConvId) return;
    getConversation(openConvId)
      .then((c) =>
        setMessages(
          c.messages.map((m) => ({
            type: m.role === "user" ? "user" : "assistant",
            text: m.text,
          }))
        )
      )
      .catch(() => {});
  }, []);

  // keep the newest message in view
  useEffect(() => {
    if (messages.length) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleAsk = async (text = query) => {
    const question = text.trim();
    if (!question) return;

    setMessages((prev) => [...prev, { type: "user", text: question }]);
    setQuery("");

    // save to the database (first question creates the conversation)
    try {
      if (!convId) {
        const created = await createConversation({ role: "user", text: question });
        setConvId(created.id);
      } else {
        await addMessage(convId, { role: "user", text: question });
      }
    } catch {
      /* chat still works if saving fails */
    }
  };

  /* EDIT PROFILE — opens inside the Assistant */
  if (editing) {
    return (
      <div className="assistant-page">
        <MyProfile
          initial={profile}
          onBack={() => setEditing(false)}
          onSaved={(data) => {
            onProfileUpdated(data);
            setEditing(false);
            setNotice("Financial profile updated successfully.");
            setTimeout(() => setNotice(""), 3000);
          }}
        />
      </div>
    );
  }

  return (
    <div className="assistant-page">

      {notice && <div className="st-notice success">{notice}</div>}

      {/* TITLE + GREETING BOX + RECOMMENDATION */}
      <div className={`assistant-welcome ${messages.length > 0 ? "has-chat" : ""}`}>

        <h1>Financial Assistant</h1>

        <p>
          Your personalized financial companion for questions,
          analysis, and investment guidance.
        </p>

        <div className="assistant-greeting">
          <div className="greet-card">
            <div className="greet-text">
              <h2>{greeting()}, {firstName}</h2>
              <p>Welcome back. Let’s pick up where we left off.</p>
            </div>

            <div className="greet-profile">
              <div className="greet-ring" style={{ "--p": completeness }}>
                <span>{completeness}%</span>
              </div>

              <div className="greet-profile-text">
                <strong>Financial profile</strong>
                <span className={ready ? "ok" : "warn"}>
                  {ready
                    ? "Financial context complete"
                    : context.status === "CONFLICTING_CONTEXT"
                    ? "Context needs review"
                    : "More information needed"}
                </span>
              </div>

              <button type="button" className="btn-outline" onClick={openEditor}>
                Edit profile
              </button>
            </div>
          </div>

          {!ready && <ContextStatus context={context} onEdit={openEditor} />}
        </div>

        {!ready ? (
          <div className="assistant-profile-prompt">
            <div className="assistant-prompt-title">
              {context.status === "CONFLICTING_CONTEXT"
                ? "Review your financial profile"
                : "Complete your financial profile"}
            </div>

            <p>
              {context.status === "CONFLICTING_CONTEXT"
                ? "Personalized recommendations are paused until your profile is reviewed."
                : "Personalized recommendations are paused until your profile is complete."}
            </p>

            <button type="button" onClick={openEditor}>
              Edit Financial Profile
            </button>
          </div>
        ) : (
          <div className="assistant-recommendation">

            <div className="assistant-rec-header">
              <div>
                <div className="assistant-rec-label">PERSONALIZED ANALYSIS</div>
                <h2>Recommended Investment</h2>
              </div>

              <div className="assistant-rec-confidence">
                84%
                <span>Confidence</span>
              </div>
            </div>

            <div className="assistant-stock-row">
              <div>
                <div className="assistant-stock-name">NVIDIA Corporation</div>
                <div className="assistant-stock-ticker">NVDA</div>
              </div>

              <div className="assistant-sentiment">
                <TrendingUp size={14} />
                Positive
              </div>
            </div>

            <div className="assistant-rec-section">
              <div className="assistant-rec-section-title">
                Why this recommendation?
              </div>

              <p>
                Strong alignment with your investment horizon and moderate
                risk profile, supported by positive recent financial signals.
              </p>
            </div>

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

      {/* SUGGESTIONS (before chatting) OR CHAT (below the recommendation) */}
      {messages.length === 0 ? (
        <div className="assistant-suggestions">
          <div className="assistant-suggestions-title">Suggested Queries</div>

          <div className="assistant-query-list">
            {SUGGESTED_QUERIES.map((question) => (
              <button key={question} onClick={() => handleAsk(question)}>
                {question}
              </button>
            ))}
          </div>
        </div>
      ) : (
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
                <div className="assistant-message-label">You</div>
              )}

              <div className="assistant-message-text">{message.text}</div>
            </div>
          ))}

          <div ref={chatEndRef} />
        </div>
      )}

      {/* INPUT */}
      <div
        className={`assistant-input-wrapper ${
          messages.length > 0 ? "assistant-input-chat-mode" : ""
        }`}
      >
        <input
          type="text"
          value={query}
          placeholder="Ask anything about finance..."
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAsk();
          }}
        />

        <button onClick={() => handleAsk()} aria-label="Send question">
          <ArrowUp size={17} />
        </button>
      </div>

      <div className="assistant-disclaimer">
        FinGuide can make mistakes. Please verify important information. © 2026 FinGuide
      </div>

    </div>
  );
}