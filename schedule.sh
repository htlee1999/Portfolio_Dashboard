#!/usr/bin/env bash
# Schedule the twice-weekly assessments (backend/batch.py) with macOS launchd. On Mondays and
# Fridays it starts every hour from 09:00 to 20:00; each start assesses the next 4 stocks of the
# day's run and exits (the days, hours and chunk size are set in batch.py). An hour missed while
# the Mac was asleep starts when it wakes; the later hours leave room to catch up. The Ollama app
# must be running.
#
#   ./schedule.sh install     # create or update the job
#   ./schedule.sh uninstall   # remove it
#   ./schedule.sh status      # is it loaded, and the end of the log
#   ./schedule.sh run         # assess the next chunk now, in the background
set -euo pipefail
cd "$(dirname "$0")"

LABEL="com.portfolio-dashboard.assessments"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ROOT="$(pwd)"
PYTHON="${PYTHON:-$(command -v python3)}"
LOG="$ROOT/data/logs/scheduled.log"
USER_NAME="${SCHEDULE_USER:-admin}"

case "${1:-}" in
  install)
    mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
    SLOTS="$(PYTHONPATH="$ROOT" "$PYTHON" -m backend.batch --print-slots | while read -r day hour; do
      echo "    <dict><key>Weekday</key><integer>$day</integer><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>0</integer></dict>"
    done)"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string><string>-m</string><string>backend.batch</string>
    <string>--user</string><string>$USER_NAME</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict><key>PYTHONPATH</key><string>$ROOT</string></dict>
  <key>StartCalendarInterval</key>
  <array>
$SLOTS
  </array>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>ProcessType</key><string>Background</string>
</dict>
</plist>
EOF
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    echo "Scheduled hourly on run days ($(echo "$SLOTS" | wc -l | tr -d ' ') slots a week) for user $USER_NAME. Log: $LOG"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed $LABEL"
    ;;
  status)
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|last exit code|runs" || echo "Not installed"
    [ -f "$LOG" ] && tail -n 20 "$LOG"
    ;;
  run)
    launchctl kickstart "gui/$(id -u)/$LABEL"
    echo "Started; follow it with: tail -f $LOG"
    ;;
  *)
    echo "Usage: $0 install|uninstall|status|run" >&2
    exit 1
    ;;
esac
