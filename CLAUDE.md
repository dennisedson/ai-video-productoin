# Video (Dennis's YouTube editing)

Edits use the youtube-edit skill (`.claude/skills/youtube-edit/SKILL.md`). Renders run on this Mac with
`render-mac.sh`; a session working from anywhere else stops at Checkpoint B.

## The studio: every video from idea to results

Each video is a project from the idea on: `bash .claude/skills/youtube-edit/pipeline/yt new <name>` makes
`videos/<name>/` with `video.json`, `BRIEF.md` (from the idea's origin: a colleague's work, a problem, a feature),
`research.md`, `references.md` (every outside link), `SCRIPT.md` (read-aloud lines in `>` blockquotes for the
teleprompter, `→ demo:` beats, ```` ```copy: ```` blocks for the recording sheet) and `results.md`. When Dennis asks for a
new video without a name, ask for the name first (and the idea's origin), then run `yt new`.

Dennis works in the studio, a page on `http://127.0.0.1:4040` (`yt app` opens it; launchd keeps it running): the
board, each video's phases (ideation, script and direction, recording, cut, storyboard, render and music on the home
Mac, packaging, publish, results) with steps and templates, document editors, requests to Claude, a chat per video,
reviews with notes pinned to a moment and a box, and questions. Claude runs started there work on one video; they ask
Dennis with `yt ask <name> "question" --options "a|b"`, and the answers are in `videos/<name>/questions.json`. Its
code is `.claude/skills/youtube-edit/pipeline/studio/` (tests: `python3 -m unittest discover` in its `tests/`).
Scripts are written in his voice: `profiles/<profile>/VOICE.md`.

Length: under 6 minutes is the target, 10 the limit (`profiles/<profile>/youtube.json` "length"); the studio estimates
each script (150 words a minute read aloud, 45 s a demo beat, or "(~30s)" on the beat) and shows the cut's length.
When an idea is too big for that, has two audiences, or parts that stand alone, propose a split rather than saying so
in prose: `python3 .claude/skills/youtube-edit/pipeline/studio/core.py propose-split <name> --series "Title" --part
"<name>::Title::Promise::minutes" --part "next-name::Title::Promise::minutes" --why "..."`. Dennis accepts it in the
studio; the video becomes part 1 and the others are created with its research and links. A video can be in several
series (`video.json` "series" is a list); each series has a page in `catalog/series/<slug>.json` and `.md` (order of
the parts, playlist link and description, cover).

In a thread, work on one video at a time; when a request names a video, read its `BRIEF.md`, `references.md` and
answered questions first. A long thread that carries several videos costs far more on the work Mac: suggest a fresh
thread, or the studio's chat for that video, when the subject moves to another video.

## The hands-off pipeline

Recordings for a studio video go in its `raw/` and start with `yt start <name>` (the studio's "Start the cut"), or
drop them into `videos/_inbox/<name>/` under the same name. Dropping recordings into `videos/_inbox/<name>/` (the camera file with the mic, the screen file for a tutorial, an
optional `notes.txt`) starts an edit on its own: a launchd agent claims the folder, the cut runs (scripts, then an
unattended Claude Code run for the judgment calls), and a Mac notification opens `videos/<name>/REVIEW-A.html`.
`yt status` lists every edit and its stage; `yt log <name>` shows its log. Details: the skill's `pipeline/` folder and
its "Hands-off pipeline" section.

Stages: queued -> cutting -> **awaiting-A** -> storyboarding -> **awaiting-B** -> rendering -> done (or failed).
On the work Mac (hand-off) an approved render waits as **awaiting-import** until its video comes back.

A finished video that needs only YouTube metadata (no edit) goes in `videos/_youtube-inbox/` (a file, or a folder
with the video and `notes.txt`): it moves to `videos/<name>/` and runs queued -> transcribing -> drafting ->
**youtube-ready** (`yt run <name> youtube-only` reruns it). Its transcript is on the published clock already.

## When Dennis approves or sends notes in this thread

He writes things like "approve agents-3", "approve agents-3, grade blacks", "agents-3: cut the second retake at 2:10",
or "approve agents-3 with the face on the right". Then:

1. Read `videos/<name>/state.json` (`bash .claude/skills/youtube-edit/pipeline/yt status`). Act only on a video waiting at a checkpoint (awaiting-A,
   awaiting-B, or awaiting-host for a render); for anything else say what stage it is in.
2. Write his words, verbatim, with the date, to `videos/<name>/approvals/A.md` or `B.md` (append; create the folder).
   At A record the camera grade he chose; when he names none, use `blacks` and say so.
3. Notes without "approve": make the change now by the skill's rules (at A: the cut, `cut-list.json`, PAPER-CUT.md and
   the review MP4; at B: `storyboard.json`, compose, checks, `snaps/sheet.png`, and the preview if the change moves
   anything; the checkpoints work at 1080p, so any apply-cut.py run here gets `--vf scale=-2:1080` and only
   render-mac.sh builds 4K), rebuild the review page (`python3 .claude/skills/youtube-edit/pipeline/review-page.py videos/<name> A|B`),
   tell him what changed, and wait for his approval. The state stays where it is.
4. "approve" (with or without small notes you apply first): start the next stage in the background and stop there:
   at A `bash .claude/skills/youtube-edit/pipeline/yt run <name> storyboard`, at B `bash .claude/skills/youtube-edit/pipeline/yt run <name> render` AND
   `bash .claude/skills/youtube-edit/pipeline/yt run <name> youtube` (the YouTube metadata, drafted beside the render). Do not do the next stage's work in this thread.
   When he says "rush", "fast" or "I need it soon" ("approve agents-3, rush"), add `--fast` (`yt run <name> storyboard
   --fast`, or `yt run <name> cut --fast` when he asks for a cut rerun): that stage runs on all cores despite
   `PRIORITY=background` or `utility`, louder and quicker. The render already runs at normal priority, so `--fast` changes nothing
   there. A stage already running can't be sped up; restarting it with `--fast` repeats it from the start, so say what
   that costs before doing it.
   **On the work Mac** (`yt host` says renders are handed off) the render stage packs `~/Desktop/<name>-render.zip`:
   tell him to drag it through Screen Sharing into the home Mac's `videos/_render-inbox/`. When he says the video
   is back ("agents-3 is back, it's in Downloads"), find the file and run `bash .claude/skills/youtube-edit/pipeline/yt import <name> <video>`;
   if it refuses, say why. With an automatic render host (SSH or a share) instead, run `yt host` first and, when the
   home Mac isn't ready, ask whether he'll fix it or wants `yt run <name> render --here`.
5. Keep replies short: what you changed, what starts next, and that a notification will come.

## YouTube metadata

`videos/<name>/youtube/YOUTUBE.md` holds the titles, description, chapters, cards, end screen, tags, pinned comment
and links to shorten; `captions.srt` the captions. It is built from `youtube/metadata.json` (written by the youtube
stage; `pipeline/prompts/youtube.md` has the rules: search-first, links only from the profile's `LINKS.md` or opened
and verified, times on the flat cut's clock). When he asks for changes ("shorter title", "add the docs link"), edit
metadata.json and run `bash .claude/skills/youtube-edit/pipeline/yt youtube <name>`; never edit YOUTUBE.md by hand. Links are shortened
through Bitly's API (`yt shorten <name>`; the token is in his Keychain as `bitly-hubspot`, never ask for it or print
it). That Bitly account is HubSpot's and is for HubSpot content only: never use it for another profile or outside
content, and pass `--hubspot` only when he says the video is HubSpot content. After a Bitly limit or error the rest stay
long, so say how many are left. He can still paste a link into
`youtube/links.tsv` by hand; `yt youtube <name>` then uses it. Thumbnails (`youtube/thumbnail-N.jpg`, in the profile's brand from
`profiles/<profile>/thumbnail/`): for a new headline, key word or frame ("thumbnail 1: the frame at 2:10"), edit
`thumbnail.options` in metadata.json (a headshot instead of a frame: `"face": "<file>"`, from `shared/img/headshots/`
or the video's folder) and run `bash .claude/skills/youtube-edit/pipeline/yt thumb <name> [N]`; never restyle one video's thumbnail
by hand (brand changes go in the template, for every video). When he says a video is
live, `yt published <name> <url>`. `catalog/VIDEOS.md` is the channel's catalog (one entry per video, written by
those commands): read it for what earlier videos covered; after it changes, commit and push it. When the work on a
video is finished ("move agentcli to Drive"), `bash .claude/skills/youtube-edit/pipeline/yt drive <name>` copies the
video, thumbnails, captions and YOUTUBE.md to the team's Drive folder by year, month and series (the profile's
youtube.json "drive"; `--dry-run` first when a video of another size is already there, and ask which one belongs).

## Machines

This repo is cloned on two Macs: the home Mac and the HubSpot work Mac. `videos/` is not in git, so footage, edits and
renders stay on the machine that made them. On the work Mac there are no Tella or Epidemic Sound connectors: take
screen recordings as plain files (the "Two-file tutorials" route), use the sound effects in `shared/sfx`, and default
to the `hubspot` profile. Music is picked on the home Mac, which has the Epidemic Sound connector, while the 4K render
runs there (a notification says when): when he says "music for <name>", follow
`.claude/skills/youtube-edit/pipeline/prompts/music.md` (five Epidemic candidates, each edited so its drop lands on the
sting's hit, 30 s samples under the video, `MUSIC-REVIEW.html`) and wait for his pick. "music 3 for <name>" -> `bash
.claude/skills/youtube-edit/pipeline/yt music <name> 3` (make edit B first when the plan has one); "no music for <name>"
-> `yt music <name> none`. The render waits for the pick at its end (awaiting-music), then mixes it in and delivers
the music version, the no-music twin and `MUSIC.md`. Never in the work Mac's thread (its renders don't wait for music). Company software on the work Mac blocks file sharing and SSH to the home
network, so its renders are handed off by hand: a bundle zip carried over Screen Sharing, rendered on the home Mac,
the video carried back and imported (`yt import`). Devs:After Dark is edited and rendered on the home Mac only. When the
skill changes ("save this to the skill"), commit it and push, so the other Mac gets it with `git pull`.
