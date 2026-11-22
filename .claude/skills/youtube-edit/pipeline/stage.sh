#!/bin/bash
# stage.sh NAME cut|storyboard|render: one stage of the hands-off pipeline for videos/NAME.
#   cut        mechanical prep (no AI), then headless Claude finishes Checkpoint A  -> awaiting-A, notification
#   storyboard headless Claude builds Checkpoint B, a 1080p preview render and render.json -> awaiting-B, notification
#   render     render-mac.sh (no AI) -> done, notification
# Approvals come from Dennis in a Claude Code thread (see the project's CLAUDE.md), which starts the next stage with `yt run`.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
NAME="${1:?usage: stage.sh NAME cut|storyboard|render}"; STAGE="${2:?stage}"
W="videos/$NAME"; cd "$ROOT" || exit 1
mkdir -p "$W/pipeline"
fail() { state_set "$NAME" failed "$STAGE: $1"; notify "YouTube edit: $NAME" "Stopped in $STAGE: $1" "$ROOT/$W/pipeline/stage.log"; exit 1; }
run() { echo "== $(date '+%H:%M:%S') $*"; "$@" || fail "$(basename "$1") $2 failed (see pipeline/stage.log)"; }

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
  state_set "$NAME" rendering
  bash "$SK/scripts/render-mac.sh" "$W" || fail "render-mac.sh failed (see $W/render.log; resume with --from)"
  state_set "$NAME" done
  OUT="$(python3 -c 'import json,sys,os; c=json.load(open(sys.argv[1])); print(os.path.expanduser(c.get("deliver","~/Movies/YouTube Renders/"+c.get("name",""))))' "$W/render.json")"
  notify "YouTube edit: $NAME" "Rendered and checked. Delivered to $OUT." "$OUT"
  ;;
*) echo "unknown stage $STAGE"; exit 2 ;;
esac
