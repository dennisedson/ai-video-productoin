#!/bin/bash
# install.sh: one-time setup of the hands-off pipeline on the Mac. Safe to run again.
#   bash .claude/skills/youtube-edit/pipeline/install.sh [--budget 20] [--model NAME]
# Writes pipeline/config.sh, creates videos/_inbox/, and loads a launchd agent that runs inbox.sh when the inbox changes
# (and every 2 minutes). Nothing here needs admin rights.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
BUDGET=20; MOD=""
while [ $# -gt 0 ]; do case "$1" in --budget) BUDGET="$2"; shift ;; --model) MOD="$2"; shift ;; esac; shift; done
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
dirs=""; for c in python3 ffmpeg node auto-editor "$CLAUDE"; do d="$(dirname "$(command -v "$c" || echo "$c")")"; case ":$dirs:" in *":$d:"*) ;; *) dirs="${dirs:+$dirs:}$d" ;; esac; done
cat > "$PIPE/config.sh" <<CFG
# written by install.sh on $(date '+%Y-%m-%d %H:%M'); launchd starts with a bare PATH, so the tools' folders are listed here
CLAUDE_BIN="$CLAUDE"
EXTRA_PATH="$dirs:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
BUDGET_USD="$BUDGET"   # cap per Claude stage (claude -p --max-budget-usd)
MODEL="$MOD"           # empty = Claude Code's default model
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
  <key>StandardOutPath</key><string>$INBOX/launchd.log</string>
  <key>StandardErrorPath</key><string>$INBOX/launchd.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "launchd agent loaded: $LABEL"
command -v terminal-notifier >/dev/null || echo "tip: 'brew install terminal-notifier' makes a notification click open the review page"
ln -sf "$PIPE/yt" "$HOME/.local/bin/yt" 2>/dev/null || { mkdir -p "$HOME/.local/bin" && ln -sf "$PIPE/yt" "$HOME/.local/bin/yt"; }
notify "YouTube edit pipeline" "Installed. Drop recordings into videos/_inbox/<name>/ to start an edit."
echo "inbox:  $INBOX"
echo "status: yt status   (yt is linked into ~/.local/bin; add it to your PATH if 'yt' is not found)"
echo "Test the unattended Claude step once: yt run <an existing video> cut   (then: yt log <name>)"
