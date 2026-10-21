import { useCallback, useEffect, useState } from "react";
import {
  Cpu,
  Landmark,
  Car,
  Zap,
  Pill,
  ShoppingCart,
  Hammer,
  Building2,
} from "lucide-react";
import { fetchInsights } from "../api";
import "../styles.css";

const CACHE_KEY = "fg_insights_v5";

// Last good response is kept in the browser so the page paints instantly
// and never goes blank, even if the backend is slow or down.
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

const fmt = (n) =>
  Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sign = (n) => (n > 0 ? "+" : "");
const dir = (n) => (n > 0 ? "up" : n < 0 ? "down" : "flat");
const arrow = (d) => (d === "up" ? "\u25B2" : d === "down" ? "\u25BC" : "\u2013");
const clamp = (n, a, b) => Math.min(b, Math.max(a, n));
const minsSince = (iso) => Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));

function hue(name = "") {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

const SECTOR_ICON = { IT: Cpu, Bank: Landmark, Auto: Car, Energy: Zap, Pharma: Pill, FMCG: ShoppingCart, Metal: Hammer, Realty: Building2 };
const HERO = ["^NSEI", "^BSESN", "^GSPC", "^IXIC"];
const CHART_SYMS = ["^NSEI", "^BSESN", "^NSEBANK", "^GSPC", "^IXIC"];
const TAGS = { "^NSEI": "NSE", "^BSESN": "BSE", "^GSPC": "US", "^IXIC": "NASDAQ" };
const TZ = { "^NSEI": "Asia/Kolkata", "^BSESN": "Asia/Kolkata", "^NSEBANK": "Asia/Kolkata", "^GSPC": "America/New_York", "^IXIC": "America/New_York" };

const REGION_TZ = { India: "Asia/Kolkata", US: "America/New_York" };

// "Today" while the market trades, otherwise the date of the last close.
function sessionNote(market, region) {
  if (!market) return "";
  const open = region === "US" ? market.us_open : market.india_open;
  const t = region === "US" ? market.us_t : market.india_t;
  if (open) return "Today";
  if (!t) return "Last close";
  const day = new Date(t * 1000).toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", timeZone: REGION_TZ[region === "US" ? "US" : "India"],
  });
  return `Last close, ${day}`;
}

/* ---------- small pieces ---------- */
function Chip({ pct }) {
  const d = dir(pct);
  return (
    <span className={`fi-chip fi-${d}`}>
      <span aria-hidden="true">{arrow(d)}</span>
      {sign(pct)}
      {fmt(pct)}%
    </span>
  );
}

const Saved = ({ stale }) =>
  stale ? (
    <span className="fi-saved" title="Live price unavailable, showing last saved value">
      saved
    </span>
  ) : null;

function Spark({ values, d, id }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const pts = values.map((v, i) => [((i / (values.length - 1)) * 100).toFixed(1), (30 - ((v - min) / span) * 26).toFixed(1)]);
  const line = pts.map((p) => p.join(",")).join(" ");
  const gid = `sp-${String(id).replace(/[^a-z0-9]/gi, "")}`;
  return (
    <svg className={`fi-spark fi-spark-${d}`} viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.3" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,32 ${line} 100,32`} fill={`url(#${gid})`} />
      <polyline points={line} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function Panel({ title, note, children, className = "" }) {
  return (
    <section className={`fi-panel ${className}`}>
      <header className="fi-panel-head">
        <h2>{title}</h2>
        {note && <span>{note}</span>}
      </header>
      {children}
    </section>
  );
}

const Session = ({ label, open }) => (
  <span className={`fi-session ${open ? "fi-session-open" : ""}`}>
    <span className="fi-dot" aria-hidden="true" />
    {label} {open ? "open" : "closed"}
  </span>
);

function RangeBar({ label, lo, hi, price }) {
  if (lo == null || hi == null || hi <= lo) return null;
  const pos = clamp(((price - lo) / (hi - lo)) * 100, 0, 100);
  return (
    <div className="fi-range">
      <div className="fi-range-top">
        <span>{label}</span>
        <span>
          {fmt(lo)} {"\u2013"} {fmt(hi)}
        </span>
      </div>
      <div className="fi-range-track">
        <i style={{ left: `${pos}%` }} />
      </div>
    </div>
  );
}

/* ---------- index cards ---------- */
function IndexCard({ q, market }) {
  const d = dir(q.pct);
  const note = sessionNote(market, q.region);
  const when = !note ? "" : note === "Today" ? "today" : `${note.replace("Last close, ", "")} close`;
  return (
    <article className="fi-card">
      <div className="fi-card-top">
        <span className="fi-card-name">{q.name}</span>
        {TAGS[q.symbol] && <span className="fi-tag">{TAGS[q.symbol]}</span>}
      </div>
      <div className="fi-card-price">
        {fmt(q.price)} <Saved stale={q.stale} />
      </div>
      <div className="fi-card-bottom">
        <div>
          <Chip pct={q.pct} />
          <div className={`fi-card-abs fi-${d}`}>
            {sign(q.change)}
            {fmt(q.change)}
            {when && <span> {"\u00B7"} {when}</span>}
          </div>
        </div>
        <Spark values={q.spark} d={d} id={q.symbol} />
      </div>
      <RangeBar label="Day range" lo={q.dl} hi={q.dh} price={q.price} />
      <RangeBar label="52-week range" lo={q.l52} hi={q.h52} price={q.price} />
    </article>
  );
}

/* ---------- simple chart: last month of daily closes ---------- */
const W = 900;
const H = 280;
const PAD = { l: 10, r: 70, t: 14, b: 28 };
const dayLabel = (ts, tz) =>
  new Date(ts * 1000).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: tz });

function IndexChart({ indices, market }) {
  const options = CHART_SYMS.map((s) => indices.find((i) => i.symbol === s)).filter(Boolean);
  const [sym, setSym] = useState(options[0]?.symbol);
  const [hover, setHover] = useState(null);

  const q = options.find((o) => o.symbol === sym) || options[0];
  if (!q) return null;

  const tz = TZ[q.symbol];
  const series =
    q.hist?.length >= 2 ? q.hist : q.spark?.length >= 2 ? q.spark.map((v) => [null, v]) : null;
  const d = dir(q.pct);
  const note = sessionNote(market, q.region);
  const label = (i) => (series[i][0] ? dayLabel(series[i][0], tz) : `${series.length - 1 - i}d ago`);

  let body = (
    <p className="fi-empty">
      Chart data will appear after the next market refresh, within about 10 minutes. Tap Refresh to check again.
    </p>
  );

  if (series) {
    const vals = series.map((p) => p[1]);
    const lo0 = Math.min(...vals);
    const hi0 = Math.max(...vals);
    const padY = (hi0 - lo0 || 1) * 0.1;
    const lo = lo0 - padY;
    const hi = hi0 + padY;
    const pw = W - PAD.l - PAD.r;
    const ph = H - PAD.t - PAD.b;
    const X = (i) => PAD.l + (i / (series.length - 1)) * pw;
    const Y = (v) => PAD.t + (1 - (v - lo) / (hi - lo)) * ph;
    const line = vals.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
    const trend = dir(vals[vals.length - 1] - vals[0]);
    const gid = `ch-${String(q.symbol).replace(/[^a-z0-9]/gi, "")}`;
    const ticks = [hi0, (hi0 + lo0) / 2, lo0];
    const xs = [0, Math.floor((series.length - 1) / 2), series.length - 1];

    const onMove = (e) => {
      const r = e.currentTarget.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width) * W;
      setHover(clamp(Math.round(((x - PAD.l) / pw) * (series.length - 1)), 0, series.length - 1));
    };

    const left = hover != null ? (X(hover) / W) * 100 : 0;
    body = (
      <div className="fi-chartwrap">
        {hover != null && (
          <div className="fi-tip" style={{ left: `${left}%`, transform: `translateX(${left > 80 ? "-100%" : left < 20 ? "0" : "-50%"})` }}>
            <b>{fmt(vals[hover])}</b>
            <span>{label(hover)}</span>
          </div>
        )}
        <svg
          className={`fi-chart fi-chart-${trend}`}
          viewBox={`0 0 ${W} ${H}`}
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
          role="img"
          aria-label={`${q.name} closing prices over the last month`}
        >
          <defs>
            <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.18" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          {ticks.map((t, i) => (
            <g key={i}>
              <line x1={PAD.l} x2={W - PAD.r} y1={Y(t)} y2={Y(t)} className="fi-grid" />
              <text x={W - PAD.r + 8} y={Y(t) + 4} className="fi-axis">
                {Number(t).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
              </text>
            </g>
          ))}
          <polygon points={`${PAD.l},${H - PAD.b} ${line} ${PAD.l + pw},${H - PAD.b}`} fill={`url(#${gid})`} />
          <polyline points={line} className="fi-line" />
          {xs.map((i, k) => (
            <text key={k} x={X(i)} y={H - 8} className="fi-axis" textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"}>
              {label(i)}
            </text>
          ))}
          {hover != null && (
            <g>
              <line x1={X(hover)} x2={X(hover)} y1={PAD.t} y2={H - PAD.b} className="fi-cross" />
              <circle cx={X(hover)} cy={Y(vals[hover])} r="4.5" className="fi-dotc" />
            </g>
          )}
        </svg>
      </div>
    );
  }

  return (
    <Panel title="Index chart" note="Last month, daily closes" className="fi-chartpanel">
      <div className="fi-chart-ctrl">
        <div className="fi-seg-group" role="group" aria-label="Choose index">
          {options.map((o) => (
            <button key={o.symbol} type="button" className="fi-pill" aria-pressed={o.symbol === q.symbol} onClick={() => { setSym(o.symbol); setHover(null); }}>
              {o.name}
            </button>
          ))}
        </div>
      </div>
      <div className="fi-chart-head">
        <span className="fi-chart-price">{fmt(q.price)}</span>
        <span className={`fi-chart-delta fi-${d}`}>
          <span aria-hidden="true">{arrow(d)}</span> {sign(q.change)}
          {fmt(q.change)} ({sign(q.pct)}
          {fmt(q.pct)}%)
        </span>
        {note && <span className="fi-chart-when">{note}</span>}
        <Saved stale={q.stale} />
      </div>
      {body}
    </Panel>
  );
}

/* ---------- breadth, sectors, movers, others ---------- */
function Breadth({ b }) {
  const p = (n) => (b.total ? (n / b.total) * 100 : 0);
  const adv = p(b.advancing);
  const dec = p(b.declining);
  const label = adv >= 60 ? "Bullish" : dec >= 60 ? "Bearish" : "Mixed";
  const tone = label === "Bullish" ? "up" : label === "Bearish" ? "down" : "flat";
  return (
    <Panel title="Market breadth" note={`${b.total} large companies`}>
      <div className="fi-breadth">
        <span className={`fi-mood fi-mood-${tone}`}>{label}</span>
        <div className="fi-meter" role="img" aria-label={`${b.advancing} advancing, ${b.declining} declining, ${b.unchanged} unchanged`}>
          <span className="fi-seg fi-seg-up" style={{ width: `${adv}%` }} />
          <span className="fi-seg fi-seg-flat" style={{ width: `${p(b.unchanged)}%` }} />
          <span className="fi-seg fi-seg-down" style={{ width: `${dec}%` }} />
        </div>
        <ul className="fi-legend">
          <li><i className="fi-seg-up" />Advancing <b>{b.advancing}</b></li>
          <li><i className="fi-seg-flat" />Unchanged <b>{b.unchanged}</b></li>
          <li><i className="fi-seg-down" />Declining <b>{b.declining}</b></li>
        </ul>
      </div>
    </Panel>
  );
}

function Sectors({ rows, note }) {
  return (
    <Panel title="Sector performance" note={note}>
      <ul className="fi-sectors">
        {rows.map((r) => {
          const d = dir(r.pct);
          const Icon = SECTOR_ICON[r.name] || Building2;
          return (
            <li key={r.symbol} className={`fi-sector fi-sec-${d}`}>
              <span className="fi-sector-icon"><Icon size={16} /></span>
              <span className="fi-sector-name">{r.name}</span>
              <span className={`fi-sector-val fi-${d}`}>
                {sign(r.pct)}
                {fmt(r.pct)}% <span aria-hidden="true">{arrow(d)}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

function MoversTable({ title, rows, note }) {
  return (
    <Panel title={title} note={note}>
      {rows?.length ? (
        <table className="fi-table">
          <thead>
            <tr>
              <th scope="col">Stock</th>
              <th scope="col" className="num">Price ({"\u20B9"})</th>
              <th scope="col" className="num">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol}>
                <th scope="row">
                  <span className="fi-av" style={{ background: `hsl(${hue(r.name)} 42% 40%)` }} aria-hidden="true">{r.name.slice(0, 2)}</span>
                  {r.name}
                </th>
                <td className="num">{fmt(r.price)}</td>
                <td className="num"><Chip pct={r.pct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="fi-empty">Nothing to show right now.</p>
      )}
    </Panel>
  );
}

function OtherMarkets({ rows }) {
  return (
    <Panel title="Other markets" note="Currency, commodities, crypto">
      <ul className="fi-rows">
        {rows.map((r) => (
          <li key={r.symbol}>
            <span className="fi-row-name">
              {r.name}
              {r.unit && <small>{r.unit}</small>} <Saved stale={r.stale} />
            </span>
            <span className="fi-row-price">{fmt(r.price)}</span>
            <Chip pct={r.pct} />
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Skeleton() {
  return (
    <div aria-hidden="true">
      <div className="fi-hero">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="fi-card fi-skel">
            <span className="fi-sk" style={{ width: "45%" }} />
            <span className="fi-sk fi-sk-big" />
            <span className="fi-sk" style={{ width: "60%" }} />
          </div>
        ))}
      </div>
      <div className="fi-panel fi-skel" style={{ height: 260 }} />
    </div>
  );
}

/* ---------- page ---------- */
export default function MarketInsights() {
  const [data, setData] = useState(readCache);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchInsights();
      if (res?.ready) {
        setData(res);
        writeCache(res);
      } else if (!data) {
        setData({ ready: false });
      }
    } catch (e) {
      setError(e.message || "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
    const t = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (data && data.ready === false) {
      const t = setTimeout(load, 8000);
      return () => clearTimeout(t);
    }
  }, [data, load]);

  const hasData = data?.ready;
  const hero = HERO.map((s) => data?.indices?.find((i) => i.symbol === s)).filter(Boolean);
  const others = [...(data?.indices?.filter((i) => !HERO.includes(i.symbol)) ?? []), ...(data?.other ?? [])];
  const saved = hasData && (data.status === "saved" || !!error);
  const ageMin = hasData ? minsSince(data.updated_at) : null;
  const today = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

  return (
    <section className="fg-ins">
      <header className="fi-head">
        <div>
          <h1>Market Insights</h1>
          <p className="fi-tagline">Delayed market data and trends, all in one place.</p>
        </div>
        <div className="fi-head-right">
          {hasData && data.market && (
            <>
              <Session label="India" open={data.market.india_open} />
              <Session label="US" open={data.market.us_open} />
            </>
          )}
          <span className="fi-date">{today}</span>
          <button type="button" className="fi-refresh" onClick={load} disabled={loading}>
            {loading ? "Updating" : "Refresh"}
          </button>
        </div>
      </header>

      <p className="fi-status" role="status">
        {hasData ? (saved ? `Showing saved prices from ${ageMin} min ago` : `Prices delayed, updated ${ageMin} min ago`) : "Loading market data"}
      </p>

      {saved && (
        <p className="fi-banner" role="alert">
          Live prices are temporarily unavailable{error ? " (cannot reach the server)" : ""}. The figures below are the last saved ones and will update automatically when the feed is back.
        </p>
      )}
      {!hasData && !error && (
        <>
          <p className="fi-banner" role="status">Building the first market snapshot. This takes about 30 seconds the first time.</p>
          <Skeleton />
        </>
      )}
      {!hasData && error && (
        <p className="fi-banner" role="alert">{error} Check that the backend is running, then tap Refresh.</p>
      )}

      {hasData && (
        <>
          {hero.length > 0 && (
            <div className="fi-hero">
              {hero.map((q) => (
                <IndexCard key={q.symbol} q={q} market={data.market} />
              ))}
            </div>
          )}

          <div className="fi-main">
            <IndexChart indices={data.indices ?? []} market={data.market} />
            <div className="fi-stack">
              {data.breadth?.total > 0 && <Breadth b={data.breadth} />}
              {data.sectors?.length > 0 && <Sectors rows={data.sectors} note={sessionNote(data.market, "India")} />}
            </div>
          </div>

          <div className="fi-trio">
            <MoversTable title="Top gainers" rows={data.gainers} note={sessionNote(data.market, "India")} />
            <MoversTable title="Top losers" rows={data.losers} note={sessionNote(data.market, "India")} />
            {others.length > 0 && <OtherMarkets rows={others} />}
          </div>
        </>
      )}

      <p className="fi-foot">
        Source: Yahoo Finance (unofficial, delayed).
      </p>
    </section>
  );
}