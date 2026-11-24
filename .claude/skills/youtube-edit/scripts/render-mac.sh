#!/bin/bash
# render-mac.sh: everything after Checkpoint B, on the Mac, with no AI in the loop.
#
#   bash .claude/skills/youtube-edit/scripts/render-mac.sh videos/<project> [--dry-run] [--from STEP] [--keep-cache]
#
# Reads videos/<project>/render.json (written at Checkpoint B):
#   {"name": "agents-2", "shared": "shared",
#    "face_raw": "raw/talking-head.mp4", "grade": "blacks",          # rebuild the 4K flat cut (skipped when absent)
#    "face_crop": "1110:1936:1505:0",                                  # tutorial layout: the face card's region (optional)
#    "workers": 1, "bitrate": "45M", "min_mbps": 40,                   # min_mbps 15 for screen-heavy videos (still screens undershoot)
#    "card": "48,48,1232,2112", "face_windows": "0-34.9,64.4-78.4,228-",   # tutorial layout: blank face-card check (optional)
#    "bookends": {"intro": {"at": 7.5, "resume": 7.6, "eyebrow": "...", "title": "..."}, "outro": {"next": "..."}},   # optional
#    "deliver": "~/Movies/YouTube Renders/agents"}
# Steps (resume any with --from): flatcut facecrop compose check render tags loudness verify card bookends music deliver
# music: the bed picked from the music pass (music.py), mixed onto the finished video, the no-music twin kept;
# with the pass on and nothing picked yet it stops with exit 10 (awaiting music): resume with --from music.
# With "bookends" (a profile with intro/outro templates), the delivered file is <name>-full-4k.mp4: the sting cut in,
# the end card on the end (bookends.py); verify and card run on the main video before that.
# Stops at the first failure; every step's output and timing goes to videos/<project>/render.log.
set -u -o pipefail

W="${1:?usage: render-mac.sh videos/<project> [--dry-run] [--from STEP] [--keep-cache]}"; shift
DRY=0; FROM=""; KEEP_CACHE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --from) FROM="$2"; shift ;;
    --keep-cache) KEEP_CACHE=1 ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
SK="$(cd "$(dirname "$0")/.." && pwd)"
W="${W%/}"
[ -f "$W/render.json" ] || { echo "no $W/render.json (it is written at Checkpoint B)"; exit 2; }
[ -f "$W/storyboard.json" ] || { echo "no $W/storyboard.json"; exit 2; }
cfg() { python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2], sys.argv[3]); print("" if v is None else v)' "$W/render.json" "$1" "${2:-}"; }
NAME="$(cfg name "$(basename "$W")")"; SHARED="$(cfg shared shared)"
FACE_RAW="$(cfg face_raw)"; GRADE="$(cfg grade none)"; FACE_CROP="$(cfg face_crop)"
WORKERS="$(cfg workers 1)"; BITRATE="$(cfg bitrate 45M)"; MIN_MBPS="$(cfg min_mbps 40)"
CARD="$(cfg card)"; WINDOWS="$(cfg face_windows)"; DELIVER="$(cfg deliver "$HOME/Movies/YouTube Renders/$NAME")"
DELIVER="${DELIVER/#\~/$HOME}"
LOG="$W/render.log"
STEPS="flatcut facecrop compose check render tags loudness verify card bookends music deliver"
if [ -n "$FROM" ]; then
  case " $STEPS " in *" $FROM "*) ;; *) echo "--from must be one of: $STEPS"; exit 2 ;; esac
fi

for c in python3 ffmpeg ffprobe npx; do command -v "$c" >/dev/null || { echo "missing: $c (see the skill's setup check)"; exit 2; }; done

started=0; [ -z "$FROM" ] && started=1
T0=$(date +%s)
step() {   # step NAME DESCRIPTION -- command...
  local name="$1" desc="$2"; shift 3
  [ "$started" = 0 ] && [ "$name" = "$FROM" ] && started=1
  if [ "$started" = 0 ]; then echo "-- skip $name"; return 0; fi
  echo "== $name: $desc"
  if [ "$DRY" = 1 ]; then printf '   %q' "$@"; echo; return 0; fi
  local t=$(date +%s)
  { echo "== $name $(date '+%H:%M:%S')"; "$@"; } >>"$LOG" 2>&1
  local rc=$?
  tail -n 3 "$LOG" | sed 's/^/   /'
  echo "   ($(( $(date +%s) - t )) s)"
  if [ $rc -ne 0 ]; then echo "!! $name failed (exit $rc). Full output: $LOG. Fix it, then: render-mac.sh $W --from $name"; exit $rc; fi
}
echo "render $NAME  (log: $LOG)"; [ "$DRY" = 1 ] || echo "---- $(date) ----" >>"$LOG"

if [ -n "$FACE_RAW" ]; then
  step flatcut "4K flat cut from cut-list.json, grade: $GRADE" -- \
    python3 "$SK/scripts/apply-cut.py" --input "$W/$FACE_RAW" --cut-list "$W/cut-list.json" --out "$W/public/input-video.mp4" --grade "$GRADE"
else
  [ "$started" = 0 ] && [ "$FROM" = flatcut ] && started=1; echo "-- flatcut: no face_raw in render.json, using public/input-video.mp4 as it is"
fi
if [ -n "$FACE_CROP" ]; then
  step facecrop "the face card's 4K crop ($FACE_CROP)" -- \
    ffmpeg -y -v error -i "$W/public/input-video.mp4" -vf "crop=$FACE_CROP" -c:v libx264 -preset fast -crf 16 -g 30 -keyint_min 30 \
      -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -c:a copy -movflags +faststart "$W/public/face-crop.mp4"
else
  [ "$started" = 0 ] && [ "$FROM" = facecrop ] && started=1
fi
step compose "compose.py (storyboard -> public/index.html)" -- \
  python3 "$SK/scripts/compose.py" --spec "$W/storyboard.json" --out "$W/public" --shared "$SHARED"
step check "hyperframes check" -- npx hyperframes check "$W/public"
step render "4K render, $WORKERS worker(s), $BITRATE" -- \
  env PRODUCER_BROWSER_GPU_MODE=hardware NODE_OPTIONS=--max-old-space-size=8192 \
  npx hyperframes render "$W/public" --resolution 4k --video-bitrate "$BITRATE" --gpu --workers "$WORKERS" -o "$W/output-4k-raw.mp4"
step tags "BT.709 tags (lossless remux)" -- \
  ffmpeg -y -v error -i "$W/output-4k-raw.mp4" -c copy -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
    -movflags +write_colr+faststart "$W/output-4k.mp4"
if [ "$DRY" = 0 ] && { [ "$started" = 1 ] || [ "$FROM" = loudness ]; }; then
  python3 -c 'import json,sys; json.dump({"project": sys.argv[1], "loudness": -14, "segments": [{"name": sys.argv[1], "file": "output-4k.mp4"}]}, open(sys.argv[2], "w"), indent=1)' \
    "$NAME" "$W/assembly-render.json"
fi
step loudness "voice to -14 LUFS (assemble.py, one segment)" -- \
  python3 "$SK/scripts/assemble.py" --manifest "$W/assembly-render.json" --out "$W/$NAME-4k.mp4" --gpu
step verify "verify-render.py (exit 1 = do not deliver)" -- \
  python3 "$SK/scripts/verify-render.py" --render "$W/$NAME-4k.mp4" --index "$W/public/index.html" --min-mbps "$MIN_MBPS"
if [ -n "$CARD" ] && [ -n "$WINDOWS" ]; then
  step card "face card never blank in its windows" -- \
    python3 "$SK/scripts/card-check.py" --render "$W/$NAME-4k.mp4" --card "$CARD" --windows "$WINDOWS"
else
  [ "$started" = 0 ] && [ "$FROM" = card ] && started=1
fi
FINAL="$W/$NAME-4k.mp4"
if python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("bookends") else 1)' "$W/render.json"; then
  step bookends "intro sting + end card from the profile, joined on (bookends.py)" -- \
    python3 "$SK/scripts/bookends.py" --project "$W" --gpu --workers "$WORKERS"
  FINAL="$W/$NAME-full-4k.mp4"
else
  [ "$started" = 0 ] && [ "$FROM" = bookends ] && started=1
fi
MSTATE="$(python3 "$SK/scripts/music.py" status --project "$W" 2>/dev/null || echo off)"
MUSIC_OUT=""
case "$MSTATE" in
  chosen*)
    step music "music: candidate ${MSTATE#chosen }, ducked under the voice (music.py mix)" -- \
      python3 "$SK/scripts/music.py" mix --project "$W" --pick "${MSTATE#chosen }"
    MUSIC_OUT="${FINAL%.mp4}-music.mp4" ;;
  pending)
    if [ "$started" = 0 ] && [ "$FROM" = music ]; then started=1; fi
    if [ "${MUSIC_PASS:-on}" = off ]; then
      echo "-- music: the pass is off on this Mac (MUSIC_PASS=off); no music"
    elif [ "$started" = 1 ] && [ "$DRY" = 0 ]; then
      echo "== music: waiting for a pick (MUSIC-REVIEW.html; \"music N for $NAME\" or \"no music for $NAME\"), then: render-mac.sh $W --from music"
      echo "== music waiting $(date '+%H:%M:%S')" >>"$LOG"
      exit 10
    fi ;;
  *) [ "$started" = 0 ] && [ "$FROM" = music ] && started=1 ;;
esac
step deliver "copy to $DELIVER" -- \
  bash -c 'mkdir -p "$1" && cp "$2" "$1/" && { [ ! -f "$3" ] || cp "$3" "$1/"; } && { [ -z "$4" ] || cp "$4" "$1/"; } && { [ -z "$4" ] || [ ! -f "$5" ] || cp "$5" "$1/"; }' \
    _ "$DELIVER" "$FINAL" "$W/chapters.txt" "$MUSIC_OUT" "$W/MUSIC.md"

if [ "$DRY" = 0 ] && [ "$KEEP_CACHE" = 0 ]; then   # the frame cache can fill the temp folder (16 GB in a day)
  rm -rf "${TMPDIR:-/tmp}"/hyperframes-extract-cache-* 2>/dev/null
fi
echo "done in $(( ($(date +%s) - T0) / 60 )) min: $FINAL (copied to $DELIVER)"
