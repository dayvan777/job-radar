---
description: One full Job Radar run (ingest, fit, packages, sending, outcomes, learning, report) by the rules in CLAUDE.md
---
Run one complete Job Radar cycle exactly as CLAUDE.md describes, without asking questions.

1. `TZ=Europe/Berlin date` to get the current Berlin time and hour. Read state: `python3 scripts/db.py get meta run`, and jobs, signals, projects, companies, experiments, insights, events. Apply meta/run.overrides.
2. Section 7 (outcomes from Gmail) first, so replies are never missed even if later steps fail.
3. Section 2 (ingest). Arbeitnow and WebSearch only if the hour is 7, 12 or 17.
4. Section 3 (fit), section 5 (packages for priority >= 75), section 6 (sending, within limits). Browser applications only if mcp__claude-in-chrome__* tools exist.
5. Section 8 if meta/run.lastProfile is not today; weekly review if due.
6. Section 10: update meta/run (lastRun, scanned, added, sent, note, history), run `python3 scripts/dashboard.py`, notify by email only when section 10 says so.
7. Final reply: a short Russian summary, or exactly "Ничего нового".
