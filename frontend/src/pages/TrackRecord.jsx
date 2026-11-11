import { useEffect, useState } from "react";
import { ClipboardCheck, RefreshCw, ChevronDown, ShieldCheck, Swords } from "lucide-react";
import {
  listReceipts,
  getScorecard,
  getReceiptHistory,
  getReceiptInsight,
} from "../api";

const STATUS = {
  on_track: { label: "On track", cls: "tr-s-open", card: "tr-card-open" },
  target_hit: { label: "Target hit", cls: "tr-s-win", card: "tr-card-win" },
  invalidated: { label: "Invalidated", cls: "tr-s-loss", card: "tr-card-loss" },
};

const HINTS = {
  mine: "Picks you saved with “Track this pick”, followed against the market.",
  platform: "The combined result of every pick saved by all FinGuide users. Numbers only, no one's details are shown.",
};

const signed = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`);
const fmtPct = (v) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`);
const tone = (v) => (v == null || v === 0 ? "" : v > 0 ? "tr-pos" : "tr-neg");
const pctOf = (n, total) => (total ? (n / total) * 100 : 0);
const money = (symbol, v) =>
  v == null ? "—" : `${/\.(NS|BO)$/.test(symbol) ? "₹" : "$"}${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
const day = (iso) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
const benchName = (b) => (b === "^NSEI" ? "Nifty 50" : "S&P 500");
const titleCase = (v) => (v ? String(v).replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "—");
const shortSym = (s) => s.replace(/\.(NS|BO)$/, "");

const RANGES = ["1W", "1M", "3M", "6M", "1Y", "ALL"];
const CMP_COLORS = ["#2BB673", "#E2495A", "#8B5CF6", "#0EA5E9", "#D946EF", "#64748B"];

// last value, gap to the market, and how often the pick was ahead
function statsOf(pts) {
  const last = pts[pts.length - 1];
  const gap = last && last.bench != null ? last.pick - last.bench : null;
  const withBench = pts.slice(1).filter((p) => p.bench != null);
  const leadShare = withBench.length
    ? Math.round((withBench.filter((p) => p.pick > p.bench).length / withBench.length) * 100)
    : null;
  return { last, gap, leadShare };
}

const when = (t, interval) => {
  const d = new Date(t * 1000);
  return interval === "1d"
    ? d.toLocaleDateString(undefined, { day: "numeric", month: "short" })
    : d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
};

function niceTicks(lo, hi, count = 5) {
  const raw = (hi - lo) / (count - 1) || 1;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/* =====================================================
   PICK vs MARKET SHOWDOWN: interactive line chart
===================================================== */
function ShowdownChart({ data }) {
  const [hover, setHover] = useState(null);
  const pts = data?.points || [];

  if (pts.length < 2) {
    return (
      <div className="tr-chart-empty">
        Not enough price history yet. The chart fills in as the market moves, so try Refresh after trading has been open for a while.
      </div>
    );
  }

  const W = 960, H = 360, L = 58, R = 28, T = 22, B = 40;
  const n = pts.length;
  const vals = pts
    .flatMap((p) => [p.pick, p.bench, ...Object.values(p.cmp || {})])
    .filter((v) => v != null)
    .concat(0);
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  const pad = (hi - lo) * 0.18 || 1;
  lo -= pad;
  hi += pad;

  const X = (i) => L + (i / (n - 1)) * (W - L - R);
  const Y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);

  const line = (key) => {
    let d = "";
    pts.forEach((p, i) => {
      if (p[key] == null) return;
      d += `${d ? "L" : "M"}${X(i).toFixed(1)},${Y(p[key]).toFixed(1)}`;
    });
    return d;
  };

  const options = data.options || [];
  const chosen = data.compare || [];
  const colorOf = (sym) => CMP_COLORS[Math.max(0, options.findIndex((o) => o.symbol === sym)) % CMP_COLORS.length];
  const cmpLine = (sym) => {
    let d = "";
    pts.forEach((p, i) => {
      const v = p.cmp?.[sym];
      if (v == null) return;
      d += `${d ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`;
    });
    return d;
  };

  const area = `${line("pick")}L${X(n - 1).toFixed(1)},${Y(0).toFixed(1)}L${X(0).toFixed(1)},${Y(0).toFixed(1)}Z`;

  const { last, gap, leadShare } = statsOf(pts);
  const winning = gap != null && gap > 0;

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - L) / (W - L - R)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, i)));
  };

  const a = hover == null ? null : pts[hover];
  const labelIdx = [0, Math.floor((n - 1) / 3), Math.floor(((n - 1) * 2) / 3), n - 1];

  return (
    <>
      <div className="tr-scoreboard">
        <div className="tr-sb tr-sb-pick">
          <small>{data.symbol} {data.since_saved ? "since saved" : "this period"}</small>
          <strong className={tone(last.pick)}>{fmtPct(last.pick)}</strong>
        </div>
        <div className="tr-sb tr-sb-bench">
          <small>{data.bench_name} {data.since_saved ? "since saved" : "this period"}</small>
          <strong className={tone(last.bench)}>{fmtPct(last.bench)}</strong>
        </div>
        <div className={`tr-sb tr-sb-verdict ${gap == null ? "" : winning ? "win" : "lose"}`}>
          <small>Who's winning</small>
          <strong>
            {gap == null
              ? "No index data"
              : winning
              ? `${data.symbol} by ${gap.toFixed(2)}%`
              : gap === 0
              ? "Level"
              : `${data.bench_name} by ${Math.abs(gap).toFixed(2)}%`}
          </strong>
          {leadShare != null && <span>{data.symbol} led {leadShare}% of the time</span>}
        </div>
      </div>

      <div className="tr-chart-wrap">
        <svg
          className="tr-chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`${data.symbol} against ${data.bench_name}`}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            <linearGradient id="trAreaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5560E8" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#5560E8" stopOpacity="0" />
            </linearGradient>
          </defs>

          {niceTicks(lo, hi).map((v) => (
            <g key={v}>
              <line className={v === 0 ? "tr-zero" : "tr-gridline"} x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} />
              <text className="tr-ax" x={L - 10} y={Y(v) + 4} textAnchor="end">
                {v > 0 ? "+" : ""}{+v.toFixed(2)}%
              </text>
            </g>
          ))}

          {labelIdx.map((i, k) => (
            <text
              key={`${i}-${k}`}
              className="tr-ax"
              x={X(i)}
              y={H - 12}
              textAnchor={k === 0 ? "start" : k === labelIdx.length - 1 ? "end" : "middle"}
            >
              {when(pts[i].t, data.interval)}
            </text>
          ))}

          <path d={area} fill="url(#trAreaFill)" />
          <path className="tr-line tr-line-bench" d={line("bench")} />
          {chosen.map((sym) => (
            <path key={sym} className="tr-line tr-line-cmp" stroke={colorOf(sym)} d={cmpLine(sym)} />
          ))}
          <path className="tr-line tr-line-pick" d={line("pick")} />

          {hover != null && (
            <g>
              <line className="tr-cross" x1={X(hover)} x2={X(hover)} y1={T} y2={H - B} />
              <circle className="tr-dot tr-dot-pick" cx={X(hover)} cy={Y(a.pick)} r="6" />
              {a.bench != null && <circle className="tr-dot tr-dot-bench" cx={X(hover)} cy={Y(a.bench)} r="6" />}
              {chosen.map((sym) =>
                a.cmp?.[sym] != null ? (
                  <circle key={sym} className="tr-dot" fill={colorOf(sym)} cx={X(hover)} cy={Y(a.cmp[sym])} r="5" />
                ) : null
              )}
            </g>
          )}
        </svg>

        {hover != null && (
          <div className={`tr-tip ${X(hover) / W > 0.6 ? "flip" : ""}`} style={{ left: `${(X(hover) / W) * 100}%` }}>
            <b>{when(a.t, data.interval)}</b>
            <span><i className="tr-key-pick" />{data.symbol} <em className={tone(a.pick)}>{fmtPct(a.pick)}</em></span>
            <span><i className="tr-key-bench" />{data.bench_name} <em className={tone(a.bench)}>{fmtPct(a.bench)}</em></span>
            {chosen.map((sym) => (
              <span key={sym}>
                <i className="tr-key-pick" style={{ background: colorOf(sym) }} />
                {shortSym(sym)} <em className={tone(a.cmp?.[sym])}>{fmtPct(a.cmp?.[sym])}</em>
              </span>
            ))}
            {a.bench != null && (
              <span className="tr-tip-gap">
                {a.pick > a.bench ? `${data.symbol} ahead` : a.pick < a.bench ? `${data.bench_name} ahead` : "Level"}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="tr-chart-legend">
        <span><i className="tr-key-pick" /> {data.symbol} (your pick)</span>
        <span><i className="tr-key-bench" /> {data.bench_name} (the market)</span>
        {chosen.map((sym) => (
          <span key={sym}>
            <i className="tr-key-pick" style={{ background: colorOf(sym) }} /> {shortSym(sym)} {fmtPct(last.cmp?.[sym])}
          </span>
        ))}
        <span>All lines start at 0% {data.since_saved ? "on the day you saved the pick" : "at the start of this period"}.</span>
      </div>
    </>
  );
}

/* =====================================================
   PAGE
===================================================== */
export default function TrackRecord() {
  const [receipts, setReceipts] = useState([]);
  const [score, setScore] = useState(null);
  const [view, setView] = useState("mine");
  const [openId, setOpenId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);

  const [selId, setSelId] = useState(null);
  const [hist, setHist] = useState(null);
  const [histLoading, setHistLoading] = useState(false);
  const [histError, setHistError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [tab, setTab] = useState("market"); // "market" = vs the index, "picks" = vs my other picks
  const [range, setRange] = useState("ALL");
  const [compare, setCompare] = useState([]);
  const [insight, setInsight] = useState({ status: "idle", text: "", source: "" });

  // fresh = true -> the Refresh button: ask for live prices instead of cached ones
  async function load(fresh = false) {
    setLoading(true);
    setError("");
    try {
      const [list, card] = await Promise.all([listReceipts(fresh), getScorecard(fresh)]);
      setReceipts(list || []);
      setScore(card);
      setUpdatedAt(new Date());
      setSelId((prev) => ((list || []).some((r) => r.id === prev) ? prev : list?.[0]?.id ?? null));
      if (fresh) setRefreshKey((k) => k + 1);
    } catch (e) {
      setError(e.message || "Could not load your track record.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(false);
  }, []);

  // load the Showdown chart for the selected pick
  useEffect(() => {
    if (!selId) {
      setHist(null);
      return undefined;
    }
    let live = true;
    setHistLoading(true);
    setHistError("");
    getReceiptHistory(selId, range, refreshKey > 0, compare)
      .then((d) => live && setHist(d))
      .catch((e) => live && (setHist(null), setHistError(e.message || "Could not load the chart.")))
      .finally(() => live && setHistLoading(false));
    return () => {
      live = false;
    };
  }, [selId, refreshKey, range, compare]);

  // a new pick or period means any earlier AI explanation no longer applies
  useEffect(() => {
    setInsight({ status: "idle", text: "", source: "" });
  }, [selId, range]);

  async function explain() {
    setInsight({ status: "loading", text: "", source: "" });
    try {
      const r = await getReceiptInsight(selId, range);
      setInsight({ status: "done", text: r.text, source: r.source });
    } catch (e) {
      setInsight({ status: "error", text: e.message || "Could not get an explanation.", source: "" });
    }
  }

  const pickSelect = (id) => {
    setSelId(id);
    setCompare([]); // the comparison stocks depend on the selected pick
  };
  const toggleCompare = (sym) =>
    setCompare((c) => (c.includes(sym) ? c.filter((x) => x !== sym) : c.length >= 6 ? c : [...c, sym]));

  // comparison insights, all computed from the real receipts and chart data
  const withAlpha = receipts.filter((r) => r.alpha_pct != null);
  const winners = withAlpha.filter((r) => r.alpha_pct > 0).length;
  const byReturn = [...receipts].sort((a, b) => (b.return_pct ?? -Infinity) - (a.return_pct ?? -Infinity));
  const best = byReturn[0];
  const trailing = [...withAlpha].sort((a, b) => a.alpha_pct - b.alpha_pct)[0];
  const stats = hist ? statsOf(hist.points) : null;
  const maxAbs = Math.max(1, ...receipts.map((r) => Math.abs(r.return_pct ?? 0)));

  const s = score?.[view];
  const allFlat = receipts.length > 0 && receipts.every((r) => r.return_pct === 0);
  const tiles = s
    ? [
        ["Picks tracked", s.total, "saved and being followed", ""],
        ["In profit", s.in_profit_pct == null ? "—" : `${s.in_profit_pct}%`, "of picks above their entry price", ""],
        ["Beat the market", s.beat_market_pct == null ? "—" : `${s.beat_market_pct}%`, "of picks that outperformed the index", ""],
        ["Avg vs market", signed(s.avg_alpha_pct), "average gap against the index", tone(s.avg_alpha_pct)],
      ]
    : [];

  return (
    <main className="tr">
      <header className="tr-head">
        <div className="tr-title">
          <h1>Track Record</h1>
        </div>

        <div className="tr-actions">
          <button className="tr-btn" onClick={() => load(true)} disabled={loading} aria-label="Refresh with live prices">
            <RefreshCw size={15} className={loading ? "tr-spin" : ""} />
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      <div className="tr-tabs" role="tablist">
        <button role="tab" aria-selected={view === "mine"} className={view === "mine" ? "on" : ""} onClick={() => setView("mine")}>
          Your picks
        </button>
        <button role="tab" aria-selected={view === "platform"} className={view === "platform" ? "on" : ""} onClick={() => setView("platform")}>
          All FinGuide picks
        </button>
      </div>
      <p className="tr-hint">{HINTS[view]}</p>
      {updatedAt && (
        <p className="tr-updated">
          Prices updated {updatedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
        </p>
      )}

      {error && <div className="tr-error">{error}</div>}

      <div className="tr-tiles">
        {tiles.map(([label, value, sub, toneClass]) => (
          <div key={label} className="tr-tile">
            <small>{label}</small>
            <strong className={toneClass}>{value}</strong>
            <span className="tr-sub">{sub}</span>
          </div>
        ))}
      </div>

      {s && s.total > 0 && (
        <div className="tr-breakdown">
          <div className="tr-bar" aria-hidden="true">
            <span className="tr-seg-open" style={{ width: `${pctOf(s.open, s.total)}%` }} />
            <span className="tr-seg-win" style={{ width: `${pctOf(s.target_hit, s.total)}%` }} />
            <span className="tr-seg-loss" style={{ width: `${pctOf(s.invalidated, s.total)}%` }} />
          </div>
          <div className="tr-legend">
            <span><i className="tr-seg-open" /> On track {s.open}</span>
            <span><i className="tr-seg-win" /> Target hit {s.target_hit}</span>
            <span><i className="tr-seg-loss" /> Invalidated {s.invalidated}</span>
          </div>
        </div>
      )}

      {s?.early_data && s.total > 0 && (
        
        <p className="tr-note">Early data: with fewer than 5 picks, these percentages can swing a lot.</p>
      )}

      {view === "mine" && allFlat && (
        <div className="tr-flat">
          Returns start at 0% and move with the market. A stock can't move while its market is closed, so it
          may stay at 0% until it reopens. Press Refresh to pull the latest live prices.
        </div>
      )}

      {view === "mine" && receipts.length > 0 && (
        <section className="tr-show">
          <div className="tr-show-top">
            <div>
              <h2><Swords size={22} /> Pick vs Market Showdown</h2>
              
            </div>

            {tab === "market" && (
              <div className="tr-pickchips" role="tablist" aria-label="Choose a pick">
                {receipts.map((r) => (
                  <button
                    key={r.id}
                    role="tab"
                    aria-selected={selId === r.id}
                    className={`tr-pickchip ${selId === r.id ? "on" : ""}`}
                    onClick={() => pickSelect(r.id)}
                  >
                    {r.symbol}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="tr-tabs tr-show-tabs" role="tablist">
            <button role="tab" aria-selected={tab === "market"} className={tab === "market" ? "on" : ""} onClick={() => setTab("market")}>
              vs Market
            </button>
            <button role="tab" aria-selected={tab === "picks"} className={tab === "picks" ? "on" : ""} onClick={() => setTab("picks")}>
              vs My Picks
            </button>
          </div>

          {tab === "market" && (
            <>
              

              {hist?.options?.length > 0 && (
                <div className="tr-compare" role="group" aria-label="Compare with other stocks">
                  <span className="tr-compare-label">Compare {hist.symbol} with</span>
                  {hist.options.map((o, i) => (
                    <button
                      key={o.symbol}
                      className={`tr-pickchip tr-cmpchip ${compare.includes(o.symbol) ? "on" : ""}`}
                      onClick={() => toggleCompare(o.symbol)}
                      aria-pressed={compare.includes(o.symbol)}
                    >
                      <i style={{ background: CMP_COLORS[i % CMP_COLORS.length] }} />
                      {o.name}
                    </button>
                  ))}
                  {compare.length > 0 && (
                    <button className="tr-cmp-clear" onClick={() => setCompare([])}>Clear</button>
                  )}
                </div>
              )}

              {histLoading && !hist && <div className="tr-chart-empty">Loading price history…</div>}
              {histError && <div className="tr-error">{histError}</div>}
              {hist && <ShowdownChart key={`${hist.id}-${hist.range}-${refreshKey}`} data={hist} />}

              {stats && (
                <div className="tr-insights">
                  <div className="tr-sb">
                    <small>Market winners</small>
                    <strong>{winners} of {withAlpha.length}</strong>
                    <span>picks beating their index</span>
                  </div>
                  <div className="tr-sb">
                    <small>Consistency</small>
                    <strong>{stats.leadShare == null ? "—" : `${stats.leadShare}%`}</strong>
                    <span>of the time {hist.symbol} was ahead</span>
                  </div>
                  <div className="tr-sb">
                    <small>Best pick</small>
                    <strong className={tone(best?.return_pct)}>{best ? `${best.symbol} ${signed(best.return_pct)}` : "—"}</strong>
                    <span>highest return since saved</span>
                  </div>
                  <div className="tr-sb">
                    <small>Biggest underperformer</small>
                    <strong className={trailing && trailing.alpha_pct < 0 ? "tr-neg" : ""}>
                      {trailing && trailing.alpha_pct < 0 ? `${trailing.symbol} ${signed(trailing.alpha_pct)}` : "None"}
                    </strong>
                    <span>trails its index the most</span>
                  </div>
                </div>
              )}

              {hist && stats && (
                <div className="tr-ai">
                  <div className="tr-ai-head">
                    <b>FinGuide insight</b>
                    <button className="tr-btn" onClick={explain} disabled={insight.status === "loading"}>
                      {insight.status === "loading" ? "Thinking..." : "Explain with AI"}
                    </button>
                  </div>

                  <p>
                    {insight.text ||
                      (stats.gap == null
                        ? `${hist.symbol} is ${fmtPct(stats.last.pick)} over this period. No ${hist.bench_name} data is available to compare.`
                        : `${hist.symbol} ${stats.gap > 0 ? "outperformed" : stats.gap < 0 ? "underperformed" : "matched"} ${hist.bench_name}${stats.gap === 0 ? "" : ` by ${Math.abs(stats.gap).toFixed(2)} percentage points`} over this period (${fmtPct(stats.last.pick)} vs ${fmtPct(stats.last.bench)}).`)}
                  </p>

                  <small>
                    {insight.source === "gemini"
                      ? "AI explanation. Every number comes from the data above, not from the AI."
                      : insight.source === "template"
                      ? "AI isn't available right now, so this is a summary of the numbers."
                      : "Relative performance shows how a pick did against the index. It is not a measure of quality or future returns."}
                  </small>
                </div>
              )}
            </>
          )}

          {tab === "picks" && (
            <>
              <div className="tr-rank">
                {byReturn.map((r, i) => (
                  <button
                    key={r.id}
                    className="tr-rank-row"
                    onClick={() => {
                      pickSelect(r.id);
                      setTab("market");
                    }}
                  >
                    <span className="tr-rank-n">#{i + 1}</span>
                    <span className="tr-rank-sym">
                      <b>{r.symbol}</b>
                      <small>{r.name || "—"}</small>
                    </span>
                    <span className="tr-rank-bar" aria-hidden="true">
                      <i className={(r.return_pct ?? 0) >= 0 ? "pos" : "neg"} style={{ width: `${(Math.abs(r.return_pct ?? 0) / maxAbs) * 100}%` }} />
                    </span>
                    <strong className={tone(r.return_pct)}>{signed(r.return_pct)}</strong>
                    <small className={tone(r.alpha_pct)}>{signed(r.alpha_pct)} vs {benchName(r.bench_symbol)}</small>
                  </button>
                ))}
              </div>
              <p className="tr-note">
                Each return is measured from the day that pick was saved, so older picks have had longer to move. Click a pick to see its chart.
              </p>
            </>
          )}
        </section>
      )}

      {view === "platform" && (
        <div className="tr-agg">
          <ShieldCheck size={24} />
          <div>
            <h3>How “All FinGuide picks” works</h3>
            <p>
              This adds up every pick saved by every FinGuide user, wins and losses together, so you can judge
              the advice as a whole and not just your own picks. Only totals are shown. Other users' picks,
              profiles and names stay private.
            </p>
          </div>
        </div>
      )}

      {view === "mine" && !loading && receipts.length === 0 && (
        <div className="tr-empty">
          <ClipboardCheck size={34} />
          <h2>No receipts yet</h2>
          <p>Open the Assistant and press “Track this pick” on a recommendation to save your first one.</p>
        </div>
      )}

      {view === "mine" && (
        <div className="tr-list">
          {receipts.map((r) => {
            const status = STATUS[r.status] || STATUS.on_track;
            const open = openId === r.id;
            const snap = r.profile_snapshot || {};

            return (
              <article key={r.id} className={`tr-card ${status.card}`}>
                <button className="tr-row" onClick={() => setOpenId(open ? null : r.id)} aria-expanded={open}>
                  <div className="tr-id">
                    <strong>{r.symbol}</strong>
                    <small>{r.name || "—"} · saved {day(r.created_at)}</small>
                  </div>
                  <div className="tr-num">
                    <small>Return</small>
                    <strong className={tone(r.return_pct)}>{signed(r.return_pct)}</strong>
                  </div>
                  <div className="tr-num">
                    <small>vs {benchName(r.bench_symbol)}</small>
                    <strong className={tone(r.alpha_pct)}>{signed(r.alpha_pct)}</strong>
                  </div>
                  <span className={`tr-status ${status.cls}`}>{status.label}</span>
                  <ChevronDown size={20} className={`tr-chev ${open ? "open" : ""}`} />
                </button>

                {open && (
                  <div className="tr-detail">
                    <div className="tr-grid">
                      <div><small>Entry price</small><strong>{money(r.symbol, r.entry_price)}</strong></div>
                      <div><small>{r.status === "on_track" ? "Now" : "Closed at"}</small><strong>{money(r.symbol, r.current_price)}</strong></div>
                      <div><small>Reason expires if</small><strong>falls {r.stop_pct}%</strong></div>
                      <div><small>Target</small><strong>+{r.target_pct}%</strong></div>
                    </div>

                    {r.reasons?.length > 0 && (
                      <>
                        <h4>Why it was recommended</h4>
                        <ul>{r.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
                      </>
                    )}

                    <h4>Your profile at that moment</h4>
                    <div className="tr-chips">
                      <span>Risk: {titleCase(snap.risk_preference)}</span>
                      <span>Horizon: {snap.investment_horizon ?? "—"} yr</span>
                      <span>Goal: {titleCase(snap.financial_goal)}</span>
                      <span>Expected return: {snap.target_return_percent ?? "—"}%</span>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      <p className="tr-note">
        Paper tracking only: no money is invested. Past results don't predict future returns.
        This is general information, not financial advice.
      </p>
    </main>
  );
}