"use client";

import Link from "next/link";
import { use, useEffect, useMemo, useRef, useState } from "react";
import { ACTION_LABEL, api, ddmmyyyy, pretty } from "@/lib/api";

type N = { id: string; layer: number; label: string; value: any; detail: string; kind: string; path: boolean; rank?: number };
type E = { from: string; to: string; why: string; weight: number; path: boolean };
type Net = { layers: string[]; captions: string[]; nodes: N[]; edges: E[]; decision: any };

const COL_W = 182, NODE_W = 150, NODE_H = 40, GAP = 10, TOP = 56, LEFT = 16;

function show(v: any): string {
  if (v === null || v === undefined || v === "") return "";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "boolean") return v ? "yes" : "no";
  return String(v);
}

export default function NetworkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [net, setNet] = useState<Net | null>(null);
  const [brainName, setBrainName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState(7);
  const [playing, setPlaying] = useState(false);
  const [pathOnly, setPathOnly] = useState(false);
  const [sel, setSel] = useState<string | null>("decision");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api(`/customers/${id}/network`).then(setNet).catch((e) => setError(e.message));
    api(`/customers/${id}`).then((d) => setBrainName(d.brain.display_name)).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setInterval(() => {
      setStep((s) => {
        if (s >= 7) { setPlaying(false); return 7; }
        return s + 1;
      });
    }, 1400);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing]);

  const layout = useMemo(() => {
    if (!net) return null;
    const byLayer: N[][] = net.layers.map(() => []);
    net.nodes.forEach((n) => byLayer[n.layer].push(n));
    // Decision-path nodes first so the story reads top-down.
    byLayer.forEach((col) => col.sort((a, b) => Number(b.path) - Number(a.path) || (a.rank ?? 0) - (b.rank ?? 0)));
    const tallest = Math.max(...byLayer.map((c) => c.length));
    const height = TOP + tallest * (NODE_H + GAP) + 20;
    const pos: Record<string, { x: number; y: number }> = {};
    byLayer.forEach((col, li) => {
      const colH = col.length * (NODE_H + GAP);
      const y0 = TOP + (tallest * (NODE_H + GAP) - colH) / 2;
      col.forEach((n, i) => { pos[n.id] = { x: LEFT + li * COL_W, y: y0 + i * (NODE_H + GAP) }; });
    });
    return { pos, height, width: LEFT * 2 + net.layers.length * COL_W - (COL_W - NODE_W) };
  }, [net]);

  if (error) return <main className="wrap"><div className="notice">{error}</div></main>;
  if (!net || !layout) return <main className="wrap muted">Building the network…</main>;

  const nodeById = Object.fromEntries(net.nodes.map((n) => [n.id, n]));
  const visibleNode = (n: N) => n.layer <= step && (!pathOnly || n.path);
  const visibleEdge = (e: E) => nodeById[e.to].layer <= step && nodeById[e.from].layer <= step && (!pathOnly || e.path);
  const selected = sel ? nodeById[sel] : null;
  const related = new Set<string>();
  if (selected) net.edges.forEach((e) => { if (e.from === sel) related.add(e.to); if (e.to === sel) related.add(e.from); });
  const d = net.decision;

  return (
    <main className="wrap" style={{ maxWidth: 1560 }}>
      <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
        <Link href="/">Dashboard</Link> / <Link href={`/customers/${id}`}>{brainName || id}</Link> / decision network
      </div>
      <section className="hero">
        <h1>How the decision for {brainName || id} was <em>made</em></h1>
        <p>Every box is a real value the engine computed; every line is a real dependency (a formula input, a cited fact, a persona-fit rule, a vote).
          Orange lines carry the signal that reached the final decision. Press play to watch it travel layer by layer.</p>
      </section>

      <section className="panel" style={{ marginBottom: 12 }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="row">
            <button className="btn" onClick={() => { setStep(0); setPlaying(true); }}>{playing ? "Playing…" : "▶ Play the decision"}</button>
            <button className="btn ghost" disabled={playing} onClick={() => setStep((s) => Math.max(0, s - 1))}>◀ Step back</button>
            <button className="btn ghost" disabled={playing} onClick={() => setStep((s) => Math.min(7, s + 1))}>Step ▶</button>
            <label className="row" style={{ gap: 6, fontSize: 14 }}>
              <input type="checkbox" checked={pathOnly} onChange={(e) => setPathOnly(e.target.checked)} /> Only the decision path
            </label>
          </div>
          {d && (
            <div className="row" style={{ gap: 8 }}>
              <span className={`status ${d.action}`}>{ACTION_LABEL[d.action]}</span>
              {d.offer && <span className="muted" style={{ fontSize: 13 }}>{pretty(d.offer)} · {pretty(d.channel)} · {ddmmyyyy(d.send_at)}</span>}
            </div>
          )}
        </div>
        <div className="quote" style={{ marginTop: 12 }}>
          <b>{String(step + 1).padStart(2, "0")} · {net.layers[step]}.</b> {net.captions[step]}
        </div>
      </section>

      <section className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) 320px", alignItems: "start" }}>
        <div className="panel" style={{ overflowX: "auto", padding: 8 }}>
          <svg viewBox={`0 0 ${layout.width} ${layout.height}`} width={layout.width} height={layout.height} style={{ display: "block" }}>
            {net.layers.map((l, i) => (
              <g key={l} opacity={i <= step ? 1 : 0.25}>
                <text x={LEFT + i * COL_W + NODE_W / 2} y={22} textAnchor="middle" fontSize={12} fontWeight={700}
                  fill={i === step ? "#FF6623" : "#6B7280"} fontFamily="Helvetica Neue, Helvetica, Arial">
                  {String(i + 1).padStart(2, "0")} {l.toUpperCase()}
                </text>
                <line x1={LEFT + i * COL_W} x2={LEFT + i * COL_W + NODE_W} y1={32} y2={32} stroke={i === step ? "#FF6623" : "#E5E7EB"} strokeWidth={2} />
              </g>
            ))}

            {net.edges.map((e, i) => {
              const a = layout.pos[e.from], b = layout.pos[e.to];
              if (!a || !b) return null;
              const vis = visibleEdge(e);
              const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2, x2 = b.x, y2 = b.y + NODE_H / 2;
              const mx = (x1 + x2) / 2;
              const focus = sel && (e.from === sel || e.to === sel);
              return (
                <path key={i} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} fill="none"
                  stroke={focus ? "#1A1A1A" : e.path ? "#FF6623" : "#D1D5DB"}
                  strokeWidth={(e.path ? 1.6 : 1) * Math.max(0.8, Math.min(2.5, e.weight * 1.4))}
                  opacity={vis ? (e.path || focus ? 0.95 : 0.55) : 0.04}
                  className={vis && e.path && nodeById[e.to].layer === step ? "flow" : undefined}>
                  <title>{`${nodeById[e.from].label} → ${nodeById[e.to].label}: ${e.why}`}</title>
                </path>
              );
            })}

            {net.nodes.map((n) => {
              const p = layout.pos[n.id];
              const vis = visibleNode(n);
              const isDecision = n.id === "decision";
              const isSel = sel === n.id;
              const fill = isDecision ? "#FF6623" : n.path ? "#FFF3EE" : "#FFFFFF";
              const val = show(n.value);
              return (
                <g key={n.id} transform={`translate(${p.x},${p.y})`} opacity={vis ? (sel && !isSel && !related.has(n.id) && !n.path ? 0.5 : 1) : 0.06}
                  style={{ cursor: "pointer" }} onClick={() => setSel(n.id)}>
                  <rect width={NODE_W} height={NODE_H} rx={6} fill={fill} stroke={isSel ? "#1A1A1A" : n.path ? "#FF6623" : "#E5E7EB"} strokeWidth={isSel ? 2 : 1} />
                  <text x={8} y={16} fontSize={11.5} fontWeight={700} fill={isDecision ? "#fff" : "#1A1A1A"} fontFamily="Helvetica Neue, Helvetica, Arial">
                    {n.rank ? `#${n.rank} ` : ""}{n.label.length > 22 ? n.label.slice(0, 21) + "…" : n.label}
                  </text>
                  <text x={8} y={31} fontSize={11} fill={isDecision ? "#fff" : "#6B7280"} fontFamily="Helvetica Neue, Helvetica, Arial">
                    {val.length > 24 ? val.slice(0, 23) + "…" : val}
                  </text>
                  <title>{`${n.label}: ${val}\n${n.detail}`}</title>
                </g>
              );
            })}
          </svg>
        </div>

        <aside className="panel" style={{ position: "sticky", top: 76 }}>
          {selected ? (
            <>
              <h3>{selected.kind}</h3>
              <h2 style={{ fontSize: 18 }}>{selected.label}</h2>
              {show(selected.value) && <div className="quote" style={{ margin: "8px 0" }}>{show(selected.value)}</div>}
              <p style={{ fontSize: 14 }}>{selected.detail}</p>
              <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>{selected.path ? "On the decision path" : "Considered, but not on the decision path"}</div>
              <h3 style={{ marginTop: 12 }}>Fed by</h3>
              <ul className="sq" style={{ fontSize: 13 }}>
                {net.edges.filter((e) => e.to === selected.id).map((e, i) => (
                  <li key={i}><a onClick={() => setSel(e.from)} style={{ cursor: "pointer", fontWeight: 600 }}>{nodeById[e.from].label}</a>: {e.why}</li>
                ))}
                {!net.edges.some((e) => e.to === selected.id) && <li className="muted">a raw input</li>}
              </ul>
              <h3 style={{ marginTop: 12 }}>Feeds</h3>
              <ul className="sq" style={{ fontSize: 13 }}>
                {net.edges.filter((e) => e.from === selected.id).map((e, i) => (
                  <li key={i}><a onClick={() => setSel(e.to)} style={{ cursor: "pointer", fontWeight: 600 }}>{nodeById[e.to].label}</a>: {e.why}</li>
                ))}
                {!net.edges.some((e) => e.from === selected.id) && <li className="muted">the end of the line</li>}
              </ul>
            </>
          ) : <p className="muted">Click any box to see what fed it and what it fed.</p>}
        </aside>
      </section>

      {d?.message_preview && (
        <section className="panel" style={{ marginTop: 12 }}>
          <h3>What the user will see</h3>
          <div className="quote">{d.message_preview}</div>
          <p style={{ fontSize: 14, marginBottom: 0 }}>{d.reason}</p>
        </section>
      )}
    </main>
  );
}
