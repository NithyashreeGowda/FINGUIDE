import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import "../styles.css";

/* Finn lives inside the sidebar only. He can be dragged anywhere in it, and he
   disappears when the sidebar is closed. He speaks one line at a time, picked at
   random from a few per page. Polite limits: 6 questions per session, 90 s apart. */
const MAX_QUESTIONS = 6;
const GAP_MS = 90_000;
const SNOOZE_MS = 5 * 60_000;
const SHOW_MS = 30_000;
const GOALS = ["Home", "Travel", "Retirement", "Emergency fund"];

const W = 120; // px, must match the svg width
const H = 156; // px, must match the svg height
const POS_KEY = "fg_finn_pos2";

const ss = {
  get: (k) => {
    try { return sessionStorage.getItem(k); } catch { return null; }
  },
  set: (k, v) => {
    try { sessionStorage.setItem(k, v); } catch { /* ignore */ }
  },
};
const readPos = () => {
  try {
    const p = JSON.parse(localStorage.getItem(POS_KEY));
    return p && Number.isFinite(p.rx) && Number.isFinite(p.ry) ? p : null;
  } catch {
    return null;
  }
};
const savePos = (p) => {
  try { localStorage.setItem(POS_KEY, JSON.stringify(p)); } catch { /* ignore */ }
};
const clamp = (n, a, b) => Math.min(b, Math.max(a, n));

// The area Finn may move in: the sidebar. Null when the sidebar is closed.
function getBounds() {
  const r = document.querySelector(".sidebar")?.getBoundingClientRect();
  if (!r || r.width < 80 || r.height < H) return null;
  return { l: r.left + 4, t: r.top + 4, r: r.right - 4, b: r.bottom - 4 };
}
const clampTo = (b, x, y) => ({
  x: clamp(x, b.l, Math.max(b.l, b.r - W)),
  y: clamp(y, b.t, Math.max(b.t, b.b - H)),
});

/* ---------- what Finn says: several lines per page, one at a time ---------- */
const GOAL_REPLY = (g) => ({
  text: `${g} is a great goal! Tell the Assistant about it and it can help you plan.`,
  actions: [{ label: "Go to Assistant", to: "assistant" }],
});
const nav = (id, text, label, to) => ({ id, text, actions: [{ label, to }] });
const tip = (id, text, tipText, action) => ({
  id,
  text,
  chips: ["Show me", "Not now"],
  replies: { "Show me": { text: tipText, actions: action ? [action] : [] } },
});
const goalQ = (id, text) => ({ id, text, chips: GOALS, goal: true });

function questionsFor(tab, name) {
  const hi = name ? `${name}, ` : "";
  switch (tab) {
    case "market-insights":
      return [
        nav("i1", "Markets look busy. Want the headlines behind the moves?", "Open Market News", "market-news"),
        tip("i2", "Want a quick way to read this page?", "Start with the four index cards, then check market breadth. If most stocks are green, the move is broad and not just a few big names."),
        tip("i3", "Curious what the day range bar means?", "It shows where the price sits between today's low and high. A dot near the right edge means it is trading close to the day's high."),
        goalQ("i4", `${hi}are you saving for something big right now?`),
        tip("i5", "Why does the 52-week bar matter?", "It shows how far an index is from its yearly high and low. A quick way to see whether markets look stretched or beaten down."),
        nav("i6", "Want any number here explained in plain words?", "Ask the Assistant", "assistant"),
      ];
    case "market-news":
      return [
        nav("n1", "Spotted something interesting? See how prices reacted.", "Open Market Insights", "market-insights"),
        tip("n2", "Want a tip for reading headlines faster?", "Scan the colored category tags first, then open only the stories about sectors you follow."),
        goalQ("n3", `${hi}what are you saving for these days?`),
        tip("n4", "Confused by the sentiment tags?", "Positive or negative shows the tone of an article, not a prediction. Treat it as one signal, never as advice."),
        nav("n5", "Need a headline explained simply? The Assistant can do that.", "Ask the Assistant", "assistant"),
        tip("n6", "Wondering how fresh these stories are?", "This page keeps the last 48 hours of news and refreshes itself every few minutes."),
      ];
    case "assistant":
      return [
        goalQ("a1", `${hi}what are you saving for right now?`),
        tip("a2", "Not sure what to ask? Want a few ideas?", "Try: \"How much should I keep as an emergency fund?\" or \"How do I start a monthly SIP?\""),
        tip("a3", "Want to know how I can help you?", "I can walk you through budgeting, goals and basic investing ideas in plain language. For personal advice, a registered adviser is the right call."),
        nav("a4", "Curious about the market today? A quick look might help.", "Open Market Insights", "market-insights"),
        goalQ("a5", "Is there a goal that feels hard to plan? Pick one."),
        nav("a6", "Want to see the headlines before you ask?", "Open Market News", "market-news"),
      ];
    case "history":
      return [
        nav("h1", "Want to pick up an old chat or start a new one?", "Start a new chat", "assistant"),
        tip("h2", "Did you know you can rename your chats?", "Give a chat a clear name and it becomes much easier to find later."),
        goalQ("h3", `${hi}thinking about a new goal today?`),
        tip("h4", "Want a tip to keep your chats tidy?", "Delete chats you no longer need and rename the ones you come back to."),
        nav("h5", "Done here? Today's market news is one click away.", "Open Market News", "market-news"),
      ];
    case "settings":
      return [
        tip("s1", "Looking for dark mode?", "You can switch it here in Settings, and it is saved for your account."),
        tip("s2", "Want a quick security tip?", "Use a password you do not use anywhere else, and change it here whenever you feel unsure."),
        goalQ("s3", "All set? Which goal are we working on next?"),
        nav("s4", "Ready to get back to your questions?", "Go to Assistant", "assistant"),
      ];
    default:
      return [];
  }
}

/* Front-facing fox in a navy blazer: big ears, cream cheeks, lanyard badge,
   briefcase in one hand and an open hand raised to greet you. */
function FinnArt() {
  return (
    <svg viewBox="0 0 200 260" width="120" height="156" aria-hidden="true" focusable="false">
      <ellipse cx="100" cy="252" rx="48" ry="5" fill="currentColor" opacity="0.14" />

      <g className="ff-tail">
        <path d="M88 222 C60 238 24 224 18 190 C15 172 26 158 40 163 C43 178 56 190 72 196 C80 199 86 199 90 198 Z" fill="#f58a34" />
        <path d="M18 190 C15 172 26 158 40 163 C37 171 35 178 29 184 C25 188 21 190 18 190 Z" fill="#fff1de" />
      </g>

      <g className="ff-leg ff-leg-l">
        <rect x="78" y="196" width="19" height="46" rx="5" fill="#4e5a82" />
        <rect x="78" y="232" width="19" height="9" rx="3" fill="#6672a0" />
        <path d="M68 246 Q68 238 80 237 L94 238 Q99 247 93 251 L71 251 Q68 250 68 246 Z" fill="#1d1a3a" />
      </g>
      <g className="ff-leg ff-leg-r">
        <rect x="103" y="196" width="19" height="46" rx="5" fill="#4e5a82" />
        <rect x="103" y="232" width="19" height="9" rx="3" fill="#6672a0" />
        <path d="M132 246 Q132 238 120 237 L106 238 Q101 247 107 251 L129 251 Q132 250 132 246 Z" fill="#1d1a3a" />
      </g>

      <g className="ff-bob">
        <path d="M64 126 Q64 112 78 110 L122 110 Q136 112 136 126 L140 200 Q140 208 132 208 L68 208 Q60 208 60 200 Z" fill="#2c3a6e" />
        <path d="M86 110 L100 154 L114 110 Z" fill="#f6f6fb" />
        <path d="M76 111 L96 156 L87 164 L70 128 Z" fill="#23305f" />
        <path d="M124 111 L104 156 L113 164 L130 128 Z" fill="#23305f" />
        <path d="M100 156 L100 207" stroke="#23305f" strokeWidth="1.6" />
        <path d="M110 142 L124 141" stroke="#3d4d85" strokeWidth="2" strokeLinecap="round" />
        <path d="M88 108 L100 122 L112 108 L108 103 L100 112 L92 103 Z" fill="#fff" />

        <path d="M92 104 L100 168 L108 104" fill="none" stroke="#8b6be6" strokeWidth="3.4" strokeLinejoin="round" strokeLinecap="round" />
        <g className="ff-badge">
          <rect x="89" y="168" width="22" height="31" rx="3" fill="#fff" stroke="#cfcdea" />
          <rect x="93" y="173" width="14" height="12" rx="2" fill="#6b7cff" />
          <path d="M96 182 Q104 181 104 175 Q96 176 96 182 Z" fill="#fff" />
          <rect x="93" y="190" width="14" height="2" rx="1" fill="#cfcdea" />
        </g>

        <g className="ff-armup">
          <path d="M68 126 L52 146 L42 134" stroke="#2c3a6e" strokeWidth="15" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M46 139 L42 134" stroke="#fff" strokeWidth="13" fill="none" />
          <g>
            <ellipse cx="34" cy="126" rx="9.5" ry="7" transform="rotate(-35 34 126)" fill="#f58a34" />
            <ellipse cx="27" cy="119" rx="3.2" ry="7" transform="rotate(-22 27 119)" fill="#f58a34" />
            <ellipse cx="34" cy="116" rx="3.2" ry="7" transform="rotate(4 34 116)" fill="#f58a34" />
            <ellipse cx="41" cy="118" rx="3" ry="6" transform="rotate(26 41 118)" fill="#f58a34" />
            <ellipse cx="44" cy="129" rx="3.2" ry="5.5" transform="rotate(60 44 129)" fill="#f58a34" />
          </g>
          <g className="ff-spark" stroke="#6b7cff" strokeWidth="3" strokeLinecap="round">
            <path d="M22 98 L28 106" />
            <path d="M8 110 L18 114" />
            <path d="M12 126 L20 126" />
          </g>
        </g>

        <g className="ff-casearm">
          <path d="M132 128 Q148 158 150 186" stroke="#2c3a6e" strokeWidth="15" fill="none" strokeLinecap="round" />
          <path d="M150 182 L150 189" stroke="#fff" strokeWidth="13" fill="none" />
          <rect x="130" y="206" width="46" height="34" rx="4" fill="#7b4b2a" />
          <rect x="130" y="206" width="46" height="12" rx="4" fill="#6a3f22" />
          <rect x="149" y="213" width="8" height="9" rx="1.5" fill="#e6b422" />
          <path d="M141 207 Q141 194 153 194 Q165 194 165 207" fill="none" stroke="#5a3820" strokeWidth="3.4" />
          <ellipse cx="153" cy="196" rx="7.5" ry="6.5" fill="#f58a34" />
        </g>

        <g className="ff-head">
          <path d="M50 60 L40 6 L90 34 Z" fill="#f58a34" />
          <path d="M150 60 L160 6 L110 34 Z" fill="#f58a34" />
          <path d="M54 50 L49 17 L81 35 Z" fill="#2d2150" />
          <path d="M146 50 L151 17 L119 35 Z" fill="#2d2150" />
          <path d="M44 70 Q40 40 70 30 Q100 22 130 30 Q160 40 156 70 Q154 96 126 104 Q100 110 74 104 Q46 96 44 70 Z" fill="#f58a34" />
          <path d="M92 29 Q97 20 101 25 Q105 20 110 29 Z" fill="#f58a34" />
          <path d="M46 72 Q60 66 78 76 Q90 84 100 84 Q110 84 122 76 Q140 66 154 72 Q152 92 128 102 Q100 112 72 102 Q48 92 46 72 Z" fill="#fff1de" />
          <circle cx="67" cy="83" r="8" fill="#f7a3a3" opacity="0.55" />
          <circle cx="133" cy="83" r="8" fill="#f7a3a3" opacity="0.55" />
          <path d="M70 47 Q78 42 87 46" stroke="#a65a24" strokeWidth="2.4" fill="none" strokeLinecap="round" />
          <path d="M113 46 Q122 42 130 47" stroke="#a65a24" strokeWidth="2.4" fill="none" strokeLinecap="round" />
          <g className="ff-eyes">
            <ellipse cx="78" cy="63" rx="8.5" ry="9.5" fill="#3b2418" />
            <ellipse cx="78" cy="64" rx="6" ry="7" fill="#5a3623" />
            <circle cx="81" cy="59" r="2.6" fill="#fff" />
            <circle cx="75.5" cy="67" r="1.2" fill="#fff" opacity="0.7" />
            <ellipse cx="122" cy="63" rx="8.5" ry="9.5" fill="#3b2418" />
            <ellipse cx="122" cy="64" rx="6" ry="7" fill="#5a3623" />
            <circle cx="125" cy="59" r="2.6" fill="#fff" />
            <circle cx="119.5" cy="67" r="1.2" fill="#fff" opacity="0.7" />
          </g>
          <path d="M93 77 Q100 73 107 77 Q106 84 100 86 Q94 84 93 77 Z" fill="#2a2145" />
          <path d="M88 89 Q100 100 112 89 Q108 102 100 103 Q92 102 88 89 Z" fill="#c8403f" />
          <path d="M94 97 Q100 101 106 97 Q104 102 100 102 Q96 102 94 97 Z" fill="#f08a8a" />
          <path d="M88 89 Q94 91 100 88 Q106 91 112 89" stroke="#2a2145" strokeWidth="1.8" fill="none" strokeLinecap="round" />
          <path d="M100 86 L100 89" stroke="#2a2145" strokeWidth="1.8" />
        </g>
      </g>
    </svg>
  );
}

export default function Finn({ tab, onNavigate, userName }) {
  const [bubble, setBubble] = useState(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [box, setBox] = useState(null); // sidebar area, null while the sidebar is closed
  const [dragging, setDragging] = useState(false);
  const [landing, setLanding] = useState(false);
  const [tilt, setTilt] = useState(0);
  const [waving, setWaving] = useState(false);
  const [showName, setShowName] = useState(true);

  const used = useRef({});
  const nextAt = useRef(Date.now() + 15_000);
  const hideTimer = useRef(null);
  const waveTimer = useRef(null);
  const landTimer = useRef(null);
  const homeRef = useRef(null);
  const placed = useRef(false);
  const posRef = useRef(pos);
  const draggingRef = useRef(false);
  const drag = useRef({ active: false, moved: false, sx: 0, sy: 0, ox: 0, oy: 0, lastX: 0 });
  const name = (userName || "").trim();
  const shown = !!box;

  // Keep him inside the sidebar: place him, re-clamp on resize, hide when it closes.
  const sync = useCallback(() => {
    const b = getBounds();
    if (!b) {
      setBox(null);
      return;
    }
    let p;
    if (!placed.current) {
      const saved = readPos();
      if (saved) {
        p = clampTo(b, b.l - 4 + saved.rx, b.t - 4 + saved.ry);
      } else {
        const r = homeRef.current?.getBoundingClientRect();
        p = r && r.width
          ? clampTo(b, r.left + r.width / 2 - W / 2, r.bottom - H - 36)
          : clampTo(b, b.l + 20, b.b - H - 100);
      }
      placed.current = true;
    } else {
      p = clampTo(b, posRef.current.x, posRef.current.y);
    }
    posRef.current = p;
    setPos(p);
    setBox(b);
  }, []);

  useLayoutEffect(() => {
    sync();
    const sb = document.querySelector(".sidebar");
    const ro = typeof ResizeObserver !== "undefined" && sb ? new ResizeObserver(sync) : null;
    if (ro && sb) ro.observe(sb);
    window.addEventListener("resize", sync);
    return () => {
      ro?.disconnect();
      window.removeEventListener("resize", sync);
    };
  }, [sync]);

  // His name tag shows for a few seconds whenever he appears.
  useEffect(() => {
    if (!shown) return undefined;
    setShowName(true);
    const t = setTimeout(() => setShowName(false), 8000);
    return () => clearTimeout(t);
  }, [shown]);

  const wave = useCallback(() => {
    setWaving(true);
    clearTimeout(waveTimer.current);
    waveTimer.current = setTimeout(() => setWaving(false), 1700);
  }, []);

  const armHide = useCallback((ms = SHOW_MS) => {
    clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => {
      setBubble(null);
      nextAt.current = Date.now() + GAP_MS;
    }, ms);
  }, []);

  const close = useCallback((wait = GAP_MS) => {
    clearTimeout(hideTimer.current);
    setBubble(null);
    nextAt.current = Date.now() + wait;
  }, []);

  // Pick a random line for this page that he has not said yet.
  const ask = useCallback(
    (force = false) => {
      const list = questionsFor(tab, name);
      if (!list.length) return false;
      const seen = used.current[tab] || (used.current[tab] = new Set());
      let pool = list.filter((q) => !seen.has(q.id));
      if (!pool.length) {
        seen.clear();
        pool = list;
      }
      const pick = pool[Math.floor(Math.random() * pool.length)];
      seen.add(pick.id);
      if (!force) ss.set("fg_finn_count", String(Number(ss.get("fg_finn_count") || 0) + 1));
      const intro = !ss.get("fg_finn_greeted") && name && !pick.goal ? `Hi ${name}, I'm Finn! ` : "";
      ss.set("fg_finn_greeted", "1");
      setBubble({ ...pick, text: intro + pick.text });
      armHide();
      return true;
    },
    [tab, name, armHide]
  );

  useEffect(() => {
    if (bubble) wave();
  }, [bubble, wave]);

  // Politely check every few seconds whether it is time to say something.
  useEffect(() => {
    const t = setInterval(() => {
      if (!shown || bubble || draggingRef.current || document.hidden || ss.get("fg_finn_off")) return;
      if (Number(ss.get("fg_finn_count") || 0) >= MAX_QUESTIONS) return;
      if (Date.now() < nextAt.current) return;
      ask();
    }, 5000);
    return () => clearInterval(t);
  }, [shown, bubble, ask]);

  // New page: drop the old line, speak about the new page a bit later.
  useEffect(() => {
    close(20_000);
  }, [tab, close]);

  // Sidebar closed: he disappears, and so does anything he was saying.
  useEffect(() => {
    if (!shown) close(GAP_MS);
  }, [shown, close]);

  useEffect(
    () => () => {
      clearTimeout(hideTimer.current);
      clearTimeout(waveTimer.current);
      clearTimeout(landTimer.current);
    },
    []
  );

  const go = (to) => {
    onNavigate?.(to);
    close();
  };
  const choose = (chip) => {
    if (chip === "Not now") return close(SNOOZE_MS);
    const reply = bubble?.goal ? GOAL_REPLY(chip) : bubble?.replies?.[chip];
    if (!reply) return undefined;
    setBubble({ id: `${bubble.id}-answer`, text: reply.text, actions: reply.actions || [] });
    armHide();
    return undefined;
  };
  const stop = () => {
    ss.set("fg_finn_off", "1");
    close();
  };
  const talk = () => {
    if (bubble) return close();
    if (!ask(true)) {
      setBubble({ id: "hello", text: "I'm Finn. I'll pop up with ideas while you browse.", actions: [] });
      armHide(8000);
    }
    return undefined;
  };

  /* ---------- dragging, only inside the sidebar ---------- */
  const onPointerDown = (e) => {
    if (e.button !== undefined && e.button !== 0) return;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    drag.current = {
      active: true, moved: false,
      sx: e.clientX, sy: e.clientY,
      ox: posRef.current.x, oy: posRef.current.y,
      lastX: e.clientX,
    };
  };
  const onPointerMove = (e) => {
    const d = drag.current;
    if (!d.active) return;
    const dx = e.clientX - d.sx;
    const dy = e.clientY - d.sy;
    if (!d.moved) {
      if (Math.hypot(dx, dy) < 6) return;
      d.moved = true;
      draggingRef.current = true;
      setDragging(true);
      setLanding(false);
    }
    const b = getBounds();
    if (!b) return;
    const p = clampTo(b, d.ox + dx, d.oy + dy);
    posRef.current = p;
    setPos(p);
    setTilt(clamp((e.clientX - d.lastX) * 1.2, -16, 16));
    d.lastX = e.clientX;
  };
  const endDrag = (e, cancelled = false) => {
    const d = drag.current;
    if (!d.active) return;
    d.active = false;
    try { e.currentTarget.releasePointerCapture?.(e.pointerId); } catch { /* ignore */ }
    if (d.moved) {
      draggingRef.current = false;
      setDragging(false);
      setTilt(0);
      setLanding(true);
      const b = getBounds();
      if (b) savePos({ rx: posRef.current.x - (b.l - 4), ry: posRef.current.y - (b.t - 4) });
      clearTimeout(landTimer.current);
      landTimer.current = setTimeout(() => setLanding(false), 650);
      wave();
    } else if (!cancelled) {
      talk(); // a tap, not a drag: he says something
    }
  };
  const onKeyDown = (e) => {
    const step = e.shiftKey ? 48 : 16;
    const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const m = moves[e.key];
    const b = getBounds();
    if (!m || !b) return;
    e.preventDefault();
    const p = clampTo(b, posRef.current.x + m[0], posRef.current.y + m[1]);
    posRef.current = p;
    setPos(p);
    savePos({ rx: p.x - (b.l - 4), ry: p.y - (b.t - 4) });
  };

  // Speech bubble: above him (or below near the top), always inside the sidebar.
  const bw = box ? Math.min(236, box.r - box.l) : 232;
  const above = box ? pos.y - box.t > 240 : true;
  const bubbleLeft = box ? clamp(pos.x + W / 2 - bw / 2, box.l, Math.max(box.l, box.r - bw)) - pos.x : 0;
  const tailX = clamp(W / 2 - bubbleLeft, 18, bw - 18);

    const cls = [
    "fg-finn-float",
    "is-ready",
    dragging && "is-dragging",
    landing && "is-landing",
    waving && "is-waving",
  ].filter(Boolean).join(" ");

  return (
    <>
      <aside className="fg-finn-home" ref={homeRef} aria-label="Finn's corner">
        <p className="fg-finn-tag">Better insights. Smarter decisions.</p>
      </aside>

      {shown &&
        createPortal(
          <div
            className={cls}
            style={{
              position: "fixed",
              left: 0,
              top: 0,
              width: W,
              height: H,
              zIndex: 9999,
              visibility: "visible",
              transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
            }}
          >
            {bubble && (
              <div
                className={`fg-finn-bubble ${above ? "is-above" : "is-below"}`}
                style={{ left: bubbleLeft, width: bw, "--tail-x": `${tailX}px` }}
                role="group"
                aria-live="polite"
                aria-label="Message from Finn"
              >
                <button type="button" className="fg-finn-x" onClick={() => close(SNOOZE_MS)} aria-label="Dismiss Finn's message">
                  <X size={13} />
                </button>
                <div className="fg-finn-who">Finn</div>
                <p>{bubble.text}</p>
                {bubble.chips && (
                  <div className="fg-finn-row">
                    {bubble.chips.map((c) => (
                      <button key={c} type="button" className="fg-finn-chip" onClick={() => choose(c)}>
                        {c}
                      </button>
                    ))}
                  </div>
                )}
                {bubble.actions?.length > 0 && (
                  <div className="fg-finn-row">
                    {bubble.actions.map((a) => (
                      <button key={a.label} type="button" className="fg-finn-primary" onClick={() => go(a.to)}>
                        {a.label}
                      </button>
                    ))}
                  </div>
                )}
                <div className="fg-finn-foot">
                  <button type="button" onClick={() => close(SNOOZE_MS)}>Not now</button>
                  <button type="button" onClick={stop}>Stop asking</button>
                </div>
              </div>
            )}

            <button
              type="button"
              className="fg-finn-hit"
              style={{
                "--tilt": `${tilt}deg`,
                display: "block",
                width: "100%",
                height: "100%",
                padding: 0,
                border: 0,
                background: "transparent",
                cursor: "grab",
                touchAction: "none",
              }}
              aria-label="Talk to Finn. Drag to move him around the sidebar."
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={(e) => endDrag(e)}
              onPointerCancel={(e) => endDrag(e, true)}
              onKeyDown={onKeyDown}
              onClick={(e) => {
                if (e.detail === 0) talk(); // keyboard Enter / Space
              }}
            >
              <span className="fg-finn-body">
                <FinnArt />
              </span>
            </button>
            <span className={`fg-finn-name${showName ? " is-shown" : ""}`} aria-hidden="true">
              Finn
            </span>
          </div>,
          document.body
        )}
    </>
  );
}