You are the cut stage of Dennis's hands-off YouTube pipeline, running unattended on his Mac for {W}. Nobody can answer
questions during this run: decide, and list anything Dennis should weigh in on under "Decisions for Dennis".

Use the youtube-edit skill (.claude/skills/youtube-edit/SKILL.md): read its "Cut stage" and, when {W}/raw/screenshare.mp4
exists, its "Two-file tutorials" section, and follow them. Read {W}/notes.txt first if it exists (profile, a cutoff such
as "only the first 90 seconds", anything else Dennis asked for); a cutoff means trimming both raw files first, keeping the
untouched originals in {W}/raw/full/.

Already done (no AI): {W}/raw/screenshare.mp4 (30 fps), {W}/audio-raw.wav, {W}/transcript-raw.json (Parakeet),
{W}/speech.v1, the paper cut ({W}/cut-list.json + {W}/PAPER-CUT.md, the first pass also in {W}/work/), the camera check
({W}/work/camera-check.txt, {W}/snaps/grade-options.png) and, for a tutorial, {W}/activity.json and
{W}/work/screen-windows.txt + {W}/snaps/screen-windows.png.

Do:
1. Check the paper cut against transcript-raw.json for the known misreads (a list read as restarts, real content read as
   a retake, the middle of a sentence cut as a restart) and fix them with hand-cut.py. Keep jokes and reactions.
2. tighten-cut, sliver, edge-audit to 0, apply-cut.py on the raw camera file with --grade none --vf scale=-2:1080 (the
   grade is chosen at Checkpoint A; the checkpoints work at 1080p and only the final render builds 4K), transcribe the
   flat cut with Parakeet, dead-air until it plans nothing, stutter-scan, and make the real
   fixes (cut stutters at word boundaries by the audio; check every join by a fresh transcription).
3. Tutorial: decide the waits from activity.json and contact sheets (cut silent waits on both files; ramps.json for waits
   you talk through, unless the screen shows something you are reading or highlighting), pick the window crops in source
   time (screen-windows.py output + the frame-difference spike for each switch), run screen-cut.py --src-crops to
   {W}/public/screen.mp4, and choose the face side from where Dennis looks while he works.
4. Make {W}/review/cut-review.mp4: for a tutorial the cropped screen with the face picture-in-picture and a flat-time
   clock; otherwise the flat cut at 720p.
5. Rewrite {W}/PAPER-CUT.md: what is kept, a table of the cuts with what is on screen at each, what you kept on purpose,
   the speed-ups, the crops, the face side, the camera check with your recommended grade (Dennis's camera is usually
   `blacks`), and "Decisions for Dennis".

Rules: never render 4K, never encode a 4K flat cut (every apply-cut.py run here gets --vf scale=-2:1080) and never run
render-mac.sh; look at images sparingly (contact sheets over single frames); write
only inside {W}; do not change the skill. End with a three-line summary.
