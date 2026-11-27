# Astro Manas: an astro brain for every user

Astro Manas is the AI astrology version of [Manas](../manas). It implements the **Vedic Astrology Engine PRD (Draft 2.0)** exactly, stores every value on the `user` table, and adds a decision brain that picks the next best action for each user. A decision network page shows how each decision was made.

## The engine (PRD Modules A and B)

| Part | Where | Notes |
|---|---|---|
| Versioned config tables | `backend/app/astro/config.py` | Chaldean map, planets, compatibility v1.0, colours, Nakshatras, Yogas, Karanas, weights |
| Module A: Numerology | `backend/app/astro/numerology.py` | Radical, Destiny, Name, weighted lucky and challenging numbers, Lo Shu, name trials. Proof string on every number |
| Module B: Birth Panchang | `backend/app/astro/panchang.py` | Tithi, Vara (sunrise rule), Nakshatra and pada, Yoga, Karana (fixed and movable), boundaries, uncertain Angas, 30/20/20/15/15 score |
| Ephemeris | `backend/app/astro/ephemeris.py` | Demo-grade (Meeus main terms, linear Lahiri). **Replace with a validated sidereal ephemeris before production** |
| `user` table and compute pipeline | `backend/app/astro/engine.py` | Columns grouped A to I as in PRD 5.2, one transactional write, consent first, AI narrative from stored values only |

`backend/tests/test_astro_engine.py` checks the PRD worked example (RAVI, 24/06/2000) value by value.

## The brain

Chart + behaviour (sessions, chats, purchases, messages) become facts and beliefs (engagement, purchase intent, topic, anxiety, reachability). Every offer (daily horoscope, topic reading, astrologer consult, planet puja, personality report, name correction) is rehearsed on a digital twin, three agents argue (Engagement Analyst, Wellbeing Advocate, Value Strategist), and a moderator decides. Guards: consent, opt-out, caps, quiet hours, responsible copy, no gemstone prescription, and a wellbeing override so an anxious user is never sold to. Timing prefers a day whose root is a lucky number (PRD 5.7). Astrologers are matched on nakshatra lord and radical planet.

## Decision network

`/customers/{id}/network` draws the whole decision as a layered graph: inputs, chart engine, facts, beliefs, digital twin, council, moderator and guards, decision. Orange lines carry the signal that reached the final decision. Press **Play** to watch it travel layer by layer; click any box to see what fed it and what it fed. Data comes from `GET /api/customers/{id}/network` (`backend/app/network.py`).

## Run it

```powershell
cd backend; uv sync; uv run uvicorn app.main:app --port 8010
```

```powershell
cd web; npm install; npm run dev
```

Open http://localhost:3010 and press **Load demo data and run everything** (about 20 seconds for 120 fictional users). Set `ANTHROPIC_API_KEY` to let Claude write narratives, read chats, role-play the twin and run the council. Without it, everything runs on deterministic rules.

```powershell
cd backend; uv run pytest -q
```

## Upload your own data

Open **Upload data** in the app (`/data`). Each file has a card with its required columns, a downloadable template and an upload box. CSV (comma, semicolon, tab, pipe), Excel `.xlsx`, JSON and NDJSON all work, with your own column names (`User ID`, `Date of Birth`, `Place of Birth` are matched automatically) and DD/MM/YYYY dates. Every upload returns a report: rows loaded, rows skipped with the reason, matched and unrecognised columns. The users file needs `dob`; birth time, place and `astro_consent_at` (or a yes/no consent column) unlock the chart, and common Indian cities are geocoded without an external service. Then press **Build brains and decide**. Re-uploading a corrected date of birth recomputes the chart (PRD 5.5).

API: `GET /api/ingest/schema`, `GET /api/ingest/template/{source}`, `POST /api/ingest/{source}` (multipart `file`, `mode` = append or replace), `POST /api/data/reset` with `{"confirm": true}`.

## In-app events and predictions

Upload `events` (or let the app send them): `viewed_login`, `interacted_login`, `completed_login`, `viewed_screen`, `clicked_cta`, `viewed_paywall`, `started_checkout`, `abandoned_checkout`, `completed_purchase`. `backend/app/predict.py` turns them into three transparent predictions: purchase in the next 7 days, going quiet for 14 days, and finishing login. Each is a logistic score over named features with weights in config, and each returns the drivers that moved it. Fewer than 6 events in 30 days returns `insufficient_evidence`. An abandoned checkout unlocks a calm `resume_checkout` offer.

## Installed-app signals

`backend/app/astro/app_catalog.py` lists the tracked apps (mostly from the Astrotalk installed-app analysis, plus PayMe India, Ram Fincorp, Jat Shaadi, Raya, Gleeden and Slush) in categories, each with one use tier and the logic the brain may apply. The **Apps tracked** page shows the policy.

| Tier | Categories | What it may do |
|---|---|---|
| Personalise | Matrimony (incl. community apps), dating, premium dating, jobs, education, investing, credit, UPI, competitor astrology, devotional, travel, audio | Shape offers, topics and timing |
| Protect only | Instant / high-interest loans, betting / fantasy / rummy | Switch off paid offers and calm the copy. Never sells |
| Discard | Extramarital dating, period / fertility / pregnancy | Dropped at upload, never stored |

Nothing is used without `app_signal_consent` on the user. Untracked apps are never stored. Community matrimony apps are stored only as "Matrimony app (community not stored)". The brain never produces a label about character, fidelity, sexuality, health, caste or religion, and message copy blocks words such as loan, debt, betting, affair and caste. Packages for Gleeden, Slush, Raya and SC Matrimony are not confirmed, so they are matched by app name.

## MCP, Mixpanel / PostHog and delivery planning

**MCP server.** `backend/app/mcp_server.py` exposes the brains to Claude or any MCP client: `list_users`, `get_user_brain`, `get_next_action`, `decide_now`, `explain_decision`, `ask_brain`, `ingest_events`, `sync_analytics`, `push_decisions`, `rebuild_and_decide`, `messaging_platforms`, `apps_policy`. Claude Code picks up `.mcp.json` in the repo root. For Claude Desktop, add the same block with the full path to `backend`:

```json
{"mcpServers": {"astro-manas": {"command": "uv", "args": ["run", "--directory", "backend", "python", "-m", "app.mcp_server"]}}}
```

Tools never return birth date, time, place or coordinates. On Windows, keep the repo in a short path (for example `C:\\code\\astro-manas`): very long paths break a native dependency of the MCP SDK.

**Events in.** `POST /api/collect/{mixpanel|posthog|generic}` takes live events (one or a batch) in each vendor's own shape, maps their names (for example `payment_failed` to `abandoned_checkout`, `$pageview` to `viewed_screen`) and stores them. Set `MANAS_COLLECT_SECRET` to require an `X-Manas-Secret` header. `POST /api/integrations/{mixpanel|posthog}/sync` pulls recent raw events (Mixpanel Raw Event Export, PostHog HogQL query API). Override names with `MANAS_EVENT_MAP_JSON`.

**Decisions out.** `POST /api/integrations/{mixpanel|posthog}/push` writes each user's next action as `manas_*` user properties plus a `manas_decision` event (Mixpanel `/engage` + `/track`, PostHog `/batch/`). Never pushed: birth details, chart internals beyond lucky numbers, installed-app signals, protect-only flags or anything read from chats.

Env vars: `MIXPANEL_PROJECT_ID`, `MIXPANEL_SERVICE_USER`, `MIXPANEL_SERVICE_SECRET`, `MIXPANEL_TOKEN`, `MIXPANEL_REGION` (`us`, `eu` or `in`; India projects use `data-in` / `api-in` hosts), `POSTHOG_HOST`, `POSTHOG_INGEST_HOST`, `POSTHOG_PROJECT_ID`, `POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_API_KEY`. Without them every sync and push is a dry run that returns the exact request.

**Channel, platform, language and message.** `backend/app/messaging.py` turns each decision into a delivery plan: the platform for the channel (WhatsApp Cloud API, Gupshup, Twilio, MSG91, Kaleyra, FCM, OneSignal, CleverTap, in-app inbox, Exotel, SendGrid), chosen by configured credentials, your measured delivery rate per platform and cost; a same-channel backup and a fallback channel; the language from the profile and the script from how the person actually writes (Devanagari Hindi, Hinglish in Roman letters, English); and the copy in each channel's shape (WhatsApp template name and language, SMS encoding, segments and DLT id, push title and body, in-app card). Hindi and Hinglish templates are built in; other languages fall back to the nearest template and are translated by Claude when it is on. Platform costs are illustrative: override the list with `MANAS_PROVIDERS_JSON`. Nothing is sent: the plan includes the request a sender would make.

## Not done yet

- Production ephemeris and IANA timezone database (demo uses fixed offsets, Indian cities only).
- Anga scores use a placeholder rule (base 80, +10 clear of boundaries, -15 uncertain); the astrology team should own this table.
- Messages are decided, not sent. Templates are English only.
- Dashboard uplift numbers are simulated and labelled so.
