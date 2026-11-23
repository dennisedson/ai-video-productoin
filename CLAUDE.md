# Video (Dennis's YouTube editing)

Edits use the youtube-edit skill (`.claude/skills/youtube-edit/SKILL.md`). Renders run on this Mac with
`render-mac.sh`; a session working from anywhere else stops at Checkpoint B.

## The hands-off pipeline

Dropping recordings into `videos/_inbox/<name>/` (the camera file with the mic, the screen file for a tutorial, an
optional `notes.txt`) starts an edit on its own: a launchd agent claims the folder, the cut runs (scripts, then an
unattended Claude Code run for the judgment calls), and a Mac notification opens `videos/<name>/REVIEW-A.html`.
`yt status` lists every edit and its stage; `yt log <name>` shows its log. Details: the skill's `pipeline/` folder and
its "Hands-off pipeline" section.

Stages: queued -> cutting -> **awaiting-A** -> storyboarding -> **awaiting-B** -> rendering -> done (or failed).
On the work Mac (hand-off) an approved render waits as **awaiting-import** until its video comes back.

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
   at A `bash .claude/skills/youtube-edit/pipeline/yt run <name> storyboard`, at B `bash .claude/skills/youtube-edit/pipeline/yt run <name> render`. Do not do the next stage's work in this thread.
   **On the work Mac** (`yt host` says renders are handed off) the render stage packs `~/Desktop/<name>-render.zip`:
   tell him to drag it through Screen Sharing into the home Mac's `videos/_render-inbox/`. When he says the video
   is back ("agents-3 is back, it's in Downloads"), find the file and run `bash .claude/skills/youtube-edit/pipeline/yt import <name> <video>`;
   if it refuses, say why. With an automatic render host (SSH or a share) instead, run `yt host` first and, when the
   home Mac isn't ready, ask whether he'll fix it or wants `yt run <name> render --here`.
5. Keep replies short: what you changed, what starts next, and that a notification will come.

## Machines

This repo is cloned on two Macs: the home Mac and the HubSpot work Mac. `videos/` is not in git, so footage, edits and
renders stay on the machine that made them. On the work Mac there are no Tella or Epidemic Sound connectors: take
screen recordings as plain files (the "Two-file tutorials" route), use the sound effects in `shared/sfx`, and default
to the `hubspot` profile. Music for a work video goes on at the home Mac, which has the Epidemic Sound connector: when
asked there to "add music to <name> in the render inbox", work on `videos/_render-inbox/<name>/out/` by the skill's
Music rules (two or three tracks under the same 12 s, cut to length, ducked, limiter, a no-music twin, `MUSIC.md`),
writing next to the video in `out/`; never in the work Mac's thread. Company software on the work Mac blocks file sharing and SSH to the home
network, so its renders are handed off by hand: a bundle zip carried over Screen Sharing, rendered on the home Mac,
the video carried back and imported (`yt import`). Devs:After Dark is edited and rendered on the home Mac only. When the
skill changes ("save this to the skill"), commit it and push, so the other Mac gets it with `git pull`.
