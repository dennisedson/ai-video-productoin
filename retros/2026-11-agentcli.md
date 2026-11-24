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
| Render | handed off 12:13 on 11-24 | none on this Mac | rendering on the home Mac (see below) |

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

Most of the home Mac's part was building the setup the work Mac ran on (11-22 to 11-24), in one long Claude thread
attached to the home Mac's Video folder. The agentcli render itself is the last block.

### Summary (home Mac)

| Piece | When | Notes |
| --- | --- | --- |
| Connectors, work/home split, the repo | 11-22 | Minimum connectors: none required; Tella and Epidemic Sound only where allowed |
| Known-good tag, render on the home Mac | 11-22 | Built for SSH and a mounted share first; both blocked by HubSpot, so a hand-off by hand |
| Quieter checkpoints | 11-22 | 1080p checkpoints, `PRIORITY` for the cut and storyboard stages |
| Home Mac install, music, `yt status` progress | 11-23 | Install "hang" was the drawtext preflight; music moved to the home Mac |
| YouTube metadata, inbox, catalog, Bitly | 11-23 to 11-24 | Bitly limited to HubSpot content after the build |
| agentcli 4K render | 11-24, 12:24 onwards | Hand-off zip 2.5 GB; 4K flat cut 15 min; render at 65% by 13:10 |
| Thumbnails, headshots | 11-24 | Added after the render had started; first real run still to come |

### 1. Connectors and the split between Macs (11-22)
1. Minimum for the skill: no connectors at all. Tella and Epidemic Sound help where they're allowed (home Mac only);
   on the work Mac screen recordings come in as plain files and sound effects come from `shared/sfx`.
2. Setup steps and the context for a work-account Claude project, then a repo for the application only (`videos/`
   ignored, no footage, tests or project files). The DAD profile lives in the same repo.
3. Turned the home Mac's existing folder into a clone (`git init`, `reset origin/main`) instead of re-cloning.
4. Synced three fixes from the work Mac (rebase, merged by hand in `yt` and CLAUDE.md).

### 2. Rendering work videos on the home Mac (11-22)
5. Goal: AI work on the work Mac, 4K compute on the home Mac. Built `remote-render.py` with two automatic routes (a
   mounted SMB share, or tar over SSH), `--check`, and a render-host agent with a heartbeat. When the home Mac isn't
   reachable the render asks (Check again / Render here / Later), never falls back silently, per Dennis.
6. Tagged the previous setup as `before-remote-render` (dfbf480) so either Mac can go back. The tag push was refused
   from Claude's environment; Dennis pushed it.
7. Connecting failed: the address first tried, 10.5.0.2, was a virtual adapter; the home Mac's LAN address is
   192.168.86.48. Port 22 answered, then HubSpot's endpoint software showed "SSH Access Denied". SMB was blocked too.
8. Asked about GitHub as a transport for footage: declined (company footage on a personal GitHub account). Screen
   Sharing file transfer works, so the route became a hand-off by hand: `yt` packs `~/Desktop/<name>-render.zip`, it
   is dragged into the home Mac's `videos/_render-inbox/`, the render-host agent waits for the copy to finish and
   renders, the video is dragged back and `yt import` checks and delivers it. Documented in the README runbook.

### 3. Quieter checkpoints (11-22)
9. The work Mac's fans ran hard during the checkpoints. Changes: checkpoints work on a 1080p flat cut
    (`--vf scale=-2:1080`); only `render-mac.sh` builds 4K, with the grade and face source in `render.json`
    (`face_raw`, `grade`); stages run under `taskpolicy` by `PRIORITY`. Dennis was mid-Checkpoint B, so the new bundle
    waited until B finished. (The work Mac's part covers how `background` turned out to be too slow.)

### 4. Home Mac install, music, progress (11-23)
10. `install.sh --serve-renders` on the home Mac "hung". It was the ffmpeg preflight failing because Homebrew's ffmpeg
    has no drawtext: `brew install ffmpeg-full && brew unlink ffmpeg && brew link --force ffmpeg-full`.
11. Epidemic Sound isn't allowed on the work Mac's Claude connectors, so music goes on at the home Mac, on the
    rendered video in `_render-inbox/<name>/out/`, before it goes back ("add music to <name> in the render inbox").
12. `yt status` got a progress column: renders from the log (steps weighted by earlier renders, HyperFrames' frame
    count inside the render step), cut and storyboard as elapsed against this Mac's median for that stage.

### 5. YouTube metadata (11-23 to 11-24)
13. A `youtube` stage beside the render: maps the flat cut's clock onto the published video (sting, end card), writes
    captions, has a headless Claude draft `metadata.json` (search-first and AI-search-first rules), and builds
    YOUTUBE.md (titles, description with tracked CTAs, chapters, cards, end screen, tags, pinned comment) with
    YouTube's limits checked. Links only from the profile's `LINKS.md` or pages opened and verified.
14. `catalog/VIDEOS.md`: one entry per video, written by the build and `yt published`; later videos use it for cards.
15. Bugs found in testing: a caption cue straddled the sting (split and clamped), an operator-precedence bug in the
    catalog's "Related" line, stacked notes in the progress column.
16. `videos/_youtube-inbox/` for finished videos that only need metadata (transcribed on the published clock).
17. Bitly: first a manual format (`links.tsv`), then the API (`yt shorten`, token in the Keychain as
    `bitly-hubspot`). After it was built Dennis said the account is HubSpot's and for HubSpot content only, so it was
    reworked: the account belongs to the `hubspot` profile, is used only when a video is explicitly HubSpot (its
    storyboard, or the inbox `notes.txt`), and `--hubspot` confirms an assumed one. Skips are written down.
18. The stage was tested against a stand-in Bitly server; the real account was first used on the three drafts (the work Mac's part, step 26).

### 6. The agentcli render (11-24)
19. The work Mac packed the zip at 12:13 (51 files, 2.49 GB). Dragged over Screen Sharing; the render host unpacked it
    at 12:24, so about 11 minutes to copy.
20. 4K flat cut: 900 s (385.6 s of video from a 627 s camera file, 123 segments, BT.709, grade blacks). Compose and
    `hyperframes check` in 17 s (17 lint warnings, one a GSAP target that doesn't exist, `#tag-glass .pip.done`).
21. Render started 12:40 (1 worker, 45M): 11,569 frames, 65% at 13:10, about 4.7 frames a second, so done around
    13:25 before the bookends and checks.
22. Still to do: bookends and checks finish, drag back, `yt import` on the work Mac, upload with the
    YouTube metadata and thumbnail, `yt published`, `yt clean-renders` on the home Mac.

Background music was skipped for agentcli: it's part of the home Mac's job, but the hand-off went straight to the
render and the music step (step 11) only runs when asked, after it. Now built in: a notification at the start of each
render on the home Mac to pick the music, five 30 s samples synced to the sting, and the render waits for the pick at
its end, so it can't be skipped by accident (a separate pass before the render would hold the 45 min render for a
person; this way the picking happens during it).

### 7. Thumbnails (11-24, during the render)
23. Thumbnails were missed in the YouTube packaging and added now: a one-frame template per profile in its brand,
    `scripts/thumbnail.py` (candidate frames for the draft, the 4K camera frame with the grade, a cutout with
    `hyperframes remove-background`, photo fallback), `yt thumb`. A HyperFrames snapshot at twice the density gives
    3840x2160 in about 6 s; rendering it as a video took 5 min.
24. Dennis can use a headshot instead of a frame. Headshots stay local (`shared/img/headshots/`, git-ignored, and the
    video's own folder for a guest) and change per person, so the default stays a frame from the video.
25. Tested on a stand-in made from an agents-2 still, not on real 4K camera footage; the first real run is agentcli.

### How the home Mac thread was tested
- The Claude environment that edits the repo can't reach the Macs' tools directly: its link to the home Mac's folder
  runs in a VM where background jobs die, ffmpeg is 4.4 (no `-fps_mode`), and installing packages was denied. Tests
  ran on short stand-in clips in the foreground, with shims. Nothing there exercised launchd, Screen Sharing, the
  Keychain or Apple-silicon timings; those were first tried for real by Dennis.

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
| Remote render built for SSH and SMB first | a day's design and test work (11-22), not measured | HubSpot's network policy wasn't checked before designing the transport |
| First connection attempt at the wrong address | a few rounds of ping and nc, not measured | 10.5.0.2 is a virtual adapter; the Mac's LAN address wasn't looked up first |
| Home Mac install looked hung | a debugging round (ps, bash -x), not measured | The preflight's failure (no drawtext) didn't reach the screen clearly |
| Bitly built for one account, then reworked | one rework | Whose account it was, and for which content, wasn't asked before building |
| Thumbnail missing from the YouTube package | added late, after the render had started | No checklist of everything a YouTube upload needs |
| Hand-off zip 2.49 GB, not the 1.3 GB the README says | about 11 min to copy | The bundle carries the whole 627 s camera file; only 386 s of it is used |
| 4K flat cut on the home Mac: 15 min before the render starts | 15 min per render | Every hand-off rebuilds the graded 4K cut from the raw camera file |
| New features tested on stand-ins only | risk, not time yet | No small real sample (a short 4K talking-head clip) kept for end-to-end tests |
| No background music on agentcli | skipped this time | Music is a separate step after the render, started only by asking; the hand-off renders as soon as the zip lands, so nothing prompted it |
| Repo name differs from the docs | not yet | The remote is `ai-video-productoin`; the README says `ai-video-production` |

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
| Check company network and data rules before designing anything that moves files between Macs | habit | lesson |
| Ask whose account and what content before wiring any third-party API (Bitly) | habit | lesson |
| A YouTube upload checklist in YOUTUBE.md (video, captions, thumbnail, title, description, chapters, cards, end screen, playlist) that shows what's ready | youtube-meta.py | idea |
| Trim the camera file in the bundle to the kept segments plus a second of handles (cut-map re-timed): about 40% smaller, faster to copy | remote-render.py | idea |
| Show on the work Mac how far the home render is: the home Mac writes `status.json` into `out/`, visible over Screen Sharing; or `yt status` on the home Mac lists `_render-inbox` jobs (it does; say so in the runbook) | README, render-host-job.sh | idea |
| Preflight prints a clear one-line reason and the fix before `install.sh` exits | install.sh, lib.sh | idea |
| Keep a short real 4K sample (20 s talking head, git-ignored, on each Mac) and a `yt selftest` that runs cut, thumbnail and metadata on it | pipeline, tests | idea |
| Background music pass on the home Mac, picked while the render runs: five Epidemic candidates, each edited so its drop lands on the sting's hit, compared as 30 s samples under the video; the render waits for the pick at its end and mixes it in (Dennis's spec, 11-24) | music.py, prompts/music.md, render-mac.sh (music step), render-host-job.sh, stage.sh, yt music | done (built and tested on stand-in tracks; first real run next video) |
| First real thumbnail run on agentcli (frame and headshot), then adjust the templates | thumbnail templates | next |
| Fix the repo name: rename the GitHub repo to `ai-video-production` (GitHub redirects the old URL), or correct the docs | GitHub, README | next |
| Make the repo private (it's public, with HubSpot fonts in it) | GitHub settings | next |
| Lint: drop the GSAP warning for `#tag-glass .pip.done` in the composition | compose / formats | idea |
