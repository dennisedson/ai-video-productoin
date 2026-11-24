The background music pass for one video, run in a Claude Code thread on the home Mac (the one with the Epidemic Sound
connector) when Dennis says "music for <name>". It usually runs while the 4K render is going; the render waits for
the pick at its end. Never on the work Mac, never with music from anywhere but Epidemic Sound.

The video's folder D: `videos/_render-inbox/<name>` when that has a job.json (a work video handed over), else
`videos/<name>`. Scripts: `python3 .claude/skills/youtube-edit/scripts/music.py <cmd> --project D`.

1. `music.py plan`: the published timeline (the sting's in and out and its hit, the end card), the 30 s sample
   window, and how many Epidemic edits the length needs (one edit stops at 5 min: edit A, plus B past that). If it
   says the profile's pass is off, stop and say so.
2. Read what the video is: D/notes.txt, D/storyboard.json, D/transcript.json (the hook and the topic), the profile's
   music.json "brief" and STYLE.md. Then pick five candidates with SearchRecordings (filter vocals: false, the BPM range
   in the brief, durations over 90 s; search by mood and genre terms, not the topic): five different directions, not
   five versions of one: say two that sit squarely in the brief, one with more energy, one calmer, one wildcard.
   Avoid tracks whose tags say vocals, and anything that would sound like a sting of its own under talk.
3. For each candidate: download its preview to D/music/preview-N.mp3 (`curl -sL "<lqmp3Url>" -o ...`), then
   `music.py analyze --track D/music/preview-N.mp3`. It finds the track's drops (bar-aligned jumps in energy) and
   prints `edit_input`: the EditRecording input that puts the best drop on the sting's hit and lasts the whole of edit
   A. If the top drop is in the last fifth of the track or weak (score under 1.3), try the next one with `--drop T`.
   Run EditRecording(id, edit_input), poll PollEditRecordingJob until COMPLETED, DownloadRecordingEdit, and save the
   WAV as D/music/cand-N.wav. `music.py check --file D/music/cand-N.wav` says where its beat lands against the hit
   (within 60 ms is on; further off: redo the edit, or drop the candidate).
4. Write D/music/candidates.json: {"N": {"id", "title", "artist", "bpm", "why"}} (why: one line on what it brings).
5. `music.py samples`: the same 30 s of the video (hook, sting, the start of the body) under each candidate, at the
   levels the final mix uses -> D/music/samples/N.mp4 and D/MUSIC-REVIEW.html. Open the page for him (`open`) and
   list the five in one line each. Stop and wait for his pick.

When he picks ("music 3 for <name>", "the third one"):
- If the plan has an edit B: make it for that track now (`music.py analyze --track D/music/preview-3.mp3 --edit B`
  gives the input; no required region), save it as D/music/cand-3-b.wav.
- `bash .claude/skills/youtube-edit/pipeline/yt music <name> 3`. It records the pick and, if the render is waiting,
  mixes and delivers (with music and the no-music twin, plus MUSIC.md); otherwise the render mixes it at its end.
- "no music for <name>": `yt music <name> none`.
- Notes on a sample ("3, but quieter", "louder on the sting"): write D/music/levels.json with the changed levels
  (hook_db: under the hook and the sting, body_db: under the rest, card_db: the end card; dB, from the profile's
  music.json), rerun `music.py samples`, and show him again. Change the profile's music.json only when he says it
  should hold for every video.

Keep the replies short: the five picks, the page, then what started.
