import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Newspaper, RefreshCw } from "lucide-react";
import { fetchNews } from "../api";
import "../styles.css";

const CACHE_KEY = "fg_news_v1";
const readCache = () => {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY));
  } catch {
    return null;
  }
};
const writeCache = (d) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(d));
  } catch {
    /* ignore */
  }
};

const minsAgo = (iso) => Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
function timeAgo(iso) {
  const m = minsAgo(iso);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`;
}
function hue(name = "") {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

const BRAND = {
  "Economic Times": ["ET", "#d6232a"],
  Moneycontrol: ["m", "#2e9e4f"],
  Mint: ["m", "#e8820e"],
};
const TICKER_WORDS = [
  [/nifty/i, "NIFTY 50"], [/sensex/i, "SENSEX"], [/reliance|\bjio\b/i, "RELIANCE"],
  [/\btcs\b|tata consultancy/i, "TCS"], [/infosys|\binfy\b/i, "INFY"], [/hdfc/i, "HDFC"],
  [/icici/i, "ICICI"], [/\bsbi\b|state bank/i, "SBI"], [/wipro/i, "WIPRO"], [/adani/i, "ADANI"],
  [/bajaj/i, "BAJAJ"], [/gold/i, "GOLD"], [/silver/i, "SILVER"], [/crude|brent/i, "CRUDE"],
  [/rupee/i, "USDINR"], [/bitcoin/i, "BTC"], [/nasdaq/i, "NASDAQ"], [/s&p 500/i, "S&P 500"],
];

function chipsFor(n) {
  if (n.tickers?.length) return n.tickers.slice(0, 3);
  const text = `${n.title} ${n.summary}`;
  const out = [];
  for (const [re, t] of TICKER_WORDS) {
    if (re.test(text) && !out.includes(t)) out.push(t);
    if (out.length === 3) break;
  }
  return out;
}

function Logo({ name }) {
  const [txt, color] = BRAND[name] || [name.slice(0, 2).toUpperCase(), `hsl(${hue(name)} 42% 40%)`];
  return (
    <span className="fn-logo" style={{ background: color }} aria-hidden="true">
      {txt}
    </span>
  );
}

const Cat = ({ c }) => <span className={`fn-cat fn-cat-${c.toLowerCase()}`}>{c}</span>;

function Hero({ n }) {
  const [bad, setBad] = useState(false);
  const showImg = n.image && !bad;
  return (
    <article className="fn-hero">
      <div className={`fn-hero-media${showImg ? "" : " fn-hero-ph"}`}>
        {showImg ? (
          <img src={n.image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setBad(true)} />
        ) : (
          <Newspaper size={46} aria-hidden="true" />
        )}
      </div>
      <div className="fn-hero-body">
        <div className="fn-top">
          <span className="fn-who">
            <Logo name={n.source} />
            <span className="fn-source">{n.source}</span>
            <time dateTime={n.published_at}>{timeAgo(n.published_at)}</time>
          </span>
          <Cat c={n.category} />
        </div>
        <h2 className="fn-hero-title">{n.title}</h2>
        {n.summary && <p className="fn-hero-summary">{n.summary}</p>}
        <a className="fn-read" href={n.url} target="_blank" rel="noopener noreferrer">
          Read article <ArrowRight size={15} aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}

function Card({ n }) {
  const chips = chipsFor(n);
  return (
    <article className="fn-card">
      <div className="fn-top">
        <span className="fn-who">
          <Logo name={n.source} />
          <span className="fn-source">{n.source}</span>
          <time dateTime={n.published_at}>{timeAgo(n.published_at)}</time>
        </span>
        <Cat c={n.category} />
      </div>
      <h3 className="fn-title">
        <a href={n.url} target="_blank" rel="noopener noreferrer">
          {n.title}
        </a>
      </h3>
      {n.summary && <p className="fn-summary">{n.summary}</p>}
      {(chips.length > 0 || n.sentiment) && (
        <div className="fn-chips">
          {chips.map((t) => (
            <span key={t} className="fn-ticker" style={{ "--c": `hsl(${hue(t)} 55% 42%)` }}>
              {t}
            </span>
          ))}
          {n.sentiment && <span className={`fn-sent fn-sent-${n.sentiment}`}>{n.sentiment}</span>}
        </div>
      )}
    </article>
  );
}

function Skeleton() {
  return (
    <div className="fn-grid" aria-hidden="true">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="fn-card fn-skel">
          <span className="fn-sk" style={{ width: "45%" }} />
          <span className="fn-sk fn-sk-tall" />
          <span className="fn-sk" style={{ width: "85%" }} />
        </div>
      ))}
    </div>
  );
}

const PAGE_SIZE = 12;

export default function MarketNews() {
  const [data, setData] = useState(readCache);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [order, setOrder] = useState("latest");
  const [page, setPage] = useState(1);
  const listRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchNews({ limit: 100 });
      setData(res);
      writeCache(res);
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

  const { hero, rest } = useMemo(() => {
    const items = data?.items ?? [];
    if (!items.length) return { hero: null, rest: [] };
    // Prefer a recent story that has a picture for the big headline.
    const h = items.slice(0, 12).find((i) => i.image) || items[0];
    const others = items.filter((i) => i.id !== h.id);
    return { hero: h, rest: order === "oldest" ? [...others].reverse() : others };
  }, [data, order]);

  const hasItems = !!hero;
  const totalPages = Math.max(1, Math.ceil(rest.length / PAGE_SIZE));
  const current = Math.min(page, totalPages);
  const start = current === 1 ? 0 : 8 + (current - 2) * PAGE_SIZE;
  const visible = rest.slice(start, start + (current === 1 ? 8 : PAGE_SIZE));
  const goTo = (p) => {
    setPage(p);
    listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <section className="fg-news">
      <header className="fn-head">
        <div>
          <h1>Market News</h1>
          <p className="fn-sub">Latest updates from the stock market, economy and global financial markets.</p>
        </div>
        <button type="button" className="fn-refresh" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? "fn-spin" : ""} aria-hidden="true" />
          {loading ? "Updating" : "Refresh"}
        </button>
      </header>

      {data?.stale && (
        <p className="fn-note" role="status">
          No news from the last 48 hours yet. Showing the latest saved headlines.
        </p>
      )}
      {error && (
        <p className="fn-note fn-note-error" role="alert">
          {hasItems ? "Could not refresh, showing saved headlines." : `${error} Check that the backend is running, then tap Refresh.`}
        </p>
      )}

      {!hasItems && loading && <Skeleton />}
      {!hasItems && !loading && !error && (
        <p className="fn-empty">No headlines yet. Check back in a few minutes.</p>
      )}

      {hero && current === 1 && <Hero n={hero} />}

      {rest.length > 0 && (
        <>
          <div className="fn-sechead" ref={listRef}>
            <h2>
              Latest News
              <span className="fn-count">
                {start + 1}{"\u2013"}{Math.min(start + PAGE_SIZE, rest.length)} of {rest.length}
              </span>
            </h2>
            <label className="fn-sort">
              <span className="fn-sr">Sort order</span>
              <select
                value={order}
                onChange={(e) => {
                  setOrder(e.target.value);
                  setPage(1);
                }}
              >
                <option value="latest">Latest</option>
                <option value="oldest">Oldest</option>
              </select>
            </label>
          </div>

          <div className="fn-grid">
            {visible.map((n) => (
              <Card key={n.id} n={n} />
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="fn-pager" aria-label="News pages">
              <button type="button" onClick={() => goTo(current - 1)} disabled={current === 1}>
                Previous
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={p === current ? "is-current" : ""}
                  aria-current={p === current ? "page" : undefined}
                  onClick={() => goTo(p)}
                >
                  {p}
                </button>
              ))}
              <button type="button" onClick={() => goTo(current + 1)} disabled={current === totalPages}>
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}