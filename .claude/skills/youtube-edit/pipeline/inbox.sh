#!/bin/bash
# inbox.sh: launchd runs this when videos/_inbox changes (and every 5 minutes as a backstop).
# Drop a folder videos/_inbox/<name>/ holding the camera file (with the mic) and, for a tutorial, the screen file
# (no audio), plus an optional notes.txt ("HubSpot profile", "only the first 90 seconds", anything else).
# A folder whose size has not changed for 20 s is claimed: its files move to videos/<name>/raw/ and the cut stage starts.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
mkdir -p "$INBOX"
mkdir "$INBOX/.lock" 2>/dev/null || exit 0          # one run at a time
trap 'rmdir "$INBOX/.lock" 2>/dev/null' EXIT
size() { du -sk "$1" 2>/dev/null | cut -f1; }
for d in "$INBOX"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  case "$name" in .*|_*) continue ;; esac
  [ -e "$d/.claimed" ] && continue
  ls "$d" | grep -qiE '\.(mp4|mov|m4v)$' || continue
  s1=$(size "$d"); sleep 20; s2=$(size "$d")
  if [ "$s1" != "$s2" ]; then log "$name: still copying"; continue; fi
  slug="$(echo "$name" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9._-')"
  if [ -e "$ROOT/videos/$slug" ]; then
    notify "YouTube edit: $name" "videos/$slug already exists. Rename the inbox folder to start a new edit."
    touch "$d/.claimed"; log "$name: videos/$slug exists, skipped"; continue
  fi
  # which file is which: the one with an audio stream (the largest, if several) is the camera; one without is the screen
  roles="$(python3 - "$d" <<'PY'
import json, os, subprocess, sys
d = sys.argv[1]; face, screens = [], []
for f in sorted(os.listdir(d)):
    if not f.lower().endswith((".mp4", ".mov", ".m4v")): continue
    p = os.path.join(d, f)
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", p], capture_output=True, text=True).stdout or "{}")
    kinds = [s.get("codec_type") for s in j.get("streams", [])]
    (face if "audio" in kinds else screens).append((os.path.getsize(p), f))
if not face: print("ERROR no file with audio (the camera file carries the mic)"); sys.exit()
face.sort(reverse=True)
print("FACE\t" + face[0][1])
for _, f in face[1:] + screens: print(("SCREEN\t" if (_, f) in screens else "EXTRA\t") + f)
PY
)"
  if echo "$roles" | grep -q '^ERROR'; then
    notify "YouTube edit: $name" "$(echo "$roles" | sed 's/^ERROR //')"; touch "$d/.claimed"; log "$name: $roles"; continue
  fi
  W="$ROOT/videos/$slug"; mkdir -p "$W/raw" "$W/work" "$W/snaps" "$W/public" "$W/review" "$W/pipeline"
  face="$(echo "$roles" | awk -F'\t' '$1=="FACE"{print $2}')"
  mv "$d/$face" "$W/raw/talking-head.$(echo "${face##*.}" | tr '[:upper:]' '[:lower:]')"
  screen="$(echo "$roles" | awk -F'\t' '$1=="SCREEN"{print $2; exit}')"
  [ -n "$screen" ] && mv "$d/$screen" "$W/raw/screenshare-vfr.$(echo "${screen##*.}" | tr '[:upper:]' '[:lower:]')"
  for f in "$d"*; do [ -f "$f" ] && mv "$f" "$W/raw/"; done            # notes.txt and anything else
  [ -f "$W/raw/notes.txt" ] && mv "$W/raw/notes.txt" "$W/notes.txt"
  touch "$d/.claimed"; rmdir "$d" 2>/dev/null || true
  state_set "$slug" queued "from the inbox: camera $face${screen:+, screen $screen}"
  notify "YouTube edit: $slug" "Started: cutting $( [ -n "$screen" ] && echo 'a two-file tutorial' || echo 'a camera file')."
  nohup bash "$PIPE/stage.sh" "$slug" cut >> "$W/pipeline/stage.log" 2>&1 &
done
