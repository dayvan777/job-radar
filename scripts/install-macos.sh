#!/bin/bash
# Installs a launchd agent that runs scripts/run.sh at minute 37 of every hour 07-22 (local time).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PL="$HOME/Library/LaunchAgents/com.jobradar.agent.plist"
INTERVALS=""
for h in $(seq 7 22); do INTERVALS="$INTERVALS<dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>37</integer></dict>"; done
cat > "$PL" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.jobradar.agent</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>$DIR/scripts/run.sh</string></array>
<key>StartCalendarInterval</key><array>$INTERVALS</array>
<key>StandardOutPath</key><string>$DIR/logs/launchd.out</string>
<key>StandardErrorPath</key><string>$DIR/logs/launchd.err</string>
</dict></plist>
PLIST
mkdir -p "$DIR/logs"
launchctl unload "$PL" 2>/dev/null
launchctl load "$PL" && echo "OK: Job Radar будет запускаться в :37 каждый час с 07 до 22. Проверить: launchctl list | grep jobradar"
