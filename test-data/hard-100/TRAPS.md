# Hard 100-user test set

All 100 people are fictional. Regenerate with `python scripts/make_hard_dataset.py`. Upload in this order on the **Upload data** page (or run `python scripts/upload_hard_dataset.py --live` against the running app):

| # | File | Upload as | Format | Traps planted |
|---|---|---|---|---|
| 1 | `1_users.csv` | Customers | CSV, BOM, own headers | DOB in 4 formats (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, DD.MM.YYYY); impossible 31/02/1990; "not known"; year 1890; blank DOB; birth time as `10:35`, `6:20 PM`, `06:20pm`, `18.45`, `06:20:00`, `unknown`, `25:61`; ids with spaces; consent as yes / Y / TRUE / 1 / agree / a date / no / blank; Devanagari names (no Chaldean letters); "Dr. A. K." names; unknown cities (Gorakhpur, Ujjain) with and without Lat/Lon; duplicate U050; an empty row; extra Notes column |
| 2 | `2_sessions.ndjson` | Sessions | NDJSON | Keys `uid`, `opened_at`, `duration`; ISO and DD/MM/YYYY HH:MM timestamps; minutes as "", "abc", numbers |
| 3 | `3_chats.csv` | Chats | Semicolon CSV | Hinglish with emoji; worry, opt-outs ("notifications band karo", "mat bhejo"), relative dates ("interview next week", "kal match hai"); lowercase ids `u015`; an id that does not exist (U999) |
| 4 | `4_purchases.json` | Purchases | JSON array | Amounts as "₹299", "₹1,100", "199.00", blank; a product the catalog does not know |
| 5 | `5_messages.tsv` | Communications | Tab-separated | Channel as WhatsApp / whatsapp / Push Notification / In-App / SMS; status as Read / DELIVERED / Seen / failed; replies in Hinglish |
| 6 | `6_events.xlsx` | Events | Excel | Event names as "Clicked CTA" and `clicked_cta`; real Excel datetimes mixed with "20/11/2026 07:04 PM"; half the ids lowercase |
| 7 | `7_installed_apps.csv` | Installed apps | CSV | Gleeden and Flo (must be dropped), Jat Shaadi and SC Matrimony (community must not be stored), PayMe and Ram Fincorp (protect only), Raya by name only, WhatsApp (untracked, dropped), a row with no package and no name |

## What a correct run looks like

- Users: 97 loaded, 5 skipped (31/02, "not known", 1890, blank DOB, empty row), U050 flagged as duplicate. `25:61` keeps the user but skips Panchang.
- Other files: rows for the 4 skipped users and U999 are reported as "no matching user"; lowercase ids are matched to the right user and reported as auto-fixed.
- Installed apps: 177 kept, 39 dropped (13 period / pregnancy, 12 extramarital dating, 13 untracked, 1 empty). No "Jat" anywhere in stored rows.
- Build: 96 brains, about 66 charts (consent) and 45 Panchang (consent + usable time + known place), 0 failures.
- Decisions by persona (`personas_answer_key.json`): money_stress and gamer users get only free daily guidance (protect only); opted_out and lapsing users are held; curious users with an abandoned checkout get a calm resume nudge; marriage seekers get marriage readings.
