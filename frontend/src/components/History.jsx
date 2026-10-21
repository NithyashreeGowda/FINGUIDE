import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Search,
  MessageSquare,
  MessagesSquare,
  Clock3,
  Download,
  Sparkles,
  X,
  Pencil,
  Trash2,
  Copy,
  Check,
  Bookmark,
  BookmarkCheck,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  FileText,
  FileJson,
  FileType2,
} from "lucide-react";

import {
  listConversations,
  getConversation,
  renameConversation,
  deleteConversation,
  getHistorySummary,
  saveHistorySummary,
  getHistoryPreviews,
  downloadHistoryExport,
} from "../api";

import "../styles.css";

const isValidDate = (v) => Boolean(v) && !Number.isNaN(new Date(v).getTime());

const dateLabel = (v) =>
  isValidDate(v)
    ? new Date(v).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Date unavailable";

const timeLabel = (v) =>
  isValidDate(v)
    ? new Date(v).toLocaleTimeString(undefined, {
        hour: "numeric",
        minute: "2-digit",
      })
    : "";

const stamp = (item) => item.updated_at || item.created_at;
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

const SORTERS = {
  title: (a, b) =>
    (a.title || "Untitled chat").localeCompare(b.title || "Untitled chat"),
  date: (a, b) => new Date(stamp(a) || 0) - new Date(stamp(b) || 0),
  messages: (a, b) => (a.message_count || 0) - (b.message_count || 0),
};

const SCOPES = [
  { value: "all", label: "All chats", hint: "Messages, plus the summary for chats where you saved one" },
  { value: "selected", label: "Selected chat", hint: "Only the chat you have open, with its saved summary" },
  { value: "summaries", label: "Saved summaries", hint: "Summaries only, without the messages" },
];

const FORMATS = [
  { value: "pdf", label: "PDF", icon: FileText },
  { value: "txt", label: "Text", icon: FileType2 },
  { value: "json", label: "JSON", icon: FileJson },
];

export default function History({ onOpenAssistant }) {
  const [conversations, setConversations] = useState([]);
  const [previews, setPreviews] = useState({});
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("date");
  const [sortDir, setSortDir] = useState("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [openId, setOpenId] = useState(null);
  const [chat, setChat] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [tab, setTab] = useState("chat");
  const [copied, setCopied] = useState(false);

  const [summary, setSummary] = useState(null);
  const [summarySaved, setSummarySaved] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState("");
  const [confirmId, setConfirmId] = useState(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exportScope, setExportScope] = useState("all");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [exporting, setExporting] = useState(false);

  const timer = useRef(null);

  const flash = useCallback((text) => {
    setNotice(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setNotice(""), 3000);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);

  /* ---------- load ---------- */

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setConversations((await listConversations()) || []);
      // previews are a nice extra; the page works without them
      getHistoryPreviews()
        .then((r) => setPreviews(r?.previews || {}))
        .catch(() => {});
    } catch (e) {
      setError(e.message || "Could not load your history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /* ---------- list ---------- */

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const sorter = SORTERS[sortKey];

    return conversations
      .filter((c) => !q || (c.title || "Untitled chat").toLowerCase().includes(q))
      .sort((a, b) => (sortDir === "asc" ? sorter(a, b) : sorter(b, a)));
  }, [conversations, search, sortKey, sortDir]);

  const totalMessages = useMemo(
    () => conversations.reduce((s, c) => s + (c.message_count || 0), 0),
    [conversations]
  );

  const latest = useMemo(() => {
    const dates = conversations.map(stamp).filter(isValidDate);
    if (!dates.length) return null;
    return dates.sort((a, b) => new Date(b) - new Date(a))[0];
  }, [conversations]);

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "title" ? "asc" : "desc");
    }
  }

  /* ---------- open chat ---------- */

  async function openChat(id, startTab = "chat") {
    setOpenId(id);
    setChat(null);
    setSummary(null);
    setSummarySaved(false);
    setTab(startTab);
    setChatLoading(true);
    setError("");

    try {
      const data = await getConversation(id);
      setChat(data);
      if (startTab === "summary") loadSummary(id);
    } catch (e) {
      setError(e.message || "Could not open that chat.");
      setOpenId(null);
    } finally {
      setChatLoading(false);
    }
  }

  const closeChat = useCallback(() => {
    setOpenId(null);
    setChat(null);
  }, []);

  /* ---------- summary ---------- */

  async function loadSummary(id = openId) {
    if (!id) return;
    setSummaryLoading(true);
    try {
      const result = await getHistorySummary(id);
      setSummary(result.summary);
      setSummarySaved(Boolean(result.saved));
    } catch (e) {
      setError(e.message || "Could not create a summary.");
    } finally {
      setSummaryLoading(false);
    }
  }

  function showSummary() {
    setTab("summary");
    if (!summary) loadSummary();
  }

  async function saveSummary() {
    if (!openId || !summary) return;
    setSummaryLoading(true);
    try {
      const result = await saveHistorySummary(openId, summary);
      setSummary(result.summary);
      setSummarySaved(true);
      flash("Summary saved.");
    } catch (e) {
      setError(e.message || "Could not save the summary.");
    } finally {
      setSummaryLoading(false);
    }
  }

  /* ---------- rename / delete ---------- */

  async function commitRename(item) {
    const next = renameValue.trim();
    setRenamingId(null);
    if (!next || next === item.title) return;

    try {
      await renameConversation(item.id, next);
      setConversations((list) =>
        list.map((c) => (c.id === item.id ? { ...c, title: next } : c))
      );
      flash("Chat renamed.");
    } catch (e) {
      setError(e.message || "Could not rename the chat.");
    }
  }

  async function confirmDelete(item) {
    setConfirmId(null);
    try {
      await deleteConversation(item.id);
      setConversations((list) => list.filter((c) => c.id !== item.id));
      if (openId === item.id) closeChat();
      flash("Chat deleted.");
    } catch (e) {
      setError(e.message || "Could not delete the chat.");
    }
  }

  /* ---------- copy / export ---------- */

  async function copyChat() {
    if (!chat) return;
    const text = (chat.messages || [])
      .map((m) => `${m.role === "user" ? "You" : "FinGuide"}: ${m.text || ""}`)
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Could not copy to the clipboard.");
    }
  }

  // Header button -> "all". Button inside an open chat -> "selected".
  function openExport(scope) {
    setExportScope(scope);
    setExportOpen(true);
  }

  async function handleExport() {
    if (exportScope === "selected" && !openId) {
      setError("Open a chat first, then export just that chat.");
      setExportOpen(false);
      return;
    }

    setExporting(true);
    setError("");

    try {
      const blob = await downloadHistoryExport({
        scope: exportScope,
        format: exportFormat,
        conversationId: exportScope === "selected" ? openId : null,
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `finguide-${exportScope}-history.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setExportOpen(false);
      flash("Export downloaded.");
    } catch (e) {
      setError(e.message || "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    if (!openId && !exportOpen) return undefined;
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      if (exportOpen) setExportOpen(false);
      else closeChat();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openId, exportOpen, closeChat]);

  /* ---------- render ---------- */

  const SortArrow = ({ k }) =>
    sortKey === k ? (
      sortDir === "asc" ? <ArrowUp size={13} /> : <ArrowDown size={13} />
    ) : null;

  return (
    <main className="hp">
      <header className="hp-head">
        <div>
          <h1>Conversation history</h1>
          <p>Review, summarize and export your past chats with FinGuide.</p>
        </div>

        <button className="hp-btn hp-primary" onClick={() => openExport("all")}>
          <Download size={16} />
          Export
        </button>
      </header>

      <div className="hp-stats">
        <div className="hp-stat">
          <span className="hp-stat-icon"><MessagesSquare size={18} /></span>
          <div>
            <small>Total chats</small>
            <strong>{conversations.length}</strong>
          </div>
        </div>
        <div className="hp-stat">
          <span className="hp-stat-icon"><MessageSquare size={18} /></span>
          <div>
            <small>Saved messages</small>
            <strong>{totalMessages}</strong>
          </div>
        </div>
        <div className="hp-stat">
          <span className="hp-stat-icon"><Clock3 size={18} /></span>
          <div>
            <small>Last activity</small>
            <strong>{latest ? dateLabel(latest) : "—"}</strong>
          </div>
        </div>
      </div>

      {error && (
        <div className="hp-banner hp-error" role="alert">
          <span>{error}</span>
          <button aria-label="Dismiss" onClick={() => setError("")}>
            <X size={14} />
          </button>
        </div>
      )}
      {notice && (
        <div className="hp-banner hp-ok" role="status">
          <Check size={15} />
          <span>{notice}</span>
        </div>
      )}

      <section className="hp-card" aria-label="Saved chats">
        <div className="hp-toolbar">
          <div className="hp-search">
            <Search size={16} aria-hidden="true" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats by title"
              aria-label="Search chats"
            />
            {search && (
              <button type="button" aria-label="Clear search" onClick={() => setSearch("")}>
                <X size={14} />
              </button>
            )}
          </div>

          <span className="hp-count">
            {rows.length === conversations.length
              ? plural(conversations.length, "chat")
              : `${rows.length} of ${conversations.length} chats`}
          </span>

          <button
            className="hp-icon"
            onClick={load}
            disabled={loading}
            title="Refresh"
            aria-label="Refresh history"
          >
            <RefreshCw size={16} className={loading ? "hp-spin" : ""} />
          </button>
        </div>

        <div className="hp-table" role="table" aria-label="Conversations">
          <div className="hp-tr hp-thead" role="row">
            <button role="columnheader" onClick={() => toggleSort("title")}>
              Chat <SortArrow k="title" />
            </button>
            <button role="columnheader" onClick={() => toggleSort("date")}>
              Last activity <SortArrow k="date" />
            </button>
            <button role="columnheader" onClick={() => toggleSort("messages")}>
              Messages <SortArrow k="messages" />
            </button>
            <span role="columnheader" className="hp-right">Actions</span>
          </div>

          {loading && conversations.length === 0 &&
            [0, 1, 2, 3].map((n) => <div key={n} className="hp-skel" />)}

          {!loading && conversations.length === 0 && (
            <div className="hp-empty">
              <MessageSquare size={30} />
              <h2>No chats yet</h2>
              <p>Ask FinGuide a question and it will show up here.</p>
              {onOpenAssistant && (
                <button className="hp-btn hp-primary" onClick={() => onOpenAssistant()}>
                  Start a chat
                </button>
              )}
            </div>
          )}

          {!loading && conversations.length > 0 && rows.length === 0 && (
            <div className="hp-empty">
              <Search size={28} />
              <h2>No matching chats</h2>
              <p>No chat title contains “{search}”.</p>
            </div>
          )}

          {rows.map((item) => {
            const title = item.title || "Untitled chat";
            const renaming = renamingId === item.id;
            const confirming = confirmId === item.id;
            const preview = previews[item.id];

            return (
              <div
                key={item.id}
                className="hp-tr hp-row"
                role="row"
                onClick={() => !renaming && !confirming && openChat(item.id)}
              >
                <div className="hp-cell hp-title" role="cell">
                  <span className="hp-row-icon">
                    <MessageSquare size={16} />
                  </span>

                  {renaming ? (
                    <input
                      className="hp-rename"
                      autoFocus
                      value={renameValue}
                      maxLength={120}
                      aria-label="Chat title"
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => commitRename(item)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.currentTarget.blur();
                        if (e.key === "Escape") setRenamingId(null);
                      }}
                    />
                  ) : (
                    <div className="hp-title-text">
                      <button
                        className="hp-title-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          openChat(item.id);
                        }}
                        title={title}
                      >
                        {title}
                      </button>
                      {preview && <span className="hp-preview">{preview}</span>}
                    </div>
                  )}
                </div>

                <div className="hp-cell hp-date" role="cell">
                  <span>{dateLabel(stamp(item))}</span>
                  <small>{timeLabel(stamp(item))}</small>
                </div>

                <div className="hp-cell" role="cell">
                  <span className="hp-badge">{item.message_count || 0}</span>
                </div>

                <div className="hp-cell hp-actions" role="cell" onClick={(e) => e.stopPropagation()}>
                  {confirming ? (
                    <div className="hp-confirm">
                      <span>Delete?</span>
                      <button className="hp-danger" onClick={() => confirmDelete(item)}>
                        Yes
                      </button>
                      <button onClick={() => setConfirmId(null)}>No</button>
                    </div>
                  ) : (
                    <>
                      <button className="hp-chip" onClick={() => openChat(item.id, "summary")}>
                        <Sparkles size={13} />
                        Summary
                      </button>
                      <button
                        className="hp-sq"
                        title="Rename"
                        aria-label={`Rename ${title}`}
                        onClick={() => {
                          setConfirmId(null);
                          setRenamingId(item.id);
                          setRenameValue(item.title || "");
                        }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        className="hp-sq hp-sq-del"
                        title="Delete"
                        aria-label={`Delete ${title}`}
                        onClick={() => setConfirmId(item.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ---------- Reader ---------- */}
      {openId && (
        <div
          className="hp-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closeChat();
          }}
        >
          <section className="hp-reader" role="dialog" aria-modal="true" aria-label="Chat">
            <header className="hp-reader-head">
              <div>
                <h2>{chat?.title || "Chat"}</h2>
                {chat && (
                  <p>
                    {dateLabel(stamp(chat))} · {plural(chat.messages?.length || 0, "message")}
                  </p>
                )}
              </div>
              <button className="hp-icon" onClick={closeChat} aria-label="Close">
                <X size={18} />
              </button>
            </header>

            <div className="hp-reader-bar">
              <div className="hp-tabs" role="tablist">
                <button
                  role="tab"
                  aria-selected={tab === "chat"}
                  className={tab === "chat" ? "on" : ""}
                  onClick={() => setTab("chat")}
                >
                  Conversation
                </button>
                <button
                  role="tab"
                  aria-selected={tab === "summary"}
                  className={tab === "summary" ? "on" : ""}
                  onClick={showSummary}
                  disabled={!chat}
                >
                  <Sparkles size={14} />
                  Smart summary
                </button>
              </div>

              {chat && (
                <div className="hp-reader-actions">
                  <button className="hp-btn hp-ghost" onClick={copyChat}>
                    {copied ? <Check size={15} /> : <Copy size={15} />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                  <button className="hp-btn hp-ghost" onClick={() => openExport("selected")}>
                    <Download size={15} />
                    Export
                  </button>
                  {onOpenAssistant && (
                    <button className="hp-btn hp-outline" onClick={() => onOpenAssistant(chat.id)}>
                      Continue chat
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="hp-reader-body">
              {chatLoading || !chat ? (
                <div className="hp-pad">
                  <div className="hp-skel" />
                  <div className="hp-skel" />
                </div>
              ) : tab === "summary" ? (
                <SummaryPanel
                  summary={summary}
                  loading={summaryLoading}
                  saved={summarySaved}
                  onSave={saveSummary}
                  onRefresh={() => loadSummary()}
                />
              ) : (
                <div className="hp-thread">
                  {(chat.messages || []).length === 0 && (
                    <p className="hp-muted">No saved messages in this chat.</p>
                  )}
                  {(chat.messages || []).map((m, i) => {
                    const mine = m.role === "user";
                    return (
                      <article key={i} className={`hp-msg ${mine ? "me" : "bot"}`}>
                        <header>
                          <span>{mine ? "You" : "FinGuide"}</span>
                          {isValidDate(m.at) && (
                            <time dateTime={m.at}>
                              {dateLabel(m.at)}, {timeLabel(m.at)}
                            </time>
                          )}
                        </header>
                        <p>{m.text}</p>
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      {/* ---------- Export ---------- */}
      {exportOpen && (
        <div
          className="hp-backdrop"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setExportOpen(false);
          }}
        >
          <section className="hp-modal" role="dialog" aria-modal="true" aria-labelledby="hp-ex-title">
            <button
              className="hp-icon hp-modal-x"
              onClick={() => setExportOpen(false)}
              aria-label="Close"
            >
              <X size={18} />
            </button>

            <h2 id="hp-ex-title">Export history</h2>
            <p className="hp-modal-sub">Download the chats saved to your account.</p>

            <div className="hp-group-title" id="hp-scope-title">What to export</div>
            <div className="hp-options" role="radiogroup" aria-labelledby="hp-scope-title">
              {SCOPES.map((s) => {
                const disabled = s.value === "selected" && !openId;

                return (
                  <button
                    key={s.value}
                    type="button"
                    role="radio"
                    aria-checked={exportScope === s.value}
                    disabled={disabled}
                    className={`hp-option ${exportScope === s.value ? "on" : ""}`}
                    onClick={() => setExportScope(s.value)}
                  >
                    <span className="hp-dot" aria-hidden="true" />
                    <span className="hp-option-text">
                      <strong>{s.label}</strong>
                      <small>
                        {s.value === "selected"
                          ? chat
                            ? chat.title || "Untitled chat"
                            : "Open a chat first to enable this"
                          : s.hint}
                      </small>
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="hp-group-title" id="hp-format-title">File format</div>
            <div className="hp-formats" role="radiogroup" aria-labelledby="hp-format-title">
              {FORMATS.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={exportFormat === value}
                  className={`hp-format ${exportFormat === value ? "on" : ""}`}
                  onClick={() => setExportFormat(value)}
                >
                  <Icon size={18} />
                  {label}
                  <small>.{value}</small>
                </button>
              ))}
            </div>

            <div className="hp-modal-actions">
              <button className="hp-btn hp-ghost" onClick={() => setExportOpen(false)}>
                Cancel
              </button>
              <button className="hp-btn hp-primary" onClick={handleExport} disabled={exporting}>
                <Download size={16} />
                {exporting ? "Preparing…" : "Download"}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

/* ---------- Smart summary ---------- */

function SummaryPanel({ summary, loading, saved, onSave, onRefresh }) {
  if (loading && !summary) {
    return (
      <div className="hp-pad">
        <div className="hp-skel" />
        <div className="hp-skel" />
        <div className="hp-skel" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="hp-empty">
        <Sparkles size={28} />
        <h2>No summary yet</h2>
        <p>Get the key points, decisions and next topics from this chat.</p>
        <button className="hp-btn hp-primary" onClick={onRefresh}>
          Generate summary
        </button>
      </div>
    );
  }

  const sections = [
    ["Key takeaways", "key_takeaways", "No key takeaways found."],
    ["Decisions", "decisions", "No explicit decisions identified."],
    ["Follow-up topics", "follow_up_topics", "No follow-up topics identified."],
  ];

  return (
    <div className="hp-summary">
      <div className="hp-summary-bar">
        <span>
          {summary.generated_at ? `Generated ${dateLabel(summary.generated_at)}` : "Just generated"}
          {saved && (
            <b className="hp-saved">
              <BookmarkCheck size={13} /> Saved
            </b>
          )}
        </span>

        <div>
          <button className="hp-btn hp-ghost" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={14} className={loading ? "hp-spin" : ""} />
            Refresh
          </button>
          <button className="hp-btn hp-primary" onClick={onSave} disabled={loading || saved}>
            <Bookmark size={14} />
            {saved ? "Saved" : "Save summary"}
          </button>
        </div>
      </div>

      {sections.map(([title, key, empty]) => {
        const values = summary[key] || [];
        return (
          <section key={key} className="hp-summary-card">
            <h3>{title}</h3>
            {values.length ? (
              <ul>
                {values.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            ) : (
              <p className="hp-muted">{empty}</p>
            )}
          </section>
        );
      })}

      <p className="hp-note">
        Built from your chat text, so it can miss context. This is general information, not financial advice.
      </p>
    </div>
  );
}