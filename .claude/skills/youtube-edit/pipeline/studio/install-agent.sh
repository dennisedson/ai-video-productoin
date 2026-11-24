#!/bin/bash
# install-agent.sh: a launchd agent that keeps the studio (server.py) running on 127.0.0.1:${STUDIO_PORT:-4040}.
# install.sh runs it; run it alone to (re)load the studio. --remove unloads it.
. "$(cd "$(dirname "$0")/.." && pwd)/lib.sh"
LABEL="com.youtube-edit.studio"; PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
if [ "${1:-}" = --remove ]; then rm -f "$PLIST"; echo "studio agent removed"; exit 0; fi
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/videos"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>-c</string><string>. "$PIPE/lib.sh"; exec python3 "$PIPE/studio/server.py" --port ${STUDIO_PORT:-4040}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$ROOT/videos/.studio.log</string>
  <key>StandardErrorPath</key><string>$ROOT/videos/.studio.log</string>
</dict></plist>
PL
launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "studio running: http://127.0.0.1:${STUDIO_PORT:-4040} (launchd agent $LABEL)"
