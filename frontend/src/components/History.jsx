import { useEffect, useState } from "react";
import {
  Search,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import {
  deleteConversation,
  listConversations,
  renameConversation,
} from "../api";

// the backend sends UTC times without a "Z", so add it before reading
const toDate = (iso) =>
  new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);

function groupOf(iso) {
  const d = toDate(iso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (d >= today) return "Today";

  const week = new Date(today);
  week.setDate(week.getDate() - 7);
  return d >= week ? "Previous 7 days" : "Older";
}

const formatDate = (iso) =>
  toDate(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

export default function History({ onOpenChat, onStartChat }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [openMenu, setOpenMenu] = useState(null);
  const [notice, setNotice] = useState(null);

  const flash = (type, text) => {
    setNotice({ type, text });
    setTimeout(() => setNotice(null), 2500);
  };

  // load this user's saved conversations
  useEffect(() => {
    listConversations()
      .then(setItems)
      .catch((e) => flash("error", e.message))
      .finally(() => setLoading(false));
  }, []);

  // click anywhere else to close the menu
  useEffect(() => {
    const close = () => setOpenMenu(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const handleRename = async (item) => {
    setOpenMenu(null);
    const title = window.prompt("Rename conversation:", item.title);
    if (!title || !title.trim()) return;

    try {
      const updated = await renameConversation(item.id, title.trim());
      setItems((prev) =>
        prev.map((c) => (c.id === item.id ? { ...c, title: updated.title } : c))
      );
      flash("success", "Conversation renamed.");
    } catch (e) {
      flash("error", e.message);
    }
  };

  const handleDelete = async (item) => {
    setOpenMenu(null);
    if (!window.confirm("Delete this conversation?")) return;

    try {
      await deleteConversation(item.id);
      setItems((prev) => prev.filter((c) => c.id !== item.id));
      flash("success", "Conversation deleted.");
    } catch (e) {
      flash("error", e.message);
    }
  };

  const filtered = items.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="history-page">
      {notice && <div className={`st-notice ${notice.type}`}>{notice.text}</div>}

      <div className="history-header">
        <h1>History</h1>
        <p>Your previous conversations with FinGuide.</p>
      </div>

      <div className="history-search">
        <Search size={16} />

        <input
          type="text"
          value={search}
          placeholder="Search conversations..."
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="history-list">
        {loading ? (
          <div className="history-empty">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="history-empty">
            {items.length === 0 ? (
              <>
                <p>No conversations yet.</p>
                <button type="button" className="btn-fill" onClick={onStartChat}>
                  Ask your first question
                </button>
              </>
            ) : (
              "No conversations found."
            )}
          </div>
        ) : (
          filtered.map((item, index) => {
            const group = groupOf(item.updated_at);
            const showGroup =
              index === 0 || groupOf(filtered[index - 1].updated_at) !== group;

            return (
              <div key={item.id}>
                {showGroup && <div className="history-date-group">{group}</div>}

                <div className="history-chat-item" onClick={() => onOpenChat(item.id)}>
                  <div className="history-chat-icon">
                    <MessageSquare size={17} />
                  </div>

                  <div className="history-chat-content">
                    <div className="history-chat-title">{item.title}</div>

                    <div className="history-chat-meta">
                      <span>
                        {item.message_count}{" "}
                        {item.message_count === 1 ? "message" : "messages"}
                      </span>
                      <span>·</span>
                      <span>{formatDate(item.updated_at)}</span>
                    </div>
                  </div>

                  <div
                    className="history-menu-wrapper"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      className={`history-more-button ${
                        openMenu === item.id ? "open" : ""
                      }`}
                      onClick={() =>
                        setOpenMenu(openMenu === item.id ? null : item.id)
                      }
                    >
                      <MoreHorizontal size={18} />
                    </button>

                    {openMenu === item.id && (
                      <div className="history-menu">
                        <button type="button" onClick={() => handleRename(item)}>
                          <Pencil size={14} />
                          Rename
                        </button>

                        <button
                          type="button"
                          className="history-delete"
                          onClick={() => handleDelete(item)}
                        >
                          <Trash2 size={14} />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}