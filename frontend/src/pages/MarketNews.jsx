import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, RefreshCw, Search, X } from "lucide-react";
import { fetchNews } from "../api";

const CACHE_KEY = "fg_news_v4";
const PAGE = 12;

const TABS = [
  { id: "india", label: "India", icon: "🇮🇳" },
  { id: "global", label: "US & Global", icon: "🌎" },
  { id: "crypto", label: "Crypto", icon: "₿" },
];

const readCache = () => { try { return JSON.parse(localStorage.getItem(CACHE_KEY)); } catch { return null; } };
const writeCache = (d) => { try { localStorage.setItem(CACHE_KEY, JSON.stringify(d)); } catch { /* ignore */ } };

/* ---------- text helpers ---------- */
const ta = document.createElement("textarea");
function decode(text = "") {               // twice: some feeds double-encode (&amp;nbsp;)
  let out = text;
  for (let i = 0; i < 2; i++) { ta.innerHTML = out; out = ta.value; }
  return out.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
}
const BOILERPLATE = [/^click to read more/i, /^read more/i, /^continue reading/i, /^the post .* appeared first on/i];
function cleanSummary(s = "") {
  return decode(s).split(/(?<=[.!?])\s+/).filter((x) => !BOILERPLATE.some((re) => re.test(x))).join(" ").trim();
}
const SOURCES = {
  "economictimes.indiatimes.com": "Economic Times", "economic times": "Economic Times",
  "livemint.com": "Mint", mint: "Mint", "moneycontrol.com": "Moneycontrol",
  "seekingalpha.com": "Seeking Alpha", "financefeeds.com": "FinanceFeeds",
};
const sourceName = (raw = "") => SOURCES[raw.trim().toLowerCase().replace(/^www\./, "")] || raw;

const AVATARS = ["#1E3A8A", "#0F766E", "#B45309", "#6D28D9", "#B91C1C", "#0369A1"];
function avatarColor(name) {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 997;
  return AVATARS[h % AVATARS.length];
}

/* ---------- time ---------- */
function timeAgo(iso) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`;
}
function bucket(iso) {
  const h = (Date.now() - new Date(iso).getTime()) / 36e5;
  if (h < 1) return "Last hour";
  if (h < 24) return "Past 24 hours";
  return "Older";
}

/* ---------- tabs ---------- */
const isCrypto = (n) => n.category === "Crypto" || /bitcoin|ethereum|crypto/i.test(n.title || "");
const byNewest = (a, b) => new Date(b.published_at) - new Date(a.published_at);
const dedupe = (list) => [...new Map(list.map((n) => [n.id, n])).values()];

function splitIntoTabs(all) {
  const pool = dedupe(all).sort(byNewest);
  return {
    india: pool.filter((n) => !isCrypto(n) && n.region === "India"),
    global: pool.filter((n) => !isCrypto(n) && n.region !== "India"),
    crypto: pool.filter(isCrypto),
  };
}

/* ---------- mood: real sentiment if the API gave one, else a guess from the headline ---------- */
const POS = /\b(surge[sd]?|jump(s|ed)?|rall(y|ies|ied)|rise[sn]?|rising|gain(s|ed)?|climb(s|ed)?|soar(s|ed)?|beats?|upbeat|bullish|boost(s|ed)?|rebound(s|ed)?|strong|upper circuit|record high|hits? (a )?(52-week )?high)\b/i;
const NEG = /\b(fall(s|en)?|drop(s|ped)?|crash(es|ed)?|plunge[sd]?|slump(s|ed)?|sink(s)?|sank|tumble[sd]?|slide[sd]?|loss(es)?|weak(er|est)?|bearish|miss(es|ed)?|sell-?off|decline[sd]?|lower circuit|fraud|probe|warn(s|ed)?)\b/i;

function moodOf(n) {
  if (n.sentiment === "positive" || n.sentiment === "negative") return { kind: n.sentiment, guessed: false };
  if (n.sentiment === "neutral") return { kind: "neutral", guessed: false };
  const t = n.title || "";
  const p = POS.test(t), g = NEG.test(t);
  if (p && !g) return { kind: "positive", guessed: true };
  if (g && !p) return { kind: "negative", guessed: true };
  return { kind: "none", guessed: false };
}

/* ---------- small shared pieces ---------- */
function Top({ n, mood }) {
  const source = sourceName(n.source);
  const showMood = mood.kind === "positive" || mood.kind === "negative" || (mood.kind === "neutral" && !mood.guessed);
  return (
    <div className="news-top">
      <span className="news-avatar" style={{ background: avatarColor(source) }} aria-hidden="true">
        {source.slice(0, 1).toUpperCase()}
      </span>
      <div className="news-meta">
        <span className="news-source">{source}</span>
        <time dateTime={n.published_at}>{timeAgo(n.published_at)}</time>
      </div>
      {showMood && (
        <span
          className={`news-sent news-sent-${mood.kind}`}
          title={mood.guessed ? "Estimated from the headline wording" : "Sentiment from the news provider"}
        >
          {mood.kind[0].toUpperCase() + mood.kind.slice(1)}
        </span>
      )}
    </div>
  );
}

function Foot({ n }) {
  const tickers = (n.tickers || []).slice(0, 2);
  return (
    <div className="news-foot">
      <div className="news-chips">
        <span className={`news-cat news-cat-${(n.category || "markets").toLowerCase()}`}>{n.category}</span>
        {tickers.map((t) => <span key={t} className="news-ticker">{t}</span>)}
      </div>
      <a className="news-read" href={n.url} target="_blank" rel="noopener noreferrer">
        Read article <ArrowUpRight size={14} aria-hidden="true" />
      </a>
    </div>
  );
}

// click or press Enter / Space on a box to highlight it
function selectable(id, selected, setSelected) {
  return {
    tabIndex: 0,
    "aria-current": selected === id ? "true" : undefined,
    onClick: () => setSelected(selected === id ? null : id),
    onKeyDown: (e) => {
      if (e.target !== e.currentTarget) return;
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(selected === id ? null : id); }
    },
  };
}

/* ---------- top story ---------- */
function Lead({ n, selected, setSelected }) {
  const [bad, setBad] = useState(false);
  const summary = cleanSummary(n.summary);
  const mood = moodOf(n);
  const hasImg = n.image && !bad;
  return (
    <article
      className={`news-lead s-${mood.kind} ${selected === n.id ? "is-selected" : ""}`}
      {...selectable(n.id, selected, setSelected)}
    >
      {hasImg && (
        <div className="news-lead-img">
          <img src={n.image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setBad(true)} />
        </div>
      )}
      <div className="news-lead-body">
        <span className="news-flag">Top story</span>
        <Top n={n} mood={mood} />
        <h2><a href={n.url} target="_blank" rel="noopener noreferrer">{decode(n.title)}</a></h2>
        {summary && <p>{summary}</p>}
        <Foot n={n} />
      </div>
    </article>
  );
}

/* ---------- trending list ---------- */
function Trending({ list, selected, setSelected }) {
  return (
    <aside className="news-side" aria-label="Also trending">
      <h2 className="news-side-title">Also trending</h2>
      <ol>
        {list.map((n, i) => {
          const mood = moodOf(n);
          return (
            <li key={n.id} className={selected === n.id ? "is-selected" : ""} {...selectable(n.id, selected, setSelected)}>
              <span className="news-rank">{i + 1}</span>
              <div>
                <a href={n.url} target="_blank" rel="noopener noreferrer">{decode(n.title)}</a>
                <span className="news-side-meta">
                  {sourceName(n.source)} · {timeAgo(n.published_at)}
                  {(mood.kind === "positive" || mood.kind === "negative") && (
                    <i className={`news-dot news-dot-${mood.kind}`} title={mood.kind} />
                  )}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}

/* ---------- regular box ---------- */
function Card({ n, index, selected, setSelected }) {
  const summary = cleanSummary(n.summary);
  const mood = moodOf(n);
  return (
    <article
      className={`news-card s-${mood.kind} ${selected === n.id ? "is-selected" : ""}`}
      style={{ "--i": Math.min(index, 11) }}
      {...selectable(n.id, selected, setSelected)}
    >
      <Top n={n} mood={mood} />
      <h3><a href={n.url} target="_blank" rel="noopener noreferrer">{decode(n.title)}</a></h3>
      {summary && <p>{summary}</p>}
      <Foot n={n} />
    </article>
  );
}

/* ---------- page ---------- */
export default function MarketNews() {
  const [data, setData] = useState(readCache);            // { india: [], global: [], crypto: [] }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState(null);
  const [tab, setTab] = useState("india");
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(PAGE);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      // one request per region/topic so a busy one can't push the others out
      const results = await Promise.allSettled([
        fetchNews({ region: "India", limit: 60 }),
        fetchNews({ region: "US", limit: 40 }),
        fetchNews({ region: "Global", limit: 30 }),
        fetchNews({ category: "Crypto", limit: 40 }),
      ]);
      if (results.every((r) => r.status === "rejected")) throw new Error("Could not load news.");
      const all = results.flatMap((r) => (r.status === "fulfilled" ? r.value.items || [] : []));
      const next = splitIntoTabs(all);
      setData(next);
      writeCache(next);
      setUpdated(new Date());
    } catch (e) {
      setError(e.message || "Could not load news.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [load]);

  const searched = useMemo(() => {
    const q = query.trim().toLowerCase();
    const run = (list = []) => !q ? list : list.filter((n) =>
      `${n.title} ${n.summary} ${n.source} ${(n.tickers || []).join(" ")}`.toLowerCase().includes(q));
    return { india: run(data?.india), global: run(data?.global), crypto: run(data?.crypto) };
  }, [data, query]);

  const items = searched[tab];

  // top story + 3 trending, only when not searching and there is enough news
  const magazine = !query.trim() && items.length >= 5;
  const lead = magazine ? items[0] : null;
  const trending = magazine ? items.slice(1, 4) : [];
  const rest = magazine ? items.slice(4) : items;

  const groups = useMemo(() => {
    const out = [];
    rest.slice(0, shown).forEach((n, i) => {
      const name = bucket(n.published_at);
      const last = out[out.length - 1];
      if (last && last.name === name) last.items.push({ n, i });
      else out.push({ name, items: [{ n, i }] });
    });
    return out;
  }, [rest, shown]);

  const pickTab = (id) => { setTab(id); setShown(PAGE); setSelected(null); };
  const onSearch = (v) => { setQuery(v); setShown(PAGE); setSelected(null); };

  return (
    <section className="news">
      <header className="news-hero">
        <h1>Market News</h1>
        <p>
          Latest updates from the stock market, economy and crypto.
          {updated && (
            <span className="news-live">
              <i aria-hidden="true" /> Updated {updated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </p>
      </header>

      <div className="news-bar">
        <div className="news-tabs" role="tablist" aria-label="News categories">
          {TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
              className={`news-tab ${tab === t.id ? "is-active" : ""}`} onClick={() => pickTab(t.id)}>
              <span aria-hidden="true">{t.icon}</span>
              {t.label}
              <span className="news-tab-count">{searched[t.id].length}</span>
            </button>
          ))}
        </div>

        <div className="news-actions">
          <label className="news-search">
            <Search size={16} aria-hidden="true" />
            <input type="search" value={query} onChange={(e) => onSearch(e.target.value)}
              placeholder="Search headlines, stocks, sources" aria-label="Search news" />
            {query && (
              <button type="button" className="news-clear" onClick={() => onSearch("")} aria-label="Clear search">
                <X size={14} />
              </button>
            )}
          </label>
          <button type="button" className="btn-fill news-refresh" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "news-spin" : ""} aria-hidden="true" />
            {loading ? "Updating" : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <p className="news-note news-note-error" role="alert">
          {data ? "Could not refresh, showing saved headlines." : `${error} Check that the backend is running, then tap Refresh.`}
        </p>
      )}

      {!data && loading && (
        <div className="news-grid" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="news-card news-skel" />)}
        </div>
      )}

      {data && !items.length && !loading && (
        <p className="news-empty">
          {query
            ? `No stories match “${query}” in this tab.`
            : tab === "crypto"
              ? "No crypto stories yet. The backend picks them up on its next fetch (every 15 minutes)."
              : "No stories in this tab right now."}
        </p>
      )}

      {lead && (
        <div className="news-feature" key={`f-${tab}`}>
          <Lead n={lead} selected={selected} setSelected={setSelected} />
          <Trending list={trending} selected={selected} setSelected={setSelected} />
        </div>
      )}

      <div key={`g-${tab}-${query}`}>
        {groups.map((g) => (
          <section key={g.name} className="news-group">
            <h2 className="news-group-title">
              {g.name}
              <span>{g.items.length} {g.items.length === 1 ? "story" : "stories"}</span>
            </h2>
            <div className="news-grid">
              {g.items.map(({ n, i }) => (
                <Card key={n.id} n={n} index={i} selected={selected} setSelected={setSelected} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {rest.length > shown && (
        <div className="news-more">
          <button type="button" className="btn-outline" onClick={() => setShown((s) => s + PAGE)}>
            Show more ({rest.length - shown} left)
          </button>
        </div>
      )}
    </section>
  );
}