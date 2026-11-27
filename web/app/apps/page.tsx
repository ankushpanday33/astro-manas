"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const USE_LABEL: Record<string, { label: string; color: string; text: string }> = {
  personalise: { label: "Personalise", color: "#22C55E", text: "May shape offers, topics and timing." },
  protect: { label: "Protect only", color: "#F59E0B", text: "Can only switch off paid offers and calm the copy. Never sells." },
  discard: { label: "Discard", color: "#EF4444", text: "Dropped at upload. Never stored, never inferred." },
};

export default function AppsPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api("/apps/catalog").then(setData).catch(() => {}); }, []);

  return (
    <main className="wrap">
      <section className="hero">
        <h1>Apps <em>tracked</em> and what they may tell the brain</h1>
        <p>If a user agrees, the app reports which tracked apps are installed. Each category has one use tier. Nothing here ever becomes a label
          about a person's character, fidelity, sexuality, health, caste or religion.</p>
      </section>
      {data && (
        <>
          <section className="panel" style={{ marginBottom: 16 }}>
            <h3>Rules</h3>
            <ul className="sq">{data.rules.map((r: string) => <li key={r}>{r}</li>)}</ul>
            <div className="row" style={{ gap: 18, marginTop: 8 }}>
              {Object.entries(USE_LABEL).map(([k, v]) => (
                <span key={k} style={{ fontSize: 13 }}><span className="status" style={{ color: v.color }}>{v.label}</span> <span className="muted">{v.text}</span></span>
              ))}
            </div>
          </section>
          <section className="panel">
            <table>
              <thead><tr><th>Category</th><th>Use</th><th>What the brain may conclude</th><th>Apps</th></tr></thead>
              <tbody>
                {data.categories.map((c: any) => (
                  <tr key={c.category}>
                    <td className="ink" style={{ fontWeight: 600 }}>{c.label}</td>
                    <td><span className="chip" style={{ borderColor: USE_LABEL[c.use].color, color: USE_LABEL[c.use].color }}>{USE_LABEL[c.use].label}</span></td>
                    <td style={{ fontSize: 14 }}>{c.logic}</td>
                    <td style={{ fontSize: 13 }}>{c.apps} · <span className="muted">{c.examples.join(", ")}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
              Package names mostly come from the Astrotalk installed-app analysis (23/11/2026). A few newer ones (PayMe India, Ram Fincorp, Jat Shaadi)
              come from third-party app trackers; Gleeden, Slush, Raya and SC Matrimony are matched by app name until their packages are confirmed.
            </p>
          </section>
        </>
      )}
    </main>
  );
}
