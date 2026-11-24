You are the storyboard stage of Dennis's hands-off YouTube pipeline, running unattended on his Mac for {W}. Nobody can
answer questions during this run: decide, and list anything Dennis should weigh in on in CHECKPOINT-B.md.

Checkpoint A is approved: read {W}/approvals/A.md (Dennis's grade choice and notes) and {W}/notes.txt. Use the
youtube-edit skill (.claude/skills/youtube-edit/SKILL.md) and the profile Dennis named (notes or approvals; HubSpot work
uses the `hubspot` profile; when nothing says, use the house look and say so).

Do:
1. Rebuild the flat cut with the chosen grade **at 1080p**: apply-cut.py --input <raw camera> --cut-list
   {W}/cut-list.json --out {W}/public/input-video.mp4 --grade <choice> --vf scale=-2:1080; re-transcribe it to
   {W}/transcript.json. The checkpoints work at 1080p; render-mac.sh builds the 4K flat cut from the same cut list and
   grade (step 6). The composition is 1920x1080 and face_crop is a region of the raw frame ("src": the raw camera's
   size), so nothing in the storyboard depends on the flat cut's resolution. Exception: a file made from the flat cut's
   picture (a subject matte, a span cut to its own file, a frame reference) must be made from a 4K flat cut; when the
   storyboard needs one, build the 4K flat cut for it as before and leave face_raw out of render.json. For the tutorial layout,
   pick the face card's region in the raw camera frame (592:1032 aspect, a tight crop on the head) for layout.face_crop
   (no separate crop file: the storyboard's video is input-video.mp4), and make sure {W}/public/screen.mp4 still matches
   cut-map.json.
2. Build {W}/storyboard.json by the skill (layout with face_crop, so the intro is full frame and face-only stretches
   go full frame too, see "No empty third"; overlays on their words, zooms where screen text is small, camera,
   the profile), compose, `npx hyperframes check` passes, beat-check 0 problems, gap-scan.
3. snap-beats.py -> {W}/snaps/sheet.png, and read it once to catch broken frames.
4. The preview Dennis watches: `npx hyperframes render {W}/public --quality draft --workers 1 -o {W}/review/preview.mp4`
   (1080p, no 4K), then card-check.py on it over the face-card windows when the tutorial layout is used.
5. When a choice is close (face side, a format, a zoom), render 6 to 10 s of each alternative into {W}/review/variants/
   (window-patch.py, draft quality) and name them.
6. Write {W}/render.json for render-mac.sh: name, shared "shared", face_raw (the raw camera file, relative to {W}, e.g.
   "raw/talking-head.mp4") and grade (the approved one), so render-mac.sh builds the 4K flat cut, no face_crop,
   workers 1, bitrate "45M", min_mbps 15 for screen-heavy videos (still screens undershoot the 40 floor), card and face_windows for the tutorial layout (starting where each face_full stretch ends), deliver
   "~/Movies/YouTube Renders/<name>".
6b. When the profile has bookends (profiles/<profile>/intro, outro): choose the sting point and the end card's "next"
   by the skill ("Bookends"), add "bookends" to render.json, and run bookends.py --project {W} --preview (the two
   clips land in {W}/bookends/; copy them into {W}/review/). Then, after card-check, splice them into
   {W}/review/preview.mp4 the way the render will (the sting cut in at bookends.intro.at, the video resuming at .resume,
   the end card after; ffmpeg, re-encoded at draft quality, audio kept), so the preview Dennis watches plays in the
   published order and he sees the sting land. Times in CHECKPOINT-B.md stay on the flat cut's clock; say so there.
7. Write {W}/CHECKPOINT-B.md (including the sting point and the end card text): the layout, every overlay and zoom with its time, the variants, open questions.

Rules: never render 4K, never encode a 4K flat cut except for the exception in step 1, and never run render-mac.sh; look at images sparingly; write only inside {W}; do not change the
skill. End with a three-line summary.

The studio (when the video has one): read {W}/BRIEF.md, {W}/references.md and {W}/SCRIPT.md / recording-sheet.md when
they exist (the plan, the links and what Dennis meant to show), and the answered questions in {W}/questions.json. For
anything that is Dennis's to decide, besides listing it in your write-up, ask it so it reaches him in the studio:
bash .claude/skills/youtube-edit/pipeline/yt ask <name> "the question" --options "choice a|choice b"
(one question per decision; carry on with your default and say which you chose).
