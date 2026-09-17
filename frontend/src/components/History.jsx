import { useState } from "react";
import {
  Search,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";

const INITIAL_RECORDS = [
  {
    dateGroup: "Today",
    title: "Why was NVIDIA recommended?",
    investment: "NVIDIA",
    sentiment: "Positive",
    confidence: "82%",
    date: "12 Sep 2026",
  },
  {
    dateGroup: "Previous 7 days",
    title: "Is Tata Motors suitable for me?",
    investment: "Tata Motors",
    sentiment: "Neutral",
    confidence: "58%",
    date: "05 Sep 2026",
  },
  {
    dateGroup: "Previous 7 days",
    title: "What are the risks with Adani Green?",
    investment: "Adani Green",
    sentiment: "Negative",
    confidence: "71%",
    date: "28 Aug 2026",
  },
];

export default function History() {
  const [records, setRecords] = useState(INITIAL_RECORDS);
  const [search, setSearch] = useState("");
  const [openMenu, setOpenMenu] = useState(null);

  const handleDelete = (index) => {
    setRecords((prev) => prev.filter((_, i) => i !== index));
    setOpenMenu(null);
  };

  const handleRename = (index) => {
    const currentTitle = records[index].title;
    const newTitle = window.prompt("Rename conversation:", currentTitle);

    if (!newTitle || !newTitle.trim()) return;

    setRecords((prev) =>
      prev.map((record, i) =>
        i === index
          ? { ...record, title: newTitle.trim() }
          : record
      )
    );

    setOpenMenu(null);
  };

  const filteredRecords = records.filter((record) =>
    `${record.title} ${record.investment}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <div className="history-page">
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
        {filteredRecords.length === 0 ? (
          <div className="history-empty">
            No conversations found.
          </div>
        ) : (
          filteredRecords.map((record, index) => {
            const originalIndex = records.indexOf(record);

            const showGroup =
              index === 0 ||
              filteredRecords[index - 1].dateGroup !== record.dateGroup;

            return (
              <div key={originalIndex}>
                {showGroup && (
                  <div className="history-date-group">
                    {record.dateGroup}
                  </div>
                )}

                <div className="history-chat-item">
                  <div className="history-chat-icon">
                    <MessageSquare size={17} />
                  </div>

                  <div className="history-chat-content">
                    <div className="history-chat-title">
                      {record.title}
                    </div>

                    <div className="history-chat-meta">
                      <span>{record.investment}</span>
                      <span>·</span>

                      <span
                        className={
                          record.sentiment === "Positive"
                            ? "history-positive"
                            : record.sentiment === "Negative"
                            ? "history-negative"
                            : "history-neutral"
                        }
                      >
                        {record.sentiment}
                      </span>

                      <span>·</span>
                      <span>{record.confidence} confidence</span>
                      <span>·</span>
                      <span>{record.date}</span>
                    </div>
                  </div>

                  <div className="history-menu-wrapper">
                    <button
                      type="button"
                      className="history-more-button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenu(
                          openMenu === originalIndex
                            ? null
                            : originalIndex
                        );
                      }}
                    >
                      <MoreHorizontal size={18} />
                    </button>

                    {openMenu === originalIndex && (
                      <div className="history-menu">
                        <button
                          type="button"
                          onClick={() =>
                            handleRename(originalIndex)
                          }
                        >
                          <Pencil size={14} />
                          Rename
                        </button>

                        <button
                          type="button"
                          className="history-delete"
                          onClick={() =>
                            handleDelete(originalIndex)
                          }
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