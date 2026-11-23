#!/bin/bash
# install.sh: one-time setup of the hands-off pipeline on the Mac. Safe to run again.
#   bash .claude/skills/youtube-edit/pipeline/install.sh [--budget 20] [--model NAME] [--render-host DIR|none] [--serve-renders] [--priority background|normal]
# Writes pipeline/config.sh, creates videos/_inbox/, and loads a launchd agent that runs inbox.sh when the inbox changes
# (and every 2 minutes). Nothing here needs admin rights.
#   --render-host DIR  (the work Mac) render on the home Mac: DIR is its Video folder, either mounted here as a share
#                      (/Volumes/Video) or over SSH (user@host:/Users/you/AI/claude-cowork/Video, with a key set up).
#                      Or "handoff": approving B makes a bundle zip on the Desktop to carry over by hand (Screen
#                      Sharing) into the home Mac's videos/_render-inbox; yt import brings the video back.
#                      Kept on later runs; --render-host none goes back to rendering here.
#   --serve-renders    (the home Mac) also load the render agent that renders bundles the work Mac sends (render-host.sh).
#   --priority background  (the work Mac) run the cut and storyboard stages at background priority: quieter fans,
#                      slower stages. Kept on later runs; --priority normal goes back.
USER_PY="$(command -v python3 || true)"
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
BUDGET=20; MOD=""; RHOST="${RENDER_HOST_DIR:-}"; SERVE=0; PRIO="${PRIORITY:-normal}"
while [ $# -gt 0 ]; do case "$1" in
  --budget) BUDGET="$2"; shift ;; --model) MOD="$2"; shift ;;
  --render-host) RHOST="$2"; [ "$RHOST" = none ] && RHOST=""; shift ;; --serve-renders) SERVE=1 ;;
  --priority) PRIO="$2"; shift; case "$PRIO" in background|normal) ;; *) echo "--priority background|normal"; exit 2 ;; esac ;;
  *) echo "unknown option $1"; exit 2 ;;
esac; shift; done
[ "$(uname)" = Darwin ] || { echo "install.sh sets up launchd on the Mac; run it there."; exit 1; }
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.claude/local:$PATH"
miss=""
for c in python3 ffmpeg ffprobe node npx auto-editor; do command -v "$c" >/dev/null || miss="$miss $c"; done
[ -z "$miss" ] || { echo "missing:$miss (run the skill's setup check in Claude Code first)"; exit 1; }
CLAUDE="$(command -v claude || true)"
if [ -z "$CLAUDE" ]; then
  echo "The Claude Code command line ('claude') is not on your PATH. Install it (see https://code.claude.com/docs),"
  echo "run 'claude' once to sign in, then run this script again."; exit 1
fi
# the scripts need numpy: use the first python3 that has it (the terminal's own first), its folder first on EXTRA_PATH
PY=""; for p in "$USER_PY" $(which -a python3); do
  [ -n "$p" ] && "$p" -c "import numpy" 2>/dev/null && { PY="$("$p" -c 'import sys; print(sys.executable)')"; break; }
done
[ -n "$PY" ] || { echo "no python3 with numpy: python3 -m pip install numpy (or brew install numpy), then run this again"; exit 1; }
dirs=""; for c in "$PY" ffmpeg node auto-editor "$CLAUDE"; do d="$(dirname "$(command -v "$c" || echo "$c")")"; case ":$dirs:" in *":$d:"*) ;; *) dirs="${dirs:+$dirs:}$d" ;; esac; done
pf="$(PATH="$dirs:$PATH" preflight)"; [ -z "$pf" ] || { echo "not ready: $pf"; exit 1; }
cat > "$PIPE/config.sh" <<CFG
# written by install.sh on $(date '+%Y-%m-%d %H:%M'); launchd starts with a bare PATH, so the tools' folders are listed here
CLAUDE_BIN="$CLAUDE"
EXTRA_PATH="$dirs:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
BUDGET_USD="$BUDGET"   # cap per Claude stage (claude -p --max-budget-usd)
MODEL="$MOD"           # empty = Claude Code's default model
RENDER_HOST_DIR="$RHOST"   # the home Mac's Video folder as mounted here; empty = render on this Mac
PRIORITY="$PRIO"           # background = cut and storyboard on the efficiency cores (quieter, slower)
CFG
mkdir -p "$INBOX"
LABEL="com.youtube-edit.inbox"; PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"; mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$PIPE/inbox.sh</string></array>
  <key>WatchPaths</key><array><string>$INBOX</string></array>
  <key>StartInterval</key><integer>120</integer>
  <key>AbandonProcessGroup</key><true/>
  <key>StandardOutPath</key><string>$INBOX/launchd.log</string>
  <key>StandardErrorPath</key><string>$INBOX/launchd.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "launchd agent loaded: $LABEL"
if [ "$SERVE" = 1 ]; then          # the home Mac: render what the work Mac sends
  HIN="$ROOT/videos/_render-inbox"; mkdir -p "$HIN"
  RLABEL="com.youtube-edit.render-host"; RPLIST="$HOME/Library/LaunchAgents/$RLABEL.plist"
  cat > "$RPLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$RLABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$PIPE/render-host.sh</string></array>
  <key>WatchPaths</key><array><string>$HIN</string></array>
  <key>StartInterval</key><integer>60</integer>
  <key>AbandonProcessGroup</key><true/>
  <key>StandardOutPath</key><string>$HIN/launchd.log</string>
  <key>StandardErrorPath</key><string>$HIN/launchd.log</string>
</dict></plist>
PL
  launchctl bootout "gui/$(id -u)/$RLABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$RPLIST" && echo "render agent loaded: $RLABEL (watching $HIN)"
  echo "The work Mac reaches this folder by File Sharing (mount it there) or, when that is blocked, by Remote Login (SSH)."
  echo "Both are in System Settings > General > Sharing."
fi
[ "$PRIO" = background ] && echo "cut and storyboard run at background priority (quieter, slower)"
if [ "$RHOST" = handoff ]; then echo "renders are handed off: approving B makes a bundle zip on the Desktop; yt import NAME VIDEO brings it back"
elif [ -n "$RHOST" ]; then echo "renders go to the home Mac at $RHOST (asks first when it can't be reached; check with: yt host)"; fi
command -v terminal-notifier >/dev/null || echo "tip: 'brew install terminal-notifier' makes a notification click open the review page"
ln -sf "$PIPE/yt" "$HOME/.local/bin/yt" 2>/dev/null || { mkdir -p "$HOME/.local/bin" && ln -sf "$PIPE/yt" "$HOME/.local/bin/yt"; }
notify "YouTube edit pipeline" "Installed. Drop recordings into videos/_inbox/<name>/ to start an edit."
echo "inbox:  $INBOX"
echo "status: yt status   (yt is linked into ~/.local/bin; add it to your PATH if 'yt' is not found)"
echo "Test the unattended Claude step once: yt run <an existing video> cut   (then: yt log <name>)"
