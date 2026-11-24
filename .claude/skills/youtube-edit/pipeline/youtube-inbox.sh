#!/bin/bash
# youtube-inbox.sh: finished videos that need only the YouTube metadata treatment, no edit. Run by inbox.sh (the same
# launchd agent watches videos/_youtube-inbox). Drop either a video file (its name becomes the video's name) or a folder
# <name>/ holding the video and an optional notes.txt ("Devs:After Dark", "series: HubSpot Is Going Headless",
# "next: the Agent CLI", links or names to use). Once it has stopped growing for 20 s it moves to videos/<name>/, and
# the youtube-only stage transcribes it and drafts youtube/YOUTUBE.md, captions.srt, links.tsv and the catalog entry.
. "$(cd "$(dirname "$0")" && pwd)/lib.sh"
YTIN="$ROOT/videos/_youtube-inbox"; mkdir -p "$YTIN"
mkdir "$YTIN/.lock" 2>/dev/null || exit 0
trap 'rmdir "$YTIN/.lock" 2>/dev/null' EXIT
size() { du -sk "$1" 2>/dev/null | cut -f1; }
for p in "$YTIN"/*; do
  [ -e "$p" ] || continue
  base="$(basename "$p")"
  case "$base" in .*|_*) continue ;; esac
  if [ -d "$p" ]; then
    [ -e "$p/.claimed" ] && continue
    vid="$(ls -S "$p" 2>/dev/null | grep -iE '\.(mp4|mov|m4v)$' | head -1)"; [ -n "$vid" ] || continue
    name="$base"
  else
    echo "$base" | grep -qiE '\.(mp4|mov|m4v)$' || continue
    vid="$base"; name="${base%.*}"
  fi
  s1=$(size "$p"); sleep 20; s2=$(size "$p")
  if [ "$s1" != "$s2" ]; then log "youtube inbox: $base still copying"; continue; fi
  slug="$(echo "$name" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9._-')"
  W="$ROOT/videos/$slug"
  if [ -e "$W" ]; then
    notify "YouTube metadata: $base" "videos/$slug already exists. Rename it in the YouTube inbox to start a new one."
    [ -d "$p" ] && touch "$p/.claimed" || mv "$p" "$p.skipped"; log "youtube inbox: videos/$slug exists, skipped"; continue
  fi
  mkdir -p "$W/youtube" "$W/pipeline"
  ext="$(echo "${vid##*.}" | tr '[:upper:]' '[:lower:]')"
  if [ -d "$p" ]; then
    mv "$p/$vid" "$W/$slug.$ext"
    [ -f "$p/notes.txt" ] && mv "$p/notes.txt" "$W/notes.txt"
    for f in "$p"/*; do [ -f "$f" ] && mv "$f" "$W/"; done
    rmdir "$p" 2>/dev/null || touch "$p/.claimed"      # empty: gone; anything left: marked, never taken twice
  else
    mv "$p" "$W/$slug.$ext"
  fi
  profile=hubspot; grep -qiE 'after ?dark|devs-after-dark|\bDAD\b' "$W/notes.txt" 2>/dev/null && profile=devs-after-dark
  printf '{"kind": "metadata-only", "video": "%s", "profile": "%s", "from": "%s"}\n' "$slug.$ext" "$profile" "$base" > "$W/youtube/source.json"
  state_set "$slug" queued "metadata only: $base"
  notify "YouTube metadata: $slug" "Started: transcribing $base for its YouTube metadata."
  nohup bash "$PIPE/stage.sh" "$slug" youtube-only >> "$W/pipeline/stage.log" 2>&1 &
done
