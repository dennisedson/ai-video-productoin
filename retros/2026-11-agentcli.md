# Retro: agentcli, end to end (Nov 2026)

The first HubSpot work video through the hands-off pipeline from the work Mac: two-file tutorial (camera + screen
recording), hubspot profile, render handed off to the home Mac. This file lists every step we took, what went wrong,
and what to change. Each machine adds its own part; times are local (ET).

How to add to it: put new steps under your machine's heading in order, and add a row to "Ideas to improve" for anything
worth changing. Tag each idea with where the fix lives (skill script, prompt, pipeline, CLAUDE.md, habit).

## Summary so far (work Mac)

| Stage | Wall time | Claude runs (cost) | Rounds of notes |
| --- | --- | --- | --- |
| Setup fixes before the cut could run | about 1.5 h on 11-23 | interactive | n/a |
| Cut (Checkpoint A) | first run 14:06-15:15 on 11-23; rerun 20:35-21:15 | cut stage $2.85 (39 min, the rerun) | 2 (PAPER-CUT notes, enhanced audio) plus a false alarm (browser cache) |
| Storyboard (Checkpoint B) | 21:29 on 11-23 to 12:13 on 11-24 | storyboard stage $2.15 (rerun with notes), plus interactive fixes | 3 (10 notes, 4 notes, "drop a second") |
| YouTube metadata | drafted 21:31 on 11-23, redrafted 12:13 on 11-24 | youtube stage $0.39 per draft | links: Bitly, exercise repo, series links |
| Render | handed off 12:13 on 11-24 | none on this Mac | pending (home Mac) |

## Steps on the work Mac

### 1. Ingest and setup (11-23)
1. Recordings dropped into `videos/_inbox/agentcli/` (camera with mic, screen recording). launchd claimed it.
2. The cut stage failed: `camera-check.py` needs ffmpeg `drawtext`, and Homebrew's ffmpeg has none. Fix: `ffmpeg-full`,
   which is keg-only, so `brew unlink ffmpeg; brew link --force ffmpeg-full`. Added to the skill as a gotcha.
3. It failed again: `screen-windows.py` needs numpy, and launchd's python (Homebrew 3.14) isn't the terminal's (pyenv
   3.11.9). Fix: install.sh now picks a python that has numpy, and a `preflight` check in lib.sh/stage.sh names what's
   missing before a stage starts.
4. Git was one behind and one ahead of the home Mac; rebased and pushed.
5. The cut looked hung: `PRIORITY=background` (efficiency cores) made apply-cut about 13x slower (about 45 min against
   4 min per pass). Measured the options, added `PRIORITY=utility` (nearly full speed, other apps first) and
   `yt run NAME STAGE --fast` (rush), and wrote the rush rule into CLAUDE.md. A running stage can't be sped up.

### 2. Checkpoint A: the cut
6. The cut stage (scripts, then an unattended Claude run) wrote PAPER-CUT.md, the review MP4 and REVIEW-A.html.
7. Dennis didn't know how to open the review page (he expected it to open on its own). Answer: the notification, or
   `yt open NAME`.
8. Dennis left notes in PAPER-CUT.md and supplied enhanced audio. The first "enhanced" MP4 was byte-identical to the
   original; the second was a WAV with no extension.
9. Synced the WAV to the camera (sync-tracks.py: +72 ms; the first mux used `adelay`, the wrong direction; fixed with
   `atrim`) and muxed it into `raw/talking-head.mp4`, so every stage and the 4K render use it.
10. Cut rerun ("our faster setup"): 385 s, 120 segments, $2.85.
11. Dennis added `raw/breel/` (the previous video) for a b-roll clip and the intro pattern (talk, sting, back to work).
12. Dennis heard clipped words after 4:00 ("apologize"). We checked all 120 joins (cross-correlation, 0 mismatches) and
    the RMS at each edge. Cause: the browser cached the old `cut-review.mp4` under the same name. Fix: the review page
    adds `?v=mtime` to every video and image (review-page.py). Lost about half an hour and some confidence.
13. edge-audit's default threshold (300 RMS) was too high for the enhanced audio (floor about 7). At about 40 it found one
    edge through sound (5:52); Dennis said it was fine.
14. Approved A ("the edge is fine / approve agentcli"), grade blacks.

### 3. Checkpoint B: storyboard
15. Storyboard stage: 1080p flat cut, storyboard, compose, checks, preview, render.json with bookends (sting at 26.72).
16. The sting title "Agent CLI" overflowed the template, so the run picked "The CLI". Fix: the sting template now fits
    its title (300 px down to 120 px).
17. The preview had no sting or end card, so Dennis couldn't see where the sting landed. Fix: the storyboard prompt
    now splices both into the preview in published order.
18. Dennis didn't know where B notes go. Answer: a "Dennis feedback" section at the end of CHECKPOINT-B.md (the stage
    rewrites that file, so it gets backed up to `work/` before a rerun).
19. Round 1, 10 notes: b-roll with your face plus the clip, sting point, two overlays white on white, zoom in at 1:34,
    zoom out at 4:11, a missing "open up Claude" line (a cut change at B), a zoom out/in at 4:22, remove an untrue
    overlay, sting title sizing. Cut changes done by hand, the rest by a storyboard rerun ($2.15).
20. Round 2, 4 notes, done interactively: two of you on screen didn't work (clip full screen, screen only); the deals
    never showed at 4:14 (in the recording they're on screen for 0.45 s before the page reloads; fixed with a screen
    ramp: loading at 3x, the table held in slow motion); cut "you never have to run an agent again" from the speech.
21. Round 3: "drop a second" from the deals hold. Took a segment split (the face is hidden there) plus new ramps.
22. Each round re-ran apply-cut, screen-cut, transcription, compose, the checks and a 15 min draft preview render.
23. Approved B; render handoff zip packed on the Desktop; YouTube stage redrafted for the new cut.

### 4. YouTube metadata
24. The youtube stage drafted titles, description, chapters, cards, end screen, tags, pinned comment and captions
    (about $0.39 each).
25. Checked every link for 404s (all 200, titles read for soft 404s).
26. Dennis added the Bitly helper on the home Mac; ran it on all three drafts (agentcli plus two inbox videos). Inbox
    videos without "HubSpot" in notes.txt need `--hubspot` each time.
27. Added the builder-exercises repo (the exercise the videos say is "linked below") to the library and both videos.
28. Added the series links (landing page `developers.hubspot.com/ai-tools/mcp`, Brooke Bond's blog post) as standard
    for HubSpot Is Going Headless. The blog post 404s today, so it's held back until it's live.

## Steps on the home Mac

(Home Mac: add the render, music, import back and publishing steps here, plus anything you changed along the way:
the YouTube metadata work, the Bitly helper.)

## What went wrong, and why

| What | Cost | Root cause |
| --- | --- | --- |
| Stage failures before the first cut (drawtext, numpy) | about 1.5 h | The work Mac's toolchain wasn't checked before the first video; launchd uses a different python and ffmpeg than the terminal |
| Cut looked hung | about 45 min per pass | `PRIORITY=background` puts ffmpeg on efficiency cores |
| "Clipped words" false alarm | about 30 min | Review videos reuse the same file name; the browser served the cached one |
| Enhanced audio needed three tries | about 20 min | No format check on what was dropped in (identical file, missing extension) |
| Sting title fallback "The CLI" | one round trip | Template sized for one word |
| Couldn't judge the sting in the preview | one round trip | The preview left out the bookends |
| B notes needed a cut change | manual work outside the stage | The storyboard stage can't change the cut; the notes had to be split between cut and storyboard by hand |
| The deals shot needed three rounds | three 15 min preview renders | The recording only shows the result for 0.45 s; nothing flags "the thing he's pointing at is barely on screen" |
| Two faces in the hook | one round | The note said "talking head and a screenshare"; read literally |
| Each small B change costs a full 15 min preview | about 15 min per round | The preview always renders the whole video |

## Ideas to improve

| Idea | Where the fix lives | Status |
| --- | --- | --- |
| Run `install.sh` preflight on any new Mac before the first video | habit, README | done (preflight added) |
| Default the work Mac to `PRIORITY=utility` | config | done |
| Cache-busting on review pages | review-page.py | done |
| Bookends in the preview | prompts/checkpoint-b.md | done |
| Sting title fits any length | profiles/hubspot/intro | done |
| Check dropped-in media (identical to the original? a real audio/video file?) before using it | pipeline | idea |
| A "result on screen" check: when he says "there we go" or shows a result, measure how long it's visible and hold it if short | storyboard skill (screen ramps/holds) | idea |
| Let the storyboard stage apply small cut changes from B notes (restore a line, cut a line), so a rerun handles them | prompts/checkpoint-b.md, scripts | idea |
| Partial preview: render only the changed windows (window-patch.py) for small B rounds, the full preview only at the end | storyboard skill | idea |
| A `yt notes NAME` that backs up CHECKPOINT-B.md / PAPER-CUT.md and starts the rerun, so notes are never overwritten | pipeline/yt | idea |
| edge-audit threshold scaled to the audio's noise floor | edge-audit.py | idea |
| Mark inbox videos as HubSpot content once (notes.txt) so Bitly doesn't need `--hubspot` each time | habit or youtube-inbox.sh | idea |
| A freeze-frame piece for screen-cut (the slow-motion hold works, but the pointer can drift) | screen-cut.py | idea |
