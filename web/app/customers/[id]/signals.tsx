"use client";

import Link from "next/link";
import { pretty } from "@/lib/api";

const PRED: [string, string][] = [
  ["purchase_propensity_7d", "Buys in the next 7 days"],
  ["churn_risk_14d", "Goes quiet for 14 days"],
  ["login_completion", "Finishes login"],
];

/** In-app events, the predictions built on them, and installed-app signals by use tier. */
export default function SignalsPanel({ brain }: { brain: any }) {
  const p = brain.predictions ?? {};
  const fv: Record<string, any> = Object.fromEntries(brain.facts.map((f: any) => [f.id, f.value]));
  const signals = p.app_signals;

  return (
    <section className="panel" style={{ marginBottom: 16 }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>Signals and predictions</h3>
        <span className="badge gray">{p.rule_version ?? "events"}</span>
      </div>
      <div className="grid g3" style={{ marginTop: 12 }}>
        {PRED.map(([k, label]) => {
          const x = p[k] ?? { status: "insufficient_evidence" };
          return (
            <div key={k} className="tile" style={{ borderTopColor: x.value != null && k === "churn_risk_14d" && x.value > 0.5 ? "#F59E0B" : "#FF6623" }}>
              <div className="k">{label}</div>
              <div className="v">{x.value == null ? "–" : `${Math.round(x.value * 100)}%`}</div>
              {x.status !== "ok" ? <div className="n">{x.note ?? "not enough events yet"}</div> : (
                <div className="n">
                  {x.drivers.slice(0, 4).map((d: any) => (
                    <div key={d.feature}>{d.effect > 0 ? "▲" : d.effect < 0 ? "▼" : "■"} {pretty(d.feature)} = {String(d.value)} {d.effect ? `(${d.effect > 0 ? "+" : ""}${d.effect})` : ""}</div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <div>
          <h3>In-app events (30 days)</h3>
          <ul className="sq" style={{ fontSize: 14 }}>
            <li>{fv.events_30d ?? 0} events · {fv.cta_clicks_7d ?? 0} CTA clicks this week{fv.top_cta ? ` · most clicked: ${pretty(fv.top_cta)}` : ""}</li>
            <li>{fv.abandoned_checkout ? <>Left <b>{pretty(fv.abandoned_checkout)}</b> halfway in checkout</> : "No open checkout"}</li>
            <li>{fv.login_dropoff ? "Started login without finishing at least once" : "No login drop-off"}</li>
          </ul>
          <p className="muted" style={{ fontSize: 12 }}>Predictions are a transparent logistic score over named features; the drivers above are exactly what moved each number.</p>
        </div>
        <div>
          <h3>Installed-app signals</h3>
          {!p.app_consent ? (
            <p className="muted" style={{ fontSize: 14 }}>No app-signal consent: installed apps are ignored for this user.</p>
          ) : (
            <>
              <div style={{ fontSize: 14 }}>
                <span className="muted">Personalise: </span>
                {(fv.app_interests ?? []).length ? fv.app_interests.map((x: string) => <span key={x} className="chip high">{x}</span>) : <span className="muted">none</span>}
              </div>
              <div style={{ fontSize: 14, marginTop: 4 }}>
                <span className="muted">Protect only: </span>
                {(signals?.protect ?? []).length ? signals.protect.map((x: string) => <span key={x} className="chip" style={{ borderColor: "#F59E0B" }}>{pretty(x)}</span>) : <span className="muted">none</span>}
              </div>
              {fv.app_topic_hint && <p style={{ fontSize: 14, margin: "6px 0 0" }}>Apps point to: <b>{fv.app_topic_hint}</b></p>}
              {(fv.money_pressure_flag || fv.gaming_exposure_flag) && (
                <div className="notice" style={{ marginTop: 8 }}>Protect-only signal present: paid offers are switched off and the copy stays calm.</div>
              )}
            </>
          )}
          <p className="muted" style={{ fontSize: 12 }}>Affair-dating and period / pregnancy apps are dropped at upload; community matrimony apps count only as matrimony. <Link href="/apps" className="orange">See the policy</Link></p>
        </div>
      </div>
    </section>
  );
}
