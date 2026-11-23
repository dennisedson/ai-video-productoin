# lib.sh: shared by the pipeline scripts (sourced, not run). Paths, config, state, log, notifications.
PIPE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SK="$(cd "$PIPE/.." && pwd)"                 # .claude/skills/youtube-edit
ROOT="$(cd "$SK/../../.." && pwd)"           # the project folder (…/Video)
INBOX="$ROOT/videos/_inbox"
[ -f "$PIPE/config.sh" ] && . "$PIPE/config.sh"     # written by install.sh: CLAUDE_BIN, EXTRA_PATH, BUDGET_USD, MODEL, RENDER_HOST_DIR, PRIORITY
: "${CLAUDE_BIN:=claude}"; : "${BUDGET_USD:=20}"; : "${MODEL:=}"
: "${RENDER_HOST_DIR:=}"    # the work Mac: the home Mac's Video folder, mounted path or user@host:/path (empty = here)
: "${PRIORITY:=normal}"    # background = cut and storyboard on the efficiency cores (quieter, slower)
[ -n "${EXTRA_PATH:-}" ] && export PATH="$EXTRA_PATH:$PATH"

log() { mkdir -p "$INBOX"; echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$INBOX/pipeline.log"; }

# state.json in the video folder: {"stage": "...", "history": [{"stage", "at", "note"}]}
state_get() { python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("stage",""))
except Exception: print("")' "$ROOT/videos/$1/state.json"; }
state_set() { python3 -c 'import json,sys,time,os
p=sys.argv[1]; s=json.load(open(p)) if os.path.exists(p) else {"history": []}
s["stage"]=sys.argv[2]; s["history"].append({"stage": sys.argv[2], "at": time.strftime("%Y-%m-%d %H:%M:%S"), "note": sys.argv[3]})
json.dump(s, open(p, "w"), indent=1)' "$ROOT/videos/$1/state.json" "$2" "${3:-}"; log "$1 -> $2 ${3:-}"; }

# preflight: prints what the pipeline's own python3 and ffmpeg (the ones on EXTRA_PATH, not the terminal's) lack; empty = ready
preflight() {
  python3 -c "import numpy" 2>/dev/null || echo "$(command -v python3) has no numpy: '$(command -v python3)' -m pip install numpy, or rerun install.sh;"
  ffmpeg -hide_banner -filters 2>/dev/null | grep -q drawtext \
    || echo "ffmpeg ($(command -v ffmpeg || echo 'not found')) has no drawtext: brew install ffmpeg-full && brew unlink ffmpeg; brew link --force ffmpeg-full;"
}

# notify TITLE MESSAGE [FILE TO OPEN ON CLICK]; terminal-notifier makes the click open the file, osascript cannot
notify() {
  if command -v terminal-notifier >/dev/null 2>&1; then
    terminal-notifier -title "$1" -message "$2" ${3:+-open "file://$3"} -group "youtube-edit" -sound default >/dev/null 2>&1 && return
  fi
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${2//\"/\'}\" with title \"${1//\"/\'}\" sound name \"default\"" >/dev/null 2>&1 && return
  fi
  echo "NOTIFY: $1 - $2 ${3:-}"
}
