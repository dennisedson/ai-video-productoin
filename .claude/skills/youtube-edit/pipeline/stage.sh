#!/bin/bash
# stage.sh NAME cut|storyboard|render: one stage of the hands-off pipeline for videos/NAME.
#   cut        mechanical prep (no AI), then headless Claude finishes Checkpoint A  -> awaiting-A, notification
#   storyboard headless Claude builds Checkpoint B, a 1080p preview render and render.json -> awaiting-B, notification
#   render     render-mac.sh (no AI) -> done, notification; on the home Mac when RENDER_HOST_DIR is set (asks first
#              when the home Mac isn't mounted or ready: Check again / Render on this Mac / Later -> awaiting-host);
#              RENDER_HOST_DIR=handoff makes a bundle zip to carry over by hand -> awaiting-import (yt import)
# Approvals come from Dennis in a Claude Code thread (see the project's CLAUDE.md), which starts the next stage with `yt run`.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
NAME="${1:?usage: stage.sh NAME cut|storyboard|render [--here|--fast]}"; STAGE="${2:?stage}"; OPT="${3:-}"
# PRIORITY=background (install.sh --priority background, for the work Mac): cut and storyboard run at macOS background
# priority (taskpolicy -b: the efficiency cores, throttled disk), so the fans stay down and the stages take longer.
# The render keeps normal priority (on the work Mac it is sent to the home Mac anyway).
if [ "${PRIORITY:-normal}" = background ] && [ "$STAGE" != render ] && [ "$OPT" != --fast ] && [ -z "${YT_BACKGROUND:-}" ] \
   && command -v taskpolicy >/dev/null 2>&1; then
  export YT_BACKGROUND=1
  exec taskpolicy -b /bin/bash "$0" "$@"
fi
W="videos/$NAME"; cd "$ROOT" || exit 1
mkdir -p "$W/pipeline"
fail() { state_set "$NAME" failed "$STAGE: $1"; notify "YouTube edit: $NAME" "Stopped in $STAGE: $1" "$ROOT/$W/pipeline/stage.log"; exit 1; }
run() { echo "== $(date '+%H:%M:%S') $*"; "$@" || fail "$(basename "$1") $2 failed (see pipeline/stage.log)"; }
echo "==== $(date '+%Y-%m-%d %H:%M:%S') $STAGE"   # where this run starts in stage.log (progress.py reads it)
pf="$(preflight)"; [ -z "$pf" ] || { echo "== preflight: $pf"; fail "setup: $pf"; }

claude_stage() {   # claude_stage PROMPT_FILE: headless Claude Code from the project root, so CLAUDE.md and the skill load
  local prompt; prompt="$(sed -e "s#{NAME}#$NAME#g" -e "s#{W}#$W#g" "$PIPE/prompts/$1")"
  echo "== $(date '+%H:%M:%S') claude -p ($1, budget \$$BUDGET_USD)"
  "$CLAUDE_BIN" -p "$prompt" --permission-mode auto --permission-prompts none --output-format json \
    --max-budget-usd "$BUDGET_USD" ${MODEL:+--model "$MODEL"} > "$W/pipeline/claude-$STAGE.json" 2>> "$W/pipeline/stage.log"
  local rc=$?
  python3 -c 'import json,sys
try:
    j=json.load(open(sys.argv[1])); print("claude: %s, cost $%.2f, %s turns" % ("error" if j.get("is_error") else "ok", j.get("total_cost_usd") or 0, j.get("num_turns")))
    print((j.get("result") or "")[-1500:])
except Exception as e: print("claude: no JSON result (%s)" % e)' "$W/pipeline/claude-$STAGE.json"
  [ $rc -eq 0 ] || fail "Claude stopped (exit $rc)"
}
ask_host() {   # ask_host WHY: a dialog on this Mac; prints again|here|later (later when nobody answers within 4 h)
  command -v osascript >/dev/null 2>&1 || { echo later; return; }
  local why="${1//\"/\'}" r
  r="$(osascript -e "display dialog \"$NAME is ready to render on the home Mac, but $why.

Fix that (mount the share, or wake the home Mac), then choose Check again.\" with title \"YouTube edit\" buttons {\"Later\", \"Render on this Mac\", \"Check again\"} default button \"Check again\" giving up after 14400" 2>/dev/null)" || { echo later; return; }
  case "$r" in *"gave up:true"*) echo later ;; *"Check again"*) echo again ;; *"this Mac"*) echo here ;; *) echo later ;; esac
}
need() { for f in "$@"; do [ -e "$W/$f" ] || fail "missing $f after the $STAGE stage"; done; }

case "$STAGE" in
cut)
  state_set "$NAME" cutting
  FACE="$(ls "$W"/raw/talking-head.* 2>/dev/null | head -1)"; [ -n "$FACE" ] || fail "no raw/talking-head.*"
  SCREEN="$(ls "$W"/raw/screenshare-vfr.* 2>/dev/null | head -1)"
  if [ -n "$SCREEN" ]; then
    run ffmpeg -y -v error -i "$SCREEN" -vf fps=30 -an -c:v libx264 -preset veryfast -crf 16 -g 30 -keyint_min 30 -pix_fmt yuv420p \
        -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart "$W/raw/screenshare.mp4"
  fi
  run ffmpeg -y -v error -i "$FACE" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$W/audio-raw.wav"
  run npx --yes hyperframes transcribe "$W/audio-raw.wav" -d "$W" --engine parakeet --json
  mv "$W/transcript.json" "$W/transcript-raw.json"
  run auto-editor "$FACE" --edit audio:-30dB --margin 0.12s,0.35s --export v1 -o "$W/speech.v1"
  DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FACE")"
  run python3 "$SK/scripts/paper-cut.py" --transcript "$W/transcript-raw.json" --duration "$DUR" --out-dir "$W" --speech "$W/speech.v1"
  cp "$W/PAPER-CUT.md" "$W/work/PAPER-CUT.paper-pass.md"
  run python3 "$SK/scripts/camera-check.py" --video "$FACE" --sheet "$W/snaps/grade-options.png" > "$W/work/camera-check.txt"; cat "$W/work/camera-check.txt"
  if [ -n "$SCREEN" ]; then
    run python3 "$SK/scripts/screen-activity.py" --video "$W/raw/screenshare.mp4" --out "$W/activity.json" --fps 4 --width 344
    run python3 "$SK/scripts/screen-windows.py" --video "$W/raw/screenshare.mp4" --sheet "$W/snaps/screen-windows.png" > "$W/work/screen-windows.txt"; cat "$W/work/screen-windows.txt"
  fi
  claude_stage checkpoint-a.md
  need PAPER-CUT.md review/cut-review.mp4 cut-list.json
  python3 "$PIPE/review-page.py" "$ROOT/$W" A
  state_set "$NAME" awaiting-A
  notify "YouTube edit: $NAME" "Checkpoint A (the cut) is ready to review." "$ROOT/$W/REVIEW-A.html"
  ;;
storyboard)
  state_set "$NAME" storyboarding
  claude_stage checkpoint-b.md
  need storyboard.json snaps/sheet.png render.json review/preview.mp4
  python3 "$PIPE/review-page.py" "$ROOT/$W" B
  state_set "$NAME" awaiting-B
  notify "YouTube edit: $NAME" "Checkpoint B (storyboard + preview) is ready to review." "$ROOT/$W/REVIEW-B.html"
  ;;
render)
  # With RENDER_HOST_DIR set (the work Mac: the home Mac's Video folder, mounted or user@host:/path over SSH), the render
# runs on the home Mac.
  # When the home Mac isn't ready, ask: never fall back to rendering here on its own. `yt run NAME render --here` skips it.
  # RENDER_HOST_DIR=handoff: make the bundle zip on the Desktop for you to carry over (Screen Sharing), -> awaiting-import.
  WHERE=here; [ -n "${RENDER_HOST_DIR:-}" ] && [ "$OPT" != --here ] && WHERE=home
  if [ "$WHERE" = home ] && [ "$RENDER_HOST_DIR" = handoff ]; then
    python3 "$PIPE/remote-render.py" --project "$W" --zip "${HANDOFF_DIR:-$HOME/Desktop}" | tee "$W/pipeline/bundle.out"
    [ "${PIPESTATUS[0]}" -eq 0 ] || fail "making the hand-off bundle failed (see pipeline/stage.log)"
    ZIP="$(awk -F'\t' '$1=="BUNDLE"{print $2}' "$W/pipeline/bundle.out")"
    state_set "$NAME" awaiting-import "bundle: $ZIP"
    notify "YouTube edit: $NAME" "Bundle ready: drag $(basename "$ZIP") into the home Mac's videos/_render-inbox. Then: yt import $NAME <video>." "$ZIP"
    exit 0
  fi
  while [ "$WHERE" = home ]; do
    why="$(python3 "$PIPE/remote-render.py" --check --host "$RENDER_HOST_DIR")" && break
    echo "== $(date '+%H:%M:%S') home Mac not ready: $why"
    case "$(ask_host "$why")" in
      again) ;;
      here) WHERE=here ;;
      *) state_set "$NAME" awaiting-host "$why"
         notify "YouTube edit: $NAME" "Ready to render on the home Mac, but $why. Then: yt run $NAME render (--here renders on this Mac)."
         exit 0 ;;
    esac
  done
  if [ "$WHERE" = home ]; then
    state_set "$NAME" rendering "on the home Mac"
    python3 "$PIPE/remote-render.py" --project "$W" --host "$RENDER_HOST_DIR" | tee "$W/pipeline/remote-render.out"
    rc=${PIPESTATUS[0]}
    if [ "$rc" -eq 3 ]; then
      state_set "$NAME" awaiting-host "the home Mac went away before the bundle was sent"
      notify "YouTube edit: $NAME" "The home Mac went away before the render was sent. When it is back: yt run $NAME render (--here renders on this Mac)."
      exit 0
    fi
    [ "$rc" -eq 0 ] || fail "the render on the home Mac failed (see $W/render-remote.log)"
    OUT="$(awk -F'\t' '$1=="DELIVERED"{print $2}' "$W/pipeline/remote-render.out")"
    state_set "$NAME" done "rendered on the home Mac"
  else
    state_set "$NAME" rendering "on this Mac"
    bash "$SK/scripts/render-mac.sh" "$W" || fail "render-mac.sh failed (see $W/render.log; resume with --from)"
    OUT="$(python3 -c 'import json,sys,os; c=json.load(open(sys.argv[1])); print(os.path.expanduser(c.get("deliver","~/Movies/YouTube Renders/"+c.get("name",""))))' "$W/render.json")"
    state_set "$NAME" done
  fi
  notify "YouTube edit: $NAME" "Rendered and checked. Delivered to $OUT." "$OUT"
  ;;
*) echo "unknown stage $STAGE"; exit 2 ;;
esac
