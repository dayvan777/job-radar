#!/bin/bash
# One scheduled Job Radar run. Called by launchd (macOS) or cron (Linux) at :37 every hour.
# Runs only 07-22 Berlin time; skips if a previous run is still going.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:/Library/TeX/texbin:/usr/bin:/bin:$PATH:$DIR/cv/tpl/bin"
H=$(TZ=Europe/Berlin date +%H)
if [ "$H" -lt 7 ] || [ "$H" -gt 22 ]; then exit 0; fi
mkdir -p logs tmp
LOCK="$DIR/tmp/run.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  # stale lock older than 90 minutes is removed
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +90 2>/dev/null)" ]; then rmdir "$LOCK"; mkdir "$LOCK"; else exit 0; fi
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
LOG="logs/run-$(TZ=Europe/Berlin date +%F).log"
echo "=== $(TZ=Europe/Berlin date '+%F %T') ===" >> "$LOG"
CHROME_FLAG=""
[ "${JOB_RADAR_CHROME:-0}" = "1" ] && CHROME_FLAG="--chrome"
claude -p "/job-run" $CHROME_FLAG --permission-mode dontAsk --max-turns 200 --output-format text >> "$LOG" 2>&1
echo "exit=$?" >> "$LOG"
python3 scripts/appstore.py >> "$LOG" 2>&1
python3 scripts/dashboard.py >> "$LOG" 2>&1
if [ -d .git ]; then git add -A data dashboard.html cv/jobs logs >/dev/null 2>&1; git commit -qm "run $(TZ=Europe/Berlin date '+%F %H:%M')" >/dev/null 2>&1; fi
