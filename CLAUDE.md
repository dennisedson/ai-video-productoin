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
On the work Mac a render waiting for the home Mac shows as **awaiting-host**.

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
   **Before a render on the work Mac** (the render host is set: `yt host` says so), run `bash .claude/skills/youtube-edit/pipeline/yt host` first. If
   the home Mac isn't ready, don't start the render: tell him why and ask whether he'll fix it (wake the home Mac,
   reconnect; then check again and start with `yt run <name> render`) or wants it rendered on the work Mac
   (`yt run <name> render --here`). The
   same applies to "render <name>" for a video in awaiting-host.
5. Keep replies short: what you changed, what starts next, and that a notification will come.

## Machines

This repo is cloned on two Macs: the home Mac and the HubSpot work Mac. `videos/` is not in git, so footage, edits and
renders stay on the machine that made them. On the work Mac there are no Tella or Epidemic Sound connectors: take
screen recordings as plain files (the "Two-file tutorials" route), use HubSpot-licensed music and the sound effects in
`shared/sfx`, and default to the `hubspot` profile. The work Mac renders on the home Mac (its Video folder over SSH,
`homemac`) and asks when the home Mac can't be reached; Devs:After Dark is edited and rendered on the home Mac only. When the
skill changes ("save this to the skill"), commit it and push, so the other Mac gets it with `git pull`.
