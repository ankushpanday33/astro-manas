const LAYERS = [
  ["Consent and inputs", "Name, date of birth, birth time and place, only after astro_consent_at is recorded (PRD 5.8). Plus what the user does: sessions, chats, purchases, messages."],
  ["Numerology engine", "Module A exactly as the PRD: Radical, Destiny, Chaldean Name number, weighted lucky and challenging numbers, colours, metals, Lo Shu. Every number keeps its proof string."],
  ["Panchang engine", "Module B at the exact birth instant: Tithi, Vara (sunrise rule), Nakshatra and pada, Yoga, Karana (fixed and movable rule), boundaries and uncertain Angas. Weighted 30/20/20/15/15."],
  ["The user row", "Everything is written once, in one transaction, to the \"user\" table with rule_version. The brain and the app read stored columns only."],
  ["Memory", "Chats read in time: the topic on their mind, worry, an upcoming interview or exam with its resolved date, opt-outs."],
  ["Facts and beliefs", "Facts computed in code with citations; beliefs (engagement, purchase intent, topic, anxiety, reachability) formed only from cited facts."],
  ["Digital twin", "Each offer x channel x time is scored on the user's own outcomes and rehearsed on their persona (MiroFish idea)."],
  ["Council", "Engagement Analyst, Wellbeing Advocate and Value Strategist argue; a moderator decides (BettaFish idea). An anxious user is never sold to."],
  ["Guards and timing", "Consent, opt-out, caps, quiet hours, responsible copy, no gemstone prescription. Then a send date whose day root is a lucky number (PRD 5.7)."],
  ["Holdout", "A fixed 10% is never messaged, so uplift is measured, not claimed."],
];

export default function How() {
  return (
    <main className="wrap">
      <section className="hero">
        <h1>How the astro brain <em>decides</em></h1>
        <p>Deterministic first, AI second. Claude only narrates and argues over values the engine already computed; it never invents a chart value.</p>
      </section>
      <section className="grid g2">
        {LAYERS.map(([t, d], i) => (
          <div key={t} className="panel">
            <h3>{String(i + 1).padStart(2, "0")} · {t}</h3>
            <p style={{ margin: 0 }}>{d}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
