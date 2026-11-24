#!/bin/bash
# render-host-job.sh NAME: render one bundle the work Mac sent, on the home Mac. Started by render-host.sh.
# Runs render-mac.sh on videos/_render-inbox/NAME with the delivery redirected into its out/ folder, and keeps
# status.json current ({"stage": rendering|awaiting-music|done|failed, "step", "error", "at"}) for the work Mac to read.
# With the music pass on (the profile's music.json) it says to pick music while the render runs; the job stops as
# awaiting-music at the end if nothing is picked yet, and "yt music NAME N|none" resumes it (--from music).
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
n="${1:?usage: render-host-job.sh NAME [--from STEP]}"; FROMARG=("${@:2}")
J="videos/_render-inbox/$n"; cd "$ROOT" || exit 1
L="$ROOT/videos/_render-inbox/.lock"; [ ${#FROMARG[@]} -gt 0 ] || trap 'rm -rf "$L"' EXIT   # a resumed music step holds no lock

status() {   # status STAGE [STEP] [ERROR]
  python3 - "$J/status.json" "$@" <<'PY'
import json, os, sys, time
p, stage = sys.argv[1], sys.argv[2]
s = {"stage": stage, "step": sys.argv[3] if len(sys.argv) > 3 else "", "at": time.strftime("%Y-%m-%d %H:%M:%S")}
if len(sys.argv) > 4: s["error"] = sys.argv[4]
json.dump(s, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
PY
}

status rendering "${FROMARG[1]:+resuming at }${FROMARG[1]:-starting}"
FROM="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("from","the work Mac"))' "$J/job.json" 2>/dev/null)"
VIA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("via",""))' "$J/job.json" 2>/dev/null)"
[ ${#FROMARG[@]} -gt 0 ] || python3 - "$J/render.json" "$ROOT/$J/out" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p)); c["deliver"] = sys.argv[2]
json.dump(c, open(p, "w"), indent=1)
PY
log "render host: $n from $FROM"
[ ${#FROMARG[@]} -gt 0 ] || notify "Render host" "Rendering $n for $FROM."

told=0
MUSIC_PASS="${MUSIC_PASS:-on}" bash "$SK/scripts/render-mac.sh" "$J" "${FROMARG[@]}" 2>&1 | while IFS= read -r line; do
  echo "$line"
  case "$line" in "== "*) status rendering "${line#== }" ;; esac
  case "$line" in "== render:"*)
    if [ "$told" = 0 ] && [ "$(python3 "$SK/scripts/music.py" status --project "$J" 2>/dev/null)" = pending ]; then
      told=1
      notify "Music for $n" "Rendering now. Pick the music meanwhile: in a Claude thread on this Mac, \"music for $n\"."
    fi ;;
  esac
done
rc=${PIPESTATUS[0]}
if [ "$rc" -eq 10 ]; then
  status awaiting-music "rendered; waiting for a music pick"
  log "render host: $n waiting for music"
  page="$ROOT/$J/MUSIC-REVIEW.html"; [ -f "$page" ] || page=""
  notify "Music for $n" "Rendered. It waits for the music: $( [ -n "$page" ] && echo 'pick from MUSIC-REVIEW.html (\"music N for '"$n"'\")' || echo 'ask a Claude thread on this Mac: \"music for '"$n"'\"'), or \"no music for $n\"." $page
  exit 0
fi

if [ "$rc" -eq 0 ] && ls "$J"/out/*.mp4 >/dev/null 2>&1; then
  status done "delivered to out/"
  log "render host: $n done"
  if [ "$VIA" = handoff ]; then
    mv_="$(ls "$J"/out/*-music.mp4 2>/dev/null | head -1)"
    notify "Render host" "Rendered $n. Drag $( [ -n "$mv_" ] && echo "$(basename "$mv_") (with music)" || echo "the video") in videos/_render-inbox/$n/out/ back to the work Mac, then: yt import $n <video>." "$ROOT/$J/out"
  else
    notify "Render host" "Rendered $n; the work Mac is copying it back."
  fi
else
  err="$(grep -m1 '^!! ' "$J/render-host.log" 2>/dev/null | sed 's/^!! //')"
  status failed "" "${err:-render-mac.sh exited $rc}"
  log "render host: $n failed ($rc)"
  notify "Render host" "Rendering $n failed: ${err:-exit $rc}" "$ROOT/$J/render.log"
fi
