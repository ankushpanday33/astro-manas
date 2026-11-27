"use client";

import { useEffect, useState } from "react";
import { api, ddmmyyyy } from "@/lib/api";

const LOSHU = [[4, 9, 2], [3, 5, 7], [8, 1, 6]];
const DIMS: [string, string, string][] = [
  ["score_core_personality", "Core personality", "Nakshatra · 30%"],
  ["score_mind_emotions", "Mind and emotions", "Tithi · 20%"],
  ["score_thinking_style", "Thinking style", "Yoga · 20%"],
  ["score_behaviour", "Behaviour", "Vara · 15%"],
  ["score_working_style", "Working style", "Karana · 15%"],
];

/** The stored "user" row, rendered exactly as computed (PRD: show the proof). Groups A and E stay in the engine. */
export default function AstroPanel({ id, hasChart }: { id: string; hasChart: boolean }) {
  const [data, setData] = useState<any>(null);
  const [spelling, setSpelling] = useState("");
  const [trial, setTrial] = useState<any>(null);

  useEffect(() => {
    if (hasChart) api(`/customers/${id}/astro`).then(setData).catch(() => setData(null));
  }, [id, hasChart]);

  if (!hasChart)
    return (
      <section className="panel" style={{ marginBottom: 16 }}>
        <h3>Astro profile</h3>
        <p className="muted" style={{ margin: 0 }}>No chart. Birth-data consent (astro_consent_at) is missing, so the engine did not compute anything (PRD 5.8). Only generic offers are allowed.</p>
      </section>
    );
  if (!data) return <section className="panel muted" style={{ marginBottom: 16 }}>Loading chart…</section>;

  const B = data.groups.B, C = data.groups.C, D = data.groups.D, F = data.groups.F, G = data.groups.G, H = data.groups.H, I = data.groups.I;
  const grid = D.loshu_grid ?? {};
  const hasP = F.nakshatra_name != null;

  return (
    <section className="panel" style={{ marginBottom: 16 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Astro profile: stored on the user row</h3>
        <span className="row" style={{ gap: 6 }}>
          <span className="badge gray">rule v{I.rule_version}</span>
          <span className="badge gray">{I.source_tradition}</span>
          <span className="badge gray">compatibility v{I.compatibility_version}</span>
        </span>
      </div>
      {H.personality_title && <h2 style={{ fontSize: 22, margin: "10px 0 4px" }} className="orange">{H.personality_title}</h2>}
      {H.core_traits?.length > 0 && <p style={{ margin: "0 0 12px" }}>{H.core_traits.join(" ")}</p>}

      <div className="grid g3">
        <div>
          <h3>Numerology (Module A)</h3>
          <table><tbody>
            {[["Radical (Mulank)", B.radical_number, B.radical_planet, B.radical_calculation],
              ["Destiny (Bhagyank)", B.destiny_number, B.destiny_planet, B.destiny_calculation],
              ["Name (Namank)", B.name_number, B.name_planet, B.name_calculation]].map(([k, v, p, calc]) => (
              <tr key={k as string}>
                <td><div className="ink">{k}</div><div className="mono">{calc}</div></td>
                <td className="ink" style={{ fontSize: 22, fontWeight: 700 }}>{v}</td>
                <td className="muted">{p}</td>
              </tr>
            ))}
          </tbody></table>
          <div style={{ marginTop: 10, fontSize: 14 }}>
            <div>Lucky: {C.lucky_numbers?.map((n: number) => <span key={n} className="chip high">{n}</span>)}</div>
            <div>Neutral: {C.neutral_numbers?.map((n: number) => <span key={n} className="chip">{n}</span>)}</div>
            <div>Challenging: {C.challenging_numbers?.map((n: number) => <span key={n} className="chip low">{n}</span>)}
              <span className="muted" style={{ fontSize: 12 }}> a compatibility reading, not a bad-luck prediction</span></div>
            <div className="mono" style={{ marginTop: 4 }}>scores {JSON.stringify(C.number_scores)}</div>
          </div>
        </div>

        <div>
          <h3>Recommendations</h3>
          <ul className="sq" style={{ fontSize: 14 }}>
            <li>Colours: <b>{C.lucky_colours_primary?.join(", ")}</b>{C.lucky_colours_secondary?.length ? `, then ${C.lucky_colours_secondary.join(", ")}` : ""}</li>
            <li>Metals: {C.lucky_metals?.join(", ")}</li>
            <li>Traditional gemstone: {C.traditional_gemstones?.join(", ")} <span className="badge">{C.gemstone_prescription}</span>
              <div className="muted" style={{ fontSize: 12 }}>Association only. Wearing advice needs a full Kundli review.</div></li>
          </ul>
          <h3 style={{ marginTop: 14 }}>Lo Shu grid ({D.loshu_variant})</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 52px)", border: "2px solid #FF6623", width: 160 }}>
            {LOSHU.flat().map((n) => (
              <div key={n} style={{ height: 52, border: "1px solid #FFE0D0", display: "flex", alignItems: "center", justifyContent: "center",
                background: grid[n] ? "#FFF3EE" : "#fff", color: grid[n] ? "#FF6623" : "#D1D5DB", fontWeight: 700, fontSize: 16 }}>
                {grid[n] ? String(n).repeat(grid[n]) : n}
              </div>
            ))}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Missing {D.loshu_missing_digits?.join(", ") || "none"} · planes {D.loshu_complete_planes?.length ? D.loshu_complete_planes.join(", ") : "none"}
          </div>
          <h3 style={{ marginTop: 14 }}>Name correction</h3>
          <form className="row" onSubmit={async (e) => { e.preventDefault(); if (spelling.trim()) setTrial(await api(`/customers/${id}/name-trial`, { spelling })); }}>
            <input type="text" placeholder="Try a spelling" value={spelling} onChange={(e) => setSpelling(e.target.value)} style={{ width: 150 }} />
            <button className="btn ghost">Compare</button>
          </form>
          {trial && (
            <div style={{ fontSize: 13, marginTop: 6 }}>
              <div>Main: <b>{trial.main.name}</b> = {trial.main.compound} → {trial.main.value}</div>
              <div>Trial: <b>{trial.trial.name}</b> = {trial.trial.calculation} → {trial.trial.value} ({trial.trial.planet})</div>
              <div className="muted">Saved to name_correction_trials only; the main result is never overwritten.</div>
            </div>
          )}
        </div>

        <div>
          <h3>Birth Panchang (Module B)</h3>
          {hasP ? (
            <>
              <table style={{ fontSize: 13 }}><tbody>
                <tr><td className="muted">Nakshatra</td><td className="ink">{F.nakshatra_name} pada {F.nakshatra_pada} · {F.nakshatra_lord} · navamsa {F.navamsa_sign}</td></tr>
                <tr><td className="muted">Tithi</td><td className="ink">{F.tithi_name} ({F.paksha})</td></tr>
                <tr><td className="muted">Vara</td><td className="ink">{F.vara_name} · {F.vara_lord}{F.vara_sunrise_adjusted ? " · born before sunrise" : ""}</td></tr>
                <tr><td className="muted">Yoga</td><td className="ink">{F.yoga_name}</td></tr>
                <tr><td className="muted">Karana</td><td className="ink">{F.karana_name} ({F.karana_type})</td></tr>
                <tr><td className="muted">Nakshatra window</td><td className="mono">{ddmmyyyy(F.nakshatra_start_utc)} to {ddmmyyyy(F.nakshatra_end_utc)} UTC</td></tr>
              </tbody></table>
              {F.panchang_uncertain_angas?.length > 0 && (
                <div className="notice" style={{ marginTop: 8 }}>Birth time is approximate: {F.panchang_uncertain_angas.join(", ")} may change inside the window.</div>
              )}
              <div style={{ marginTop: 10 }}>
                {DIMS.map(([k, label, src]) => (
                  <div key={k} style={{ marginBottom: 6 }}>
                    <div className="row" style={{ justifyContent: "space-between", fontSize: 13 }}><span className="ink">{label}</span><span className="muted">{src} · {G[k]}</span></div>
                    <div className="bar" style={{ border: "1px solid #E5E7EB" }}><div style={{ width: `${G[k]}%`, background: "#FF6623" }} /></div>
                  </div>
                ))}
                <div className="ink" style={{ fontWeight: 700, marginTop: 6 }}>Overall {G.overall_profile_score} / 100</div>
                <div className="muted" style={{ fontSize: 12 }}>An internal weighting of description strength, not a measure of intelligence, success or character.</div>
              </div>
            </>
          ) : (
            <p className="muted">Birth time unknown, so Panchang columns stay NULL (PRD 5.1). Numerology still works from the date of birth.</p>
          )}
        </div>
      </div>
      {(H.strengths?.length > 0 || H.career_work_style) && (
        <div className="grid g3" style={{ marginTop: 14, fontSize: 14 }}>
          <div><h3>Strengths</h3><ul className="sq">{H.strengths?.map((x: string) => <li key={x}>{x}</li>)}</ul></div>
          <div><h3>Work style</h3><p style={{ margin: 0 }}>{H.career_work_style}</p></div>
          <div><h3>Social style</h3><p style={{ margin: 0 }}>{H.relationship_style}</p>
            <p className="muted" style={{ fontSize: 12 }}>Narrative by {H.ai_model}, from stored values only.</p></div>
        </div>
      )}
    </section>
  );
}
