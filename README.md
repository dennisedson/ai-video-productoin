# ai-video-production

Dennis's YouTube editing setup: the youtube-edit skill (WeAreNoCode's, customised) with its hands-off pipeline, the
`hubspot` and `devs-after-dark` profiles, and the shared sound effects and images. It runs locally in Claude Code on a
Mac and renders 4K with HyperFrames.

The repo is the Claude Code project folder. Clone it, open Claude Code on it, and the skill and `CLAUDE.md` load.
`videos/` is ignored, so footage, edits and renders never leave the machine that made them.

| Path | What it is |
|---|---|
| `.claude/skills/youtube-edit/` | the skill: `SKILL.md`, `scripts/`, `pipeline/`, `profiles/`, `formats/`, `assets/` |
| `CLAUDE.md` | how Claude Code handles approvals and notes, and what differs between the two Macs |
| `shared/` | the `--shared` folder every edit uses: `sfx/`, `img/`, `DAD-Audio/` |
| `WeAreNoCode-YouTube-Editor/` | the style guide (with the "Yours" column), setup notes and licences |
| `videos/` | one folder per video (`videos/<name>/raw/`) and the pipeline inbox `videos/_inbox/`; not in git |

Connectors are optional. Tella and Epidemic Sound help when they're there; without them you record the screen with
anything and use `shared/sfx` and music you're licensed to use.

---

## Set up a new Mac (the work Mac)

### 0. Check with IT first
Find out whether you're allowed to:
- clone a private repo from your personal GitHub account
- install Homebrew, and packages from npm and pip
- download the Parakeet speech-to-text model (`npx hyperframes models install parakeet`)
- run Google Chrome (HyperFrames renders through it, in the background)
- use Claude Code on this machine, and with which account (probably HubSpot's, not your personal one)
- add a LaunchAgent (only for the hands-off pipeline in step 8; everything else works without it)

### 1. Clone the repo

    git clone https://github.com/dennisedson/ai-video-production.git ~/Video

Any folder works; the rest of this guide calls it the Video folder. If git asks for a password, sign in with
`gh auth login` or a personal access token.

### 2. Open Claude Code on the folder
- Claude desktop app → New → **Claude Code**
- **Local**, not cloud, so footage and renders stay on the machine
- Folder: the Video folder
- Permissions: **Auto** if your work setup allows it, otherwise **Ask**
- Model: the latest Opus for setup

### 3. Turn on the browser and install Chrome
Settings → Claude Code → turn on the browser setting. Install Google Chrome if it isn't there.

### 4. Install the dependencies and run the tests
Paste this into Claude Code:

> The youtube-edit skill is already installed in .claude/skills/youtube-edit. Run its setup check: verify Node 22+,
> HyperFrames (npx hyperframes --version and npx hyperframes doctor), FFmpeg/ffprobe, Python 3 with numpy, auto-editor,
> Parakeet (npx hyperframes models install parakeet) and Chrome. Install whatever is missing with Homebrew and pip, and
> ask me before anything that needs admin rights. Also download the local GSAP copy and the HyperFrames media skill
> (npx hyperframes skills update media-use). The sound effects are already in shared/sfx; don't copy them again. Then
> run the tests from the scripts folder: cd .claude/skills/youtube-edit/scripts && python3 -m unittest tests

- If Homebrew's Python refuses `pip install numpy`, use `brew install numpy`.
- `hyperframes doctor` may flag Kokoro TTS, MusicGen and Docker. The skill uses none of them; ignore those.
- You're done when the tests end with **OK**.

### 5. Start a new thread
Skills load when a thread starts. Open a new Claude Code thread on the Video folder and ask "what skills do you
have?" `youtube-edit` should be in the list.

### 6. Smoke test with a 30–60 s hook
- Record a talking-head hook (4K, 30 fps, nothing baked in). Fluffed a line? Pause about 2 s and restart the sentence.
- Put it in `videos/test-hook/raw/`
- Prompt: "Use the HubSpot profile. Please use my YouTube editing skill to edit this hook: videos/test-hook/raw/<file>"
- **Checkpoint A:** `PAPER-CUT.md` (what gets cut) and the camera grade sheet. The home camera wants `blacks`; with a
  different camera or room, look at the sheet before choosing.
- **Checkpoint B:** `storyboard.json` and `snaps/sheet.png` (the planned overlays). Claude also writes `render.json`.

### 7. Render
In Terminal, from the Video folder:

    bash .claude/skills/youtube-edit/scripts/render-mac.sh videos/test-hook

One command, no AI in the loop. It builds the graded 4K cut, renders, levels to -14 LUFS, checks the result, adds the
intro sting and end card when `render.json` has `bookends`, and copies the file to `~/Movies/YouTube Renders/<name>/`.
On a failure it prints the step to resume from (`--from STEP`); `--dry-run` shows the commands.

### 8. Optional: the hands-off pipeline
Needs the `claude` command line signed in once and permission to add a LaunchAgent. From the Video folder:

    bash .claude/skills/youtube-edit/pipeline/install.sh

Then drop recordings into `videos/_inbox/<name>/` (camera file, screen file for a tutorial, optional `notes.txt` such
as "HubSpot profile"). A notification comes at each checkpoint; approve or send notes in a Claude Code thread
("approve <name>, grade blacks"). `yt status` (every video with its progress; `yt watch` keeps it on screen), `yt log <name>`,
`yt run <name> cut|storyboard|render`.
`--budget N` caps each Claude stage (default $20); `uninstall.sh` removes it. `install.sh` writes
`pipeline/config.sh` for that machine; it isn't in git.

If IT blocks LaunchAgents, skip this step: run the same stages by hand in a Claude Code thread and render with step 7.

---

## Render work videos on the home Mac

The home Mac renders much faster, so the work Mac does the edit (the cut, the storyboard, both checkpoints) and the
home Mac does the 4K render. Nothing AI runs on the home Mac for this, so the personal Claude account isn't involved.
Only what the render needs goes over (about 1.3 GB for a tutorial; the 4K flat cut is built on the home Mac).

**On the HubSpot work Mac this is a hand-off by hand**, because company software blocks file sharing and SSH to the
home network (check with your manager or IT that carrying renders over this way is fine):

1. Approve Checkpoint B as usual. Instead of rendering, the work Mac packs the render bundle into
   `~/Desktop/<name>-render.zip` and notifies you; the video waits in **awaiting-import** (`yt bundle <name>` makes the
   zip again any time).
2. Drag the zip through Screen Sharing into the home Mac's `videos/_render-inbox/` (open that folder in Finder on the
   home Mac, inside the Screen Sharing window).
3. The home Mac's render agent waits until the zip has finished copying, unpacks it and renders. Its notification
   opens `videos/_render-inbox/<name>/out/`.
4. Drag the video (and `chapters.txt`) back to the work Mac, then `yt import <name> <video>` there: it checks the file
   (picture, sound, length), delivers it to `~/Movies/YouTube Renders/<name>/` and marks the video done. Or tell the
   Claude Code thread where you put it.
5. On the home Mac, `yt clean-renders` removes finished jobs, so no work footage stays there.

`yt run <name> render --here` renders on the work Mac instead. Devs:After Dark doesn't use any of this: it's edited
and rendered on the home Mac only.

### Home Mac (once)
1. `git pull` in the Video folder, then `bash .claude/skills/youtube-edit/pipeline/install.sh --serve-renders`.
   That loads a second agent that watches `videos/_render-inbox/` and checks in every minute.
2. The home Mac renders only while it's awake and you're logged in. Battery → Options: prevent automatic sleeping on
   power adapter when the display is off.

### Work Mac (once)
1. `git pull && git fetch --tags` in the Video folder.
2. `bash .claude/skills/youtube-edit/pipeline/install.sh --render-host handoff --priority utility`
   (`--render-host none` renders on the work Mac again). `--priority utility` runs the cut and storyboard stages at
   nearly full speed while other apps keep priority. `--priority background` puts them on the efficiency cores so the
   fans stay down, but the video steps take about 13x longer (a cut pass: ~45 min instead of ~4). `--priority normal`
   undoes either. In a rush:
   `yt run <name> cut --fast` runs that stage on all cores (a stage already running can't be sped up). The checkpoints
   work at 1080p on both Macs: only the final render builds 4K.
3. `yt host` should say renders are handed off by hand.

### Where the network allows it: automatic over SSH or a mounted share
On a Mac that may reach the home Mac directly, the work Mac can send the bundle, wait, and fetch the result on its own
(not on the HubSpot work Mac, where both are blocked):
- **SSH:** Remote Login on the home Mac; on the other Mac a key (`ssh-keygen -t ed25519 -f ~/.ssh/homemac -N ""`,
  `ssh-copy-id -i ~/.ssh/homemac.pub you@<home address>`), a `Host homemac` entry in `~/.ssh/config` with `HostName`,
  `User` and `IdentityFile ~/.ssh/homemac`, then `install.sh --render-host homemac:/Users/<you>/AI/claude-cowork/Video`.
- **Mounted share:** File Sharing on the home Mac with the Video folder shared; mount `smb://<home address>` → Video,
  then `install.sh --render-host /Volumes/Video`.

When the home Mac can't be reached the render asks (from a Claude Code thread, or a dialog: Check again / Render on
this Mac / Later -> awaiting-host) and never falls back on its own. `yt host` says what's missing.

### If something goes wrong
- A render that fails on the home Mac: its log is `videos/_render-inbox/<name>/render.log` there (and, in the
  automatic modes, comes back as `videos/<name>/render-remote.log`). Resume on the home Mac with
  `render-mac.sh videos/_render-inbox/<name> --from STEP`, or send the bundle again.
- `yt import` refuses a file without picture or sound, or whose length doesn't match the composition: check you
  dragged back the right video.
- A zip in the render inbox that isn't a render bundle is renamed `.rejected`, with a notification.

### Going back to the known-good version
The tag `before-remote-render` (commit `dfbf480`) is the setup both Macs ran on 2026-11-22: renders on each Mac, 4K
checkpoints, the inbox agent only. `videos/` isn't in git, so going back or forward never touches footage or edits,
and a video started on either version renders on the other. On either Mac, from the Video folder, with no stage
running (`yt status`):

    bash .claude/skills/youtube-edit/pipeline/uninstall.sh      # stops both agents (this version knows both)
    git checkout before-remote-render
    bash .claude/skills/youtube-edit/pipeline/install.sh        # the old installer: inbox agent only, fresh config

Forward again: `git checkout main && git pull`, then `install.sh` with the flags you use on that Mac. If the tag
isn't there (`git tag` shows nothing), use `dfbf480` in its place, or create it once: `git tag before-remote-render
dfbf480 && git push origin before-remote-render`.

---

## Turn the home Mac's folder into a clone (once)

The home folder (`~/AI/claude-cowork/Video`) already has these files, so connect it to the repo instead of cloning
again. Don't change the skill until this is done. In Terminal:

    cd ~/AI/claude-cowork/Video
    git init -b main
    git remote add origin https://github.com/dennisedson/ai-video-production.git
    git fetch origin
    git reset origin/main          # points at the repo; your files are untouched
    git status                     # expect only CLAUDE.md (the repo adds a "Machines" section)
    git checkout -- .              # take the repo's versions
    git branch --set-upstream-to=origin/main
    rm .repo-export.tgz            # left over from building the repo

`videos/`, `Claude outputs/` and the upstream `WeAreNoCode-YouTube-Editor/youtube-edit/` copy are ignored and stay
as they are.

## Keeping the two Macs in step

- After a change to the skill or a profile (including "save this to the skill"): ask Claude Code to commit and push,
  or run `git add -A && git commit -m "..." && git push`.
- Before an edit on the other Mac: `git pull`. Threads load the skill when they start, so pull before opening one.
- If both Macs changed the skill, `git pull` merges; `SKILL.md` is long, so commit small and often to avoid conflicts.

## YouTube metadata

Approving Checkpoint B also starts `yt run <name> youtube` beside the render (a notification when it's ready; `yt
status` shows "YouTube: ready"). It writes `videos/<name>/youtube/`:

- `YOUTUBE.md`: three title options, the description (search-first opening, CTA links, "In this video" questions,
  chapters, key terms, hashtags), cards with timestamps, the end screen, tags, the pinned comment, and what to check.
  Times are on the published video's clock (the intro sting and end card accounted for).
- `thumbnail-N.jpg`: two or three thumbnail options in the profile's brand (3840x2160; `-mobile.jpg` is a 1280x720
  copy under the YouTube app's 2 MB limit), side by side in `thumbnails.jpg`. The draft picks the words (2 to 5, one
  key word in the accent colour) and a camera frame from `frames.jpg`; `scripts/thumbnail.py` takes that frame from
  the 4K camera file with the video's grade, cuts you out (`hyperframes remove-background`; if that fails, the photo
  fades into the background instead and YOUTUBE.md says so) and lays it out from `profiles/<profile>/thumbnail/`:
  HubSpot's Deep Teal, HubSpot Serif headline in Cream with the key word in Orange, Sage series line, Orange ring and
  rule, sprocket lockup; Devs:After Dark's Night and amber glow, Playfair headline with the key word in amber italic,
  JetBrains Mono label, the logo. Change the words or frame ("thumbnail 2: 'Skip the HubSpot UI', the frame at 1:40")
  and a thread edits `metadata.json` and runs `yt thumb <name> [N]`; `yt thumb <name> frames` makes a fresh frame sheet.
  The first cutout on a Mac downloads the background-removal runtime once.
  **A headshot instead of a frame:** put it in `shared/img/headshots/` on each Mac (git-ignored, so your photo stays
  off GitHub; a guest's goes in `videos/<name>/`). Ask for it per video ("thumbnail 1: use dennis.jpg"), or make it a
  profile's default with `"face": "dennis.jpg"` in `profiles/<profile>/thumbnail/config.json`. A PNG with a
  transparent background is used as it is; anything else is cut out.
- `captions.srt`: your own captions with transcription fixes; upload it in Studio (Subtitles → Upload file → With
  timing). AI search reads captions, chapter titles and descriptions, not the video.
- `links.tsv`: every tracked link with its full UTM URL (`utm_source=youtube&utm_medium=video&utm_campaign=<series>&
  utm_content=<video>_<placement>_<link>`) and its Bitly link. The pipeline shortens them through Bitly's API after
  each draft (`yt shorten <name>` does it by hand), titled "video · link · placement" and tagged in Bitly, then
  rebuilds YOUTUBE.md with them. A short link is reused on every rebuild and replaced only if its long link changes
  (a renamed campaign). Without a token, or past the plan's monthly cap, the rest stay long and YOUTUBE.md says so.

**The Bitly account is HubSpot's and is used only for HubSpot content.** It belongs to the `hubspot` profile; other
profiles (Devs:After Dark) have none, so their links stay long. It's used only when a video is explicitly HubSpot: an
edited video on the `hubspot` profile, or an inbox video whose `notes.txt` says HubSpot. An inbox video with no notes is
only assumed to be HubSpot, so it's skipped, and YOUTUBE.md says so; if it is HubSpot content, `yt shorten <name>
--hubspot` confirms it.

**Bitly setup, once per Mac:** create a token in the HubSpot Bitly account (Settings → API) and store it in the
Keychain as `bitly-hubspot` (it asks for the token; nothing goes in the repo or your shell history):

    security add-generic-password -U -a "$USER" -s bitly-hubspot -w

Settings are in `profiles/hubspot/youtube.json` under `bitly`: `keychain` (the Keychain item), `auto` (shorten after
each draft), `domain` (`bit.ly`, or a branded domain the plan has), `group_guid` (empty = the default group),
`per_placement` (`false` = the description and pinned comment share one link per destination, about one fewer link
per video, for a plan's monthly cap).

Links come only from the profile's library (`profiles/hubspot/LINKS.md`, pages opened and checked) or pages the run
opens and verifies; anything it can't confirm is listed for you. Ask a Claude Code thread for changes ("make the
second title the first", "add the Agent CLI blog") and it edits `metadata.json` and rebuilds.

**Finished videos that need only the metadata** (no edit): drop the video into `videos/_youtube-inbox/`, either the
file itself (its name becomes the video's name) or a folder `<name>/` with the video and a `notes.txt` saying what it is
("series: HubSpot Is Going Headless", "next: the Agent CLI", "Devs:After Dark", names to spell right, links to use).
Once it stops growing it moves to `videos/<name>/`, is transcribed, and the same draft lands in `videos/<name>/youtube/`
(`yt status`: transcribing -> drafting -> youtube-ready; a notification opens YOUTUBE.md). It works on either Mac;
after a `git pull`, run `install.sh` once with your usual flags so the agent also watches this folder.

When the video is live: `yt published <name> <url>`. The catalog, `catalog/VIDEOS.md`, keeps one entry per video
(summary, topics, questions it answers, chapters, links, URL); the next videos' metadata uses it for cards and
related links. Commit and push it when it changes; a copy lives in the Claude project.

## Music and sound
- Sound effects inside the edit: `shared/sfx` (the free HyperFrames library), on both Macs.
- Music: the skill mixes it onto the finished master (ducked under the voice, a no-music twin kept, `MUSIC.md`).
  The Epidemic Sound connector is allowed only on the home Mac, so for a work video music goes on there, after the
  4K render and before the video goes back: in a Claude Code thread on the home Mac's Video folder, "add music to
  <name> in the render inbox" (the files land next to the video in `out/`); then drag the music version back and
  `yt import` it. Check that your Epidemic Sound plan covers videos on HubSpot's channel; a personal or creator
  licence may not.

## Licences
The skill started as WeAreNoCode's starter kit (MIT, see `WeAreNoCode-YouTube-Editor/LICENSES/`). The HubSpot fonts in
`profiles/hubspot/fonts/` are HubSpot's and the Devs:After Dark assets are Dennis's; keep the repo private.

---

## Context for a Claude project on the work account

Claude Code gets its context from `CLAUDE.md`. A Claude project on the work account is for planning chats (scripts,
video ideas, review notes) that should know about the setup.

**Name:** HubSpot Video Production

**Description:** Editing HubSpot developer videos locally with Claude Code and the youtube-edit skill.

**Instructions** (paste into the project's instructions):

> I'm Dennis, a Senior Developer Advocate on HubSpot's builder relations team. I make developer videos (talking-head
> hooks and screen tutorials) and edit them with Claude Code on this Mac, using the youtube-edit skill (originally
> WeAreNoCode's, customised by me). The setup lives in my private repo dennisedson/ai-video-production, cloned on my home
> Mac and this work Mac.
>
> How the setup works:
> - Edits run locally in Claude Code on the Video folder; renders always run on the Mac with
>   `.claude/skills/youtube-edit/scripts/render-mac.sh`, never in the cloud. Footage stays on the machine.
> - Every HubSpot video uses the `hubspot` profile: Orange #FF4800 key words, Deep Teal #042729 background, Cream cards
>   with Neutral text, HubSpot Sans for words and HubSpot Serif for headlines. A 3 s intro sting goes after the hook
>   (never before it), and a 15 s end card ("Up next" plus YouTube end-screen placeholders) goes after the sign-off.
> - No connectors on this machine: no Tella, no Epidemic Sound. Screen recordings come in as plain files; music must be
>   HubSpot-licensed; sound effects come from `shared/sfx`.
> - Each edit stops at two checkpoints for my approval: A (the paper cut plus the camera grade, usually `blacks`) and
>   B (the storyboard with its overlay sheet and a 1080p preview).
> - Tutorials are two files (face + screen). The face card goes on the side I look toward, never facing off-screen.
>   The video opens full frame on me until the screen matters, and any stretch of 8 s or more with nothing worth
>   watching on screen goes full frame too.
>
> When I ask for help in this project: write scripts and hooks for camera (short sentences, a clear first line that
> names the topic), plan tutorials so the screen is worth watching, and turn my review notes into timestamped
> instructions I can paste into Claude Code. Keep answers short.

**Knowledge:** add this README and `WeAreNoCode-YouTube-Editor/STYLE-GUIDE.md`.
